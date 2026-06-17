"use client";

import { RemedyAction } from "@/lib/types";
import { effortLabel, effortTone } from "@/lib/decision-v2";
import { RecoveryLabel } from "./recovery-label";
import { cn } from "@/lib/utils";

export function RemedyEffortTable({ remedies }: { remedies: RemedyAction[] }) {
  if (!remedies.length) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-[#edf0f6]">
      <table className="w-full text-left text-sm">
        <thead className="bg-[#fbfaff] text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">
          <tr>
            <th className="px-3 py-2">Remedy</th>
            <th className="px-3 py-2">Effort</th>
            <th className="px-3 py-2">Potential Value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf0f6]">
          {remedies.map((remedy) => (
            <tr key={remedy.id} className="bg-white">
              <td className="px-3 py-3 font-semibold text-[#101426]">{remedy.label}</td>
              <td className="px-3 py-3">
                <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-bold", effortTone(remedy.effort))}>
                  {effortLabel(remedy.effort)}
                </span>
              </td>
              <td className="px-3 py-3">
                <RecoveryLabel
                  value={remedy.expectedRiskReductionLabel}
                  explanation={remedy.recoveryExplanation}
                  metricLabel={remedy.recoveryLabel}
                  stacked
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}