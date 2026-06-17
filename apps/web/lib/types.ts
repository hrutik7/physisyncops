export type Severity = "high" | "medium" | "low";
export type ActionEffort = "low" | "medium" | "high";
export type ConfidenceDriverStatus = "verified" | "inferred" | "warning";
export type DecisionState =
  | "pending"
  | "acknowledged"
  | "action_planned"
  | "action_executed"
  | "monitoring"
  | "verified"
  | "successful"
  | "unsuccessful"
  | "ignored"
  | "snoozed";
export type SignalType =
  | "InventoryRisk"
  | "CreativeFatigue"
  | "MarginLeakage"
  | "MarginTrap"
  | "CampaignRTOSpike"
  | "NewLaunchRisk"
  | "StateRTOLeakage"
  | "AudienceAudit"
  | "ScalingOpportunity"
  | "AOVDilution"
  | "DataGapWarning";

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
  roasOnPlacedOrders?: number;
  roasOnDeliveredOrders?: number;
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

export interface Intervention {
  id: string;
  actionType: string;
  status: string;
  expectedEffect: Record<string, any>;
  verificationMetric: Record<string, any>;
  outcome: Record<string, any>;
}

export interface VerificationScorecard {
  score: number;
  status: string;
  metrics: VerificationRule[];
  summary: string | null;
}

export interface WhyAnalysis {
  formula: string;
  sourceFields: { source: string; field: string; value: string }[];
  confidenceFactors: string[];
  goalAlignment: string;
  snapshotId: string;
}

export interface RemedyAction {
  id: string;
  label: string;
  rank: "primary" | "alternative";
  effort: ActionEffort;
  expectedRiskReduction: number;
  expectedRiskReductionLabel: string;
  expectedOutcome: Record<string, { before: string; after: string } | number>;
  medal?: string;
  recoveryExplanation?: string;
  recoveryLabel?: string;
}

export type DecisionVerificationType = "estimated" | "verified";

export interface DecisionVerification {
  type: DecisionVerificationType;
  label: string;
  reason: string;
}

export interface TriggerReason {
  headline: string;
  metrics: { label: string; value: string }[];
}

export interface AutoResolutionCriteria {
  headline: string;
  intro: string;
  criteria: string[];
}

export interface StockoutScenario {
  label: string;
  detail: string;
  estimatedLostSales: number;
  estimatedLostSalesLabel: string;
  lostDays?: number;
  lostUnits?: number;
}

export interface StockoutScenarioAnalysis {
  headline: string;
  scenarios: StockoutScenario[];
}

export interface ImpactContext {
  totalRevenue: number;
  totalRevenueLabel: string;
  atRiskRevenue: number;
  atRiskRevenueLabel: string;
  impactPercent: number;
  contextLabel: string;
  atRiskLabel?: string;
  atRiskExplanation?: string;
  contextExplanation?: string;
  shippingWaste?: number;
  shippingWasteLabel?: string;
  shippingWasteExplanation?: string;
  actionUrgency?: "monitor" | "act";
  campaignSpend?: number;
  campaignSpendLabel?: string;
  deliveredRevenue?: number;
  deliveredRevenueLabel?: string;
  inventoryLeft?: number;
  inventoryCoverDays?: number;
  dailyVelocity?: number;
  stockoutState?: "already_stocked_out" | "low_cover";
  stockoutStateLabel?: string;
  financialImpactTier?: "low" | "medium" | "high";
  financialImpactLabel?: string;
  operationalRiskLabel?: string;
  impactNarrative?: string;
}

export interface ConfidenceDriver {
  label: string;
  status: ConfidenceDriverStatus;
  detail: string;
}

export interface MetricVerificationItem {
  label: string;
  detail?: string;
}

export interface MetricVerificationStatus {
  headline: string;
  observedLabel: string;
  estimatedLabel: string;
  observed: MetricVerificationItem[];
  estimated: MetricVerificationItem[];
}

export interface EvidenceRequirement {
  label: string;
  required: boolean;
  available: boolean;
}

export interface EvidenceRequired {
  requirements: EvidenceRequirement[];
  allRequiredAvailable: boolean;
  disclaimer: string;
}

export interface DecisionDependency {
  label: string;
  status: "resolved" | "in_progress" | "planned";
  detail: string;
  effect: "downgrade" | "neutral" | "resolve";
  resolvesDecision: boolean;
}

export interface OutcomeMeasurement {
  before: Record<string, string>;
  after: Record<string, string>;
  recoveredRevenue: number;
  recoveredRevenueLabel: string;
  decisionAccuracy: number | null;
  status: DecisionState;
}

export interface StaleMetadata {
  ageDays: number;
  isStale: boolean;
  staleLabel: string;
}

export interface LifecycleStage {
  key: DecisionState;
  title: string;
  description: string;
  status: "done" | "active" | "upcoming";
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
  whyAnalysis?: WhyAnalysis;
  intervention?: Intervention | null;
  verificationScorecard?: VerificationScorecard | null;
  remedies?: RemedyAction[];
  impactContext?: ImpactContext;
  confidenceDrivers?: ConfidenceDriver[];
  metricVerification?: MetricVerificationStatus;
  evidenceRequired?: EvidenceRequired;
  dependencies?: DecisionDependency[];
  outcomeMeasurement?: OutcomeMeasurement | null;
  staleMetadata?: StaleMetadata;
  lifecycleStages?: LifecycleStage[];
  lifecycleLabel?: string;
  selectedRemedyId?: string | null;
  detectedAt?: string;
  decisionVerification?: DecisionVerification;
  triggerReason?: TriggerReason | null;
  autoResolutionCriteria?: AutoResolutionCriteria | null;
  stockoutScenarios?: StockoutScenarioAnalysis | null;
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
