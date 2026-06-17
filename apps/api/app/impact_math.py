"""Shared revenue impact calculations for campaign-level decisions."""

from __future__ import annotations

from typing import Any


def compute_campaign_revenue_impact(
    spend: float,
    placed_roas: float,
    delivered_roas: float | None = None,
) -> dict[str, Any]:
    spend = float(spend or 0)
    placed_roas = float(placed_roas or 0)
    delivered_roas = float(delivered_roas if delivered_roas is not None else placed_roas)

    placed_revenue = spend * placed_roas
    delivered_revenue = spend * delivered_roas
    revenue_gap = max(placed_revenue - delivered_revenue, 0)

    impact_percent = 0.0
    if placed_revenue > 0 and revenue_gap > 0:
        impact_percent = min(round((revenue_gap / placed_revenue) * 100, 1), 100.0)

    return {
        "spend": round(spend),
        "placed_roas": placed_roas,
        "delivered_roas": delivered_roas,
        "placed_revenue": round(placed_revenue),
        "delivered_revenue": round(delivered_revenue),
        "revenue_gap": round(revenue_gap),
        "impact_percent": impact_percent,
    }


def recovery_from_gap(revenue_gap: float, capture_rate: float) -> int:
    return round(max(revenue_gap, 0) * capture_rate)


def sample_size_confidence_cap(order_count: int) -> float:
    """Upper bound on confidence based on statistical sample size."""
    if order_count < 20:
        return 0.72
    if order_count < 50:
        return 0.80
    if order_count < 100:
        return 0.90
    return 0.95


def compute_state_revenue_impact(
    total_orders: int,
    rto_pct: float,
    total_revenue: float = 0,
    rto_revenue: float = 0,
    delivered_revenue: float = 0,
    shipping_cost_per_rto: float = 150,
) -> dict[str, Any]:
    """Align regional GMV, RTO-order value, and shipping waste into one consistent model."""
    total_orders = int(total_orders or 0)
    rto_pct = float(rto_pct or 0)
    total_revenue = float(total_revenue or 0)
    rto_revenue = float(rto_revenue or 0)
    delivered_revenue = float(delivered_revenue or 0)

    rto_count = round(total_orders * (rto_pct / 100)) if total_orders else 0

    if rto_revenue > 0:
        at_risk_gmv = round(rto_revenue)
    elif total_revenue > 0 and rto_pct > 0:
        at_risk_gmv = round(total_revenue * (rto_pct / 100))
    elif delivered_revenue > 0 and 0 < rto_pct < 100:
        inferred_total = delivered_revenue / (1 - (rto_pct / 100))
        at_risk_gmv = round(inferred_total - delivered_revenue)
        total_revenue = round(inferred_total)
    else:
        at_risk_gmv = 0

    if total_revenue <= 0 and delivered_revenue > 0 and at_risk_gmv > 0:
        total_revenue = round(delivered_revenue + at_risk_gmv)
    elif total_revenue <= 0 and delivered_revenue > 0:
        total_revenue = round(delivered_revenue)

    shipping_waste = round(rto_count * shipping_cost_per_rto)
    impact_percent = 0.0
    if total_revenue > 0 and at_risk_gmv > 0:
        impact_percent = min(round((at_risk_gmv / total_revenue) * 100, 1), 100.0)
    elif rto_pct > 0:
        impact_percent = min(round(rto_pct, 1), 100.0)

    return {
        "total_orders": total_orders,
        "rto_count": rto_count,
        "total_revenue": round(total_revenue),
        "delivered_revenue": round(delivered_revenue or max(total_revenue - at_risk_gmv, 0)),
        "at_risk_revenue": round(at_risk_gmv),
        "shipping_waste": shipping_waste,
        "impact_percent": impact_percent,
    }


def state_operational_framing(
    cod_pct: float,
    rto_delta: float | None,
    at_risk_gmv: float,
    state_name: str,
) -> dict[str, Any]:
    delta = abs(rto_delta or 0)
    cod_pct = float(cod_pct or 0)
    if delta <= 5:
        return {
            "financialImpactTier": "low" if at_risk_gmv < 5000 else "medium",
            "financialImpactLabel": "Low Financial Impact" if at_risk_gmv < 5000 else "Moderate Financial Impact",
            "operationalRiskLabel": "Monitor",
            "impactNarrative": (
                f"State RTO exceeds brand average by only {rto_delta:+.1f}%. "
                f"Current risk in {state_name} appears driven more by {cod_pct:.0f}% COD dependence "
                f"than a uniquely poor regional return profile."
            ),
            "actionUrgency": "monitor",
        }
    return {
        **financial_impact_metadata(at_risk_gmv),
        "actionUrgency": "act",
    }


def normalize_sku_metrics(sku: dict[str, Any]) -> dict[str, Any]:
    """Reconcile inventory, velocity, and cover into one consistent view."""
    inventory_left = max(0, int(float(sku.get("inventory_left", 0) or 0)))
    daily_velocity = max(0.0, float(sku.get("daily_velocity", 0) or 0))

    if daily_velocity > 0:
        projected_stockout_days = round(inventory_left / daily_velocity, 1)
    elif inventory_left > 0:
        projected_stockout_days = 99.0
    else:
        projected_stockout_days = 0.0

    return {
        **sku,
        "inventory_left": inventory_left,
        "daily_velocity": daily_velocity,
        "projected_stockout_days": projected_stockout_days,
    }


def compute_inventory_revenue_impact(
    daily_velocity: float,
    average_order_value: float,
    projected_stockout_days: float,
    *,
    horizon_days: int = 7,
) -> dict[str, Any]:
    """Model stockout-specific revenue at risk from a 7-day demand forecast."""
    daily_velocity = max(0.0, float(daily_velocity or 0))
    average_order_value = max(0.0, float(average_order_value or 0))
    projected = max(0.0, float(projected_stockout_days or 0))
    horizon_days = max(1, int(horizon_days))

    daily_revenue = daily_velocity * average_order_value
    forecast_revenue = round(daily_revenue * horizon_days)

    if daily_velocity <= 0:
        return {
            "daily_revenue": 0,
            "forecast_revenue": 0,
            "stockout_days_in_window": 0.0,
            "at_risk_revenue": 0,
            "impact_percent": 0.0,
            "horizon_days": horizon_days,
        }

    already_stocked_out = projected <= 0
    if already_stocked_out:
        stockout_days = float(horizon_days)
        at_risk = forecast_revenue
        impact_percent = 100.0 if forecast_revenue > 0 else 0.0
    else:
        stockout_days = round(max(0.1, horizon_days - projected), 1)
        at_risk = round(daily_revenue * stockout_days)
        impact_percent = 0.0
        if forecast_revenue > 0 and at_risk > 0:
            impact_percent = min(round((at_risk / forecast_revenue) * 100, 1), 100.0)

    return {
        "daily_revenue": round(daily_revenue),
        "forecast_revenue": forecast_revenue,
        "stockout_days_in_window": stockout_days,
        "at_risk_revenue": at_risk,
        "impact_percent": impact_percent,
        "horizon_days": horizon_days,
        "already_stocked_out": already_stocked_out,
    }


def stockout_lost_sales(
    daily_revenue: float,
    cover_days: float,
    *,
    po_eta_days: float | None = None,
    horizon_days: int = 7,
    daily_velocity: float | None = None,
    average_order_value: float | None = None,
) -> int:
    """Estimate lost sales for a stockout scenario within the forecast window."""
    if daily_velocity is not None and average_order_value is not None:
        scenario = compute_stockout_scenario(
            daily_velocity,
            average_order_value,
            cover_days,
            po_eta_days=po_eta_days,
            horizon_days=horizon_days,
            already_stocked_out=cover_days <= 0,
        )
        return scenario["lost_revenue"]

    daily_revenue = max(0.0, float(daily_revenue or 0))
    cover_days = max(0.0, float(cover_days or 0))
    horizon_days = max(1, int(horizon_days))
    if daily_revenue <= 0:
        return 0
    if po_eta_days is None:
        lost_days = horizon_days if cover_days <= 0 else max(0.0, horizon_days - cover_days)
    elif cover_days <= 0:
        lost_days = min(float(po_eta_days), float(horizon_days))
    else:
        lost_days = max(0.0, min(float(po_eta_days) - cover_days, float(horizon_days)))
    return round(daily_revenue * lost_days)


def compute_stockout_scenario(
    daily_velocity: float,
    average_order_value: float,
    cover_days: float,
    *,
    po_eta_days: float | None = None,
    horizon_days: int = 7,
    already_stocked_out: bool = False,
) -> dict[str, Any]:
    """Return lost demand days, units, and revenue for a replenishment scenario."""
    daily_velocity = max(0.0, float(daily_velocity or 0))
    average_order_value = max(0.0, float(average_order_value or 0))
    cover_days = max(0.0, float(cover_days or 0))
    horizon_days = max(1, int(horizon_days))
    daily_revenue = daily_velocity * average_order_value

    if daily_velocity <= 0 or daily_revenue <= 0:
        return {
            "daily_velocity": daily_velocity,
            "lost_days": 0.0,
            "lost_units": 0.0,
            "lost_revenue": 0,
            "detail": "Demand forecast unavailable",
        }

    if already_stocked_out or cover_days <= 0:
        if po_eta_days is None:
            lost_days = float(horizon_days)
            lead = "Already stocked out — full forecast window at risk"
        else:
            lost_days = min(float(po_eta_days), float(horizon_days))
            lead = f"Already stocked out — replenishment in {int(po_eta_days)} days"
    elif po_eta_days is None:
        lost_days = max(0.0, horizon_days - cover_days)
        lead = f"Stockout expected after ~{cover_days:g} day{'s' if cover_days != 1 else ''} of cover"
    else:
        lost_days = max(0.0, min(float(po_eta_days) - cover_days, float(horizon_days)))
        lead = f"Inbound inventory lands after ~{cover_days:g} day{'s' if cover_days != 1 else ''} of remaining cover"

    lost_units = round(lost_days * daily_velocity, 1)
    lost_revenue = round(daily_revenue * lost_days)
    detail = f"{lead}; ≈ {lost_days:g} days of lost demand ({lost_units:g} units at current velocity)"
    return {
        "daily_velocity": daily_velocity,
        "lost_days": lost_days,
        "lost_units": lost_units,
        "lost_revenue": lost_revenue,
        "detail": detail,
    }


def financial_impact_metadata(at_risk: float) -> dict[str, Any]:
    if at_risk < 2000:
        return {
            "financialImpactTier": "low",
            "financialImpactLabel": "Low Financial Impact",
            "operationalRiskLabel": "High Operational Risk",
            "impactNarrative": (
                "Low financial impact today, but may indicate a broader regional COD issue if volume increases."
            ),
        }
    if at_risk < 10000:
        return {
            "financialImpactTier": "medium",
            "financialImpactLabel": "Moderate Financial Impact",
            "operationalRiskLabel": "Elevated Operational Risk",
            "impactNarrative": "Meaningful return-shipping waste that warrants regional fulfillment review.",
        }
    return {
        "financialImpactTier": "high",
        "financialImpactLabel": "High Financial Impact",
        "operationalRiskLabel": "High Operational Risk",
        "impactNarrative": "Material margin leakage that should be addressed before scaling volume in this corridor.",
    }