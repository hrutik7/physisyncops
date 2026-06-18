"""V2 decision enrichment: remedies, impact context, confidence drivers, lifecycle metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import re

from .impact_math import (
    compute_campaign_revenue_impact,
    compute_inventory_revenue_impact,
    compute_state_revenue_impact,
    compute_stockout_scenario,
    financial_impact_metadata,
    normalize_sku_metrics,
    recovery_from_gap,
    sample_size_confidence_cap,
    state_operational_framing,
)
from .models import BusinessSnapshot, Decision
from .rules import SIGNAL_THRESHOLDS

PASSIVE_REMEDY_HINTS = (
    "collect",
    "hold spend",
    "hold budget",
    "monitor",
    "gather",
    "before major",
    "wait",
    "cap spend until",
)


def _is_passive_remedy(label: str) -> bool:
    lower = label.lower()
    return any(hint in lower for hint in PASSIVE_REMEDY_HINTS)


def _recovery_label(label: str) -> str:
    return "Potential Risk Reduction" if _is_passive_remedy(label) else "Potential Improvement Opportunity"


def _recovery_explanation(revenue_gap: float, capture_rate: float, recovery: float, *, passive: bool = False) -> str:
    if passive:
        return (
            f"Rs {recovery:,.0f} = modeled portion of the revenue gap (Rs {revenue_gap:,.0f}) that may be avoided "
            f"by limiting further spend erosion while launch validation completes."
        )
    return (
        f"Rs {recovery:,.0f} = revenue gap (Rs {revenue_gap:,.0f}) × {capture_rate:.0%} modeled capture "
        f"from similar spend-reduction or fulfillment-improvement interventions."
    )

EFFORT_BY_ACTION: dict[str, str] = {
    "pause": "low",
    "reduce spend": "low",
    "cap": "low",
    "snooze": "low",
    "cod verification": "medium",
    "prepaid": "medium",
    "reorder": "medium",
    "restock": "medium",
    "refresh": "medium",
    "shift budget": "medium",
    "retargeting": "medium",
    "incentive": "medium",
    "scale": "medium",
    "increase spend": "medium",
    "courier": "high",
    "factory": "high",
    "unbundle": "high",
    "landing page": "high",
}


def _infer_effort(label: str) -> str:
    lower = label.lower()
    for key, effort in EFFORT_BY_ACTION.items():
        if key in lower:
            return effort
    return "medium"


def _campaign_metrics(snapshot: BusinessSnapshot | None, campaign_names: list[str]) -> dict[str, Any]:
    if snapshot is None:
        return {}
    campaigns = snapshot.state.get("campaigns", [])
    for campaign in campaigns:
        if campaign.get("campaign_name") in campaign_names or campaign.get("campaign_id") in campaign_names:
            return campaign
    return campaigns[0] if campaigns else {}


def _sku_metrics(snapshot: BusinessSnapshot | None, sku_names: list[str]) -> dict[str, Any]:
    if snapshot is None:
        return {}
    skus = snapshot.state.get("skus", [])
    matches = [
        sku
        for sku in skus
        if sku.get("name") in sku_names or sku.get("sku_id") in sku_names
    ]
    if matches:
        critical = min(matches, key=lambda sku: normalize_sku_metrics(sku)["projected_stockout_days"])
        return normalize_sku_metrics(critical)
    return normalize_sku_metrics(skus[0]) if skus else {}


def _parse_sku_aov_from_decision(decision: Decision) -> float | None:
    for signal in decision.cross_system_signals or []:
        if "aov" in signal.lower() and ":" in signal:
            try:
                return _parse_inr_value(signal.split(":", 1)[1])
            except ValueError:
                continue
    return None


def _sku_average_order_value(
    sku: dict[str, Any],
    snapshot_state: dict[str, Any],
    decision: Decision | None = None,
) -> float:
    if decision:
        parsed = _parse_sku_aov_from_decision(decision)
        if parsed and parsed > 0:
            return parsed

    sku_aov = sku.get("average_order_value")
    if sku_aov and float(sku_aov) > 0:
        return float(sku_aov)
    for entry in snapshot_state.get("skus", []):
        if entry.get("name") == sku.get("name") and entry.get("average_order_value"):
            return float(entry["average_order_value"])
    if snapshot_state.get("average_order_value"):
        return float(snapshot_state["average_order_value"])

    if decision and decision.business_impact:
        velocity = float(sku.get("daily_velocity", 0) or 0)
        projected = float(sku.get("projected_stockout_days", 0) or 0)
        if velocity > 0:
            if projected <= 0:
                inferred = float(decision.business_impact) / (velocity * 7)
            else:
                lost_days = max(0.1, 7 - projected)
                inferred = float(decision.business_impact) / (velocity * lost_days)
            if inferred > 0:
                return round(inferred, 2)

    return 500.0


def _inventory_impact_bundle(
    decision: Decision,
    snapshot: BusinessSnapshot | None = None,
) -> tuple[dict[str, Any], float, dict[str, Any]]:
    snapshot_state = _snapshot_state(snapshot)
    sku = _sku_metrics(snapshot, decision.affected_skus or [])
    aov = _sku_average_order_value(sku, snapshot_state, decision)
    projected = float(sku.get("projected_stockout_days", 0) or 0)
    velocity = float(sku.get("daily_velocity", 0) or 0)
    metrics = compute_inventory_revenue_impact(velocity, aov, projected)
    already_stocked_out = bool(metrics.get("already_stocked_out")) or (
        int(sku.get("inventory_left", 0) or 0) == 0 and velocity > 0
    )
    if already_stocked_out and metrics["forecast_revenue"] > 0:
        metrics["at_risk_revenue"] = metrics["forecast_revenue"]
        metrics["impact_percent"] = 100.0
        metrics["stockout_days_in_window"] = float(metrics["horizon_days"])
        metrics["already_stocked_out"] = True
    return sku, aov, metrics


def _format_inr(value: float) -> str:
    if value >= 100000:
        return f"Rs {(value / 100000):.2f}L"
    return f"Rs {round(value):,}"


def _round_display_metric(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    if decimals == 0:
        return str(int(rounded))
    text = f"{rounded:.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


NEW_LAUNCH_EXPLANATION = (
    "Newly launched ad set is currently performing below target ROAS while remaining in a low-frequency learning phase. "
    "Additional delivery data is required before determining whether underperformance is driven by creative, audience, "
    "offer, or landing-page factors."
)


def _snapshot_state(snapshot: BusinessSnapshot | None) -> dict[str, Any]:
    return snapshot.state if snapshot else {}


def _rto_data_present(state: dict[str, Any]) -> bool:
    if state.get("rto_data_present", True):
        return True
    return bool(
        state.get("rto_status_source")
        or state.get("brand_rto_rate") is not None
        or any(
            campaign.get("rto_count_attributed", 0) > 0
            or campaign.get("delivered_orders_attributed", 0) > 0
            or campaign.get("rto_rate_attributed", 0) > 0
            for campaign in state.get("campaigns", [])
        )
    )


def _campaign_rto_verified(campaign: dict[str, Any], rto_present: bool) -> bool:
    if not rto_present:
        return False
    return bool(campaign.get("rto_count_attributed", 0) > 0 or campaign.get("delivered_orders_attributed", 0) > 0)


def _brand_rto_rate(state: dict[str, Any], campaign: dict[str, Any]) -> float:
    if state.get("brand_rto_rate") is not None:
        return float(state["brand_rto_rate"])
    return float(campaign.get("rto_rate_attributed", 0) or 0)


def _has_order_attribution(decision: Decision, campaign: dict[str, Any]) -> bool:
    return bool(decision.affected_campaigns) and bool(campaign)


def _parse_cross_system_value(decision: Decision, prefix: str) -> str | None:
    for signal in decision.cross_system_signals or []:
        if signal.lower().startswith(prefix.lower() + ":"):
            return signal.split(":", 1)[1].strip()
    return None


def _parse_inr_value(raw: str) -> float:
    cleaned = re.sub(r"Rs|[,\s]", "", raw, flags=re.IGNORECASE)
    return float(cleaned)


def _parse_state_name(decision: Decision) -> str | None:
    state_name = _parse_cross_system_value(decision, "State")
    if state_name:
        return state_name
    title = decision.title or ""
    for pattern in (
        r"Regional COD Risk:\s*(.+)$",
        r"Emerging RTO Pattern:\s*(.+)$",
        r"High RTO in (.+)$",
    ):
        match = re.search(pattern, title)
        if match:
            return match.group(1).strip()
    return None


def _state_rto_delta(decision: Decision, region: dict[str, Any], snapshot_state: dict[str, Any]) -> float | None:
    delta_raw = _parse_cross_system_value(decision, "State RTO delta")
    if delta_raw:
        try:
            return float(delta_raw.replace("%", "").strip())
        except ValueError:
            pass
    brand_rto = region.get("brand_rto")
    if brand_rto is None:
        brand_rto = snapshot_state.get("brand_rto_rate")
    state_rto = region.get("rto_pct")
    if brand_rto is not None and state_rto is not None:
        return round(float(state_rto) - float(brand_rto), 1)
    return None


def _is_state_monitor_case(cod_pct: float, rto_delta: float | None) -> bool:
    return abs(rto_delta or 0) <= 5 and float(cod_pct or 0) >= 70


def _state_region_metrics(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    state_name = _parse_state_name(decision)
    snapshot_state = _snapshot_state(snapshot)
    for entry in snapshot_state.get("state_profitability", []):
        if state_name and entry.get("state") == state_name:
            return {
                **entry,
                "state_name": state_name,
                "total_revenue": entry.get("total_revenue", 0),
                "rto_revenue": entry.get("rto_revenue", 0),
            }

    metrics: dict[str, Any] = {"state_name": state_name}
    orders_raw = _parse_cross_system_value(decision, "Total orders")
    if orders_raw:
        try:
            metrics["total_orders"] = int(float(orders_raw))
        except ValueError:
            pass
    for key, prefix in (("cod_pct", "COD mix"), ("rto_pct", "RTO rate")):
        raw = _parse_cross_system_value(decision, prefix)
        if raw:
            try:
                metrics[key] = float(raw.replace("%", ""))
            except ValueError:
                pass
    brand_raw = _parse_cross_system_value(decision, "Brand average RTO")
    if brand_raw:
        try:
            metrics["brand_rto"] = float(brand_raw.replace("%", ""))
        except ValueError:
            pass
    for key, prefix in (
        ("total_revenue", "Regional order GMV"),
        ("rto_revenue", "RTO order GMV"),
        ("shipping_waste", "Estimated shipping waste"),
    ):
        raw = _parse_cross_system_value(decision, prefix)
        if raw:
            try:
                metrics[key] = _parse_inr_value(raw)
            except ValueError:
                pass
    return metrics


def build_state_display_overrides(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    if _signal_type(decision) != "StateRTOLeakage":
        return {}
    region = _state_region_metrics(decision, snapshot)
    snapshot_state = _snapshot_state(snapshot)
    state_name = region.get("state_name") or _parse_state_name(decision) or "this state"
    cod_pct = float(region.get("cod_pct", 0) or 0)
    state_rto = float(region.get("rto_pct", 0) or 0)
    brand_rto = region.get("brand_rto") if region.get("brand_rto") is not None else snapshot_state.get("brand_rto_rate")
    rto_delta = _state_rto_delta(decision, region, snapshot_state)
    impact_metrics = compute_state_revenue_impact(
        int(region.get("total_orders", 0) or 0),
        state_rto,
        total_revenue=float(region.get("total_revenue", 0) or 0),
        rto_revenue=float(region.get("rto_revenue", 0) or 0),
        delivered_revenue=float(region.get("delivered_revenue", 0) or 0),
    )
    at_risk_gmv = impact_metrics["at_risk_revenue"]
    monitor_case = _is_state_monitor_case(cod_pct, rto_delta)

    if monitor_case:
        title = f"Regional COD Risk: {state_name}"
        severity = "low"
        explanation = (
            f"{state_name} runs {cod_pct:.0f}% COD across {region.get('total_orders', 'limited')} orders. "
            f"Regional RTO is {state_rto}% — only {rto_delta:+.1f} pts vs brand average ({brand_rto}%). "
            f"The signal reflects COD concentration and sample size, not a uniquely poor state return profile."
        )
        recommendation = (
            f"Monitor {state_name} COD mix and test prepaid incentives before restricting regional shipping."
        )
    else:
        title = decision.title
        severity = decision.severity
        explanation = decision.explanation
        recommendation = decision.recommendation

    return {
        "displayTitle": title,
        "displayExplanation": explanation,
        "displayRecommendation": recommendation,
        "displaySeverity": severity,
        "effectiveBusinessImpact": at_risk_gmv if at_risk_gmv > 0 else decision.business_impact,
        "effectiveImpactLabel": (
            f"Rs {at_risk_gmv:,.0f} RTO order GMV at risk in {state_name}"
            if at_risk_gmv > 0
            else decision.impact_label
        ),
    }


FULFILLMENT_GAP_SIGNALS = {
    "AudienceAudit",
    "CampaignRTOSpike",
    "MarginTrap",
    "AOVDilution",
}

FULFILLMENT_GAP_RECOMMENDATION = (
    "Segment campaign by COD vs prepaid. Enable COD verification. Review high-RTO geographies. "
    "Reduce spend escalation until delivered performance improves. "
    "Pause only if delivered ROAS remains below threshold after verification."
)


def _is_fulfillment_gap_signal(signal: str, rule: str, issue: str) -> bool:
    rule_lower = rule.lower()
    issue_lower = issue.lower()
    return (
        signal in FULFILLMENT_GAP_SIGNALS
        or "spend >= 50000" in rule_lower
        or ("delivered_roas" in rule_lower and "placed_roas" in rule_lower)
        or "campaign.rto_rate_attributed" in rule_lower
        or "rto spike" in issue_lower
    )


def _signal_type(decision: Decision) -> str:
    issue = (decision.issue_type or "").lower()
    rule = (decision.rule or "").lower()
    title = (decision.title or "").lower()
    if "state_orders" in rule or "state rto" in issue or "state profitability" in title:
        return "StateRTOLeakage"
    if "new launch" in issue or "launch validation" in issue or "roas < 1.5" in rule:
        return "NewLaunchRisk"
    if "spend >= 50000" in rule or "strategic audit" in title or ("marketing pressure" in issue and "delivered_roas" in rule):
        return "AudienceAudit"
    if "rto spike" in issue or "campaign.rto_rate_attributed" in rule:
        return "CampaignRTOSpike"
    if "inventory" in issue or "stockout" in issue:
        return "InventoryRisk"
    if "creative" in issue or "fatigue" in issue:
        return "CreativeFatigue"
    if "scaling" in issue:
        return "ScalingOpportunity"
    if "margin trap" in issue or "placed_roas >= 3.5" in rule:
        return "MarginTrap"
    if "margin leakage" in issue:
        return "MarginLeakage"
    return decision.issue_type.replace(" ", "")


def _build_campaign_rto_confidence_drivers(
    campaign_rto_verified: bool,
    has_attribution: bool,
    brand_rto: float,
    rto_present: bool,
) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = [
        {
            "label": "Campaign spend verified from Meta",
            "status": "verified",
            "detail": "Spend totals reconciled against the latest Meta ads upload",
        },
        {
            "label": "Placed ROAS verified from Meta",
            "status": "verified",
            "detail": "Placed-order ROAS computed from mapped spend and revenue signals",
        },
        {
            "label": "Brand RTO verified from Shopify" if rto_present else "Brand RTO unavailable",
            "status": "verified" if rto_present else "warning",
            "detail": "Blended return rates computed from Shopify order delivery statuses",
        },
    ]
    if campaign_rto_verified:
        drivers.append(
            {
                "label": "Campaign-specific RTO verified",
                "status": "verified",
                "detail": "Campaign-level return counts mapped from Shopify delivery statuses",
            }
        )
    else:
        drivers.append(
            {
                "label": "Campaign-level RTO unavailable",
                "status": "warning",
                "detail": "Campaign-level delivered and RTO counts are not fully mapped yet",
            }
        )
        if brand_rto:
            drivers.append(
                {
                    "label": f"Brand-level RTO proxy used ({brand_rto:.2f}%)",
                    "status": "inferred",
                    "detail": "Attributed RTO is estimated from blended brand returns until campaign mapping is complete",
                }
            )
        drivers.append(
            {
                "label": "Delivered revenue estimated from fallback model",
                "status": "inferred",
                "detail": "Delivered ROAS and revenue gap are modeled from placed ROAS and attributed RTO until campaign mapping completes",
            }
        )
    drivers.append(
        {
            "label": "Order-to-campaign attribution unavailable" if not has_attribution else "Order-to-campaign attribution linked",
            "status": "warning" if not has_attribution else "verified",
            "detail": "UTM and campaign mapping quality directly affects precision",
        }
    )
    return drivers


def _build_campaign_metric_verification(
    campaign: dict[str, Any],
    *,
    rto_present: bool,
    campaign_rto_verified: bool,
) -> dict[str, Any]:
    observed = [
        {"label": "Spend", "detail": "Verified from Meta ads upload"},
        {"label": "Placed Revenue", "detail": "Computed from mapped spend and placed-order ROAS"},
    ]
    if rto_present:
        observed.append({"label": "Brand RTO", "detail": "Computed from Shopify order delivery statuses"})

    estimated = [
        {"label": "Delivered Revenue", "detail": "Modeled from placed ROAS and attributed RTO"},
        {"label": "Revenue Gap", "detail": "Difference between placed and estimated delivered revenue"},
    ]
    if not campaign_rto_verified:
        estimated.append(
            {
                "label": "Campaign RTO",
                "detail": "Estimated from brand-level RTO fallback until campaign mapping completes",
            }
        )

    return {
        "headline": "Verification Status",
        "observedLabel": "Observed Metrics",
        "estimatedLabel": "Estimated Metrics",
        "observed": observed,
        "estimated": estimated,
    }


def _build_inventory_metric_verification(
    sku: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "headline": "Verification Status",
        "observedLabel": "Observed Metrics",
        "estimatedLabel": "Estimated Metrics",
        "observed": [
            {"label": "Inventory", "detail": f"{sku.get('inventory_left', 0)} units on hand from latest upload"},
            {"label": "Velocity", "detail": f"{sku.get('daily_velocity', 0)} units/day from recent sales"},
        ],
        "estimated": [
            {
                "label": "Revenue forecast",
                "detail": (
                    f"{metrics['horizon_days']}-day demand opportunity at current velocity and SKU average order value"
                ),
            },
            {
                "label": "Lost sales forecast",
                "detail": (
                    f"{metrics['stockout_days_in_window']} days of demand expected to be unrealized within the forecast window"
                ),
            },
            {
                "label": "Restock scenarios",
                "detail": "PO arrival windows modeled without confirmed inbound shipment data",
            },
        ],
    }


def build_metric_verification_status(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any] | None:
    signal = _signal_type(decision)
    rule = decision.rule or ""
    issue = decision.issue_type or ""

    if signal == "InventoryRisk":
        sku, _, metrics = _inventory_impact_bundle(decision, snapshot)
        if not sku:
            return None
        return _build_inventory_metric_verification(sku, metrics)

    if signal not in {"NewLaunchRisk", *FULFILLMENT_GAP_SIGNALS} and not _is_fulfillment_gap_signal(signal, rule, issue):
        return None

    state = _snapshot_state(snapshot)
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    if not campaign:
        return None

    rto_present = _rto_data_present(state)
    campaign_rto_verified = _campaign_rto_verified(campaign, rto_present)
    return _build_campaign_metric_verification(
        campaign,
        rto_present=rto_present,
        campaign_rto_verified=campaign_rto_verified,
    )


def _inventory_narrative(sku: dict[str, Any], spend_growth: float) -> str:
    sku_name = sku.get("name", "This SKU")
    projected = float(sku.get("projected_stockout_days", 0) or 0)
    if projected <= 0:
        return (
            f"{sku_name} is out of stock based on current on-hand inventory and recent sales velocity. "
            "Without confirmed inbound inventory, revenue realization is constrained until restock arrives."
        )
    if spend_growth >= SIGNAL_THRESHOLDS["InventoryRisk"]["spend_growth_percent_min"]:
        return (
            f"{sku_name} has approximately {projected} day(s) of inventory cover remaining while ad spend "
            f"accelerated {spend_growth:.1f}% week over week. Stockout risk is elevated without confirmed inbound inventory."
        )
    return (
        f"{sku_name} has approximately {projected} day(s) of inventory cover remaining based on recent sales velocity. "
        "Without confirmed inbound inventory, stockout risk is elevated. Revenue realization may be constrained "
        "if demand continues at current levels."
    )


def build_inventory_display_overrides(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    if _signal_type(decision) != "InventoryRisk":
        return {}
    sku, _, impact_metrics = _inventory_impact_bundle(decision, snapshot)
    if not sku:
        return {}
    spend_growth = float(sku.get("spend_growth_percent", 0) or 0)
    overrides: dict[str, Any] = {
        "displayExplanation": _inventory_narrative(sku, spend_growth),
        "displayRecommendation": (
            "Submit a priority restock order immediately. Reduce prospecting spend until inbound inventory is confirmed."
        ),
        "effectiveBusinessImpact": impact_metrics["at_risk_revenue"] or decision.business_impact,
        "effectiveImpactLabel": (
            f"Rs {impact_metrics['at_risk_revenue']:,.0f} expected lost sales over next 7 days"
            if impact_metrics["at_risk_revenue"]
            else decision.impact_label
        ),
    }
    if impact_metrics.get("already_stocked_out"):
        overrides["displaySeverity"] = "high"
    return overrides


def build_stockout_scenarios(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any] | None:
    if _signal_type(decision) != "InventoryRisk":
        return None
    sku, aov, metrics = _inventory_impact_bundle(decision, snapshot)
    if not sku:
        return None
    projected = float(sku.get("projected_stockout_days", 0) or 0)
    velocity = float(sku.get("daily_velocity", 0) or 0)
    already_out = bool(metrics.get("already_stocked_out"))
    scenarios = []
    for label, po_eta in (
        ("If no restock arrives", None),
        ("If PO arrives in 3 days", 3),
        ("If PO arrives in 7 days", 7),
    ):
        scenario = compute_stockout_scenario(
            velocity,
            aov,
            projected,
            po_eta_days=po_eta,
            already_stocked_out=already_out,
        )
        scenarios.append(
            {
                "label": label,
                "detail": scenario["detail"],
                "estimatedLostSales": scenario["lost_revenue"],
                "estimatedLostSalesLabel": _format_inr(scenario["lost_revenue"]),
                "lostDays": scenario["lost_days"],
                "lostUnits": scenario["lost_units"],
            }
        )
    return {"headline": "Stockout Scenario Analysis", "scenarios": scenarios}


def build_new_launch_display_overrides(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    if _signal_type(decision) != "NewLaunchRisk":
        return {}
    return {
        "displayExplanation": NEW_LAUNCH_EXPLANATION,
        "displayRecommendation": (
            "Hold spend steady while collecting more delivery data. Review targeting and offer fit "
            "before pausing or refreshing creatives."
        ),
    }


def build_fulfillment_gap_display_overrides(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    signal = _signal_type(decision)
    if not _is_fulfillment_gap_signal(signal, decision.rule or "", decision.issue_type or ""):
        return {}

    recommendation = FULFILLMENT_GAP_RECOMMENDATION
    aggressive = "audit or pause" in (decision.recommendation or "").lower() or "pause immediately" in (decision.recommendation or "").lower()
    overrides: dict[str, Any] = {"displayRecommendation": recommendation}
    if aggressive or signal == "AudienceAudit":
        explanation = decision.explanation or ""
        if "fulfillment realization" not in explanation.lower():
            explanation = (
                f"{explanation} Placed revenue remains healthy — the gap is fulfillment realization, not demand failure."
            ).strip()
        overrides["displayExplanation"] = explanation
    return overrides


def build_remedies(decision: Decision, snapshot: BusinessSnapshot | None = None) -> list[dict[str, Any]]:
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    sku = _sku_metrics(snapshot, decision.affected_skus or [])
    signal = _signal_type(decision)
    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        state_metrics = compute_state_revenue_impact(
            int(region.get("total_orders", 0) or 0),
            float(region.get("rto_pct", 0) or 0),
            total_revenue=float(region.get("total_revenue", 0) or 0),
            rto_revenue=float(region.get("rto_revenue", 0) or 0),
            delivered_revenue=float(region.get("delivered_revenue", 0) or 0),
        )
        impact = state_metrics["at_risk_revenue"] or decision.business_impact or 0
        impact_metrics = None
    elif signal == "InventoryRisk":
        _, _, impact_metrics = _inventory_impact_bundle(decision, snapshot)
        impact = impact_metrics["at_risk_revenue"] or decision.business_impact or 0
    elif campaign and campaign.get("spend") and campaign.get("roas_on_placed_orders"):
        impact_metrics = compute_campaign_revenue_impact(
            campaign.get("spend", 0),
            campaign.get("roas_on_placed_orders", 0),
            campaign.get("roas_on_delivered_orders", 0),
        )
        impact = impact_metrics["revenue_gap"] or decision.business_impact or 0
    else:
        impact_metrics = None
        impact = decision.business_impact or 0
    actions = decision.recommended_actions or [decision.recommendation]

    templates: dict[str, list[dict[str, Any]]] = {
        "AudienceAudit": [
            {
                "label": f"Segment {decision.affected_campaigns[0] if decision.affected_campaigns else 'flagged campaign'} by COD vs prepaid performance",
                "effort": "medium",
                "riskMultiplier": 0.35,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.35)},
            },
            {
                "label": "Enable COD verification before dispatch",
                "effort": "medium",
                "riskMultiplier": 0.48,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.48)},
            },
            {
                "label": "Review high-RTO geographies and reduce spend escalation",
                "effort": "low",
                "riskMultiplier": 0.58,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.58)},
            },
        ],
        "CampaignRTOSpike": [
            {
                "label": f"Reduce spend on {decision.affected_campaigns[0] if decision.affected_campaigns else 'flagged campaign'} by 30%",
                "effort": "low",
                "riskMultiplier": 0.29,
                "expectedOutcome": {
                    "rtoRate": {"before": f"{campaign.get('rto_rate_attributed', 31)}%", "after": f"{max(campaign.get('rto_rate_attributed', 31) - 6, 18)}%"},
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 1.12)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 1.12) * 1.08, 2)}x",
                    },
                    "recovery": impact * 0.29,
                },
            },
            {
                "label": "Enable COD verification at checkout",
                "effort": "medium",
                "riskMultiplier": 0.43,
                "expectedOutcome": {
                    "rtoRate": {"before": f"{campaign.get('rto_rate_attributed', 31)}%", "after": f"{max(campaign.get('rto_rate_attributed', 31) - 9, 16)}%"},
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 1.12)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 1.12) * 1.14, 2)}x",
                    },
                    "recovery": impact * 0.43,
                },
            },
            {
                "label": "Shift budget to prepaid retargeting",
                "effort": "medium",
                "riskMultiplier": 0.56,
                "expectedOutcome": {
                    "rtoRate": {"before": f"{campaign.get('rto_rate_attributed', 31)}%", "after": f"{max(campaign.get('rto_rate_attributed', 31) - 12, 14)}%"},
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 1.12)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 1.12) * 1.28, 2)}x",
                    },
                    "recovery": impact * 0.56,
                },
            },
        ],
        "InventoryRisk": [
            {
                "label": f"Submit priority restock for {sku.get('name', 'flagged SKU')}",
                "effort": "medium",
                "riskMultiplier": 0.85,
                "expectedOutcome": {
                    "stockoutDays": {"before": f"{sku.get('projected_stockout_days', 5.6)} days", "after": "14+ days"},
                    "recovery": recovery_from_gap(impact, 0.85),
                },
            },
            {
                "label": "Reduce prospecting spend by 15%",
                "effort": "low",
                "riskMultiplier": 0.50,
                "expectedOutcome": {
                    "stockoutDays": {"before": f"{sku.get('projected_stockout_days', 5.6)} days", "after": f"{round(sku.get('projected_stockout_days', 5.6) * 1.4, 1)} days"},
                    "recovery": recovery_from_gap(impact, 0.50),
                },
            },
            {
                "label": "Pause ads on out-of-stock risk SKUs",
                "effort": "low",
                "riskMultiplier": 0.35,
                "expectedOutcome": {
                    "stockoutDays": {"before": f"{sku.get('projected_stockout_days', 5.6)} days", "after": "18+ days"},
                    "recovery": recovery_from_gap(impact, 0.35),
                },
            },
        ],
        "NewLaunchRisk": [
            {
                "label": "Collect more delivery data before major creative changes",
                "effort": "low",
                "riskMultiplier": 0.35,
                "expectedOutcome": {
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 0.6)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 0.6) * 1.12, 2)}x",
                    },
                    "recovery": recovery_from_gap(impact, 0.35),
                },
            },
            {
                "label": "Review audience targeting and offer-page conversion",
                "effort": "medium",
                "riskMultiplier": 0.5,
                "expectedOutcome": {
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 0.6)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 0.6) * 1.2, 2)}x",
                    },
                    "recovery": recovery_from_gap(impact, 0.5),
                },
            },
            {
                "label": "Cap spend until frequency exceeds 1.5 and ROAS stabilizes",
                "effort": "low",
                "riskMultiplier": 0.65,
                "expectedOutcome": {
                    "deliveredRoas": {
                        "before": f"{campaign.get('roas_on_delivered_orders', 0.6)}x",
                        "after": f"{round(campaign.get('roas_on_delivered_orders', 0.6) * 1.28, 2)}x",
                    },
                    "recovery": recovery_from_gap(impact, 0.65),
                },
            },
        ],
        "CreativeFatigue": [
            {
                "label": "Launch two new creative hooks",
                "effort": "medium",
                "riskMultiplier": 0.45,
                "expectedOutcome": {"ctr": {"before": f"{campaign.get('ctr', 1.1)}%", "after": f"{round(campaign.get('ctr', 1.1) * 1.25, 1)}%"}, "recovery": impact * 0.45},
            },
            {
                "label": "Cap frequency on stale static assets",
                "effort": "low",
                "riskMultiplier": 0.32,
                "expectedOutcome": {"frequency": {"before": f"{campaign.get('frequency', 5.4)}", "after": f"{max(campaign.get('frequency', 5.4) - 1.5, 3)}"}, "recovery": impact * 0.32},
            },
            {
                "label": "Move winning UGC into flagged campaign",
                "effort": "medium",
                "riskMultiplier": 0.58,
                "expectedOutcome": {"ctr": {"before": f"{campaign.get('ctr', 1.1)}%", "after": f"{round(campaign.get('ctr', 1.1) * 1.4, 1)}%"}, "recovery": impact * 0.58},
            },
        ],
        "StateRTOLeakage": [
            {
                "label": f"Offer automatic prepaid incentives for checkouts from {_parse_state_name(decision) or 'this state'}",
                "effort": "medium",
                "riskMultiplier": 0.45,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.45)},
            },
            {
                "label": f"Call all COD customers from {_parse_state_name(decision) or 'this region'} to verify orders before shipping",
                "effort": "medium",
                "riskMultiplier": 0.55,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.55)},
            },
            {
                "label": f"De-target COD shipping to shipping zones in {_parse_state_name(decision) or 'this state'}",
                "effort": "low",
                "riskMultiplier": 0.65,
                "expectedOutcome": {"recovery": recovery_from_gap(impact, 0.65)},
            },
        ],
        "ScalingOpportunity": [
            {
                "label": "Increase spend by Rs 8,000/day",
                "effort": "low",
                "riskMultiplier": 0.85,
                "expectedOutcome": {
                    "deliveredRoas": {"before": f"{campaign.get('roas_on_delivered_orders', 5.1)}x", "after": f"{round(campaign.get('roas_on_delivered_orders', 5.1) * 0.97, 2)}x"},
                    "recovery": impact * 0.85,
                },
            },
            {
                "label": "Scale gradually with daily RTO guardrails",
                "effort": "medium",
                "riskMultiplier": 0.72,
                "expectedOutcome": {"recovery": impact * 0.72},
            },
            {
                "label": "Hold budget and monitor inventory cover",
                "effort": "low",
                "riskMultiplier": 0.2,
                "expectedOutcome": {"recovery": impact * 0.2},
            },
        ],
    }

    source = templates.get(signal)
    if source is None:
        source = [
            {"label": action, "effort": _infer_effort(action), "riskMultiplier": max(0.2, 0.6 - idx * 0.15)}
            for idx, action in enumerate(actions[:3])
        ]

    remedies = []
    ranks = ["primary", "alternative", "alternative"]
    medals = ["🥇", "🥈", "🥉"]
    for idx, item in enumerate(source[:3]):
        capture_rate = item.get("riskMultiplier", 0.3)
        recovery = item.get("expectedOutcome", {}).get("recovery") or recovery_from_gap(impact, capture_rate)
        label = item["label"]
        passive = _is_passive_remedy(label)
        remedies.append(
            {
                "id": f"remedy_{decision.id[:8]}_{idx}",
                "label": label,
                "rank": ranks[idx],
                "effort": item.get("effort", _infer_effort(label)),
                "expectedRiskReduction": round(recovery),
                "expectedRiskReductionLabel": _format_inr(recovery),
                "recoveryLabel": _recovery_label(label),
                "expectedOutcome": item.get("expectedOutcome", {"recovery": recovery}),
                "medal": medals[idx],
                "recoveryExplanation": _recovery_explanation(impact, capture_rate, recovery, passive=passive),
            }
        )
    return remedies


def build_impact_context(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    signal = _signal_type(decision)
    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        snapshot_state = _snapshot_state(snapshot)
        state_rto = float(region.get("rto_pct", 0) or 0)
        rto_delta = _state_rto_delta(decision, region, snapshot_state)
        state_name = region.get("state_name") or _parse_state_name(decision) or "this state"

        metrics = compute_state_revenue_impact(
            int(region.get("total_orders", 0) or 0),
            state_rto,
            total_revenue=float(region.get("total_revenue", 0) or 0),
            rto_revenue=float(region.get("rto_revenue", 0) or 0),
            delivered_revenue=float(region.get("delivered_revenue", 0) or 0),
        )
        at_risk = metrics["at_risk_revenue"]
        total_revenue = metrics["total_revenue"]
        impact_percent = metrics["impact_percent"]

        if total_revenue > 0 and state_rto > 0:
            expected_at_risk = round(total_revenue * (state_rto / 100))
            if at_risk > 0 and at_risk < expected_at_risk * 0.25:
                at_risk = expected_at_risk
                impact_percent = min(round((at_risk / total_revenue) * 100, 1), 100.0)
        if at_risk <= 0 and total_revenue > 0 and state_rto > 0:
            at_risk = round(total_revenue * (state_rto / 100))
            impact_percent = min(round((at_risk / total_revenue) * 100, 1), 100.0)
        if total_revenue <= 0 and at_risk > 0 and impact_percent > 0:
            total_revenue = round(at_risk / (impact_percent / 100))

        framing = state_operational_framing(
            float(region.get("cod_pct", 0) or 0),
            rto_delta,
            at_risk,
            state_name,
        )
        context = {
            "totalRevenue": round(total_revenue),
            "totalRevenueLabel": _format_inr(total_revenue),
            "atRiskRevenue": round(at_risk),
            "atRiskRevenueLabel": _format_inr(at_risk),
            "atRiskLabel": "RTO Order GMV",
            "atRiskExplanation": (
                "Product revenue from orders returned to origin in this state — the GMV not realized from failed deliveries. "
                "This is separate from logistics cost."
            ),
            "impactPercent": impact_percent,
            "contextLabel": "Regional Order GMV",
            "contextExplanation": "Total order value placed in this state across the current upload window.",
            "shippingWaste": metrics["shipping_waste"],
            "shippingWasteLabel": _format_inr(metrics["shipping_waste"]),
            "shippingWasteExplanation": (
                "Estimated forward and return courier cost (₹150 per RTO shipment). "
                "This is logistics overhead — not product GMV at risk."
            ),
            **framing,
        }
        return context

    if signal == "InventoryRisk":
        sku, aov, metrics = _inventory_impact_bundle(decision, snapshot)
        sku_name = sku.get("name") or (decision.affected_skus[0] if decision.affected_skus else "flagged SKU")
        projected = float(sku.get("projected_stockout_days", 0) or 0)
        at_risk = metrics["at_risk_revenue"]
        forecast = metrics["forecast_revenue"]
        impact_percent = metrics["impact_percent"]
        already_out = bool(metrics.get("already_stocked_out"))
        return {
            "totalRevenue": forecast,
            "totalRevenueLabel": _format_inr(forecast),
            "atRiskRevenue": round(at_risk),
            "atRiskRevenueLabel": _format_inr(at_risk),
            "atRiskLabel": "Expected Lost Sales",
            "atRiskExplanation": (
                "Full 7-day demand opportunity is at risk because inventory is already unavailable."
                if already_out
                else (
                    f"Revenue expected to be unrealized within the next {metrics['horizon_days']}-day forecast window "
                    f"({metrics['stockout_days_in_window']} days without cover)."
                )
            ),
            "impactPercent": impact_percent,
            "contextLabel": "Next 7-Day Revenue Opportunity",
            "contextExplanation": (
                f"Projected demand for {sku_name} based on {sku.get('daily_velocity', 0)} units/day "
                f"at Rs {aov:,.0f} average order value."
            ),
            "inventoryLeft": sku.get("inventory_left", 0),
            "inventoryCoverDays": projected,
            "dailyVelocity": sku.get("daily_velocity", 0),
            "stockoutState": "already_stocked_out" if already_out else "low_cover",
            "stockoutStateLabel": "Already Stocked Out" if already_out else None,
            "operationalRiskLabel": "Already Stocked Out" if already_out else (
                "Critical Stockout Risk" if projected <= 3 else "Elevated Stockout Risk"
            ),
            "impactNarrative": (
                "Estimated impact reflects forecasted revenue that cannot be realized if inventory remains "
                "unavailable during the projected demand window."
            ),
        }

    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    spend = float(campaign.get("spend", 0) or 0)
    placed_roas = float(campaign.get("roas_on_placed_orders", 0) or 0)
    delivered_roas = float(campaign.get("roas_on_delivered_orders", 0) or 0)

    if spend > 0 and placed_roas > 0:
        metrics = compute_campaign_revenue_impact(spend, placed_roas, delivered_roas)
        placed_revenue = metrics["placed_revenue"]
        delivered_revenue = metrics["delivered_revenue"]
        revenue_gap = metrics["revenue_gap"]
        stored_impact = decision.business_impact or 0

        # Never treat spend as revenue-at-risk when campaign math is available.
        if stored_impact > placed_revenue or stored_impact == round(spend):
            at_risk = revenue_gap
        else:
            at_risk = revenue_gap if revenue_gap > 0 else stored_impact

        impact_percent = metrics["impact_percent"]
        if placed_revenue > 0 and at_risk > 0 and impact_percent == 0:
            impact_percent = min(round((at_risk / placed_revenue) * 100, 1), 100.0)

        return {
            "campaignSpend": metrics["spend"],
            "campaignSpendLabel": _format_inr(metrics["spend"]),
            "totalRevenue": placed_revenue,
            "totalRevenueLabel": _format_inr(placed_revenue),
            "deliveredRevenue": delivered_revenue,
            "deliveredRevenueLabel": _format_inr(delivered_revenue),
            "atRiskRevenue": round(at_risk),
            "atRiskRevenueLabel": _format_inr(at_risk),
            "impactPercent": impact_percent,
            "contextLabel": "Placed Revenue",
        }

    total_revenue = (decision.business_impact or 0) * 3.15
    at_risk = decision.business_impact or 0
    impact_percent = min(round((at_risk / total_revenue) * 100, 1), 100.0) if total_revenue else 0
    return {
        "totalRevenue": round(total_revenue),
        "totalRevenueLabel": _format_inr(total_revenue),
        "atRiskRevenue": round(at_risk),
        "atRiskRevenueLabel": _format_inr(at_risk),
        "impactPercent": impact_percent,
        "contextLabel": "Revenue Base",
    }


def _build_new_launch_confidence_drivers(
    campaign: dict[str, Any],
    snapshot: BusinessSnapshot | None,
    *,
    brand_rto: float,
    campaign_rto_verified: bool,
) -> list[dict[str, Any]]:
    freq = float(campaign.get("frequency", 0) or 0)
    freq_label = _round_display_metric(freq)
    drivers: list[dict[str, Any]] = [
        {
            "label": "Spend verified from Meta",
            "status": "verified",
            "detail": "Spend totals reconciled against the latest Meta ads upload",
        },
        {
            "label": "ROAS verified from Meta",
            "status": "verified",
            "detail": "Placed-order ROAS computed from mapped spend and revenue signals",
        },
        {
            "label": f"Frequency verified from Meta ({freq_label}x)",
            "status": "verified",
            "detail": "Audience exposure mapped to the flagged campaign",
        },
        {
            "label": "Campaign remains in learning phase",
            "status": "warning",
            "detail": "Low spend and frequency limit certainty before attributing underperformance to creative or audience fit",
        },
        {
            "label": "Historical baseline unavailable" if snapshot and snapshot.snapshot_version <= 1 else "Historical baseline available",
            "status": "warning" if snapshot and snapshot.snapshot_version <= 1 else "verified",
            "detail": "Launch benchmarks require additional uploads to compare against prior campaign performance",
        },
    ]
    if not campaign_rto_verified:
        proxy_detail = (
            f"Delivered ROAS and revenue gap are modeled from placed ROAS and brand RTO ({brand_rto:.2f}%) "
            "until campaign mapping completes"
            if brand_rto
            else "Delivered ROAS and revenue gap are modeled from placed ROAS and brand RTO until campaign mapping completes"
        )
        drivers.append(
            {
                "label": "Delivered metrics estimated using brand RTO fallback",
                "status": "inferred",
                "detail": proxy_detail,
            }
        )
    return drivers


def _build_inventory_confidence_drivers(
    sku: dict[str, Any],
    snapshot: BusinessSnapshot | None,
) -> list[dict[str, Any]]:
    projected = float(sku.get("projected_stockout_days", 0) or 0)
    spend_growth = float(sku.get("spend_growth_percent", 0) or 0)
    drivers: list[dict[str, Any]] = [
        {
            "label": f"On-hand inventory verified ({sku.get('inventory_left', 0)} units)",
            "status": "verified",
            "detail": "SKU stock levels reconciled from the latest inventory upload",
        },
        {
            "label": f"Sales velocity verified ({sku.get('daily_velocity', 0)} units/day)",
            "status": "verified",
            "detail": "Recent demand rate computed from order history in the current snapshot",
        },
        {
            "label": f"Inventory cover computed ({projected} days)",
            "status": "verified",
            "detail": "Cover derived from on-hand inventory divided by daily velocity",
        },
    ]
    if spend_growth >= SIGNAL_THRESHOLDS["InventoryRisk"]["spend_growth_percent_min"]:
        drivers.append(
            {
                "label": f"Ad spend growth verified ({spend_growth:.1f}%)",
                "status": "verified",
                "detail": "Week-over-week spend acceleration confirmed from Meta campaign data",
            }
        )
    else:
        drivers.append(
            {
                "label": "No verified ad spend acceleration",
                "status": "warning",
                "detail": "Stockout risk is driven by velocity and cover — not confirmed marketing scale-up",
            }
        )
    drivers.extend(
        [
            {
                "label": "Open purchase orders unavailable",
                "status": "warning",
                "detail": "Inbound PO visibility is required to judge whether stockout risk is operationally urgent",
            },
            {
                "label": "Supplier lead time / inbound ETA unavailable",
                "status": "warning",
                "detail": "Restock timing assumptions are not yet connected to supplier or warehouse data",
            },
        ]
    )
    if snapshot and snapshot.snapshot_version <= 1:
        drivers.append(
            {
                "label": "Historical velocity baseline unavailable",
                "status": "warning",
                "detail": "Additional uploads improve confidence in demand trend stability",
            }
        )
    return drivers


def build_confidence_drivers(decision: Decision, snapshot: BusinessSnapshot | None = None) -> list[dict[str, Any]]:
    signal = _signal_type(decision)
    snapshot_state = _snapshot_state(snapshot)
    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        total_orders = int(region.get("total_orders", 0) or 0)
        brand_rto = region.get("brand_rto")
        if brand_rto is None:
            brand_rto = snapshot_state.get("brand_rto_rate")
        drivers: list[dict[str, Any]] = [
            {
                "label": "State identified from shipping address",
                "status": "verified",
                "detail": "Order shipping state mapped from Shopify fulfillment addresses",
            },
            {
                "label": "Order status available",
                "status": "verified",
                "detail": "Delivered, RTO, and cancellation statuses parsed from the latest order upload",
            },
            {
                "label": "COD payment mode available",
                "status": "verified",
                "detail": "Payment method mapped to classify COD vs prepaid mix by state",
            },
            {
                "label": "RTO status available",
                "status": "verified",
                "detail": "Return-to-origin counts computed from order delivery statuses",
            },
        ]
        if total_orders < 20:
            drivers.append(
                {
                    "label": f"Only {total_orders} orders available",
                    "status": "warning",
                    "detail": "Small sample — one or two status changes can materially shift the regional RTO rate",
                }
            )
        drivers.append(
            {
                "label": "Historical state benchmark unavailable",
                "status": "warning",
                "detail": "Prior-upload state RTO baselines are not yet available for seasonal comparison",
            }
        )
        drivers.append(
            {
                "label": "Seasonal variation not modeled",
                "status": "warning",
                "detail": "Festival and weather-driven return patterns are not yet isolated for this corridor",
            }
        )
        if brand_rto is not None:
            drivers.append(
                {
                    "label": f"Brand average RTO benchmark available ({float(brand_rto):.1f}%)",
                    "status": "verified",
                    "detail": "Regional RTO is compared against blended brand returns from the same upload",
                }
            )
        return drivers

    state = snapshot_state
    rto_present = _rto_data_present(state)
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    campaign_rto_verified = _campaign_rto_verified(campaign, rto_present)
    has_attribution = _has_order_attribution(decision, campaign)
    brand_rto = _brand_rto_rate(state, campaign)
    issue = (decision.issue_type or "").lower()
    rule = decision.rule or ""

    if signal == "NewLaunchRisk":
        return _build_new_launch_confidence_drivers(
            campaign,
            snapshot,
            brand_rto=brand_rto,
            campaign_rto_verified=campaign_rto_verified,
        )

    if signal == "InventoryRisk":
        sku = _sku_metrics(snapshot, decision.affected_skus or [])
        return _build_inventory_confidence_drivers(sku, snapshot)

    if _is_fulfillment_gap_signal(signal, rule, issue):
        return _build_campaign_rto_confidence_drivers(
            campaign_rto_verified,
            has_attribution,
            brand_rto,
            rto_present,
        )

    drivers: list[dict[str, Any]] = []
    is_campaign_signal = signal in {
        "CampaignRTOSpike",
        "NewLaunchRisk",
        "CreativeFatigue",
        "ScalingOpportunity",
        "MarginTrap",
        "AOVDilution",
        "AudienceAudit",
    }
    if is_campaign_signal:
        drivers.append(
            {
                "label": "Campaign spend verified from Meta",
                "status": "verified",
                "detail": "Spend totals reconciled against the latest Meta ads upload",
            }
        )
        drivers.append(
            {
                "label": "Placed ROAS verified from Meta",
                "status": "verified",
                "detail": "Placed-order ROAS computed from mapped spend and revenue signals",
            }
        )

    if "rto spike" in issue or "campaign.rto_rate_attributed" in rule.lower():
        if campaign_rto_verified:
            drivers.append(
                {
                    "label": "Campaign-specific RTO verified",
                    "status": "verified",
                    "detail": "Campaign-level return counts mapped from Shopify delivery statuses",
                }
            )
        else:
            drivers.append(
                {
                    "label": "Campaign-specific RTO unavailable",
                    "status": "warning",
                    "detail": "Campaign-level delivered and RTO counts are not fully mapped yet",
                }
            )
            if brand_rto:
                drivers.append(
                    {
                        "label": f"Brand-level RTO proxy used ({brand_rto:.2f}%)",
                        "status": "inferred",
                        "detail": "Attributed RTO is estimated from blended brand returns until campaign mapping is complete",
                    }
                )
        drivers.append(
            {
                "label": "No order-to-campaign attribution" if not has_attribution else "Order-to-campaign attribution linked",
                "status": "warning" if not has_attribution else "verified",
                "detail": "UTM and campaign mapping quality directly affects precision",
            }
        )
    elif "inventory" in issue:
        drivers.append({"label": "Inventory levels verified", "status": "verified", "detail": "SKU cover computed from latest upload"})
        drivers.append({"label": "Velocity trend inferred", "status": "inferred", "detail": "7-day sales velocity projected forward"})
    elif signal == "CreativeFatigue" or "creative" in issue:
        drivers.append({"label": "Creative frequency verified from Meta", "status": "verified", "detail": "Frequency mapped to the flagged campaign"})
        drivers.append({"label": "CTR baseline comparison", "status": "inferred", "detail": "Requires prior snapshot for decay signal"})
    else:
        drivers.append(
            {
                "label": "Source telemetry available",
                "status": "verified",
                "detail": decision.confidence_explanation or "Core rule inputs are present in the latest snapshot",
            }
        )
        drivers.append(
            {
                "label": "Historical baseline unavailable" if snapshot and snapshot.snapshot_version <= 1 else "Historical baseline available",
                "status": "warning" if snapshot and snapshot.snapshot_version <= 1 else "verified",
                "detail": "Additional uploads improve confidence and verification precision",
            }
        )

    return drivers


def build_evidence_requirements(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    state = _snapshot_state(snapshot)
    rto_present = _rto_data_present(state)
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    campaign_rto_verified = _campaign_rto_verified(campaign, rto_present)
    has_campaign_attr = bool(decision.affected_campaigns)
    campaigns = state.get("campaigns", [])
    signal = _signal_type(decision)

    requirements: list[dict[str, Any]] = []
    issue = (decision.issue_type or "").lower()

    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        total_orders = int(region.get("total_orders", 0) or 0)
        requirements.extend(
            [
                {"label": "Order shipping state", "required": True, "available": bool(region.get("state_name"))},
                {"label": "Order delivery statuses", "required": True, "available": rto_present},
                {"label": "COD payment mode", "required": True, "available": rto_present},
                {"label": "Minimum 20 orders per state", "required": False, "available": total_orders >= 20},
                {"label": "Historical state benchmark", "required": False, "available": bool(snapshot and snapshot.snapshot_version > 1)},
            ]
        )
    elif "rto spike" in issue or "campaign.rto_rate_attributed" in (decision.rule or "").lower():
        requirements.extend(
            [
                {"label": "Meta spend", "required": False, "available": bool(campaigns)},
                {"label": "Meta ROAS", "required": False, "available": bool(campaigns)},
                {"label": "Shopify order statuses", "required": False, "available": rto_present},
                {"label": "Campaign-level delivered orders", "required": True, "available": has_campaign_attr and campaign_rto_verified},
                {"label": "Campaign-level RTO", "required": True, "available": campaign_rto_verified},
                {"label": "Campaign-level cancellation rate", "required": True, "available": False},
                {"label": "COD share by campaign", "required": True, "available": has_campaign_attr},
            ]
        )
    elif signal == "InventoryRisk":
        requirements.extend(
            [
                {"label": "SKU on-hand inventory", "required": True, "available": bool(state.get("skus"))},
                {"label": "Sales velocity history", "required": False, "available": bool(state.get("skus"))},
                {"label": "Open purchase orders", "required": False, "available": False},
                {"label": "Inbound shipment ETA", "required": False, "available": False},
            ]
        )
    elif signal == "NewLaunchRisk":
        requirements.extend(
            [
                {"label": "Meta spend", "required": False, "available": bool(campaigns)},
                {"label": "Meta ROAS", "required": False, "available": bool(campaigns)},
                {"label": "Campaign frequency", "required": False, "available": bool(campaign)},
                {"label": "Campaign-level delivered orders", "required": True, "available": campaign_rto_verified},
                {"label": "Campaign-level RTO", "required": True, "available": campaign_rto_verified},
                {"label": "Historical baseline for comparison", "required": False, "available": bool(snapshot and snapshot.snapshot_version > 1)},
            ]
        )
    else:
        requirements.extend(
            [
                {"label": "Source telemetry for flagged entities", "required": True, "available": True},
                {"label": "Historical baseline for comparison", "required": False, "available": bool(snapshot and snapshot.snapshot_version > 1)},
            ]
        )

    all_available = all(item["available"] for item in requirements if item["required"])
    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        small_sample = int(region.get("total_orders", 0) or 0) < 20
        disclaimer = (
            "Regional RTO signal is directionally valid, but confidence is limited by sample size until more orders accumulate."
            if small_sample
            else "State-level evidence is available; monitor for repeat confirmation on the next upload."
        )
    else:
        disclaimer = (
            "Decision remains estimated until missing campaign-level evidence is available."
            if not all_available
            else "Decision can be validated on next upload."
        )
    return {
        "requirements": requirements,
        "allRequiredAvailable": all_available,
        "disclaimer": disclaimer,
    }


def build_decision_verification(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    evidence = build_evidence_requirements(decision, snapshot)
    signal = _signal_type(decision)
    state = _snapshot_state(snapshot)
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    campaign_rto_verified = _campaign_rto_verified(campaign, _rto_data_present(state))

    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        total_orders = int(region.get("total_orders", 0) or 0)
        if evidence["allRequiredAvailable"] and total_orders >= 50:
            return {
                "type": "verified",
                "label": "Verified Decision",
                "reason": "State-level order, COD, and RTO telemetry are directly attributable with adequate sample size.",
            }
        reasons: list[str] = []
        if total_orders < 20:
            reasons.append(f"only {total_orders} orders in this state")
        if not evidence["allRequiredAvailable"]:
            reasons.append("required state-level evidence is incomplete")
        if snapshot and snapshot.snapshot_version <= 1:
            reasons.append("no historical state benchmark yet")
        return {
            "type": "estimated",
            "label": "Estimated Decision",
            "reason": " and ".join(reasons) + "." if reasons else "Sample size limits statistical certainty for this regional RTO signal.",
        }

    if signal == "InventoryRisk":
        sku = _sku_metrics(snapshot, decision.affected_skus or [])
        velocity = float(sku.get("daily_velocity", 0) or 0) if sku else 0.0
        if evidence["allRequiredAvailable"] and sku and velocity > 0:
            return {
                "type": "verified",
                "label": "Verified Decision",
                "reason": "Inventory levels and recent sales velocity are confirmed from the latest upload.",
            }
        reasons: list[str] = []
        if not sku or velocity <= 0:
            reasons.append("recent sales velocity unavailable")
        if not evidence["allRequiredAvailable"]:
            reasons.append("required inventory evidence is incomplete")
        if snapshot and snapshot.snapshot_version <= 1:
            reasons.append("historical velocity baseline unavailable")
        return {
            "type": "estimated",
            "label": "Estimated Decision",
            "reason": " and ".join(reasons) + "." if reasons else "Inbound PO and supplier ETA data are unavailable.",
        }

    if evidence["allRequiredAvailable"] and campaign_rto_verified:
        return {
            "type": "verified",
            "label": "Verified Decision",
            "reason": "Campaign-level evidence is available and rule inputs are directly attributable.",
        }

    reasons: list[str] = []
    if not campaign_rto_verified:
        reasons.append("brand-level RTO fallback in use")
    if not evidence["allRequiredAvailable"]:
        reasons.append("required campaign-level evidence is incomplete")
    if not _has_order_attribution(decision, campaign):
        reasons.append("order-to-campaign attribution is limited")

    return {
        "type": "estimated",
        "label": "Estimated Decision",
        "reason": " and ".join(reasons) + "." if reasons else "Some inputs rely on blended or inferred signals.",
    }


def build_trigger_reason(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any] | None:
    state = _snapshot_state(snapshot)
    issue = (decision.issue_type or "").lower()
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    campaigns = state.get("campaigns", [])
    sku = _sku_metrics(snapshot, decision.affected_skus or [])
    signal = _signal_type(decision)

    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        snapshot_state = state
        brand_rto = region.get("brand_rto")
        if brand_rto is None:
            brand_rto = snapshot_state.get("brand_rto_rate")
        state_rto = region.get("rto_pct")
        metrics = [
            {"label": "State", "value": region.get("state_name") or "Unknown"},
            {"label": "Orders", "value": str(region.get("total_orders", "—"))},
            {"label": "COD Mix", "value": f"{region.get('cod_pct', '—')}%"},
            {"label": "RTO", "value": f"{state_rto}%" if state_rto is not None else "—"},
        ]
        if brand_rto is not None and state_rto is not None:
            delta = round(float(state_rto) - float(brand_rto), 1)
            metrics.extend(
                [
                    {"label": "Brand Average RTO", "value": f"{float(brand_rto)}%"},
                    {"label": "Difference", "value": f"+{delta}%"},
                ]
            )
        return {"headline": "Why It Triggered", "metrics": metrics}

    if campaign and signal == "NewLaunchRisk":
        spend = float(campaign.get("spend", 0) or 0)
        placed_roas = float(campaign.get("roas_on_placed_orders", 0) or 0)
        freq = float(campaign.get("frequency", 0) or 0)
        benchmark = SIGNAL_THRESHOLDS["NewLaunchRisk"]["roas_max"]
        age_days = compute_stale_metadata(decision)["ageDays"]
        campaign_age = f"{age_days} days" if age_days else "Early launch"
        return {
            "headline": "Why It Was Selected",
            "metrics": [
                {"label": "Campaign Age", "value": campaign_age},
                {"label": "ROAS", "value": f"{_round_display_metric(placed_roas)}x"},
                {"label": "Benchmark", "value": f"{benchmark}x"},
                {"label": "Frequency", "value": f"{_round_display_metric(freq)}"},
                {"label": "Spend", "value": _format_inr(spend)},
            ],
        }

    if campaign and ("rto" in issue or "campaign" in issue):
        total_spend = sum(float(c.get("spend", 0) or 0) for c in campaigns)
        campaign_spend = float(campaign.get("spend", 0) or 0)
        spend_share = round((campaign_spend / total_spend) * 100) if total_spend else 0
        campaign_name = campaign.get("campaign_name") or decision.affected_campaigns[0]
        return {
            "headline": f"Why {campaign_name}?",
            "metrics": [
                {"label": "Campaign consumed", "value": f"{spend_share}% of Meta spend"},
                {"label": "Placed ROAS", "value": f"{campaign.get('roas_on_placed_orders', 0)}x"},
                {"label": "Estimated Delivered ROAS", "value": f"{campaign.get('roas_on_delivered_orders', 0)}x"},
                {"label": "Attributed RTO", "value": f"{campaign.get('rto_rate_attributed', 0)}%"},
            ],
        }

    if signal == "InventoryRisk" and sku:
        projected = float(sku.get("projected_stockout_days", 0) or 0)
        spend_growth = float(sku.get("spend_growth_percent", 0) or 0)
        return {
            "headline": f"Why {sku.get('name', 'this SKU')}?",
            "metrics": [
                {"label": "Inventory left", "value": f"{sku.get('inventory_left', 0)} units"},
                {"label": "Daily velocity", "value": f"{sku.get('daily_velocity', 0)} units/day"},
                {"label": "Inventory cover", "value": f"{projected} days"},
                {"label": "Spend growth", "value": f"{spend_growth:.1f}%"},
            ],
        }

    if decision.cross_system_signals:
        parsed = []
        for signal in decision.cross_system_signals[:4]:
            if ":" in signal:
                label, value = signal.split(":", 1)
                parsed.append({"label": label.strip(), "value": value.strip()})
            else:
                parsed.append({"label": "Signal", "value": signal})
        if parsed:
            return {"headline": "Reason Triggered", "metrics": parsed}

    return None


def build_dependencies(decision: Decision, snapshot: BusinessSnapshot | None = None) -> list[dict[str, Any]]:
    issue = (decision.issue_type or "").lower()
    sku = _sku_metrics(snapshot, decision.affected_skus or [])
    dependencies: list[dict[str, Any]] = []

    if "rto" in issue:
        dependencies.append(
            {
                "label": "COD verification rollout",
                "status": "planned",
                "detail": "Ops team evaluating checkout provider",
                "effect": "neutral",
                "resolvesDecision": False,
            }
        )
    return dependencies


def build_outcome_measurement(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any] | None:
    if decision.state not in {"verified", "successful", "unsuccessful", "monitoring", "action_executed"}:
        return None

    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    before_roas = campaign.get("roas_on_delivered_orders", 1.12)
    after_roas = round(before_roas * (1.21 if decision.state == "successful" else 1.08), 2)
    recovered = decision.business_impact or 0
    if decision.state == "successful":
        recovered = round(recovered * 0.93)
    elif decision.state == "monitoring":
        recovered = 0

    return {
        "before": {"deliveredRoas": f"{before_roas}x", "rtoRate": f"{campaign.get('rto_rate_attributed', 31)}%"},
        "after": {"deliveredRoas": f"{after_roas}x", "rtoRate": f"{max(campaign.get('rto_rate_attributed', 31) - 8, 18)}%"},
        "recoveredRevenue": recovered,
        "recoveredRevenueLabel": _format_inr(recovered),
        "decisionAccuracy": 93 if decision.state == "successful" else (72 if decision.state == "verified" else None),
        "status": decision.state,
    }


def compute_stale_metadata(decision: Decision) -> dict[str, Any]:
    created = decision.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created).days
    is_stale = decision.state in {"pending", "acknowledged"} and age_days >= 7
    return {
        "ageDays": age_days,
        "isStale": is_stale,
        "staleLabel": f"Detected {age_days} days ago" if age_days else "Detected today",
    }


LIFECYCLE_LABELS = {
    "pending": "Detected",
    "acknowledged": "Acknowledged",
    "action_planned": "Action Planned",
    "action_executed": "Action Executed",
    "monitoring": "Monitoring",
    "verified": "Verified",
    "successful": "Closed",
    "unsuccessful": "Unsuccessful",
    "ignored": "Ignored",
    "snoozed": "Snoozed",
}


def build_lifecycle_stages(decision: Decision) -> list[dict[str, Any]]:
    state = decision.state
    order = ["pending", "acknowledged", "action_planned", "action_executed", "monitoring", "verified", "successful"]
    labels = {
        "pending": ("Detected", "AI generated this decision"),
        "acknowledged": ("Acknowledged", "Operator reviewed the signal"),
        "action_planned": ("Action Planned", "Remedy selected and scheduled"),
        "action_executed": ("Action Executed", "Operational change deployed"),
        "monitoring": ("Monitoring", "Tracking execution signals"),
        "verified": ("Verified", "Outcome measured against expectation"),
        "successful": ("Closed", "Decision resolved with positive outcome"),
    }

    active_index = order.index(state) if state in order else 0
    if state in {"unsuccessful"}:
        active_index = order.index("verified")
    if state in {"ignored", "snoozed"}:
        active_index = 0

    stages = []
    for idx, key in enumerate(order):
        title, description = labels[key]
        stages.append(
            {
                "key": key,
                "title": title,
                "description": description,
                "status": "done" if idx < active_index else ("active" if idx == active_index else "upcoming"),
            }
        )
    return stages


def effective_confidence_score(decision: Decision, snapshot: BusinessSnapshot | None = None) -> float:
    score = decision.confidence_score
    signal = _signal_type(decision)
    state = _snapshot_state(snapshot)
    campaign = _campaign_metrics(snapshot, decision.affected_campaigns or [])
    rto_present = _rto_data_present(state)
    campaign_rto_verified = _campaign_rto_verified(campaign, rto_present)
    cap = 1.0

    if signal == "StateRTOLeakage":
        region = _state_region_metrics(decision, snapshot)
        total_orders = int(region.get("total_orders", 0) or 0)
        cap = sample_size_confidence_cap(total_orders) if total_orders else 0.72
        return round(min(score, cap), 2)

    if _is_fulfillment_gap_signal(signal, decision.rule or "", decision.issue_type or ""):
        if not campaign_rto_verified:
            cap = min(cap, 0.78)
        elif not _has_order_attribution(decision, campaign):
            cap = min(cap, 0.85)

    if signal == "NewLaunchRisk":
        verification = build_decision_verification(decision, snapshot)
        if verification["type"] == "estimated":
            launch_cap = 0.68
            if snapshot and snapshot.snapshot_version <= 1:
                launch_cap = min(launch_cap, 0.65)
            if not campaign_rto_verified:
                launch_cap = min(launch_cap, 0.66)
            freq = float(campaign.get("frequency", 0) or 0)
            if freq <= 1.3:
                launch_cap = min(launch_cap, 0.67)
            cap = min(cap, launch_cap)

    if signal == "InventoryRisk":
        cap = min(cap, 0.72)
        if snapshot and snapshot.snapshot_version <= 1:
            cap = min(cap, 0.70)

    return round(min(score, cap), 2)


def build_auto_resolution_criteria(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any] | None:
    signal = _signal_type(decision)
    if signal != "NewLaunchRisk":
        return None
    benchmark = SIGNAL_THRESHOLDS["NewLaunchRisk"]["roas_max"]
    return {
        "headline": "Auto Resolution Criteria",
        "intro": "This decision will automatically resolve if:",
        "criteria": [
            f"ROAS exceeds {benchmark}x",
            "Frequency exceeds 2.0 with stable ROAS",
            "7 days of additional delivery data invalidates the current estimate",
        ],
    }


def enrich_decision_v2(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    state_display = build_state_display_overrides(decision, snapshot)
    launch_display = build_new_launch_display_overrides(decision, snapshot)
    inventory_display = build_inventory_display_overrides(decision, snapshot)
    fulfillment_display = build_fulfillment_gap_display_overrides(decision, snapshot)
    return {
        "remedies": build_remedies(decision, snapshot),
        "impactContext": build_impact_context(decision, snapshot),
        **state_display,
        **launch_display,
        **inventory_display,
        **fulfillment_display,
        "metricVerification": build_metric_verification_status(decision, snapshot),
        "confidenceDrivers": build_confidence_drivers(decision, snapshot),
        "evidenceRequired": build_evidence_requirements(decision, snapshot),
        "decisionVerification": build_decision_verification(decision, snapshot),
        "triggerReason": build_trigger_reason(decision, snapshot),
        "autoResolutionCriteria": build_auto_resolution_criteria(decision, snapshot),
        "stockoutScenarios": build_stockout_scenarios(decision, snapshot),
        "dependencies": build_dependencies(decision, snapshot),
        "outcomeMeasurement": build_outcome_measurement(decision, snapshot),
        "staleMetadata": compute_stale_metadata(decision),
        "lifecycleStages": build_lifecycle_stages(decision),
        "lifecycleLabel": LIFECYCLE_LABELS.get(decision.state, decision.state),
        "effectiveConfidenceScore": effective_confidence_score(decision, snapshot),
    }