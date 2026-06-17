"use client";

import { create } from "zustand";
import { operationalState } from "@/lib/demo-data";
import { enrichDecisionClient } from "@/lib/decision-v2";
import { Decision, DecisionState, OperationalState, RemedyAction, TimelineEvent, UploadSource, MappingSuggestion } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const RESET_TOKEN = process.env.NEXT_PUBLIC_RESET_TOKEN || "opentra";

interface OpentraStore extends OperationalState {
  selectedDecisionId: string;
  mappingOpen: boolean;
  loading: boolean;
  error: string | null;
  taskStatus: string | null;
  taskMeta: any;
  selectedFile: File | null;
  activeUploadSource: UploadSource;
  uploadedColumns: string[];
  brandId: string;
  
  activeView: string;
  setActiveView: (view: string) => void;
  setSelectedDecision: (id: string) => void;
  setBrandId: (id: string) => void;
  setMappingOpen: (open: boolean) => void;
  updateDecisionState: (id: string, state: DecisionState) => void;
  selectRemedy: (id: string, remedy: RemedyAction) => void;
  selectedDecision: () => Decision | undefined;
  
  // Asynchronous API Actions
  setSelectedFile: (file: File | null) => void;
  setActiveUploadSource: (source: UploadSource) => void;
  loadInitialState: () => Promise<void>;
  previewFile: (file: File, source: UploadSource) => Promise<void>;
  confirmUpload: (mapping: Record<string, string>) => Promise<void>;
  resetDatabase: () => Promise<void>;
}

function actionEvent(state: DecisionState, extra?: string): TimelineEvent {
  const copy: Record<DecisionState, string> = {
    pending: "Returned to pending",
    acknowledged: "Operator acknowledged decision",
    action_planned: "Action planned",
    action_executed: "Action executed",
    monitoring: "Monitoring started",
    verified: "Execution verified",
    successful: "Marked successful",
    unsuccessful: "Marked unsuccessful",
    ignored: "User ignored decision",
    snoozed: "User snoozed decision"
  };

  const descriptions: Partial<Record<DecisionState, string>> = {
    monitoring: "Monitoring started. The next upload will verify downstream operational change.",
    action_planned: extra || "Operator selected a remedy.",
    action_executed: "Operational change deployed in connected systems.",
    acknowledged: "Decision reviewed and ready for remedy selection."
  };

  return {
    id: `evt_${state}_${Date.now()}`,
    time: "Now",
    title: copy[state],
    description: descriptions[state] || "Decision state updated.",
    kind: ["monitoring", "action_planned", "action_executed", "acknowledged", "ignored", "snoozed"].includes(state) ? "human" : "system"
  };
}

function enrichDecisions(decisions: Decision[], campaigns: OperationalState["campaigns"], skus: OperationalState["skus"]) {
  return decisions.map((decision) => enrichDecisionClient(decision, campaigns, skus));
}

export const useOpentraStore = create<OpentraStore>((set, get) => ({
  ...operationalState,
  snapshots: [],
  skus: [],
  campaigns: [],
  customerSegments: [],
  creatives: [],
  decisions: [],
  selectedDecisionId: "",
  mappingOpen: false,
  loading: false,
  error: null,
  taskStatus: null,
  taskMeta: null,
  selectedFile: null,
  activeUploadSource: "shopify_orders",
  uploadedColumns: [],
  brandId: typeof window !== "undefined" ? (localStorage.getItem("physisync_brand_id") || "brand_unigo_real") : "brand_unigo_real",
  activeView: "Decision Feed",

  setActiveView: (view) => set({ activeView: view }),
  setSelectedDecision: (id) => set({ selectedDecisionId: id }),
  setBrandId: (id) => {
    if (typeof window !== "undefined") localStorage.setItem("physisync_brand_id", id);
    set({ brandId: id });
  },
  setMappingOpen: (open) => set({ mappingOpen: open }),
  
  updateDecisionState: (id, state) => {
    set((current) => ({
      decisions: enrichDecisions(
        current.decisions.map((decision) =>
          decision.id === id
            ? {
                ...decision,
                state,
                lifecycleLabel: state,
                timeline: [...decision.timeline, actionEvent(state)]
              }
            : decision
        ),
        current.campaigns,
        current.skus
      )
    }));

    fetch(`${API_URL}/decisions/${id}/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state })
    }).catch((err) => console.error("Failed to sync state to backend:", err));
  },

  selectRemedy: (id, remedy) => {
    set((current) => ({
      decisions: enrichDecisions(
        current.decisions.map((decision) =>
          decision.id === id
            ? {
                ...decision,
                state: "action_planned",
                selectedRemedyId: remedy.id,
                lifecycleLabel: "action_planned",
                timeline: [...decision.timeline, actionEvent("action_planned", `Selected: ${remedy.label}`)]
              }
            : decision
        ),
        current.campaigns,
        current.skus
      )
    }));

    fetch(`${API_URL}/decisions/${id}/remedy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remedy_id: remedy.id, remedy_label: remedy.label })
    }).catch((err) => console.error("Failed to sync remedy to backend:", err));
  },
  
  selectedDecision: () => get().decisions.find((decision) => decision.id === get().selectedDecisionId) || undefined,
  
  setSelectedFile: (file) => set({ selectedFile: file }),
  setActiveUploadSource: (source) => set({ activeUploadSource: source }),
  
  loadInitialState: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API_URL}/state?brand_id=${get().brandId}`);
      if (!res.ok) throw new Error("Failed to load state from backend");
      const data = await res.json();
      set({
        brandName: data.brandName,
        snapshots: data.snapshots,
        skus: data.skus,
        campaigns: data.campaigns,
        customerSegments: data.customerSegments,
        creatives: data.creatives,
        decisions: enrichDecisions(data.decisions || [], data.campaigns || [], data.skus || []),
        loading: false
      });
      if (data.decisions && data.decisions.length > 0) {
        set({ selectedDecisionId: data.decisions[0].id });
      }
    } catch (err: any) {
      console.warn("Backend unavailable, keeping live state empty:", err.message);
      set({
        brandName: "Uploaded Brand",
        snapshots: [],
        skus: [],
        campaigns: [],
        customerSegments: [],
        creatives: [],
        decisions: [],
        mappingSuggestions: [],
        selectedDecisionId: "",
        loading: false,
        error: "Backend unavailable. Start the API and upload a workbook to generate decisions."
      });
    }
  },
  
  previewFile: async (file, source) => {
    set({ loading: true, error: null, activeUploadSource: source, selectedFile: file });
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch(`${API_URL}/uploads/preview?brand_id=${get().brandId}&upload_source=${source}`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Preview API failed");
      const data = await res.json();
      
      set({
        uploadedColumns: data.columns,
        mappingSuggestions: data.suggestions,
        mappingOpen: true,
        loading: false
      });
    } catch (err: any) {
      console.error(err);
      set({ error: "Failed to generate column preview suggestions. Is the backend running?", loading: false });
    }
  },
  
  confirmUpload: async (mapping) => {
    const file = get().selectedFile;
    const source = get().activeUploadSource;
    if (!file) {
      set({ error: "No file selected for confirmation" });
      return;
    }
    
    set({ loading: true, error: null, taskStatus: "PENDING", taskMeta: null });
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("brand_id", get().brandId);
      formData.append("upload_source", source);
      formData.append("mapping", JSON.stringify(mapping));
      
      const res = await fetch(`${API_URL}/uploads/confirm`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Failed to submit confirm mapping");
      
      const data = await res.json();
      const taskId = data.task_id;
      let pollCount = 0;
      
      // Start background task polling
      const poll = setInterval(async () => {
        try {
          pollCount += 1;
          const statusRes = await fetch(`${API_URL}/uploads/status/${taskId}`);
          if (!statusRes.ok) throw new Error("Polling status failed");
          
          const statusData = await statusRes.json();
          if (statusData.status === "success") {
            clearInterval(poll);
            set({ taskStatus: "SUCCESS", loading: false, mappingOpen: false });
            // Reload operational state with newly computed backend decisions
            get().loadInitialState();
          } else if (statusData.status === "failure") {
            clearInterval(poll);
            set({ error: `Task failed: ${statusData.error}`, loading: false, taskStatus: "FAILURE" });
          } else if (statusData.status === "progress") {
            set({ taskStatus: "PROGRESS", taskMeta: statusData.meta });
          } else if (pollCount >= 60) {
            clearInterval(poll);
            set({
              error: "Upload is still pending. Make sure the Celery worker is running, then upload again.",
              loading: false,
              taskStatus: "TIMEOUT"
            });
          }
        } catch (pollErr: any) {
          clearInterval(poll);
          set({ error: `Polling error: ${pollErr.message}`, loading: false, taskStatus: "FAILURE" });
        }
      }, 1000);
      
    } catch (err: any) {
      console.error(err);
      set({ error: `Upload confirmation failed: ${err.message}`, loading: false, taskStatus: "FAILURE" });
    }
  },

  resetDatabase: async () => {
    set({ loading: true, error: null });
    try {
      const resetUrl = new URL(`${API_URL}/reset`);
      if (RESET_TOKEN) resetUrl.searchParams.set("reset_token", RESET_TOKEN);

      const res = await fetch(resetUrl.toString(), {
        method: "POST"
      });
      if (!res.ok) throw new Error(res.status === 403 ? "Reset is locked. Configure RESET_TOKEN on the API and NEXT_PUBLIC_RESET_TOKEN in the web app." : "Reset API failed");
      
      set({
        snapshots: [],
        skus: [],
        campaigns: [],
        customerSegments: [],
        creatives: [],
        decisions: [],
        selectedDecisionId: "",
        loading: false,
        error: null,
        taskStatus: null,
        taskMeta: null,
        selectedFile: null,
        uploadedColumns: [],
        mappingOpen: false
      });
    } catch (err: any) {
      console.error(err);
      set({ error: `Database reset failed: ${err.message}`, loading: false });
    }
  }
}));
