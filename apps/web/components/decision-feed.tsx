"use client";

import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  CalendarDays,
  Check,
  ChevronDown,
  Filter,
  Megaphone,
  PackageOpen,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  UploadCloud,
  Users,
  Loader2
} from "lucide-react";
import * as XLSX from "xlsx";
import { useOpentraStore } from "@/store/use-opentra-store";
import { cn } from "@/lib/utils";
import { Decision, Severity, UploadSource } from "@/lib/types";
import { Pill, StatePill } from "./ui";

const iconBySignal = {
  InventoryRisk: PackageOpen,
  CreativeFatigue: BarChart3,
  MarginLeakage: ShieldAlert,
  CampaignRTOSpike: TrendingUp,
  ScalingOpportunity: Users
};

function detectUploadSourceFromSheets(sheetNames: string[]): UploadSource {
  // Map sheet names to upload sources
  const sheetLower = sheetNames.map(s => s.toLowerCase());
  
  if (sheetLower.some(s => s.includes("shopify") || s.includes("order"))) {
    return "shopify_orders";
  }
  if (sheetLower.some(s => s.includes("meta") || s.includes("ad"))) {
    return "meta_ads";
  }
  if (sheetLower.some(s => s.includes("inventory"))) {
    return "inventory";
  }
  if (sheetLower.some(s => s.includes("creative"))) {
    return "creative_performance";
  }
  if (sheetLower.some(s => s.includes("customer"))) {
    return "customer_signals";
  }
  
  // Default to first sheet name heuristic
  return "shopify_orders";
}

const iconToneBySeverity: Record<Severity, string> = {
  high: "bg-[#fff1f0] text-[#de2b25]",
  medium: "bg-[#fff8e8] text-[#c27803]",
  low: "bg-[#ecfff6] text-[#07824b]"
};

const labelBySignal = {
  InventoryRisk: "CRITICAL",
  CampaignRTOSpike: "HIGH",
  CreativeFatigue: "INFO",
  MarginLeakage: "HIGH",
  ScalingOpportunity: "OPPORTUNITY"
};

const metricColorBySeverity: Record<Severity, string> = {
  high: "text-[#de2b25]",
  medium: "text-[#c27803]",
  low: "text-[#07824b]"
};

const confidenceColor = (score: number) => {
  if (score >= 0.75) return "bg-[#0fb36b]";
  if (score >= 0.6) return "bg-[#e4b100]";
  return "bg-[#f59e0b]";
};

function compactImpact(decision: Decision) {
  if (decision.businessImpact) {
    if (decision.businessImpact >= 100000) {
      return { value: `Rs ${(decision.businessImpact / 100000).toFixed(2)}L`, label: decision.impactLabel || "revenue at risk" };
    }
    return { value: `Rs ${decision.businessImpact}`, label: decision.impactLabel || "margin risk" };
  }
  return { value: decision.impactLabel, label: "estimated impact" };
}

function statusSubtext(decision: Decision) {
  if (decision.state === "monitoring") return "Tracking signals";
  if (decision.state === "ignored") return "Ignored by operator";
  if (decision.state === "snoozed") return "Paused review";
  if (decision.state === "successful") return "Outcome verified successful";
  if (decision.state === "verified") return "Signal confirmed";
  return "Waiting for review";
}

export function DecisionFeed() {
  const decisions = useOpentraStore((state) => state.decisions);
  const selectedDecisionId = useOpentraStore((state) => state.selectedDecisionId);
  const setSelectedDecision = useOpentraStore((state) => state.setSelectedDecision);
  const updateDecisionState = useOpentraStore((state) => state.updateDecisionState);
  const snapshots = useOpentraStore((state) => state.snapshots);
  const loading = useOpentraStore((state) => state.loading);
  const error = useOpentraStore((state) => state.error);
  const loadInitialState = useOpentraStore((state) => state.loadInitialState);
  const previewFile = useOpentraStore((state) => state.previewFile);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load backend state on mount
  useEffect(() => {
    loadInitialState();
  }, [loadInitialState]);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        // Read Excel file to detect sheet names and determine upload source
        const arrayBuffer = await file.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { sheets: [] });
        const sheetNames = workbook.SheetNames;
        
        // Auto-detect upload source from sheet names
        const detectedSource = detectUploadSourceFromSheets(sheetNames);
        
        // Preview with detected source
        await previewFile(file, detectedSource);
      } catch (err) {
        console.error("Error reading Excel file:", err);
      }
    }
    // reset target value so same file can be uploaded again
    event.target.value = "";
  };

  const isBaseline = snapshots.length === 1 && snapshots[0].isBaseline;

  return (
    <section className="min-w-0 bg-[#fbfaff] px-6 py-7">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[30px] font-semibold leading-none tracking-normal text-[#101426]">Decision Feed</h1>
            <Pill className="border-[#d9f2e7] bg-[#e9fff4] text-[#07824b]">Live</Pill>
            {loading && <Loader2 className="animate-spin text-[#5b35d5]" size={20} />}
          </div>
          <p className="mt-3 text-sm text-[#68708a]">AI-powered operational intelligence for your D2C business</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {error && (
            <div className="text-xs text-[#de2b25] bg-[#fff1f0] border border-[#fde8e8] px-3 py-1.5 rounded-lg max-w-sm">
              {error}
            </div>
          )}
          
          <button type="button" className="inline-flex h-11 items-center gap-2 rounded-lg border border-[#e6e8f0] bg-white px-4 text-sm font-medium text-[#172039] shadow-sm">
            <Filter size={17} />
            Filter
          </button>
          <button type="button" className="inline-flex h-11 items-center gap-2 rounded-lg border border-[#e6e8f0] bg-white px-4 text-sm font-medium text-[#172039] shadow-sm">
            <CalendarDays size={17} />
            Last 7 days
            <ChevronDown size={15} />
          </button>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex h-11 items-center gap-2 rounded-lg bg-[#5b35d5] px-4 text-sm font-semibold text-white shadow-sm shadow-[#5b35d5]/20 hover:bg-[#4320c2]"
          >
            <UploadCloud size={17} />
            Upload Data
          </button>
          
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".xlsx,.xls,.csv"
            className="hidden"
          />
        </div>
      </header>

      {isBaseline ? (
        <div className="mt-6 flex items-start gap-3 rounded-lg border border-[#dbe7ff] bg-[#eef5ff] px-4 py-3 text-sm text-[#185be8]">
          <RefreshCw className="mt-0.5 shrink-0" size={17} />
          <div>
            <p className="font-semibold">Baseline snapshot active. Waiting for next upload to verify inferences.</p>
            <p className="mt-0.5 text-[#426da7]">Upload another spreadsheet of Meta spend or inventory cover to run verification metrics.</p>
          </div>
        </div>
      ) : null}

      <div className="mt-8 overflow-hidden rounded-xl border border-[#e6e8f0] bg-white shadow-[0_20px_60px_rgba(38,35,64,0.06)]">
        <div className="grid h-14 grid-cols-[92px_minmax(260px,1.6fr)_150px_130px_150px_132px] items-center border-b border-[#e6e8f0] px-5 text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a]">
          <span>Priority</span>
          <span>Decision</span>
          <span>Impact</span>
          <span>Confidence</span>
          <span>Status</span>
          <span className="text-center">Action</span>
        </div>

        <div className="divide-y divide-[#edf0f6]">
          {decisions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#ecfff6] text-[#07824b] mb-4">
                <Check className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-bold text-[#101426]">No Operational Risks Found</h3>
              <p className="mt-2 text-sm text-[#68708a] max-w-sm leading-relaxed">
                Your D2C brand metrics are looking completely optimized. No active campaign spikes, creative fatigue, or inventory stockout risks have been flagged.
              </p>
            </div>
          ) : (
            decisions.map((decision) => {
              const Icon = iconBySignal[decision.signalType as keyof typeof iconBySignal] || ShieldAlert;
              const impact = compactImpact(decision);
              const selected = selectedDecisionId === decision.id;
              return (
                <button
                  key={decision.id}
                  type="button"
                  onClick={() => setSelectedDecision(decision.id)}
                  className={cn(
                    "grid min-h-[112px] w-full grid-cols-[92px_minmax(260px,1.6fr)_150px_130px_150px_132px] items-center gap-0 px-5 text-left transition hover:bg-[#fbfaff] focus:outline-none",
                    selected && "bg-[#faf8ff] border-l-4 border-l-[#5b35d5]"
                  )}
                >
                  <div className="flex flex-col items-start gap-2">
                    <span className={cn("grid h-12 w-12 place-items-center rounded-lg", iconToneBySeverity[decision.severity])}>
                      <Icon size={23} />
                    </span>
                    <span className={cn("rounded-md px-2 py-1 text-[11px] font-bold", iconToneBySeverity[decision.severity])}>
                      {labelBySignal[decision.signalType as keyof typeof labelBySignal] || "INFO"}
                    </span>
                  </div>

                  <div className="min-w-0 pr-6">
                    <h2 className="truncate text-[17px] font-semibold text-[#101426]" title={decision.title}>{decision.title}</h2>
                    <p className="mt-2 max-w-[520px] text-sm leading-6 text-[#303954] line-clamp-2" title={decision.explanation}>{decision.explanation}</p>
                  </div>

                  <div>
                    <p className={cn("text-[17px] font-bold", metricColorBySeverity[decision.severity])}>{impact.value}</p>
                    <p className="mt-1 text-sm text-[#68708a]">{impact.label}</p>
                  </div>

                  <div className="pr-5">
                    <p className="text-[15px] font-bold text-[#101426]">{Math.round(decision.confidenceScore * 100)}%</p>
                    <div className="mt-3 h-1.5 rounded-full bg-[#edf0f6]">
                      <div className={cn("h-1.5 rounded-full", confidenceColor(decision.confidenceScore))} style={{ width: `${Math.round(decision.confidenceScore * 100)}%` }} />
                    </div>
                  </div>

                  <div>
                    <StatePill state={decision.state} />
                    <p className="mt-2 max-w-[120px] text-xs leading-5 text-[#68708a]">{statusSubtext(decision)}</p>
                  </div>

                  <div className="flex justify-end">
                    {decision.state === "monitoring" || decision.state === "verified" || decision.state === "successful" ? (
                      <span className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#e6e8f0] bg-white px-4 text-sm font-semibold text-[#172039]">
                        <Check size={16} className="text-[#07824b]" />
                        Taken
                      </span>
                    ) : decision.state === "ignored" ? (
                      <button
                        type="button"
                        disabled
                        className="inline-flex h-10 items-center rounded-lg border border-[#e6e8f0] bg-gray-50 px-4 text-sm font-semibold text-[#68708a] opacity-50"
                      >
                        Ignored
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          updateDecisionState(decision.id, "monitoring");
                        }}
                        className={cn(
                          "inline-flex h-10 items-center gap-2 rounded-lg px-4 text-sm font-semibold",
                          selected ? "bg-[#5b35d5] text-white shadow-sm shadow-[#5b35d5]/20" : "border border-[#e6e8f0] bg-white text-[#4320c2]"
                        )}
                      >
                        Take Action
                      </button>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      <button type="button" className="mx-auto mt-7 flex items-center gap-2 text-sm font-medium text-[#4f5872]">
        Load more
        <ChevronDown size={16} />
      </button>
    </section>
  );
}
