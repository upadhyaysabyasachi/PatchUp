const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 90000; // STT + LLM + TTS can be slow

// ─── Types ───────────────────────────────────────────────────────────────────

export type ConversationType = "negotiation" | "feedback" | "emotional_repair" | "difficult_news";
export type SessionStatus = "ongoing" | "patched_up" | "blocked" | "quit";
export type BriefKind = "preset" | "custom" | "classic";

export interface Dimension { id: string; label: string; description: string; }
export interface IntakeCounterpart {
  name: string; role: string; gender: "male" | "female"; relationship: string; style: string;
}
export interface Intake {
  counterpart: IntakeCounterpart; user_goal: string; user_fears: string; history: string;
}
export const EMPTY_INTAKE: Intake = {
  counterpart: { name: "", role: "", gender: "female", relationship: "", style: "" },
  user_goal: "", user_fears: "", history: "",
};

export interface Preset {
  id: string; title: string; emoji: string; description: string;
  conversation_type: ConversationType; intake: Intake;
}
export interface Persona { id: string; name: string; title: string; emoji: string; description: string; }
export interface Scenario { id: string; title: string; emoji: string; description: string; }
export interface LevelOption { id: string; name: string; description: string; starting_score: number; }
export interface Language { id: string; label: string; }
export interface Rubric { name: string; meter_label: string; dimensions: Dimension[]; }
export interface Catalog {
  presets: Preset[]; personas: Persona[]; scenarios: Scenario[];
  temperaments: LevelOption[]; difficulties: LevelOption[]; languages: Language[];
  rubrics: Record<ConversationType, Rubric>;
  judge?: "jev" | "actor";
}

export interface Brief {
  kind: BriefKind; preset_id?: string | null; persona_id?: string | null;
  title: string; emoji: string; description: string; conversation_type: ConversationType;
  counterpart: IntakeCounterpart & { voice_id: string };
  user_goal: string; user_fears: string; history: string;
  hidden_motivations: string[]; curveballs: string[]; opening_line: string;
}
export interface SafetyNotice {
  flagged: true; category: string; title: string; message: string;
  resources: { name: string; contact: string }[];
}
export interface ScenarioBuildResponse { brief: Brief | null; safety: SafetyNotice | null; built_by: string; }

export interface CounterpartState { trust: number; defensiveness: number; }
export interface CoachNote { scores: Record<string, number>; note: string; stronger: string; }

export interface SessionStartResponse {
  session_id: string; opening_message: string; opening_audio: string; initial_score: number;
  kind: BriefKind; counterpart_name: string; counterpart_role: string; counterpart_emoji: string;
  scenario_title: string; difficulty_name: string; conversation_type: ConversationType;
  meter_label: string; dimensions: Dimension[]; goal: string; counterpart_state: CounterpartState;
  audio_mime?: string; voice_provider?: string;
}
export interface RespondResponse {
  user_text: string; counterpart_text: string; counterpart_audio: string;
  score_delta: number; current_score: number; emotion: string;
  status: SessionStatus; turn_number: number;
  coach: CoachNote | null; skill_scores: Record<string, number>; counterpart_state: CounterpartState;
  judged_by?: "jev" | "actor";
  audio_mime?: string; voice_provider?: string; stt_provider?: string | null;
}
export interface Turn {
  role: "user" | "counterpart"; text: string; emotion?: string; score_delta?: number;
  turn_number?: number; coach?: CoachNote | null;
  state?: CounterpartState & { receptiveness: number }; timestamp?: string;
}
export interface SessionSnapshot {
  session_id: string; status: SessionStatus; current_score: number;
  counterpart_state: CounterpartState; skill_scores: Record<string, number>;
  conversation: Turn[]; next_turn_number: number;
}
export interface SessionEndResponse {
  final_score: number; verdict: string; total_turns: number;
  best_response: string | null; worst_response: string | null; tips: string[];
  status: SessionStatus; kind: BriefKind; conversation_type: ConversationType; goal: string;
  meter_label: string; dimensions: Dimension[]; skill_scores: Record<string, number>;
  transcript: Turn[]; reveal: { hidden_motivations: string[]; curveballs: string[] };
  previous_score: number | null; counterpart_name: string;
}

export type StartParams = { difficulty: string; language: string; previous_session_id?: string } & (
  | { brief: Brief }
  | { persona_id: string; scenario_id: string }
);

// ─── Transport ───────────────────────────────────────────────────────────────

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = API_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
    if (!res.ok) {
      let msg = `${init.method || "GET"} ${path} failed: ${res.status}`;
      try {
        const err = await res.json() as { detail?: unknown };
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch { /* non-JSON error body */ }
      throw new Error(msg);
    }
    return await res.json() as T;
  } catch (e) {
    if (e instanceof Error) {
      if (e.name === "AbortError") throw new Error("Request took too long. Try again or use text.");
      if (e.message === "Failed to fetch" || e.cause?.toString?.().includes("fetch"))
        throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

// Accept either backend version while independent deployments roll out.
function normalizeResponse(data: RespondResponse & { girlfriend_text?: string; girlfriend_audio?: string }): RespondResponse {
  return {
    ...data,
    counterpart_text: data.counterpart_text ?? data.girlfriend_text ?? "",
    counterpart_audio: data.counterpart_audio ?? data.girlfriend_audio ?? "",
    coach: data.coach ?? null,
    skill_scores: data.skill_scores ?? {},
    counterpart_state: data.counterpart_state ?? { trust: 50, defensiveness: 50 },
  };
}

// ─── API ─────────────────────────────────────────────────────────────────────

// Long timeout: a free-tier backend can take up to a minute to wake from idle.
export const getCatalog = () => request<Catalog>("/api/catalog", {}, 90000);

export const buildScenario = (params: { preset_id?: string; intake?: Intake }) =>
  request<ScenarioBuildResponse>("/api/scenario/build", json(params));

export const startSession = (params: StartParams) =>
  request<SessionStartResponse>("/api/session/start", json(params));

export async function sendVoiceResponse(sessionId: string, audioBlob: Blob): Promise<RespondResponse> {
  const formData = new FormData();
  const ext = audioBlob.type.includes("webm") ? "webm" : "wav";
  formData.append("audio", audioBlob, `recording.${ext}`);
  return normalizeResponse(await request(`/api/session/${sessionId}/respond`, { method: "POST", body: formData }));
}

export async function sendTextResponse(sessionId: string, text: string): Promise<RespondResponse> {
  const formData = new FormData();
  formData.append("text", text);
  return normalizeResponse(await request(`/api/session/${sessionId}/respond-text`, { method: "POST", body: formData }));
}

export const getSession = (sessionId: string) => request<SessionSnapshot>(`/api/session/${sessionId}`, {}, 15000);

export const rewindSession = (sessionId: string, turnNumber: number) =>
  request<SessionSnapshot>(`/api/session/${sessionId}/rewind`, json({ turn_number: turnNumber }), 15000);

export const restartSession = (sessionId: string) =>
  request<SessionStartResponse>(`/api/session/${sessionId}/restart`, { method: "POST" });

export const endSession = (sessionId: string) =>
  request<SessionEndResponse>(`/api/session/${sessionId}/end`, { method: "POST" });

export const deleteSession = (sessionId: string) =>
  request<{ deleted: boolean }>(`/api/session/${sessionId}`, { method: "DELETE" }, 15000);

// mime defaults to WAV (Sarvam); ElevenLabs returns MP3 and the backend says so in audio_mime.
export function playBase64Audio(base64Audio: string, mime = "audio/wav"): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const bytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: mime });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = reject;
      audio.play().catch(reject);
    } catch (e) { reject(e); }
  });
}

// ─── Display helpers ─────────────────────────────────────────────────────────

export const isSessionError = (msg: string) =>
  msg.includes("404") || msg.toLowerCase().includes("session not found");

export function averageSkill(scores: Record<string, number>): number | null {
  const values = Object.values(scores);
  return values.length ? Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10 : null;
}
