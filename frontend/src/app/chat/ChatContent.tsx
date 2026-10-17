"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { sendVoiceResponse, sendTextResponse, playBase64Audio, rewindSession, isSessionError } from "@/lib/api";
import type { SessionStartResponse, RespondResponse, CoachNote, CounterpartState, SessionStatus, Turn } from "@/lib/api";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import PatchMeter from "@/components/PatchMeter";
import SkillMeter from "@/components/SkillMeter";
import MicButton from "@/components/MicButton";
import ChatBubble from "@/components/ChatBubble";

interface Msg {
  role: "counterpart" | "user"; text: string; emotion?: string; scoreDelta?: number;
  audio?: string; audioMime?: string; turnNumber?: number; coach?: CoachNote | null;
}

const fromTurn = (t: Turn): Msg => ({
  role: t.role, text: t.text, emotion: t.emotion, scoreDelta: t.score_delta,
  turnNumber: t.turn_number, coach: t.coach ?? null,
});

export default function ChatContent() {
  const router = useRouter();
  const sessionId = useSearchParams().get("id");
  const [session, setSession] = useState<SessionStartResponse | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [score, setScore] = useState(50);
  const [lastDelta, setLastDelta] = useState(0);
  const [emotion, setEmotion] = useState("neutral");
  const [status, setStatus] = useState<SessionStatus>("ongoing");
  const [skill, setSkill] = useState<Record<string, number>>({});
  const [cpState, setCpState] = useState<CounterpartState>({ trust: 50, defensiveness: 50 });
  const [processing, setProcessing] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [textIn, setTextIn] = useState("");
  const [textMode, setTextMode] = useState(false);
  const [turn, setTurn] = useState(0);
  const [judgedBy, setJudgedBy] = useState<string | null>(null);
  const [voiceProvider, setVoiceProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const autoStopRef = useRef<() => void>(() => {});
  const { isRecording, startRecording, stopRecording } = useAudioRecorder(() => autoStopRef.current());

  useEffect(() => {
    const s = sessionStorage.getItem("patchup_session");
    if (!s) { router.push("/setup"); return; }
    const p: SessionStartResponse = JSON.parse(s);
    if (p.session_id !== sessionId) { router.push("/setup"); return; }
    setSession(p); setScore(p.initial_score); setCpState(p.counterpart_state);
    setEmotion(p.kind === "classic" ? "angry" : "neutral");
    setMsgs([{ role: "counterpart", text: p.opening_message, emotion: p.kind === "classic" ? "angry" : "neutral", audio: p.opening_audio, audioMime: p.audio_mime }]);
    setVoiceProvider(p.voice_provider ?? null);
    if (p.opening_audio) {
      setPlaying(true);
      playBase64Audio(p.opening_audio, p.audio_mime).catch(() => {}).finally(() => setPlaying(false));
    }
  }, [router, sessionId]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, status]);

  const showError = (e: unknown, fallback: string) => {
    console.error(e);
    let msg = e instanceof Error ? e.message : fallback;
    if (isSessionError(msg)) msg = "Session expired or backend restarted. Go to Setup to start a new one.";
    setError(msg);
  };

  const handleResp = useCallback(async (d: RespondResponse) => {
    setMsgs(p => [...p, { role: "user", text: d.user_text, turnNumber: d.turn_number, coach: d.coach }]);
    await new Promise(r => setTimeout(r, 300));
    setMsgs(p => [...p, { role: "counterpart", text: d.counterpart_text, emotion: d.emotion, scoreDelta: d.score_delta, audio: d.counterpart_audio, audioMime: d.audio_mime }]);
    setScore(d.current_score); setLastDelta(d.score_delta); setEmotion(d.emotion); setStatus(d.status);
    setTurn(d.turn_number); setSkill(d.skill_scores); setCpState(d.counterpart_state); setJudgedBy(d.judged_by ?? null);
    setVoiceProvider(d.voice_provider ?? null);
    if (d.counterpart_audio) {
      setPlaying(true);
      try { await playBase64Audio(d.counterpart_audio, d.audio_mime); } catch {}
      setPlaying(false);
    }
  }, []);

  const sendRecording = useCallback(async () => {
    setProcessing(true);
    setError(null);
    try {
      const blob = await stopRecording();
      if (!sessionId) return;
      if (blob.size === 0) {
        setError("Recording was empty. Tap the mic and speak, then tap again to send.");
        return;
      }
      await handleResp(await sendVoiceResponse(sessionId, blob));
    } catch (e) {
      showError(e, "Could not send voice. Try \"Switch to Text\".");
    } finally {
      setProcessing(false);
    }
  }, [sessionId, stopRecording, handleResp]);

  // Keep ref in sync so the auto-stop timer can call sendRecording
  autoStopRef.current = sendRecording;

  const onMicTap = useCallback(async () => {
    if (processing || playing || status !== "ongoing") return;
    if (isRecording) {
      await sendRecording();
    } else {
      try { await startRecording(); } catch { setTextMode(true); }
    }
  }, [processing, playing, status, isRecording, sendRecording, startRecording]);

  const onTextSend = async () => {
    if (!textIn.trim() || !sessionId || processing || status !== "ongoing") return;
    const t = textIn.trim(); setTextIn("");
    setProcessing(true);
    setError(null);
    try {
      await handleResp(await sendTextResponse(sessionId, t));
    } catch (e) {
      showError(e, "Message could not be sent.");
    }
    setProcessing(false);
  };

  const onRetry = useCallback(async (turnNumber: number) => {
    if (!sessionId || processing || playing) return;
    setProcessing(true);
    setError(null);
    try {
      const snap = await rewindSession(sessionId, turnNumber);
      const opening = msgs[0]; // keep the opening audio; older counterpart turns lose theirs
      setMsgs(snap.conversation.map((t, i) => (i === 0 && opening ? { ...fromTurn(t), audio: opening.audio } : fromTurn(t))));
      setScore(snap.current_score); setStatus(snap.status); setSkill(snap.skill_scores);
      setCpState(snap.counterpart_state); setTurn(snap.next_turn_number - 1); setLastDelta(0);
      const lastCp = [...snap.conversation].reverse().find(t => t.role === "counterpart");
      setEmotion(lastCp?.emotion || "neutral");
    } catch (e) {
      showError(e, "Could not rewind.");
    }
    setProcessing(false);
  }, [sessionId, processing, playing, msgs]);

  const goToResult = () => {
    sessionStorage.setItem("patchup_result", JSON.stringify({ sessionId, status, score }));
    router.push(`/result?id=${sessionId}`);
  };

  if (!session) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" /></div>;

  const classic = session.kind === "classic";
  const ended = status !== "ongoing";
  const won = status === "patched_up";

  return (
    <main className="min-h-screen flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-patch-bg/90 backdrop-blur-xl border-b border-patch-border px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 shrink-0 rounded-full bg-patch-accent/20 border border-patch-accent/30 flex items-center justify-center text-sm">
              {session.counterpart_emoji}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-display font-semibold text-patch-soft truncate">
                {session.counterpart_name}
                <span className="font-body font-normal text-patch-soft/40"> · {session.counterpart_role}</span>
              </div>
              <div className="text-[10px] text-patch-soft/40 truncate">{session.scenario_title} · {session.difficulty_name}</div>
            </div>
          </div>
          <button onClick={goToResult} className="shrink-0 text-xs text-patch-soft/40 hover:text-red-400 px-3 py-1 border border-patch-border rounded-lg hover:border-red-400/30 transition-colors">
            {ended ? "Debrief →" : "End"}
          </button>
        </div>
        {session.goal && !classic && (
          <p className="text-[11px] text-patch-soft/50 mb-2 truncate" title={session.goal}>
            <span className="text-patch-glow/60">Your goal:</span> {session.goal}
          </p>
        )}
        <PatchMeter score={score} scoreDelta={lastDelta} emotion={emotion} label={session.meter_label} kind={session.kind} />
        <div className="mt-2.5 max-w-md mx-auto">
          <SkillMeter dimensions={session.dimensions} scores={skill} compact />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {msgs.map((m, i) => (
          <ChatBubble key={`${i}-${m.turnNumber ?? "c"}`} role={m.role} text={m.text} emotion={m.emotion} scoreDelta={m.scoreDelta} audio={m.audio} audioMime={m.audioMime}
            personaName={m.role === "counterpart" ? session.counterpart_name : undefined}
            coach={m.coach} turnNumber={m.turnNumber} onRetry={onRetry} canRetry={!processing && !playing} />
        ))}
        {ended && (
          <div className="text-center py-6 animate-slide-up space-y-3">
            <span className="text-4xl block">{won ? "🎉" : classic ? "💔" : "🚪"}</span>
            <span className={`font-display text-xl block ${won ? "text-green-400" : "text-red-400"}`}>
              {won ? (classic ? "PATCHED UP!" : "You got there") : (classic ? "BLOCKED" : `${session.counterpart_name} walked away`)}
            </span>
            <p className="text-sm text-patch-soft/50">
              {won ? (classic ? "She forgave you!" : `${session.counterpart_name} is on board.`) : (classic ? "She's done." : "The conversation is over, for now.")}
            </p>
            <div className="flex justify-center gap-2 pt-1">
              {turn > 0 && (
                <button onClick={() => onRetry(turn)} disabled={processing}
                  className="px-4 py-2 bg-patch-card border border-patch-border rounded-xl text-sm text-patch-soft/70 hover:border-patch-accent/40 transition-colors disabled:opacity-50">
                  ↺ Retry last turn
                </button>
              )}
              <button onClick={goToResult} className="px-4 py-2 bg-patch-accent rounded-xl text-sm text-white font-medium hover:bg-patch-accent/90 transition-colors">
                See debrief →
              </button>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      {!ended && (
        <div className="sticky bottom-0 bg-patch-bg/90 backdrop-blur-xl border-t border-patch-border px-4 py-4">
          {error && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between gap-2">
              <span>{error}</span>
              <button type="button" onClick={() => setError(null)} className="shrink-0 text-patch-soft/50 hover:text-patch-soft">✕</button>
            </div>
          )}
          <div className="flex justify-center mb-3">
            <button onClick={() => { setTextMode(!textMode); setError(null); }} className="text-[10px] text-patch-soft/30 hover:text-patch-soft/50 transition-colors">
              {textMode ? "Switch to Voice 🎙️" : "Switch to Text ⌨️"}
            </button>
          </div>
          {textMode ? (
            <div className="flex gap-2">
              <input type="text" value={textIn} onChange={e => setTextIn(e.target.value)}
                onKeyDown={e => e.key === "Enter" && onTextSend()} placeholder="Type your response..."
                disabled={processing} className="flex-1 px-4 py-3 bg-patch-card border border-patch-border rounded-xl text-sm text-patch-soft placeholder-patch-soft/30 focus:outline-none focus:border-patch-accent/50" />
              <button onClick={onTextSend} disabled={processing || !textIn.trim()}
                className="px-4 py-3 bg-patch-accent rounded-xl text-white font-medium text-sm disabled:opacity-30 hover:bg-patch-accent/80 transition-colors">
                {processing ? "..." : "Send"}
              </button>
            </div>
          ) : (
            <div className="flex justify-center">
              <MicButton isRecording={isRecording} isProcessing={processing} isPlaying={playing}
                disabled={ended} onTap={onMicTap} speakerName={session.counterpart_name} />
            </div>
          )}
          <div className="text-center mt-2 flex items-center justify-center gap-3">
            <span className="text-[10px] text-patch-soft/20">Turn {turn + 1}</span>
            {!classic && (
              <span className="text-[10px] text-patch-soft/20" title="The counterpart's internal dials">
                trust {cpState.trust} · defensiveness {cpState.defensiveness}
              </span>
            )}
            {judgedBy && (
              <span className="text-[10px] text-patch-soft/20" title={judgedBy === "jev" ? "Movement and scores judged by TypeSafe Jev" : "Movement self-reported by the actor; scores by the coach LLM"}>
                judged by {judgedBy === "jev" ? "Jev" : "the actor"}
              </span>
            )}
            {voiceProvider && (
              <span className="text-[10px] text-patch-soft/20" title={voiceProvider === "elevenlabs" ? "Voice by ElevenLabs" : "Voice by Sarvam Bulbul (fallback or configured)"}>
                voice {voiceProvider === "elevenlabs" ? "ElevenLabs" : "Sarvam"}
              </span>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
