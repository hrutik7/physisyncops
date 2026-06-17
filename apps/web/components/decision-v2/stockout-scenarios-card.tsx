"use client";

import { StockoutScenarioAnalysis } from "@/lib/types";

export function StockoutScenariosCard({ analysis }: { analysis: StockoutScenarioAnalysis }) {
  return (
    <section className="rounded-xl border border-[#ffe7ba] bg-[#fffaf0] p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#b86d00]">{analysis.headline}</h4>
      <div className="mt-3 space-y-3">
        {analysis.scenarios.map((scenario) => (
          <div key={scenario.label} className="rounded-lg border border-[#ffe7ba] bg-white px-3 py-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-bold text-[#101426]">{scenario.label}</p>
                <p className="mt-1 text-xs text-[#68708a]">{scenario.detail}</p>
              </div>
              <p className="text-sm font-black text-[#de2b25]">{scenario.estimatedLostSalesLabel}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}