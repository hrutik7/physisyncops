"use client";

import { HelpCircle } from "lucide-react";
import { RemedyAction } from "@/lib/types";
import { IMPACT_SHARE_EXPLANATION, effortLabel, effortMeta, effortTone, remedyImpactShare } from "@/lib/decision-v2";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

function effortBarWidth(score: number) {
  if (score <= 1) return "w-1/3";
  if (score >= 3) return "w-full";
  return "w-2/3";
}

export function RemedyDifficultyChart({ remedies }: { remedies: RemedyAction[] }) {
  if (!remedies.length) return null;

  return (
    <div className="space-y-3">
      {remedies.map((remedy, index) => {
        const meta = effortMeta(remedy.effort);
        const impactShare = remedyImpactShare(remedies, remedy);

        return (
          <div key={remedy.id} className="rounded-xl border border-[#edf0f6] bg-white p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{remedy.medal}</span>
                  <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#68708a]">
                    Option {index + 1}
                  </span>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", effortTone(remedy.effort))}>
                    {effortLabel(remedy.effort)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-[#68708a]">{remedy.label}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className="inline-flex items-center justify-end gap-1 text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">
                  Impact share
                  <Tooltip side="bottom" maxWidth={320} content={<span>{IMPACT_SHARE_EXPLANATION}</span>}>
                    <span className="inline-flex cursor-help text-[#68708a]">
                      <HelpCircle size={12} />
                    </span>
                  </Tooltip>
                </p>
                <p className="text-sm font-black text-[#101426]">{impactShare}%</p>
              </div>
            </div>

            <div className="mt-3">
              <div className="mb-1 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.06em] text-[#68708a]">
                <span>Difficulty</span>
                <span>{meta.deployTime}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#edf0f6]">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    remedy.effort === "low" && "bg-[#34c759]",
                    remedy.effort === "medium" && "bg-[#f5a623]",
                    remedy.effort === "high" && "bg-[#ff3b30]",
                    effortBarWidth(meta.score)
                  )}
                />
              </div>
              <p className="mt-1.5 text-xs text-[#68708a]">{meta.complexity}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}