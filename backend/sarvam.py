"""Sarvam AI API helpers: Saarika (STT), Bulbul (TTS), Sarvam 105b (LLM), Mayura (Translate)."""
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"
# `sarvam-m` was retired. 105b-conversations is tuned for real-time dialogue (the actor);
# 105b for reasoning tasks (coach, scenario builder, debrief).
SARVAM_LLM_MODEL = os.getenv("SARVAM_LLM_MODEL", "sarvam-105b")
SARVAM_ACTOR_MODEL = os.getenv("SARVAM_ACTOR_MODEL", "sarvam-105b-conversations")

log = logging.getLogger("patchup")


def _headers(json_body: bool = True) -> dict:
    headers = {"api-subscription-key": SARVAM_API_KEY}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _error_message(resp: httpx.Response, default: str) -> str:
    try:
        err = resp.json()
        return err.get("error", {}).get("message", default) or str(err)
    except Exception:
        return resp.text or default


def _stt_file_tuple(content_type: Optional[str], audio_bytes: bytes) -> tuple[str, tuple]:
    """Return (form_key, file_tuple) for STT. Use simple MIME; Sarvam may reject audio/webm;codecs=opus."""
    if content_type and "webm" in content_type.lower():
        return "file", ("audio.webm", audio_bytes, "audio/webm")
    if content_type and content_type.strip():
        mime = content_type.split(";")[0].strip() or "audio/wav"
        return "file", ("audio.wav", audio_bytes, mime)
    return "file", ("audio.wav", audio_bytes, "audio/wav")


async def sarvam_stt(audio_bytes: bytes, language: str = "hi-IN", content_type: Optional[str] = None) -> str:
    """Speech-to-Text using Sarvam Saarika v2.5. Accepts WAV, WebM, and other formats."""
    if not audio_bytes or len(audio_bytes) < 500:
        raise ValueError("Audio too short. Hold the mic for at least a second.")
    key, file_tuple = _stt_file_tuple(content_type, audio_bytes)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers=_headers(json_body=False),
            files={key: file_tuple},
            data={"language_code": language, "model": "saarika:v2.5"},
        )
        if resp.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Sarvam STT {resp.status_code}: {_error_message(resp, resp.text)}",
                request=resp.request,
                response=resp,
            )
        return resp.json().get("transcript", "")


async def sarvam_tts(
    text: str,
    speaker: str = "priya",
    language: str = "hi-IN",
    pace: float = 1.0,
    temperature: float = 0.6,
) -> str:
    """Text-to-Speech using Sarvam Bulbul V3. Returns base64 audio."""
    if not (SARVAM_API_KEY and text and text.strip()):
        raise ValueError("SARVAM_API_KEY and non-empty text required for TTS")
    payload = {
        "text": text.strip()[:2500],  # bulbul:v3 max
        "target_language_code": language.strip(),
        "speaker": (speaker or "shubh").strip().lower(),
        "model": "bulbul:v3",
        "pace": max(0.5, min(2.0, float(pace))),
        "temperature": max(0.01, min(2.0, float(temperature))),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{SARVAM_BASE_URL}/text-to-speech", headers=_headers(), json=payload)
        if resp.status_code != 200:
            log.warning("Sarvam TTS error %s: %s", resp.status_code, _error_message(resp, resp.text))
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        return audios[0] if audios else ""


async def sarvam_llm(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 512,
    model: Optional[str] = None,
    reasoning: Optional[str] = None,
    json_mode: bool = True,
) -> str:
    """Chat completion on Sarvam's 105b models.

    `reasoning` is the API's reasoning_effort: None disables it (the default would otherwise be
    'medium', and reasoning tokens count against max_tokens). `json_mode` asks for a JSON object;
    every caller here parses JSON, so it's on by default.
    """
    payload = {
        "model": model or SARVAM_LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{SARVAM_BASE_URL}/v1/chat/completions", headers=_headers(), json=payload)
        if resp.status_code != 200:
            log.warning("Sarvam LLM error %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def sarvam_translate(
    text: str,
    target_language: str,
    source_language: str = "en-IN",
    speaker_gender: Optional[str] = None,
) -> str:
    """Translate with Mayura v1. Hinglish targets use code-mixed mode so the result sounds spoken, not formal."""
    if not text.strip() or target_language == source_language:
        return text
    payload = {
        "input": text.strip()[:1000],  # mayura:v1 max
        "source_language_code": source_language,
        "target_language_code": target_language,
        "mode": "code-mixed" if target_language == "hi-IN" else "modern-colloquial",
        "model": "mayura:v1",
    }
    if speaker_gender in ("Male", "Female"):
        payload["speaker_gender"] = speaker_gender
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(f"{SARVAM_BASE_URL}/translate", headers=_headers(), json=payload)
        if resp.status_code != 200:
            log.warning("Sarvam Translate error %s: %s", resp.status_code, _error_message(resp, resp.text))
        resp.raise_for_status()
        return resp.json().get("translated_text") or text
