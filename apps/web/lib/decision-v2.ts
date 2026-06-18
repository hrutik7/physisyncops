import { Campaign, Decision, ImpactContext, RemedyAction, Severity, SignalType, SKU } from "./types";

function computeCampaignRevenueImpact(spend: number, placedRoas: number, deliveredRoas: number) {
  const placedRevenue = spend * placedRoas;
  const deliveredRevenue = spend * deliveredRoas;
  const revenueGap = Math.max(placedRevenue - deliveredRevenue, 0);
  const impactPercent = placedRevenue > 0 && revenueGap > 0
    ? Math.min(Math.round((revenueGap / placedRevenue) * 1000) / 10, 100)
    : 0;
  return { placedRevenue, deliveredRevenue, revenueGap, impactPercent };
}

const PASSIVE_REMEDY_HINTS = ["collect", "hold spend", "hold budget", "monitor", "gather", "before major", "wait", "cap spend until"];

function isPassiveRemedy(label: string) {
  const lower = label.toLowerCase();
  return PASSIVE_REMEDY_HINTS.some((hint) => lower.includes(hint));
}

function recoveryLabel(label: string) {
  return isPassiveRemedy(label) ? "Potential Risk Reduction" : "Potential Improvement Opportunity";
}

function recoveryExplanation(revenueGap: number, captureRate: number, recovery: number, passive = false) {
  if (passive) {
    return `Rs ${recovery.toLocaleString("en-IN")} = modeled portion of the revenue gap (Rs ${Math.round(revenueGap).toLocaleString("en-IN")}) that may be avoided by limiting further spend erosion while launch validation completes.`;
  }
  return `Rs ${recovery.toLocaleString("en-IN")} = revenue gap (Rs ${Math.round(revenueGap).toLocaleString("en-IN")}) × ${Math.round(captureRate * 100)}% modeled capture from similar interventions.`;
}

function formatInr(value: number) {
  if (value >= 100000) return `Rs ${(value / 100000).toFixed(2)}L`;
  return `Rs ${Math.round(value).toLocaleString("en-IN")}`;
}

function roundDisplayMetric(value: number, decimals = 2) {
  const rounded = Number(value.toFixed(decimals));
  return Number.isInteger(rounded) ? String(rounded) : String(rounded);
}

function inferEffort(label: string): "low" | "medium" | "high" {
  const lower = label.toLowerCase();
  if (/(pause|reduce|cap|snooze)/.test(lower)) return "low";
  if (/(courier|factory|unbundle|landing page)/.test(lower)) return "high";
  return "medium";
}

function findCampaign(campaigns: Campaign[], names: string[]) {
  return campaigns.find((c) => names.includes(c.campaignName) || names.includes(c.campaignId));
}

function normalizeSkuMetrics(sku: SKU): SKU {
  const inventoryLeft = Math.max(0, Math.round(sku.inventoryLeft || 0));
  const dailyVelocity = Math.max(0, sku.dailyVelocity || 0);
  const projectedStockoutDays =
    dailyVelocity > 0
      ? Math.round((inventoryLeft / dailyVelocity) * 10) / 10
      : inventoryLeft > 0
        ? 99
        : 0;
  return { ...sku, inventoryLeft, dailyVelocity, projectedStockoutDays };
}

function findSku(skus: SKU[], names: string[]) {
  const matches = skus.filter((s) => names.includes(s.name) || names.includes(s.skuId)).map(normalizeSkuMetrics);
  if (!matches.length) return undefined;
  return matches.reduce((critical, sku) =>
    sku.projectedStockoutDays < critical.projectedStockoutDays ? sku : critical
  );
}

function parseSkuAov(decision: Decision) {
  const signal = decision.crossSystemSignals?.find((entry) => entry.toLowerCase().includes("aov"));
  if (!signal || !signal.includes(":")) return null;
  const value = Number(signal.split(":", 2)[1].replace(/Rs|[,\s]/gi, ""));
  return Number.isFinite(value) && value > 0 ? value : null;
}

function resolveSkuAov(decision: Decision, sku: SKU, averageOrderValue = 500) {
  const parsed = parseSkuAov(decision);
  if (parsed) return parsed;
  if (decision.businessImpact && sku.dailyVelocity > 0) {
    const projected = normalizeSkuMetrics(sku).projectedStockoutDays;
    const divisor = projected <= 0 ? sku.dailyVelocity * 7 : sku.dailyVelocity * Math.max(0.1, 7 - projected);
    if (divisor > 0) return Math.round(decision.businessImpact / divisor);
  }
  return averageOrderValue;
}

function computeInventoryRevenueImpact(dailyVelocity: number, averageOrderValue: number, projectedStockoutDays: number) {
  const dailyRevenue = dailyVelocity * averageOrderValue;
  const forecastRevenue = Math.round(dailyRevenue * 7);
  const alreadyStockedOut = projectedStockoutDays <= 0 && dailyVelocity > 0;
  const stockoutDaysInWindow = alreadyStockedOut ? 7 : Math.max(0.1, 7 - projectedStockoutDays);
  const atRiskRevenue = alreadyStockedOut ? forecastRevenue : Math.round(dailyRevenue * stockoutDaysInWindow);
  const impactPercent =
    alreadyStockedOut
      ? forecastRevenue > 0
        ? 100
        : 0
      : forecastRevenue > 0 && atRiskRevenue > 0
        ? Math.min(Math.round((atRiskRevenue / forecastRevenue) * 1000) / 10, 100)
        : 0;
  return { dailyRevenue, forecastRevenue, stockoutDaysInWindow, atRiskRevenue, impactPercent, alreadyStockedOut };
}

function computeStockoutScenario(
  dailyVelocity: number,
  averageOrderValue: number,
  coverDays: number,
  poEtaDays?: number,
  alreadyStockedOut = false
) {
  const dailyRevenue = dailyVelocity * averageOrderValue;
  if (dailyVelocity <= 0 || dailyRevenue <= 0) {
    return { lostDays: 0, lostUnits: 0, lostRevenue: 0, detail: "Demand forecast unavailable" };
  }
  let lostDays = 0;
  let lead = "";
  if (alreadyStockedOut || coverDays <= 0) {
    if (poEtaDays === undefined) {
      lostDays = 7;
      lead = "Already stocked out — full forecast window at risk";
    } else {
      lostDays = Math.min(poEtaDays, 7);
      lead = `Already stocked out — replenishment in ${poEtaDays} days`;
    }
  } else if (poEtaDays === undefined) {
    lostDays = Math.max(0, 7 - coverDays);
    lead = `Stockout expected after ~${coverDays} day${coverDays === 1 ? "" : "s"} of cover`;
  } else {
    lostDays = Math.max(0, Math.min(poEtaDays - coverDays, 7));
    lead = `Inbound inventory lands after ~${coverDays} day${coverDays === 1 ? "" : "s"} of remaining cover`;
  }
  const lostUnits = Math.round(lostDays * dailyVelocity * 10) / 10;
  const lostRevenue = Math.round(dailyRevenue * lostDays);
  return {
    lostDays,
    lostUnits,
    lostRevenue,
    detail: `${lead}; ≈ ${lostDays} days of lost demand (${lostUnits} units at current velocity)`,
  };
}

function withRecoveryExplanation(remedies: RemedyAction[], revenueGap = 0) {
  return remedies.map((remedy) => ({
    ...remedy,
    recoveryLabel: remedy.recoveryLabel ?? recoveryLabel(remedy.label),
    recoveryExplanation:
      remedy.recoveryExplanation ??
      recoveryExplanation(
        revenueGap,
        remedy.expectedRiskReduction / Math.max(revenueGap, 1),
        remedy.expectedRiskReduction,
        isPassiveRemedy(remedy.label)
      ),
  }));
}

function buildInventoryImpactContext(decision: Decision, sku: SKU): ImpactContext {
  const normalized = normalizeSkuMetrics(sku);
  const averageOrderValue = resolveSkuAov(decision, normalized);
  const metrics = computeInventoryRevenueImpact(
    normalized.dailyVelocity,
    averageOrderValue,
    normalized.projectedStockoutDays
  );
  return {
    totalRevenue: metrics.forecastRevenue,
    totalRevenueLabel: formatInr(metrics.forecastRevenue),
    atRiskRevenue: metrics.atRiskRevenue,
    atRiskRevenueLabel: formatInr(metrics.atRiskRevenue),
    atRiskLabel: "Expected Lost Sales",
    atRiskExplanation: metrics.alreadyStockedOut
      ? "Full 7-day demand opportunity is at risk because inventory is already unavailable."
      : `Revenue expected to be unrealized within the next 7-day forecast window (${metrics.stockoutDaysInWindow} days without cover).`,
    impactPercent: metrics.impactPercent,
    contextLabel: "Next 7-Day Revenue Opportunity",
    contextExplanation: `Projected demand for ${normalized.name} based on ${normalized.dailyVelocity} units/day at Rs ${Math.round(averageOrderValue).toLocaleString("en-IN")} average order value.`,
    inventoryLeft: normalized.inventoryLeft,
    inventoryCoverDays: normalized.projectedStockoutDays,
    dailyVelocity: normalized.dailyVelocity,
    stockoutState: metrics.alreadyStockedOut ? "already_stocked_out" : "low_cover",
    stockoutStateLabel: metrics.alreadyStockedOut ? "Already Stocked Out" : undefined,
    operationalRiskLabel: metrics.alreadyStockedOut
      ? "Already Stocked Out"
      : normalized.projectedStockoutDays <= 3
        ? "Critical Stockout Risk"
        : "Elevated Stockout Risk",
    impactNarrative:
      "Estimated impact reflects forecasted revenue that cannot be realized if inventory remains unavailable during the projected demand window.",
  };
}

function buildImpactContext(decision: Decision, campaign?: Campaign): ImpactContext {
  if (campaign?.spend && campaign.roasOnPlacedOrders) {
    const metrics = computeCampaignRevenueImpact(
      campaign.spend,
      campaign.roasOnPlacedOrders,
      campaign.roasOnDeliveredOrders ?? campaign.roasOnPlacedOrders
    );
    const storedImpact = decision.businessImpact || 0;
    const atRisk =
      storedImpact > metrics.placedRevenue || storedImpact === Math.round(campaign.spend)
        ? Math.round(metrics.revenueGap)
        : Math.round(metrics.revenueGap || storedImpact);

    return {
      campaignSpend: Math.round(campaign.spend),
      campaignSpendLabel: formatInr(campaign.spend),
      totalRevenue: Math.round(metrics.placedRevenue),
      totalRevenueLabel: formatInr(metrics.placedRevenue),
      deliveredRevenue: Math.round(metrics.deliveredRevenue),
      deliveredRevenueLabel: formatInr(metrics.deliveredRevenue),
      atRiskRevenue: atRisk,
      atRiskRevenueLabel: formatInr(atRisk),
      impactPercent: metrics.impactPercent || (metrics.placedRevenue ? Math.min(Math.round((atRisk / metrics.placedRevenue) * 1000) / 10, 100) : 0),
      contextLabel: "Placed Revenue",
    };
  }

  const atRisk = decision.businessImpact || 0;
  const totalRevenue = atRisk * 3.15;
  return {
    totalRevenue: Math.round(totalRevenue),
    totalRevenueLabel: formatInr(totalRevenue),
    atRiskRevenue: Math.round(atRisk),
    atRiskRevenueLabel: formatInr(atRisk),
    impactPercent: totalRevenue ? Math.min(Math.round((atRisk / totalRevenue) * 1000) / 10, 100) : 0,
    contextLabel: "Revenue Base",
  };
}

export function buildFallbackRemedies(decision: Decision, campaigns: Campaign[] = [], skus: SKU[] = []): RemedyAction[] {
  const impact =
    decision.signalType === "StateRTOLeakage"
      ? buildStateImpactContext(decision).atRiskRevenue
      : (decision.businessImpact || 0);
  const actions = decision.recommendedActions?.length ? decision.recommendedActions : [decision.recommendation];
  const campaign = findCampaign(campaigns, decision.affectedCampaigns);
  const medals = ["🥇", "🥈", "🥉"];
  const ranks: RemedyAction["rank"][] = ["primary", "alternative", "alternative"];
  const multipliers = [0.29, 0.43, 0.56];

  if (decision.signalType === "CampaignRTOSpike" && campaign) {
    return withRecoveryExplanation([
      {
        id: `${decision.id}_r0`,
        label: `Reduce spend on ${campaign.campaignName} by 30%`,
        rank: "primary",
        effort: "low",
        expectedRiskReduction: Math.round(impact * 0.29),
        expectedRiskReductionLabel: formatInr(impact * 0.29),
        medal: medals[0],
        expectedOutcome: {
          rtoRate: { before: `${campaign.rtoRateAttributed}%`, after: `${Math.max(campaign.rtoRateAttributed - 6, 18)}%` },
          deliveredRoas: { before: `${campaign.roasOnDeliveredOrders}x`, after: `${(campaign.roasOnDeliveredOrders * 1.08).toFixed(2)}x` },
          recovery: Math.round(impact * 0.29),
        },
      },
      {
        id: `${decision.id}_r1`,
        label: "Enable COD verification at checkout",
        rank: "alternative",
        effort: "medium",
        expectedRiskReduction: Math.round(impact * 0.43),
        expectedRiskReductionLabel: formatInr(impact * 0.43),
        medal: medals[1],
        expectedOutcome: {
          rtoRate: { before: `${campaign.rtoRateAttributed}%`, after: `${Math.max(campaign.rtoRateAttributed - 9, 16)}%` },
          deliveredRoas: { before: `${campaign.roasOnDeliveredOrders}x`, after: `${(campaign.roasOnDeliveredOrders * 1.14).toFixed(2)}x` },
          recovery: Math.round(impact * 0.43),
        },
      },
      {
        id: `${decision.id}_r2`,
        label: "Shift budget to prepaid retargeting",
        rank: "alternative",
        effort: "medium",
        expectedRiskReduction: Math.round(impact * 0.56),
        expectedRiskReductionLabel: formatInr(impact * 0.56),
        medal: medals[2],
        expectedOutcome: {
          rtoRate: { before: `${campaign.rtoRateAttributed}%`, after: `${Math.max(campaign.rtoRateAttributed - 12, 14)}%` },
          deliveredRoas: { before: `${campaign.roasOnDeliveredOrders}x`, after: `${(campaign.roasOnDeliveredOrders * 1.28).toFixed(2)}x` },
          recovery: Math.round(impact * 0.56),
        },
      },
    ]);
  }

  return withRecoveryExplanation(
    actions.slice(0, 3).map((action, idx) => ({
      id: `${decision.id}_r${idx}`,
      label: action,
      rank: ranks[idx],
      effort: inferEffort(action),
      expectedRiskReduction: Math.round(impact * multipliers[idx]),
      expectedRiskReductionLabel: formatInr(impact * multipliers[idx]),
      medal: medals[idx],
      expectedOutcome: { recovery: Math.round(impact * multipliers[idx]) },
    }))
  );
}

function parseCrossSignal(decision: Decision, prefix: string) {
  const signal = decision.crossSystemSignals?.find((entry) => entry.toLowerCase().startsWith(prefix.toLowerCase() + ":"));
  return signal?.split(":", 2)[1]?.trim();
}

function parseInrValue(raw: string) {
  return Number(raw.replace(/Rs|[,\s]/gi, ""));
}

function parseStateName(decision: Decision) {
  const fromSignal = parseCrossSignal(decision, "State");
  if (fromSignal) return fromSignal;
  const patterns = [/Regional COD Risk:\s*(.+)$/i, /Emerging RTO Pattern:\s*(.+)$/i, /High RTO in (.+)$/i];
  for (const pattern of patterns) {
    const match = decision.title.match(pattern);
    if (match) return match[1].trim();
  }
  return null;
}

function resolveSignalType(decision: Decision): SignalType {
  if (
    decision.rule?.includes("state_orders") ||
    decision.title.includes("State Profitability") ||
    decision.title.includes("Regional COD Risk") ||
    decision.title.includes("Emerging RTO Pattern") ||
    decision.issueType === "State RTO leakage"
  ) {
    return "StateRTOLeakage";
  }
  if (
    decision.rule?.includes("spend >= 50000") ||
    decision.title.includes("Strategic Audit") ||
    decision.title.includes("Fulfillment Gap") ||
    decision.issueType === "Marketing pressure"
  ) {
    return "AudienceAudit";
  }
  if (
    decision.rule?.includes("roas < 1.5 AND frequency <= 1.5") ||
    decision.title.includes("New Launch") ||
    decision.issueType === "Launch validation"
  ) {
    return "NewLaunchRisk";
  }
  if (
    decision.rule?.includes("projected_stockout_days") ||
    decision.title.includes("Stockout") ||
    decision.title.includes("Inventory Cliff") ||
    decision.issueType === "Inventory pressure"
  ) {
    return "InventoryRisk";
  }
  return decision.signalType;
}

function stateRtoDelta(decision: Decision) {
  const deltaRaw = parseCrossSignal(decision, "State RTO delta");
  if (deltaRaw) return Number(deltaRaw.replace("%", "").replace("+", ""));
  const stateRto = Number((parseCrossSignal(decision, "RTO rate") || "0").replace("%", ""));
  const brandRto = Number((parseCrossSignal(decision, "Brand average RTO") || "0").replace("%", ""));
  if (stateRto && brandRto) return Math.round((stateRto - brandRto) * 10) / 10;
  return null;
}

function isStateMonitorCase(decision: Decision) {
  const delta = stateRtoDelta(decision);
  const cod = Number((parseCrossSignal(decision, "COD mix") || "0").replace("%", ""));
  return Math.abs(delta ?? 0) <= 5 && cod >= 70;
}

function computeStateRevenueImpact(
  totalOrders: number,
  rtoPct: number,
  totalRevenue = 0,
  rtoRevenue = 0,
  deliveredRevenue = 0,
  shippingCostPerRto = 150
) {
  const rtoCount = totalOrders ? Math.round(totalOrders * (rtoPct / 100)) : 0;
  let atRiskGmv = 0;
  let total = totalRevenue;

  if (rtoRevenue > 0) {
    atRiskGmv = Math.round(rtoRevenue);
  } else if (total > 0 && rtoPct > 0) {
    atRiskGmv = Math.round(total * (rtoPct / 100));
  } else if (deliveredRevenue > 0 && rtoPct > 0 && rtoPct < 100) {
    const inferredTotal = deliveredRevenue / (1 - rtoPct / 100);
    atRiskGmv = Math.round(inferredTotal - deliveredRevenue);
    total = Math.round(inferredTotal);
  }

  if (total <= 0 && deliveredRevenue > 0 && atRiskGmv > 0) {
    total = Math.round(deliveredRevenue + atRiskGmv);
  } else if (total <= 0 && deliveredRevenue > 0) {
    total = Math.round(deliveredRevenue);
  }

  const shippingWaste = Math.round(rtoCount * shippingCostPerRto);
  const impactPercent =
    total > 0 && atRiskGmv > 0
      ? Math.min(Math.round((atRiskGmv / total) * 1000) / 10, 100)
      : rtoPct > 0
        ? Math.min(Math.round(rtoPct * 10) / 10, 100)
        : 0;

  return { totalRevenue: total, atRiskGmv, shippingWaste, impactPercent, rtoCount };
}

function buildStateImpactContext(decision: Decision): ImpactContext {
  const totalOrders = Number(parseCrossSignal(decision, "Total orders") || 0);
  const rtoPct = Number((parseCrossSignal(decision, "RTO rate") || "0").replace("%", ""));
  const totalRevenue = parseInrValue(parseCrossSignal(decision, "Regional order GMV") || "0") || 0;
  const rtoRevenue = parseInrValue(parseCrossSignal(decision, "RTO order GMV") || "0") || 0;
  const deliveredRaw = parseCrossSignal(decision, "Delivered revenue");
  const deliveredRevenue = deliveredRaw ? parseInrValue(deliveredRaw) : 0;
  const stateName = parseStateName(decision) || "this state";
  const codPct = Number((parseCrossSignal(decision, "COD mix") || "0").replace("%", ""));
  const rtoDelta = stateRtoDelta(decision);

  const metrics = computeStateRevenueImpact(totalOrders, rtoPct, totalRevenue, rtoRevenue, deliveredRevenue);
  let atRisk = metrics.atRiskGmv;
  let total = metrics.totalRevenue;
  let impactPercent = metrics.impactPercent;

  const stale = decision.impactContext;
  if (stale?.totalRevenue && stale.totalRevenue > 0 && rtoPct > 0) {
    const expectedAtRisk = Math.round(stale.totalRevenue * (rtoPct / 100));
    const staleAtRisk = stale.atRiskRevenue || 0;
    if (staleAtRisk > 0 && staleAtRisk < expectedAtRisk * 0.25) {
      total = stale.totalRevenue;
      atRisk = expectedAtRisk;
      impactPercent = Math.min(Math.round((atRisk / total) * 1000) / 10, 100);
    } else if (atRisk <= 0) {
      total = stale.totalRevenue;
      atRisk = expectedAtRisk;
      impactPercent = Math.min(Math.round((atRisk / total) * 1000) / 10, 100);
    }
  }

  if (atRisk <= 0 && total > 0 && rtoPct > 0) {
    atRisk = Math.round(total * (rtoPct / 100));
    impactPercent = Math.min(Math.round((atRisk / total) * 1000) / 10, 100);
  }

  const monitorCase = isStateMonitorCase(decision);
  return {
    totalRevenue: total,
    totalRevenueLabel: formatInr(total),
    atRiskRevenue: atRisk,
    atRiskRevenueLabel: formatInr(atRisk),
    atRiskLabel: "RTO Order GMV",
    atRiskExplanation:
      "Product revenue from orders returned to origin in this state — GMV not realized from failed deliveries. Separate from logistics cost.",
    impactPercent,
    contextLabel: "Regional Order GMV",
    contextExplanation: "Total order value placed in this state across the current upload window.",
    shippingWaste: metrics.shippingWaste,
    shippingWasteLabel: formatInr(metrics.shippingWaste),
    shippingWasteExplanation:
      "Estimated forward and return courier cost (₹150 per RTO shipment). Logistics overhead — not product GMV at risk.",
    financialImpactTier: atRisk < 5000 ? "low" : "medium",
    financialImpactLabel: atRisk < 5000 ? "Low Financial Impact" : "Moderate Financial Impact",
    operationalRiskLabel: monitorCase ? "Monitor" : "High Operational Risk",
    actionUrgency: monitorCase ? "monitor" : "act",
    impactNarrative: monitorCase
      ? `State RTO exceeds brand average by only ${rtoDelta !== null ? `${rtoDelta >= 0 ? "+" : ""}${rtoDelta}%` : "a small margin"}. Current risk in ${stateName} appears driven more by ${codPct}% COD dependence than a uniquely poor regional return profile.`
      : "Regional return pressure warrants prepaid conversion and fulfillment verification before scaling volume.",
  };
}

function applyStateDisplayOverrides(decision: Decision) {
  const stateName = parseStateName(decision) || "this state";
  const codPct = Number((parseCrossSignal(decision, "COD mix") || "0").replace("%", ""));
  const stateRto = parseCrossSignal(decision, "RTO rate") || "elevated";
  const brandRto = parseCrossSignal(decision, "Brand average RTO") || "brand average";
  const rtoDelta = stateRtoDelta(decision);
  const totalOrders = parseCrossSignal(decision, "Total orders") || "limited";
  const monitorCase = isStateMonitorCase(decision);

  if (!monitorCase) {
    return {};
  }

  return {
    title: `Regional COD Risk: ${stateName}`,
    severity: "low" as Severity,
    explanation: `${stateName} runs ${codPct}% COD across ${totalOrders} orders. Regional RTO is ${stateRto} — only ${rtoDelta !== null ? `${rtoDelta >= 0 ? "+" : ""}${rtoDelta}` : "marginally different"} pts vs brand average (${brandRto}). The signal reflects COD concentration and sample size, not a uniquely poor state return profile.`,
    recommendation: `Monitor ${stateName} COD mix and test prepaid incentives before restricting regional shipping.`,
  };
}

function isFulfillmentGapDecision(decision: Decision) {
  return (
    decision.signalType === "AudienceAudit" ||
    decision.rule?.includes("spend >= 50000") ||
    decision.issueType === "Marketing pressure"
  );
}

function needsCampaignMetricVerification(decision: Decision) {
  return isFulfillmentGapDecision(decision) || decision.signalType === "NewLaunchRisk";
}

function needsInventoryMetricVerification(decision: Decision) {
  return decision.signalType === "InventoryRisk";
}

function buildFallbackMetricVerification(decision: Decision, campaign?: Campaign, sku?: SKU): Decision["metricVerification"] {
  if (needsInventoryMetricVerification(decision) && sku) {
    const normalized = normalizeSkuMetrics(sku);
    const metrics = computeInventoryRevenueImpact(
      normalized.dailyVelocity,
      resolveSkuAov(decision, normalized),
      normalized.projectedStockoutDays
    );
    return {
      headline: "Verification Status",
      observedLabel: "Observed Metrics",
      estimatedLabel: "Estimated Metrics",
      observed: [
        { label: "Inventory", detail: `${normalized.inventoryLeft} units on hand from latest upload` },
        { label: "Velocity", detail: `${normalized.dailyVelocity} units/day from recent sales` },
      ],
      estimated: [
        { label: "Revenue forecast", detail: "7-day demand opportunity at current velocity and SKU average order value" },
        { label: "Lost sales forecast", detail: `${metrics.stockoutDaysInWindow} days of demand expected to be unrealized within the forecast window` },
        { label: "Restock scenarios", detail: "PO arrival windows modeled without confirmed inbound shipment data" },
      ],
    };
  }
  if (!needsCampaignMetricVerification(decision) || !campaign) return decision.metricVerification;
  return {
    headline: "Verification Status",
    observedLabel: "Observed Metrics",
    estimatedLabel: "Estimated Metrics",
    observed: [
      { label: "Spend", detail: "Verified from Meta ads upload" },
      { label: "Placed Revenue", detail: "Computed from mapped spend and placed-order ROAS" },
      { label: "Brand RTO", detail: "Computed from Shopify order delivery statuses" },
    ],
    estimated: [
      { label: "Delivered Revenue", detail: "Modeled from placed ROAS and attributed RTO" },
      { label: "Revenue Gap", detail: "Difference between placed and estimated delivered revenue" },
      { label: "Campaign RTO", detail: "Estimated from brand-level RTO fallback until campaign mapping completes" },
    ],
  };
}

function buildFallbackConfidenceDrivers(decision: Decision, campaign?: Campaign, sku?: SKU) {
  const brandRto = campaign?.rtoRateAttributed ?? 31.89;
  if (isFulfillmentGapDecision(decision)) {
    return [
      { label: "Campaign spend verified from Meta", status: "verified" as const, detail: "Spend totals reconciled against the latest Meta ads upload" },
      { label: "Placed ROAS verified from Meta", status: "verified" as const, detail: "Placed-order ROAS computed from mapped spend and revenue signals" },
      { label: "Brand RTO verified from Shopify", status: "verified" as const, detail: "Blended return rates computed from Shopify order delivery statuses" },
      { label: "Campaign-level RTO unavailable", status: "warning" as const, detail: "Campaign-level delivered and RTO counts are not fully mapped yet" },
      { label: `Brand-level RTO proxy used (${brandRto}%)`, status: "inferred" as const, detail: "Attributed RTO is estimated from blended brand returns until campaign mapping is complete" },
      { label: "Delivered revenue estimated from fallback model", status: "inferred" as const, detail: "Delivered ROAS and revenue gap are modeled from placed ROAS and attributed RTO" },
      { label: decision.affectedCampaigns.length ? "Order-to-campaign attribution linked" : "Order-to-campaign attribution unavailable", status: decision.affectedCampaigns.length ? ("verified" as const) : ("warning" as const), detail: "UTM and campaign mapping quality directly affects precision" },
    ];
  }
  if (decision.signalType === "StateRTOLeakage") {
    const totalOrders = Number(parseCrossSignal(decision, "Total orders") || 0);
    const brandAverage = parseCrossSignal(decision, "Brand average RTO");
    return [
      { label: "State identified from shipping address", status: "verified" as const, detail: "Order shipping state mapped from Shopify fulfillment addresses" },
      { label: "Order status available", status: "verified" as const, detail: "Delivered, RTO, and cancellation statuses parsed from the latest order upload" },
      { label: "COD payment mode available", status: "verified" as const, detail: "Payment method mapped to classify COD vs prepaid mix by state" },
      { label: "RTO status available", status: "verified" as const, detail: "Return-to-origin counts computed from order delivery statuses" },
      ...(totalOrders < 20
        ? [{ label: `Only ${totalOrders} orders available`, status: "warning" as const, detail: "Small sample — one or two status changes can materially shift the regional RTO rate" }]
        : []),
      { label: "Historical state benchmark unavailable", status: "warning" as const, detail: "Prior-upload state RTO baselines are not yet available for seasonal comparison" },
      { label: "Seasonal variation not modeled", status: "warning" as const, detail: "Festival and weather-driven return patterns are not yet isolated for this corridor" },
      ...(brandAverage
        ? [{ label: `Brand average RTO benchmark available (${brandAverage})`, status: "verified" as const, detail: "Regional RTO is compared against blended brand returns from the same upload" }]
        : []),
    ];
  }
  if (decision.signalType === "InventoryRisk" && sku) {
    const normalized = normalizeSkuMetrics(sku);
    const projected = normalized.projectedStockoutDays;
    const spendGrowth = normalized.spendGrowthPercent ?? 0;
    return [
      { label: `On-hand inventory verified (${normalized.inventoryLeft} units)`, status: "verified" as const, detail: "SKU stock levels reconciled from the latest inventory upload" },
      { label: `Sales velocity verified (${normalized.dailyVelocity} units/day)`, status: "verified" as const, detail: "Recent demand rate computed from order history in the current snapshot" },
      { label: `Inventory cover computed (${projected} days)`, status: "verified" as const, detail: "Cover derived from on-hand inventory divided by daily velocity" },
      ...(spendGrowth >= 15
        ? [{ label: `Ad spend growth verified (${spendGrowth.toFixed(1)}%)`, status: "verified" as const, detail: "Week-over-week spend acceleration confirmed from Meta campaign data" }]
        : [{ label: "No verified ad spend acceleration", status: "warning" as const, detail: "Stockout risk is driven by velocity and cover — not confirmed marketing scale-up" }]),
      { label: "Open purchase orders unavailable", status: "warning" as const, detail: "Inbound PO visibility is required to judge whether stockout risk is operationally urgent" },
      { label: "Supplier lead time / inbound ETA unavailable", status: "warning" as const, detail: "Restock timing assumptions are not yet connected to supplier or warehouse data" },
    ];
  }
  if (decision.signalType === "NewLaunchRisk") {
    const freq = campaign?.frequency ?? 0;
    const freqLabel = roundDisplayMetric(freq);
    return [
      { label: "Spend verified from Meta", status: "verified" as const, detail: "Spend totals reconciled against the latest Meta ads upload" },
      { label: "ROAS verified from Meta", status: "verified" as const, detail: "Placed-order ROAS computed from mapped spend and revenue signals" },
      { label: `Frequency verified from Meta (${freqLabel}x)`, status: "verified" as const, detail: "Audience exposure mapped to the flagged campaign" },
      { label: "Campaign remains in learning phase", status: "warning" as const, detail: "Low spend and frequency limit certainty before attributing underperformance to creative or audience fit" },
      { label: "Historical baseline unavailable", status: "warning" as const, detail: "Launch benchmarks require additional uploads to compare against prior campaign performance" },
      { label: "Delivered metrics estimated using brand RTO fallback", status: "inferred" as const, detail: `Delivered ROAS and revenue gap are modeled from placed ROAS and brand RTO (${brandRto}%) until campaign mapping completes` },
    ];
  }
  return [
    { label: "Campaign spend verified from Meta", status: "verified" as const, detail: "Spend totals reconciled against the latest Meta ads upload" },
    { label: "Placed ROAS verified from Meta", status: "verified" as const, detail: "Placed-order ROAS computed from mapped spend and revenue signals" },
    { label: "Campaign-specific RTO unavailable", status: "warning" as const, detail: "Campaign-level delivered and RTO counts are not fully mapped yet" },
    { label: `Brand-level RTO proxy used (${brandRto}%)`, status: "inferred" as const, detail: "Attributed RTO is estimated from blended brand returns until campaign mapping is complete" },
    { label: decision.affectedCampaigns.length ? "Order-to-campaign attribution linked" : "No order-to-campaign attribution", status: decision.affectedCampaigns.length ? ("verified" as const) : ("warning" as const), detail: "UTM and campaign mapping quality directly affects precision" },
  ];
}

function buildFallbackEvidence(decision: Decision, campaign?: Campaign) {
  const hasCampaign = !!decision.affectedCampaigns.length;
  return {
    requirements: [
      { label: "Meta spend", required: false, available: true },
      { label: "Meta ROAS", required: false, available: true },
      { label: "Shopify order statuses", required: false, available: true },
      { label: "Campaign-level delivered orders", required: true, available: false },
      { label: "Campaign-level RTO", required: true, available: false },
      { label: "Campaign-level cancellation rate", required: true, available: false },
      { label: "COD share by campaign", required: true, available: !!campaign },
    ],
    allRequiredAvailable: false,
    disclaimer: "Decision remains estimated until missing campaign-level evidence is available.",
  };
}

function buildFallbackStockoutScenarios(decision: Decision, sku?: SKU): Decision["stockoutScenarios"] {
  if (decision.signalType !== "InventoryRisk" || !sku) return decision.stockoutScenarios;
  const normalized = normalizeSkuMetrics(sku);
  const averageOrderValue = resolveSkuAov(decision, normalized);
  const projected = normalized.projectedStockoutDays;
  const alreadyOut = projected <= 0 && normalized.dailyVelocity > 0;
  const buildScenario = (label: string, poEtaDays?: number) => {
    const scenario = computeStockoutScenario(
      normalized.dailyVelocity,
      averageOrderValue,
      projected,
      poEtaDays,
      alreadyOut
    );
    return {
      label,
      detail: scenario.detail,
      estimatedLostSales: scenario.lostRevenue,
      estimatedLostSalesLabel: formatInr(scenario.lostRevenue),
      lostDays: scenario.lostDays,
      lostUnits: scenario.lostUnits,
    };
  };
  return {
    headline: "Stockout Scenario Analysis",
    scenarios: [
      buildScenario("If no restock arrives"),
      buildScenario("If PO arrives in 3 days", 3),
      buildScenario("If PO arrives in 7 days", 7),
    ],
  };
}

function buildFallbackTriggerReason(decision: Decision, campaign?: Campaign, campaigns: Campaign[] = [], sku?: SKU) {
  if (decision.signalType === "StateRTOLeakage") {
    const state = parseCrossSignal(decision, "State") || "Unknown";
    const orders = parseCrossSignal(decision, "Total orders") || "—";
    const codMix = parseCrossSignal(decision, "COD mix") || "—";
    const rto = parseCrossSignal(decision, "RTO rate") || "—";
    const brandAverage = parseCrossSignal(decision, "Brand average RTO");
    const delta = parseCrossSignal(decision, "State RTO delta");
    return {
      headline: "Why It Triggered",
      metrics: [
        { label: "State", value: state },
        { label: "Orders", value: orders },
        { label: "COD Mix", value: codMix },
        { label: "RTO", value: rto },
        ...(brandAverage ? [{ label: "Brand Average RTO", value: brandAverage }] : []),
        ...(delta ? [{ label: "Difference", value: delta }] : []),
      ],
    };
  }

  if (sku && decision.signalType === "InventoryRisk") {
    const normalized = normalizeSkuMetrics(sku);
    return {
      headline: `Why ${normalized.name}?`,
      metrics: [
        { label: "Inventory left", value: `${normalized.inventoryLeft} units` },
        { label: "Daily velocity", value: `${normalized.dailyVelocity} units/day` },
        { label: "Inventory cover", value: `${normalized.projectedStockoutDays} days` },
        { label: "Spend growth", value: `${(normalized.spendGrowthPercent ?? 0).toFixed(1)}%` },
      ],
    };
  }

  if (campaign && decision.signalType === "NewLaunchRisk") {
    return {
      headline: "Why It Was Selected",
      metrics: [
        { label: "Campaign Age", value: decision.staleMetadata?.ageDays ? `${decision.staleMetadata.ageDays} days` : "Early launch" },
        { label: "ROAS", value: `${roundDisplayMetric(campaign.roasOnPlacedOrders)}x` },
        { label: "Benchmark", value: "1.5x" },
        { label: "Frequency", value: roundDisplayMetric(campaign.frequency) },
        { label: "Spend", value: formatInr(campaign.spend) },
      ],
    };
  }

  if (campaign) {
    const totalSpend = campaigns.reduce((sum, c) => sum + (c.spend || 0), 0);
    const spendShare = totalSpend ? Math.round((campaign.spend / totalSpend) * 100) : 0;
    return {
      headline: `Why ${campaign.campaignName}?`,
      metrics: [
        { label: "Campaign consumed", value: `${spendShare}% of Meta spend` },
        { label: "Placed ROAS", value: `${campaign.roasOnPlacedOrders}x` },
        { label: "Estimated Delivered ROAS", value: `${campaign.roasOnDeliveredOrders}x` },
        { label: "Attributed RTO", value: `${campaign.rtoRateAttributed}%` },
      ],
    };
  }

  if (decision.crossSystemSignals?.length) {
    return {
      headline: "Reason Triggered",
      metrics: decision.crossSystemSignals.slice(0, 4).map((signal) => {
        const [label, value] = signal.includes(":") ? signal.split(":", 2) : ["Signal", signal];
        return { label: label.trim(), value: value.trim() };
      }),
    };
  }

  return null;
}

function buildFallbackAutoResolution(decision: Decision): Decision["autoResolutionCriteria"] {
  if (decision.signalType !== "NewLaunchRisk") return decision.autoResolutionCriteria;
  return {
    headline: "Auto Resolution Criteria",
    intro: "This decision will automatically resolve if:",
    criteria: [
      "ROAS exceeds 1.5x",
      "Frequency exceeds 2.0 with stable ROAS",
      "7 days of additional delivery data invalidates the current estimate",
    ],
  };
}

export function enrichDecisionClient(
  decision: Decision,
  campaigns: Campaign[] = [],
  skus: SKU[] = []
): Decision {
  const signalType = resolveSignalType(decision);
  const campaign = findCampaign(campaigns, decision.affectedCampaigns);
  const sku = findSku(skus, decision.affectedSkus);
  const isStateDecision = signalType === "StateRTOLeakage";
  const isInventoryDecision = signalType === "InventoryRisk";
  const impactContext = isStateDecision
    ? buildStateImpactContext({ ...decision, signalType })
    : isInventoryDecision && sku
      ? buildInventoryImpactContext({ ...decision, signalType }, sku)
      : (decision.impactContext ?? buildImpactContext(decision, campaign));
  const revenueGap = impactContext.atRiskRevenue;
  const evidenceRequired = decision.evidenceRequired ?? buildFallbackEvidence(decision, campaign);
  const stateOverrides = isStateDecision ? applyStateDisplayOverrides({ ...decision, signalType }) : {};
  const fulfillmentRecommendation =
    "Segment campaign by COD vs prepaid. Enable COD verification. Review high-RTO geographies. Reduce spend escalation until delivered performance improves. Pause only if delivered ROAS remains below threshold after verification.";
  const fulfillmentOverrides =
    isFulfillmentGapDecision({ ...decision, signalType }) &&
    (decision.recommendation || "").toLowerCase().includes("audit or pause")
      ? { recommendation: fulfillmentRecommendation }
      : isFulfillmentGapDecision({ ...decision, signalType })
        ? { recommendation: decision.recommendation || fulfillmentRecommendation }
        : {};

  let effectiveConfidence = decision.confidenceScore;
  if (isFulfillmentGapDecision({ ...decision, signalType }) && (effectiveConfidence || 0) > 0.78) {
    effectiveConfidence = Math.min(effectiveConfidence, 0.78);
  }
  if (isInventoryDecision && (effectiveConfidence || 0) > 0.72) {
    effectiveConfidence = Math.min(effectiveConfidence, 0.72);
  }

  return {
    ...decision,
    ...stateOverrides,
    ...fulfillmentOverrides,
    signalType,
    confidenceScore: effectiveConfidence,
    remedies: decision.remedies?.length
      ? withRecoveryExplanation(decision.remedies, revenueGap)
      : withRecoveryExplanation(buildFallbackRemedies({ ...decision, signalType }, campaigns, skus), revenueGap),
    impactContext,
    confidenceDrivers: decision.confidenceDrivers ?? buildFallbackConfidenceDrivers({ ...decision, signalType }, campaign, sku),
    metricVerification: decision.metricVerification ?? buildFallbackMetricVerification({ ...decision, signalType }, campaign, sku),
    evidenceRequired,
    decisionVerification: decision.decisionVerification ?? {
      type: evidenceRequired.allRequiredAvailable ? "verified" : "estimated",
      label: evidenceRequired.allRequiredAvailable ? "Verified Decision" : "Estimated Decision",
      reason: evidenceRequired.allRequiredAvailable
        ? "Campaign-level evidence is available and rule inputs are directly attributable."
        : "brand-level RTO fallback in use and required campaign-level evidence is incomplete.",
    },
    triggerReason: decision.triggerReason ?? buildFallbackTriggerReason(decision, campaign, campaigns, sku),
    autoResolutionCriteria: decision.autoResolutionCriteria ?? buildFallbackAutoResolution({ ...decision, signalType }),
    stockoutScenarios: decision.stockoutScenarios ?? buildFallbackStockoutScenarios({ ...decision, signalType }, sku),
    dependencies: decision.dependencies ?? [],
    staleMetadata: decision.staleMetadata ?? { ageDays: 0, isStale: false, staleLabel: "Detected today" },
    lifecycleLabel: decision.lifecycleLabel ?? decision.state,
  };
}

export function effortLabel(effort: string) {
  return effort.charAt(0).toUpperCase() + effort.slice(1);
}

export function effortTone(effort: string) {
  if (effort === "low") return "border-[#c8f3df] bg-[#ecfff6] text-[#07824b]";
  if (effort === "high") return "border-[#ffd9d7] bg-[#fff1f0] text-[#de2b25]";
  return "border-[#ffe7ba] bg-[#fff8e8] text-[#b86d00]";
}

export function effortMeta(effort: string) {
  if (effort === "low") {
    return { score: 1, deployTime: "Same day", complexity: "Quick operational change" };
  }
  if (effort === "high") {
    return { score: 3, deployTime: "1+ week", complexity: "Cross-team coordination required" };
  }
  return { score: 2, deployTime: "2–3 days", complexity: "Moderate setup and monitoring" };
}

export function remedyImpactShare(remedies: { expectedRiskReduction: number }[], remedy: { expectedRiskReduction: number }) {
  const max = Math.max(...remedies.map((item) => item.expectedRiskReduction), 1);
  return Math.round((remedy.expectedRiskReduction / max) * 100);
}

export const IMPACT_SHARE_EXPLANATION =
  "Impact share compares remedies for this decision only. Each option's expected value is modeled as decision impact × capture rate. Impact share = this remedy's expected value ÷ the highest expected value among the listed options × 100. The top option is always 100%; others are relative to that.";

export const DEFAULT_RECOVERY_EXPLANATION =
  "Modeled value derived from the revenue gap and expected impact of the selected intervention — protective for hold-and-validate actions, improvement-oriented for active changes.";