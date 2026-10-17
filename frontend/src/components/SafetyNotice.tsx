"use client";
import type { SafetyNotice as Notice } from "@/lib/api";

export default function SafetyNotice({ notice, onBack }: { notice: Notice; onBack: () => void }) {
  return (
    <div className="glass-card rounded-2xl p-6 space-y-4 animate-slide-up border-amber-400/30">
      <div>
        <h2 className="font-display text-xl text-patch-soft">{notice.title}</h2>
        <p className="text-sm text-patch-soft/70 mt-2 leading-relaxed">{notice.message}</p>
      </div>
      <ul className="space-y-2">
        {notice.resources.map((r) => (
          <li key={r.name} className="flex items-center justify-between gap-3 bg-patch-card border border-patch-border rounded-xl px-4 py-3">
            <span className="text-sm text-patch-soft/80">{r.name}</span>
            <a href={`tel:${r.contact.replace(/[^\d+]/g, "")}`} className="font-mono text-sm text-patch-glow whitespace-nowrap hover:underline">
              {r.contact}
            </a>
          </li>
        ))}
      </ul>
      <p className="text-xs text-patch-soft/40">Nothing you typed was saved.</p>
      <button onClick={onBack} className="w-full py-3 bg-patch-card border border-patch-border rounded-xl text-sm text-patch-soft/70 hover:border-patch-accent/40 transition-colors">
        ← Back
      </button>
    </div>
  );
}
