"use client";
import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { endSession } from "@/lib/api";
import type { SessionEndResponse } from "@/lib/api";

export default function ResultContent() {
  const router = useRouter();
  const sessionId = useSearchParams().get("id");
  const [result, setResult] = useState<SessionEndResponse|null>(null);
  const [local, setLocal] = useState<{status:string;score:number}|null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const s = sessionStorage.getItem("patchup_result");
    if (s) setLocal(JSON.parse(s));
    if (sessionId) endSession(sessionId).then(setResult).catch(()=>{}).finally(() => setLoading(false));
    else setLoading(false);
  }, [sessionId]);

  const score = result?.final_score ?? local?.score ?? 0;

  const v = score >= 90
    ? { emoji:"🎉", title:"PATCHED UP!", sub:"She forgave you! You smooth talker.", color:"text-green-400", border:"border-green-400/20" }
    : score >= 70
    ? { emoji:"😊", title:"Almost There!", sub:"She's softening up, but you ran out of time.", color:"text-amber-400", border:"border-amber-400/20" }
    : score >= 40
    ? { emoji:"😐", title:"Still Naraaz", sub:"You tried, but she's not impressed.", color:"text-orange-400", border:"border-orange-400/20" }
    : score >= 20
    ? { emoji:"😤", title:"Made It Worse", sub:"You somehow managed to make things worse.", color:"text-red-400", border:"border-red-400/20" }
    : { emoji:"💔", title:"BLOCKED", sub:"She's done. Gone. Blocked. Deleted.", color:"text-red-500", border:"border-red-500/20" };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-2 border-patch-accent border-t-transparent rounded-full" /></div>;

  return (
    <main className="min-h-screen px-4 py-8 max-w-lg mx-auto">
      <div className="text-center mb-10 animate-slide-up">
        <div className="text-7xl mb-4">{v.emoji}</div>
        <h1 className={`font-display text-4xl font-bold ${v.color}`}>{v.title}</h1>
        <p className="text-sm text-patch-soft/50 mt-2">{v.sub}</p>
      </div>

      <div className={`glass-card rounded-2xl p-6 mb-6 text-center ${v.border} animate-slide-up`} style={{animationDelay:"0.1s"}}>
        <div className="text-xs text-patch-soft/40 uppercase tracking-wider mb-2">Final Score</div>
        <div className={`font-display text-6xl font-bold ${v.color}`}>{score}%</div>
        {result && <div className="text-sm text-patch-soft/50 mt-2">{result.total_turns} turn{result.total_turns !== 1 ? "s" : ""}</div>}
      </div>

      {result && (result.best_response || result.worst_response) && (
        <div className="space-y-3 mb-6 animate-slide-up" style={{animationDelay:"0.2s"}}>
          {result.best_response && (
            <div className="glass-card rounded-xl p-4">
              <div className="text-[10px] text-green-400/60 uppercase tracking-wider mb-1">✅ Your best move</div>
              <p className="text-sm text-patch-soft/80 italic">&quot;{result.best_response}&quot;</p>
            </div>
          )}
          {result.worst_response && (
            <div className="glass-card rounded-xl p-4">
              <div className="text-[10px] text-red-400/60 uppercase tracking-wider mb-1">❌ Your worst move</div>
              <p className="text-sm text-patch-soft/80 italic">&quot;{result.worst_response}&quot;</p>
            </div>
          )}
        </div>
      )}

      {result?.tips && result.tips.length > 0 && (
        <div className="glass-card rounded-2xl p-5 mb-6 animate-slide-up" style={{animationDelay:"0.3s"}}>
          <h3 className="font-display text-sm text-patch-soft/50 uppercase tracking-wider mb-3">💡 What you should have said</h3>
          <div className="space-y-2">
            {result.tips.map((tip, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-patch-accent text-xs mt-1">•</span>
                <p className="text-sm text-patch-soft/70">{tip}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3 animate-slide-up" style={{animationDelay:"0.4s"}}>
        <button onClick={() => router.push("/setup")} className="w-full py-4 bg-patch-accent rounded-2xl font-body font-semibold text-white text-lg hover:bg-patch-accent/90 transition-all hover:scale-[1.02] active:scale-[0.98]">
          Try Again 🔄
        </button>
        <button onClick={() => router.push("/")} className="w-full py-3 bg-patch-card border border-patch-border rounded-2xl font-body text-patch-soft/60 text-sm hover:border-patch-accent/30 transition-all">
          Back to Home
        </button>
      </div>

      <div className="text-center mt-8 animate-slide-up" style={{animationDelay:"0.5s"}}>
        <div className="inline-block px-4 py-2 bg-patch-card border border-patch-border rounded-full">
          <span className="text-xs text-patch-soft/40">Share your score! 🩹 #TheMicIsYours @SarvamAI</span>
        </div>
      </div>
      <div className="text-center mt-6 text-[10px] text-patch-soft/20">Powered by Sarvam Bulbul V3 🇮🇳</div>
    </main>
  );
}
