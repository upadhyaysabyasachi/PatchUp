"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getCatalog, buildScenario, startSession, EMPTY_INTAKE } from "@/lib/api";
import type { Catalog, Intake, LevelOption, SafetyNotice as Notice } from "@/lib/api";
import IntakeForm from "@/components/IntakeForm";
import SafetyNotice from "@/components/SafetyNotice";

type Mode = "" | "preset" | "custom" | "classic";

const LEVEL_EMOJI: Record<string, string> = {
  open: "🙂", defensive: "🛡️", hostile: "🔥",
  easy: "😤", medium: "😠", hard: "💢", nightmare: "☠️",
};
const LANG_FLAG: Record<string, string> = { "en-IN": "🇬🇧" };

const card = "w-full text-left glass-card rounded-2xl p-4 transition-all hover:border-patch-accent/50 hover:scale-[1.01] active:scale-[0.99]";
const selectedCard = "border-patch-accent ring-1 ring-patch-accent/30";

function LevelPicker({ title, options, onPick }: { title: string; options: LevelOption[]; onPick: (id: string) => void }) {
  return (
    <div className="space-y-3 animate-slide-up">
      <h2 className="font-display text-xl text-patch-soft/80 mb-4">{title}</h2>
      {options.map((d) => (
        <button key={d.id} onClick={() => onPick(d.id)} className={card}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{LEVEL_EMOJI[d.id] || "•"}</span>
              <div>
                <div className="font-display font-semibold text-patch-soft">{d.name}</div>
                <div className="text-xs text-patch-soft/50">{d.description}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-patch-soft/40">Starting</div>
              <div className="font-mono text-sm text-patch-glow">{d.starting_score}%</div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

export default function SetupPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("");
  const [step, setStep] = useState(1);
  const [presetId, setPresetId] = useState("");
  const [intake, setIntake] = useState<Intake>(EMPTY_INTAKE);
  const [customize, setCustomize] = useState(false);
  const [persona, setPersona] = useState("");
  const [scenario, setScenario] = useState("");
  const [level, setLevel] = useState("");
  const [lang, setLang] = useState("en-IN");
  const [busy, setBusy] = useState<"" | "building" | "starting">("");
  const [error, setError] = useState<string | null>(null);
  const [safety, setSafety] = useState<Notice | null>(null);
  const [slowLoad, setSlowLoad] = useState(false);

  useEffect(() => {
    getCatalog().then(setCatalog).catch((e) => setLoadError(e instanceof Error ? e.message : "Could not load"));
    const t = setTimeout(() => setSlowLoad(true), 4000);
    return () => clearTimeout(t);
  }, []);

  const preset = useMemo(() => catalog?.presets.find(p => p.id === presetId), [catalog, presetId]);
  const totalSteps = mode === "classic" ? 4 : 3;
  const levelOptions = mode === "classic" ? catalog?.difficulties ?? [] : catalog?.temperaments ?? [];
  const levelName = levelOptions.find(l => l.id === level)?.name;

  const reset = () => { setMode(""); setStep(1); setPresetId(""); setIntake(EMPTY_INTAKE); setCustomize(false); setPersona(""); setScenario(""); setLevel(""); setSafety(null); setError(null); };
  const back = () => {
    setError(null);
    if (safety) { setSafety(null); return; }
    if (step > 1) setStep(step - 1);
    else if (mode) reset();
    else router.push("/");
  };
  const enter = (next: Mode) => { setMode(next); setStep(1); setLang(next === "classic" ? "hi-IN" : "en-IN"); };

  const pickPreset = (id: string) => {
    const p = catalog!.presets.find(x => x.id === id)!;
    setPresetId(id); setIntake(p.intake); setCustomize(false); enter("preset");
  };

  const handleStart = async () => {
    if (!catalog || !level) return;
    setError(null);
    try {
      if (mode === "classic") {
        setBusy("starting");
        const session = await startSession({ persona_id: persona, scenario_id: scenario, difficulty: level, language: lang });
        sessionStorage.setItem("patchup_session", JSON.stringify(session));
        router.push(`/chat?id=${session.session_id}`);
        return;
      }
      setBusy("building");
      const built = await buildScenario(mode === "preset" ? { preset_id: presetId, intake } : { intake });
      if (built.safety) { setSafety(built.safety); setBusy(""); return; }
      if (!built.brief) throw new Error("No brief came back. Try again.");
      setBusy("starting");
      const session = await startSession({ brief: built.brief, difficulty: level, language: lang });
      sessionStorage.setItem("patchup_session", JSON.stringify(session));
      router.push(`/chat?id=${session.session_id}`);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy("");
    }
  };

  if (loadError) return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="glass-card rounded-2xl p-6 max-w-md text-center space-y-3">
        <p className="text-sm text-red-400">{loadError}</p>
        <p className="text-xs text-patch-soft/40">Start the backend (<code>uvicorn main:app --reload --port 8000</code>) and reload.</p>
      </div>
    </main>
  );
  if (!catalog) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" />
      {slowLoad && <p className="text-xs text-patch-soft/40 animate-slide-up">Waking up the backend… free hosting can take up to a minute after idle.</p>}
    </div>
  );

  const stepLabel = mode === "classic"
    ? ["Who you're dealing with", "What you did", "How angry she is", "Language"][step - 1]
    : mode === "preset" ? ["The setup", "Their temperament", "Language"][step - 1]
    : mode === "custom" ? ["Your situation", "Their temperament", "Language"][step - 1]
    : "Pick a conversation";

  return (
    <main className="min-h-screen px-4 py-8 max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <button onClick={back} className="text-patch-soft/40 hover:text-patch-soft/60 text-sm mb-4 inline-block">
          ← {safety ? "Back" : step > 1 ? "Back" : mode ? "All conversations" : "Home"}
        </button>
        <h1 className="font-display text-3xl font-bold text-patch-soft">{mode ? (preset?.title ?? (mode === "custom" ? "Your conversation" : "Set the Scene")) : "What are you rehearsing?"}</h1>
        <p className="text-sm text-patch-soft/50 mt-2">{mode ? `Step ${step}/${totalSteps} — ${stepLabel}` : "Pick a template, write your own, or play the classic."}</p>
        {mode && (
          <div className="flex gap-1 mt-4 max-w-xs mx-auto">
            {Array.from({ length: totalSteps }, (_, i) => i + 1).map((s) => (
              <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? "bg-patch-accent" : "bg-patch-border"}`} />
            ))}
          </div>
        )}
      </div>

      {safety && <SafetyNotice notice={safety} onBack={back} />}

      {/* ── Mode picker ── */}
      {!safety && !mode && (
        <div className="space-y-8 animate-slide-up">
          <section>
            <h2 className="font-display text-lg text-patch-soft/80 mb-3">Rehearse a real one</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {catalog.presets.map((p) => (
                <button key={p.id} onClick={() => pickPreset(p.id)} className={`${card} text-left`}>
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{p.emoji}</span>
                    <div className="min-w-0">
                      <div className="font-display font-semibold text-sm text-patch-soft">{p.title}</div>
                      <div className="text-[10px] text-patch-glow/50 uppercase tracking-wider mt-0.5">{catalog.rubrics[p.conversation_type].name}</div>
                      <p className="text-xs text-patch-soft/50 mt-1 leading-relaxed">{p.description}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <button onClick={() => { setIntake(EMPTY_INTAKE); enter("custom"); }} className={`${card} border-dashed`}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">✍️</span>
              <div>
                <div className="font-display font-semibold text-patch-soft">Write your own</div>
                <p className="text-xs text-patch-soft/50 mt-0.5">Tell us who it is and what you need. We&apos;ll build the other side, with a few things you haven&apos;t prepared for.</p>
              </div>
            </div>
          </button>

          <button onClick={() => enter("classic")} className={card}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">🩹</span>
              <div>
                <div className="font-display font-semibold text-patch-soft">Classic PatchUp</div>
                <p className="text-xs text-patch-soft/50 mt-0.5">The original. Convince an angry girlfriend to forgive you. Priya, Neha, Ritu, Kavya.</p>
              </div>
            </div>
          </button>
        </div>
      )}

      {/* ── Preset: brief + customize ── */}
      {!safety && mode === "preset" && step === 1 && preset && (
        <div className="space-y-4 animate-slide-up">
          <div className="glass-card rounded-2xl p-5 space-y-3">
            <div className="flex items-start gap-3">
              <span className="text-3xl">{preset.emoji}</span>
              <div>
                <div className="font-display font-semibold text-patch-soft">{intake.counterpart.name} <span className="font-body font-normal text-patch-soft/50">· {intake.counterpart.role}</span></div>
                <p className="text-sm text-patch-soft/60 mt-1">{preset.description}</p>
              </div>
            </div>
            <div className="text-sm space-y-2 pt-2 border-t border-patch-border/60">
              <div><span className="text-patch-glow/60 text-xs uppercase tracking-wider">You need</span><p className="text-patch-soft/80">{intake.user_goal}</p></div>
              <div><span className="text-patch-glow/60 text-xs uppercase tracking-wider">You&apos;re afraid they&apos;ll say</span><p className="text-patch-soft/80">{intake.user_fears}</p></div>
              <div><span className="text-patch-glow/60 text-xs uppercase tracking-wider">So far</span><p className="text-patch-soft/80">{intake.history}</p></div>
            </div>
            <button onClick={() => setCustomize(!customize)} className="text-xs text-patch-glow/60 hover:text-patch-glow transition-colors">
              {customize ? "▴ Hide" : "▾ Customize this"} <span className="text-patch-soft/30">— names, goal, what actually happened</span>
            </button>
            {customize && <div className="pt-2"><IntakeForm value={intake} onChange={setIntake} accents={catalog.accents} /></div>}
          </div>
          <button onClick={() => setStep(2)} className="w-full py-3.5 bg-patch-accent rounded-2xl font-semibold text-white hover:bg-patch-accent/90 transition-all hover:scale-[1.01] active:scale-[0.99]">
            Continue →
          </button>
        </div>
      )}

      {/* ── Custom: intake ── */}
      {!safety && mode === "custom" && step === 1 && (
        <div className="space-y-4 animate-slide-up">
          <div className="glass-card rounded-2xl p-5">
            <IntakeForm value={intake} onChange={setIntake} accents={catalog.accents} />
          </div>
          <button onClick={() => setStep(2)} disabled={!intake.user_goal.trim() || !intake.counterpart.role.trim()}
            className="w-full py-3.5 bg-patch-accent rounded-2xl font-semibold text-white hover:bg-patch-accent/90 transition-all disabled:opacity-40 hover:scale-[1.01] active:scale-[0.99]">
            Continue →
          </button>
          <p className="text-center text-[11px] text-patch-soft/30">We need at least who they are and what you need from them.</p>
        </div>
      )}

      {/* ── Classic: persona / scenario ── */}
      {!safety && mode === "classic" && step === 1 && (
        <div className="space-y-3 animate-slide-up">
          <h2 className="font-display text-xl text-patch-soft/80 mb-4">Who are you dealing with?</h2>
          {catalog.personas.map((p) => (
            <button key={p.id} onClick={() => { setPersona(p.id); setStep(2); }} className={card}>
              <div className="flex items-start gap-4">
                <span className="text-3xl">{p.emoji}</span>
                <div>
                  <span className="font-display font-semibold text-patch-soft">{p.name}</span>
                  <span className="ml-2 text-xs text-patch-glow/50 bg-patch-accent/10 px-2 py-0.5 rounded-full">{p.title}</span>
                  <p className="text-sm text-patch-soft/50 mt-1">{p.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
      {!safety && mode === "classic" && step === 2 && (
        <div className="animate-slide-up">
          <h2 className="font-display text-xl text-patch-soft/80 mb-4">What did you do? 😬</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {catalog.scenarios.map((s) => (
              <button key={s.id} onClick={() => { setScenario(s.id); setStep(3); }} className={`${card} hover:scale-[1.02]`}>
                <span className="text-2xl block mb-2">{s.emoji}</span>
                <span className="font-display font-semibold text-sm text-patch-soft">{s.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Temperament / difficulty ── */}
      {!safety && ((mode !== "classic" && step === 2) || (mode === "classic" && step === 3)) && (
        <LevelPicker
          title={mode === "classic" ? "How angry is she?" : `How is ${intake.counterpart.name || "the other person"} coming into this?`}
          options={levelOptions}
          onPick={(id) => { setLevel(id); setStep(step + 1); }}
        />
      )}

      {/* ── Language + summary + start ── */}
      {!safety && step === totalSteps && mode && (
        <div className="space-y-6 animate-slide-up">
          <div>
            <h2 className="font-display text-xl text-patch-soft/80 mb-4">What language?</h2>
            <div className="grid grid-cols-2 gap-2">
              {catalog.languages.map((l) => (
                <button key={l.id} onClick={() => setLang(l.id)}
                  className={`text-left glass-card rounded-xl p-3 transition-all hover:border-patch-accent/50 ${lang === l.id ? selectedCard : ""}`}>
                  <span className="text-lg mr-2">{LANG_FLAG[l.id] || "🇮🇳"}</span>
                  <span className="text-sm text-patch-soft">{l.label}</span>
                </button>
              ))}
            </div>
            {mode !== "classic" && lang !== "en-IN" && (
              <p className="text-[11px] text-patch-soft/40 mt-2">The opening line is translated with Sarvam Mayura; the rest of the conversation happens in that language.</p>
            )}
          </div>
          <div className="glass-card rounded-2xl p-5 space-y-2 text-sm">
            <h3 className="font-display text-xs text-patch-soft/50 uppercase tracking-wider mb-2">Your Setup</h3>
            {mode === "classic" ? (
              <>
                <div className="flex justify-between"><span className="text-patch-soft/60">Girlfriend</span><span className="text-patch-soft">{catalog.personas.find(p => p.id === persona)?.emoji} {catalog.personas.find(p => p.id === persona)?.name}</span></div>
                <div className="flex justify-between"><span className="text-patch-soft/60">Your Crime</span><span className="text-patch-soft">{catalog.scenarios.find(s => s.id === scenario)?.emoji} {catalog.scenarios.find(s => s.id === scenario)?.title}</span></div>
                <div className="flex justify-between"><span className="text-patch-soft/60">Anger Level</span><span className="text-patch-soft">{LEVEL_EMOJI[level]} {levelName}</span></div>
              </>
            ) : (
              <>
                <div className="flex justify-between gap-4"><span className="text-patch-soft/60 shrink-0">Talking to</span><span className="text-patch-soft text-right">{intake.counterpart.name || "—"} · {intake.counterpart.role}</span></div>
                <div className="flex justify-between"><span className="text-patch-soft/60">Voice</span><span className="text-patch-soft capitalize">{intake.counterpart.gender} · {catalog.accents?.find(a => a.id === intake.counterpart.accent)?.label ?? intake.counterpart.accent}</span></div>
                <div className="flex justify-between gap-4"><span className="text-patch-soft/60 shrink-0">You need</span><span className="text-patch-soft text-right line-clamp-2">{intake.user_goal}</span></div>
                <div className="flex justify-between"><span className="text-patch-soft/60">Temperament</span><span className="text-patch-soft">{LEVEL_EMOJI[level]} {levelName}</span></div>
              </>
            )}
            <div className="flex justify-between"><span className="text-patch-soft/60">Language</span><span className="text-patch-soft">{catalog.languages.find(l => l.id === lang)?.label}</span></div>
          </div>
          {error && <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">{error}</div>}
          <button onClick={handleStart} disabled={!!busy}
            className="w-full py-4 bg-patch-accent rounded-2xl font-body font-semibold text-white text-lg hover:bg-patch-accent/90 transition-all animate-glow-pulse disabled:opacity-50 disabled:animate-none hover:scale-[1.02] active:scale-[0.98]">
            {busy === "building" ? "Building the other side…" : busy === "starting" ? "Connecting…" : "Start Conversation 🎙️"}
          </button>
          {busy === "building" && <p className="text-center text-[11px] text-patch-soft/40">Sarvam 105b is writing {intake.counterpart.name || "their"} hidden motivations and a couple of curveballs. ~10s.</p>}
        </div>
      )}
    </main>
  );
}
