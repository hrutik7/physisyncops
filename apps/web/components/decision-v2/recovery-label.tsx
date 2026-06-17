"use client";

import { HelpCircle } from "lucide-react";
import { DEFAULT_RECOVERY_EXPLANATION } from "@/lib/decision-v2";
import { Tooltip } from "@/components/ui/tooltip";

export function RecoveryLabel({
  value,
  explanation = DEFAULT_RECOVERY_EXPLANATION,
  metricLabel,
  className,
  stacked = false,
}: {
  value: string;
  explanation?: string;
  metricLabel?: string;
  className?: string;
  stacked?: boolean;
}) {
  const content = (
    <>
      {metricLabel ? (
        <span className={stacked ? "block text-[10px] font-semibold uppercase tracking-[0.06em] text-[#68708a]" : "mr-1.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-[#68708a]"}>
          {metricLabel}
        </span>
      ) : null}
      <span className="font-bold text-[#07824b]">{value}</span>
      <Tooltip side="bottom" content={<span>{explanation}</span>}>
        <span className="ml-1.5 inline-flex cursor-help align-middle text-[#68708a]">
          <HelpCircle size={13} />
        </span>
      </Tooltip>
    </>
  );

  return (
    <span className={className}>
      {stacked ? <span className="inline-flex flex-col items-start gap-0.5">{content}</span> : content}
    </span>
  );
}