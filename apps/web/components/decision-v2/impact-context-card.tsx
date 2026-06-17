"use client";

import { HelpCircle } from "lucide-react";
import { ImpactContext } from "@/lib/types";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function ImpactContextCard({ context }: { context: ImpactContext }) {
  const hasCampaignBreakdown = Boolean(context.campaignSpendLabel && context.deliveredRevenueLabel);
  const hasStateBreakdown = Boolean(context.shippingWasteLabel && context.atRiskLabel);
  const hasInventoryBreakdown = Boolean(
    context.inventoryCoverDays !== undefined && context.dailyVelocity !== undefined
  );
  const tooltip = context.impactNarrative
    ? context.impactNarrative
    : hasInventoryBreakdown
      ? "Forecasted lost sales from stockout within the 7-day demand window — not an RTO revenue gap."
      : "Revenue at risk is the gap between placed revenue and estimated delivered revenue — not total campaign spend.";
  const atRiskHeading = context.atRiskLabel || "At-Risk Revenue";

  return (
    <section className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Why This Matters</h4>
        {context.stockoutStateLabel ? (
          <span className="rounded-full border border-[#ffd9d7] bg-[#fff1f0] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[#de2b25]">
            {context.stockoutStateLabel}
          </span>
        ) : context.operationalRiskLabel ? (
          <span className="rounded-full border border-[#ffe7ba] bg-[#fff8e8] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[#b86d00]">
            {context.operationalRiskLabel}
          </span>
        ) : null}
        {context.financialImpactLabel ? (
          <span className="rounded-full border border-[#dbe7ff] bg-[#f7faff] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[#185be8]">
            {context.financialImpactLabel}
          </span>
        ) : null}
        <Tooltip side="bottom" content={tooltip}>
          <span className="inline-flex cursor-help text-[#68708a]" aria-label="Why this matters">
            <HelpCircle size={14} />
          </span>
        </Tooltip>
      </div>
      <div className={cn("mt-4 grid gap-3", hasCampaignBreakdown || hasStateBreakdown || hasInventoryBreakdown ? "grid-cols-2" : "grid-cols-3")}>
        {hasInventoryBreakdown ? (
          <>
            <Metric label={context.contextLabel} value={context.totalRevenueLabel} tone="neutral" help={context.contextExplanation} />
            <Metric
              label="Inventory Cover"
              value={context.stockoutState === "already_stocked_out" ? "0 days" : `${context.inventoryCoverDays} days`}
              tone="neutral"
              help={`${context.inventoryLeft ?? 0} units at ${context.dailyVelocity ?? 0} units/day`}
            />
            <Metric label={context.atRiskLabel || "Expected Lost Sales"} value={context.atRiskRevenueLabel} tone="risk" help={context.atRiskExplanation} />
            <Metric label="Impact" value={`${context.impactPercent}%`} tone="impact" help="Share of the 7-day forecast expected to be lost from stockout." />
          </>
        ) : hasCampaignBreakdown ? (
          <>
            <Metric label="Campaign Spend" value={context.campaignSpendLabel!} tone="neutral" />
            <Metric label="Placed Revenue" value={context.totalRevenueLabel} tone="neutral" />
            <Metric label="Estimated Delivered Revenue" value={context.deliveredRevenueLabel!} tone="neutral" />
            <Metric label="Estimated Revenue Gap" value={context.atRiskRevenueLabel} tone="risk" />
            <Metric label="Impact" value={`${context.impactPercent}%`} tone="impact" className="col-span-2" />
          </>
        ) : hasStateBreakdown ? (
          <>
            <Metric label={context.contextLabel} value={context.totalRevenueLabel} tone="neutral" help={context.contextExplanation} />
            <Metric label={atRiskHeading} value={context.atRiskRevenueLabel} tone="risk" help={context.atRiskExplanation} />
            <Metric
              label="Estimated Shipping Waste"
              value={context.shippingWasteLabel!}
              tone="neutral"
              help={context.shippingWasteExplanation}
            />
            <Metric label="Impact" value={`${context.impactPercent}%`} tone="impact" help="Share of regional order GMV tied to RTO orders." />
          </>
        ) : (
          <>
            <Metric label={context.contextLabel} value={context.totalRevenueLabel} tone="neutral" help={context.contextExplanation} />
            <Metric label={atRiskHeading} value={context.atRiskRevenueLabel} tone="risk" help={context.atRiskExplanation} />
            <Metric label="Impact" value={`${context.impactPercent}%`} tone="impact" />
          </>
        )}
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  tone,
  className,
  help,
}: {
  label: string;
  value: string;
  tone: "neutral" | "risk" | "impact";
  className?: string;
  help?: string;
}) {
  const toneClass =
    tone === "risk" ? "text-[#de2b25]" : tone === "impact" ? "text-[#4320c2]" : "text-[#101426]";
  return (
    <div className={cn("rounded-lg border border-[#e6e8f0] bg-white px-3 py-3", className)}>
      <div className="flex items-center gap-1">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">{label}</p>
        {help ? (
          <Tooltip side="bottom" content={help}>
            <span className="inline-flex cursor-help text-[#68708a]">
              <HelpCircle size={12} />
            </span>
          </Tooltip>
        ) : null}
      </div>
      <p className={cn("mt-1 text-[17px] font-black", toneClass)}>{value}</p>
    </div>
  );
}