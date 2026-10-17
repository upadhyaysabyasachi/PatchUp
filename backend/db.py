"""Session persistence: Supabase when configured, in-memory otherwise.

A Supabase error opens a circuit breaker for SUPABASE_RETRY_SECONDS; during that
window everything goes to memory, then we try Supabase again. Sessions created
while the breaker is open live in memory and are always read from there first.
"""
import os
import time
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_RETRY_SECONDS = 60

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected")
else:
    print("⚠️  Supabase not configured — using in-memory storage")

memory_sessions: dict = {}
_supabase_failed_at: Optional[float] = None

SESSION_COLUMNS = (
    "id", "persona_id", "scenario_id", "difficulty", "language", "current_score", "status",
    "conversation", "system_prompt", "brief", "conversation_type", "counterpart_state",
    "skill_scores", "previous_session_id",
)


def db_ready() -> bool:
    """True when we should talk to Supabase right now."""
    global _supabase_failed_at
    if supabase is None:
        return False
    if _supabase_failed_at is None:
        return True
    if time.monotonic() - _supabase_failed_at < SUPABASE_RETRY_SECONDS:
        return False
    _supabase_failed_at = None  # half-open: try again
    return True


def _db_failed(error: Exception) -> None:
    global _supabase_failed_at
    _supabase_failed_at = time.monotonic()
    print(f"⚠️  Supabase error (using in-memory storage for {SUPABASE_RETRY_SECONDS}s): {error}")


def normalize_session(session: Optional[dict]) -> Optional[dict]:
    """Read rows written by older backends: legacy role names, missing rehearsal columns."""
    if session is None:
        return None
    roles = {"boyfriend": "user", "girlfriend": "counterpart"}
    normalized = {
        "brief": None, "conversation_type": None, "counterpart_state": None,
        "previous_session_id": None, **session,
        "conversation": [
            {**turn, "role": roles.get(turn.get("role"), turn.get("role"))}
            for turn in (session.get("conversation") or [])
        ],
    }
    if not isinstance(normalized.get("skill_scores"), dict):
        normalized["skill_scores"] = {}
    return normalized


def db_create_session(session_data: dict) -> dict:
    if db_ready():
        try:
            supabase.table("sessions").insert({k: session_data.get(k) for k in SESSION_COLUMNS}).execute()
            return session_data
        except Exception as e:
            _db_failed(e)
    memory_sessions[session_data["id"]] = session_data
    return session_data


def db_get_session(session_id: str) -> Optional[dict]:
    if session_id in memory_sessions:
        return normalize_session(memory_sessions[session_id])
    if db_ready():
        try:
            result = supabase.table("sessions").select("*").eq("id", session_id).execute()
            return normalize_session(result.data[0]) if result.data else None
        except Exception as e:
            _db_failed(e)
    return None


def db_update_session(session_id: str, updates: dict) -> None:
    if session_id in memory_sessions:
        memory_sessions[session_id].update(updates)
        return
    if db_ready():
        try:
            supabase.table("sessions").update(updates).eq("id", session_id).execute()
        except Exception as e:
            _db_failed(e)


def db_delete_session(session_id: str) -> bool:
    found = memory_sessions.pop(session_id, None) is not None
    if db_ready():
        try:
            result = supabase.table("sessions").delete().eq("id", session_id).execute()
            found = found or bool(result.data)
        except Exception as e:
            _db_failed(e)
    return found


def db_record_stats(session: dict, total_turns: int) -> None:
    """Aggregate row for the leaderboard. No transcript, no PII."""
    if not db_ready():
        return
    try:
        supabase.table("game_stats").insert({
            "session_id": session["id"],
            "persona_id": session.get("persona_id"),
            "scenario_id": session.get("scenario_id"),
            "difficulty": session["difficulty"],
            "final_score": session["current_score"],
            "status": session["status"],
            "total_turns": total_turns,
            "conversation_type": session.get("conversation_type"),
            "skill_scores": session.get("skill_scores") or {},
        }).execute()
    except Exception as e:
        _db_failed(e)


def db_leaderboard(limit: int = 10) -> list:
    if not db_ready():
        return []
    try:
        result = supabase.table("game_stats").select("*") \
            .eq("status", "patched_up").order("final_score", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        _db_failed(e)
        return []


def storage_mode() -> str:
    return "supabase" if db_ready() else "memory"
