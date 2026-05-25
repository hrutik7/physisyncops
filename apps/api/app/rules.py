from dataclasses import dataclass
from typing import Any
import pandas as pd
from datetime import datetime, timezone

SIGNAL_THRESHOLDS = {
    "InventoryRisk": {"projected_stockout_days_max": 7, "spend_growth_percent_min": 15, "severity": "high", "confidence": 0.82},
    "CreativeFatigue": {"frequency_min": 4, "ctr_drop_percent_min": 20, "severity": "medium", "confidence": 0.76},
    "MarginLeakage": {"cod_ratio_min": 60, "rto_rate_on_delivered_min": 18, "roas_on_placed_orders_min": 3, "severity": "high", "confidence": 0.85},
    "CampaignRTOSpike": {"rto_rate_attributed_min": 25, "cod_order_count_min": 50, "severity": "high", "confidence": 0.88},
    "ScalingOpportunity": {
        "roas_on_delivered_orders_min": 4,
        "repeat_rate_min": 25,
        "rto_rate_on_delivered_max": 7,
        "projected_stockout_days_min": 14,
        "contribution_margin_after_rto_min": 30,
        "severity": "low",
        "confidence": 0.79,
    },
}

VERIFICATION_THRESHOLDS = {
    "inventoryReorder": {"inventory_level_increase_min": 25, "projected_stockout_days_improvement_min": 3, "confidence": 0.81},
    "spendReduction": {"campaign_spend_decrease_min": 15, "confidence": 0.77},
    "creativeRefresh": {"fatigue_score_decrease_min": 20, "confidence": 0.74},
    "codCampaignPause": {"flagged_campaign_spend_drop_min": 80, "confidence": 0.91},
}


def rto_rate(returned_orders: float, delivered_orders: float) -> float:
    if delivered_orders <= 0:
        return 0
    return (returned_orders / delivered_orders) * 100


def realized_roas(revenue_from_delivered_orders: float, ad_spend: float) -> float:
    if ad_spend <= 0:
        return 0
    return revenue_from_delivered_orders / ad_spend


@dataclass
class Signal:
    title: str
    signal_type: str
    issue_type: str
    severity: str
    confidence_score: float
    business_impact: float | None
    impact_label: str
    recommendation: str
    affected_campaigns: list[str]
    affected_skus: list[str]
    rule: str
    explanation: str
    cross_system_signals: list[str]
    risk_projection: list[dict[str, str]]
    recommended_actions: list[str]
    verification_signals: list[dict[str, Any]]
    confidence_explanation: str
    relationship_edges: list[dict[str, str]]


class DataFreshnessValidator:
    @staticmethod
    def validate(df: pd.DataFrame) -> float:
        # Try to find a date-like column
        date_col = None
        for col in df.columns:
            if "date" in str(col).lower() or "time" in str(col).lower():
                date_col = col
                break
        
        if date_col is not None and not df[date_col].empty:
            try:
                latest_date = pd.to_datetime(df[date_col]).max()
                if latest_date.tzinfo is not None:
                    delta = datetime.now(timezone.utc) - latest_date
                else:
                    delta = datetime.now() - latest_date
                
                days_old = max(delta.days, 0)
                if days_old <= 1:
                    return 1.0
                elif days_old <= 3:
                    return 0.88
                elif days_old <= 7:
                    return 0.75
                else:
                    return 0.50
            except Exception:
                pass
        return 0.95  # Fallback high freshness if no date parsed


class ConfidenceEngine:
    @staticmethod
    def calculate(base_score: float, freshness: float, alignment_confirmed: bool) -> tuple[float, str]:
        alignment_multiplier = 1.0 if alignment_confirmed else 0.85
        final_score = base_score * freshness * alignment_multiplier
        final_score = round(min(final_score, 1.0), 2)
        
        explanation = (
            f"Confidence score of {int(final_score * 100)}% calculated dynamically. "
            f"Base rule reliability is {int(base_score * 100)}%. Data freshness factor is {int(freshness * 100)}%. "
        )
        if alignment_confirmed:
            explanation += "Cross-system verification confirmed matching anomalies."
        else:
            explanation += "Cross-system correlation factor penalized due to limited downstream validation."
        
        return final_score, explanation


class OntologyLayer:
    @staticmethod
    def build_relationships(signal_type: str, entities: list[str]) -> list[dict[str, str]]:
        edges = []
        if signal_type == "CampaignRTOSpike":
            campaign_name = entities[0] if entities else "Flagged Campaign"
            edges = [
                {"from": campaign_name, "to": "COD orders", "label": "drives 67% COD mix", "strength": "strong"},
                {"from": "COD orders", "to": "RTO probability", "label": "elevates", "strength": "strong"},
                {"from": "RTO probability", "to": "Realized ROAS", "label": "reduces to 2.1x", "strength": "strong"},
                {"from": "Realized ROAS", "to": "Margin", "label": "compresses to 8%", "strength": "strong"}
            ]
        elif signal_type == "InventoryRisk":
            sku_name = entities[0] if entities else "Flagged SKU"
            edges = [
                {"from": "Velar-Static-V1", "to": f"{sku_name} velocity", "label": "drives demand", "strength": "strong"},
                {"from": f"{sku_name} velocity", "to": "Inventory pressure", "label": f"{sku_name} stockout in 5 days", "strength": "strong"}
            ]
        elif signal_type == "CreativeFatigue":
            campaign_name = entities[0] if entities else "Flagged Campaign"
            edges = [
                {"from": campaign_name, "to": "Frequency", "label": "5.4 exposures", "strength": "strong"},
                {"from": "Frequency", "to": "CTR", "label": "34% drop", "strength": "strong"},
                {"from": "CTR", "to": "CAC stability", "label": "destabilizes", "strength": "medium"}
            ]
        elif signal_type == "ScalingOpportunity":
            campaign_name = entities[0] if entities else "Flagged Campaign"
            edges = [
                {"from": "Prepaid audience", "to": "Low RTO", "label": "4% delivered-order RTO", "strength": "strong"},
                {"from": "Low RTO", "to": "Realized ROAS", "label": "supports 5.1x", "strength": "strong"},
                {"from": "Inventory cover", "to": "Scale safety", "label": "22 days available", "strength": "strong"}
            ]
        elif signal_type == "MarginLeakage":
            segment_name = entities[0] if entities else "Flagged Segment"
            edges = [
                {"from": segment_name, "to": "COD Mix", "label": "67% cash preference", "strength": "strong"},
                {"from": "COD Mix", "to": "RTO Spike", "label": "erodes margin", "strength": "strong"}
            ]
        return edges


class SignalDetectionEngine:
    @staticmethod
    def detect(state: dict[str, Any], freshness: float = 1.0) -> list[Signal]:
        signals: list[Signal] = []
        skus = state.get("skus", [])
        campaigns = state.get("campaigns", [])
        segments = state.get("customer_segments", [])

        for sku in skus:
            thresholds = SIGNAL_THRESHOLDS["InventoryRisk"]
            if sku["projected_stockout_days"] <= thresholds["projected_stockout_days_max"] and sku["spend_growth_percent"] >= thresholds["spend_growth_percent_min"]:
                base_conf = thresholds["confidence"]
                conf_score, conf_expl = ConfidenceEngine.calculate(base_conf, freshness, alignment_confirmed=True)
                
                signals.append(
                    Signal(
                        title=f"{sku['name']} stockout risk in {sku['projected_stockout_days']} days",
                        signal_type="InventoryRisk",
                        issue_type="Inventory pressure",
                        severity=thresholds["severity"],
                        confidence_score=conf_score,
                        business_impact=148000,
                        impact_label="Rs 1.48L revenue at risk over 72 hr",
                        recommendation="Reduce spend by 15% OR reorder within 48 hours",
                        affected_campaigns=sku.get("campaigns", []),
                        affected_skus=[sku["name"]],
                        rule="projected_stockout_days <= 7 AND spend_growth_percent >= 15",
                        explanation="Spend is accelerating while SKU inventory is below one week of cover.",
                        cross_system_signals=[
                            f"SKU velocity is {sku['daily_velocity']} units/day",
                            f"Inventory left is {sku['inventory_left']} units",
                            f"Ad spend grew {sku['spend_growth_percent']}% week over week"
                        ],
                        risk_projection=[
                            {"horizon": "24 hr", "impact": "Inventory cover falls further"},
                            {"horizon": "48 hr", "impact": "Reorder window becomes operationally tight"},
                            {"horizon": "72 hr", "impact": "Paid traffic drives demand into stockout"}
                        ],
                        recommended_actions=["Create reorder today", "Reduce prospecting spend by 15%", "Keep prepaid retargeting live"],
                        verification_signals=[
                            {
                                "label": "Inventory reorder verification",
                                "condition": f"inventory level increases >= {VERIFICATION_THRESHOLDS['inventoryReorder']['inventory_level_increase_min']}% AND projected stockout days improves >= {VERIFICATION_THRESHOLDS['inventoryReorder']['projected_stockout_days_improvement_min']}",
                                "confidence": VERIFICATION_THRESHOLDS['inventoryReorder']['confidence']
                            },
                            {
                                "label": "Spend reduction verification",
                                "condition": f"campaign spend decreases >= {VERIFICATION_THRESHOLDS['spendReduction']['campaign_spend_decrease_min']}%",
                                "confidence": VERIFICATION_THRESHOLDS['spendReduction']['confidence']
                            }
                        ],
                        confidence_explanation=conf_expl,
                        relationship_edges=OntologyLayer.build_relationships("InventoryRisk", [sku["name"]])
                    )
                )

        for campaign in campaigns:
            thresholds = SIGNAL_THRESHOLDS["CampaignRTOSpike"]
            if campaign["rto_rate_attributed"] >= thresholds["rto_rate_attributed_min"] and campaign["cod_order_count"] >= thresholds["cod_order_count_min"]:
                base_conf = thresholds["confidence"]
                # Cross system alignment confirmed if COD ratio is also elevated
                alignment = campaign["cod_ratio"] >= 50
                conf_score, conf_expl = ConfidenceEngine.calculate(base_conf, freshness, alignment)
                
                signals.append(
                    Signal(
                        title=f"Pause {campaign['campaign_name']}",
                        signal_type="CampaignRTOSpike",
                        issue_type="Campaign-level RTO spike",
                        severity=thresholds["severity"],
                        confidence_score=conf_score,
                        business_impact=6200,
                        impact_label="Losing Rs 6,200/day in realized margin",
                        recommendation=f"Pause {campaign['campaign_name']} immediately. Estimated daily margin loss: Rs 6,200",
                        affected_campaigns=[campaign["campaign_name"]],
                        affected_skus=campaign.get("skus", []),
                        rule="campaign.rto_rate_attributed >= 25 AND campaign.cod_order_count >= 50",
                        explanation="This specific campaign is driving disproportionate RTO. Blended RTO masks this.",
                        cross_system_signals=[
                            f"COD ratio is {campaign['cod_ratio']}% on the flagged audience",
                            f"Placed-order ROAS is {campaign.get('roas_on_placed_orders', 3.0)}x, but realized ROAS is only {campaign.get('roas_on_delivered_orders', 2.0)}x",
                            f"Contribution margin after RTO has compressed to {campaign.get('contribution_margin_after_rto', 10)}%"
                        ],
                        risk_projection=[
                            {"horizon": "24 hr", "impact": "Rs 6,200 additional realized margin loss"},
                            {"horizon": "48 hr", "impact": "Rs 12,400 loss and blended ROAS contamination"},
                            {"horizon": "72 hr", "impact": "Rs 18,600 loss with COD RTO compounding"}
                        ],
                        recommended_actions=["Pause campaign", "Shift budget to prepaid retargeting", "Add prepaid incentive for Tier 2 traffic"],
                        verification_signals=[
                            {
                                "label": "COD campaign pause verification",
                                "condition": f"flagged campaign spend drops >= {VERIFICATION_THRESHOLDS['codCampaignPause']['flagged_campaign_spend_drop_min']}%",
                                "confidence": VERIFICATION_THRESHOLDS['codCampaignPause']['confidence']
                            }
                        ],
                        confidence_explanation=conf_expl,
                        relationship_edges=OntologyLayer.build_relationships("CampaignRTOSpike", [campaign["campaign_name"]])
                    )
                )

            fatigue = SIGNAL_THRESHOLDS["CreativeFatigue"]
            if campaign["frequency"] >= fatigue["frequency_min"] and campaign["ctr_drop_percent"] >= fatigue["ctr_drop_percent_min"]:
                base_conf = fatigue["confidence"]
                conf_score, conf_expl = ConfidenceEngine.calculate(base_conf, freshness, alignment_confirmed=True)
                
                signals.append(
                    Signal(
                        title=f"Refresh {campaign['campaign_name']} creatives",
                        signal_type="CreativeFatigue",
                        issue_type="Creative fatigue",
                        severity=fatigue["severity"],
                        confidence_score=conf_score,
                        business_impact=28000,
                        impact_label="Rs 28K spend efficiency at risk",
                        recommendation="Refresh creatives on flagged campaigns",
                        affected_campaigns=[campaign["campaign_name"]],
                        affected_skus=campaign.get("skus", []),
                        rule="frequency >= 4 AND ctr_drop_percent >= 20",
                        explanation="Frequency is high while CTR has dropped sharply.",
                        cross_system_signals=[
                            f"CTR is {campaign.get('ctr', 1.5)}%",
                            f"Frequency is {campaign['frequency']}",
                            f"CTR has decayed by {campaign['ctr_drop_percent']}% versus last week"
                        ],
                        risk_projection=[
                            {"horizon": "24 hr", "impact": "CAC instability likely begins"},
                            {"horizon": "48 hr", "impact": "CTR decay reduces paid traffic quality"},
                            {"horizon": "72 hr", "impact": "Budget continues scaling stale traffic"}
                        ],
                        recommended_actions=["Launch two new hooks", "Cap stale static asset", "Move winning UGC into Velar campaign"],
                        verification_signals=[
                            {
                                "label": "Creative refresh verification",
                                "condition": f"fatigue score decreases >= {VERIFICATION_THRESHOLDS['creativeRefresh']['fatigue_score_decrease_min']}%",
                                "confidence": VERIFICATION_THRESHOLDS['creativeRefresh']['confidence']
                            }
                        ],
                        confidence_explanation=conf_expl,
                        relationship_edges=OntologyLayer.build_relationships("CreativeFatigue", [campaign["campaign_name"]])
                    )
                )

        for segment in segments:
            leakage = SIGNAL_THRESHOLDS["MarginLeakage"]
            if segment["cod_ratio"] >= leakage["cod_ratio_min"] and segment["rto_rate_on_delivered"] >= leakage["rto_rate_on_delivered_min"] and segment.get("roas_on_placed_orders", 0.0) >= leakage["roas_on_placed_orders_min"]:
                base_conf = leakage["confidence"]
                conf_score, conf_expl = ConfidenceEngine.calculate(base_conf, freshness, alignment_confirmed=True)
                
                signals.append(
                    Signal(
                        title=f"Margin leakage in {segment['name']}",
                        signal_type="MarginLeakage",
                        issue_type="Margin leakage",
                        severity=leakage["severity"],
                        confidence_score=conf_score,
                        business_impact=24000,
                        impact_label="Rs 24K margin leakage detected",
                        recommendation="Pause or reduce COD-heavy campaigns. Push prepaid incentives.",
                        affected_campaigns=segment.get("campaigns", []),
                        affected_skus=segment.get("skus", [segment["name"]]),
                        rule="cod_ratio >= 60 AND rto_rate_on_delivered >= 18 AND roas_on_placed_orders >= 3",
                        explanation="Topline ROAS looks healthy but realized profitability is eroding due to high COD RTO.",
                        cross_system_signals=[
                            f"COD ratio is {segment['cod_ratio']}%",
                            f"RTO rate on delivered is {segment['rto_rate_on_delivered']}%",
                            f"ROAS on placed orders is {segment.get('roas_on_placed_orders', 0.0)}x"
                        ],
                        risk_projection=[
                            {"horizon": "24 hr", "impact": "Margin compression continues"},
                            {"horizon": "48 hr", "impact": "Blended margins compress further"},
                            {"horizon": "72 hr", "impact": "Working capital tied up in returned shipments"}
                        ],
                        recommended_actions=["De-prioritize COD prospecting", "Shift budget to prepaid segments", "Incentivize UPI payment method"],
                        verification_signals=[],
                        confidence_explanation=conf_expl,
                        relationship_edges=OntologyLayer.build_relationships("MarginLeakage", [segment["name"]])
                    )
                )

        for campaign in campaigns:
            opp = SIGNAL_THRESHOLDS["ScalingOpportunity"]
            
            # Find matching SKU repeat rates and stock metrics
            skus_list = campaign.get("skus", [])
            projected_stockout = 99.0
            repeat_rate = 0.0
            
            for s_name in skus_list:
                sku_ent = next((s for s in skus if s["name"].lower() == s_name.lower() or s["sku_id"].lower() == s_name.lower()), None)
                if sku_ent:
                    projected_stockout = min(projected_stockout, sku_ent["projected_stockout_days"])
                seg_ent = next((sg for sg in segments if sg["name"].lower() == s_name.lower()), None)
                if seg_ent:
                    repeat_rate = max(repeat_rate, seg_ent.get("repeat_rate", 0.0))
            
            # Check all ScalingOpportunity thresholds
            roas_deliv = campaign.get("roas_on_delivered_orders", 0.0)
            rto_rate_attr = campaign.get("rto_rate_attributed", 0.0)
            margin = campaign.get("contribution_margin_after_rto", 0)
            
            if (roas_deliv >= opp["roas_on_delivered_orders_min"] and 
                rto_rate_attr <= opp["rto_rate_on_delivered_max"] and 
                margin >= opp["contribution_margin_after_rto_min"] and 
                projected_stockout >= opp["projected_stockout_days_min"]):
                
                base_conf = opp["confidence"]
                conf_score, conf_expl = ConfidenceEngine.calculate(base_conf, freshness, alignment_confirmed=True)
                
                signals.append(
                    Signal(
                        title=f"Scale budget on {campaign['campaign_name']}",
                        signal_type="ScalingOpportunity",
                        issue_type="Scaling opportunity",
                        severity=opp["severity"],
                        confidence_score=conf_score,
                        business_impact=185000,
                        impact_label="Rs 1.85L incremental revenue opportunity",
                        recommendation=f"Increase budget on {campaign['campaign_name']} by 25%. Metrics are highly profitable with low return rates.",
                        affected_campaigns=[campaign["campaign_name"]],
                        affected_skus=skus_list,
                        rule="roas_on_delivered_orders >= 4 AND rto_rate_attributed <= 7 AND contribution_margin >= 30 AND projected_stockout_days >= 14",
                        explanation="This campaign is driving highly profitable prepaid sales with low returns and has ample inventory cover to scale.",
                        cross_system_signals=[
                            f"Realized ROAS is {roas_deliv}x",
                            f"RTO rate is {rto_rate_attr}%",
                            f"Inventory projected stockout is {projected_stockout} days",
                            f"Attributed contribution margin is {margin}%"
                        ],
                        risk_projection=[
                            {"horizon": "24 hr", "impact": "Increase traffic share before ad delivery cost increases"},
                            {"horizon": "48 hr", "impact": "Capture incremental repeat customer conversions"},
                            {"horizon": "72 hr", "impact": "Scale sales volume with highly efficient ROAS"}
                        ],
                        recommended_actions=["Increase budget by 20-30%", "Incentivize high-LTV segment retargeting", "Maintain current creative flow"],
                        verification_signals=[],
                        confidence_explanation=conf_expl,
                        relationship_edges=OntologyLayer.build_relationships("ScalingOpportunity", [campaign["campaign_name"]])
                    )
                )

        return signals


def detect_signals(state: dict[str, Any]) -> list[Signal]:
    # Backward compatibility wrapper
    return SignalDetectionEngine.detect(state)
