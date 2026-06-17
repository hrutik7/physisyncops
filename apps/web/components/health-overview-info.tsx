"use client";

import { HelpCircle } from "lucide-react";
import { ScoreExplanation } from "@/lib/health-overview-math";
import { Popover } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export function ScoreExplainer({
  explanation,
  className,
  size = 14,
}: {
  explanation: ScoreExplanation;
  className?: string;
  size?: number;
}) {
  return (
    <Popover
      align="end"
      className={className}
      panelClassName="w-[min(320px,calc(100vw-2rem))]"
      trigger={
        <span
          aria-label={`Why ${explanation.title}`}
          className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[#dbe7ff] bg-[#f7faff] text-[#185be8] hover:bg-[#eef5ff] focus:outline-none focus:ring-2 focus:ring-[#cdbdff]"
        >
          <HelpCircle size={size} />
        </span>
      }
      content={<ExplanationPanel explanation={explanation} />}
    />
  );
}

export function ExplanationPanel({ explanation }: { explanation: ScoreExplanation }) {
  return (
    <div className="space-y-3 text-left">
      <div>
        <p className="text-xs font-bold text-[#101426]">{explanation.title}</p>
        <p className="mt-1 text-xs leading-5 text-[#4f5872]">{explanation.summary}</p>
      </div>

      <div className="rounded-lg border border-[#edf0f6] bg-[#fcfcff] px-3 py-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Formula</p>
        <p className="mt-1 font-mono text-[11px] leading-5 text-[#101426]">{explanation.formula}</p>
      </div>

      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Your Inputs</p>
        <ul className="mt-2 space-y-1.5">
          {explanation.inputs.map((input) => (
            <li key={`${explanation.title}-${input.label}`} className="flex items-start justify-between gap-3 text-xs">
              <span className="text-[#68708a]">{input.label}</span>
              <span className="font-semibold text-[#101426] text-right">{input.value}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-lg border border-[#d8f3e7] bg-[#f4fff9] px-3 py-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#07824b]">Result</p>
        <p className="mt-1 text-sm font-bold text-[#101426]">{explanation.result}</p>
      </div>

      {explanation.drivers?.length ? (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">What moved this</p>
          <ul className="mt-2 space-y-1">
            {explanation.drivers.map((driver) => (
              <li key={driver} className="text-xs leading-5 text-[#4f5872]">
                • {driver}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export function InlineInfoBadge({ explanation, label }: { explanation: ScoreExplanation; label?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5")}>
      {label ? <span className="text-[10px] font-bold uppercase tracking-wider text-[#68708a]">{label}</span> : null}
      <ScoreExplainer explanation={explanation} size={12} />
    </span>
  );
}