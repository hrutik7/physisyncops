"use client";

import { Check, AlertTriangle, HelpCircle } from "lucide-react";
import { ConfidenceDriver, MetricVerificationStatus } from "@/lib/types";
import { MetricVerificationCard } from "./metric-verification-card";
import { Popover } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

const statusIcon = {
  verified: { icon: Check, className: "text-[#07824b]" },
  inferred: { icon: AlertTriangle, className: "text-[#c27803]" },
  warning: { icon: AlertTriangle, className: "text-[#c27803]" },
};

function DriverList({ drivers }: { drivers: ConfidenceDriver[] }) {
  return (
    <ul className="space-y-2">
      {drivers.map((driver) => {
        const meta = statusIcon[driver.status];
        const Icon = meta.icon;
        return (
          <li key={driver.label} className="flex items-start gap-2 text-sm">
            <Icon size={15} className={cn("mt-0.5 shrink-0", meta.className)} />
            <div>
              <p className="font-semibold text-[#101426]">{driver.label}</p>
              <p className="text-xs text-[#68708a]">{driver.detail}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function ConfidenceDriversDetail({
  score,
  drivers,
  metricVerification,
}: {
  score: number;
  drivers: ConfidenceDriver[];
  metricVerification?: MetricVerificationStatus;
}) {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
        <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Confidence Drivers</h4>
        <div className="mt-3">
          <DriverList drivers={drivers} />
        </div>
        <div className="mt-4 rounded-lg bg-[#f7f5ff] px-3 py-2 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Confidence</p>
          <p className="text-2xl font-black text-[#101426]">{Math.round(score * 100)}%</p>
        </div>
      </section>
      {metricVerification ? <MetricVerificationCard status={metricVerification} /> : null}
    </div>
  );
}

export function ConfidenceDriversPanel({
  score,
  drivers,
}: {
  score: number;
  drivers: ConfidenceDriver[];
}) {
  return (
    <Popover
      align="end"
      trigger={
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-lg border border-[#e6e8f0] bg-white px-3 py-1.5 text-sm font-semibold text-[#101426] hover:border-[#cdbdff] hover:bg-[#faf8ff]"
        >
          {Math.round(score * 100)}%
          <HelpCircle size={15} className="text-[#68708a]" />
        </button>
      }
      content={
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-[#68708a]">Confidence Drivers</p>
          <div className="mt-3">
            <DriverList drivers={drivers} />
          </div>
          <div className="mt-4 rounded-lg bg-[#f7f5ff] px-3 py-2 text-center">
            <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Confidence</p>
            <p className="text-2xl font-black text-[#101426]">{Math.round(score * 100)}%</p>
          </div>
        </div>
      }
    />
  );
}