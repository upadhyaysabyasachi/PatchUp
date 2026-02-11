const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 90000; // STT + LLM + TTS can be slow

export interface Persona {
  id: string; name: string; title: string; emoji: string; description: string;
}
export interface Scenario {
  id: string; title: string; emoji: string; description: string;
}
export interface SessionStartResponse {
  session_id: string; opening_message: string; opening_audio: string;
  initial_score: number; persona_name: string; scenario_title: string; difficulty_name: string;
}
export interface RespondResponse {
  user_text: string; girlfriend_text: string; girlfriend_audio: string;
  score_delta: number; current_score: number; emotion: string;
  status: "ongoing" | "patched_up" | "blocked"; turn_number: number;
}
export interface SessionEndResponse {
  final_score: number; verdict: string; total_turns: number;
  best_response: string | null; worst_response: string | null; tips: string[];
}

export async function startSession(params: {
  persona_id: string; scenario_id: string; difficulty: string; language: string;
}): Promise<SessionStartResponse> {
  const res = await fetch(`${API_URL}/api/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Start failed: ${res.status}`);
  return res.json();
}

export async function sendVoiceResponse(sessionId: string, audioBlob: Blob): Promise<RespondResponse> {
  const formData = new FormData();
  const ext = audioBlob.type.includes("webm") ? "webm" : "wav";
  formData.append("audio", audioBlob, `recording.${ext}`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}/api/session/${sessionId}/respond`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let msg = `Voice respond failed: ${res.status}`;
      try {
        const err = await res.json() as { detail?: string };
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch {
        // ignore
      }
      throw new Error(msg);
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof Error) {
      if (e.name === "AbortError") throw new Error("Request took too long. Try again or use text.");
      if (e.message === "Failed to fetch" || e.cause?.toString?.().includes("fetch"))
        throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
    }
    throw e;
  }
}

export async function sendTextResponse(sessionId: string, text: string): Promise<RespondResponse> {
  const formData = new FormData();
  formData.append("text", text);
  try {
    const res = await fetch(`${API_URL}/api/session/${sessionId}/respond-text`, {
      method: "POST", body: formData,
    });
    if (!res.ok) {
      let msg = `Text respond failed: ${res.status}`;
      try {
        const err = await res.json() as { detail?: string };
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch {
        // ignore
      }
      throw new Error(msg);
    }
    return res.json();
  } catch (e) {
    if (e instanceof Error && (e.message === "Failed to fetch" || e.cause?.toString?.().includes("fetch")))
      throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
    throw e;
  }
}

export async function endSession(sessionId: string): Promise<SessionEndResponse> {
  const res = await fetch(`${API_URL}/api/session/${sessionId}/end`, { method: "POST" });
  if (!res.ok) throw new Error(`End failed: ${res.status}`);
  return res.json();
}

export function playBase64Audio(base64Audio: string): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const bytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: "audio/wav" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = reject;
      audio.play().catch(reject);
    } catch (e) { reject(e); }
  });
}
