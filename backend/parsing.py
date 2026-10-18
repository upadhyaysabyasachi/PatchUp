"""Turn LLM output and client payloads into validated dicts.

The actor/coach/brief parsers never raise on bad LLM output: they return a safe
fallback (actor), None (coach, brief), or raise ValueError only where the caller
explicitly expects it (tips).
"""
import json
import re
from typing import Optional

from content import ACCENT_IDS, DEFAULT_ACCENT, VOICES, pick_voice


def _fix_json_quirks(text: str) -> str:
    """Fix common LLM JSON quirks that break json.loads (e.g. "score": +12)."""
    return re.sub(
        r'"(?:\\.|[^"\\])*"|(:\s*)\+(\d)',
        lambda match: match.group(1) + match.group(2) if match.group(1) else match.group(0),
        text,
    )


def parse_json_payload(raw: str):
    """Decode an object or array, including fenced or prose-wrapped JSON."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Decode from the first container boundary so trailing prose is harmless.
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if starts:
            candidate = text[min(starts):]
            try:
                return json.JSONDecoder().raw_decode(candidate)[0]
            except json.JSONDecodeError:
                return json.JSONDecoder().raw_decode(_fix_json_quirks(candidate))[0]
        raise


def parse_object(raw: str) -> Optional[dict]:
    try:
        parsed = parse_json_payload(raw)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def clamp_int(value, lo: int, hi: int, default: int = 0) -> int:
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError):
        return default
    return max(lo, min(hi, number))


def clean_str(value, limit: Optional[int] = None) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    return text[:limit] if limit else text


def str_list(value, max_items: int, limit: int = 300) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [clean_str(item, limit) for item in value]
    return [item for item in items if item][:max_items]


# ─── Actor ───────────────────────────────────────────────────────────────────

def parse_actor(raw: str, valid_emotions, default_emotion: str) -> dict:
    """One counterpart turn. Accepts legacy `score_delta` for sessions started by the old prompt."""
    data = parse_object(raw)
    if data is None:
        return {
            "response": raw.strip()[:200] or "...",
            "emotion": default_emotion,
            "receptiveness_delta": 0,
            "trust_delta": 0,
            "defensiveness_delta": 0,
        }
    emotion = data.get("emotion")
    if not isinstance(emotion, str) or emotion not in valid_emotions:
        emotion = default_emotion
    receptiveness = data.get("receptiveness_delta", data.get("score_delta", 0))
    return {
        "response": clean_str(data.get("response"), 1000) or "...",
        "emotion": emotion,
        "receptiveness_delta": clamp_int(receptiveness, -25, 25),
        "trust_delta": clamp_int(data.get("trust_delta", 0), -25, 25),
        "defensiveness_delta": clamp_int(data.get("defensiveness_delta", 0), -25, 25),
    }


# ─── Coach ───────────────────────────────────────────────────────────────────

def parse_coach(raw: str, dimensions) -> Optional[dict]:
    """Per-turn rubric scores plus a note and a stronger rephrase. None if unusable."""
    data = parse_object(raw)
    if data is None:
        return None
    scores_raw = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    scores = {}
    for dim in dimensions:
        if dim in scores_raw:
            value = clamp_int(scores_raw[dim], 0, 10, default=-1)
            if value >= 0:
                scores[dim] = value
    note = clean_str(data.get("note"), 300) or ""
    stronger = clean_str(data.get("stronger"), 600) or ""
    if not scores and not note and not stronger:
        return None
    return {"scores": scores, "note": note, "stronger": stronger}


# ─── Debrief tips ────────────────────────────────────────────────────────────

def parse_tips(raw: str) -> list[str]:
    tips = parse_json_payload(raw)
    if not isinstance(tips, list) or len(tips) < 3 or not all(
        isinstance(tip, str) and tip.strip() for tip in tips
    ):
        raise ValueError("Expected at least three non-empty tips")
    return [tip.strip() for tip in tips[:3]]


# ─── Scenario brief ──────────────────────────────────────────────────────────

SAFETY_CATEGORIES = ("self_harm", "abuse")
BRIEF_KINDS = ("preset", "custom", "classic")


def _counterpart_from(data: dict, fallback: dict) -> dict:
    gender = fallback.get("gender") if fallback.get("gender") in ("male", "female") else data.get("gender")
    if gender not in ("male", "female"):
        gender = "female"
    name = clean_str(data.get("name"), 60) or clean_str(fallback.get("name"), 60) or "Them"
    # The user's accent choice wins over anything the LLM wrote; both must be a known id.
    accent = next(
        (value for value in (fallback.get("accent"), data.get("accent")) if value in ACCENT_IDS),
        DEFAULT_ACCENT,
    )
    voice = data.get("voice_id")
    all_voices = VOICES["male"] + VOICES["female"]
    return {
        "name": name,
        "role": clean_str(data.get("role"), 120) or clean_str(fallback.get("role"), 120) or "The other person",
        "gender": gender,
        "accent": accent,
        "relationship": clean_str(data.get("relationship"), 400) or clean_str(fallback.get("relationship"), 400) or "",
        "style": clean_str(data.get("style"), 800) or clean_str(fallback.get("style"), 800) or "",
        "voice_id": voice if isinstance(voice, str) and voice in all_voices else pick_voice(name, gender),
    }


def brief_from_data(data: dict, intake: dict, valid_types, default_type: str, kind: str = "custom") -> Optional[dict]:
    """Validate a brief-shaped dict (from the LLM or from a client) and fill gaps from the intake."""
    if not isinstance(data, dict):
        return None
    opening = clean_str(data.get("opening_line"), 500)
    if not opening:
        return None
    counterpart_raw = data.get("counterpart") if isinstance(data.get("counterpart"), dict) else {}
    intake_counterpart = intake.get("counterpart") if isinstance(intake.get("counterpart"), dict) else {}
    conversation_type = data.get("conversation_type")
    if conversation_type not in valid_types:
        conversation_type = default_type
    safety = data.get("safety_category")
    return {
        "kind": kind if kind in BRIEF_KINDS else "custom",
        "preset_id": clean_str(data.get("preset_id"), 40) or clean_str(intake.get("preset_id"), 40),
        "persona_id": clean_str(data.get("persona_id"), 40),
        "title": clean_str(data.get("title"), 60) or "Your conversation",
        "emoji": clean_str(data.get("emoji"), 8) or "🗣️",
        "description": clean_str(data.get("description"), 300) or "",
        "conversation_type": conversation_type,
        "counterpart": _counterpart_from(counterpart_raw, intake_counterpart),
        "user_goal": clean_str(data.get("user_goal"), 400) or clean_str(intake.get("user_goal"), 400) or "",
        "user_fears": clean_str(data.get("user_fears"), 400) or clean_str(intake.get("user_fears"), 400) or "",
        "history": clean_str(data.get("history"), 800) or clean_str(intake.get("history"), 800) or "",
        "hidden_motivations": str_list(data.get("hidden_motivations"), 3),
        "curveballs": str_list(data.get("curveballs"), 2),
        "opening_line": opening,
        "safety_category": safety if safety in SAFETY_CATEGORIES else None,
    }


def parse_brief(raw: str, intake: dict, valid_types, default_type: str) -> Optional[dict]:
    data = parse_object(raw)
    if data is None:
        return None
    return brief_from_data(data, intake, valid_types, default_type, kind="custom")
