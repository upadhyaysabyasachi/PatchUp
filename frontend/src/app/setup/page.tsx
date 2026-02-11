"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { startSession } from "@/lib/api";

const PERSONAS = [
  { id: "priya", name: "Priya", title: "Bollywood Drama Queen", emoji: "🎬", desc: "Over-the-top emotional, filmy dialogues, Karan Johar movie vibes" },
  { id: "neha", name: "Neha", title: "Silent Treatment Expert", emoji: "🧊", desc: "One-word answers, devastating one-liners, makes you feel the silence" },
  { id: "ritu", name: "Ritu", title: "The Logical Arguer", emoji: "🧠", desc: "Timestamps, receipts, builds a legal case against you" },
  { id: "kavya", name: "Kavya", title: "The Explosive One", emoji: "🌪️", desc: "Zero to hundred instantly, rapid-fire accusations, full rage" },
];

const SCENARIOS = [
  { id: "anniversary", title: "Forgot the Anniversary", emoji: "💀" },
  { id: "ex_photo", title: "Caught Liking Ex's Photo", emoji: "📱" },
  { id: "cooking", title: "Said Her Cooking Was 'Okay'", emoji: "🍳" },
  { id: "boys_trip", title: "Boys Trip Without Telling Her", emoji: "✈️" },
  { id: "late", title: "2 Hours Late, No Text", emoji: "🕐" },
  { id: "gaming", title: "Chose Gaming Over Date Night", emoji: "🎮" },
];

const DIFFS = [
  { id: "easy", name: "Thoda Gussa", emoji: "😤", desc: "Annoyed but willing to listen", score: 50 },
  { id: "medium", name: "Full Naraaz", emoji: "😠", desc: "Cold shoulder, work for it", score: 30 },
  { id: "hard", name: "Breakup Mode", emoji: "💢", desc: "One wrong word = it's over", score: 15 },
  { id: "nightmare", name: "Maa Ko Bata Dungi", emoji: "☠️", desc: "Threatens to involve family", score: 5 },
];

const LANGS = [
  { id: "hi-IN", label: "Hindi-English Mix", flag: "🇮🇳" },
  { id: "en-IN", label: "English (Indian)", flag: "🇬🇧" },
  { id: "ta-IN", label: "Tamil", flag: "🇮🇳" },
  { id: "te-IN", label: "Telugu", flag: "🇮🇳" },
  { id: "bn-IN", label: "Bengali", flag: "🇮🇳" },
  { id: "kn-IN", label: "Kannada", flag: "🇮🇳" },
  { id: "ml-IN", label: "Malayalam", flag: "🇮🇳" },
];

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [persona, setPersona] = useState("");
  const [scenario, setScenario] = useState("");
  const [diff, setDiff] = useState("medium");
  const [lang, setLang] = useState("hi-IN");
  const [starting, setStarting] = useState(false);

  const handleStart = async () => {
    if (!persona || !scenario) return;
    setStarting(true);
    try {
      const session = await startSession({ persona_id: persona, scenario_id: scenario, difficulty: diff, language: lang });
      sessionStorage.setItem("patchup_session", JSON.stringify(session));
      router.push(`/chat?id=${session.session_id}`);
    } catch (err) {
      console.error(err);
      alert("Failed to connect. Is the backend running on localhost:8000?");
      setStarting(false);
    }
  };

  const labels = ["opponent", "crime", "difficulty", "language"];

  return (
    <main className="min-h-screen px-4 py-8 max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <button onClick={() => (step > 1 ? setStep(step - 1) : router.push("/"))} className="text-patch-soft/40 hover:text-patch-soft/60 text-sm mb-4 inline-block">
          ← {step > 1 ? "Back" : "Home"}
        </button>
        <h1 className="font-display text-3xl font-bold text-patch-soft">Set the Scene</h1>
        <p className="text-sm text-patch-soft/50 mt-2">Step {step}/4 — Choose your {labels[step - 1]}</p>
        <div className="flex gap-1 mt-4 max-w-xs mx-auto">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? "bg-patch-accent" : "bg-patch-border"}`} />
          ))}
        </div>
      </div>

      {step === 1 && (
        <div className="space-y-3 animate-slide-up">
          <h2 className="font-display text-xl text-patch-soft/80 mb-4">Who are you dealing with?</h2>
          {PERSONAS.map((p) => (
            <button key={p.id} onClick={() => { setPersona(p.id); setStep(2); }}
              className="w-full text-left glass-card rounded-2xl p-4 transition-all hover:border-patch-accent/50 hover:scale-[1.01] active:scale-[0.99]">
              <div className="flex items-start gap-4">
                <span className="text-3xl">{p.emoji}</span>
                <div>
                  <span className="font-display font-semibold text-patch-soft">{p.name}</span>
                  <span className="ml-2 text-xs text-patch-glow/50 bg-patch-accent/10 px-2 py-0.5 rounded-full">{p.title}</span>
                  <p className="text-sm text-patch-soft/50 mt-1">{p.desc}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="animate-slide-up">
          <h2 className="font-display text-xl text-patch-soft/80 mb-4">What did you do? 😬</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SCENARIOS.map((s) => (
              <button key={s.id} onClick={() => { setScenario(s.id); setStep(3); }}
                className="text-left glass-card rounded-2xl p-4 transition-all hover:border-patch-accent/50 hover:scale-[1.02] active:scale-[0.98]">
                <span className="text-2xl block mb-2">{s.emoji}</span>
                <span className="font-display font-semibold text-sm text-patch-soft">{s.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3 animate-slide-up">
          <h2 className="font-display text-xl text-patch-soft/80 mb-4">How angry is she?</h2>
          {DIFFS.map((d) => (
            <button key={d.id} onClick={() => { setDiff(d.id); setStep(4); }}
              className="w-full text-left glass-card rounded-2xl p-4 transition-all hover:border-patch-accent/50 hover:scale-[1.01] active:scale-[0.99]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{d.emoji}</span>
                  <div>
                    <div className="font-display font-semibold text-patch-soft">{d.name}</div>
                    <div className="text-xs text-patch-soft/50">{d.desc}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-patch-soft/40">Starting</div>
                  <div className="font-mono text-sm text-patch-glow">{d.score}%</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {step === 4 && (
        <div className="space-y-6 animate-slide-up">
          <div>
            <h2 className="font-display text-xl text-patch-soft/80 mb-4">What language?</h2>
            <div className="grid grid-cols-2 gap-2">
              {LANGS.map((l) => (
                <button key={l.id} onClick={() => setLang(l.id)}
                  className={`text-left glass-card rounded-xl p-3 transition-all hover:border-patch-accent/50 ${lang === l.id ? "border-patch-accent ring-1 ring-patch-accent/30" : ""}`}>
                  <span className="text-lg mr-2">{l.flag}</span>
                  <span className="text-sm text-patch-soft">{l.label}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="glass-card rounded-2xl p-5 space-y-2 text-sm">
            <h3 className="font-display text-xs text-patch-soft/50 uppercase tracking-wider mb-2">Your Setup</h3>
            <div className="flex justify-between"><span className="text-patch-soft/60">Girlfriend</span><span className="text-patch-soft">{PERSONAS.find(p => p.id === persona)?.emoji} {PERSONAS.find(p => p.id === persona)?.name}</span></div>
            <div className="flex justify-between"><span className="text-patch-soft/60">Your Crime</span><span className="text-patch-soft">{SCENARIOS.find(s => s.id === scenario)?.emoji} {SCENARIOS.find(s => s.id === scenario)?.title}</span></div>
            <div className="flex justify-between"><span className="text-patch-soft/60">Anger Level</span><span className="text-patch-soft">{DIFFS.find(d => d.id === diff)?.emoji} {DIFFS.find(d => d.id === diff)?.name}</span></div>
            <div className="flex justify-between"><span className="text-patch-soft/60">Language</span><span className="text-patch-soft">{LANGS.find(l => l.id === lang)?.label}</span></div>
          </div>
          <button onClick={handleStart} disabled={starting}
            className="w-full py-4 bg-patch-accent rounded-2xl font-body font-semibold text-white text-lg hover:bg-patch-accent/90 transition-all animate-glow-pulse disabled:opacity-50 disabled:animate-none hover:scale-[1.02] active:scale-[0.98]">
            {starting ? "Connecting..." : "Start Conversation 🎙️"}
          </button>
        </div>
      )}
    </main>
  );
}
