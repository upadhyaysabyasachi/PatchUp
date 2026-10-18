"""ElevenLabs speech: text-to-speech (Eleven v3 by default) and speech-to-text (Scribe).

Primary voice provider when ELEVENLABS_API_KEY is set; main.py falls back to Sarvam
on any failure here. Nothing in this module catches errors on purpose: the caller
decides what to do when ElevenLabs is unavailable.
"""
import asyncio
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from content import DEFAULT_ACCENT, VOICES

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io").rstrip("/")
ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_v3")
ELEVENLABS_STT_MODEL = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2")
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
ELEVENLABS_AUDIO_MIME = "audio/mpeg" if ELEVENLABS_OUTPUT_FORMAT.startswith("mp3") else "audio/wav"

log = logging.getLogger("patchup")

# BCP-47 (what the UI uses) → ISO-639-1 (what ElevenLabs takes).
ISO_639_1 = {
    "hi-IN": "hi", "en-IN": "en", "ta-IN": "ta", "te-IN": "te", "bn-IN": "bn",
    "kn-IN": "kn", "ml-IN": "ml", "mr-IN": "mr", "gu-IN": "gu",
}
# Languages the non-v3 TTS models can speak, among the ones the UI offers.
V2_FAMILY_LANGUAGES = {"en", "hi", "ta"}

# Eleven v3 audio tags, by counterpart emotion. Empty = no tag.
EMOTION_TAGS = {
    "angry": "[angry]",
    "cold": "[coldly]",
    "sarcastic": "[sarcastic]",
    "softening": "[softly]",
    "happy": "[happy]",
    "crying": "[crying]",
    "explosive": "[shouting]",
    "neutral": "",
    "warm": "[warmly]",
    "anxious": "[nervously]",
    "firm": "[firmly]",
    "defensive": "[defensive]",
}

# Premade voices that exist on every ElevenLabs account; used only if /v1/voices is unreachable.
DEFAULT_VOICE_IDS = {
    "female": ["21m00Tcm4TlvDq8ikWAM", "EXAVITQu4vr4xnSDxMaL", "XB0fDUnXU5powFXDhCwa", "XrExE9yKIg1WjnnlVkGX"],
    "male": ["pNInz6obpgDQGcFmaJgB", "JBFqnCBsd6RMkjVDRZzb", "TX3LPaxmHKxFdv7VOQHJ", "onwK4e9ZLuTAKqWW03F9"],
}

_voice_cache: Optional[list] = None
_library_cache: dict[tuple[str, str], str] = {}  # (gender, accent) → voice id added from the Voice Library
_library_lock = asyncio.Lock()


def elevenlabs_enabled() -> bool:
    return bool(ELEVENLABS_API_KEY)


def is_v3(model: str) -> bool:
    return model.startswith("eleven_v3")


def supports_language(model: str, language: str) -> bool:
    """v3 covers every language the UI offers; the v2 family only a few."""
    if is_v3(model):
        return True
    return ISO_639_1.get(language, "") in V2_FAMILY_LANGUAGES


def _headers(json_body: bool = True) -> dict:
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


# ─── Voices ──────────────────────────────────────────────────────────────────

def _env_voice_ids(gender: str) -> list[str]:
    raw = os.getenv(f"ELEVENLABS_VOICE_IDS_{gender.upper()}", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


async def get_voices() -> list:
    """The account's voices, fetched once per process. Raises if the request fails."""
    global _voice_cache
    if _voice_cache is None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ELEVENLABS_BASE_URL}/v1/voices", headers=_headers(json_body=False))
            resp.raise_for_status()
            _voice_cache = resp.json().get("voices", [])
    return _voice_cache


def _label(voice: dict, key: str) -> str:
    return str((voice.get("labels") or {}).get(key, "")).lower()


def voice_pool(voices: list, gender: str, accent: str = "any") -> list[str]:
    """Account voice ids for the gender. If any carry the wanted accent, only those are returned."""
    wanted = "male" if gender == "male" else "female"
    matching = [voice for voice in voices if _label(voice, "gender") == wanted and voice.get("voice_id")]
    if accent and accent != "any":
        with_accent = [v["voice_id"] for v in matching if accent in _label(v, "accent")]
        if with_accent:
            return with_accent
    return [v["voice_id"] for v in matching]


def choose_voice(name: str, pool: list[str]) -> str:
    """Deterministic pick so a counterpart keeps the same voice across turns and runs."""
    seed = sum(ord(ch) for ch in (name or "").lower())
    return pool[seed % len(pool)]


async def search_library(gender: str, accent: str, page_size: int = 10) -> list:
    """Voice Library entries for the gender + accent, most-used first."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{ELEVENLABS_BASE_URL}/v1/shared-voices",
            headers=_headers(json_body=False),
            params={"gender": gender, "accent": accent, "page_size": page_size, "sort": "usage_character_count_1y"},
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])


async def add_library_voice(public_owner_id: str, voice_id: str, new_name: str) -> str:
    """Add a shared voice to the account; returns the id it gets in this account."""
    global _voice_cache
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE_URL}/v1/voices/add/{public_owner_id}/{voice_id}",
            headers=_headers(),
            json={"new_name": new_name},
        )
        resp.raise_for_status()
    _voice_cache = None  # the account's voice list changed
    return resp.json()["voice_id"]


def pick_library_candidate(entries: list) -> Optional[dict]:
    """Prefer voices free plans may use; skip 'famous' (celebrity) voices."""
    usable = [e for e in entries if e.get("category") != "famous" and e.get("voice_id") and e.get("public_owner_id")]
    free = [e for e in usable if e.get("free_users_allowed")]
    return (free or usable or [None])[0]


async def library_voice(gender: str, accent: str) -> Optional[str]:
    """A voice with this accent from the Voice Library, added to the account on first use."""
    key = (gender, accent)
    if key in _library_cache:
        return _library_cache[key]
    async with _library_lock:
        if key in _library_cache:
            return _library_cache[key]
        candidate = pick_library_candidate(await search_library(gender, accent))
        if candidate is None:
            return None
        voice_id = await add_library_voice(
            candidate["public_owner_id"], candidate["voice_id"],
            new_name=f"PatchUp {accent} {gender} ({candidate.get('name', 'voice')})",
        )
        _library_cache[key] = voice_id
        log.info("Added Voice Library voice %r for %s/%s", candidate.get("name"), gender, accent)
        return voice_id


async def pick_elevenlabs_voice(name: str, gender: str, accent: str = DEFAULT_ACCENT) -> str:
    """Env override → account voice with the accent → Voice Library (added to the account) →
    any account voice of the gender → premade defaults."""
    gender = "male" if gender == "male" else "female"
    accent = (accent or DEFAULT_ACCENT).lower()
    pool = _env_voice_ids(gender)
    if pool:
        return choose_voice(name, pool)

    gender_pool: list[str] = []
    try:
        voices = await get_voices()
        pool = voice_pool(voices, gender, accent)
        gender_pool = voice_pool(voices, gender, "any")
        if pool and pool != gender_pool:
            return choose_voice(name, pool)  # the account already has voices with this accent
    except Exception as e:
        log.warning("Could not list ElevenLabs voices: %s", e)

    if accent != "any":
        try:
            voice_id = await library_voice(gender, accent)
            if voice_id:
                return voice_id
        except Exception as e:
            log.warning("Voice Library lookup for %s/%s failed; using a %s voice without that accent: %s", gender, accent, gender, e)

    return choose_voice(name, gender_pool or DEFAULT_VOICE_IDS[gender])


# ─── Text-to-speech ──────────────────────────────────────────────────────────

def tts_text(model: str, emotion: str, text: str) -> str:
    """v3 reads bracketed audio tags as delivery direction; other models would speak them."""
    tag = EMOTION_TAGS.get(emotion, "") if is_v3(model) else ""
    return f"{tag} {text}".strip() if tag else text


def voice_settings(model: str, emotion: str, pace: float, temperature: float) -> dict:
    """Map the game's pace/temperature onto the model's knobs.

    v3 only honours stability, at three levels (0 creative, 0.5 natural, 1 robust); the
    emotion goes in as an audio tag instead. v2-family models take continuous settings.
    """
    if is_v3(model):
        stability = 0.0 if temperature >= 0.75 else 1.0 if temperature <= 0.45 else 0.5
        return {"stability": stability, "similarity_boost": 0.75}
    return {
        "stability": round(max(0.1, min(0.9, 1 - temperature * 0.8)), 2),
        "similarity_boost": 0.75,
        "style": round(max(0.0, min(0.6, temperature - 0.4)), 2),
        "speed": round(max(0.7, min(1.2, pace)), 2),
        "use_speaker_boost": True,
    }


async def elevenlabs_tts(
    text: str,
    voice_id: str,
    language: str,
    emotion: str = "neutral",
    pace: float = 1.0,
    temperature: float = 0.6,
    model: Optional[str] = None,
) -> bytes:
    """Synthesise with ElevenLabs. Returns encoded audio bytes (ELEVENLABS_AUDIO_MIME)."""
    if not (ELEVENLABS_API_KEY and text and text.strip()):
        raise ValueError("ELEVENLABS_API_KEY and non-empty text required for TTS")
    model = model or ELEVENLABS_TTS_MODEL
    payload = {
        "text": tts_text(model, emotion, text.strip()[:4000]),
        "model_id": model,
        "voice_settings": voice_settings(model, emotion, pace, temperature),
    }
    # language_code is honoured by flash/turbo models only; multilingual_v2 rejects it, v3 ignores it.
    if "flash" in model or "turbo" in model:
        payload["language_code"] = ISO_639_1.get(language, "en")
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE_URL}/v1/text-to-speech/{voice_id}",
            params={"output_format": ELEVENLABS_OUTPUT_FORMAT},
            headers=_headers(),
            json=payload,
        )
        if resp.status_code != 200:
            log.warning("ElevenLabs TTS error %s: %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()
        return resp.content


# ─── Speech-to-text ──────────────────────────────────────────────────────────

async def elevenlabs_stt(audio_bytes: bytes, language: str = "hi-IN", content_type: Optional[str] = None) -> str:
    """Transcribe with Scribe. The language is a hint; Scribe detects it otherwise."""
    if not audio_bytes or len(audio_bytes) < 500:
        raise ValueError("Audio too short. Hold the mic for at least a second.")
    mime = (content_type or "audio/wav").split(";")[0].strip() or "audio/wav"
    filename = "audio.webm" if "webm" in mime else "audio.wav"
    data = {"model_id": ELEVENLABS_STT_MODEL, "tag_audio_events": "false", "diarize": "false"}
    iso = ISO_639_1.get(language)
    if iso:
        data["language_code"] = iso
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE_URL}/v1/speech-to-text",
            headers=_headers(json_body=False),
            files={"file": (filename, audio_bytes, mime)},
            data=data,
        )
        if resp.status_code != 200:
            log.warning("ElevenLabs STT error %s: %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()
        return (resp.json().get("text") or "").strip()


__all__ = [
    "ELEVENLABS_AUDIO_MIME", "ELEVENLABS_TTS_MODEL", "elevenlabs_enabled", "elevenlabs_stt",
    "elevenlabs_tts", "pick_elevenlabs_voice", "supports_language", "VOICES",
]
