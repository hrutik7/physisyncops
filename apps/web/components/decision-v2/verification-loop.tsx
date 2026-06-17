"use client";

import { Brain, TrendingUp } from "lucide-react";
import { OutcomeMeasurement } from "@/lib/types";

export function VerificationLoop({ outcome }: { outcome: OutcomeMeasurement }) {
  return (
    <section className="rounded-xl border border-[#dbe7ff] bg-[#f0f5ff] p-4">
      <div className="flex items-center gap-2">
        <TrendingUp size={16} className="text-[#185be8]" />
        <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#185be8]">Verification Loop</h4>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Snapshot title="Before" data={outcome.before} />
        <Snapshot title="After" data={outcome.after} highlight />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[#dbe7ff]/80 pt-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Recovered Revenue</p>
          <p className="mt-1 text-lg font-black text-[#07824b]">{outcome.recoveredRevenueLabel}</p>
        </div>
        {outcome.decisionAccuracy != null ? (
          <div className="rounded-lg border border-[#cdbdff] bg-white px-3 py-2">
            <p className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.08em] text-[#4320c2]">
              <Brain size={12} /> AI Score
            </p>
            <p className="mt-1 text-lg font-black text-[#4320c2]">{outcome.decisionAccuracy}%</p>
            <p className="text-[11px] text-[#68708a]">Decision Accuracy</p>
          </div>
        ) : (
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Status</p>
            <p className="mt-1 text-sm font-semibold capitalize text-[#185be8]">{outcome.status.replaceAll("_", " ")}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function Snapshot({ title, data, highlight }: { title: string; data: Record<string, string>; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-3 ${highlight ? "border-[#c8f3df] bg-[#ecfff6]" : "border-[#e6e8f0] bg-white"}`}>
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">{title}</p>
      <div className="mt-2 space-y-1">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between text-xs">
            <span className="capitalize text-[#68708a]">{key.replace(/([A-Z])/g, " $1")}</span>
            <span className="font-bold text-[#101426]">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}