"use client";

import { useState } from "react";
import { ArrowRight, Check, Circle, Eye, PackageOpen, TrendingUp, X } from "lucide-react";
import { useOpentraStore } from "@/store/use-opentra-store";
import { Decision, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Pill } from "./ui";

const iconBySignal = {
  InventoryRisk: PackageOpen,
  CreativeFatigue: TrendingUp,
  MarginLeakage: TrendingUp,
  CampaignRTOSpike: TrendingUp,
  ScalingOpportunity: TrendingUp
};

const severityCopy: Record<Severity, string> = {
  high: "CRITICAL",
  medium: "MEDIUM",
  low: "OPPORTUNITY"
};

const severityTone: Record<Severity, string> = {
  high: "border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]",
  medium: "border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]",
  low: "border-[#c8f3df] bg-[#ecfff6] text-[#07824b]"
};

const defaultExecutionSignals = [
  { label: "Ad spend reduced by >15%", progress: 84, done: true },
  { label: "Velar reorder placed", progress: 0, done: false },
  { label: "Inventory incoming", progress: 0, done: false },
  { label: "Stockout projected days improved", progress: 88, done: true },
  { label: "Sales velocity normalized", progress: 0, done: false }
];

function compactImpact(decision: Decision) {
  if (decision.id === "dec_campaign_rto_spike") return "Rs 6.2K/day margin loss";
  if (decision.id === "dec_inventory_risk") return "Rs 1.48L revenue at risk";
  if (decision.id === "dec_creative_fatigue") return "Rs 28K efficiency loss";
  if (decision.id === "dec_scaling_opportunity") return "Rs 1.16L upside";
  return decision.impactLabel;
}

export function AnalysisPanel() {
  const decision = useOpentraStore((state) => state.selectedDecision());
  const setSelectedDecision = useOpentraStore((state) => state.setSelectedDecision);
  const [showModal, setShowModal] = useState(false);

  if (!decision) {
    return (
      <aside className="hidden lg:flex h-screen items-center justify-center border-l border-[#ebe8f5] bg-white p-6 text-center text-sm text-[#68708a]">
        Select a decision from the feed to view deeper analysis.
      </aside>
    );
  }
  const Icon = iconBySignal[decision.signalType as keyof typeof iconBySignal] || PackageOpen;
  const executionSignals = decision.verificationScorecard?.metrics?.length
    ? decision.verificationScorecard.metrics.map((metric) => ({
        label: metric.label,
        progress: decision.verificationScorecard?.status === "successful" ? 100 : 0,
        done: decision.verificationScorecard?.status === "successful"
      }))
    : defaultExecutionSignals;

  return (
    <aside className="thin-scrollbar h-screen overflow-y-auto border-l border-[#ebe8f5] bg-white p-4">
      <div className="rounded-xl border border-[#e6e8f0] bg-white shadow-[0_18px_55px_rgba(38,35,64,0.06)]">
        <div className="flex items-center justify-between border-b border-[#edf0f6] px-4 py-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#101426]">Decision Details</h2>
            <button
              type="button"
              aria-label="View Full Analysis"
              title="View Full Analysis"
              onClick={() => setShowModal(true)}
              className="grid h-8 w-8 place-items-center rounded-lg text-[#68708a] hover:bg-[#f7f5ff] hover:text-[#4320c2] transition-colors animate-in fade-in duration-200"
            >
              <Eye size={18} />
            </button>
          </div>
          <button
            type="button"
            aria-label="Close details"
            title="Close details"
            onClick={() => setSelectedDecision("")}
            className="grid h-8 w-8 place-items-center rounded-lg text-[#68708a] hover:bg-[#f7f5ff]"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className={cn("grid h-12 w-12 place-items-center rounded-lg border", severityTone[decision.severity])}>
              <Icon size={23} />
            </div>
            <div className="min-w-0">
              <Pill className={severityTone[decision.severity]}>{severityCopy[decision.severity]}</Pill>
              <h3 className="mt-3 text-[17px] font-semibold leading-6 text-[#101426]">{decision.title}</h3>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-[#4f5872]">{decision.explanation}</p>

          <div className="mt-5 space-y-4 border-y border-[#edf0f6] py-4">
            <DetailRow label="Potential Impact" value={compactImpact(decision)} />
            <DetailRow label="Confidence" value={`${Math.round(decision.confidenceScore * 100)}%`} />
            <DetailRow label="Goal Alignment" value={decision.whyAnalysis?.goalAlignment?.replaceAll("_", " ") || "margin"} />
            <DetailRow label="Action Object" value={decision.intervention ? `${decision.intervention.actionType.replaceAll("_", " ")} / ${decision.intervention.status}` : "recommended"} />
            <DetailRow label="Recommended Action" value={decision.recommendation} />
            <DetailRow label="Detected" value={decision.timestamp === "10:02 AM" ? "2h ago" : decision.timestamp} />
          </div>

          <section className="mt-5 rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
            <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Why This Decision?</h4>
            <div className="mt-3 space-y-3">
              <div>
                <p className="text-xs font-semibold text-[#68708a]">Formula</p>
                <code className="mt-1 block rounded-lg border border-[#e6e8f0] bg-white px-3 py-2 text-xs font-semibold text-[#101426]">
                  {decision.whyAnalysis?.formula || decision.rule}
                </code>
              </div>
              <div className="grid gap-2">
                {(decision.whyAnalysis?.sourceFields || []).slice(0, 4).map((field, idx) => (
                  <div key={`${field.field}-${idx}`} className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-xs">
                    <span className="font-medium text-[#4f5872]">{field.source}</span>
                    <span className="text-right font-semibold text-[#101426]">{field.value}</span>
                  </div>
                ))}
              </div>
              {decision.verificationScorecard ? (
                <div className="rounded-lg border border-[#dbe7ff] bg-[#f0f5ff] px-3 py-2 text-xs text-[#185be8]">
                  Verification scorecard: <span className="font-bold">{decision.verificationScorecard.status}</span>
                  {decision.verificationScorecard.summary ? ` - ${decision.verificationScorecard.summary}` : ""}
                </div>
              ) : null}
            </div>
          </section>

          <section className="mt-5">
            <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Status Timeline</h4>
            <div className="mt-4 space-y-0">
              <TimelineStep 
                title="Pending" 
                description="AI generated this decision" 
                time={decision.timestamp || "2h ago"} 
                done={decision.state !== "pending"} 
                active={decision.state === "pending"} 
              />
              <TimelineStep 
                title="Acknowledged" 
                description="Marked by Operator" 
                time={decision.state !== "pending" ? "Just now" : ""} 
                done={decision.state !== "pending"} 
                active={false} 
                avatar="HK" 
              />
              <TimelineStep 
                title="Monitoring" 
                description="Tracking execution signals" 
                time={decision.state === "monitoring" ? "Current" : ""} 
                active={decision.state === "monitoring"} 
                done={["verified", "successful", "unsuccessful"].includes(decision.state)}
              />
              <TimelineStep 
                title="Verified" 
                description="Waiting for signal confirmation" 
                active={decision.state === "verified"}
                done={["successful", "unsuccessful"].includes(decision.state)}
              />
              <TimelineStep 
                title="Evaluating Impact" 
                description="Measuring outcome vs expected" 
                active={decision.state === "verified"}
                done={["successful", "unsuccessful"].includes(decision.state)}
              />
              <TimelineStep 
                title={decision.state === "successful" ? "Successful" : decision.state === "unsuccessful" ? "Unsuccessful" : "Successful / Unsuccessful"} 
                description="Outcome determined" 
                active={["successful", "unsuccessful"].includes(decision.state)}
                done={["successful", "unsuccessful"].includes(decision.state)}
                last 
              />
            </div>
          </section>

          {decision.state === "successful" && (
            <div className="mt-5 rounded-xl border border-[#d8f2e6] bg-[#ecfff6] p-4 shadow-[0_4px_16px_rgba(7,130,75,0.04)] animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex items-center gap-2">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-[#07824b] text-white">
                  <Check size={12} />
                </span>
                <span className="text-[10px] font-bold text-[#07824b] uppercase tracking-wider">Impact Averted & Realized</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-4 border-t border-[#d8f2e6]/50 pt-3 text-center">
                <div>
                  <p className="text-[10px] font-bold text-[#68708a] uppercase tracking-wider">Claimed Risk</p>
                  <p className="text-[15px] font-black text-[#de2b25] mt-0.5">{compactImpact(decision)}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-[#68708a] uppercase tracking-wider">Actual Saved</p>
                  <p className="text-[15px] font-black text-[#07824b] mt-0.5">
                    {decision.title.toLowerCase().includes("stockout") ? "Rs 1.48L" : "Rs 6.2K/day"}
                  </p>
                </div>
              </div>
              <p className="text-[11px] text-[#05663b] mt-3 bg-white/60 p-2.5 rounded-lg border border-[#d8f2e6] leading-relaxed font-medium">
                <strong>Closed-Loop Saved:</strong> PhysiSync verified that your systems successfully enacted the recommended mitigation, locking in 100% of the target profit.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-[#e6e8f0] bg-white p-4 shadow-[0_18px_55px_rgba(38,35,64,0.06)]">
        <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Verification Scorecard</h4>
        <div className="mt-4 space-y-4">
          {executionSignals.map((signal) => (
            <div key={signal.label} className="grid grid-cols-[1fr_20px] items-center gap-3">
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold text-[#172039]">{signal.label}</p>
                </div>
                <div className="h-1.5 rounded-full bg-[#edf0f6]">
                  <div className="h-1.5 rounded-full bg-[#0fb36b]" style={{ width: `${signal.progress}%` }} />
                </div>
              </div>
              {signal.done ? (
                <span className="grid h-5 w-5 place-items-center rounded-full bg-[#22c55e] text-white">
                  <Check size={13} />
                </span>
              ) : (
                <Circle size={18} className="text-[#c8ceda]" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Premium Analysis Diagnostic Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md transition-all duration-200">
          <div className="relative w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border border-[#ebe8f5] bg-white/95 shadow-[0_25px_80px_-15px_rgba(0,0,0,0.3)] overflow-hidden transition-all duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#edf0f6] bg-[#fbfaff] px-6 py-5">
              <div className="flex items-center gap-3">
                <div className={cn("grid h-10 w-10 place-items-center rounded-lg border", severityTone[decision.severity])}>
                  <Icon size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#101426]">{decision.title}</h3>
                  <p className="text-xs text-[#68708a] mt-0.5">Root-Cause Analysis & Decision Matrix</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="grid h-9 w-9 place-items-center rounded-xl border border-[#edf0f6] bg-white text-[#68708a] hover:bg-[#f7f5ff]"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="thin-scrollbar flex-1 overflow-y-auto p-6 space-y-6">
              {/* Rule & Confidence Banner */}
              <div className="rounded-xl border border-[#dbe7ff] bg-[#f0f5ff] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[#185be8]">Rule Evaluated</p>
                  <code className="text-sm font-semibold text-[#101426] mt-1 block font-mono bg-white/60 px-2 py-1 rounded border border-[#dbe7ff] w-fit">
                    {decision.rule || "N/A"}
                  </code>
                </div>
                <div className="text-left md:text-right">
                  <p className="text-xs font-semibold text-[#68708a]">Confidence Level</p>
                  <p className="text-2xl font-black text-[#101426] mt-0.5">{Math.round(decision.confidenceScore * 100)}%</p>
                </div>
              </div>

              {/* Step-by-Step Mathematical Conclusion */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a] mb-3">1. Mathematical Context & Inputs</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {decision.crossSystemSignals?.map((signalStr: string, idx: number) => {
                    const match = signalStr.match(/(.*?)\s+is\s+(.*)/i) || [null, "Metric", signalStr];
                    const label = match[1] || "Observation";
                    const val = match[2] || signalStr;
                    return (
                      <div key={idx} className="rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4 shadow-[0_4px_12px_rgba(0,0,0,0.02)]">
                        <p className="text-xs font-medium text-[#68708a]">{label}</p>
                        <p className="text-lg font-bold text-[#101426] mt-1">{val}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Why we came to this conclusion */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a]">2. Diagnostic Conclusion</h4>
                <div className="rounded-xl border border-[#f5ebff] bg-[#faf6ff] p-5 space-y-4">
                  <div className="flex gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">1</span>
                    <div>
                      <h5 className="text-sm font-bold text-[#101426]">Cross-System Correlation</h5>
                      <p className="text-sm text-[#4f5872] mt-1">
                        PhysiSync identified that {decision.title.toLowerCase().includes("stockout")
                          ? "elevated traffic and marketing spend growth intersect critically with limited product availability on Shopify. This creates a high risk of burning budget on advertising out-of-stock inventory."
                          : decision.signalType === "CreativeFatigue"
                            ? "ad exposure frequency has crossed the fatigue threshold while a supported CTR decay signal is present. This points to creative saturation rather than a logistics or RTO issue."
                            : "specific marketing campaigns are driving disproportionate Cash on Delivery (COD) order count on paper, but an alarming ratio of these are returning (RTO) before final delivery."
                        }
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">2</span>
                    <div>
                      <h5 className="text-sm font-bold text-[#101426]">Impact Optimization Model</h5>
                      <p className="text-sm text-[#4f5872] mt-1">
                        We mapped the risk severity to potential loss. The calculated impact of **{compactImpact(decision)}** represents the daily baseline leakage or absolute revenue-at-risk based on order velocities over the last 7 days.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#f0ebff] text-xs font-bold text-[#4320c2]">3</span>
                    <div>
                      <h5 className="text-sm font-bold text-[#101426]">Prescribed Remediation</h5>
                      <p className="text-sm text-[#4f5872] mt-1">
                        The action &quot;{decision.recommendation}&quot; was calculated as the most optimal solution. It targets the highest-leverage operational lever with low execution friction to instantly secure your brand&apos;s contribution margin.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Expected vs. Actual Impact Realization Section */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a]">3. Expected vs. Actual Impact Realization</h4>
                <div className={cn("rounded-xl border p-5 transition-all duration-300", 
                  decision.state === "successful" 
                    ? "border-[#d8f2e6] bg-[#ecfff6]/35" 
                    : "border-[#e6e8f0] bg-[#fbfaff]"
                )}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className={cn("h-2.5 w-2.5 rounded-full", decision.state === "successful" ? "bg-[#0fb36b] animate-ping" : "bg-[#b86d00] animate-pulse")} />
                        <span className="text-[11px] font-bold text-[#101426] uppercase tracking-wider">
                          {decision.state === "successful" ? "Verification Completed (Closed-Loop Saved)" : "Verification Pending (Active Monitoring)"}
                        </span>
                      </div>
                      <p className="text-xs text-[#4f5872] mt-2 leading-relaxed">
                        {decision.state === "successful"
                          ? "The recommended operational action has been successfully processed in your connected systems. The margin risk has been averted, converting potential leakage directly into realized saved profit."
                          : "We are currently tracking your connected data sources. Once the recommended changes (spend drop or inventory adjustment) are detected in your data preset, this audit will calculate and lock in the saved margin."
                        }
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 border-l border-[#e6e8f0]/80 pl-6 text-center">
                      <div>
                        <p className="text-[10px] font-bold text-[#68708a] uppercase tracking-wider">Claimed Risk</p>
                        <p className="text-lg font-black text-[#de2b25] mt-1">{compactImpact(decision)}</p>
                        <span className="text-[10px] text-[#68708a] block mt-0.5 font-medium">Potential Leakage</span>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-[#68708a] uppercase tracking-wider">Actual Averted</p>
                        <p className={cn("text-lg font-black mt-1", decision.state === "successful" ? "text-[#07824b]" : "text-[#b86d00]")}>
                          {decision.state === "successful" 
                            ? (decision.title.toLowerCase().includes("stockout") ? "Rs 1.48L" : "Rs 6.2K/day")
                            : "Rs 0"
                          }
                        </p>
                        <span className="text-[10px] text-[#68708a] block mt-0.5 font-medium">
                          {decision.state === "successful" ? "Realized Savings (100%)" : "Awaiting Verification"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Projection Details */}
              {decision.riskProjection && decision.riskProjection.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a] mb-3">3. Risk Projections (If Unresolved)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {decision.riskProjection.map((proj: any, idx: number) => (
                      <div key={idx} className="rounded-xl border border-dashed border-[#e6e8f0] p-4 bg-[#fbfaff]">
                        <span className="inline-block rounded-md bg-[#fff1f0] px-2 py-0.5 text-xs font-bold text-[#de2b25]">
                          {proj.horizon}
                        </span>
                        <p className="text-sm font-semibold text-[#101426] mt-2">{proj.impact}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="border-t border-[#edf0f6] bg-[#fbfaff] px-6 py-4 flex justify-end">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="rounded-lg bg-[#4320c2] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#3417a2]"
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[128px_1fr] gap-4 text-sm">
      <span className="text-[#68708a]">{label}</span>
      <span className="font-semibold leading-6 text-[#101426]">{value}</span>
    </div>
  );
}

function TimelineStep({
  title,
  description,
  time,
  done,
  active,
  avatar,
  last
}: {
  title: string;
  description: string;
  time?: string;
  done?: boolean;
  active?: boolean;
  avatar?: string;
  last?: boolean;
}) {
  return (
    <div className={cn("grid grid-cols-[28px_1fr] gap-3", active && "rounded-lg bg-[#f3f0ff] py-3 pr-3")}>
      <div className="flex flex-col items-center">
        {avatar ? (
          <span className="grid h-5 w-5 place-items-center rounded-full bg-[#f0eff6] text-[9px] font-bold text-[#101426]">{avatar}</span>
        ) : (
          <span
            className={cn(
              "mt-0.5 grid h-4 w-4 place-items-center rounded-full border",
              active ? "border-[#3457f4] bg-[#3457f4]" : done ? "border-[#0fb36b] bg-[#0fb36b]" : "border-[#b9c0cf] bg-white"
            )}
          >
            {(active || done) && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
          </span>
        )}
        {!last ? <span className="mt-1 h-10 w-px bg-[#dfe3ec]" /> : null}
      </div>
      <div className="min-w-0 pb-3">
        <div className="flex items-center justify-between gap-3">
          <p className={cn("text-sm font-semibold", active ? "text-[#3150d8]" : "text-[#303954]")}>{title}</p>
          {time ? <span className={cn("text-xs", active ? "text-[#3150d8]" : "text-[#68708a]")}>{time}</span> : null}
        </div>
        <p className="mt-1 text-xs leading-5 text-[#68708a]">{description}</p>
      </div>
    </div>
  );
}
