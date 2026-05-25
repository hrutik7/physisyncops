export type Severity = "high" | "medium" | "low";
export type DecisionState = "pending" | "monitoring" | "verified" | "successful" | "unsuccessful" | "ignored" | "snoozed";
export type SignalType =
  | "InventoryRisk"
  | "CreativeFatigue"
  | "MarginLeakage"
  | "CampaignRTOSpike"
  | "ScalingOpportunity";

export type UploadSource = "shopify_orders" | "meta_ads" | "inventory" | "creative_performance" | "customer_signals";

export interface MappingSuggestion {
  canonicalField: string;
  uploadedColumn: string | null;
  confidence: number;
  alternatives: string[];
  required: boolean;
}

export interface BusinessSnapshot {
  snapshotId: string;
  createdAt: string;
  uploadSource: UploadSource;
  brandId: string;
  snapshotVersion: number;
  isBaseline: boolean;
}

export interface SKU {
  skuId: string;
  name: string;
  inventoryLeft: number;
  dailyVelocity: number;
  reorderThreshold: number;
  projectedStockoutDays: number;
  contributionMarginAfterRto: number;
  spendGrowthPercent: number;
}

export interface Campaign {
  campaignId: string;
  campaignName: string;
  spend: number;
  spendGrowthPercent: number;
  roasOnPlacedOrders: number;
  roasOnDeliveredOrders: number;
  ctr: number;
  ctrDropPercent: number;
  frequency: number;
  audienceRegion: string;
  codOrderCount: number;
  codRatio: number;
  rtoCountAttributed: number;
  deliveredOrdersAttributed: number;
  rtoRateAttributed: number;
  contributionMarginAfterRto: number;
}

export interface CustomerSegment {
  segmentId: string;
  name: string;
  prepaidRatio: number;
  codRatio: number;
  repeatRate: number;
  returnRate: number;
  rtoRateOnDelivered: number;
}

export interface Creative {
  creativeId: string;
  campaignId: string;
  name: string;
  fatigueScore: number;
  previousFatigueScore: number;
  frequency: number;
  ctr: number;
  hookRate: number;
}

export interface VerificationRule {
  label: string;
  condition: string;
  confidence: number;
}

export interface TimelineEvent {
  id: string;
  time: string;
  title: string;
  description: string;
  kind: "signal" | "human" | "system" | "outcome";
}

export interface RelationshipEdge {
  from: string;
  to: string;
  label: string;
  strength: "strong" | "medium" | "weak";
}

export interface Decision {
  id: string;
  title: string;
  signalType: SignalType;
  issueType: string;
  severity: Severity;
  confidenceScore: number;
  businessImpact: number | null;
  impactLabel: string;
  explanation: string;
  rule: string;
  recommendation: string;
  affectedCampaigns: string[];
  affectedSkus: string[];
  timestamp: string;
  state: DecisionState;
  crossSystemSignals: string[];
  riskProjection: { horizon: string; impact: string }[];
  recommendedActions: string[];
  verificationSignals: VerificationRule[];
  timeline: TimelineEvent[];
  confidenceExplanation: string;
  relationshipEdges: RelationshipEdge[];
}

export interface OperationalState {
  brandName: string;
  snapshots: BusinessSnapshot[];
  skus: SKU[];
  campaigns: Campaign[];
  customerSegments: CustomerSegment[];
  creatives: Creative[];
  decisions: Decision[];
  mappingSuggestions: MappingSuggestion[];
}
