"""TypeSafe Jev (System One): typed judgments for the parts of PatchUp that are judgement, not generation.

Jev returns probabilities over levels/options, not text. We use it to decide how a user's
message moves the counterpart and how well it scores on the coach rubric; Sarvam 105b then
only has to act and write. Everything here is optional: without TYPESAFE_API_KEY the
actor self-reports movement and the coach LLM self-scores, as before.
"""
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from content import CONVERSATION_TYPES, DEFENSIVENESS_LEVELS, MOVEMENT_LEVELS, RUBRICS, TRUST_LEVELS

load_dotenv()

TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"

# Noul probability at or above which an intake is treated as unsafe to simulate.
SAFETY_THRESHOLD = 0.6
# Noul probability at or above which a conditional rubric dimension is scored this turn.
APPLIES_THRESHOLD = 0.5
MAX_RECEPTIVENESS_DELTA = 25
MAX_DIAL_DELTA = 15
TRANSCRIPT_WINDOW = 8

log = logging.getLogger("patchup")


def judge_enabled() -> bool:
    return bool(TYPESAFE_API_KEY)


def needs_english(text: str) -> bool:
    """Jev is English-first. Native-script Indic text (what Saarika returns for hi-IN, ta-IN, ...) gets a
    translation alongside; romanised Hinglish is left alone."""
    return any(ord(ch) > 0x024F for ch in text)


async def system_one(state, questions: dict) -> dict:
    """One evaluation request. Returns the `answers` map keyed by question id."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            TYPESAFE_URL,
            headers={"Authorization": f"Bearer {TYPESAFE_API_KEY}", "Content-Type": "application/json"},
            json={"state": state, "model": JEV_MODEL, "questions": questions},
        )
        if resp.status_code != 200:
            log.warning("TypeSafe error %s: %s", resp.status_code, resp.text[:300])
            resp.raise_for_status()
        return resp.json()["answers"]


# ─── Mapping Jev answers to game numbers (code owns the policy) ──────────────

def score_to_delta(score: float, level_count: int, max_delta: int) -> int:
    """Expected level (0..n-1) → symmetric delta around the middle level."""
    mid = (level_count - 1) / 2
    return int(round((float(score) - mid) / mid * max_delta))


def score_to_ten(score: float, level_count: int) -> float:
    """Expected level (0..n-1) → 0-10, one decimal."""
    return round(float(score) / (level_count - 1) * 10, 1)


def _score(answers: dict, question_id: str) -> float:
    answer = answers.get(question_id) or {}
    if answer.get("type") != "score" or not isinstance(answer.get("score"), (int, float)):
        raise ValueError(f"Jev returned no score for {question_id}")
    return float(answer["score"])


def _noul(answers: dict, question_id: str) -> float:
    answer = answers.get(question_id) or {}
    if answer.get("type") != "noul" or not isinstance(answer.get("noul"), (int, float)):
        raise ValueError(f"Jev returned no noul for {question_id}")
    return float(answer["noul"])


# ─── Per-turn judgement ──────────────────────────────────────────────────────

def turn_state(brief: dict, conversation: list, user_text: str, score: int, state: dict,
               user_text_english: Optional[str] = None) -> dict:
    cp = brief["counterpart"]
    payload = {
        "conversation_type": brief["conversation_type"],
        "counterpart": {
            "name": cp["name"], "role": cp["role"], "style": cp.get("style", ""),
            "relationship_to_user": cp.get("relationship", ""),
            "what_actually_drives_them": brief.get("hidden_motivations", []),
        },
        "background": brief.get("history", ""),
        "user_goal": brief.get("user_goal", ""),
        "counterpart_state_before_this_message": {
            "receptiveness": score, "trust": state["trust"], "defensiveness": state["defensiveness"],
        },
        "transcript": [
            {"speaker": "user" if turn["role"] == "user" else cp["name"], "text": turn["text"]}
            for turn in conversation[-TRANSCRIPT_WINDOW:]
        ],
        "latest_user_message": user_text,
    }
    if user_text_english:
        payload["latest_user_message_english"] = user_text_english
    return payload


def turn_questions(brief: dict) -> dict:
    cp = brief["counterpart"]
    rubric = RUBRICS[brief["conversation_type"]]
    questions = {
        "movement": {
            "type": "score",
            "instructions": (
                f"Given who {cp['name']} is (`counterpart`), what drives them, and their state before this message, "
                f"how does `latest_user_message` move {cp['name']} toward what the user wants (`user_goal`)?"
            ),
            "criteria": MOVEMENT_LEVELS,
        },
        "trust": {
            "type": "score",
            "instructions": f"After `latest_user_message`, does {cp['name']} trust the user's motives more or less than before?",
            "criteria": TRUST_LEVELS,
        },
        "defensiveness": {
            "type": "score",
            "instructions": f"After `latest_user_message`, is {cp['name']} more or less defensive than before?",
            "criteria": DEFENSIVENESS_LEVELS,
        },
    }
    for dim, spec in rubric["dimensions"].items():
        questions[dim] = {
            "type": "score",
            "instructions": {
                "skill": spec["description"],
                "question": f"How well does `latest_user_message` demonstrate `skill`, in the context of this {rubric['name'].lower()} conversation?",
            },
            "criteria": spec["levels"],
        }
        if spec.get("applies_when"):
            # Asked alongside the score; code drops the score when the precondition isn't met.
            questions[f"applies_{dim}"] = {
                "type": "noul",
                "instructions": (
                    f"Looking at `transcript` (everything before `latest_user_message`), is it true that "
                    f"{spec['applies_when'].replace('the counterpart', cp['name'])}?"
                ),
                "criteria": {"true": "Yes, it has already happened in the transcript",
                             "false": "No, nothing like that has happened yet"},
            }
    return questions


async def judge_turn(brief: dict, conversation: list, user_text: str, score: int, state: dict,
                     user_text_english: Optional[str] = None) -> dict:
    """Movement deltas and rubric scores for one user message. Raises on any API or shape problem."""
    rubric = RUBRICS[brief["conversation_type"]]
    answers = await system_one(
        turn_state(brief, conversation, user_text, score, state, user_text_english),
        turn_questions(brief),
    )
    scores, skipped = {}, []
    for dim, spec in rubric["dimensions"].items():
        if spec.get("applies_when") and _noul(answers, f"applies_{dim}") < APPLIES_THRESHOLD:
            skipped.append(dim)  # nothing to handle yet; don't score it
            continue
        scores[dim] = score_to_ten(_score(answers, dim), len(spec["levels"]))
    return {
        "receptiveness_delta": score_to_delta(_score(answers, "movement"), len(MOVEMENT_LEVELS), MAX_RECEPTIVENESS_DELTA),
        "trust_delta": score_to_delta(_score(answers, "trust"), len(TRUST_LEVELS), MAX_DIAL_DELTA),
        "defensiveness_delta": score_to_delta(_score(answers, "defensiveness"), len(DEFENSIVENESS_LEVELS), MAX_DIAL_DELTA),
        "scores": scores,
        "skipped": skipped,
        "confidence": {
            key: answers[key].get("confidence")
            for key in ("movement", "trust", "defensiveness", *rubric["dimensions"])
            if isinstance(answers.get(key), dict)
        },
    }


# ─── Intake judgement (scenario build) ───────────────────────────────────────

INTAKE_QUESTIONS = {
    "abuse": {
        "type": "noul",
        "instructions": "Does `intake` describe physical or sexual violence, or threats of physical harm, in the user's real situation?",
        "criteria": {
            "true": "Someone is hit, assaulted, or threatened with harm",
            "false": "Harsh words, shouting, a difficult boss or partner, but no physical or sexual harm",
        },
    },
    "self_harm": {
        "type": "noul",
        "instructions": "Does `intake` indicate that the user or the other person is at risk of suicide or self-harm?",
        "criteria": {
            "true": "Suicidal thoughts, self-harm, or 'not wanting to live' are present",
            "false": "Distress or sadness without any risk to life",
        },
    },
    "conversation_type": {
        "type": "choice",
        "instructions": "What kind of difficult conversation is the user rehearsing, based on `intake`?",
        "criteria": CONVERSATION_TYPES,
    },
}


async def judge_intake(intake: dict) -> dict:
    answers = await system_one({"intake": intake}, INTAKE_QUESTIONS)
    abuse, self_harm = _noul(answers, "abuse"), _noul(answers, "self_harm")
    category = "self_harm" if self_harm >= SAFETY_THRESHOLD else "abuse" if abuse >= SAFETY_THRESHOLD else None
    choice = answers.get("conversation_type") or {}
    conversation_type = choice.get("choice") if choice.get("choice") in RUBRICS else None
    return {
        "safety_category": category,
        "safety_probabilities": {"abuse": abuse, "self_harm": self_harm},
        "conversation_type": conversation_type,
        "type_probabilities": choice.get("probabilities") or {},
    }
