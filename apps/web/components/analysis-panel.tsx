"use client";

import { useState } from "react";
import { ArrowRight, Check, Circle, Eye, PackageOpen, TrendingUp, X, ShieldAlert, ListChecks, Play, Flag } from "lucide-react";
import { useOpentraStore } from "@/store/use-opentra-store";
import { Decision, RemedyAction, Severity } from "@/lib/types";
import { effortLabel, effortTone } from "@/lib/decision-v2";
import { cn } from "@/lib/utils";
import { Pill } from "./ui";
import { ConfidenceDriversDetail } from "./decision-v2/confidence-drivers";
import { DecisionVerificationBadge } from "./decision-v2/decision-verification-badge";
import { ImpactContextCard } from "./decision-v2/impact-context-card";
import { EvidencePanel } from "./decision-v2/evidence-panel";
import { RecoveryLabel } from "./decision-v2/recovery-label";
import { RemedyEffortTable } from "./decision-v2/remedy-effort-table";
import { TriggerReasonCard } from "./decision-v2/trigger-reason-card";
import { AutoResolutionCard } from "./decision-v2/auto-resolution-card";
import { StockoutScenariosCard } from "./decision-v2/stockout-scenarios-card";
import { VerificationLoop } from "./decision-v2/verification-loop";
import { RemediesModal } from "./decision-v2/remedies-modal";
import { DeleteDecisionButton } from "./decision-v2/delete-decision-button";
import { RootCauseAnalysis } from "./decision-v2/root-cause-analysis";

const iconBySignal = {
  InventoryRisk: PackageOpen,
  CreativeFatigue: TrendingUp,
  MarginLeakage: TrendingUp,
  CampaignRTOSpike: TrendingUp,
  ScalingOpportunity: TrendingUp,
  DataGapWarning: ShieldAlert
};

const severityCopy: Record<Severity, string> = {
  high: "CRITICAL",
  medium: "MEDIUM",
  low: "OPPORTUNITY"
};

function decisionSeverityLabel(decision: Decision) {
  if (decision.impactContext?.stockoutStateLabel) return decision.impactContext.stockoutStateLabel.toUpperCase();
  if (decision.impactContext?.actionUrgency === "monitor") return "MONITOR";
  return severityCopy[decision.severity];
}

function decisionSeverityTone(decision: Decision) {
  if (decision.impactContext?.actionUrgency === "monitor") return severityTone.medium;
  return severityTone[decision.severity];
}

const severityTone: Record<Severity, string> = {
  high: "border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]",
  medium: "border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]",
  low: "border-[#c8f3df] bg-[#ecfff6] text-[#07824b]"
};

export function AnalysisPanel() {
  const decision = useOpentraStore((state) => state.selectedDecision());
  const setSelectedDecision = useOpentraStore((state) => state.setSelectedDecision);
  const updateDecisionState = useOpentraStore((state) => state.updateDecisionState);
  const selectRemedy = useOpentraStore((state) => state.selectRemedy);
  const deleteDecision = useOpentraStore((state) => state.deleteDecision);
  const [showModal, setShowModal] = useState(false);
  const [showRemedies, setShowRemedies] = useState(false);

  if (!decision) {
    return (
      <aside className="hidden lg:flex h-screen items-center justify-center border-l border-[#ebe8f5] bg-white p-6 text-center text-sm text-[#68708a]">
        Select a decision from the feed to view deeper analysis.
      </aside>
    );
  }

  const Icon = iconBySignal[decision.signalType as keyof typeof iconBySignal] || PackageOpen;
  const remedies = decision.remedies || [];
  const selectedRemedy = remedies.find((r) => r.id === decision.selectedRemedyId) || remedies[0];
  const lifecycleStages = decision.lifecycleStages || [];

  return (
    <aside className="thin-scrollbar h-screen overflow-y-auto border-l border-[#ebe8f5] bg-white p-4">
      <div className="rounded-xl border border-[#e6e8f0] bg-white shadow-[0_18px_55px_rgba(38,35,64,0.06)]">
        <div className="flex items-center justify-between border-b border-[#edf0f6] px-4 py-4">
          <div className="flex items-center gap-1">
            <h2 className="text-base font-semibold text-[#101426]">Decision Details</h2>
            <button
              type="button"
              aria-label="View Full Analysis"
              title="View Full Analysis"
              onClick={() => setShowModal(true)}
              className="grid h-8 w-8 place-items-center rounded-lg text-[#68708a] hover:bg-[#f7f5ff] hover:text-[#4320c2] transition-colors"
            >
              <Eye size={18} />
            </button>
            <DeleteDecisionButton
              compact
              onDelete={async () => {
                await deleteDecision(decision.id);
                setShowRemedies(false);
                setShowModal(false);
              }}
            />
          </div>
          <button
            type="button"
            aria-label="Close details"
            onClick={() => setSelectedDecision("")}
            className="grid h-8 w-8 place-items-center rounded-lg text-[#68708a] hover:bg-[#f7f5ff]"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className={cn("grid h-12 w-12 place-items-center rounded-lg border", decisionSeverityTone(decision))}>
              <Icon size={23} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Pill className={decisionSeverityTone(decision)}>{decisionSeverityLabel(decision)}</Pill>
                {decision.staleMetadata?.isStale ? (
                  <Pill className="border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]">🚨 Stale Decision</Pill>
                ) : null}
              </div>
              <h3 className="mt-3 text-[17px] font-semibold leading-6 text-[#101426]">{decision.title}</h3>
              {decision.decisionVerification ? (
                <div className="mt-3">
                  <DecisionVerificationBadge verification={decision.decisionVerification} />
                </div>
              ) : null}
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-[#4f5872]">{decision.explanation}</p>

          {decision.triggerReason ? <div className="mt-5"><TriggerReasonCard trigger={decision.triggerReason} /></div> : null}

          {decision.autoResolutionCriteria ? (
            <div className="mt-5">
              <AutoResolutionCard criteria={decision.autoResolutionCriteria} />
            </div>
          ) : null}

          {decision.stockoutScenarios ? (
            <div className="mt-5">
              <StockoutScenariosCard analysis={decision.stockoutScenarios} />
            </div>
          ) : null}

          {decision.impactContext ? <div className="mt-5"><ImpactContextCard context={decision.impactContext} /></div> : null}

          <section className="mt-5 rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
            <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Root-Cause Analysis</h4>
            <div className="mt-4">
              <RootCauseAnalysis decision={decision} compact />
            </div>
          </section>

          {decision.confidenceDrivers?.length ? (
            <div className="mt-5">
              <ConfidenceDriversDetail
                score={decision.confidenceScore}
                drivers={decision.confidenceDrivers}
                metricVerification={decision.metricVerification}
              />
            </div>
          ) : null}

          <div className="mt-5 space-y-4 border-y border-[#edf0f6] py-4">
            <DetailRow label="Goal Alignment" value={decision.whyAnalysis?.goalAlignment?.replaceAll("_", " ") || "margin"} />
            <DetailRow label="Detected" value={decision.staleMetadata?.staleLabel || decision.timestamp} />
          </div>

          <section className="mt-5 rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Recommended Actions</h4>
              <button
                type="button"
                onClick={() => setShowRemedies(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#5b35d5] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#4320c2]"
              >
                <ListChecks size={14} />
                View Remedies ({remedies.length})
              </button>
            </div>

            {selectedRemedy ? (
              <div className="mt-4 rounded-xl border border-[#cdbdff] bg-[#faf8ff] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span>{selectedRemedy.medal}</span>
                  <span className="text-xs font-bold uppercase tracking-[0.08em] text-[#4320c2]">
                    {selectedRemedy.rank === "primary" ? "Primary" : "Alternative"}
                  </span>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-bold", effortTone(selectedRemedy.effort))}>
                    {effortLabel(selectedRemedy.effort)} effort
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-[#101426]">{selectedRemedy.label}</p>
                <p className="mt-2 text-xs text-[#68708a]">
                  {selectedRemedy.recoveryLabel || "Potential value"}:{" "}
                  <RecoveryLabel value={selectedRemedy.expectedRiskReductionLabel} explanation={selectedRemedy.recoveryExplanation} />
                </p>
                <ExpectedOutcome remedy={selectedRemedy} />
              </div>
            ) : (
              <p className="mt-3 text-sm text-[#68708a]">No remedy selected yet. Compare options before committing.</p>
            )}

            {remedies.length > 1 ? (
              <div className="mt-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Action Difficulty</p>
                <div className="mt-2">
                  <RemedyEffortTable remedies={remedies} />
                </div>
              </div>
            ) : null}
          </section>

          {decision.evidenceRequired ? <div className="mt-5"><EvidencePanel evidence={decision.evidenceRequired} /></div> : null}

          {decision.dependencies && decision.dependencies.length > 0 ? (
            <section className="mt-5 rounded-xl border border-[#ffe7ba] bg-[#fff8e8] p-4">
              <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#b86d00]">Decision Dependencies</h4>
              <div className="mt-3 space-y-2">
                {decision.dependencies.map((dep) => (
                  <div key={dep.label} className="rounded-lg border border-[#ffe7ba] bg-white px-3 py-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-[#101426]">{dep.label}</span>
                      <Pill className="border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]">{dep.status.replaceAll("_", " ")}</Pill>
                    </div>
                    <p className="mt-1 text-xs text-[#68708a]">{dep.detail}</p>
                    {dep.effect === "downgrade" ? (
                      <p className="mt-2 text-xs font-semibold text-[#b86d00]">This decision may downgrade in urgency.</p>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <LifecycleActions decision={decision} onAdvance={updateDecisionState} />

          <section className="mt-5">
            <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Lifecycle</h4>
            <div className="mt-4 space-y-0">
              {lifecycleStages.length > 0 ? (
                lifecycleStages.map((stage, idx) => (
                  <TimelineStep
                    key={stage.key}
                    title={stage.title}
                    description={stage.description}
                    done={stage.status === "done"}
                    active={stage.status === "active"}
                    last={idx === lifecycleStages.length - 1}
                  />
                ))
              ) : (
                <>
                  <TimelineStep title="Detected" description="AI generated this decision" time={decision.timestamp} done={decision.state !== "pending"} active={decision.state === "pending"} />
                  <TimelineStep title="Monitoring" description="Tracking execution signals" active={decision.state === "monitoring"} done={["verified", "successful"].includes(decision.state)} />
                  <TimelineStep title="Closed" description="Outcome determined" active={decision.state === "successful"} done={decision.state === "successful"} last />
                </>
              )}
            </div>
          </section>

          {decision.outcomeMeasurement ? (
            <div className="mt-5">
              <VerificationLoop outcome={decision.outcomeMeasurement} />
            </div>
          ) : null}

          {decision.state === "successful" && (
            <div className="mt-5 rounded-xl border border-[#d8f2e6] bg-[#ecfff6] p-4">
              <div className="flex items-center gap-2">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-[#07824b] text-white">
                  <Check size={12} />
                </span>
                <span className="text-[10px] font-bold text-[#07824b] uppercase tracking-wider">Closed-Loop Verified</span>
              </div>
              <p className="mt-3 text-[11px] text-[#05663b] leading-relaxed font-medium">
                PhysiSync measured the outcome, scored decision accuracy, and logged the recovery for learning.
              </p>
            </div>
          )}
        </div>
      </div>

      {showRemedies ? (
        <RemediesModal
          decision={decision}
          remedies={remedies}
          selectedRemedyId={decision.selectedRemedyId}
          onClose={() => setShowRemedies(false)}
          onSelect={(remedy) => {
            selectRemedy(decision.id, remedy);
            setShowRemedies(false);
          }}
        />
      ) : null}

      {showModal ? <AnalysisModal decision={decision} onClose={() => setShowModal(false)} /> : null}
    </aside>
  );
}

function ExpectedOutcome({ remedy }: { remedy: RemedyAction }) {
  const entries = Object.entries(remedy.expectedOutcome).filter(
    ([key, value]) => key !== "recovery" && typeof value === "object" && value !== null && "before" in value
  ) as [string, { before: string; after: string }][];

  if (!entries.length) return null;

  return (
    <div className="mt-3 space-y-1 rounded-lg border border-[#edf0f6] bg-white p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#68708a]">Expected Outcome</p>
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center justify-between text-xs">
          <span className="capitalize text-[#68708a]">{key.replace(/([A-Z])/g, " $1")}</span>
          <span className="font-semibold text-[#101426]">
            {value.before} <ArrowRight size={12} className="mx-1 inline text-[#68708a]" /> {value.after}
          </span>
        </div>
      ))}
    </div>
  );
}

function LifecycleActions({
  decision,
  onAdvance,
}: {
  decision: Decision;
  onAdvance: (id: string, state: Decision["state"]) => void;
}) {
  const actions: { label: string; next: Decision["state"]; icon: typeof Play; show: boolean }[] = [
    { label: "Acknowledge", next: "acknowledged", icon: Flag, show: decision.state === "pending" },
    { label: "Mark Executed", next: "action_executed", icon: Play, show: decision.state === "action_planned" },
    { label: "Start Monitoring", next: "monitoring", icon: TrendingUp, show: decision.state === "action_executed" },
  ];

  const visible = actions.filter((a) => a.show);
  if (!visible.length) return null;

  return (
    <section className="mt-5 rounded-xl border border-[#edf0f6] bg-[#fcfcff] p-4">
      <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">Next Step</h4>
      <div className="mt-3 flex flex-wrap gap-2">
        {visible.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.next}
              type="button"
              onClick={() => onAdvance(decision.id, action.next)}
              className="inline-flex items-center gap-2 rounded-lg border border-[#cdbdff] bg-white px-3 py-2 text-sm font-semibold text-[#4320c2] hover:bg-[#faf8ff]"
            >
              <Icon size={15} />
              {action.label}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function AnalysisModal({ decision, onClose }: { decision: Decision; onClose: () => void }) {
  const deleteDecision = useOpentraStore((state) => state.deleteDecision);
  const Icon = iconBySignal[decision.signalType as keyof typeof iconBySignal] || PackageOpen;
  const remedies = decision.remedies || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-md">
      <div className="relative flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-[#ebe8f5] bg-white">
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
          <button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-xl border border-[#edf0f6] bg-white text-[#68708a] hover:bg-[#f7f5ff]">
            <X size={18} />
          </button>
        </div>

        <div className="thin-scrollbar flex-1 overflow-y-auto p-6 space-y-6">
          {decision.decisionVerification ? <DecisionVerificationBadge verification={decision.decisionVerification} /> : null}

          {decision.triggerReason ? <TriggerReasonCard trigger={decision.triggerReason} /> : null}

          {decision.autoResolutionCriteria ? <AutoResolutionCard criteria={decision.autoResolutionCriteria} /> : null}

          {decision.stockoutScenarios ? <StockoutScenariosCard analysis={decision.stockoutScenarios} /> : null}

          {decision.impactContext ? <ImpactContextCard context={decision.impactContext} /> : null}

          <RootCauseAnalysis decision={decision} />

          {decision.confidenceDrivers?.length ? (
            <ConfidenceDriversDetail
              score={decision.confidenceScore}
              drivers={decision.confidenceDrivers}
              metricVerification={decision.metricVerification}
            />
          ) : null}

          {remedies.length ? (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#68708a] mb-3">Remedy Comparison</h4>
              <RemedyEffortTable remedies={remedies} />
            </div>
          ) : null}

          {decision.evidenceRequired ? <EvidencePanel evidence={decision.evidenceRequired} /> : null}

          {decision.outcomeMeasurement ? <VerificationLoop outcome={decision.outcomeMeasurement} /> : null}
        </div>

        <div className="border-t border-[#edf0f6] bg-[#fbfaff] px-6 py-4 flex items-center justify-between gap-3">
          <DeleteDecisionButton
            onDelete={async () => {
              await deleteDecision(decision.id);
              onClose();
            }}
          />
          <button type="button" onClick={onClose} className="rounded-lg bg-[#4320c2] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#3417a2]">
            Close Analysis
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[128px_1fr] gap-4 text-sm items-center">
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
  last
}: {
  title: string;
  description: string;
  time?: string;
  done?: boolean;
  active?: boolean;
  last?: boolean;
}) {
  return (
    <div className={cn("grid grid-cols-[28px_1fr] gap-3", active && "rounded-lg bg-[#f3f0ff] py-3 pr-3")}>
      <div className="flex flex-col items-center">
        <span
          className={cn(
            "mt-0.5 grid h-4 w-4 place-items-center rounded-full border",
            active ? "border-[#3457f4] bg-[#3457f4]" : done ? "border-[#0fb36b] bg-[#0fb36b]" : "border-[#b9c0cf] bg-white"
          )}
        >
          {(active || done) && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
        </span>
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