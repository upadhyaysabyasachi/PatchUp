"use client";
import type { Accent, Intake } from "@/lib/api";

const inputClass = "w-full px-3 py-2.5 bg-patch-card border border-patch-border rounded-xl text-sm text-patch-soft placeholder-patch-soft/30 focus:outline-none focus:border-patch-accent/50";
const DEFAULT_ACCENTS: Accent[] = [{ id: "indian", label: "Indian" }, { id: "any", label: "No preference" }];

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-patch-soft/60 mb-1">{label}{hint && <span className="text-patch-soft/30"> · {hint}</span>}</span>
      {children}
    </label>
  );
}

/** The scenario intake: who the other person is, what you need, what you're afraid of. */
export default function IntakeForm({ value, onChange, accents = DEFAULT_ACCENTS }: {
  value: Intake; onChange: (next: Intake) => void; accents?: Accent[];
}) {
  const cp = value.counterpart;
  const setCp = (patch: Partial<Intake["counterpart"]>) => onChange({ ...value, counterpart: { ...cp, ...patch } });
  const set = (patch: Partial<Intake>) => onChange({ ...value, ...patch });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="Their name">
          <input className={inputClass} value={cp.name} onChange={e => setCp({ name: e.target.value })} placeholder="Rohan" maxLength={60} />
        </Field>
        <Field label="Who they are to you">
          <input className={inputClass} value={cp.role} onChange={e => setCp({ role: e.target.value })} placeholder="My manager / my father / my co-founder" maxLength={120} />
        </Field>
      </div>

      <div className="grid grid-cols-[auto_1fr] gap-3">
        <Field label="Voice">
          <div className="flex rounded-xl overflow-hidden border border-patch-border">
            {(["female", "male"] as const).map(g => (
              <button key={g} type="button" onClick={() => setCp({ gender: g })}
                className={`px-3 py-2.5 text-sm capitalize transition-colors ${cp.gender === g ? "bg-patch-accent/30 text-patch-soft" : "bg-patch-card text-patch-soft/50 hover:text-patch-soft"}`}>
                {g}
              </button>
            ))}
          </div>
        </Field>
        <Field label="Accent" hint="how they sound">
          <select className={inputClass} value={cp.accent || "indian"} onChange={e => setCp({ accent: e.target.value })}>
            {accents.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </Field>
      </div>

      <Field label="What outcome do you need?" hint="be concrete">
        <input className={inputClass} value={value.user_goal} onChange={e => set({ user_goal: e.target.value })}
          placeholder="A 20% raise, or a written plan to get there" maxLength={400} />
      </Field>

      <Field label="What are you afraid they'll say?">
        <input className={inputClass} value={value.user_fears} onChange={e => set({ user_fears: e.target.value })}
          placeholder="That the budget is frozen. That I'm being ungrateful." maxLength={400} />
      </Field>

      <Field label="Relationship & history" hint="what's happened so far">
        <textarea className={`${inputClass} min-h-[72px] resize-y`} value={value.history} onChange={e => set({ history: e.target.value })}
          placeholder="Last cycle I got 6%. Two peers were promoted. I shipped the migration on time." maxLength={800} />
      </Field>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="How they relate to you" hint="optional">
          <textarea className={`${inputClass} min-h-[60px] resize-y`} value={cp.relationship} onChange={e => setCp({ relationship: e.target.value })}
            placeholder="Friendly but businesslike. Reported to him 18 months." maxLength={400} />
        </Field>
        <Field label="Their usual style under pressure" hint="optional">
          <textarea className={`${inputClass} min-h-[60px] resize-y`} value={cp.style} onChange={e => setCp({ style: e.target.value })}
            placeholder="Deflects to process. Rarely commits in the room." maxLength={800} />
        </Field>
      </div>
    </div>
  );
}
