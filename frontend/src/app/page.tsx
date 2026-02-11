"use client";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  return (
    <main className="min-h-screen flex flex-col items-center justify-center relative px-4">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-patch-accent/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="relative z-10 text-center max-w-lg mx-auto flex-1 flex flex-col items-center justify-center">
        <div className="mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-patch-card border border-patch-border mb-6" style={{ boxShadow: "0 0 30px rgba(225,29,72,0.2)" }}>
            <span className="text-5xl">🩹</span>
          </div>
          <h1 className="font-display text-5xl sm:text-6xl font-bold text-patch-soft tracking-tight">
            Patch<span className="text-patch-accent">Up</span>
          </h1>
          <p className="mt-3 text-lg text-patch-soft/60 font-body">Practice before you patch up.</p>
          <p className="text-sm text-patch-soft/40 font-body italic mt-1">Because second chances don&apos;t come with a tutorial.</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {["🗣️ Voice Conversations", "🎭 Multiple Personas", "🔥 Difficulty Levels", "💕 Patch-Up Meter"].map((f) => (
            <span key={f} className="px-3 py-1.5 text-xs font-medium bg-patch-card border border-patch-border rounded-full text-patch-soft/70">{f}</span>
          ))}
        </div>
        <button onClick={() => router.push("/setup")}
          className="group relative px-8 py-4 bg-patch-accent rounded-2xl font-body font-semibold text-white text-lg hover:bg-patch-accent/90 transition-all duration-200 animate-glow-pulse hover:scale-105 active:scale-95">
          Start Practicing <span className="ml-2 inline-block group-hover:translate-x-1 transition-transform">→</span>
        </button>
        <div className="mt-12 flex items-center justify-center gap-2 text-xs text-patch-soft/30">
          <span>Powered by</span><span className="font-semibold text-patch-soft/50">Sarvam AI — Bulbul V3</span><span>🇮🇳</span>
        </div>
        <div className="mt-4 inline-block px-3 py-1 bg-patch-card border border-patch-border rounded-full">
          <span className="text-[10px] text-patch-soft/40 tracking-wider uppercase">#TheMicIsYours · Build with Bulbul Challenge</span>
        </div>
      </div>
      <footer className="relative z-10 w-full py-6 text-center border-t border-patch-border/50 mt-auto">
        <p className="text-sm text-patch-soft/50 font-body">
          Made by Sabyasachi Upadhyay with <span className="text-patch-accent">♥</span>
        </p>
        <p className="mt-1 text-xs text-patch-soft/40">
          © {new Date().getFullYear()} Sabyasachi Upadhyay. All rights reserved.
        </p>
      </footer>
    </main>
  );
}
