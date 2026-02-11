import os
import json
import base64
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

try:
    from postgrest.exceptions import APIError as PostgrestAPIError
except ImportError:
    PostgrestAPIError = Exception  # noqa: A001

load_dotenv()

app = FastAPI(title="PatchUp API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───────────────────────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected")
else:
    print("⚠️  Supabase not configured — using in-memory storage")

# In-memory fallback when Supabase isn't configured or Supabase fails (e.g. invalid key)
memory_sessions: dict = {}
_supabase_failed = False  # set True on first Supabase error so we stop trying

# ─── Persona Definitions ─────────────────────────────────────────────────────
PERSONAS = {
    "priya": {
        "id": "priya",
        "name": "Priya",
        "title": "Bollywood Drama Queen",
        "emoji": "🎬",
        "description": "Over-the-top emotional, filmy dialogues, thinks her life is a Karan Johar movie",
        "voice_id": "Priya",
        "default_language": "hi-IN",
        "system_prompt": (
            "You are Priya, an extremely dramatic Indian girlfriend who treats every fight like a Bollywood movie scene. "
            "You use filmy dialogues, dramatic pauses, and emotional blackmail. You say things like 'Tum meri zindagi barbaad kar diya!', "
            "'Mujhe laga tha tum alag ho', 'Main apni maa se kya bolungi?'. You mix Hindi and English naturally. "
            "You are hurt but deep down you want him to fight for you. You love grand gestures and heartfelt apologies."
        ),
    },
    "neha": {
        "id": "neha",
        "name": "Neha",
        "title": "Silent Treatment Expert",
        "emoji": "🧊",
        "description": "One-word answers, long pauses, makes you wonder if she's even there",
        "voice_id": "Neha",
        "default_language": "en-IN",
        "system_prompt": (
            "You are Neha, a girlfriend who is a master of the silent treatment. You respond with extremely short, cold replies. "
            "Things like 'K.', 'Hmm.', 'Whatever.', 'Sure.', 'Fine.', 'I don't care.', 'Do what you want.'. "
            "You occasionally drop a devastating one-liner that cuts deep. You speak mostly in English with occasional Hindi. "
            "You make him feel the weight of silence. Only genuinely thoughtful and specific apologies crack your armor. "
            "Generic 'sorry' gets a 'K.' from you."
        ),
    },
    "ritu": {
        "id": "ritu",
        "name": "Ritu",
        "title": "The Logical Arguer",
        "emoji": "🧠",
        "description": "Builds a legal case against you, has receipts and timestamps for everything",
        "voice_id": "Ritu",
        "default_language": "en-IN",
        "system_prompt": (
            "You are Ritu, a sharp and logical girlfriend who argues like a lawyer. You remember exact dates, times, and quotes. "
            "You say things like 'On January 14th at 9:47 PM, you said and I quote...', 'This is the third time in two months', "
            "'Let me list the pattern I'm seeing here'. You mix English and Hindi. You are not emotional but coldly analytical. "
            "You deconstruct his excuses with logic. Only genuine accountability and a concrete plan to change impresses you."
        ),
    },
    "kavya": {
        "id": "kavya",
        "name": "Kavya",
        "title": "The Explosive One",
        "emoji": "🌪️",
        "description": "Zero to hundred real quick, rapid-fire accusations, full rage mode",
        "voice_id": "Kavya",
        "default_language": "hi-IN",
        "system_prompt": (
            "You are Kavya, an extremely passionate and explosive Indian girlfriend. You go from 0 to 100 instantly. "
            "You fire rapid accusations, bring up old fights, and escalate quickly. You speak mostly in Hindi with English mixed in. "
            "Things like 'Tumse baat hi nahi karni mujhe!', 'Tumhari himmat kaise hui?!', 'Sab yaad hai mujhe!'. "
            "You are loud, fast, and intense. But underneath all the anger is deep hurt. A sincere, calm, patient response "
            "that shows he truly understands why you're upset can break through — but it takes real effort."
        ),
    },
}

# ─── Scenario Definitions ────────────────────────────────────────────────────
SCENARIOS = {
    "anniversary": {
        "id": "anniversary",
        "title": "Forgot the Anniversary",
        "emoji": "💀",
        "description": "You completely forgot your anniversary. She planned the whole day. You didn't even wish her.",
        "opening_lines": {
            "priya": "Pata hai aaj kya din hai? Nahi pata na? Obviously nahi pata. Tumhe kab yaad rehta hai mera. Koi nahi, main toh aadat si ho gayi hai.",
            "neha": "Hey.",
            "ritu": "So. Today is February 10th. Does that date ring a bell? I'll give you 10 seconds.",
            "kavya": "TUMHE YAAD BHI HAI AAJ KYA DIN HAI?! Nahi yaad hoga, tum toh apne mein hi rehte ho!",
        },
        "context": "The boyfriend forgot their anniversary. The girlfriend had planned something special and waited all day.",
    },
    "ex_photo": {
        "id": "ex_photo",
        "title": "Caught Liking Ex's Photo",
        "emoji": "📱",
        "description": "She caught you liking your ex's vacation photo at 2 AM. Good luck.",
        "opening_lines": {
            "priya": "Ek baat batao... raat ke 2 baje tum Sneha ki photo like kar rahe the? SNEHA KI? Woh Sneha jiske baare mein tumne bola tha ki 'she means nothing to me'?",
            "neha": "Interesting photo Sneha posted, no? You seemed to think so at 2 AM.",
            "ritu": "I noticed something at 2:03 AM. Your Instagram activity shows you liked Sneha's Maldives photo. The same Sneha you told me on March 15th was 'just a friend from college'. Would you like to explain the timeline?",
            "kavya": "SNEHA KI PHOTO?! RAAT KE DO BAJE?! Tumhari himmat kaise hui! Main sab dekh liya hai, SCREENSHOTS HAI MERE PAAS!",
        },
        "context": "The boyfriend liked his ex-girlfriend Sneha's vacation photo on Instagram at 2 AM.",
    },
    "cooking": {
        "id": "cooking",
        "title": "Said Her Cooking Was 'Okay'",
        "emoji": "🍳",
        "description": "She spent 3 hours making your favorite dish. You said 'hmm, it's okay'. Fatal error.",
        "opening_lines": {
            "priya": "Teen ghante... TEEN GHANTE lagaye maine wo biryani banane mein. Aur tumne kya bola? 'Hmm okay hai.' OKAY HAI?!",
            "neha": "Cool. Next time I'll just order Swiggy.",
            "ritu": "Let me understand this. I spent 3 hours, used 14 ingredients, watched 3 YouTube tutorials, and your review was — 'hmm, it's okay'. That's 180 minutes of effort summarized in two words.",
            "kavya": "OKAY?! OKAY BOLA TUMNE?! TEEN GHANTE SE KHANA BANA RAHI THI MAIN! Aaj ke baad khud banao apna khana!",
        },
        "context": "The girlfriend spent 3 hours cooking his favorite biryani. He said 'hmm, it's okay' while scrolling his phone.",
    },
    "boys_trip": {
        "id": "boys_trip",
        "title": "Boys Trip Without Telling Her",
        "emoji": "✈️",
        "description": "You planned a Goa trip with the boys. She found out from someone else's Instagram story.",
        "opening_lines": {
            "priya": "Mujhe Rahul ki story se pata chala ki tum Goa ja rahe ho. RAHUL KI STORY SE. Main kya hoon tumhari zindagi mein?",
            "neha": "Saw Rahul's story. Goa looks fun. Have a good trip.",
            "ritu": "When exactly were you planning to tell me about the Goa trip? Before boarding? After landing? Or was I supposed to find out from Rahul's Instagram story?",
            "kavya": "GOA JA RAHE HO?! BINA BATAYE?! Mujhe Rahul ki story se pata chala — RAHUL KI STORY SE!",
        },
        "context": "The boyfriend planned a Goa trip with friends but didn't tell her. She found out from his friend's Instagram story.",
    },
    "late": {
        "id": "late",
        "title": "2 Hours Late, No Text",
        "emoji": "🕐",
        "description": "You were 2 hours late for dinner and didn't even text. She sat alone at the restaurant.",
        "opening_lines": {
            "priya": "Do ghante. Do ghante akeli baithi rahi main restaurant mein. Waiter ne teen baar pucha 'ma'am aur koi aa raha hai?'. Mujhe itna sharam aaya na...",
            "neha": "I already ate. Alone.",
            "ritu": "Our reservation was at 8 PM. You arrived at 10:07 PM. That's 2 hours and 7 minutes. I called you 4 times and sent 6 messages. Zero responses.",
            "kavya": "DO GHANTE! DO GHANTE WAIT KARWAYI TUMNE! EK TEXT NAHI KAR SAKTE THE?!",
        },
        "context": "The boyfriend was 2 hours late for a dinner reservation and didn't text or call.",
    },
    "gaming": {
        "id": "gaming",
        "title": "Chose Gaming Over Date Night",
        "emoji": "🎮",
        "description": "She planned date night. You said you'd come but started ranked matches instead.",
        "opening_lines": {
            "priya": "Main ready hokar baithi thi. Naya dress pehna tha. Makeup kiya tha. Aur tum? 'Baby bas ek aur match, 20 minute.' WOH 20 MINUTE 3 GHANTE HO GAYE!",
            "neha": "Your K/D ratio must be great tonight. Congrats.",
            "ritu": "Let me reconstruct the timeline. 7 PM: 'getting ready'. 7:30: 'one quick match'. 8:15: 'last one I promise'. 9:45: you're still playing. I have the WhatsApp timestamps.",
            "kavya": "GAMING?! GAMING ZYADA IMPORTANT HAI MUJHSE?! Maine itna plan kiya tha aur tumhe apna stupid game khelna tha!",
        },
        "context": "The girlfriend planned a date night. The boyfriend kept saying 'one more match' and never showed up.",
    },
}

# ─── Difficulty Config ────────────────────────────────────────────────────────
DIFFICULTY_CONFIG = {
    "easy": {
        "name": "Thoda Gussa",
        "starting_score": 50,
        "tts_pace": 0.9,
        "tts_temperature": 0.4,
        "prompt_modifier": (
            "Difficulty: EASY. You are annoyed but willing to listen. You give hints about what he should say. "
            "You soften relatively easily with a genuine apology. Score generously for good responses (+15 to +25). "
            "Only deduct heavily for truly dismissive responses."
        ),
    },
    "medium": {
        "name": "Full Naraaz",
        "starting_score": 30,
        "tts_pace": 1.0,
        "tts_temperature": 0.6,
        "prompt_modifier": (
            "Difficulty: MEDIUM. You are genuinely upset. Generic apologies barely register (+2 to +5). "
            "Only specific, thoughtful responses earn good scores (+10 to +20). Excuses get punished (-10 to -15)."
        ),
    },
    "hard": {
        "name": "Breakup Mode",
        "starting_score": 15,
        "tts_pace": 1.2,
        "tts_temperature": 0.8,
        "prompt_modifier": (
            "Difficulty: HARD. You are on the verge of ending things. One wrong word makes it worse. "
            "Only deeply genuine acknowledgments earn points (+5 to +15). Generic sorry = -5. Excuses = -15."
        ),
    },
    "nightmare": {
        "name": "Maa Ko Bata Dungi",
        "starting_score": 5,
        "tts_pace": 1.3,
        "tts_temperature": 0.9,
        "prompt_modifier": (
            "Difficulty: NIGHTMARE. You are FURIOUS. You threaten to involve family. You bring up things from years ago. "
            "Almost nothing works. Only extraordinary, deeply heartfelt responses earn points (+3 to +10). Score very harshly."
        ),
    },
}

# ─── Voice Emotion Mapping ───────────────────────────────────────────────────
EMOTION_VOICE_PARAMS = {
    "angry":     {"pace": 1.3,  "temperature": 0.9},
    "cold":      {"pace": 0.85, "temperature": 0.3},
    "sarcastic": {"pace": 1.0,  "temperature": 0.6},
    "softening": {"pace": 0.9,  "temperature": 0.5},
    "happy":     {"pace": 1.0,  "temperature": 0.5},
    "crying":    {"pace": 0.8,  "temperature": 0.7},
    "explosive": {"pace": 1.4,  "temperature": 0.95},
}


# ═══════════════════════════════════════════════════════════════════════════════
# SARVAM API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

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
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={key: file_tuple},
            data={"language_code": language, "model": "saarika:v2.5"},
        )
        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err = resp.json()
                err_msg = err.get("error", {}).get("message", err_msg) or str(err)
            except Exception:
                pass
            raise httpx.HTTPStatusError(
                f"Sarvam STT {resp.status_code}: {err_msg}",
                request=resp.request,
                response=resp,
            )
        return resp.json().get("transcript", "")


async def sarvam_tts(
    text: str,
    speaker: str = "Priya",
    language: str = "hi-IN",
    pace: float = 1.0,
    temperature: float = 0.6,
) -> str:
    """Text-to-Speech using Sarvam Bulbul V3. Returns base64 audio."""
    if not (SARVAM_API_KEY and text and text.strip()):
        raise ValueError("SARVAM_API_KEY and non-empty text required for TTS")
    text_clean = text.strip()[:2500]  # bulbul:v3 max
    payload = {
        "text": text_clean,
        "target_language_code": language.strip(),
        "speaker": (speaker or "Shubh").strip().lower(),
        "model": "bulbul:v3",
        "pace": max(0.5, min(2.0, float(pace))),
        "temperature": max(0.01, min(2.0, float(temperature))),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SARVAM_BASE_URL}/text-to-speech",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            try:
                err = resp.json()
                import logging
                logging.getLogger("patchup").warning("Sarvam TTS error: %s", err)
            except Exception:
                pass
        resp.raise_for_status()
        data = resp.json()
        audios = data.get("audios", [])
        return audios[0] if audios else ""


async def sarvam_llm(messages: list, temperature: float = 0.7) -> str:
    """Chat completion using Sarvam-M."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{SARVAM_BASE_URL}/v1/chat/completions",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": "sarvam-m",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 512,
            },
        )
        if resp.status_code != 200:
            print(f"Sarvam LLM error {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def parse_llm_json(raw: str) -> dict:
    """Robustly parse JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    # Fallback
    return {
        "response": raw[:200],
        "score_delta": 0,
        "emotion": "angry",
        "should_end": False,
        "end_reason": None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def db_create_session(session_data: dict) -> dict:
    """Insert a new session into Supabase (or memory fallback)."""
    global _supabase_failed
    if supabase and not _supabase_failed:
        try:
            result = supabase.table("sessions").insert({
                "id": session_data["id"],
                "persona_id": session_data["persona_id"],
                "scenario_id": session_data["scenario_id"],
                "difficulty": session_data["difficulty"],
                "language": session_data["language"],
                "current_score": session_data["current_score"],
                "status": "ongoing",
                "conversation": session_data["conversation"],
                "system_prompt": session_data["system_prompt"],
            }).execute()
            return result.data[0] if result.data else session_data
        except (PostgrestAPIError, Exception) as e:
            _supabase_failed = True
            print(f"⚠️  Supabase error (falling back to in-memory): {e}")
    memory_sessions[session_data["id"]] = session_data
    return session_data


def db_get_session(session_id: str) -> Optional[dict]:
    """Fetch a session."""
    global _supabase_failed
    if supabase and not _supabase_failed:
        try:
            result = supabase.table("sessions").select("*").eq("id", session_id).execute()
            return result.data[0] if result.data else None
        except (PostgrestAPIError, Exception) as e:
            _supabase_failed = True
            print(f"⚠️  Supabase error (falling back to in-memory): {e}")
    return memory_sessions.get(session_id)


def db_update_session(session_id: str, updates: dict):
    """Update session fields."""
    global _supabase_failed
    if supabase and not _supabase_failed:
        try:
            supabase.table("sessions").update(updates).eq("id", session_id).execute()
            return
        except (PostgrestAPIError, Exception) as e:
            _supabase_failed = True
            print(f"⚠️  Supabase error (falling back to in-memory): {e}")
    if session_id in memory_sessions:
        memory_sessions[session_id].update(updates)


def db_record_stats(session_id: str, persona_id: str, scenario_id: str, difficulty: str, final_score: int, status: str, total_turns: int):
    """Record game stats for leaderboard."""
    global _supabase_failed
    if supabase and not _supabase_failed:
        try:
            supabase.table("game_stats").insert({
                "session_id": session_id,
                "persona_id": persona_id,
                "scenario_id": scenario_id,
                "difficulty": difficulty,
                "final_score": final_score,
                "status": status,
                "total_turns": total_turns,
            }).execute()
        except (PostgrestAPIError, Exception) as e:
            _supabase_failed = True
            print(f"⚠️  Supabase error (falling back to in-memory): {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(persona_id: str, scenario_id: str, difficulty: str, language: str) -> str:
    persona = PERSONAS[persona_id]
    scenario = SCENARIOS[scenario_id]
    diff_config = DIFFICULTY_CONFIG[difficulty]

    return f"""You are playing the role of {persona['name']}, an angry Indian girlfriend in a voice conversation simulator called PatchUp.

CHARACTER:
{persona['system_prompt']}

SCENARIO:
{scenario['description']}
Context: {scenario['context']}

{diff_config['prompt_modifier']}

LANGUAGE:
- Primary: {language}
- Mix Hindi and English naturally (code-mixing) as real Indian couples speak
- Keep responses SHORT (1-3 sentences max) — this is voice, not text

CRITICAL — OUTPUT FORMAT:
Respond with ONLY a valid JSON object. No text before or after.
{{
    "response": "Your in-character dialogue here",
    "score_delta": <integer from -25 to 25>,
    "emotion": "<angry|cold|sarcastic|softening|happy|crying|explosive>",
    "should_end": <true|false>,
    "end_reason": "<patched_up|blocked|null>"
}}

SCORING:
- Genuine acknowledgment + specific details: +15 to +25
- Thoughtful, shows he understands her feelings: +10 to +20
- Simple sincere "I messed up": +5 to +10
- Generic "sorry babe": +1 to +3
- Deflecting / changing topic: -5 to -10
- Making excuses: -10 to -15
- Getting defensive: -15 to -20
- Dismissive or hurtful: -20 to -25

END CONDITIONS:
- Score ≥ 90 → should_end=true, end_reason="patched_up", emotion="happy"
- Score ≤ 0 → should_end=true, end_reason="blocked", emotion="angry"

Stay in character. React to what he actually says."""


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SessionStartRequest(BaseModel):
    persona_id: str
    scenario_id: str
    difficulty: str = "medium"
    language: str = "hi-IN"

class SessionStartResponse(BaseModel):
    session_id: str
    opening_message: str
    opening_audio: str
    initial_score: int
    persona_name: str
    scenario_title: str
    difficulty_name: str

class RespondResponse(BaseModel):
    user_text: str
    girlfriend_text: str
    girlfriend_audio: str
    score_delta: int
    current_score: int
    emotion: str
    status: str
    turn_number: int

class SessionEndResponse(BaseModel):
    final_score: int
    verdict: str
    total_turns: int
    best_response: Optional[str] = None
    worst_response: Optional[str] = None
    tips: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# CORE CONVERSATION LOGIC (shared by voice + text endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

async def process_user_message(session_id: str, user_text: str) -> RespondResponse:
    """Core logic: take user text, get LLM response, generate TTS, update score."""
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session["status"] != "ongoing":
        raise HTTPException(400, f"Session already ended: {session['status']}")

    persona = PERSONAS[session["persona_id"]]
    diff_config = DIFFICULTY_CONFIG[session["difficulty"]]
    conversation = session["conversation"]

    # Build LLM messages
    # Sarvam-M requires first non-system message to be "user", so fold the
    # girlfriend's opening line into the system prompt and start the
    # conversation history from the first boyfriend (user) message.
    opening_text = conversation[0]["text"] if conversation and conversation[0]["role"] == "girlfriend" else None
    system_content = session["system_prompt"]
    if opening_text:
        system_content += f"\n\nYou already said this opening line: \"{opening_text}\""
    llm_messages = [{"role": "system", "content": system_content}]
    for turn in conversation:
        if turn is conversation[0] and turn["role"] == "girlfriend":
            continue  # skip opening line, already in system prompt
        if turn["role"] == "girlfriend":
            llm_messages.append({"role": "assistant", "content": turn["text"]})
        else:
            llm_messages.append({"role": "user", "content": turn["text"]})
    llm_messages.append({
        "role": "user",
        "content": f"{user_text}\n\n[Current score: {session['current_score']}/100. Output ONLY valid JSON.]",
    })

    # Get LLM response
    raw = await sarvam_llm(llm_messages, temperature=0.7)
    parsed = parse_llm_json(raw)

    gf_text = parsed.get("response", "...")
    score_delta = max(-25, min(25, int(parsed.get("score_delta", 0))))
    emotion = parsed.get("emotion", "angry")
    should_end = parsed.get("should_end", False)
    end_reason = parsed.get("end_reason")

    # Update score
    new_score = max(0, min(100, session["current_score"] + score_delta))

    # Determine status
    if should_end and end_reason == "patched_up" or new_score >= 95:
        status = "patched_up"
    elif should_end and end_reason == "blocked" or new_score <= 0:
        status = "blocked"
    else:
        status = "ongoing"

    # TTS with emotion-based voice params
    emo_params = EMOTION_VOICE_PARAMS.get(emotion, {"pace": 1.0, "temperature": 0.6})
    final_pace = (diff_config["tts_pace"] + emo_params["pace"]) / 2
    final_temp = (diff_config["tts_temperature"] + emo_params["temperature"]) / 2

    gf_audio = await sarvam_tts(
        text=gf_text,
        speaker=persona["voice_id"],
        language=session["language"],
        pace=final_pace,
        temperature=final_temp,
    )

    # Update conversation history
    turn_number = len([t for t in conversation if t["role"] == "boyfriend"]) + 1
    conversation.append({"role": "boyfriend", "text": user_text, "timestamp": datetime.now(timezone.utc).isoformat()})
    conversation.append({
        "role": "girlfriend", "text": gf_text, "emotion": emotion,
        "score_delta": score_delta, "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Persist
    db_update_session(session_id, {
        "current_score": new_score,
        "status": status,
        "conversation": conversation,
    })

    return RespondResponse(
        user_text=user_text,
        girlfriend_text=gf_text,
        girlfriend_audio=gf_audio,
        score_delta=score_delta,
        current_score=new_score,
        emotion=emotion,
        status=status,
        turn_number=turn_number,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "supabase": supabase is not None}


@app.get("/api/personas")
async def get_personas():
    return {"personas": [
        {"id": p["id"], "name": p["name"], "title": p["title"], "emoji": p["emoji"], "description": p["description"]}
        for p in PERSONAS.values()
    ]}


@app.get("/api/scenarios")
async def get_scenarios():
    return {"scenarios": [
        {"id": s["id"], "title": s["title"], "emoji": s["emoji"], "description": s["description"]}
        for s in SCENARIOS.values()
    ]}


@app.get("/api/difficulties")
async def get_difficulties():
    return {"difficulties": [
        {"id": k, "name": v["name"], "starting_score": v["starting_score"]}
        for k, v in DIFFICULTY_CONFIG.items()
    ]}


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Top 10 patch-up scores."""
    global _supabase_failed
    if supabase and not _supabase_failed:
        try:
            result = supabase.table("game_stats") \
                .select("*") \
                .eq("status", "patched_up") \
                .order("final_score", desc=True) \
                .limit(10) \
                .execute()
            return {"leaderboard": result.data or []}
        except (PostgrestAPIError, Exception):
            _supabase_failed = True
    return {"leaderboard": []}


@app.post("/api/session/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest):
    if req.persona_id not in PERSONAS:
        raise HTTPException(400, f"Unknown persona: {req.persona_id}")
    if req.scenario_id not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario_id}")
    if req.difficulty not in DIFFICULTY_CONFIG:
        raise HTTPException(400, f"Unknown difficulty: {req.difficulty}")

    persona = PERSONAS[req.persona_id]
    scenario = SCENARIOS[req.scenario_id]
    diff = DIFFICULTY_CONFIG[req.difficulty]

    opening = scenario["opening_lines"].get(req.persona_id, list(scenario["opening_lines"].values())[0])

    # Generate opening audio
    try:
        opening_audio = await sarvam_tts(
            text=opening, speaker=persona["voice_id"],
            language=req.language, pace=diff["tts_pace"], temperature=diff["tts_temperature"],
        )
    except httpx.HTTPStatusError as e:
        detail = "Sarvam TTS failed."
        if e.response is not None:
            try:
                err = e.response.json()
                detail = err.get("error", {}).get("message", detail) or str(err)
            except Exception:
                detail = e.response.text or detail
        raise HTTPException(status_code=502, detail=detail)

    session_id = str(uuid.uuid4())
    session_data = {
        "id": session_id,
        "persona_id": req.persona_id,
        "scenario_id": req.scenario_id,
        "difficulty": req.difficulty,
        "language": req.language,
        "current_score": diff["starting_score"],
        "status": "ongoing",
        "conversation": [
            {"role": "girlfriend", "text": opening, "emotion": "angry", "score_delta": 0,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ],
        "system_prompt": build_system_prompt(req.persona_id, req.scenario_id, req.difficulty, req.language),
    }
    db_create_session(session_data)

    return SessionStartResponse(
        session_id=session_id, opening_message=opening, opening_audio=opening_audio,
        initial_score=diff["starting_score"], persona_name=persona["name"],
        scenario_title=scenario["title"], difficulty_name=diff["name"],
    )


@app.post("/api/session/{session_id}/respond", response_model=RespondResponse)
async def respond_voice(session_id: str, audio: UploadFile = File(...)):
    """Voice input → STT → LLM → TTS."""
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    audio_bytes = await audio.read()
    content_type = audio.content_type or ""
    try:
        user_text = await sarvam_stt(audio_bytes, language=session["language"], content_type=content_type)
    except ValueError as e:
        raise HTTPException(400, str(e))  # e.g. "Audio too short..."
    except httpx.HTTPStatusError as e:
        detail = "Speech recognition failed."
        if e.response is not None:
            try:
                err = e.response.json()
                detail = err.get("error", {}).get("message", detail) or str(err)
            except Exception:
                detail = e.response.text or str(e) or detail
        raise HTTPException(502, detail)
    if not user_text.strip():
        user_text = "(silence)"

    return await process_user_message(session_id, user_text)


@app.post("/api/session/{session_id}/respond-text", response_model=RespondResponse)
async def respond_text(session_id: str, text: str = Form(...)):
    """Text input fallback."""
    return await process_user_message(session_id, text)


@app.post("/api/session/{session_id}/end", response_model=SessionEndResponse)
async def end_session_endpoint(session_id: str):
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if session["status"] == "ongoing":
        db_update_session(session_id, {"status": "quit"})

    conversation = session["conversation"]
    bf_turns = [t for t in conversation if t["role"] == "boyfriend"]
    gf_turns = [t for t in conversation if t["role"] == "girlfriend" and "score_delta" in t]

    best_resp = worst_resp = None
    if gf_turns:
        best_gf = max(gf_turns, key=lambda t: t.get("score_delta", 0))
        worst_gf = min(gf_turns, key=lambda t: t.get("score_delta", 0))
        best_idx = conversation.index(best_gf)
        worst_idx = conversation.index(worst_gf)
        if best_idx > 0 and conversation[best_idx - 1]["role"] == "boyfriend":
            best_resp = conversation[best_idx - 1]["text"]
        if worst_idx > 0 and conversation[worst_idx - 1]["role"] == "boyfriend":
            worst_resp = conversation[worst_idx - 1]["text"]

    score = session["current_score"]
    if score >= 90: verdict = "🎉 PATCHED UP! She forgave you!"
    elif score >= 70: verdict = "😊 Almost there! She's softening up."
    elif score >= 40: verdict = "😐 Still naraaz. Better luck next time."
    elif score >= 20: verdict = "😤 You made it worse. Much worse."
    else: verdict = "💔 BLOCKED. She's done."

    # Generate tips
    try:
        tips_raw = await sarvam_llm([{"role": "user", "content": (
            f"A boyfriend tried to patch up after: {SCENARIOS[session['scenario_id']]['description']}. "
            f"His responses were: {[t['text'] for t in bf_turns]}. Score: {score}/100. "
            f"Give 3 short tips (one sentence each) on what he could do better. Reply as JSON array: [\"tip1\",\"tip2\",\"tip3\"]"
        )}], temperature=0.5)
        tips = json.loads(parse_llm_json(tips_raw).get("response", "[]")) if isinstance(parse_llm_json(tips_raw), dict) else json.loads(tips_raw.strip().strip("`").replace("json\n", "").strip())
        if not isinstance(tips, list):
            raise ValueError
    except Exception:
        tips = [
            "Acknowledge her feelings before explaining yourself",
            "Be specific about what you did wrong — not just 'sorry'",
            "Show a concrete plan for how you'll do better",
        ]

    # Record stats
    db_record_stats(session_id, session["persona_id"], session["scenario_id"],
                    session["difficulty"], score, session["status"], len(bf_turns))

    return SessionEndResponse(
        final_score=score, verdict=verdict, total_turns=len(bf_turns),
        best_response=best_resp, worst_response=worst_resp, tips=tips[:3],
    )
