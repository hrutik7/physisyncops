"use client";

import { AutoResolutionCriteria } from "@/lib/types";

export function AutoResolutionCard({ criteria }: { criteria: AutoResolutionCriteria }) {
  return (
    <section className="rounded-xl border border-[#d8f3e7] bg-[#f4fff9] p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#07824b]">{criteria.headline}</h4>
      <p className="mt-2 text-sm text-[#4f5872]">{criteria.intro}</p>
      <ul className="mt-3 space-y-2">
        {criteria.criteria.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm text-[#101426]">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#07824b]" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}