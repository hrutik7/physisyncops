"use client";

import { useRef, useState } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  Database,
  ArrowRight,
  TrendingUp,
  PackageOpen,
  Users,
  Layers,
  Sparkles,
  RefreshCw,
  Loader2
} from "lucide-react";
import * as XLSX from "xlsx";
import { useOpentraStore } from "@/store/use-opentra-store";
import { cn } from "@/lib/utils";
import { UploadSource } from "@/lib/types";

function detectUploadSourceFromSheets(sheetNames: string[]): UploadSource {
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
  
  return "shopify_orders";
}

export function ConnectDataSources() {
  const previewFile = useOpentraStore((state) => state.previewFile);
  const loading = useOpentraStore((state) => state.loading);
  const error = useOpentraStore((state) => state.error);
  
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const processSelectedFile = async (file: File) => {
    try {
      // Read Excel sheet names to auto-detect source
      const arrayBuffer = await file.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer, { sheets: [] });
      const sheetNames = workbook.SheetNames;
      
      const detectedSource = detectUploadSourceFromSheets(sheetNames);
      await previewFile(file, detectedSource);
    } catch (err) {
      console.error("Error reading file:", err);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await processSelectedFile(e.target.files[0]);
    }
    e.target.value = "";
  };

  return (
    <section className="flex flex-col min-h-screen bg-[#fbfaff] overflow-y-auto px-8 py-10">
      <header className="max-w-4xl mx-auto w-full mb-10">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#efebff] text-[#4320c2] text-xs font-semibold w-fit mb-4 border border-[#dfd7ff] animate-pulse">
          <Sparkles size={13} />
          <span>Connect Data Sources to Begin</span>
        </div>
        <h1 className="text-[38px] font-bold text-[#101426] tracking-tight leading-tight">
          Unify Your Operational Intelligence
        </h1>
        <p className="mt-3 text-base text-[#68708a] max-w-2xl leading-relaxed">
          Opentra automatically ingests, maps, and analyzes spreadsheet data across Meta Ads, Shopify Orders, and Inventory to isolate margin leaks and stockout risks.
        </p>
      </header>

      <main className="max-w-4xl mx-auto w-full grid grid-cols-1 md:grid-cols-5 gap-8 items-start">
        {/* Upload Container */}
        <div className="md:col-span-3 space-y-6">
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "relative flex flex-col items-center justify-center min-h-[360px] rounded-2xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-300",
              isDragActive
                ? "border-[#5b35d5] bg-[#faf8ff] scale-[1.01] shadow-lg shadow-[#5b35d5]/5"
                : "border-[#d8dce6] bg-white hover:border-[#5b35d5]/50 hover:shadow-md hover:shadow-gray-100/50"
            )}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".xlsx,.xls,.csv"
              className="hidden"
            />

            {loading ? (
              <div className="flex flex-col items-center">
                <Loader2 className="h-14 w-14 animate-spin text-[#5b35d5]" />
                <h3 className="mt-5 text-lg font-bold text-[#101426]">Analyzing Workbook Schema...</h3>
                <p className="mt-2 text-sm text-[#68708a] max-w-xs">
                  We are parsing sheets and detecting column structures for instant mapping.
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="relative mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-[#f5f3ff] text-[#5b35d5] transition-transform duration-300 hover:scale-105">
                  <UploadCloud size={32} />
                  <span className="absolute -bottom-1 -right-1 grid h-5 w-5 place-items-center rounded-full bg-[#0fb36b] text-white">
                    <CheckCircle2 size={13} />
                  </span>
                </div>
                <h3 className="text-xl font-bold text-[#101426]">Select or Drag & Drop Spreadsheet</h3>
                <p className="mt-2 text-sm text-[#68708a] max-w-xs">
                  Supported formats: <strong className="text-[#303954]">.xlsx, .xls, .csv</strong> (Multi-sheet workbooks or single sheets)
                </p>
                <div className="mt-6 inline-flex h-11 items-center justify-center rounded-lg bg-[#5b35d5] px-5 text-sm font-semibold text-white shadow-sm shadow-[#5b35d5]/20 transition-all hover:bg-[#4320c2] hover:scale-[1.02]">
                  Choose Spreadsheet File
                </div>
              </div>
            )}

            {/* Micro animation rings */}
            <div className="absolute inset-0 border border-transparent rounded-2xl pointer-events-none transition-all duration-300 peer-hover:border-[#5b35d5]/10" />
          </div>

          {error && (
            <div className="p-4 rounded-xl text-sm text-[#de2b25] bg-[#fff1f0] border border-[#fde8e8] flex items-start gap-2.5 shadow-sm">
              <span className="font-bold">Error:</span>
              <span>{error}</span>
            </div>
          )}

          {/* Integration options guide */}
          <div className="bg-white rounded-xl border border-[#e6e8f0] p-6 shadow-sm">
            <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[#68708a] mb-4 flex items-center gap-2">
              <Database size={13} />
              Unified Workbook Specifications
            </h4>
            <p className="text-sm text-[#4f5872] leading-relaxed mb-3">
              For full multi-system alignment, upload an Excel file containing separate sheets named matching these heuristics:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-[#faf8ff] border border-[#efebff]">
                <p className="font-bold text-[#5b35d5] mb-1">shopify_orders</p>
                <p className="text-[#68708a]">Contains checkout date, variant/sku, cod/prepaid revenue.</p>
              </div>
              <div className="p-2.5 rounded-lg bg-[#faf8ff] border border-[#efebff]">
                <p className="font-bold text-[#5b35d5] mb-1">meta_ads</p>
                <p className="text-[#68708a]">Contains campaign name, CTR, spending, frequency.</p>
              </div>
              <div className="p-2.5 rounded-lg bg-[#faf8ff] border border-[#efebff]">
                <p className="font-bold text-[#5b35d5] mb-1">inventory</p>
                <p className="text-[#68708a]">Contains SKU ID, variant name, and stock level.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Informational Pipeline Side Panel */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-[#faf8ff] rounded-2xl border border-[#efebff] p-6">
            <h3 className="text-lg font-bold text-[#101426] mb-5">Supported Integrations</h3>
            <div className="space-y-4">
              <IntegrationItem
                icon={TrendingUp}
                title="Meta Ads Attribution"
                desc="Tracks creative fatigue scores, frequency, and placed vs delivered ROAS."
                color="text-[#1877f2] bg-[#eef4ff]"
              />
              <IntegrationItem
                icon={PackageOpen}
                title="Shopify Operations"
                desc="Aggregates returned orders, calculates COD to prepaid ratios, and flags RTO anomalies."
                color="text-[#95bf47] bg-[#f4f7ee]"
              />
              <IntegrationItem
                icon={Users}
                title="Inventory & Stock Velocity"
                desc="Monitors SKU velocities to prevent stockout spikes during aggressive paid campaigns."
                color="text-[#e2a400] bg-[#fffcf0]"
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#e6e8f0] p-6 shadow-sm">
            <h3 className="text-base font-semibold text-[#101426] mb-4">Steps to Analysis</h3>
            <div className="space-y-4">
              <StepItem
                num="1"
                title="Upload & Parse"
                desc="Upload your spreadsheets. We automatically detect schema and sheets."
              />
              <StepItem
                num="2"
                title="Fuzzy Schema Mapping"
                desc="Ensure column mapping accuracy via our intuitive review modal."
              />
              <StepItem
                num="3"
                title="Isolate Margin Leaks"
                desc="View high-confidence decisions with simulated profit impact tags."
                isLast
              />
            </div>
          </div>
        </div>
      </main>
    </section>
  );
}

function IntegrationItem({
  icon: Icon,
  title,
  desc,
  color
}: {
  icon: any;
  title: string;
  desc: string;
  color: string;
}) {
  return (
    <div className="flex gap-3">
      <div className={cn("grid h-10 w-10 shrink-0 place-items-center rounded-lg text-sm", color)}>
        <Icon size={18} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-[#172039]">{title}</h4>
        <p className="mt-1 text-xs leading-relaxed text-[#68708a]">{desc}</p>
      </div>
    </div>
  );
}

function StepItem({
  num,
  title,
  desc,
  isLast = false
}: {
  num: string;
  title: string;
  desc: string;
  isLast?: boolean;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <span className="grid h-6 w-6 place-items-center rounded-full bg-[#efebff] text-xs font-bold text-[#4320c2]">
          {num}
        </span>
        {!isLast && <span className="h-8 w-px bg-[#e6e8f0] mt-1" />}
      </div>
      <div>
        <h4 className="text-sm font-semibold text-[#172039]">{title}</h4>
        <p className="mt-0.5 text-xs text-[#68708a] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}
