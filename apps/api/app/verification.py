from typing import Any
from .rules import VERIFICATION_THRESHOLDS


def percent_change(previous: float, latest: float) -> float:
    if previous == 0:
        return 0
    return ((latest - previous) / previous) * 100


class MonitoringEngine:
    @staticmethod
    def verify_actions(previous_state: dict[str, Any] | None, latest_state: dict[str, Any], db_session=None) -> list[dict[str, Any]]:
        """
        Runs diff analysis to verify if the operator took suggested actions between snapshots.
        Checks decisions that are currently in 'monitoring' state and evaluates their
        verification_signals conditions against the new data.
        """
        if db_session is not None:
            from .models import Decision, BusinessSnapshot
            from sqlalchemy import select

            # Only check decisions already in 'monitoring' state (operator took action)
            stmt = select(Decision).where(Decision.state == "monitoring")
            monitoring_decisions = db_session.scalars(stmt).all()

            for d in monitoring_decisions:
                orig_snapshot = db_session.get(BusinessSnapshot, d.snapshot_id)
                if not orig_snapshot or not orig_snapshot.state:
                    continue

                orig_state = orig_snapshot.state
                verified = False
                verify_description = ""

                # --- Inventory reorder verification ---
                for latest_sku in latest_state.get("skus", []):
                    sku_id = latest_sku["sku_id"]
                    sku_name = latest_sku["name"]
                    if not (sku_id in d.affected_skus or sku_name in d.affected_skus or
                            (sku_name and sku_name.lower() in d.title.lower())):
                        continue

                    orig_sku = next((s for s in orig_state.get("skus", []) if s["sku_id"] == sku_id), None)
                    if not orig_sku:
                        continue

                    inventory_increase = percent_change(orig_sku["inventory_left"], latest_sku["inventory_left"])
                    stockout_improvement = latest_sku["projected_stockout_days"] - orig_sku["projected_stockout_days"]
                    rule = VERIFICATION_THRESHOLDS["inventoryReorder"]

                    if (inventory_increase >= rule["inventory_level_increase_min"] and
                            stockout_improvement >= rule["projected_stockout_days_improvement_min"]):
                        verified = True
                        verify_description = (
                            f"Verified: Inventory reorder completed (Confidence: {int(rule['confidence'] * 100)}%). "
                            f"Stock increased {inventory_increase:.0f}%, stockout days improved by {stockout_improvement:.1f}."
                        )
                        break

                if verified:
                    d.state = "successful"
                    d.timeline = [*d.timeline, {
                        "id": f"evt_verif_{d.id}",
                        "time": "Now",
                        "title": "Action Verified Successfully",
                        "description": verify_description,
                        "kind": "outcome"
                    }]
                    continue

                # --- Campaign pause / spend reduction verification ---
                for latest_campaign in latest_state.get("campaigns", []):
                    campaign_id = latest_campaign["campaign_id"]
                    campaign_name = latest_campaign["campaign_name"]
                    if not (campaign_id in d.affected_campaigns or campaign_name in d.affected_campaigns or
                            (campaign_name and campaign_name.lower() in d.title.lower())):
                        continue

                    orig_campaign = next((c for c in orig_state.get("campaigns", []) if c["campaign_id"] == campaign_id), None)
                    if not orig_campaign:
                        continue

                    spend_drop = -percent_change(orig_campaign["spend"], latest_campaign["spend"])
                    pause_rule = VERIFICATION_THRESHOLDS["codCampaignPause"]
                    spend_rule = VERIFICATION_THRESHOLDS["spendReduction"]

                    if spend_drop >= pause_rule["flagged_campaign_spend_drop_min"]:
                        verified = True
                        verify_description = (
                            f"Verified: Campaign paused (Confidence: {int(pause_rule['confidence'] * 100)}%). "
                            f"Spend dropped {spend_drop:.0f}%."
                        )
                    elif spend_drop >= spend_rule["campaign_spend_decrease_min"]:
                        verified = True
                        verify_description = (
                            f"Verified: Spend reduction implemented (Confidence: {int(spend_rule['confidence'] * 100)}%). "
                            f"Spend reduced by {spend_drop:.0f}%."
                        )

                    # --- Creative refresh verification (fatigue score proxy via CTR recovery) ---
                    if not verified and d.issue_type == "Creative fatigue":
                        prev_ctr = orig_campaign.get("ctr", 0)
                        new_ctr = latest_campaign.get("ctr", 0)
                        ctr_recovery = percent_change(prev_ctr, new_ctr)
                        refresh_rule = VERIFICATION_THRESHOLDS["creativeRefresh"]
                        if ctr_recovery >= refresh_rule["fatigueScoreDecreaseMin"] if "fatigueScoreDecreaseMin" in refresh_rule else ctr_recovery >= refresh_rule.get("fatigue_score_decrease_min", 20):
                            verified = True
                            verify_description = (
                                f"Verified: Creative refresh effective (Confidence: {int(refresh_rule['confidence'] * 100)}%). "
                                f"CTR recovered {ctr_recovery:.0f}%."
                            )

                    if verified:
                        break

                if verified:
                    d.state = "successful"
                    d.timeline = [*d.timeline, {
                        "id": f"evt_verif_{d.id}",
                        "time": "Now",
                        "title": "Action Verified Successfully",
                        "description": verify_description,
                        "kind": "outcome"
                    }]

            db_session.flush()

        if previous_state is None:
            return [{"infer": "Monitoring active - waiting for next upload to compare", "confidence": None, "baseline_mode": True}]

        inferences = []
        inventory_rule = VERIFICATION_THRESHOLDS["inventoryReorder"]
        for latest_sku in latest_state.get("skus", []):
            previous_sku = next((sku for sku in previous_state.get("skus", []) if sku["sku_id"] == latest_sku["sku_id"]), None)
            if not previous_sku:
                continue

            inventory_increase = percent_change(previous_sku["inventory_left"], latest_sku["inventory_left"])
            stockout_improvement = latest_sku["projected_stockout_days"] - previous_sku["projected_stockout_days"]

            if (inventory_increase >= inventory_rule["inventory_level_increase_min"] and
                    stockout_improvement >= inventory_rule["projected_stockout_days_improvement_min"]):
                inferences.append({
                    "infer": "Reorder likely completed",
                    "confidence": inventory_rule["confidence"],
                    "sku_id": latest_sku["sku_id"],
                    "sku_name": latest_sku["name"],
                    "action_type": "reorder"
                })

        spend_rule = VERIFICATION_THRESHOLDS["spendReduction"]
        pause_rule = VERIFICATION_THRESHOLDS["codCampaignPause"]
        for latest_campaign in latest_state.get("campaigns", []):
            previous_campaign = next((c for c in previous_state.get("campaigns", []) if c["campaign_id"] == latest_campaign["campaign_id"]), None)
            if not previous_campaign:
                continue

            spend_drop = -percent_change(previous_campaign["spend"], latest_campaign["spend"])
            if spend_drop >= pause_rule["flagged_campaign_spend_drop_min"]:
                inferences.append({
                    "infer": "Campaign paused",
                    "confidence": pause_rule["confidence"],
                    "campaign_id": latest_campaign["campaign_id"],
                    "campaign_name": latest_campaign["campaign_name"],
                    "action_type": "pause"
                })
            elif spend_drop >= spend_rule["campaign_spend_decrease_min"]:
                inferences.append({
                    "infer": "Spend reduction implemented",
                    "confidence": spend_rule["confidence"],
                    "campaign_id": latest_campaign["campaign_id"],
                    "campaign_name": latest_campaign["campaign_name"],
                    "action_type": "spend_reduction"
                })

        return inferences


def infer_execution(previous: dict[str, Any] | None, latest: dict[str, Any]) -> list[dict[str, Any]]:
    return MonitoringEngine.verify_actions(previous, latest)

