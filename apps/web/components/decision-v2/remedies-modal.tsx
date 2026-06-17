"use client";

import { X, Zap, Clock3, TrendingDown } from "lucide-react";
import { Decision, RemedyAction } from "@/lib/types";
import { effortLabel, effortTone } from "@/lib/decision-v2";
import { RecoveryLabel } from "./recovery-label";
import { RemedyEffortTable } from "./remedy-effort-table";
import { cn } from "@/lib/utils";

function OutcomePreview({ remedy }: { remedy: RemedyAction }) {
  const entries = Object.entries(remedy.expectedOutcome).filter(
    ([key, value]) => key !== "recovery" && typeof value === "object" && value !== null && "before" in value
  ) as [string, { before: string; after: string }][];

  if (!entries.length) return null;

  return (
    <div className="mt-3 space-y-1.5 rounded-lg border border-[#edf0f6] bg-[#fcfcff] p-3">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center justify-between text-xs">
          <span className="font-medium capitalize text-[#68708a]">{key.replace(/([A-Z])/g, " $1").trim()}</span>
          <span className="font-semibold text-[#101426]">
            {value.before} <span className="text-[#68708a]">→</span> {value.after}
          </span>
        </div>
      ))}
    </div>
  );
}

export function RemediesModal({
  decision,
  remedies,
  selectedRemedyId,
  onClose,
  onSelect,
}: {
  decision: Decision;
  remedies: RemedyAction[];
  selectedRemedyId?: string | null;
  onClose: () => void;
  onSelect: (remedy: RemedyAction) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm">
      <div className="relative flex max-h-[88vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[#ebe8f5] bg-white shadow-[0_25px_80px_-15px_rgba(0,0,0,0.28)]">
        <div className="flex items-start justify-between border-b border-[#edf0f6] bg-[#fbfaff] px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.08em] text-[#4320c2]">Choose Action</p>
            <h3 className="mt-1 text-lg font-bold text-[#101426]">{decision.title}</h3>
            <p className="mt-1 text-sm text-[#68708a]">Compare remedies by effort, expected recovery, and operational fit.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="grid h-9 w-9 place-items-center rounded-xl border border-[#edf0f6] bg-white text-[#68708a] hover:bg-[#f7f5ff]"
          >
            <X size={18} />
          </button>
        </div>

        <div className="thin-scrollbar flex-1 space-y-4 overflow-y-auto p-6">
          {remedies.map((remedy) => {
            const selected = selectedRemedyId === remedy.id;
            return (
              <button
                key={remedy.id}
                type="button"
                onClick={() => onSelect(remedy)}
                className={cn(
                  "w-full rounded-xl border p-4 text-left transition hover:border-[#cdbdff] hover:bg-[#faf8ff]",
                  selected ? "border-[#5b35d5] bg-[#faf8ff] shadow-[0_8px_24px_rgba(91,53,213,0.08)]" : "border-[#e6e8f0] bg-white"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-base">{remedy.medal}</span>
                      <span className="text-xs font-bold uppercase tracking-[0.08em] text-[#4320c2]">
                        {remedy.rank === "primary" ? "Primary" : "Alternative"}
                      </span>
                      <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-bold", effortTone(remedy.effort))}>
                        {effortLabel(remedy.effort)} effort
                      </span>
                    </div>
                    <p className="mt-2 text-[15px] font-semibold leading-6 text-[#101426]">{remedy.label}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#68708a]">
                      {remedy.recoveryLabel || "Potential Value"}
                    </p>
                    <p className="mt-1 text-lg font-black">
                      <RecoveryLabel value={remedy.expectedRiskReductionLabel} explanation={remedy.recoveryExplanation} />
                    </p>
                  </div>
                </div>

                <OutcomePreview remedy={remedy} />

                <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-[#68708a]">
                  <span className="inline-flex items-center gap-1.5">
                    <Clock3 size={14} />
                    {effortLabel(remedy.effort)} execution cost
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <TrendingDown size={14} />
                    {remedy.recoveryLabel || "Potential value"} {remedy.expectedRiskReductionLabel}
                  </span>
                </div>
              </button>
            );
          })}
          <div className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
            <h4 className="text-xs font-bold uppercase tracking-[0.08em] text-[#68708a]">Action Difficulty</h4>
            <p className="mt-1 text-xs text-[#68708a]">Compare impact against execution effort before committing.</p>
            <div className="mt-3">
              <RemedyEffortTable remedies={remedies} />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-[#edf0f6] bg-[#fbfaff] px-6 py-4">
          <p className="text-xs text-[#68708a]">
            <Zap size={14} className="mr-1 inline text-[#4320c2]" />
            Selecting a remedy moves the decision to <strong>Action Planned</strong>.
          </p>
          <button type="button" onClick={onClose} className="rounded-lg border border-[#e6e8f0] bg-white px-4 py-2 text-sm font-semibold text-[#172039]">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}