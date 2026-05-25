"use client";

import { useEffect } from "react";
import { Sidebar } from "@/components/sidebar";
import { DecisionFeed } from "@/components/decision-feed";
import { AnalysisPanel } from "@/components/analysis-panel";
import { MappingModal } from "@/components/mapping-modal";
import { ConnectDataSources } from "@/components/connect-data-sources";
import { DataSandbox } from "@/components/data-sandbox";
import { HealthOverview } from "@/components/health-overview";
import { useOpentraStore } from "@/store/use-opentra-store";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Home() {
  const snapshots = useOpentraStore((state) => state.snapshots);
  const decisions = useOpentraStore((state) => state.decisions);
  const loading = useOpentraStore((state) => state.loading);
  const selectedDecisionId = useOpentraStore((state) => state.selectedDecisionId);
  const activeView = useOpentraStore((state) => state.activeView);
  const loadInitialState = useOpentraStore((state) => state.loadInitialState);

  useEffect(() => {
    loadInitialState();
  }, [loadInitialState]);

  const hasData = snapshots && snapshots.length > 0;
  const hasSelectedDecision = !!selectedDecisionId;

  return (
    <main className="min-h-screen bg-[#fbfaff]">
      <div className="grid min-h-screen lg:grid-cols-[260px_1fr]">
        <Sidebar />
        {loading && !hasData ? (
          <div className="flex h-screen items-center justify-center bg-[#fbfaff] w-full">
            <div className="text-center">
              <Loader2 className="mx-auto h-12 w-12 animate-spin text-[#5b35d5]" />
              <p className="mt-4 text-sm font-semibold text-[#68708a] tracking-normal">
                Connecting to Opentra Core...
              </p>
            </div>
          </div>
        ) : activeView === "Data Sandbox" ? (
          <DataSandbox />
        ) : activeView === "Health Overview" ? (
          <HealthOverview />
        ) : hasData ? (
          <div className={cn(
            "grid grid-cols-1 h-screen overflow-hidden transition-all duration-300",
            hasSelectedDecision ? "lg:grid-cols-[1fr_390px]" : "grid-cols-1"
          )}>
            <div className="h-screen overflow-y-auto thin-scrollbar">
              <DecisionFeed />
            </div>
            {hasSelectedDecision && <AnalysisPanel />}
          </div>
        ) : (
          <ConnectDataSources />
        )}
      </div>
      <MappingModal />
    </main>
  );
}

