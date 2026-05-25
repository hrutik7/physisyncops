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
        If actions are verified, updates decision states in database to 'verified', 'successful', or 'unsuccessful'.
        """
        # Update matching decisions in DB to verified/successful if session is provided
        if db_session is not None:
            from .models import Decision, BusinessSnapshot
            from sqlalchemy import select
            
            stmt = select(Decision).where(Decision.state.in_(["pending", "monitoring"]))
            pending_decisions = db_session.scalars(stmt).all()
            
            for d in pending_decisions:
                orig_snapshot = db_session.get(BusinessSnapshot, d.snapshot_id)
                if not orig_snapshot or not orig_snapshot.state:
                    continue
                    
                orig_state = orig_snapshot.state
                
                # Check SKU Reorders
                for latest_sku in latest_state.get("skus", []):
                    sku_id = latest_sku["sku_id"]
                    sku_name = latest_sku["name"]
                    
                    if (sku_id in d.affected_skus or 
                        sku_name in d.affected_skus or 
                        (sku_name and sku_name.lower() in d.title.lower()) or 
                        (sku_id and sku_id.lower() in d.title.lower())):
                        
                        orig_sku = next((sku for sku in orig_state.get("skus", []) if sku["sku_id"] == sku_id), None)
                        if orig_sku:
                            inventory_increase = percent_change(orig_sku["inventory_left"], latest_sku["inventory_left"])
                            stockout_improvement = latest_sku["projected_stockout_days"] - orig_sku["projected_stockout_days"]
                            
                            inventory_rule = VERIFICATION_THRESHOLDS["inventoryReorder"]
                            if inventory_increase >= inventory_rule["inventory_level_increase_min"] and stockout_improvement >= inventory_rule["projected_stockout_days_improvement_min"]:
                                d.state = "successful"
                                d.timeline = [
                                    *d.timeline,
                                    {
                                        "id": f"evt_verif_{d.id}",
                                        "time": "Now",
                                        "title": "Action Verified Successfully",
                                        "description": f"Verified: Reorder completed (Confidence: {int(inventory_rule['confidence'] * 100)}%). SKU inventory replenished.",
                                        "kind": "outcome"
                                    }
                                ]
                                
                # Check Campaign Pause / Spend Reduction
                for latest_campaign in latest_state.get("campaigns", []):
                    campaign_id = latest_campaign["campaign_id"]
                    campaign_name = latest_campaign["campaign_name"]
                    
                    if (campaign_id in d.affected_campaigns or 
                        campaign_name in d.affected_campaigns or 
                        (campaign_name and campaign_name.lower() in d.title.lower()) or 
                        (campaign_id and campaign_id.lower() in d.title.lower())):
                        
                        orig_campaign = next((c for c in orig_state.get("campaigns", []) if c["campaign_id"] == campaign_id), None)
                        if orig_campaign:
                            spend_drop = -percent_change(orig_campaign["spend"], latest_campaign["spend"])
                            
                            spend_rule = VERIFICATION_THRESHOLDS["spendReduction"]
                            pause_rule = VERIFICATION_THRESHOLDS["codCampaignPause"]
                            
                            if spend_drop >= pause_rule["flagged_campaign_spend_drop_min"]:
                                d.state = "successful"
                                d.timeline = [
                                    *d.timeline,
                                    {
                                        "id": f"evt_verif_{d.id}",
                                        "time": "Now",
                                        "title": "Action Verified Successfully",
                                        "description": f"Verified: Campaign paused (Confidence: {int(pause_rule['confidence'] * 100)}%). Spend reduced.",
                                        "kind": "outcome"
                                    }
                                ]
                            elif spend_drop >= spend_rule["campaign_spend_decrease_min"]:
                                d.state = "successful"
                                d.timeline = [
                                    *d.timeline,
                                    {
                                        "id": f"evt_verif_{d.id}",
                                        "time": "Now",
                                        "title": "Action Verified Successfully",
                                        "description": f"Verified: Spend reduction implemented (Confidence: {int(spend_rule['confidence'] * 100)}%). Spend reduced.",
                                        "kind": "outcome"
                                    }
                                ]
            db_session.flush()

        if previous_state is None:
            return [
                {
                    "infer": "Monitoring active - waiting for next upload to compare",
                    "confidence": None,
                    "baseline_mode": True,
                }
            ]

        inferences = []
        inventory_rule = VERIFICATION_THRESHOLDS["inventoryReorder"]
        for latest_sku in latest_state.get("skus", []):
            previous_sku = next((sku for sku in previous_state.get("skus", []) if sku["sku_id"] == latest_sku["sku_id"]), None)
            if not previous_sku:
                continue
            
            inventory_increase = percent_change(previous_sku["inventory_left"], latest_sku["inventory_left"])
            stockout_improvement = latest_sku["projected_stockout_days"] - previous_sku["projected_stockout_days"]
            
            if inventory_increase >= inventory_rule["inventory_level_increase_min"] and stockout_improvement >= inventory_rule["projected_stockout_days_improvement_min"]:
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
            previous_campaign = next((campaign for campaign in previous_state.get("campaigns", []) if campaign["campaign_id"] == latest_campaign["campaign_id"]), None)
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
    # Backward compatibility wrapper
    return MonitoringEngine.verify_actions(previous, latest)
