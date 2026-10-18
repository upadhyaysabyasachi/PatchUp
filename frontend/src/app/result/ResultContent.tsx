"use client";
import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { endSession, restartSession, deleteSession } from "@/lib/api";
import type { SessionEndResponse, Turn } from "@/lib/api";
import SkillMeter from "@/components/SkillMeter";
import { EMOTION_LABELS } from "@/components/PatchMeter";

function verdictFor(score: number, classic: boolean) {
  if (classic) {
    return score >= 90 ? { emoji: "🎉", title: "PATCHED UP!", color: "text-green-400", border: "border-green-400/20" }
      : score >= 70 ? { emoji: "😊", title: "Almost There!", color: "text-amber-400", border: "border-amber-400/20" }
      : score >= 40 ? { emoji: "😐", title: "Still Naraaz", color: "text-orange-400", border: "border-orange-400/20" }
      : score >= 20 ? { emoji: "😤", title: "Made It Worse", color: "text-red-400", border: "border-red-400/20" }
      : { emoji: "💔", title: "BLOCKED", color: "text-red-500", border: "border-red-500/20" };
  }
  return score >= 90 ? { emoji: "🎯", title: "You got there", color: "text-green-400", border: "border-green-400/20" }
    : score >= 70 ? { emoji: "🙂", title: "Close", color: "text-amber-400", border: "border-amber-400/20" }
    : score >= 40 ? { emoji: "😐", title: "Stalemate", color: "text-orange-400", border: "border-orange-400/20" }
    : score >= 20 ? { emoji: "😬", title: "Lost ground", color: "text-red-400", border: "border-red-400/20" }
    : { emoji: "🚪", title: "They walked away", color: "text-red-500", border: "border-red-500/20" };
}

function TranscriptTurn({ turn, counterpart }: { turn: Turn; counterpart: string }) {
  if (turn.role === "counterpart") {
    const emo = turn.emotion ? EMOTION_LABELS[turn.emotion] : null;
    return (
      <div className="pl-3 border-l-2 border-patch-border">
        <div className="text-[10px] text-patch-glow/50 uppercase tracking-wider">{counterpart}{emo && <span className="normal-case text-patch-soft/30"> · {emo.label.toLowerCase()}</span>}
          {typeof turn.score_delta === "number" && turn.score_delta !== 0 && (
            <span className={`ml-2 font-mono ${turn.score_delta > 0 ? "text-green-400" : "text-red-400"}`}>{turn.score_delta > 0 ? "+" : ""}{turn.score_delta}</span>
          )}
        </div>
        <p className="text-sm text-patch-soft/70 mt-0.5">{turn.text}</p>
      </div>
    );
  }
  return (
    <div className="pl-3 border-l-2 border-patch-accent/40">
      <div className="text-[10px] text-patch-accent/70 uppercase tracking-wider">You{turn.turn_number ? ` · turn ${turn.turn_number}` : ""}</div>
      <p className="text-sm text-patch-soft mt-0.5">{turn.text}</p>
      {turn.coach && (
        <div className="mt-1.5 bg-patch-card/60 border border-patch-border rounded-lg px-3 py-2 space-y-1">
          <div className="flex flex-wrap gap-x-3">
            {Object.entries(turn.coach.scores).map(([dim, v]) => (
              <span key={dim} className="text-[10px] text-patch-soft/50 capitalize">{dim.replace(/_/g, " ")} <span className={`font-mono ${v >= 7 ? "text-green-400" : v >= 4 ? "text-amber-400" : "text-red-400"}`}>{v}</span></span>
            ))}
          </div>
          {turn.coach.note && <p className="text-xs text-patch-soft/70 italic">{turn.coach.note}</p>}
          {turn.coach.stronger && <p className="text-xs text-patch-soft"><span className="text-patch-glow/60">Stronger:</span> &ldquo;{turn.coach.stronger}&rdquo;</p>}
        </div>
      )}
    </div>
  );
}

export default function ResultContent() {
  const router = useRouter();
  const sessionId = useSearchParams().get("id");
  const [result, setResult] = useState<SessionEndResponse | null>(null);
  const [local, setLocal] = useState<{ status: string; score: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTranscript, setShowTranscript] = useState(false);
  const [busy, setBusy] = useState<"" | "restart" | "delete">("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const s = sessionStorage.getItem("patchup_result");
    if (s) setLocal(JSON.parse(s));
    if (sessionId) endSession(sessionId).then(setResult).catch((e) => setError(e instanceof Error ? e.message : "Could not load the debrief")).finally(() => setLoading(false));
    else setLoading(false);
  }, [sessionId]);

  const runAgain = async () => {
    if (!sessionId) return;
    setBusy("restart"); setError(null);
    try {
      const session = await restartSession(sessionId);
      sessionStorage.setItem("patchup_session", JSON.stringify(session));
      router.push(`/chat?id=${session.session_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not restart.");
      setBusy("");
    }
  };

  const remove = async () => {
    if (!sessionId || !confirm("Delete this session and its transcript? This can't be undone.")) return;
    setBusy("delete"); setError(null);
    try {
      await deleteSession(sessionId);
      sessionStorage.removeItem("patchup_session");
      sessionStorage.removeItem("patchup_result");
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete.");
      setBusy("");
    }
  };

  const score = result?.final_score ?? local?.score ?? 0;
  const classic = result ? result.kind === "classic" : true;
  const v = verdictFor(score, classic);
  const name = result?.counterpart_name ?? "They";
  const userTurns = result?.transcript.filter(t => t.role === "user").length ?? 0;

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" /></div>;

  return (
    <main className="min-h-screen px-4 py-8 max-w-lg mx-auto">
      <div className="text-center mb-8 animate-slide-up">
        <div className="text-7xl mb-4">{v.emoji}</div>
        <h1 className={`font-display text-4xl font-bold ${v.color}`}>{v.title}</h1>
        <p className="text-sm text-patch-soft/50 mt-2">{result?.verdict}</p>
        {result?.goal && !classic && <p className="text-xs text-patch-soft/40 mt-2 italic">Goal: {result.goal}</p>}
      </div>

      <div className={`glass-card rounded-2xl p-6 mb-4 text-center ${v.border} animate-slide-up`} style={{ animationDelay: "0.1s" }}>
        <div className="text-xs text-patch-soft/40 uppercase tracking-wider mb-2">{result ? `${result.counterpart_name}'s ${result.meter_label.toLowerCase()}` : "Final score"}</div>
        <div className={`font-display text-6xl font-bold ${v.color}`}>{score}%</div>
        {result && (
          <div className="text-sm text-patch-soft/50 mt-2 flex items-center justify-center gap-3">
            <span>{result.total_turns} turn{result.total_turns !== 1 ? "s" : ""}</span>
            {typeof result.previous_score === "number" && (
              <span className="font-mono text-xs">
                last run {result.previous_score}% <span className={score > result.previous_score ? "text-green-400" : score < result.previous_score ? "text-red-400" : "text-patch-soft/40"}>
                  {score > result.previous_score ? "▲" : score < result.previous_score ? "▼" : "="} {Math.abs(score - result.previous_score)}
                </span>
              </span>
            )}
          </div>
        )}
      </div>

      {result && result.dimensions.length > 0 && (
        <div className="glass-card rounded-2xl p-5 mb-4 animate-slide-up border-patch-accent/30" style={{ animationDelay: "0.15s" }}>
          <h3 className="font-display text-sm text-patch-glow uppercase tracking-wider mb-1">🙂 You · how you communicated</h3>
          <p className="text-[11px] text-patch-soft/40 mb-3">The coach scored each of your messages 0–10 on these; this is your average.</p>
          {Object.keys(result.skill_scores).length ? (
            <SkillMeter dimensions={result.dimensions} scores={result.skill_scores} />
          ) : (
            <p className="text-xs text-patch-soft/40">No scored turns yet. Say something next time and the coach will grade it.</p>
          )}
        </div>
      )}

      {result && (result.reveal.hidden_motivations.length > 0 || result.reveal.curveballs.length > 0) && (
        <div className="glass-card rounded-2xl p-5 mb-4 animate-slide-up border-patch-glow/20" style={{ animationDelay: "0.2s" }}>
          <h3 className="font-display text-sm text-patch-soft/50 uppercase tracking-wider mb-3">🎭 What {name} wasn&apos;t saying</h3>
          <ul className="space-y-1.5 mb-3">
            {result.reveal.hidden_motivations.map((m, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-patch-soft/80"><span className="text-patch-glow/60 mt-0.5">•</span><span>{m}</span></li>
            ))}
          </ul>
          {result.reveal.curveballs.length > 0 && (
            <>
              <div className="text-[10px] text-patch-glow/60 uppercase tracking-wider mb-1.5">Curveballs in play</div>
              <ul className="space-y-1.5">
                {result.reveal.curveballs.map((c, i) => (
                  <li key={i} className="text-sm text-patch-soft/70 italic">&ldquo;{c}&rdquo;</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {result && (result.best_response || result.worst_response) && (
        <div className="space-y-3 mb-4 animate-slide-up" style={{ animationDelay: "0.25s" }}>
          {result.best_response && (
            <div className="glass-card rounded-xl p-4">
              <div className="text-[10px] text-green-400/60 uppercase tracking-wider mb-1">✅ Moved {name} most</div>
              <p className="text-sm text-patch-soft/80 italic">&quot;{result.best_response}&quot;</p>
            </div>
          )}
          {result.worst_response && result.worst_response !== result.best_response && (
            <div className="glass-card rounded-xl p-4">
              <div className="text-[10px] text-red-400/60 uppercase tracking-wider mb-1">❌ Cost you the most</div>
              <p className="text-sm text-patch-soft/80 italic">&quot;{result.worst_response}&quot;</p>
            </div>
          )}
        </div>
      )}

      {result?.tips && result.tips.length > 0 && (
        <div className="glass-card rounded-2xl p-5 mb-4 animate-slide-up" style={{ animationDelay: "0.3s" }}>
          <h3 className="font-display text-sm text-patch-soft/50 uppercase tracking-wider mb-3">💡 Next time</h3>
          <div className="space-y-2">
            {result.tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-patch-accent text-xs mt-1">•</span>
                <p className="text-sm text-patch-soft/70">{tip}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && userTurns > 0 && (
        <div className="glass-card rounded-2xl p-5 mb-6 animate-slide-up" style={{ animationDelay: "0.35s" }}>
          <button onClick={() => setShowTranscript(!showTranscript)} className="w-full flex items-center justify-between text-left">
            <h3 className="font-display text-sm text-patch-soft/50 uppercase tracking-wider">📝 Annotated transcript</h3>
            <span className="text-xs text-patch-soft/40">{userTurns} turn{userTurns !== 1 ? "s" : ""} {showTranscript ? "▴" : "▾"}</span>
          </button>
          {showTranscript && (
            <div className="mt-4 space-y-4">
              {result.transcript.map((t, i) => <TranscriptTurn key={i} turn={t} counterpart={name} />)}
            </div>
          )}
        </div>
      )}

      {error && <div className="mb-4 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">{error}</div>}

      <div className="space-y-3 animate-slide-up" style={{ animationDelay: "0.4s" }}>
        {result && (
          <button onClick={runAgain} disabled={!!busy} className="w-full py-4 bg-patch-accent rounded-2xl font-body font-semibold text-white text-lg hover:bg-patch-accent/90 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50">
            {busy === "restart" ? "Setting up…" : "Run it again 🔁"}
          </button>
        )}
        <button onClick={() => router.push("/setup")} className="w-full py-3 bg-patch-card border border-patch-border rounded-2xl font-body text-patch-soft/70 text-sm hover:border-patch-accent/30 transition-all">
          Different conversation
        </button>
        <div className="flex justify-between items-center pt-1">
          <button onClick={() => router.push("/")} className="text-xs text-patch-soft/40 hover:text-patch-soft/60">Home</button>
          {sessionId && (
            <button onClick={remove} disabled={!!busy} className="text-xs text-patch-soft/40 hover:text-red-400 disabled:opacity-50">
              {busy === "delete" ? "Deleting…" : "Delete my session data"}
            </button>
          )}
        </div>
      </div>

      <div className="text-center mt-8 animate-slide-up" style={{ animationDelay: "0.5s" }}>
        <div className="inline-block px-4 py-2 bg-patch-card border border-patch-border rounded-full">
          <span className="text-xs text-patch-soft/40">Share your score! 🩹 #TheMicIsYours @SarvamAI</span>
        </div>
      </div>
      <div className="text-center mt-6 text-[10px] text-patch-soft/20">Powered by Sarvam Bulbul V3 · Saarika · Sarvam 105b · Mayura 🇮🇳</div>
    </main>
  );
}
