export const SIGNAL_THRESHOLDS = {
  inventoryRisk: {
    projectedStockoutDaysMax: 7,
    spendGrowthPercentMin: 15,
    severity: "high",
    confidence: 0.82
  },
  creativeFatigue: {
    frequencyMin: 4,
    ctrDropPercentMin: 20,
    severity: "medium",
    confidence: 0.76
  },
  marginLeakage: {
    codRatioMin: 60,
    rtoRateOnDeliveredMin: 18,
    roasOnPlacedOrdersMin: 3,
    severity: "high",
    confidence: 0.85
  },
  campaignRtoSpike: {
    rtoRateAttributedMin: 25,
    codOrderCountMin: 50,
    severity: "high",
    confidence: 0.88
  },
  scalingOpportunity: {
    roasOnDeliveredOrdersMin: 4,
    repeatRateMin: 25,
    rtoRateOnDeliveredMax: 7,
    projectedStockoutDaysMin: 14,
    contributionMarginAfterRtoMin: 30,
    severity: "low",
    confidence: 0.79
  }
} as const;

export const VERIFICATION_THRESHOLDS = {
  inventoryReorder: {
    inventoryLevelIncreaseMin: 25,
    projectedStockoutDaysImprovementMin: 3,
    confidence: 0.81
  },
  spendReduction: {
    campaignSpendDecreaseMin: 15,
    confidence: 0.77
  },
  creativeRefresh: {
    fatigueScoreDecreaseMin: 20,
    confidence: 0.74
  },
  codCampaignPause: {
    flaggedCampaignSpendDropMin: 80,
    confidence: 0.91
  }
} as const;

export function calculateRtoRate(returnedOrders: number, deliveredOrders: number) {
  if (deliveredOrders <= 0) return 0;
  return (returnedOrders / deliveredOrders) * 100;
}

export function calculateRealizedRoas(revenueFromDeliveredOrders: number, adSpend: number) {
  if (adSpend <= 0) return 0;
  return revenueFromDeliveredOrders / adSpend;
}
