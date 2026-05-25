import { SIGNAL_THRESHOLDS, VERIFICATION_THRESHOLDS } from "./rules";
import { OperationalState } from "./types";

export const operationalState: OperationalState = {
  brandName: "Unigo Footwear",
  snapshots: [
    {
      snapshotId: "snap_001",
      createdAt: "2026-05-20T10:02:00+05:30",
      uploadSource: "shopify_orders",
      brandId: "brand_unigo",
      snapshotVersion: 1,
      isBaseline: true
    }
  ],
  skus: [
    {
      skuId: "SKU-003",
      name: "Velar Runner",
      inventoryLeft: 180,
      dailyVelocity: 32,
      reorderThreshold: 240,
      projectedStockoutDays: 5.6,
      contributionMarginAfterRto: 28,
      spendGrowthPercent: 22
    },
    {
      skuId: "SKU-017",
      name: "Metro Slip-On",
      inventoryLeft: 1240,
      dailyVelocity: 56,
      reorderThreshold: 320,
      projectedStockoutDays: 22,
      contributionMarginAfterRto: 42,
      spendGrowthPercent: 8
    }
  ],
  campaigns: [
    {
      campaignId: "cmp_t2_cod_may",
      campaignName: "Tier2-COD-Lookalike-May",
      spend: 18400,
      spendGrowthPercent: 16,
      roasOnPlacedOrders: 3.8,
      roasOnDeliveredOrders: 2.1,
      ctr: 1.8,
      ctrDropPercent: 8,
      frequency: 3.2,
      audienceRegion: "Tier 2 North + West",
      codOrderCount: 186,
      codRatio: 67,
      rtoCountAttributed: 58,
      deliveredOrdersAttributed: 187,
      rtoRateAttributed: 31,
      contributionMarginAfterRto: 8
    },
    {
      campaignId: "cmp_velar_static_v1",
      campaignName: "Velar-Static-V1",
      spend: 9400,
      spendGrowthPercent: 22,
      roasOnPlacedOrders: 3.2,
      roasOnDeliveredOrders: 2.7,
      ctr: 1.1,
      ctrDropPercent: 34,
      frequency: 5.4,
      audienceRegion: "Pan India",
      codOrderCount: 41,
      codRatio: 45,
      rtoCountAttributed: 11,
      deliveredOrdersAttributed: 93,
      rtoRateAttributed: 11.8,
      contributionMarginAfterRto: 24
    },
    {
      campaignId: "cmp_prepaid_metro_rt",
      campaignName: "Prepaid-Metro-Retargeting",
      spend: 37500,
      spendGrowthPercent: 6,
      roasOnPlacedOrders: 5.3,
      roasOnDeliveredOrders: 5.1,
      ctr: 3.9,
      ctrDropPercent: 3,
      frequency: 2.1,
      audienceRegion: "Metro prepaid buyers",
      codOrderCount: 18,
      codRatio: 14,
      rtoCountAttributed: 5,
      deliveredOrdersAttributed: 126,
      rtoRateAttributed: 4,
      contributionMarginAfterRto: 42
    }
  ],
  customerSegments: [
    {
      segmentId: "seg_tier2_cod",
      name: "Tier 2 COD prospecting",
      prepaidRatio: 33,
      codRatio: 67,
      repeatRate: 13,
      returnRate: 9,
      rtoRateOnDelivered: 31
    },
    {
      segmentId: "seg_metro_prepaid",
      name: "Metro prepaid repeat buyers",
      prepaidRatio: 86,
      codRatio: 14,
      repeatRate: 31,
      returnRate: 4,
      rtoRateOnDelivered: 4
    }
  ],
  creatives: [
    {
      creativeId: "cr_velar_static_01",
      campaignId: "cmp_velar_static_v1",
      name: "Velar Static V1",
      fatigueScore: 78,
      previousFatigueScore: 48,
      frequency: 5.4,
      ctr: 1.1,
      hookRate: 22
    },
    {
      creativeId: "cr_metro_prepaid_04",
      campaignId: "cmp_prepaid_metro_rt",
      name: "Metro UGC Comfort Cut",
      fatigueScore: 18,
      previousFatigueScore: 20,
      frequency: 2.1,
      ctr: 3.9,
      hookRate: 41
    }
  ],
  mappingSuggestions: [
    { canonicalField: "revenue", uploadedColumn: "Gross Sales", confidence: 0.94, alternatives: ["Net Sales", "Total"], required: true },
    { canonicalField: "rto_count", uploadedColumn: "Undelivered", confidence: 0.88, alternatives: ["Returns", "RTO"], required: false },
    { canonicalField: "campaign_id", uploadedColumn: "utm_campaign", confidence: 0.82, alternatives: ["Campaign Name", "Ad Set"], required: true },
    { canonicalField: "sku_id", uploadedColumn: "Variant SKU", confidence: 0.91, alternatives: ["Product ID", "Item Code"], required: true },
    { canonicalField: "cod_orders", uploadedColumn: "Payment Method", confidence: 0.68, alternatives: ["COD", "Cash Orders"], required: false },
    { canonicalField: "delivered_orders", uploadedColumn: "Delivered", confidence: 0.96, alternatives: ["Fulfilled", "Confirmed Delivered"], required: true }
  ],
  decisions: [
    {
      id: "dec_campaign_rto_spike",
      title: "Pause Tier2-COD-Lookalike-May",
      signalType: "CampaignRTOSpike",
      issueType: "Campaign-level RTO spike",
      severity: "high",
      confidenceScore: SIGNAL_THRESHOLDS.campaignRtoSpike.confidence,
      businessImpact: 6200,
      impactLabel: "Losing Rs 6,200/day in realized margin",
      explanation: "This specific campaign is driving disproportionate RTO. Blended RTO masks the loss.",
      rule: "campaign.rto_rate_attributed >= 25 AND campaign.cod_order_count >= 50",
      recommendation: "Pause Tier2-COD-Lookalike-May immediately. Estimated daily margin loss: Rs 6,200.",
      affectedCampaigns: ["Tier2-COD-Lookalike-May"],
      affectedSkus: ["Velar Runner"],
      timestamp: "10:02 AM",
      state: "pending",
      crossSystemSignals: [
        "COD ratio is 67% on the flagged audience",
        "Placed-order ROAS is 3.8x, but realized ROAS is only 2.1x",
        "Contribution margin after RTO has compressed to 8%"
      ],
      riskProjection: [
        { horizon: "24 hr", impact: "Rs 6,200 additional realized margin loss" },
        { horizon: "48 hr", impact: "Rs 12,400 loss and blended ROAS contamination" },
        { horizon: "72 hr", impact: "Rs 18,600 loss with COD RTO compounding" }
      ],
      recommendedActions: ["Pause campaign", "Shift budget to prepaid retargeting", "Add prepaid incentive for Tier 2 traffic"],
      verificationSignals: [
        {
          label: "COD campaign pause verification",
          condition: `flagged campaign spend drops >= ${VERIFICATION_THRESHOLDS.codCampaignPause.flaggedCampaignSpendDropMin}%`,
          confidence: VERIFICATION_THRESHOLDS.codCampaignPause.confidence
        }
      ],
      timeline: [
        { id: "evt_1", time: "10:02 AM", title: "Campaign RTO spike detected", description: "Rule fired on delivered-order RTO attribution.", kind: "signal" },
        { id: "evt_2", time: "Now", title: "Awaiting operator action", description: "Take Action starts monitoring for spend drop.", kind: "system" }
      ],
      confidenceExplanation: "High confidence because both required thresholds fired: attributed RTO is 31% and COD order count is 186.",
      relationshipEdges: [
        { from: "Tier2-COD-Lookalike-May", to: "COD orders", label: "drives 67% COD mix", strength: "strong" },
        { from: "COD orders", to: "RTO probability", label: "elevates", strength: "strong" },
        { from: "RTO probability", to: "Realized ROAS", label: "reduces to 2.1x", strength: "strong" },
        { from: "Realized ROAS", to: "Margin", label: "compresses to 8%", strength: "strong" }
      ]
    },
    {
      id: "dec_inventory_risk",
      title: "Velar Runner stockout risk in 5.6 days",
      signalType: "InventoryRisk",
      issueType: "Inventory pressure",
      severity: "high",
      confidenceScore: SIGNAL_THRESHOLDS.inventoryRisk.confidence,
      businessImpact: 148000,
      impactLabel: "Rs 1.48L revenue at risk over 72 hr",
      explanation: "Spend is accelerating while Velar Runner inventory is below one week of cover.",
      rule: "projected_stockout_days <= 7 AND spend_growth_percent >= 15",
      recommendation: "Reduce spend by 15% or reorder within 48 hours.",
      affectedCampaigns: ["Velar-Static-V1"],
      affectedSkus: ["Velar Runner"],
      timestamp: "10:03 AM",
      state: "pending",
      crossSystemSignals: ["SKU velocity is 32 units/day", "Inventory left is 180 units", "Ad spend grew 22% week over week"],
      riskProjection: [
        { horizon: "24 hr", impact: "Inventory cover falls to 4.6 days" },
        { horizon: "48 hr", impact: "Reorder window becomes operationally tight" },
        { horizon: "72 hr", impact: "Paid traffic may drive demand into stockout" }
      ],
      recommendedActions: ["Create reorder today", "Reduce Velar prospecting spend by 15%", "Keep prepaid retargeting live"],
      verificationSignals: [
        {
          label: "Inventory reorder verification",
          condition: `inventory level increases >= ${VERIFICATION_THRESHOLDS.inventoryReorder.inventoryLevelIncreaseMin}% AND projected stockout days improves >= ${VERIFICATION_THRESHOLDS.inventoryReorder.projectedStockoutDaysImprovementMin}`,
          confidence: VERIFICATION_THRESHOLDS.inventoryReorder.confidence
        },
        {
          label: "Spend reduction verification",
          condition: `campaign spend decreases >= ${VERIFICATION_THRESHOLDS.spendReduction.campaignSpendDecreaseMin}%`,
          confidence: VERIFICATION_THRESHOLDS.spendReduction.confidence
        }
      ],
      timeline: [
        { id: "evt_3", time: "10:03 AM", title: "Inventory risk detected", description: "Projected stockout is 5.6 days with spend up 22%.", kind: "signal" }
      ],
      confidenceExplanation: "Both explicit thresholds fired with current-state data. Baseline mode prevents comparison inferences until the next upload.",
      relationshipEdges: [
        { from: "Velar-Static-V1", to: "Velar Runner velocity", label: "drives demand", strength: "strong" },
        { from: "Velocity", to: "Inventory pressure", label: "stockout in 5.6 days", strength: "strong" }
      ]
    },
    {
      id: "dec_creative_fatigue",
      title: "Refresh Velar-Static-V1 creatives",
      signalType: "CreativeFatigue",
      issueType: "Creative fatigue",
      severity: "medium",
      confidenceScore: SIGNAL_THRESHOLDS.creativeFatigue.confidence,
      businessImpact: 28000,
      impactLabel: "Rs 28K spend efficiency at risk",
      explanation: "Frequency crossed 5.4 while CTR dropped 34% versus last week.",
      rule: "frequency >= 4 AND ctr_drop_percent >= 20",
      recommendation: "Refresh creatives on flagged campaigns.",
      affectedCampaigns: ["Velar-Static-V1"],
      affectedSkus: ["Velar Runner"],
      timestamp: "10:05 AM",
      state: "pending",
      crossSystemSignals: ["Hook rate is down to 22%", "CTR is 1.1%", "Frequency is 5.4"],
      riskProjection: [
        { horizon: "24 hr", impact: "CAC instability likely begins" },
        { horizon: "48 hr", impact: "CTR decay may reduce paid velocity quality" },
        { horizon: "72 hr", impact: "Budget may keep scaling stale traffic" }
      ],
      recommendedActions: ["Launch two new hooks", "Cap stale static asset", "Move winning UGC into Velar campaign"],
      verificationSignals: [
        {
          label: "Creative refresh verification",
          condition: `new creative_ids appear AND fatigue score decreases >= ${VERIFICATION_THRESHOLDS.creativeRefresh.fatigueScoreDecreaseMin}%`,
          confidence: VERIFICATION_THRESHOLDS.creativeRefresh.confidence
        }
      ],
      timeline: [
        { id: "evt_4", time: "10:05 AM", title: "Creative fatigue detected", description: "Frequency and CTR decay thresholds fired together.", kind: "signal" }
      ],
      confidenceExplanation: "Medium confidence because creative metrics are strongly degraded, but outcome verification needs the next creative upload.",
      relationshipEdges: [
        { from: "Velar Static V1", to: "Frequency", label: "5.4 exposures", strength: "strong" },
        { from: "Frequency", to: "CTR", label: "34% drop", strength: "strong" },
        { from: "CTR", to: "CAC stability", label: "destabilizes", strength: "medium" }
      ]
    },
    {
      id: "dec_scaling_opportunity",
      title: "Scale Prepaid-Metro-Retargeting",
      signalType: "ScalingOpportunity",
      issueType: "Scaling opportunity",
      severity: "low",
      confidenceScore: SIGNAL_THRESHOLDS.scalingOpportunity.confidence,
      businessImpact: 116000,
      impactLabel: "Rs 1.16L upside over 72 hr",
      explanation: "Realized ROAS, repeat rate, RTO, inventory cover, and margin all support safe scaling.",
      rule: "roas_on_delivered_orders >= 4 AND repeat_rate >= 25 AND rto_rate_on_delivered <= 7 AND projected_stockout_days >= 14 AND contribution_margin_after_rto >= 30",
      recommendation: "Safe to increase spend by Rs 8,000-12,000/day.",
      affectedCampaigns: ["Prepaid-Metro-Retargeting"],
      affectedSkus: ["Metro Slip-On"],
      timestamp: "10:09 AM",
      state: "pending",
      crossSystemSignals: ["Realized ROAS is 5.1x", "Repeat rate is 31%", "RTO on delivered orders is 4%", "Inventory cover is 22 days"],
      riskProjection: [
        { horizon: "24 hr", impact: "Conservative scale preserves margin" },
        { horizon: "48 hr", impact: "Incremental contribution improves blended profitability" },
        { horizon: "72 hr", impact: "Opportunity cost grows if budget remains capped" }
      ],
      recommendedActions: ["Increase spend by Rs 8,000/day", "Monitor RTO drift", "Keep inventory reserve above 14 days"],
      verificationSignals: [
        {
          label: "Spend increase monitoring",
          condition: "realized ROAS remains >= 4 after spend increase",
          confidence: 0.79
        }
      ],
      timeline: [
        { id: "evt_5", time: "10:09 AM", title: "Scaling opportunity detected", description: "Delivered-order ROAS and margin thresholds fired.", kind: "signal" }
      ],
      confidenceExplanation: "Low priority but useful confidence: all scale criteria are satisfied and inventory cover is healthy.",
      relationshipEdges: [
        { from: "Prepaid audience", to: "Low RTO", label: "4% delivered-order RTO", strength: "strong" },
        { from: "Low RTO", to: "Realized ROAS", label: "supports 5.1x", strength: "strong" },
        { from: "Inventory cover", to: "Scale safety", label: "22 days available", strength: "strong" }
      ]
    }
  ]
};
