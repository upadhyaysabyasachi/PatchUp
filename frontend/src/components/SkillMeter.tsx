"use client";
import type { Dimension } from "@/lib/api";

/** Per-dimension coaching averages (0-10). Dims with no scored turns yet show as empty. */
export default function SkillMeter({ dimensions, scores, compact = false }: {
  dimensions: Dimension[]; scores: Record<string, number>; compact?: boolean;
}) {
  if (!dimensions.length) return null;
  return (
    <div className={`grid gap-x-4 gap-y-1.5 ${compact ? "grid-cols-3" : "grid-cols-1"}`}>
      {dimensions.map((d) => {
        const value = scores[d.id];
        const scored = typeof value === "number";
        const pct = scored ? Math.max(4, (value / 10) * 100) : 0;
        const tone = !scored ? "bg-patch-border" : value >= 7 ? "bg-green-400" : value >= 4 ? "bg-amber-400" : "bg-red-400";
        return (
          <div key={d.id} title={scored ? d.description : `${d.description}. Not scored until it applies.`}>
            <div className="flex items-center justify-between mb-0.5">
              <span className={`truncate ${scored ? "text-patch-soft/60" : "text-patch-soft/35"} ${compact ? "text-[10px]" : "text-xs"}`}>{d.label}</span>
              <span className={`font-mono ${scored ? "text-patch-soft/80" : "text-patch-soft/30"} ${compact ? "text-[10px]" : "text-xs"}`}>{scored ? value.toFixed(1) : "n/a yet"}</span>
            </div>
            <div className="h-1.5 bg-patch-card rounded-full overflow-hidden border border-patch-border/60">
              <div className={`h-full rounded-full transition-all duration-500 ${tone}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
