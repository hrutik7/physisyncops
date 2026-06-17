"use client";

import { Decision } from "@/lib/types";
import { cn } from "@/lib/utils";

function parseMetricSignal(signal: string) {
  const colonMatch = signal.match(/^(.+?):\s*(.+)$/);
  if (colonMatch) return { label: colonMatch[1].trim(), value: colonMatch[2].trim() };
  const isMatch = signal.match(/(.*?)\s+is\s+(.*)/i);
  if (isMatch) return { label: isMatch[1].trim(), value: isMatch[2].trim() };
  return { label: "Metric", value: signal };
}

export function mathematicalInputs(decision: Decision) {
  if (decision.crossSystemSignals?.length) {
    return decision.crossSystemSignals.map(parseMetricSignal);
  }
  if (decision.whyAnalysis?.sourceFields?.length) {
    return decision.whyAnalysis.sourceFields.map((field) => ({
      label: field.field || field.source,
      value: field.value,
    }));
  }
  return [];
}

export function diagnosticImpactLabel(decision: Decision) {
  return decision.impactContext?.atRiskRevenueLabel || decision.impactLabel || "the modeled risk";
}

function impactOptimizationCopy(decision: Decision) {
  if (decision.signalType === "InventoryRisk") {
    return (
      <>
        We mapped inventory cover to forecasted demand. The estimated impact of{" "}
        <span className="font-semibold text-[#101426]">{diagnosticImpactLabel(decision)}</span> reflects forecasted revenue
        that cannot be realized if inventory remains unavailable during the projected demand window.
      </>
    );
  }
  if (decision.signalType === "StateRTOLeakage") {
    return (
      <>
        We mapped regional return pressure to order GMV. The estimated impact of{" "}
        <span className="font-semibold text-[#101426]">{diagnosticImpactLabel(decision)}</span> reflects RTO order value at
        risk in this corridor — not a daily leakage rate.
      </>
    );
  }
  return (
    <>
      We mapped the risk severity to revenue realization. The estimated impact of{" "}
      <span className="font-semibold text-[#101426]">{diagnosticImpactLabel(decision)}</span> reflects estimated revenue at
      risk based on attributed RTO-adjusted revenue realization — not a daily leakage rate.
    </>
  );
}

export function RuleConfidenceBanner({ decision, compact = false }: { decision: Decision; compact?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[#dbe7ff] bg-[#f0f5ff] flex flex-col justify-between gap-3",
        compact ? "p-3" : "p-4 md:flex-row md:items-center md:gap-4"
      )}
    >
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wider text-[#185be8]">Rule Evaluated</p>
        <code
          className={cn(
            "text-[#101426] mt-1 block font-mono bg-white/60 px-2 py-1 rounded border border-[#dbe7ff] break-all",
            compact ? "text-[11px] font-semibold" : "text-sm font-semibold w-fit"
          )}
        >
          {decision.whyAnalysis?.formula || decision.rule || "N/A"}
        </code>
      </div>
      <div className={cn(compact ? "text-left" : "text-left md:text-right shrink-0")}>
        <p className="text-xs font-semibold text-[#68708a]">Confidence Level</p>
        <p className={cn("font-black text-[#101426] mt-0.5", compact ? "text-xl" : "text-2xl")}>
          {Math.round(decision.confidenceScore * 100)}%
        </p>
      </div>
    </div>
  );
}

export function MathematicalContextSection({ decision, compact = false }: { decision: Decision; compact?: boolean }) {
  const inputs = mathematicalInputs(decision);

  return (
    <section>
      <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a] mb-3">
        {compact ? "Mathematical Context & Inputs" : "1. Mathematical Context & Inputs"}
      </h4>
      {inputs.length > 0 ? (
        <div className={cn("grid gap-3", compact ? "grid-cols-2" : "grid-cols-1 md:grid-cols-3 gap-4")}>
          {inputs.map((input, idx) => (
            <div
              key={`${input.label}-${idx}`}
              className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-3 shadow-[0_4px_12px_rgba(0,0,0,0.02)]"
            >
              <p className="text-[10px] font-medium text-[#68708a]">{input.label}</p>
              <p className={cn("font-bold text-[#101426] mt-1", compact ? "text-sm" : "text-lg")}>{input.value}</p>
            </div>
          ))}
        </div>
      ) : (
        <code className="block rounded-lg border border-[#e6e8f0] bg-[#fcfcff] px-3 py-2 text-xs font-semibold text-[#101426]">
          {decision.whyAnalysis?.formula || decision.rule}
        </code>
      )}
    </section>
  );
}

const LAUNCH_REMEDIATION_COPY =
  "Early launch performance is below target. Continue gathering delivery data while reviewing creatives, offer positioning, and audience targeting. Limit spend escalation until ROAS stabilizes.";

function launchRemediationCopy(decision: Decision) {
  const recommendation = (decision.recommendation || "").toLowerCase();
  if (
    recommendation.includes("gathering delivery data") ||
    recommendation.includes("hold spend") ||
    recommendation.includes("limit spend escalation")
  ) {
    return decision.recommendation;
  }
  return LAUNCH_REMEDIATION_COPY;
}

function parseCrossSignal(decision: Decision, prefix: string) {
  const signal = decision.crossSystemSignals?.find((entry) => entry.toLowerCase().startsWith(prefix.toLowerCase() + ":"));
  return signal?.split(":", 2)[1]?.trim();
}

function isStateMonitorCase(decision: Decision) {
  if (decision.impactContext?.actionUrgency === "monitor") return true;
  if (decision.title.includes("Regional COD Risk") || decision.title.includes("Emerging RTO Pattern")) return true;
  const delta = Number((parseCrossSignal(decision, "State RTO delta") || "0").replace("%", "").replace("+", ""));
  const cod = Number((parseCrossSignal(decision, "COD mix") || "0").replace("%", ""));
  return Math.abs(delta) <= 5 && cod >= 70;
}

function remediationNarrative(decision: Decision) {
  const isLaunch = decision.signalType === "NewLaunchRisk";
  const isInventory = decision.signalType === "InventoryRisk";
  const isStateCodRisk = decision.signalType === "StateRTOLeakage";
  const isFulfillmentGap = decision.signalType === "AudienceAudit" || Boolean(decision.metricVerification);
  const recommendedAction = isLaunch
    ? launchRemediationCopy(decision)
    : decision.recommendation || decision.recommendedActions?.[0] || "the recommended operational change";

  if (isLaunch) {
    return {
      recommendedAction,
      body: (
        <>
          Early launch performance is below target. The recommended path prioritizes data collection and measured review — not
          immediate creative pivots — until frequency and delivery signals stabilize.
        </>
      ),
    };
  }

  if (isInventory) {
    return {
      recommendedAction,
      body: (
        <>
          Inventory cover is critically low relative to recent sales velocity. Restocking is the highest-leverage action because
          pausing ads does not restore sellable units. Reduce spend only to buy time while inbound inventory is confirmed.{" "}
          <span className="font-semibold text-[#101426]">{recommendedAction}</span>
        </>
      ),
    };
  }

  if (isStateCodRisk) {
    const codMix = parseCrossSignal(decision, "COD mix") || "high COD";
    const delta = parseCrossSignal(decision, "State RTO delta");
    const monitorCase = isStateMonitorCase(decision);
    return {
      recommendedAction,
      body: monitorCase ? (
        <>
          Regional RTO is slightly above the current brand average{delta ? ` (${delta})` : ""} and coincides with {codMix} COD
          dependence. Elevated returns are observed alongside complete COD reliance, although the regional rate is only modestly
          above the blended brand average. Monitor prepaid tests before restricting shipping.{" "}
          <span className="font-semibold text-[#101426]">{recommendedAction}</span>
        </>
      ) : (
        <>
          Regional RTO runs meaningfully above brand average with heavy COD exposure. The recommended path targets prepaid
          conversion and fulfillment verification before scaling volume in this corridor.{" "}
          <span className="font-semibold text-[#101426]">{recommendedAction}</span>
        </>
      ),
    };
  }

  if (isFulfillmentGap) {
    return {
      recommendedAction,
      body: (
        <>
          Placed revenue remains healthy — the issue is fulfillment realization, not demand failure. Prioritize COD segmentation,
          verification, and geography review before pausing spend.{" "}
          <span className="font-semibold text-[#101426]">{recommendedAction}</span>
        </>
      ),
    };
  }

  return {
    recommendedAction,
    body: (
      <>
        The action &quot;{recommendedAction}&quot; was calculated as the most optimal solution. It targets the highest-leverage
        operational lever with low execution friction to secure your brand&apos;s contribution margin.
      </>
    ),
  };
}

export function DiagnosticConclusionSection({ decision, compact = false }: { decision: Decision; compact?: boolean }) {
  const { body } = remediationNarrative(decision);

  return (
    <section className="space-y-3">
      <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a]">
        {compact ? "Diagnostic Conclusion" : "2. Diagnostic Conclusion"}
      </h4>
      <div className={cn("rounded-xl border border-[#f5ebff] bg-[#faf6ff] space-y-4", compact ? "p-4" : "p-5")}>
        <div className="flex gap-3">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">1</span>
          <div>
            <h5 className="text-sm font-bold text-[#101426]">Cross-System Correlation</h5>
            <p className={cn("text-[#4f5872] mt-1", compact ? "text-xs leading-5" : "text-sm")}>{decision.explanation}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">2</span>
          <div>
            <h5 className="text-sm font-bold text-[#101426]">Impact Optimization Model</h5>
            <p className={cn("text-[#4f5872] mt-1", compact ? "text-xs leading-5" : "text-sm")}>
              {impactOptimizationCopy(decision)}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">3</span>
          <div>
            <h5 className="text-sm font-bold text-[#101426]">Prescribed Remediation</h5>
            <p className={cn("text-[#4f5872] mt-1", compact ? "text-xs leading-5" : "text-sm")}>{body}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function RootCauseAnalysis({ decision, compact = false }: { decision: Decision; compact?: boolean }) {
  return (
    <div className={cn("space-y-5", !compact && "space-y-6")}>
      <RuleConfidenceBanner decision={decision} compact={compact} />
      <MathematicalContextSection decision={decision} compact={compact} />
      <DiagnosticConclusionSection decision={decision} compact={compact} />
    </div>
  );
}