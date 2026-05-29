"use client";

import React, { useState, useEffect } from "react";
import { useOpentraStore } from "@/store/use-opentra-store";
import { cn } from "@/lib/utils";
import { Database, Play, Sparkles, AlertCircle, Plus, Trash2, CheckCircle2 } from "lucide-react";

// Inline demo data in case the store is empty
const defaultSKUs = [
  { skuId: "SKU-003", name: "Velar Runner", inventoryLeft: 180, dailyVelocity: 32, reorderThreshold: 240, projectedStockoutDays: 5.6, contributionMarginAfterRto: 28, spendGrowthPercent: 22 },
  { skuId: "SKU-017", name: "Metro Slip-On", inventoryLeft: 1240, dailyVelocity: 56, reorderThreshold: 320, projectedStockoutDays: 22, contributionMarginAfterRto: 42, spendGrowthPercent: 8 }
];

const defaultCampaigns = [
  { campaignId: "cmp_t2_cod_may", campaignName: "Tier2-COD-Lookalike-May", spend: 18400, spendGrowthPercent: 16, roasOnPlacedOrders: 3.8, roasOnDeliveredOrders: 2.1, ctr: 1.8, ctrDropPercent: 8, frequency: 3.2, codOrderCount: 186, codRatio: 67, rtoCountAttributed: 58, deliveredOrdersAttributed: 187, rtoRateAttributed: 31, contributionMarginAfterRto: 8 },
  { campaignId: "cmp_velar_static_v1", campaignName: "Velar-Static-V1", spend: 9400, spendGrowthPercent: 22, roasOnPlacedOrders: 3.2, roasOnDeliveredOrders: 2.7, ctr: 1.1, ctrDropPercent: 34, frequency: 5.4, codOrderCount: 41, codRatio: 45, rtoCountAttributed: 11, deliveredOrdersAttributed: 91, rtoRateAttributed: 12, contributionMarginAfterRto: 22 }
];

const defaultSegments = [
  { segmentId: "seg_velar_runner", name: "Velar Runner Buyers", prepaidRatio: 33, codRatio: 67, repeatRate: 14, returnRate: 6, rtoRateOnDelivered: 12 },
  { segmentId: "seg_metro_slip", name: "Metro Slip-On Buyers", prepaidRatio: 55, codRatio: 45, repeatRate: 24, returnRate: 2, rtoRateOnDelivered: 4 }
];

export function DataSandbox() {
  const store = useOpentraStore();
  const [activeTab, setActiveTab] = useState<"campaigns" | "skus" | "segments">("campaigns");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Local state for interactive manipulation
  const [skus, setSkus] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [segments, setSegments] = useState<any[]>([]);

  // Sync from store or defaults
  useEffect(() => {
    if (store.skus.length > 0) {
      setSkus(JSON.parse(JSON.stringify(store.skus)));
    } else {
      setSkus(JSON.parse(JSON.stringify(defaultSKUs)));
    }

    if (store.campaigns.length > 0) {
      setCampaigns(JSON.parse(JSON.stringify(store.campaigns)));
    } else {
      setCampaigns(JSON.parse(JSON.stringify(defaultCampaigns)));
    }

    if (store.customerSegments.length > 0) {
      setSegments(JSON.parse(JSON.stringify(store.customerSegments)));
    } else {
      setSegments(JSON.parse(JSON.stringify(defaultSegments)));
    }
  }, [store.skus, store.campaigns, store.customerSegments]);

  // Handlers for cell editing
  const handleCampaignChange = (index: number, field: string, value: any) => {
    setCampaigns((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const handleSkuChange = (index: number, field: string, value: any) => {
    setSkus((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const handleSegmentChange = (index: number, field: string, value: any) => {
    setSegments((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Quick manipulation presets to test rules
  const applyPreset = (type: "pause_cod" | "restock") => {
    if (type === "pause_cod") {
      setCampaigns((prev) =>
        prev.map((c) =>
          c.campaignName.includes("COD")
            ? { ...c, spend: 0, rtoRateAttributed: 0, codRatio: 0, spendGrowthPercent: -100 }
            : c
        )
      );
    } else if (type === "restock") {
      setSkus((prev) =>
        prev.map((s) =>
          s.name.includes("Velar")
            ? { ...s, inventoryLeft: 400, dailyVelocity: 32 }
            : s
        )
      );
    }
  };

  // Submit dynamic sandbox state to backend
  const handleSimulate = async () => {
    setLoading(true);
    setSuccess(false);

    try {
      const sandboxUrl = new URL(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/state/sandbox/update`);
      sandboxUrl.searchParams.set("brand_id", store.brandId);

      const response = await fetch(sandboxUrl.toString(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skus,
          campaigns,
          customerSegments: segments
        })
      });

      if (!response.ok) throw new Error("Sandbox update failed");

      // Reload store state to immediately show updated decisions and outcomes
      await store.loadInitialState();
      
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        store.setActiveView("Decision Feed");
      }, 1500);
    } catch (err) {
      console.error(err);
      alert("Error processing sandbox operational state");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-8 py-8 bg-[#f9fafc]">
      {/* Premium Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#efebff] px-2.5 py-1 text-xs font-semibold text-[#4320c2]">
              <Sparkles size={12} />
              Simulation Mode
            </span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-[#101426]">Interactive Data Sandbox</h1>
          <p className="mt-1 text-[15px] text-[#68708a]">
            Double-click or click inside any cell to manipulate live Meta Ads and Shopify data dynamically.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleSimulate}
            disabled={loading}
            className={cn(
              "inline-flex h-12 items-center gap-2 rounded-xl px-5 text-sm font-bold text-white transition-all shadow-md shadow-[#4320c2]/20",
              loading ? "bg-[#7963d2] cursor-not-allowed" : "bg-[#4320c2] hover:bg-[#3418aa]"
            )}
          >
            {success ? (
              <>
                <CheckCircle2 size={16} />
                Calculated Successfully!
              </>
            ) : (
              <>
                <Play size={16} fill="white" />
                {loading ? "Recalculating..." : "Run Simulation & Recalculate"}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Preset simulation helper cards */}
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="flex items-start gap-4 rounded-xl border border-dashed border-[#dcd9e9] bg-white p-5 shadow-sm transition hover:border-[#4320c2]/40">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#efebff] text-[#4320c2]">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-[#101426]">Simulate Decision: Pause Tier 2 COD Ads</h3>
            <p className="mt-1 text-sm text-[#68708a] leading-relaxed">
              Instantly zeros out the flagged Meta COD campaign spend. Click to trigger our closed-loop Monitoring engine to verify the action!
            </p>
            <button
              type="button"
              onClick={() => applyPreset("pause_cod")}
              className="mt-3 inline-flex items-center text-xs font-bold text-[#4320c2] hover:text-[#3418aa] gap-1"
            >
              Apply Preset
            </button>
          </div>
        </div>

        <div className="flex items-start gap-4 rounded-xl border border-dashed border-[#dcd9e9] bg-white p-5 shadow-sm transition hover:border-[#4320c2]/40">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#e3fcf1] text-[#0f975d]">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-[#101426]">Simulate Decision: Replenish Velar Runner Inventory</h3>
            <p className="mt-1 text-sm text-[#68708a] leading-relaxed">
              Increases Velar Runner inventory in Shopify to 400 units, demonstrating replenishment verification.
            </p>
            <button
              type="button"
              onClick={() => applyPreset("restock")}
              className="mt-3 inline-flex items-center text-xs font-bold text-[#0f975d] hover:text-[#0b7447] gap-1"
            >
              Apply Preset
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Spreadsheet Layout */}
      <div className="mt-8 rounded-xl border border-[#ebe8f5] bg-white shadow-sm overflow-hidden">
        {/* Spreadsheet Tabs */}
        <div className="flex border-b border-[#ebe8f5] bg-[#faf9ff] px-6">
          <button
            type="button"
            onClick={() => setActiveTab("campaigns")}
            className={cn(
              "flex h-14 items-center gap-2 border-b-2 px-4 text-sm font-semibold transition",
              activeTab === "campaigns" ? "border-[#4320c2] text-[#4320c2]" : "border-transparent text-[#68708a] hover:text-[#101426]"
            )}
          >
            📢 Meta Ads Manager
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("skus")}
            className={cn(
              "flex h-14 items-center gap-2 border-b-2 px-4 text-sm font-semibold transition",
              activeTab === "skus" ? "border-[#4320c2] text-[#4320c2]" : "border-transparent text-[#68708a] hover:text-[#101426]"
            )}
          >
            📦 Shopify Inventory
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("segments")}
            className={cn(
              "flex h-14 items-center gap-2 border-b-2 px-4 text-sm font-semibold transition",
              activeTab === "segments" ? "border-[#4320c2] text-[#4320c2]" : "border-transparent text-[#68708a] hover:text-[#101426]"
            )}
          >
            👥 Shopify Customer Signals
          </button>
        </div>

        {/* Tab Sheets */}
        <div className="overflow-x-auto">
          {activeTab === "campaigns" && (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#faf9ff] border-b border-[#ebe8f5] text-xs font-bold text-[#68708a] uppercase tracking-wider">
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Campaign Name</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Spend (Rs)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">ROAS (Placed)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">CTR (%)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Frequency</th>
                  <th className="px-6 py-4">Attributed RTO Rate (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ebe8f5]">
                {campaigns.map((camp, idx) => (
                  <tr key={camp.campaignId} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-3 border-r border-[#ebe8f5] font-semibold text-[#101426]">
                      {camp.campaignName}
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={camp.spend}
                        onChange={(e) => handleCampaignChange(idx, "spend", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        step="0.1"
                        value={camp.roasOnPlacedOrders}
                        onChange={(e) => handleCampaignChange(idx, "roasOnPlacedOrders", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        step="0.1"
                        value={camp.ctr}
                        onChange={(e) => handleCampaignChange(idx, "ctr", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        step="0.1"
                        value={camp.frequency}
                        onChange={(e) => handleCampaignChange(idx, "frequency", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="number"
                        value={camp.rtoRateAttributed}
                        onChange={(e) => handleCampaignChange(idx, "rtoRateAttributed", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === "skus" && (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#faf9ff] border-b border-[#ebe8f5] text-xs font-bold text-[#68708a] uppercase tracking-wider">
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">SKU Name</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">SKU ID</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Stock Left (Units)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Daily Sales Velocity</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Reorder Threshold</th>
                  <th className="px-6 py-4">Projected Stockout Days</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ebe8f5]">
                {skus.map((sku, idx) => (
                  <tr key={sku.skuId} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-3 border-r border-[#ebe8f5] font-semibold text-[#101426]">
                      {sku.name}
                    </td>
                    <td className="px-6 py-3 border-r border-[#ebe8f5] text-[#68708a] font-medium text-sm">
                      {sku.skuId}
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={sku.inventoryLeft}
                        onChange={(e) => handleSkuChange(idx, "inventoryLeft", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={sku.dailyVelocity}
                        onChange={(e) => handleSkuChange(idx, "dailyVelocity", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={sku.reorderThreshold}
                        onChange={(e) => handleSkuChange(idx, "reorderThreshold", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-6 py-3 text-[#101426] font-bold">
                      {sku.dailyVelocity > 0 ? (sku.inventoryLeft / sku.dailyVelocity).toFixed(1) : "99+"} days
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === "segments" && (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#faf9ff] border-b border-[#ebe8f5] text-xs font-bold text-[#68708a] uppercase tracking-wider">
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Segment Name</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Prepaid Mix (%)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">COD Mix (%)</th>
                  <th className="px-6 py-4 border-r border-[#ebe8f5]">Repeat Purchase Rate (%)</th>
                  <th className="px-6 py-4">Customer Returns (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ebe8f5]">
                {segments.map((seg, idx) => (
                  <tr key={seg.segmentId} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-3 border-r border-[#ebe8f5] font-semibold text-[#101426]">
                      {seg.name}
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={seg.prepaidRatio}
                        onChange={(e) => handleSegmentChange(idx, "prepaidRatio", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={seg.codRatio}
                        onChange={(e) => handleSegmentChange(idx, "codRatio", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 border-r border-[#ebe8f5]">
                      <input
                        type="number"
                        value={seg.repeatRate}
                        onChange={(e) => handleSegmentChange(idx, "repeatRate", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="number"
                        value={seg.returnRate}
                        onChange={(e) => handleSegmentChange(idx, "returnRate", parseInt(e.target.value) || 0)}
                        className="w-full rounded border border-[#dcd9e9] px-3 py-1.5 text-sm font-medium focus:border-[#4320c2] focus:outline-none"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
