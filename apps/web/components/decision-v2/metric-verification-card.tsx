"use client";

import { Check, AlertTriangle } from "lucide-react";
import { MetricVerificationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function MetricVerificationCard({ status }: { status: MetricVerificationStatus }) {
  return (
    <section className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">{status.headline}</h4>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <MetricGroup
          title={status.observedLabel}
          items={status.observed}
          tone="observed"
        />
        <MetricGroup
          title={status.estimatedLabel}
          items={status.estimated}
          tone="estimated"
        />
      </div>
    </section>
  );
}

function MetricGroup({
  title,
  items,
  tone,
}: {
  title: string;
  items: { label: string; detail?: string }[];
  tone: "observed" | "estimated";
}) {
  const Icon = tone === "observed" ? Check : AlertTriangle;
  const iconClass = tone === "observed" ? "text-[#07824b]" : "text-[#c27803]";
  const boxClass =
    tone === "observed" ? "border-[#c8f3df] bg-[#ecfff6]" : "border-[#ffe7ba] bg-[#fff8e8]";

  return (
    <div className={cn("rounded-lg border p-3", boxClass)}>
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">{title}</p>
      <ul className="mt-2 space-y-2">
        {items.map((item) => (
          <li key={item.label} className="flex items-start gap-2 text-sm">
            <Icon size={14} className={cn("mt-0.5 shrink-0", iconClass)} />
            <div>
              <p className="font-semibold text-[#101426]">{item.label}</p>
              {item.detail ? <p className="text-xs text-[#68708a]">{item.detail}</p> : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}