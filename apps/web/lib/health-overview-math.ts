import { Campaign, CustomerSegment, Decision, SKU } from "./types";

export type ScoreExplanation = {
  title: string;
  summary: string;
  formula: string;
  inputs: { label: string; value: string }[];
  result: string;
  drivers?: string[];
};

function formatInr(value: number) {
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

function tightestSku(skus: SKU[]) {
  if (!skus.length) return null;
  return skus.reduce((tightest, sku) =>
    sku.projectedStockoutDays < tightest.projectedStockoutDays ? sku : tightest
  );
}

export function buildStabilityExplanation(decisions: Decision[]) {
  const active = decisions.filter((d) => !["successful", "ignored", "unsuccessful"].includes(d.state));
  const deductions = active.map((d) => ({
    title: d.title,
    severity: d.severity,
    points: d.severity === "high" ? 15 : d.severity === "medium" ? 8 : 4,
  }));
  const totalDeduction = deductions.reduce((sum, item) => sum + item.points, 0);
  const score = Math.max(30, 98 - totalDeduction);

  return {
    title: "Operational Stability Score",
    summary: "Measures how much unresolved operational risk is currently open across your decision queue.",
    formula: "98 − Σ(severity penalty per unresolved decision), floored at 30",
    inputs: [
      { label: "Base score", value: "98" },
      { label: "Unresolved decisions", value: String(active.length) },
      { label: "Severity penalties", value: "High −15 · Medium −8 · Low −4" },
      { label: "Total deduction", value: `−${totalDeduction}` },
    ],
    result: `${score}/100 — ${score >= 75 ? "Stable" : score >= 55 ? "At Risk" : "Unstable"}`,
    drivers:
      deductions.length > 0
        ? deductions.slice(0, 4).map((d) => `${d.title} (${d.severity}, −${d.points})`)
        : ["No unresolved decisions — score stays near baseline"],
  } satisfies ScoreExplanation;
}

export function buildInventoryDomainExplanation(skus: SKU[]) {
  const sku = tightestSku(skus);
  const minDays = sku?.projectedStockoutDays ?? 5.6;
  const deduction = minDays < 7 ? Math.round((7 - minDays) * 10) : 0;
  const score = Math.max(40, 96 - deduction);

  return {
    title: "Inventory Domain Score",
    summary: "Penalizes SKUs with less than 7 days of cover based on on-hand inventory and recent velocity.",
    formula: "96 − max(0, (7 − min stockout days) × 10), floored at 40",
    inputs: [
      { label: "Tightest SKU", value: sku ? `${sku.name} (${sku.inventoryLeft} units)` : "No SKU data" },
      { label: "Daily velocity", value: sku ? `${sku.dailyVelocity} units/day` : "—" },
      { label: "Inventory cover", value: `${minDays.toFixed(1)} days` },
      { label: "Deduction", value: deduction ? `−${deduction}` : "0 (cover ≥ 7 days)" },
    ],
    result: `${score}/100`,
  } satisfies ScoreExplanation;
}

export function buildMarketingDomainExplanation(campaigns: Campaign[]) {
  const avgRoas =
    campaigns.length > 0
      ? campaigns.reduce((sum, c) => sum + c.roasOnDeliveredOrders, 0) / campaigns.length
      : 2.31;
  const deduction = avgRoas < 2.5 ? Math.round((2.5 - avgRoas) * 20) : 0;
  const score = Math.max(40, 94 - deduction);

  return {
    title: "Marketing Domain Score",
    summary: "Reflects blended delivered ROAS across mapped Meta campaigns in the current snapshot.",
    formula: "94 − max(0, (2.5 − avg delivered ROAS) × 20), floored at 40",
    inputs: [
      { label: "Campaigns mapped", value: String(campaigns.length || "demo fallback") },
      { label: "Avg delivered ROAS", value: `${avgRoas.toFixed(2)}x` },
      { label: "Benchmark", value: "2.5x" },
      { label: "Deduction", value: deduction ? `−${deduction}` : "0 (ROAS at/above benchmark)" },
    ],
    result: `${score}/100`,
  } satisfies ScoreExplanation;
}

export function buildLogisticsDomainExplanation(campaigns: Campaign[]) {
  const avgRto =
    campaigns.length > 0
      ? campaigns.reduce((sum, c) => sum + c.rtoRateAttributed, 0) / campaigns.length
      : 16.8;
  const deduction = avgRto > 15 ? Math.round((avgRto - 15) * 4) : 0;
  const score = Math.max(30, 92 - deduction);

  return {
    title: "Logistics Domain Score",
    summary: "Penalizes elevated attributed RTO rates that compress realized revenue after delivery.",
    formula: "92 − max(0, (avg RTO% − 15) × 4), floored at 30",
    inputs: [
      { label: "Avg attributed RTO", value: `${avgRto.toFixed(1)}%` },
      { label: "Benchmark", value: "15%" },
      { label: "Deduction", value: deduction ? `−${deduction}` : "0 (RTO at/below benchmark)" },
    ],
    result: `${score}/100`,
  } satisfies ScoreExplanation;
}

export function buildCustomersDomainExplanation(segments: CustomerSegment[]) {
  const avgRepeat =
    segments.length > 0
      ? segments.reduce((sum, s) => sum + s.repeatRate, 0) / segments.length
      : 24.6;
  const score = Math.min(98, Math.max(60, Math.round(avgRepeat * 3.5)));

  return {
    title: "Customers Domain Score",
    summary: "Rewards stronger repeat purchase behavior from mapped customer segments.",
    formula: "clamp(round(avg repeat rate × 3.5), 60, 98)",
    inputs: [
      { label: "Segments mapped", value: String(segments.length || "demo fallback") },
      { label: "Avg repeat rate", value: `${avgRepeat.toFixed(1)}%` },
      { label: "Multiplier", value: "× 3.5" },
    ],
    result: `${score}/100`,
  } satisfies ScoreExplanation;
}

export function buildProfitabilityDomainExplanation(campaigns: Campaign[]) {
  const avgMargin =
    campaigns.length > 0
      ? campaigns.reduce((sum, c) => sum + c.contributionMarginAfterRto, 0) / campaigns.length
      : 28.7;
  const score = Math.min(98, Math.max(50, Math.round(avgMargin * 2.6)));

  return {
    title: "Profitability Domain Score",
    summary: "Tracks contribution margin after RTO across active campaigns.",
    formula: "clamp(round(avg contribution margin after RTO × 2.6), 50, 98)",
    inputs: [
      { label: "Avg margin after RTO", value: `${avgMargin.toFixed(1)}%` },
      { label: "Multiplier", value: "× 2.6" },
    ],
    result: `${score}/100`,
  } satisfies ScoreExplanation;
}

export function buildKeyMetricExplanations(
  campaigns: Campaign[],
  segments: CustomerSegment[],
  totalRevenue: number,
  totalAdSpend: number,
  totalOrders: number,
  newCustomers: number,
  avgRoasDelivered: number,
  avgRtoRate: number,
  avgRepeatRate: number,
  avgMargin: number
) {
  const placedRevenue = campaigns.reduce((sum, c) => sum + c.spend * c.roasOnPlacedOrders, 0);

  return {
    revenue: {
      title: "Revenue",
      summary: "Estimated placed-order revenue scaled from mapped campaign spend and ROAS.",
      formula: "Σ(campaign spend × placed ROAS) × 14.5 (window scale factor)",
      inputs: [
        { label: "Raw placed revenue", value: formatInr(placedRevenue) },
        { label: "Window scale", value: "× 14.5" },
      ],
      result: formatInr(totalRevenue),
    },
    orders: {
      title: "Orders (Delivered)",
      summary: "Orders inferred from revenue using an average order value assumption.",
      formula: "total revenue ÷ ₹2,200 AOV",
      inputs: [
        { label: "Revenue base", value: formatInr(totalRevenue) },
        { label: "Assumed AOV", value: "₹2,200" },
      ],
      result: totalOrders.toLocaleString("en-IN"),
    },
    adSpend: {
      title: "Ad Spend",
      summary: "Total Meta spend from mapped campaigns, scaled to the reporting window.",
      formula: "Σ(campaign spend) × 15.5 (window scale factor)",
      inputs: [
        { label: "Raw spend", value: formatInr(campaigns.reduce((sum, c) => sum + c.spend, 0)) },
        { label: "Window scale", value: "× 15.5" },
      ],
      result: formatInr(totalAdSpend),
    },
    roas: {
      title: "ROAS (Realized)",
      summary: "Average delivered ROAS after returns, across all mapped campaigns.",
      formula: "average(campaign delivered ROAS)",
      inputs: campaigns.slice(0, 3).map((c) => ({
        label: c.campaignName,
        value: `${c.roasOnDeliveredOrders.toFixed(2)}x`,
      })),
      result: `${avgRoasDelivered.toFixed(2)}x`,
    },
    rto: {
      title: "RTO Rate (Delivered)",
      summary: "Blended attributed return rate weighing campaign-level RTO signals.",
      formula: "average(campaign attributed RTO %)",
      inputs: campaigns.slice(0, 3).map((c) => ({
        label: c.campaignName,
        value: `${c.rtoRateAttributed.toFixed(1)}%`,
      })),
      result: `${avgRtoRate.toFixed(1)}%`,
    },
    newCustomers: {
      title: "New Customers",
      summary: "Estimated share of orders attributed to first-time buyers.",
      formula: "orders × 37% new-customer mix",
      inputs: [
        { label: "Orders", value: totalOrders.toLocaleString("en-IN") },
        { label: "New mix", value: "37%" },
      ],
      result: newCustomers.toLocaleString("en-IN"),
    },
    repeatRate: {
      title: "Repeat Rate",
      summary: "Average repeat purchase rate across mapped customer segments.",
      formula: "average(segment repeat rate)",
      inputs: segments.slice(0, 3).map((s) => ({
        label: s.name,
        value: `${s.repeatRate.toFixed(1)}%`,
      })),
      result: `${avgRepeatRate.toFixed(1)}%`,
    },
    margin: {
      title: "Contribution Margin %",
      summary: "Average post-RTO contribution margin across campaigns.",
      formula: "average(campaign contribution margin after RTO)",
      inputs: campaigns.slice(0, 3).map((c) => ({
        label: c.campaignName,
        value: `${c.contributionMarginAfterRto.toFixed(1)}%`,
      })),
      result: `${avgMargin.toFixed(1)}%`,
    },
  } satisfies Record<string, ScoreExplanation>;
}

export function buildRiskDriverExplanations(
  avgRtoRate: number,
  minStockoutDays: number,
  tightestSkuName: string | null
) {
  const inventoryWeight = minStockoutDays < 7 ? 32 : 5;
  return {
    rto: {
      title: "RTO rate increase",
      summary: "Relative risk weight — not the literal RTO percentage.",
      formula: "round(avg attributed RTO × 1.8)",
      inputs: [
        { label: "Avg attributed RTO", value: `${avgRtoRate.toFixed(1)}%` },
        { label: "Weight multiplier", value: "× 1.8" },
      ],
      result: `${Math.round(avgRtoRate * 1.8)}% driver weight`,
    },
    inventory: {
      title: "Inventory coverage low",
      summary: "Elevated when any SKU falls below 7 days of cover.",
      formula: "32 if min cover < 7 days, else 5",
      inputs: [
        { label: "Tightest SKU", value: tightestSkuName ?? "—" },
        { label: "Min cover", value: `${minStockoutDays.toFixed(1)} days` },
      ],
      result: `${inventoryWeight}% driver weight`,
    },
  } satisfies Record<string, ScoreExplanation>;
}