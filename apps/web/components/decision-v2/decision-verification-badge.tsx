"use client";

import { DecisionVerification } from "@/lib/types";
import { cn } from "@/lib/utils";

export function DecisionVerificationBadge({ verification }: { verification: DecisionVerification }) {
  const isEstimated = verification.type === "estimated";

  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2",
        isEstimated ? "border-[#ffe7ba] bg-[#fff8e8]" : "border-[#c8f3df] bg-[#ecfff6]"
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm leading-none">{isEstimated ? "🟠" : "🟢"}</span>
        <div>
          <p className={cn("text-xs font-bold uppercase tracking-[0.08em]", isEstimated ? "text-[#b86d00]" : "text-[#07824b]")}>
            Decision Type: {verification.label}
          </p>
          <p className="mt-1 text-[11px] leading-5 text-[#68708a]">{verification.reason}</p>
        </div>
      </div>
    </div>
  );
}