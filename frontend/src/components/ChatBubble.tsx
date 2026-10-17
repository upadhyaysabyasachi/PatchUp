"use client";
import { useState } from "react";
import { playBase64Audio, averageSkill } from "@/lib/api";
import type { CoachNote } from "@/lib/api";
import { EMOTION_LABELS } from "./PatchMeter";

const labelOf = (dim: string) => dim.replace(/_/g, " ");

export default function ChatBubble({ role, text, emotion, scoreDelta, audio, personaName, coach, turnNumber, onRetry, canRetry }: {
  role: "counterpart" | "user"; text: string; emotion?: string;
  scoreDelta?: number; audio?: string; personaName?: string;
  coach?: CoachNote | null; turnNumber?: number;
  onRetry?: (turnNumber: number) => void; canRetry?: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const [showCoach, setShowCoach] = useState(false);
  const isCounterpart = role === "counterpart";
  const avg = coach ? averageSkill(coach.scores) : null;

  const replay = async () => {
    if (!audio || playing) return;
    setPlaying(true);
    try { await playBase64Audio(audio); } catch (e) { console.error(e); }
    setPlaying(false);
  };

  return (
    <div className={`flex gap-2.5 animate-slide-up ${isCounterpart ? "justify-start" : "justify-end"}`}>
      {isCounterpart && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-patch-accent/20 border border-patch-accent/30 flex items-center justify-center text-sm">
          {emotion ? EMOTION_LABELS[emotion]?.emoji || "😐" : "🗣️"}
        </div>
      )}
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
        isCounterpart ? "bg-patch-card border border-patch-border rounded-tl-sm"
             : "bg-patch-accent/20 border border-patch-accent/30 rounded-tr-sm"}`}>
        {isCounterpart && personaName && (
          <div className="text-[10px] text-patch-glow/50 font-medium mb-1 uppercase tracking-wider">{personaName}</div>
        )}
        <p className="text-sm text-patch-soft leading-relaxed">{text}</p>

        <div className="flex items-center justify-between mt-1.5 gap-3">
          {isCounterpart && audio && (
            <button onClick={replay} disabled={playing}
              className="flex items-center gap-1 text-[10px] text-patch-glow/50 hover:text-patch-glow transition-colors">
              {playing ? (
                <span className="flex gap-0.5">{[0,1,2].map(i => <span key={i} className="wave-bar inline-block w-0.5 bg-patch-glow rounded-full" style={{ height: "6px" }} />)}</span>
              ) : (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
              )}
              <span>{playing ? "Playing" : "Replay"}</span>
            </button>
          )}
          {isCounterpart && scoreDelta !== undefined && scoreDelta !== 0 && (
            <span className={`text-[10px] font-mono font-bold ${scoreDelta > 0 ? "text-green-400" : "text-red-400"}`}>
              {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}
            </span>
          )}
          {!isCounterpart && (
            <div className="flex items-center gap-3 ml-auto">
              {coach && (
                <button onClick={() => setShowCoach(!showCoach)}
                  className={`text-[10px] transition-colors ${showCoach ? "text-patch-glow" : "text-patch-glow/60 hover:text-patch-glow"}`}>
                  🧭 Coach{avg !== null && <span className="font-mono ml-1">{avg.toFixed(1)}</span>} {showCoach ? "▴" : "▾"}
                </button>
              )}
              {canRetry && onRetry && turnNumber && (
                <button onClick={() => onRetry(turnNumber)} title="Rewind the conversation to just before this message"
                  className="text-[10px] text-patch-soft/40 hover:text-patch-soft transition-colors">
                  ↺ Retry
                </button>
              )}
            </div>
          )}
        </div>

        {!isCounterpart && coach && showCoach && (
          <div className="mt-2 pt-2 border-t border-patch-accent/20 space-y-2 animate-slide-up">
            {Object.keys(coach.scores).length > 0 && (
              <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                {Object.entries(coach.scores).map(([dim, v]) => (
                  <span key={dim} className="text-[10px] text-patch-soft/60 capitalize">
                    {labelOf(dim)} <span className={`font-mono ${v >= 7 ? "text-green-400" : v >= 4 ? "text-amber-400" : "text-red-400"}`}>{v}</span>
                  </span>
                ))}
              </div>
            )}
            {coach.note && <p className="text-xs text-patch-soft/80 italic">{coach.note}</p>}
            {coach.stronger && (
              <div>
                <div className="text-[10px] text-patch-glow/60 uppercase tracking-wider mb-0.5">Stronger</div>
                <p className="text-xs text-patch-soft leading-relaxed">&ldquo;{coach.stronger}&rdquo;</p>
              </div>
            )}
          </div>
        )}
      </div>
      {!isCounterpart && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-patch-accent/10 border border-patch-accent/20 flex items-center justify-center text-sm">🙂</div>
      )}
    </div>
  );
}
