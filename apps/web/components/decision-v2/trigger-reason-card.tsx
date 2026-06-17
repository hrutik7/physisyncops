"use client";

import { TriggerReason } from "@/lib/types";

export function TriggerReasonCard({ trigger }: { trigger: TriggerReason }) {
  return (
    <section className="rounded-xl border border-[#dbe7ff] bg-[#f7faff] p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#185be8]">{trigger.headline}</h4>
      <div className="mt-3 grid grid-cols-2 gap-3">
        {trigger.metrics.map((metric) => (
          <div key={metric.label} className="rounded-lg border border-[#dbe7ff] bg-white px-3 py-2">
            <p className="text-[10px] font-medium text-[#68708a]">{metric.label}</p>
            <p className="mt-1 text-sm font-bold text-[#101426]">{metric.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}