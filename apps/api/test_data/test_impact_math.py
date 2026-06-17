import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.impact_math import (
    compute_campaign_revenue_impact,
    compute_inventory_revenue_impact,
    compute_state_revenue_impact,
    compute_stockout_scenario,
    normalize_sku_metrics,
    recovery_from_gap,
)
from app.decision_v2 import (
    NEW_LAUNCH_EXPLANATION,
    build_auto_resolution_criteria,
    build_confidence_drivers,
    build_impact_context,
    build_inventory_display_overrides,
    build_metric_verification_status,
    build_new_launch_display_overrides,
    build_remedies,
    build_state_display_overrides,
    build_stockout_scenarios,
    build_trigger_reason,
    effective_confidence_score,
)


def test_new_launch_revenue_gap_matches_unigo_example():
    metrics = compute_campaign_revenue_impact(24291, 0.9, 0.613)
    assert metrics["placed_revenue"] == 21862
    assert metrics["delivered_revenue"] == 14890
    assert metrics["revenue_gap"] == 6972
    assert metrics["impact_percent"] == 31.9


def test_recovery_is_gap_based_not_spend_based():
    gap = 6972
    assert recovery_from_gap(gap, 0.29) == 2022
    assert recovery_from_gap(gap, 0.5) == 3486


def test_build_impact_context_rejects_spend_as_at_risk():
    class FakeDecision:
        business_impact = 24291
        affected_campaigns = ["Test Campaign"]
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"

    class Snapshot:
        state = {
            "campaigns": [
                {
                    "campaign_name": "Test Campaign",
                    "spend": 24291,
                    "roas_on_placed_orders": 0.9,
                    "roas_on_delivered_orders": 0.613,
                }
            ]
        }

    context = build_impact_context(FakeDecision(), Snapshot())
    assert context["atRiskRevenue"] == 6972
    assert context["impactPercent"] == 31.9
    assert context["totalRevenue"] == 21862


def test_effective_confidence_caps_estimated_launch():
    class FakeDecision:
        confidence_score = 0.75
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "brand_rto_rate": 31.89,
            "rto_data_present": True,
            "campaigns": [
                {
                    "campaign_name": "Test Campaign",
                    "spend": 24291,
                    "roas_on_placed_orders": 0.9,
                    "roas_on_delivered_orders": 0.613,
                    "frequency": 1.22,
                }
            ],
        }

    assert effective_confidence_score(FakeDecision(), Snapshot()) <= 0.65


def test_launch_trigger_reason_includes_benchmark_metrics():
    class FakeDecision:
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "campaigns": [
                {
                    "campaign_name": "Test Campaign",
                    "spend": 24291,
                    "roas_on_placed_orders": 0.9,
                    "roas_on_delivered_orders": 0.613,
                    "frequency": 1.22,
                }
            ],
        }

    trigger = build_trigger_reason(FakeDecision(), Snapshot())
    assert trigger["headline"] == "Why It Was Selected"
    labels = [metric["label"] for metric in trigger["metrics"]]
    assert "Benchmark" in labels
    assert "Frequency" in labels
    freq_metric = next(metric for metric in trigger["metrics"] if metric["label"] == "Frequency")
    assert freq_metric["value"] == "1.22"


def test_launch_confidence_drivers_include_learning_phase():
    class FakeDecision:
        confidence_score = 0.65
        issue_type = "Creative fatigue"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "brand_rto_rate": 31.89,
            "rto_data_present": True,
            "campaigns": [
                {
                    "campaign_name": "Test Campaign",
                    "spend": 24291,
                    "roas_on_placed_orders": 0.9,
                    "roas_on_delivered_orders": 0.613,
                    "frequency": 1.22,
                }
            ],
        }

    drivers = build_confidence_drivers(FakeDecision(), Snapshot())
    labels = [driver["label"] for driver in drivers]
    assert "Campaign remains in learning phase" in labels
    assert "Delivered metrics estimated using brand RTO fallback" in labels
    assert not any("CTR baseline" in label for label in labels)


def test_launch_metric_verification_matches_audience_audit_shape():
    class FakeDecision:
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "brand_rto_rate": 31.89,
            "rto_data_present": True,
            "campaigns": [
                {
                    "campaign_name": "Test Campaign",
                    "spend": 24291,
                    "roas_on_placed_orders": 0.9,
                    "roas_on_delivered_orders": 0.613,
                    "frequency": 1.22,
                }
            ],
        }

    status = build_metric_verification_status(FakeDecision(), Snapshot())
    observed = [item["label"] for item in status["observed"]]
    estimated = [item["label"] for item in status["estimated"]]
    assert "Spend" in observed
    assert "Placed Revenue" in observed
    assert "Brand RTO" in observed
    assert "Delivered Revenue" in estimated
    assert "Revenue Gap" in estimated


def test_launch_display_override_softens_explanation():
    class FakeDecision:
        explanation = "Newly launched ad set exhibits extremely low ROAS with low frequency exposure."
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    overrides = build_new_launch_display_overrides(FakeDecision(), None)
    assert overrides["displayExplanation"] == NEW_LAUNCH_EXPLANATION
    assert "extremely" not in overrides["displayExplanation"].lower()


def test_normalize_sku_metrics_reconciles_cover():
    sku = normalize_sku_metrics({"name": "Alpha", "inventory_left": 1, "daily_velocity": 1, "projected_stockout_days": 0})
    assert sku["inventory_left"] == 1
    assert sku["projected_stockout_days"] == 1.0


def test_inventory_revenue_impact_uses_forecast_not_rto_multiplier():
    metrics = compute_inventory_revenue_impact(1, 500, 1.0)
    assert metrics["forecast_revenue"] == 3500
    assert metrics["at_risk_revenue"] == 3000
    assert metrics["impact_percent"] == 85.7


def test_inventory_already_stocked_out_is_full_forecast_at_100_percent():
    metrics = compute_inventory_revenue_impact(1, 1449, 0)
    assert metrics["forecast_revenue"] == 10143
    assert metrics["at_risk_revenue"] == 10143
    assert metrics["impact_percent"] == 100.0
    assert metrics["already_stocked_out"] is True


def test_inventory_confidence_caps_without_inbound_visibility():
    class FakeDecision:
        confidence_score = 0.82
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Critical Inventory Cliff: Alpha under 1.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 1,
                    "daily_velocity": 1,
                    "projected_stockout_days": 0,
                    "spend_growth_percent": 0,
                    "average_order_value": 500,
                }
            ]
        }

    assert effective_confidence_score(FakeDecision(), Snapshot()) <= 0.72
    drivers = build_confidence_drivers(FakeDecision(), Snapshot())
    labels = [driver["label"] for driver in drivers]
    assert "Open purchase orders unavailable" in labels
    assert "No verified ad spend acceleration" in labels


def test_inventory_display_override_removes_scaling_claim():
    class FakeDecision:
        explanation = "Rapid sales acceleration driven by scaling ad campaigns has depleted cover."
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Critical Inventory Cliff: Alpha under 1.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        business_impact = 3000
        impact_label = "legacy"
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 1,
                    "daily_velocity": 1,
                    "projected_stockout_days": 0,
                    "spend_growth_percent": 0,
                    "average_order_value": 500,
                }
            ]
        }

    overrides = build_inventory_display_overrides(FakeDecision(), Snapshot())
    assert "scaling ad campaigns" not in overrides["displayExplanation"].lower()
    assert "approximately 1.0 day" in overrides["displayExplanation"]


def test_inventory_trigger_reason_matches_normalized_metrics():
    class FakeDecision:
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Critical Inventory Cliff: Alpha under 1.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        state = "pending"
        cross_system_signals = [
            "Inventory left: 0 units",
            "Daily velocity: 1 units/day",
            "Inventory cover: 0 days",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 1,
                    "daily_velocity": 1,
                    "projected_stockout_days": 0,
                    "spend_growth_percent": 0,
                }
            ]
        }

    trigger = build_trigger_reason(FakeDecision(), Snapshot())
    inventory_metric = next(metric for metric in trigger["metrics"] if metric["label"] == "Inventory left")
    cover_metric = next(metric for metric in trigger["metrics"] if metric["label"] == "Inventory cover")
    assert inventory_metric["value"] == "1 units"
    assert cover_metric["value"] == "1.0 days"


def test_inventory_remedies_rank_restock_first():
    class FakeDecision:
        id = "decision_inventory_alpha"
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Critical Inventory Cliff: Alpha under 1.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        business_impact = 3000
        recommendation = "Restock"
        recommended_actions = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 1,
                    "daily_velocity": 1,
                    "projected_stockout_days": 1.0,
                    "average_order_value": 500,
                }
            ]
        }

    remedies = build_remedies(FakeDecision(), Snapshot())
    assert remedies[0]["rank"] == "primary"
    assert "restock" in remedies[0]["label"].lower()
    assert remedies[0]["expectedRiskReduction"] > remedies[1]["expectedRiskReduction"]
    assert remedies[0]["expectedRiskReduction"] > remedies[2]["expectedRiskReduction"]


def test_inventory_impact_and_scenarios_use_same_numbers():
    class FakeDecision:
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Active Stockout Alert: Alpha under 0.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        business_impact = 10143
        state = "pending"
        cross_system_signals = ["SKU-level AOV: Rs 1,449.00"]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 0,
                    "daily_velocity": 1,
                    "projected_stockout_days": 0,
                    "average_order_value": 0,
                }
            ]
        }

    context = build_impact_context(FakeDecision(), Snapshot())
    scenarios = build_stockout_scenarios(FakeDecision(), Snapshot())
    assert context["totalRevenue"] == 10143
    assert context["atRiskRevenue"] == 10143
    assert context["impactPercent"] == 100.0
    assert scenarios["scenarios"][0]["estimatedLostSales"] == 10143
    assert scenarios["scenarios"][2]["estimatedLostSales"] == 10143
    assert "days of lost demand" in scenarios["scenarios"][1]["detail"]


def test_inventory_metric_verification_has_observed_and_estimated_sections():
    class FakeDecision:
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Active Stockout Alert: Alpha under 0.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 0,
                    "daily_velocity": 1,
                    "projected_stockout_days": 0,
                    "average_order_value": 1449,
                }
            ]
        }

    status = build_metric_verification_status(FakeDecision(), Snapshot())
    observed = [item["label"] for item in status["observed"]]
    estimated = [item["label"] for item in status["estimated"]]
    assert "Inventory" in observed
    assert "Velocity" in observed
    assert "Revenue forecast" in estimated
    assert "Lost sales forecast" in estimated
    assert "Restock scenarios" in estimated


def test_stockout_scenarios_generated_for_inventory():
    class FakeDecision:
        issue_type = "Inventory pressure"
        rule = "projected_stockout_days <= 3.0"
        title = "Critical Inventory Cliff: Alpha under 1.0 days of cover"
        affected_campaigns = []
        affected_skus = ["Alpha"]
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "skus": [
                {
                    "name": "Alpha",
                    "inventory_left": 1,
                    "daily_velocity": 1,
                    "projected_stockout_days": 1.0,
                    "average_order_value": 500,
                }
            ]
        }

    scenarios = build_stockout_scenarios(FakeDecision(), Snapshot())
    assert scenarios["headline"] == "Stockout Scenario Analysis"
    assert len(scenarios["scenarios"]) == 3
    scenario = compute_stockout_scenario(1, 500, 1.0, po_eta_days=3)
    assert scenario["lost_revenue"] == 1000
    assert "days of lost demand" in scenario["detail"]


def test_launch_auto_resolution_criteria():
    class FakeDecision:
        issue_type = "Launch validation"
        rule = "roas < 1.5 AND frequency <= 1.5 AND daily_spend > 0"
        title = "New Launch Risk on Test Campaign"
        affected_campaigns = ["Test Campaign"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    criteria = build_auto_resolution_criteria(FakeDecision(), None)
    assert criteria["headline"] == "Auto Resolution Criteria"
    assert len(criteria["criteria"]) == 3
    assert "ROAS exceeds 1.5x" in criteria["criteria"][0]


def test_state_rto_confidence_caps_small_sample():
    class FakeDecision:
        confidence_score = 0.92
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "State Profitability Leakage: High RTO in West Bengal"
        affected_campaigns = []
        affected_skus = []
        state = "pending"
        cross_system_signals = [
            "State: West Bengal",
            "Total orders: 12",
            "COD mix: 100%",
            "RTO rate: 33.33%",
            "Brand average RTO: 18.2%",
            "State RTO delta: +15.1%",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "brand_rto_rate": 18.2,
            "state_profitability": [
                {
                    "state": "West Bengal",
                    "total_orders": 12,
                    "cod_pct": 100,
                    "rto_pct": 33.33,
                    "delivered_revenue": 1890,
                }
            ],
        }

    assert effective_confidence_score(FakeDecision(), Snapshot()) <= 0.72


def test_state_rto_drivers_exclude_meta():
    class FakeDecision:
        confidence_score = 0.72
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "State Profitability Leakage: High RTO in West Bengal"
        affected_campaigns = []
        affected_skus = []
        state = "pending"
        cross_system_signals = ["State: West Bengal", "Total orders: 12"]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "brand_rto_rate": 18.2,
            "state_profitability": [{"state": "West Bengal", "total_orders": 12, "cod_pct": 100, "rto_pct": 33.33}],
        }

    labels = [driver["label"] for driver in build_confidence_drivers(FakeDecision(), Snapshot())]
    assert "Campaign spend verified from Meta" not in labels
    assert "Only 12 orders available" in labels


def test_state_rto_trigger_includes_benchmark():
    class FakeDecision:
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "State Profitability Leakage: High RTO in West Bengal"
        affected_campaigns = []
        affected_skus = []
        state = "pending"
        cross_system_signals = [
            "State: West Bengal",
            "Total orders: 12",
            "COD mix: 100%",
            "RTO rate: 33.33%",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "brand_rto_rate": 18.2,
            "state_profitability": [
                {"state": "West Bengal", "total_orders": 12, "cod_pct": 100, "rto_pct": 33.33, "delivered_revenue": 1890}
            ],
        }

    trigger = build_trigger_reason(FakeDecision(), Snapshot())
    labels = [metric["label"] for metric in trigger["metrics"]]
    assert trigger["headline"] == "Why It Triggered"
    assert "Brand Average RTO" in labels
    assert "Difference" in labels


def test_state_revenue_math_aligns_gmv_with_rto_rate():
    metrics = compute_state_revenue_impact(
        12,
        33.33,
        total_revenue=11994,
        rto_revenue=3998,
        delivered_revenue=7996,
    )
    assert metrics["total_revenue"] == 11994
    assert metrics["at_risk_revenue"] == 3998
    assert metrics["shipping_waste"] == 600
    assert metrics["impact_percent"] == 33.3


def test_state_impact_context_marks_monitor_when_delta_small():
    class FakeDecision:
        business_impact = 600
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "Regional COD Risk: West Bengal"
        affected_campaigns = []
        state = "pending"
        cross_system_signals = [
            "State: West Bengal",
            "Total orders: 12",
            "COD mix: 100%",
            "RTO rate: 33.33%",
            "Brand average RTO: 31.89%",
            "State RTO delta: +1.4%",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "brand_rto_rate": 31.89,
            "state_profitability": [
                {
                    "state": "West Bengal",
                    "total_orders": 12,
                    "cod_pct": 100,
                    "rto_pct": 33.33,
                    "total_revenue": 11994,
                    "rto_revenue": 3998,
                    "delivered_revenue": 7996,
                }
            ],
        }

    context = build_impact_context(FakeDecision(), Snapshot())
    assert context["operationalRiskLabel"] == "Monitor"
    assert context["atRiskRevenue"] == 3998
    assert context["totalRevenue"] == 11994
    assert context["shippingWaste"] == 600
    assert context["impactPercent"] == 33.3
    assert context["actionUrgency"] == "monitor"


def test_legacy_state_decision_recomputes_gmv_not_shipping_waste():
    class FakeDecision:
        business_impact = 600
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "State Profitability Leakage: High RTO in West Bengal"
        affected_campaigns = []
        state = "pending"
        explanation = "Old aggressive explanation"
        recommendation = "Old aggressive recommendation"
        impact_label = "Rs 600 return shipping waste in West Bengal"
        cross_system_signals = [
            "State: West Bengal",
            "Total orders: 12",
            "COD mix: 100%",
            "RTO rate: 33.33%",
            "Brand average RTO: 31.89%",
            "State RTO delta: +1.4%",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "brand_rto_rate": 31.89,
            "state_profitability": [
                {
                    "state": "West Bengal",
                    "total_orders": 12,
                    "cod_pct": 100,
                    "rto_pct": 33.33,
                    "delivered_revenue": 7996,
                }
            ],
        }

    context = build_impact_context(FakeDecision(), Snapshot())
    overrides = build_state_display_overrides(FakeDecision(), Snapshot())
    assert context["atRiskRevenue"] > 3000
    assert context["impactPercent"] > 30
    assert context["shippingWaste"] == 600
    assert overrides["displayTitle"] == "Regional COD Risk: West Bengal"
    assert "COD concentration" in overrides["displayExplanation"]


def test_state_revenue_reconciles_shipping_waste_mislabeled_as_at_risk():
    class FakeDecision:
        business_impact = 600
        issue_type = "State RTO leakage"
        rule = "state_orders >= 10 AND state_rto_rate >= 30%"
        title = "State Profitability Leakage: High RTO in West Bengal"
        affected_campaigns = []
        state = "pending"
        cross_system_signals = [
            "State: West Bengal",
            "Total orders: 12",
            "COD mix: 100%",
            "RTO rate: 33.33%",
            "Brand average RTO: 31.89%",
            "State RTO delta: +1.4%",
        ]
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        state = {
            "brand_rto_rate": 31.89,
            "state_profitability": [
                {
                    "state": "West Bengal",
                    "total_orders": 12,
                    "cod_pct": 100,
                    "rto_pct": 33.33,
                    "total_revenue": 11994,
                    "rto_revenue": 0,
                    "delivered_revenue": 11994,
                }
            ],
        }

    context = build_impact_context(FakeDecision(), Snapshot())
    assert context["atRiskRevenue"] > 3000
    assert context["shippingWaste"] == 600
    assert context["impactPercent"] > 30


def test_audience_audit_confidence_caps_with_brand_rto_fallback():
    class FakeDecision:
        confidence_score = 0.89
        issue_type = "Marketing pressure"
        rule = "spend >= 50000 AND delivered_roas <= 3.0 AND placed_roas >= 1.5"
        title = "Strategic Audit: High-spend Audience Testing campaign Alpha"
        affected_campaigns = ["Alpha"]
        affected_skus = []
        state = "pending"
        cross_system_signals = []
        created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    class Snapshot:
        snapshot_version = 1
        state = {
            "brand_rto_rate": 31.89,
            "rto_data_present": True,
            "campaigns": [
                {
                    "campaign_name": "Alpha",
                    "spend": 248724.9,
                    "roas_on_placed_orders": 1.64,
                    "roas_on_delivered_orders": 1.12,
                    "rto_rate_attributed": 31.89,
                    "rto_count_attributed": 0,
                    "delivered_orders_attributed": 0,
                }
            ],
        }

    assert effective_confidence_score(FakeDecision(), Snapshot()) <= 0.78
    labels = [driver["label"] for driver in build_confidence_drivers(FakeDecision(), Snapshot())]
    assert "Campaign spend verified from Meta" in labels
    assert "Delivered revenue estimated from fallback model" in labels
    assert "Source telemetry available" not in labels
    metric_status = build_metric_verification_status(FakeDecision(), Snapshot())
    assert metric_status is not None
    assert any(item["label"] == "Spend" for item in metric_status["observed"])
    assert any(item["label"] == "Campaign RTO" for item in metric_status["estimated"])


if __name__ == "__main__":
    test_new_launch_revenue_gap_matches_unigo_example()
    test_recovery_is_gap_based_not_spend_based()
    test_build_impact_context_rejects_spend_as_at_risk()
    test_effective_confidence_caps_estimated_launch()
    test_launch_trigger_reason_includes_benchmark_metrics()
    test_launch_confidence_drivers_include_learning_phase()
    test_launch_metric_verification_matches_audience_audit_shape()
    test_launch_display_override_softens_explanation()
    test_launch_auto_resolution_criteria()
    test_normalize_sku_metrics_reconciles_cover()
    test_inventory_revenue_impact_uses_forecast_not_rto_multiplier()
    test_inventory_already_stocked_out_is_full_forecast_at_100_percent()
    test_inventory_impact_and_scenarios_use_same_numbers()
    test_inventory_metric_verification_has_observed_and_estimated_sections()
    test_inventory_confidence_caps_without_inbound_visibility()
    test_inventory_display_override_removes_scaling_claim()
    test_inventory_trigger_reason_matches_normalized_metrics()
    test_inventory_remedies_rank_restock_first()
    test_stockout_scenarios_generated_for_inventory()
    test_state_rto_confidence_caps_small_sample()
    test_state_rto_drivers_exclude_meta()
    test_state_rto_trigger_includes_benchmark()
    test_state_revenue_math_aligns_gmv_with_rto_rate()
    test_state_impact_context_marks_monitor_when_delta_small()
    test_legacy_state_decision_recomputes_gmv_not_shipping_waste()
    test_state_revenue_reconciles_shipping_waste_mislabeled_as_at_risk()
    test_audience_audit_confidence_caps_with_brand_rto_fallback()
    print("✅ impact math tests passed")