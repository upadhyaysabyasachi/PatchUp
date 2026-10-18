"""PatchUp API: rehearse difficult conversations with a voice counterpart and a coach.

Orchestration lives here. Content (presets, rubrics) is in content.py, prompt text in
prompts.py, LLM-output parsing in parsing.py, Sarvam calls in sarvam.py, TypeSafe Jev
judgements in typesafe.py, storage in db.py.
"""
import asyncio
import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, computed_field

load_dotenv()

import db  # noqa: E402  (reads env at import; load_dotenv must run first)
from content import (  # noqa: E402
    ACCENTS, CLASSIC_DIFFICULTY_IDS, DEFAULT_ACCENT, DEFAULT_EMOTION, DIFFICULTY_CONFIG, EMOTION_VOICE_PARAMS, LANGUAGES,
    PERSONAS, PRESETS, RUBRICS, SCENARIOS, TEMPERAMENT_IDS, classic_brief, guess_conversation_type,
    pick_voice, preset_brief, preset_intake, safety_payload, screen_intake_text,
)
from db import (  # noqa: E402
    db_create_session, db_delete_session, db_get_session, db_leaderboard, db_record_stats,
    db_update_session,
)
from elevenlabs import (  # noqa: E402
    ELEVENLABS_AUDIO_MIME, ELEVENLABS_TTS_MODEL, elevenlabs_enabled, elevenlabs_stt, elevenlabs_tts,
    pick_elevenlabs_voice, supports_language,
)
from parsing import brief_from_data, clamp_int, parse_actor, parse_brief, parse_coach, parse_tips  # noqa: E402
from prompts import (  # noqa: E402
    build_actor_messages, build_actor_prompt, build_brief_messages, build_coach_messages,
    build_debrief_messages,
)
from sarvam import sarvam_llm, sarvam_stt, sarvam_translate, sarvam_tts  # noqa: E402
from typesafe import judge_enabled, judge_intake, judge_turn, needs_english  # noqa: E402

log = logging.getLogger("patchup")

app = FastAPI(title="PatchUp API", version="2.1.0")

# Browsers only; no cookies are used, so credentials stay off. Set ALLOWED_ORIGINS in prod.
# ALLOWED_ORIGIN_REGEX covers hosts that vary per deployment (Vercel preview URLs).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX") or None
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

LANGUAGE_IDS = {language["id"] for language in LANGUAGES}
GOAL_SCORE = 90

# Speech providers: ElevenLabs when a key is set, Sarvam otherwise. Either can be forced
# with TTS_PROVIDER / STT_PROVIDER=sarvam|elevenlabs. ElevenLabs failures fall back to Sarvam per call.
_default_provider = "elevenlabs" if elevenlabs_enabled() else "sarvam"
TTS_PROVIDER = os.getenv("TTS_PROVIDER") or _default_provider
STT_PROVIDER = os.getenv("STT_PROVIDER") or _default_provider


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class IntakeCounterpart(BaseModel):
    name: str = ""
    role: str = ""
    gender: str = "female"
    accent: str = DEFAULT_ACCENT  # how they sound; see content.ACCENTS
    relationship: str = ""
    style: str = ""


class Intake(BaseModel):
    counterpart: IntakeCounterpart = Field(default_factory=IntakeCounterpart)
    user_goal: str = ""
    user_fears: str = ""
    history: str = ""


class ScenarioBuildRequest(BaseModel):
    preset_id: Optional[str] = None
    intake: Optional[Intake] = None


class ScenarioBuildResponse(BaseModel):
    brief: Optional[dict] = None
    safety: Optional[dict] = None
    built_by: str  # preset | llm | screen
    judged_by: str = "llm"  # jev | llm | screen


class SessionStartRequest(BaseModel):
    # Rehearsal flow: a brief from /api/scenario/build
    brief: Optional[dict] = None
    # Classic flow
    persona_id: Optional[str] = None
    scenario_id: Optional[str] = None
    difficulty: str = "medium"
    language: str = "hi-IN"
    previous_session_id: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: str
    opening_message: str
    opening_audio: str
    initial_score: int
    kind: str
    counterpart_name: str
    counterpart_role: str
    counterpart_emoji: str
    scenario_title: str
    difficulty_name: str
    conversation_type: str
    meter_label: str
    dimensions: list[dict]
    goal: str
    counterpart_state: dict
    audio_mime: str = "audio/wav"
    voice_provider: str = "sarvam"

    # Older frontend builds read this name.
    @computed_field
    @property
    def persona_name(self) -> str:
        return self.counterpart_name


class CoachNote(BaseModel):
    scores: dict[str, float]
    note: str
    stronger: str


class RespondResponse(BaseModel):
    user_text: str
    counterpart_text: str
    counterpart_audio: str
    score_delta: int
    current_score: int
    emotion: str
    status: str
    turn_number: int
    coach: Optional[CoachNote] = None
    skill_scores: dict[str, float] = Field(default_factory=dict)
    counterpart_state: dict[str, int] = Field(default_factory=dict)
    judged_by: str = "actor"  # jev | actor
    audio_mime: str = "audio/wav"
    voice_provider: str = "sarvam"  # elevenlabs | sarvam
    stt_provider: Optional[str] = None  # elevenlabs | sarvam | None for text input

    # Keep cached clients working during the production rollout.
    @computed_field
    @property
    def girlfriend_text(self) -> str:
        return self.counterpart_text

    @computed_field
    @property
    def girlfriend_audio(self) -> str:
        return self.counterpart_audio


class RewindRequest(BaseModel):
    turn_number: int


class SessionSnapshot(BaseModel):
    session_id: str
    status: str
    current_score: int
    counterpart_state: dict
    skill_scores: dict[str, float]
    conversation: list[dict]
    next_turn_number: int


class SessionEndResponse(BaseModel):
    final_score: int
    verdict: str
    total_turns: int
    best_response: Optional[str] = None
    worst_response: Optional[str] = None
    tips: list[str]
    status: str
    kind: str
    conversation_type: str
    goal: str
    meter_label: str
    dimensions: list[dict]
    skill_scores: dict[str, float]
    transcript: list[dict]
    reveal: dict
    previous_score: Optional[int] = None
    counterpart_name: str


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dimension_list(conversation_type: str) -> list[dict]:
    return [
        {"id": key, "label": key.replace("_", " ").capitalize(), "description": spec["description"]}
        for key, spec in RUBRICS[conversation_type]["dimensions"].items()
    ]


def session_brief(session: dict) -> dict:
    """Rows written before briefs existed are classic girlfriend sessions."""
    if isinstance(session.get("brief"), dict):
        return session["brief"]
    return classic_brief(session["persona_id"], session["scenario_id"])


def initial_state(difficulty: str) -> dict:
    return dict(DIFFICULTY_CONFIG[difficulty]["state"])


def session_state(session: dict) -> dict:
    state = session.get("counterpart_state") or initial_state(session["difficulty"])
    return {
        "trust": clamp_int(state.get("trust"), 0, 100, 50),
        "defensiveness": clamp_int(state.get("defensiveness"), 0, 100, 50),
    }


def state_at(conversation: list, difficulty: str) -> tuple[int, dict]:
    """Receptiveness + dials at the end of `conversation`, from snapshots or by replaying deltas."""
    diff = DIFFICULTY_CONFIG[difficulty]
    for turn in reversed(conversation):
        if turn.get("role") == "counterpart" and isinstance(turn.get("state"), dict):
            snapshot = turn["state"]
            return clamp_int(snapshot.get("receptiveness"), 0, 100, diff["starting_score"]), {
                "trust": clamp_int(snapshot.get("trust"), 0, 100, diff["state"]["trust"]),
                "defensiveness": clamp_int(snapshot.get("defensiveness"), 0, 100, diff["state"]["defensiveness"]),
            }
    score = diff["starting_score"]
    for turn in conversation:
        if turn.get("role") == "counterpart":
            score = clamp_int(score + clamp_int(turn.get("score_delta", 0), -25, 25), 0, 100)
    return score, initial_state(difficulty)


def skill_averages(conversation: list, dimensions) -> dict[str, float]:
    totals = {dim: [0.0, 0] for dim in dimensions}
    for turn in conversation:
        if turn.get("role") != "user" or not isinstance(turn.get("coach"), dict):
            continue
        for dim, value in (turn["coach"].get("scores") or {}).items():
            if dim in totals and isinstance(value, (int, float)):
                totals[dim][0] += value
                totals[dim][1] += 1
    return {dim: round(total / count, 1) for dim, (total, count) in totals.items() if count}


def status_for(score: int) -> str:
    if score >= GOAL_SCORE:
        return "patched_up"
    if score <= 0:
        return "blocked"
    return "ongoing"


def apply_gain(delta: int, difficulty: str) -> int:
    """Positive movement is scaled by the temperament; losses land in full."""
    if delta <= 0:
        return delta
    return int(round(delta * DIFFICULTY_CONFIG[difficulty]["gain_factor"]))


def voice_params(difficulty: str, emotion: str, state: dict) -> tuple[float, float]:
    """Average of difficulty base and emotion params, nudged by defensiveness (±0.1 at the extremes)."""
    diff = DIFFICULTY_CONFIG[difficulty]
    emo = EMOTION_VOICE_PARAMS.get(emotion, EMOTION_VOICE_PARAMS[DEFAULT_EMOTION])
    nudge = (state["defensiveness"] - 50) / 500
    return (diff["tts_pace"] + emo["pace"]) / 2 + nudge, (diff["tts_temperature"] + emo["temperature"]) / 2 + nudge


def verdict_for(score: int, kind: str) -> str:
    if kind == "classic":
        if score >= GOAL_SCORE: return "🎉 PATCHED UP! She forgave you!"
        if score >= 70: return "😊 Almost there! She's softening up."
        if score >= 40: return "😐 Still naraaz. Better luck next time."
        if score >= 20: return "😤 You made it worse. Much worse."
        return "💔 BLOCKED. She's done."
    if score >= GOAL_SCORE: return "You got there."
    if score >= 70: return "Close. They were coming around."
    if score >= 40: return "Stalemate. Nothing lost, nothing won."
    if score >= 20: return "You lost ground."
    return "They walked away."


def normalized_intake(intake: dict) -> dict:
    counterpart = intake.get("counterpart") or {}
    return {
        "counterpart": {key: str(counterpart.get(key, "")).strip() for key in ("name", "role", "gender", "accent", "relationship", "style")},
        **{key: str(intake.get(key, "")).strip() for key in ("user_goal", "user_fears", "history")},
    }


def get_session_or_404(session_id: str) -> dict:
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


async def speak(text: str, counterpart: dict, language: str, emotion: str, pace: float, temperature: float) -> tuple[str, str, str]:
    """Synthesise the counterpart's line. Returns (base64 audio, mime, provider).

    ElevenLabs first when it's the configured provider and its model speaks the language;
    any failure there falls back to Sarvam Bulbul. A Sarvam failure is a 502.
    """
    if TTS_PROVIDER == "elevenlabs" and supports_language(ELEVENLABS_TTS_MODEL, language):
        try:
            voice_id = await pick_elevenlabs_voice(
                counterpart["name"], counterpart.get("gender", "female"), counterpart.get("accent", DEFAULT_ACCENT),
            )
            audio = await elevenlabs_tts(text, voice_id, language, emotion=emotion, pace=pace, temperature=temperature)
            return base64.b64encode(audio).decode("ascii"), ELEVENLABS_AUDIO_MIME, "elevenlabs"
        except Exception as e:
            log.warning("ElevenLabs TTS failed; falling back to Sarvam Bulbul: %s", e)
    try:
        audio = await sarvam_tts(text=text, speaker=counterpart["voice_id"], language=language, pace=pace, temperature=temperature)
        return audio, "audio/wav", "sarvam"
    except httpx.HTTPStatusError as e:
        detail = "Sarvam TTS failed."
        if e.response is not None:
            try:
                err = e.response.json()
                detail = err.get("error", {}).get("message", detail) or str(err)
            except Exception:
                detail = e.response.text or detail
        raise HTTPException(502, detail)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Sarvam TTS unreachable: {e}")
    except ValueError as e:  # missing SARVAM_API_KEY or empty text
        raise HTTPException(502, str(e))


async def transcribe(audio_bytes: bytes, language: str, content_type: str) -> tuple[str, str]:
    """Speech-to-text with the same provider order as speak(). Returns (text, provider)."""
    if STT_PROVIDER == "elevenlabs":
        try:
            return await elevenlabs_stt(audio_bytes, language=language, content_type=content_type), "elevenlabs"
        except Exception as e:
            log.warning("ElevenLabs STT failed; falling back to Sarvam Saarika: %s", e)
    return await sarvam_stt(audio_bytes, language=language, content_type=content_type), "sarvam"


async def _none():
    return None


def snapshot(session: dict) -> SessionSnapshot:
    conversation = session["conversation"]
    return SessionSnapshot(
        session_id=session["id"],
        status=session["status"],
        current_score=session["current_score"],
        counterpart_state=session_state(session),
        skill_scores=session.get("skill_scores") or {},
        conversation=conversation,
        next_turn_number=sum(1 for turn in conversation if turn["role"] == "user") + 1,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CORE CONVERSATION LOGIC (shared by voice + text endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

async def judge_with_jev(brief: dict, conversation: list, user_text: str, score: int, state: dict,
                         language: str) -> Optional[dict]:
    """Jev's verdict on the user's message, or None when Jev is off or fails (the actor then self-reports)."""
    if not judge_enabled():
        return None
    english = None
    if language != "en-IN" and needs_english(user_text):
        try:
            english = await sarvam_translate(user_text, "en-IN", source_language="auto")
        except Exception as e:
            log.warning("Translating the user's message for Jev failed; judging the original: %s", e)
    try:
        return await judge_turn(brief, conversation, user_text, score, state, english)
    except Exception as e:
        log.warning("Jev judgement failed; the actor self-reports this turn: %s", e)
        return None


async def process_user_message(session_id: str, user_text: str, stt_provider: Optional[str] = None) -> RespondResponse:
    """Jev judges the message (when configured), then actor and coach run concurrently, then TTS.
    Coach failure never fails the turn."""
    session = get_session_or_404(session_id)
    if session["status"] != "ongoing":
        raise HTTPException(400, f"Session already ended: {session['status']}")

    brief = session_brief(session)
    dimensions = list(RUBRICS[brief["conversation_type"]]["dimensions"])
    difficulty = session["difficulty"]
    state = session_state(session)
    score = session["current_score"]
    conversation = session["conversation"]

    judgement = await judge_with_jev(brief, conversation, user_text, score, state, session["language"])

    if judgement:
        # Code owns the state change; the actor plays the already-updated counterpart.
        receptiveness_delta = apply_gain(judgement["receptiveness_delta"], difficulty)
        new_score = clamp_int(score + receptiveness_delta, 0, 100)
        new_state = {
            "trust": clamp_int(state["trust"] + judgement["trust_delta"], 0, 100),
            "defensiveness": clamp_int(state["defensiveness"] + judgement["defensiveness_delta"], 0, 100),
        }
        actor_messages = build_actor_messages(session["system_prompt"], conversation, user_text, new_score, new_state, self_judging=False)
        coach_messages = build_coach_messages(brief, conversation, user_text, scores=judgement["scores"])
    else:
        actor_messages = build_actor_messages(session["system_prompt"], conversation, user_text, score, state, self_judging=True)
        coach_messages = build_coach_messages(brief, conversation, user_text)

    raw_actor, raw_coach = await asyncio.gather(
        sarvam_llm(actor_messages, temperature=0.7, max_tokens=300),
        sarvam_llm(coach_messages, temperature=0.3, max_tokens=400),
        return_exceptions=True,
    )
    if isinstance(raw_actor, BaseException):
        raise raw_actor
    actor = parse_actor(raw_actor, EMOTION_VOICE_PARAMS, DEFAULT_EMOTION)
    if isinstance(raw_coach, BaseException):
        log.warning("Coach call failed; turn continues without a note: %s", raw_coach)
        coach = None
    else:
        coach = parse_coach(raw_coach, dimensions)

    if judgement:
        coach = {**(coach or {"note": "", "stronger": ""}), "scores": judgement["scores"]}
    else:
        receptiveness_delta = actor["receptiveness_delta"]
        new_score = clamp_int(score + receptiveness_delta, 0, 100)
        new_state = {
            "trust": clamp_int(state["trust"] + actor["trust_delta"], 0, 100),
            "defensiveness": clamp_int(state["defensiveness"] + actor["defensiveness_delta"], 0, 100),
        }
    status = status_for(new_score)

    pace, temperature = voice_params(difficulty, actor["emotion"], new_state)
    counterpart_audio, audio_mime, voice_provider = await speak(
        actor["response"], brief["counterpart"], session["language"], actor["emotion"], pace, temperature,
    )

    turn_number = sum(1 for turn in conversation if turn["role"] == "user") + 1
    conversation.append({
        "role": "user", "text": user_text, "turn_number": turn_number, "coach": coach,
        "judged_by": "jev" if judgement else "actor", "timestamp": now_iso(),
    })
    conversation.append({
        "role": "counterpart", "text": actor["response"], "emotion": actor["emotion"],
        "score_delta": receptiveness_delta,
        "state": {**new_state, "receptiveness": new_score}, "timestamp": now_iso(),
    })
    skill_scores = skill_averages(conversation, dimensions)

    updates = {
        "current_score": new_score,
        "status": status,
        "conversation": conversation,
        "counterpart_state": new_state,
        "skill_scores": skill_scores,
    }
    db_update_session(session_id, updates)
    if status != "ongoing":
        # Stats are recorded exactly once: here when the conversation resolves itself,
        # or in /end when the user quits.
        db_record_stats({**session, **updates}, turn_number)

    return RespondResponse(
        user_text=user_text,
        counterpart_text=actor["response"],
        counterpart_audio=counterpart_audio,
        score_delta=receptiveness_delta,
        current_score=new_score,
        emotion=actor["emotion"],
        status=status,
        turn_number=turn_number,
        coach=CoachNote(**coach) if coach else None,
        skill_scores=skill_scores,
        counterpart_state=new_state,
        judged_by="jev" if judgement else "actor",
        audio_mime=audio_mime,
        voice_provider=voice_provider,
        stt_provider=stt_provider,
    )


async def start_from_brief(brief: dict, difficulty: str, language: str, previous_session_id: Optional[str] = None) -> SessionStartResponse:
    diff = DIFFICULTY_CONFIG[difficulty]
    counterpart = brief["counterpart"]
    conversation_type = brief["conversation_type"]

    # Built briefs are English; say the opening line in the session language (Mayura).
    opening = brief["opening_line"]
    if brief["kind"] != "classic" and language != "en-IN":
        try:
            opening = await sarvam_translate(
                opening, language, speaker_gender="Male" if counterpart["gender"] == "male" else "Female",
            )
        except Exception as e:  # English opening is an acceptable fallback
            log.warning("Opening-line translation failed; using English: %s", e)

    opening_emotion = "angry" if brief["kind"] == "classic" else DEFAULT_EMOTION
    opening_audio, audio_mime, voice_provider = await speak(
        opening, counterpart, language, opening_emotion, diff["tts_pace"], diff["tts_temperature"],
    )

    state = initial_state(difficulty)
    session_id = str(uuid.uuid4())
    db_create_session({
        "id": session_id,
        "persona_id": brief.get("persona_id"),
        "scenario_id": brief.get("preset_id") or "custom",
        "difficulty": difficulty,
        "language": language,
        "current_score": diff["starting_score"],
        "status": "ongoing",
        "conversation": [{
            "role": "counterpart", "text": opening, "emotion": opening_emotion,
            "score_delta": 0, "state": {**state, "receptiveness": diff["starting_score"]}, "timestamp": now_iso(),
        }],
        "system_prompt": build_actor_prompt(brief, difficulty, language),
        "brief": brief,
        "conversation_type": conversation_type,
        "counterpart_state": state,
        "skill_scores": {},
        "previous_session_id": previous_session_id,
    })

    return SessionStartResponse(
        session_id=session_id,
        opening_message=opening,
        opening_audio=opening_audio,
        initial_score=diff["starting_score"],
        kind=brief["kind"],
        counterpart_name=counterpart["name"],
        counterpart_role=counterpart["role"],
        counterpart_emoji=brief.get("emoji") or "🗣️",
        scenario_title=brief.get("title") or "Your conversation",
        difficulty_name=diff["name"],
        conversation_type=conversation_type,
        meter_label=RUBRICS[conversation_type]["meter_label"],
        dimensions=dimension_list(conversation_type),
        goal=brief.get("user_goal") or "",
        counterpart_state=state,
        audio_mime=audio_mime,
        voice_provider=voice_provider,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "supabase": db.supabase is not None,
        "storage": db.storage_mode(),
        "judge": "jev" if judge_enabled() else "actor",
        "tts": TTS_PROVIDER,
        "stt": STT_PROVIDER,
        "tts_model": ELEVENLABS_TTS_MODEL if TTS_PROVIDER == "elevenlabs" else "bulbul:v3",
    }


@app.get("/api/catalog")
async def get_catalog():
    """Everything the setup screen needs in one call."""
    return {
        "presets": [
            {
                "id": preset["id"], "title": preset["title"], "emoji": preset["emoji"],
                "description": preset["description"], "conversation_type": preset["conversation_type"],
                "intake": preset_intake(preset["id"]),
            }
            for preset in PRESETS.values()
        ],
        "personas": [
            {"id": p["id"], "name": p["name"], "title": p["title"], "emoji": p["emoji"], "description": p["description"]}
            for p in PERSONAS.values()
        ],
        "scenarios": [
            {"id": s["id"], "title": s["title"], "emoji": s["emoji"], "description": s["description"]}
            for s in SCENARIOS.values()
        ],
        "temperaments": [
            {"id": key, "name": DIFFICULTY_CONFIG[key]["name"], "description": DIFFICULTY_CONFIG[key]["description"],
             "starting_score": DIFFICULTY_CONFIG[key]["starting_score"]}
            for key in TEMPERAMENT_IDS
        ],
        "difficulties": [
            {"id": key, "name": DIFFICULTY_CONFIG[key]["name"], "description": DIFFICULTY_CONFIG[key]["description"],
             "starting_score": DIFFICULTY_CONFIG[key]["starting_score"]}
            for key in CLASSIC_DIFFICULTY_IDS
        ],
        "languages": LANGUAGES,
        "accents": ACCENTS,
        "rubrics": {
            key: {"name": rubric["name"], "meter_label": rubric["meter_label"], "dimensions": dimension_list(key)}
            for key, rubric in RUBRICS.items()
        },
        "judge": "jev" if judge_enabled() else "actor",
    }


@app.get("/api/personas")
async def get_personas():
    return {"personas": (await get_catalog())["personas"]}


@app.get("/api/scenarios")
async def get_scenarios():
    return {"scenarios": (await get_catalog())["scenarios"]}


@app.get("/api/difficulties")
async def get_difficulties():
    catalog = await get_catalog()
    return {"difficulties": catalog["difficulties"] + catalog["temperaments"]}


@app.get("/api/leaderboard")
async def get_leaderboard():
    return {"leaderboard": db_leaderboard()}


@app.post("/api/scenario/build", response_model=ScenarioBuildResponse)
async def build_scenario(req: ScenarioBuildRequest):
    """Turn an intake into a counterpart brief. Presets with untouched intake skip the LLM.
    Sarvam-M writes the brief; Jev (when configured) classifies safety and conversation type in parallel."""
    if req.preset_id and req.preset_id not in PRESETS:
        raise HTTPException(400, f"Unknown preset: {req.preset_id}")
    intake = normalized_intake(req.intake.model_dump()) if req.intake else None

    if req.preset_id and (intake is None or intake == normalized_intake(preset_intake(req.preset_id))):
        return ScenarioBuildResponse(brief=preset_brief(req.preset_id), built_by="preset", judged_by="preset")
    if intake is None:
        raise HTTPException(400, "Provide a preset_id or an intake")

    intake_text = " ".join([*intake["counterpart"].values(), intake["user_goal"], intake["user_fears"], intake["history"]])
    category = screen_intake_text(intake_text)
    if category:
        return ScenarioBuildResponse(safety=safety_payload(category), built_by="screen", judged_by="screen")
    if not (intake["user_goal"] or intake["counterpart"]["role"] or intake["history"]):
        raise HTTPException(400, "Tell us at least who the other person is and what you need from them")

    preset = PRESETS.get(req.preset_id) if req.preset_id else None
    raw, verdict = await asyncio.gather(
        sarvam_llm(build_brief_messages(intake, preset), temperature=0.8, max_tokens=1024),
        judge_intake(intake) if judge_enabled() else _none(),
        return_exceptions=True,
    )
    if isinstance(raw, BaseException):
        log.warning("Scenario build failed: %s", raw)
        raise HTTPException(502, "Could not build the scenario. Try again in a moment.")
    if isinstance(verdict, BaseException):
        log.warning("Jev intake judgement failed; using the builder's own classification: %s", verdict)
        verdict = None
    judged_by = "jev" if verdict else "llm"

    default_type = preset["conversation_type"] if preset else guess_conversation_type(intake_text)
    brief = parse_brief(raw, intake, valid_types=set(RUBRICS), default_type=default_type)
    if brief is None:
        raise HTTPException(502, "The scenario builder returned something unusable. Try again, or simplify the intake.")

    safety_category = (verdict or {}).get("safety_category") or brief["safety_category"]
    if safety_category:
        return ScenarioBuildResponse(safety=safety_payload(safety_category), built_by="llm", judged_by=judged_by)

    brief["kind"] = "preset" if preset else "custom"
    if preset:
        brief["preset_id"] = preset["id"]
        brief["emoji"] = preset["emoji"]
        brief["conversation_type"] = preset["conversation_type"]  # editing a preset doesn't change what it is
    elif verdict and verdict.get("conversation_type"):
        brief["conversation_type"] = verdict["conversation_type"]
    brief["counterpart"]["voice_id"] = pick_voice(brief["counterpart"]["name"], brief["counterpart"]["gender"])
    brief.pop("safety_category", None)
    return ScenarioBuildResponse(brief=brief, built_by="llm", judged_by=judged_by)


@app.post("/api/session/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest):
    if req.difficulty not in DIFFICULTY_CONFIG:
        raise HTTPException(400, f"Unknown difficulty: {req.difficulty}")
    if req.language not in LANGUAGE_IDS:
        raise HTTPException(400, f"Unsupported language: {req.language}")

    if req.brief is not None:
        kind = req.brief.get("kind")
        if kind == "classic":
            persona_id, scenario_id = req.brief.get("persona_id"), req.brief.get("preset_id")
            if persona_id not in PERSONAS or scenario_id not in SCENARIOS:
                raise HTTPException(400, "Unknown classic persona or scenario")
            brief = classic_brief(persona_id, scenario_id)
        else:
            brief = brief_from_data(req.brief, intake={}, valid_types=set(RUBRICS),
                                    default_type="feedback", kind=kind or "custom")
            if brief is None:
                raise HTTPException(400, "Brief is missing a counterpart or an opening line")
            brief.pop("safety_category", None)
    elif req.persona_id and req.scenario_id:
        if req.persona_id not in PERSONAS:
            raise HTTPException(400, f"Unknown persona: {req.persona_id}")
        if req.scenario_id not in SCENARIOS:
            raise HTTPException(400, f"Unknown scenario: {req.scenario_id}")
        brief = classic_brief(req.persona_id, req.scenario_id)
    else:
        raise HTTPException(400, "Provide a brief, or persona_id and scenario_id")

    if req.previous_session_id and not db_get_session(req.previous_session_id):
        req.previous_session_id = None
    return await start_from_brief(brief, req.difficulty, req.language, req.previous_session_id)


@app.get("/api/session/{session_id}", response_model=SessionSnapshot)
async def get_session(session_id: str):
    return snapshot(get_session_or_404(session_id))


@app.post("/api/session/{session_id}/respond", response_model=RespondResponse)
async def respond_voice(session_id: str, audio: UploadFile = File(...)):
    """Voice input → STT → judge → actor + coach → TTS."""
    session = get_session_or_404(session_id)
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) < 500:
        raise HTTPException(400, "Audio too short. Hold the mic for at least a second.")
    try:
        user_text, stt_provider = await transcribe(audio_bytes, session["language"], audio.content_type or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except httpx.HTTPStatusError as e:
        detail = "Speech recognition failed."
        if e.response is not None:
            try:
                err = e.response.json()
                detail = err.get("error", {}).get("message", detail) or str(err)
            except Exception:
                detail = e.response.text or str(e) or detail
        raise HTTPException(502, detail)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Speech recognition unreachable: {e}")
    if not user_text.strip():
        user_text = "(silence)"
    return await process_user_message(session_id, user_text, stt_provider=stt_provider)


@app.post("/api/session/{session_id}/respond-text", response_model=RespondResponse)
async def respond_text(session_id: str, text: str = Form(...)):
    """Text input fallback."""
    return await process_user_message(session_id, text)


@app.post("/api/session/{session_id}/rewind", response_model=SessionSnapshot)
async def rewind_session(session_id: str, req: RewindRequest):
    """Drop everything from user turn N onward and reopen the session there."""
    session = get_session_or_404(session_id)
    conversation = session["conversation"]
    user_indexes = [index for index, turn in enumerate(conversation) if turn["role"] == "user"]
    if req.turn_number < 1 or req.turn_number > len(user_indexes):
        raise HTTPException(400, f"turn_number must be between 1 and {len(user_indexes)}")

    kept = conversation[:user_indexes[req.turn_number - 1]]
    score, state = state_at(kept, session["difficulty"])
    dimensions = list(RUBRICS[session_brief(session)["conversation_type"]]["dimensions"])
    updates = {
        "conversation": kept, "current_score": score, "status": "ongoing",
        "counterpart_state": state, "skill_scores": skill_averages(kept, dimensions),
    }
    db_update_session(session_id, updates)
    return snapshot({**session, **updates})


@app.post("/api/session/{session_id}/restart", response_model=SessionStartResponse)
async def restart_session(session_id: str):
    """Run the same scenario again; the new session remembers this one for score comparison."""
    session = get_session_or_404(session_id)
    if session["status"] == "ongoing":
        db_update_session(session_id, {"status": "quit"})
    return await start_from_brief(session_brief(session), session["difficulty"], session["language"], previous_session_id=session_id)


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    if not db_delete_session(session_id):
        raise HTTPException(404, "Session not found")
    return {"deleted": True}


@app.post("/api/session/{session_id}/end", response_model=SessionEndResponse)
async def end_session_endpoint(session_id: str):
    session = get_session_or_404(session_id)
    quitting = session["status"] == "ongoing"
    if quitting:
        db_update_session(session_id, {"status": "quit"})
        session["status"] = "quit"

    brief = session_brief(session)
    conversation_type = brief["conversation_type"]
    dimensions = list(RUBRICS[conversation_type]["dimensions"])
    conversation = session["conversation"]
    user_turns = [turn for turn in conversation if turn["role"] == "user"]
    scored_turns = [
        turn for index, turn in enumerate(conversation)
        if turn["role"] == "counterpart" and "score_delta" in turn and index > 0 and conversation[index - 1]["role"] == "user"
    ]

    best_resp = worst_resp = None
    if scored_turns:
        best = max(scored_turns, key=lambda turn: turn.get("score_delta", 0))
        worst = min(scored_turns, key=lambda turn: turn.get("score_delta", 0))
        best_resp = conversation[conversation.index(best) - 1]["text"]
        worst_resp = conversation[conversation.index(worst) - 1]["text"]

    score = session["current_score"]
    skill_scores = session.get("skill_scores") or skill_averages(conversation, dimensions)

    try:
        tips_raw = await sarvam_llm(
            build_debrief_messages(brief, [turn["text"] for turn in user_turns], skill_scores, score),
            temperature=0.5,
        )
        tips = parse_tips(tips_raw)
    except Exception as e:
        log.warning("Debrief tips failed; using defaults: %s", e)
        tips = [
            "Acknowledge their position before explaining yours",
            "Be specific about what you want and what you'll do, not just how you feel",
            "When they push back, answer the objection instead of repeating yourself",
        ]

    previous_score = None
    if session.get("previous_session_id"):
        previous = db_get_session(session["previous_session_id"])
        if previous:
            previous_score = previous["current_score"]

    if quitting:
        db_record_stats(session, len(user_turns))

    return SessionEndResponse(
        final_score=score,
        verdict=verdict_for(score, brief["kind"]),
        total_turns=len(user_turns),
        best_response=best_resp,
        worst_response=worst_resp,
        tips=tips[:3],
        status=session["status"],
        kind=brief["kind"],
        conversation_type=conversation_type,
        goal=brief.get("user_goal") or "",
        meter_label=RUBRICS[conversation_type]["meter_label"],
        dimensions=dimension_list(conversation_type),
        skill_scores=skill_scores,
        transcript=conversation,
        reveal={
            "hidden_motivations": brief.get("hidden_motivations", []),
            "curveballs": brief.get("curveballs", []),
        },
        previous_score=previous_score,
        counterpart_name=brief["counterpart"]["name"],
    )
