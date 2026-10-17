"use client";
import { useEffect, useState } from "react";

export const EMOTION_LABELS: Record<string, { label: string; color: string; emoji: string }> = {
  angry: { label: "Furious", color: "text-red-400", emoji: "😡" },
  cold: { label: "Ice cold", color: "text-blue-300", emoji: "🧊" },
  sarcastic: { label: "Sarcastic", color: "text-amber-300", emoji: "😏" },
  softening: { label: "Softening", color: "text-pink-300", emoji: "🌸" },
  happy: { label: "Happy", color: "text-green-300", emoji: "😊" },
  crying: { label: "Crying", color: "text-blue-200", emoji: "😢" },
  explosive: { label: "Explosive", color: "text-orange-400", emoji: "🌋" },
  neutral: { label: "Neutral", color: "text-patch-soft/60", emoji: "😐" },
  warm: { label: "Warm", color: "text-green-300", emoji: "🙂" },
  anxious: { label: "Anxious", color: "text-amber-200", emoji: "😬" },
  firm: { label: "Firm", color: "text-slate-300", emoji: "😤" },
  defensive: { label: "Defensive", color: "text-orange-300", emoji: "🛡️" },
};

function statusText(score: number, kind: string, label: string): string {
  if (kind === "classic") {
    return score >= 90 ? "🎉 She forgives you!" : score >= 70 ? "😊 Getting there..." : score >= 50 ? "🤔 She's listening"
      : score >= 30 ? "😐 Still naraaz" : score >= 15 ? "😤 Making it worse" : score >= 1 ? "💀 Almost blocked!" : "💔 BLOCKED";
  }
  return score >= 90 ? `✓ ${label} secured` : score >= 70 ? "Coming around" : score >= 50 ? "Listening"
    : score >= 30 ? "Holding their position" : score >= 15 ? "Digging in" : score >= 1 ? "About to walk" : "Walked away";
}

/** Counterpart receptiveness. The label is the rubric's meter name (Forgiveness, Buy-in, ...). */
export default function PatchMeter({ score, scoreDelta, emotion, label = "Patch-Up Meter", kind = "classic" }: {
  score: number; scoreDelta?: number; emotion?: string; label?: string; kind?: string;
}) {
  const [showDelta, setShowDelta] = useState(false);

  useEffect(() => {
    if (scoreDelta !== undefined && scoreDelta !== 0) {
      setShowDelta(true);
      const t = setTimeout(() => setShowDelta(false), 2000);
      return () => clearTimeout(t);
    }
  }, [scoreDelta]);

  const emotionInfo = emotion ? EMOTION_LABELS[emotion] : null;
  const meterColor = score >= 70 ? "from-pink-500 to-rose-400"
    : score >= 40 ? "from-amber-500 to-orange-400" : "from-red-600 to-red-500";
  const classic = kind === "classic";

  return (
    <div className="w-full max-w-md mx-auto">
      {emotionInfo && (
        <div className="text-center mb-1.5">
          <span className={`text-[10px] font-medium tracking-wider uppercase ${emotionInfo.color}`}>{emotionInfo.label} {emotionInfo.emoji}</span>
        </div>
      )}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-patch-soft/50">{label}</span>
        <div className="flex items-center gap-2">
          {showDelta && scoreDelta !== undefined && (
            <span className={`text-sm font-bold animate-slide-up ${scoreDelta > 0 ? "text-green-400" : "text-red-400"}`}>
              {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}
            </span>
          )}
          <span className="text-base font-display font-bold text-patch-soft">{score}%</span>
        </div>
      </div>
      <div className="relative h-3.5 bg-patch-card rounded-full overflow-hidden border border-patch-border">
        <div className={`meter-bar h-full rounded-full bg-gradient-to-r ${meterColor}`} style={{ width: `${Math.max(2, score)}%` }} />
        {classic && (
          <div className="absolute inset-0 flex items-center justify-between px-0.5">
            {[...Array(10)].map((_, i) => (
              <span key={i} className={`text-[8px] transition-all duration-300 ${(i + 1) * 10 <= score ? "opacity-100" : "opacity-20"}`}>
                {(i + 1) * 10 <= score ? "❤️" : "🖤"}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="text-center mt-1.5">
        <span className="text-xs text-patch-soft/70">{statusText(score, kind, label)}</span>
      </div>
    </div>
  );
}
