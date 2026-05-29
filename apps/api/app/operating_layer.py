from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .models import (
    BrandGoal,
    BusinessSnapshot,
    ConnectorEvent,
    Decision,
    Intervention,
    OntologyEdge,
    OntologyNode,
    UnitEconomics,
    VerificationScorecard,
)


DEFAULT_GOALS = [
    ("margin", 1, {"metric": "contribution_margin_after_rto", "direction": "increase"}),
    ("growth", 2, {"metric": "delivered_revenue", "direction": "increase"}),
    ("inventory_protection", 3, {"metric": "projected_stockout_days", "direction": "increase"}),
    ("retention", 4, {"metric": "repeat_rate", "direction": "increase"}),
]


def ensure_default_goals(db: Session, brand_id: str) -> None:
    if db.query(BrandGoal).filter(BrandGoal.brand_id == brand_id).first():
        return
    for goal_type, priority, target in DEFAULT_GOALS:
        db.add(BrandGoal(brand_id=brand_id, goal_type=goal_type, priority=priority, target=target))


def upsert_unit_economics_from_state(db: Session, brand_id: str, state: dict[str, Any]) -> None:
    aov = state.get("average_order_value") or state.get("aov")
    for sku in state.get("skus", []):
        sku_id = sku.get("sku_id")
        if not sku_id:
            continue
        econ = (
            db.query(UnitEconomics)
            .filter(UnitEconomics.brand_id == brand_id, UnitEconomics.sku_id == sku_id)
            .first()
        )
        margin = float(sku.get("contribution_margin_after_rto", 35))
        if econ is None:
            econ = UnitEconomics(brand_id=brand_id, sku_id=sku_id)
            db.add(econ)
        econ.gross_margin_percent = margin
        econ.average_order_value = float(aov) if aov else econ.average_order_value
        econ.updated_at = datetime.utcnow()


def persist_connector_events(db: Session, brand_id: str, snapshot: BusinessSnapshot, state: dict[str, Any]) -> None:
    for campaign in state.get("campaigns", []):
        db.add(
            ConnectorEvent(
                brand_id=brand_id,
                snapshot_id=snapshot.id,
                source=snapshot.upload_source,
                event_type="campaign_metric_snapshot",
                entity_key=campaign.get("campaign_id") or campaign.get("campaign_name"),
                payload=campaign,
            )
        )
    for sku in state.get("skus", []):
        db.add(
            ConnectorEvent(
                brand_id=brand_id,
                snapshot_id=snapshot.id,
                source=snapshot.upload_source,
                event_type="inventory_metric_snapshot",
                entity_key=sku.get("sku_id") or sku.get("name"),
                payload=sku,
            )
        )
    for segment in state.get("customer_segments", []):
        db.add(
            ConnectorEvent(
                brand_id=brand_id,
                snapshot_id=snapshot.id,
                source=snapshot.upload_source,
                event_type="customer_segment_snapshot",
                entity_key=segment.get("segment_id") or segment.get("name"),
                payload=segment,
            )
        )


def _node_key(label: str) -> str:
    return label.strip().lower().replace(" ", "_")


def persist_ontology(db: Session, brand_id: str, decision: Decision) -> None:
    for edge in decision.relationship_edges or []:
        from_label = edge.get("from", "")
        to_label = edge.get("to", "")
        if not from_label or not to_label:
            continue
        for label in [from_label, to_label]:
            key = _node_key(label)
            node = (
                db.query(OntologyNode)
                .filter(OntologyNode.brand_id == brand_id, OntologyNode.entity_key == key)
                .first()
            )
            if node is None:
                db.add(
                    OntologyNode(
                        brand_id=brand_id,
                        entity_type="derived",
                        entity_key=key,
                        label=label,
                        properties={"source": "decision_relationship"},
                    )
                )
        db.add(
            OntologyEdge(
                brand_id=brand_id,
                from_key=_node_key(from_label),
                to_key=_node_key(to_label),
                label=edge.get("label", "related"),
                strength=edge.get("strength", "medium"),
                source_decision_id=decision.id,
            )
        )


def action_type_for_decision(decision: Decision) -> str:
    text = f"{decision.issue_type} {decision.recommendation}".lower()
    if "reorder" in text:
        return "inventory_reorder"
    if "pause" in text:
        return "campaign_pause"
    if "creative" in text or "refresh" in text:
        return "creative_refresh"
    if "scale" in text or "increase budget" in text:
        return "budget_scale"
    if "prepaid" in text or "cod" in text:
        return "payment_mix_shift"
    return "operator_action"


def ensure_intervention(db: Session, brand_id: str, decision: Decision, status: str = "recommended") -> Intervention:
    intervention = db.query(Intervention).filter(Intervention.decision_id == decision.id).first()
    if intervention is None:
        intervention = Intervention(
            decision_id=decision.id,
            brand_id=brand_id,
            action_type=action_type_for_decision(decision),
            expected_effect={
                "impact_label": decision.impact_label,
                "business_impact": decision.business_impact,
                "recommendation": decision.recommendation,
            },
            verification_metric={
                "rules": decision.verification_signals,
                "confidence": decision.confidence_score,
            },
        )
        db.add(intervention)
        db.flush()
    else:
        intervention.status = status
        intervention.updated_at = datetime.utcnow()
    return intervention


def ensure_scorecard(db: Session, brand_id: str, decision: Decision, intervention: Intervention, status: str = "pending", summary: str | None = None) -> None:
    scorecard = db.query(VerificationScorecard).filter(VerificationScorecard.intervention_id == intervention.id).first()
    if scorecard is None:
        scorecard = VerificationScorecard(
            intervention_id=intervention.id,
            decision_id=decision.id,
            brand_id=brand_id,
        )
        db.add(scorecard)
    scorecard.status = status
    scorecard.score = 1.0 if status == "successful" else 0.0
    scorecard.summary = summary or ("Awaiting next connector event for verification." if status == "pending" else None)
    scorecard.metrics = decision.verification_signals or []


def why_analysis(decision: Decision, snapshot: BusinessSnapshot | None = None) -> dict[str, Any]:
    source_fields = []
    for signal in decision.cross_system_signals or []:
        source_fields.append({"source": "derived_snapshot", "field": signal, "value": signal})

    return {
        "formula": decision.rule,
        "sourceFields": source_fields,
        "confidenceFactors": [decision.confidence_explanation] if decision.confidence_explanation else [],
        "goalAlignment": infer_goal_alignment(decision),
        "snapshotId": snapshot.id if snapshot else decision.snapshot_id,
    }


def infer_goal_alignment(decision: Decision) -> str:
    issue = decision.issue_type.lower()
    if "margin" in issue or "rto" in issue:
        return "margin"
    if "inventory" in issue:
        return "inventory_protection"
    if "scaling" in issue:
        return "growth"
    if "creative" in issue:
        return "growth"
    return "retention"
