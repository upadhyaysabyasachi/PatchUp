"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { sendVoiceResponse, sendTextResponse, playBase64Audio, endSession } from "@/lib/api";
import { webmToWav } from "@/lib/audioUtils";
import type { SessionStartResponse, RespondResponse } from "@/lib/api";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import PatchMeter from "@/components/PatchMeter";
import MicButton from "@/components/MicButton";
import ChatBubble from "@/components/ChatBubble";

interface Msg { role: "girlfriend"|"boyfriend"; text: string; emotion?: string; scoreDelta?: number; audio?: string; }
const P_EMOJI: Record<string,string> = { Priya:"🎬", Neha:"🧊", Ritu:"🧠", Kavya:"🌪️" };

export default function ChatContent() {
  const router = useRouter();
  const sessionId = useSearchParams().get("id");
  const [session, setSession] = useState<SessionStartResponse|null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [score, setScore] = useState(50);
  const [lastDelta, setLastDelta] = useState(0);
  const [emotion, setEmotion] = useState("angry");
  const [status, setStatus] = useState("ongoing");
  const [processing, setProcessing] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [textIn, setTextIn] = useState("");
  const [textMode, setTextMode] = useState(false);
  const [turn, setTurn] = useState(0);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const autoStopRef = useRef<() => void>(() => {});
  const { isRecording, startRecording, stopRecording } = useAudioRecorder(() => autoStopRef.current());

  useEffect(() => {
    const s = sessionStorage.getItem("patchup_session");
    if (!s) { router.push("/setup"); return; }
    const p: SessionStartResponse = JSON.parse(s);
    setSession(p); setScore(p.initial_score);
    setMsgs([{ role:"girlfriend", text:p.opening_message, emotion:"angry", audio:p.opening_audio }]);
    if (p.opening_audio) {
      setPlaying(true);
      playBase64Audio(p.opening_audio).catch(()=>{}).finally(() => setPlaying(false));
    }
  }, [router]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior:"smooth" }); }, [msgs]);

  const handleResp = useCallback(async (d: RespondResponse) => {
    setMsgs(p => [...p, { role:"boyfriend", text:d.user_text }]);
    await new Promise(r => setTimeout(r, 300));
    setMsgs(p => [...p, { role:"girlfriend", text:d.girlfriend_text, emotion:d.emotion, scoreDelta:d.score_delta, audio:d.girlfriend_audio }]);
    setScore(d.current_score); setLastDelta(d.score_delta); setEmotion(d.emotion); setStatus(d.status); setTurn(d.turn_number);
    if (d.girlfriend_audio) {
      setPlaying(true);
      try { await playBase64Audio(d.girlfriend_audio); } catch {}
      setPlaying(false);
    }
    if (d.status !== "ongoing") {
      sessionStorage.setItem("patchup_result", JSON.stringify({ sessionId, status:d.status, score:d.current_score }));
      setTimeout(() => router.push(`/result?id=${sessionId}`), 2500);
    }
  }, [sessionId, router]);

  const onMicPress = async () => {
    if (processing || playing || status !== "ongoing") return;
    try { await startRecording(); } catch { setTextMode(true); }
  };

  const onMicRelease = useCallback(async () => {
    if (!isRecording) return;
    setProcessing(true);
    setVoiceError(null);
    setSendError(null);
    try {
      const blob = await stopRecording();
      if (!sessionId) return;
      if (blob.size === 0) {
        setVoiceError("Recording was empty. Hold the mic longer or use \"Switch to Text\".");
        return;
      }
      const audioToSend = blob.type.includes("webm") ? await webmToWav(blob) : blob;
      const d = await sendVoiceResponse(sessionId, audioToSend);
      await handleResp(d);
    } catch (e) {
      console.error(e);
      let msg = e instanceof Error ? e.message : "Could not send voice. Try \"Switch to Text\".";
      if (msg.includes("404") || msg.toLowerCase().includes("session not found"))
        msg = "Session expired or backend restarted. Go to Setup to start a new chat.";
      setVoiceError(msg);
      setSendError(msg);
    } finally {
      setProcessing(false);
    }
  }, [isRecording, sessionId, stopRecording, handleResp]);

  // Keep ref in sync so the auto-stop timer can call onMicRelease
  autoStopRef.current = onMicRelease;

  const onTextSend = async () => {
    if (!textIn.trim() || !sessionId || processing || status !== "ongoing") return;
    const t = textIn.trim(); setTextIn("");
    setProcessing(true);
    setSendError(null);
    setVoiceError(null);
    try {
      await handleResp(await sendTextResponse(sessionId, t));
    } catch (e) {
      console.error(e);
      let msg = e instanceof Error ? e.message : "Message could not be sent.";
      if (msg.includes("404") || msg.toLowerCase().includes("session not found"))
        msg = "Session expired or backend restarted. Go to Setup to start a new chat.";
      setSendError(msg);
      setVoiceError(msg);
    }
    setProcessing(false);
  };

  const onEnd = async () => {
    if (sessionId) try { await endSession(sessionId); } catch {}
    sessionStorage.setItem("patchup_result", JSON.stringify({ sessionId, status, score }));
    router.push(`/result?id=${sessionId}`);
  };

  if (!session) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" /></div>;

  return (
    <main className="min-h-screen flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-patch-bg/90 backdrop-blur-xl border-b border-patch-border px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-patch-accent/20 border border-patch-accent/30 flex items-center justify-center text-sm">
              {P_EMOJI[session.persona_name] || "👩"}
            </div>
            <div>
              <div className="text-sm font-display font-semibold text-patch-soft">{session.persona_name}</div>
              <div className="text-[10px] text-patch-soft/40">{session.scenario_title} · {session.difficulty_name}</div>
            </div>
          </div>
          <button onClick={onEnd} className="text-xs text-patch-soft/40 hover:text-red-400 px-3 py-1 border border-patch-border rounded-lg hover:border-red-400/30 transition-colors">End Chat</button>
        </div>
        <PatchMeter score={score} scoreDelta={lastDelta} emotion={emotion} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {msgs.map((m, i) => (
          <ChatBubble key={i} role={m.role} text={m.text} emotion={m.emotion} scoreDelta={m.scoreDelta} audio={m.audio}
            personaName={m.role === "girlfriend" ? session.persona_name : undefined} />
        ))}
        {status === "patched_up" && (
          <div className="text-center py-6 animate-slide-up">
            <span className="text-4xl block mb-2">🎉</span>
            <span className="font-display text-xl text-green-400">PATCHED UP!</span>
            <p className="text-sm text-patch-soft/50 mt-1">She forgave you! Redirecting...</p>
          </div>
        )}
        {status === "blocked" && (
          <div className="text-center py-6 animate-slide-up">
            <span className="text-4xl block mb-2">💔</span>
            <span className="font-display text-xl text-red-400">BLOCKED</span>
            <p className="text-sm text-patch-soft/50 mt-1">She&apos;s done. Redirecting...</p>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      {status === "ongoing" && (
        <div className="sticky bottom-0 bg-patch-bg/90 backdrop-blur-xl border-t border-patch-border px-4 py-4">
          {(voiceError || sendError) && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between gap-2">
              <span>{voiceError || sendError}</span>
              <button type="button" onClick={() => { setVoiceError(null); setSendError(null); }} className="shrink-0 text-patch-soft/50 hover:text-patch-soft">✕</button>
            </div>
          )}
          <div className="flex justify-center mb-3">
            <button onClick={() => { setTextMode(!textMode); setVoiceError(null); setSendError(null); }} className="text-[10px] text-patch-soft/30 hover:text-patch-soft/50 transition-colors">
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
                disabled={status !== "ongoing"} onPress={onMicPress} onRelease={onMicRelease} />
            </div>
          )}
          <div className="text-center mt-2"><span className="text-[10px] text-patch-soft/20">Turn {turn + 1}</span></div>
        </div>
      )}
    </main>
  );
}
