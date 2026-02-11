"use client";
import { useEffect, useState } from "react";

const EMOTION_LABELS: Record<string, { label: string; color: string }> = {
  angry: { label: "Furious 😡", color: "text-red-400" },
  cold: { label: "Ice Cold 🧊", color: "text-blue-300" },
  sarcastic: { label: "Sarcastic 😏", color: "text-amber-300" },
  softening: { label: "Softening 🌸", color: "text-pink-300" },
  happy: { label: "Happy 😊", color: "text-green-300" },
  crying: { label: "Crying 😢", color: "text-blue-200" },
  explosive: { label: "EXPLOSIVE 🌋", color: "text-orange-400" },
};

export default function PatchMeter({ score, scoreDelta, emotion }: {
  score: number; scoreDelta?: number; emotion?: string;
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

  const statusText = score >= 90 ? "🎉 She forgives you!"
    : score >= 70 ? "😊 Getting there..." : score >= 50 ? "🤔 She's listening"
    : score >= 30 ? "😐 Still naraaz" : score >= 15 ? "😤 Making it worse"
    : score >= 1 ? "💀 Almost blocked!" : "💔 BLOCKED";

  return (
    <div className="w-full max-w-md mx-auto">
      {emotionInfo && (
        <div className="text-center mb-1.5">
          <span className={`text-[10px] font-medium tracking-wider uppercase ${emotionInfo.color}`}>{emotionInfo.label}</span>
        </div>
      )}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-patch-soft/50">Patch-Up Meter</span>
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
        <div className="absolute inset-0 flex items-center justify-between px-0.5">
          {[...Array(10)].map((_, i) => (
            <span key={i} className={`text-[8px] transition-all duration-300 ${(i + 1) * 10 <= score ? "opacity-100" : "opacity-20"}`}>
              {(i + 1) * 10 <= score ? "❤️" : "🖤"}
            </span>
          ))}
        </div>
      </div>
      <div className="text-center mt-1.5">
        <span className="text-xs text-patch-soft/70">{statusText}</span>
      </div>
    </div>
  );
}
