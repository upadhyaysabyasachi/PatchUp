"use client";
import { useState } from "react";
import { playBase64Audio } from "@/lib/api";

const EMOTION_EMOJIS: Record<string, string> = {
  angry: "😡", cold: "🧊", sarcastic: "😏", softening: "🌸",
  happy: "😊", crying: "😢", explosive: "🌋",
};

export default function ChatBubble({ role, text, emotion, scoreDelta, audio, personaName }: {
  role: "girlfriend" | "boyfriend"; text: string; emotion?: string;
  scoreDelta?: number; audio?: string; personaName?: string;
}) {
  const [playing, setPlaying] = useState(false);
  const isGF = role === "girlfriend";

  const replay = async () => {
    if (!audio || playing) return;
    setPlaying(true);
    try { await playBase64Audio(audio); } catch (e) { console.error(e); }
    setPlaying(false);
  };

  return (
    <div className={`flex gap-2.5 animate-slide-up ${isGF ? "justify-start" : "justify-end"}`}>
      {isGF && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-patch-accent/20 border border-patch-accent/30 flex items-center justify-center text-sm">
          {emotion ? EMOTION_EMOJIS[emotion] || "😐" : "👩"}
        </div>
      )}
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
        isGF ? "bg-patch-card border border-patch-border rounded-tl-sm"
             : "bg-patch-accent/20 border border-patch-accent/30 rounded-tr-sm"}`}>
        {isGF && personaName && (
          <div className="text-[10px] text-patch-glow/50 font-medium mb-1 uppercase tracking-wider">{personaName}</div>
        )}
        <p className="text-sm text-patch-soft leading-relaxed">{text}</p>
        <div className="flex items-center justify-between mt-1.5 gap-3">
          {isGF && audio && (
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
          {isGF && scoreDelta !== undefined && scoreDelta !== 0 && (
            <span className={`text-[10px] font-mono font-bold ${scoreDelta > 0 ? "text-green-400" : "text-red-400"}`}>
              {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}
            </span>
          )}
        </div>
      </div>
      {!isGF && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-patch-accent/10 border border-patch-accent/20 flex items-center justify-center text-sm">🙍‍♂️</div>
      )}
    </div>
  );
}
