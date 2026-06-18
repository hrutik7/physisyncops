import json
import os
import re
import shutil
import uuid
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .db import Base, engine, get_db
from .demo_data import DEMO_STATE
from .mapping import suggest_mappings
from .models import (
    Brand,
    BrandGoal,
    BusinessSnapshot,
    ConnectorEvent,
    Decision,
    Intervention,
    MappingTemplate,
    OntologyEdge,
    OntologyNode,
    UnitEconomics,
    VerificationScorecard,
)
from .decision_v2 import enrich_decision_v2
from .operating_layer import (
    ensure_default_goals,
    ensure_intervention,
    ensure_scorecard,
    persist_connector_events,
    persist_ontology,
    upsert_unit_economics_from_state,
    why_analysis,
    carry_forward_active_decisions,
)
from .rules import detect_signals, SignalDetectionEngine
from .verification import infer_execution, MonitoringEngine
from .schemas import ConfirmMappingRequest, DecisionStateRequest, SnapshotResponse, UploadPreviewResponse
from .llm import LLMEnrichmentService

app = FastAPI(title="Opentra API", version="0.1.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def display_name_from_brand_id(brand_id: str) -> str:
    clean = re.sub(r"^brand[_-]?", "", brand_id).replace("_", " ").replace("-", " ").strip()
    return clean.title() if clean else "Uploaded Brand"


def normalize_sheet_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo")
def demo() -> dict:
    signals = [signal.__dict__ for signal in detect_signals(DEMO_STATE)]
    return {"state": DEMO_STATE, "signals": signals, "mode": "baseline"}


@app.get("/state")
def get_state(brand_id: str, db: Session = Depends(get_db)):
    # Query latest snapshot
    snapshot = db.scalars(
        select(BusinessSnapshot)
        .where(BusinessSnapshot.brand_id == brand_id)
        .order_by(BusinessSnapshot.snapshot_version.desc())
    ).first()
    
    if snapshot is None:
        brand = db.get(Brand, brand_id)
        return {
            "brandName": brand.name if brand else display_name_from_brand_id(brand_id),
            "snapshots": [],
            "skus": [],
            "campaigns": [],
            "customerSegments": [],
            "creatives": [],
            "decisions": [],
            "mappingSuggestions": []
        }
        
    all_snapshots = db.scalars(
        select(BusinessSnapshot)
        .where(BusinessSnapshot.brand_id == brand_id)
        .order_by(BusinessSnapshot.snapshot_version.desc())
    ).all()
    
    all_decisions = db.scalars(
        select(Decision)
        .where(Decision.snapshot_id == snapshot.id)
        .order_by(Decision.created_at.desc())
    ).all()
    
    # Deduplicate decisions by title or rule, keeping the latest version of each
    seen_keys = set()
    decisions = []
    for d in all_decisions:
        key = d.rule or d.title
        if key in seen_keys:
            continue
        seen_keys.add(key)
        decisions.append(d)
        
    dec_list = []
    for d in decisions:
        intervention = db.query(Intervention).filter_by(decision_id=d.id).first()
        scorecard = None
        if intervention:
            scorecard = db.query(VerificationScorecard).filter_by(intervention_id=intervention.id).first()
        enrichment = enrich_decision_v2(d, snapshot)
        effective_confidence = enrichment.pop("effectiveConfidenceScore", d.confidence_score)
        display_title = enrichment.pop("displayTitle", None)
        display_explanation = enrichment.pop("displayExplanation", None)
        display_recommendation = enrichment.pop("displayRecommendation", None)
        display_severity = enrichment.pop("displaySeverity", None)
        effective_business_impact = enrichment.pop("effectiveBusinessImpact", None)
        effective_impact_label = enrichment.pop("effectiveImpactLabel", None)
        dec_list.append({
            "id": d.id,
            "title": display_title or d.title,
            "signalType": d.issue_type.replace(" ", ""),
            "issueType": d.issue_type,
            "severity": display_severity or d.severity,
            "confidenceScore": effective_confidence,
            "businessImpact": effective_business_impact if effective_business_impact is not None else d.business_impact,
            "impactLabel": effective_impact_label or d.impact_label or f"Rs {d.business_impact} impact",
            "explanation": display_explanation or d.explanation,
            "rule": d.rule,
            "recommendation": display_recommendation or d.recommendation,
            "affectedCampaigns": d.affected_campaigns,
            "affectedSkus": d.affected_skus,
            "timestamp": d.created_at.strftime("%I:%M %p"),
            "state": d.state,
            "crossSystemSignals": d.cross_system_signals,
            "riskProjection": d.risk_projection,
            "recommendedActions": d.recommended_actions,
            "verificationSignals": d.verification_signals,
            "timeline": d.timeline,
            "confidenceExplanation": d.confidence_explanation or "",
            "relationshipEdges": d.relationship_edges,
            "whyAnalysis": why_analysis(d, snapshot),
            "intervention": {
                "id": intervention.id,
                "actionType": intervention.action_type,
                "status": intervention.status,
                "expectedEffect": intervention.expected_effect,
                "verificationMetric": intervention.verification_metric,
                "outcome": intervention.outcome,
            } if intervention else None,
            "verificationScorecard": {
                "score": scorecard.score,
                "status": scorecard.status,
                "metrics": scorecard.metrics,
                "summary": scorecard.summary,
            } if scorecard else None,
            "selectedRemedyId": (intervention.expected_effect or {}).get("selectedRemedyId") if intervention else None,
            **enrichment,
        })
        
    for d in dec_list:
        rule_str = d.get("rule", "") or ""
        title_str = d.get("title", "") or ""
        if "placed_roas >= 3.5 AND delivered_roas <= 2.2" in rule_str or "Margin Trap" in title_str:
            d["signalType"] = "MarginTrap"
        elif "campaign contains combo" in rule_str or "AOV Dilution" in title_str:
            d["signalType"] = "AOVDilution"
        elif "roas < 1.5 AND frequency <= 1.5" in rule_str or "New Launch" in title_str:
            d["signalType"] = "NewLaunchRisk"
        elif (
            "state_orders" in rule_str
            or "State Profitability" in title_str
            or "Regional COD Risk" in title_str
            or d["issueType"] == "State RTO leakage"
        ):
            d["signalType"] = "StateRTOLeakage"
        elif "spend >= 50000" in rule_str or "Strategic Audit" in title_str or d["issueType"] == "Marketing pressure":
            d["signalType"] = "AudienceAudit"
        elif d["issueType"] == "Campaign-level RTO spike":
            d["signalType"] = "CampaignRTOSpike"
        elif d["issueType"] == "Inventory pressure":
            d["signalType"] = "InventoryRisk"
        elif d["issueType"] == "Creative fatigue":
            d["signalType"] = "CreativeFatigue"
        elif d["issueType"] == "Margin leakage":
            d["signalType"] = "MarginLeakage"
        elif d["issueType"] == "Scaling opportunity":
            d["signalType"] = "ScalingOpportunity"
            
    brand = db.get(Brand, brand_id)
    brand_name = snapshot.state.get("brand_name") or (brand.name if brand else display_name_from_brand_id(brand_id))
    return {
        "brandName": brand_name,
        "snapshots": [
            {
                "snapshotId": s.id,
                "createdAt": s.created_at.isoformat(),
                "uploadSource": s.upload_source,
                "brandId": s.brand_id,
                "snapshotVersion": s.snapshot_version,
                "isBaseline": s.is_baseline
            }
            for s in all_snapshots
        ],
        "skus": [
            {
                "skuId": s.get("sku_id", f"SKU-{i}"),
                "name": s["name"],
                "inventoryLeft": s["inventory_left"],
                "dailyVelocity": s["daily_velocity"],
                "reorderThreshold": s.get("reorder_threshold", 50),
                "projectedStockoutDays": s["projected_stockout_days"],
                "contributionMarginAfterRto": s.get("contribution_margin_after_rto", 25),
                "spendGrowthPercent": s.get("spend_growth_percent", 10)
            }
            for i, s in enumerate(snapshot.state.get("skus", []))
        ],
        "campaigns": [
            {
                "campaignId": c.get("campaign_id", f"cmp_{i}"),
                "campaignName": c["campaign_name"],
                "spend": c["spend"],
                "spendGrowthPercent": c.get("spend_growth_percent", 10),
                "roasOnPlacedOrders": c.get("roas_on_placed_orders", 3.0),
                "roasOnDeliveredOrders": c.get("roas_on_delivered_orders", 2.0),
                "ctr": c.get("ctr", 1.5),
                "ctrDropPercent": c.get("ctr_drop_percent", 5),
                "frequency": c.get("frequency", 2.5),
                "audienceRegion": "Pan India",
                "codOrderCount": c["cod_order_count"],
                "codRatio": c["cod_ratio"],
                "rtoCountAttributed": c["rto_count_attributed"],
                "deliveredOrdersAttributed": c["delivered_orders_attributed"],
                "rtoRateAttributed": c["rto_rate_attributed"],
                "contributionMarginAfterRto": c.get("contribution_margin_after_rto", 20)
            }
            for i, c in enumerate(snapshot.state.get("campaigns", []))
        ],
        "customerSegments": [
            {
                "segmentId": s.get("segment_id", f"seg_{i}"),
                "name": s["name"],
                "prepaidRatio": s.get("prepaid_ratio", 50),
                "codRatio": s.get("cod_ratio", 50),
                "repeatRate": s.get("repeat_rate", 15),
                "returnRate": s.get("return_rate", 5),
                "rtoRateOnDelivered": s.get("rto_rate_on_delivered", 10),
                "roasOnPlacedOrders": s.get("roas_on_placed_orders", 0.0),
                "roasOnDeliveredOrders": s.get("roas_on_delivered_orders", 0.0)
            }
            for i, s in enumerate(snapshot.state.get("customer_segments", []))
        ],
        "creatives": [],
        "decisions": dec_list,
        "mappingSuggestions": []
    }


@app.post("/uploads/preview", response_model=UploadPreviewResponse)
async def preview_upload(upload_source: str, brand_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    xls = pd.ExcelFile(file.file)
    sheet_names = xls.sheet_names
    normalized_sheets = {normalize_sheet_name(s): s for s in sheet_names}
    
    is_multi_sheet = len(sheet_names) > 1 or any(normalize_sheet_name(s) in normalized_sheets for s in ["shopify_orders", "shopify", "meta_ads", "meta", "inventory"])
    if is_multi_sheet:
        # For multi-sheet workbook, preview columns of shopify_orders sheet by default
        preview_sheet = next((s for s in sheet_names if "shopify" in s.lower() or "order" in s.lower()), sheet_names[0])
        frame = pd.read_excel(xls, sheet_name=preview_sheet, nrows=20)
    else:
        frame = pd.read_excel(xls, nrows=20)
        
    snapshot_count = db.scalar(select(func.count()).select_from(BusinessSnapshot).where(BusinessSnapshot.brand_id == brand_id)) or 0
    return {
        "upload_source": upload_source,
        "columns": list(frame.columns),
        "suggestions": suggest_mappings(list(frame.columns)),
        "baseline_mode": snapshot_count == 0,
    }


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub('(.)([A-Z][a-z]+)', r'\1_\2', re.sub('(.)([A-Z][A-Z][a-z]+)', r'\1_\2', name)).lower()


@app.post("/uploads/confirm")
async def confirm_upload(
    brand_id: str = Form(...),
    upload_source: str = Form(...),
    mapping: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    mapping_dict = json.loads(mapping)
    
    # Convert camelCase keys to snake_case
    mapping_dict = {camel_to_snake(k): v for k, v in mapping_dict.items()}
    
    # Save the file to local temporary folder
    file_id = str(uuid.uuid4())
    os.makedirs("temp_uploads", exist_ok=True)
    
    # Sanitize file name to avoid folders crash
    clean_filename = os.path.basename(file.filename)
    temp_file_path = f"temp_uploads/{file_id}_{clean_filename}"
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Enqueue background Celery task
    from .tasks import process_excel_upload_task
    task = process_excel_upload_task.delay(brand_id, upload_source, mapping_dict, temp_file_path)
    
    return {
        "status": "processing",
        "task_id": task.id,
        "message": "Upload confirmed. Processing spreadsheet in the background..."
    }


@app.get("/uploads/status/{task_id}")
def get_task_status(task_id: str) -> dict:
    from .celery_app import celery_app
    res = celery_app.AsyncResult(task_id)
    if res.state == "SUCCESS":
        return {"status": "success", "result": res.result}
    elif res.state == "FAILURE":
        return {"status": "failure", "error": str(res.result)}
    elif res.state == "PROGRESS":
        return {"status": "progress", "meta": res.info}
    else:
        return {"status": "pending", "state": res.state}


class DecisionRemedyRequest(BaseModel):
    remedy_id: str
    remedy_label: str


@app.post("/decisions/{decision_id}/remedy")
def select_decision_remedy(decision_id: str, payload: DecisionRemedyRequest, db: Session = Depends(get_db)) -> dict:
    from sqlalchemy.orm.attributes import flag_modified
    from datetime import datetime as dt

    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.state = "action_planned"
    decision.timeline = [
        *decision.timeline,
        {
            "id": f"evt_remedy_{decision_id[:8]}",
            "time": dt.now().strftime("%I:%M %p"),
            "title": "Action planned",
            "description": f"Operator selected: {payload.remedy_label}",
            "kind": "human",
        },
    ]
    flag_modified(decision, "timeline")

    snapshot = db.get(BusinessSnapshot, decision.snapshot_id)
    if snapshot:
        intervention = ensure_intervention(db, snapshot.brand_id, decision, "planned")
        intervention.expected_effect = {
            **(intervention.expected_effect or {}),
            "selectedRemedyId": payload.remedy_id,
            "selectedRemedyLabel": payload.remedy_label,
        }
        ensure_scorecard(db, snapshot.brand_id, decision, intervention, "pending")
    db.commit()
    return {"decision_id": decision.id, "state": decision.state, "selectedRemedyId": payload.remedy_id}


@app.delete("/decisions/{decision_id}")
def delete_decision(decision_id: str, db: Session = Depends(get_db)) -> dict:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    db.query(VerificationScorecard).filter(VerificationScorecard.decision_id == decision_id).delete()
    db.query(Intervention).filter(Intervention.decision_id == decision_id).delete()
    db.query(OntologyEdge).filter(OntologyEdge.source_decision_id == decision_id).delete()
    db.delete(decision)
    db.commit()
    return {"status": "success", "decision_id": decision_id}


@app.post("/decisions/{decision_id}/state")
def update_decision_state(decision_id: str, payload: DecisionStateRequest, db: Session = Depends(get_db)) -> dict:
    from sqlalchemy.orm.attributes import flag_modified
    from datetime import datetime as dt

    allowed = {
        "acknowledged",
        "action_planned",
        "action_executed",
        "monitoring",
        "ignored",
        "snoozed",
        "verified",
        "successful",
        "unsuccessful",
    }
    if payload.state not in allowed:
        raise HTTPException(status_code=422, detail=f"State must be one of: {', '.join(allowed)}")
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision.state = payload.state
    decision.timeline = [
        *decision.timeline,
        {
            "id": f"evt_{payload.state}_{decision_id[:8]}",
            "time": dt.now().strftime("%I:%M %p"),
            "title": f"Decision moved to {payload.state}",
            "description": "State updated by operator.",
            "kind": "human"
        },
    ]
    flag_modified(decision, "timeline")
    snapshot = db.get(BusinessSnapshot, decision.snapshot_id)
    if snapshot:
        intervention = ensure_intervention(db, snapshot.brand_id, decision, "in_progress" if payload.state == "monitoring" else payload.state)
        ensure_scorecard(db, snapshot.brand_id, decision, intervention, "pending")
    db.commit()
    return {"decision_id": decision.id, "state": decision.state}


@app.post("/monitoring/compare")
def compare_snapshots(previous: dict | None, latest: dict) -> dict:
    return {"inferences": infer_execution(previous, latest)}


@app.post("/reset")
def reset_database(reset_token: str | None = None, db: Session = Depends(get_db)) -> dict:
    configured_token = os.getenv("RESET_TOKEN", "opentra")
    if not configured_token or reset_token != configured_token:
        raise HTTPException(status_code=403, detail="Reset endpoint is locked")
    db.query(VerificationScorecard).delete()
    db.query(Intervention).delete()
    db.query(OntologyEdge).delete()
    db.query(OntologyNode).delete()
    db.query(Decision).delete()
    db.query(ConnectorEvent).delete()
    db.query(BrandGoal).delete()
    db.query(UnitEconomics).delete()
    db.query(MappingTemplate).delete()
    db.query(BusinessSnapshot).delete()
    db.query(Brand).delete()
    db.commit()
    
    # Clean up uploaded excel files
    import shutil
    if os.path.exists("temp_uploads"):
        try:
            shutil.rmtree("temp_uploads")
        except Exception as e:
            print(f"Error removing temp_uploads: {e}")
            
    return {"status": "success", "message": "Database reset successfully."}


class SandboxUpdatePayload(BaseModel):
    skus: list
    campaigns: list
    customerSegments: list


class UnitEconomicsPayload(BaseModel):
    skuId: str | None = None
    grossMarginPercent: float = 35
    shippingCost: float = 0
    codFee: float = 0
    rtoCost: float = 0
    discountCost: float = 0
    paymentGatewayCost: float = 0
    packagingCost: float = 0
    averageOrderValue: float | None = None


class GoalPayload(BaseModel):
    goalType: str
    priority: int = 1
    target: dict = {}
    active: bool = True


@app.get("/brands/{brand_id}/operating-layer")
def get_operating_layer(brand_id: str, db: Session = Depends(get_db)) -> dict:
    brand = db.get(Brand, brand_id)
    if brand is None:
        brand = Brand(id=brand_id, name=display_name_from_brand_id(brand_id))
        db.add(brand)
        db.flush()
    ensure_default_goals(db, brand_id)
    db.commit()
    economics = db.query(UnitEconomics).filter(UnitEconomics.brand_id == brand_id).all()
    goals = db.query(BrandGoal).filter(BrandGoal.brand_id == brand_id).order_by(BrandGoal.priority.asc()).all()
    nodes = db.query(OntologyNode).filter(OntologyNode.brand_id == brand_id).all()
    edges = db.query(OntologyEdge).filter(OntologyEdge.brand_id == brand_id).order_by(OntologyEdge.created_at.desc()).limit(100).all()
    events = db.query(ConnectorEvent).filter(ConnectorEvent.brand_id == brand_id).order_by(ConnectorEvent.created_at.desc()).limit(100).all()

    return {
        "goals": [{"id": g.id, "goalType": g.goal_type, "priority": g.priority, "target": g.target, "active": g.active} for g in goals],
        "unitEconomics": [
            {
                "id": e.id,
                "skuId": e.sku_id,
                "grossMarginPercent": e.gross_margin_percent,
                "shippingCost": e.shipping_cost,
                "codFee": e.cod_fee,
                "rtoCost": e.rto_cost,
                "discountCost": e.discount_cost,
                "paymentGatewayCost": e.payment_gateway_cost,
                "packagingCost": e.packaging_cost,
                "averageOrderValue": e.average_order_value,
            }
            for e in economics
        ],
        "ontology": {
            "nodes": [{"id": n.id, "entityType": n.entity_type, "entityKey": n.entity_key, "label": n.label, "properties": n.properties} for n in nodes],
            "edges": [{"id": e.id, "fromKey": e.from_key, "toKey": e.to_key, "label": e.label, "strength": e.strength, "sourceDecisionId": e.source_decision_id} for e in edges],
        },
        "events": [{"id": e.id, "source": e.source, "eventType": e.event_type, "entityKey": e.entity_key, "occurredAt": e.occurred_at.isoformat(), "payload": e.payload} for e in events],
    }


@app.post("/brands/{brand_id}/unit-economics")
def upsert_unit_economics(brand_id: str, payload: UnitEconomicsPayload, db: Session = Depends(get_db)) -> dict:
    brand = db.get(Brand, brand_id)
    if brand is None:
        brand = Brand(id=brand_id, name=display_name_from_brand_id(brand_id))
        db.add(brand)
        db.flush()
    economics = db.query(UnitEconomics).filter(UnitEconomics.brand_id == brand_id, UnitEconomics.sku_id == payload.skuId).first()
    if economics is None:
        economics = UnitEconomics(brand_id=brand_id, sku_id=payload.skuId)
        db.add(economics)
    economics.gross_margin_percent = payload.grossMarginPercent
    economics.shipping_cost = payload.shippingCost
    economics.cod_fee = payload.codFee
    economics.rto_cost = payload.rtoCost
    economics.discount_cost = payload.discountCost
    economics.payment_gateway_cost = payload.paymentGatewayCost
    economics.packaging_cost = payload.packagingCost
    economics.average_order_value = payload.averageOrderValue
    db.commit()
    return {"status": "success", "id": economics.id}


@app.post("/brands/{brand_id}/goals")
def upsert_goal(brand_id: str, payload: GoalPayload, db: Session = Depends(get_db)) -> dict:
    brand = db.get(Brand, brand_id)
    if brand is None:
        brand = Brand(id=brand_id, name=display_name_from_brand_id(brand_id))
        db.add(brand)
        db.flush()
    goal = db.query(BrandGoal).filter(BrandGoal.brand_id == brand_id, BrandGoal.goal_type == payload.goalType).first()
    if goal is None:
        goal = BrandGoal(brand_id=brand_id, goal_type=payload.goalType)
        db.add(goal)
    goal.priority = payload.priority
    goal.target = payload.target
    goal.active = payload.active
    db.commit()
    return {"status": "success", "id": goal.id}


@app.post("/state/sandbox/update")
def update_state_sandbox(payload: SandboxUpdatePayload, brand_id: str, db: Session = Depends(get_db)):
    from datetime import datetime
    import json
    
    previous_snapshot = db.query(BusinessSnapshot).filter(
        BusinessSnapshot.brand_id == brand_id
    ).order_by(BusinessSnapshot.snapshot_version.desc()).first()
    
    next_version = 1 if previous_snapshot is None else previous_snapshot.snapshot_version + 1
    is_baseline = previous_snapshot is None
    
    # Build new state dictionary
    new_state = {}
    if previous_snapshot is not None:
        new_state = json.loads(json.dumps(previous_snapshot.state))
    else:
        new_state = json.loads(json.dumps(DEMO_STATE))
        
    if previous_snapshot is None:
        new_state["brand_name"] = display_name_from_brand_id(brand_id)
    else:
        new_state["brand_name"] = new_state.get("brand_name") or display_name_from_brand_id(brand_id)

    brand = db.get(Brand, brand_id)
    if brand is None:
        brand = Brand(id=brand_id, name=new_state["brand_name"])
        db.add(brand)
        db.flush()
    else:
        brand.name = new_state["brand_name"]
    
    # Map SKUs
    new_state["skus"] = []
    for s in payload.skus:
        inventory_left = int(s.get("inventoryLeft", s.get("inventory_left", 100)))
        daily_velocity = float(s.get("dailyVelocity", s.get("daily_velocity", 10)))
        projected = round(inventory_left / max(daily_velocity, 0.1), 1)
        
        new_state["skus"].append({
            "sku_id": s.get("skuId", s.get("sku_id", f"SKU-{s['name'].upper()}")),
            "name": s["name"],
            "inventory_left": inventory_left,
            "daily_velocity": daily_velocity,
            "reorder_threshold": int(s.get("reorderThreshold", s.get("reorder_threshold", 50))),
            "projected_stockout_days": projected,
            "contribution_margin_after_rto": int(s.get("contributionMarginAfterRto", s.get("contribution_margin_after_rto", 25))),
            "spend_growth_percent": float(s.get("spendGrowthPercent", s.get("spend_growth_percent", 10))),
            "campaigns": s.get("campaigns", [])
        })
        
    # Map campaigns
    new_state["campaigns"] = []
    for c in payload.campaigns:
        rto_pct = float(c.get("rtoRateAttributed", c.get("rto_rate_attributed", 0)))
        roas_placed = float(c.get("roasOnPlacedOrders", c.get("roas_on_placed_orders", 3.0)))
        roas_delivered = round(roas_placed * (1 - (rto_pct / 100)), 2)
        
        new_state["campaigns"].append({
            "campaign_id": c.get("campaignId", c.get("campaign_id", f"cmp_{c['campaignName'].lower().replace(' ', '_')}")),
            "campaign_name": c["campaignName"],
            "spend": float(c.get("spend", 0)),
            "spend_growth_percent": float(c.get("spendGrowthPercent", c.get("spend_growth_percent", 0))),
            "roas_on_placed_orders": roas_placed,
            "roas_on_delivered_orders": roas_delivered,
            "ctr": float(c.get("ctr", 1.5)),
            "ctr_drop_percent": float(c.get("ctrDropPercent", c.get("ctr_drop_percent", 0))),
            "frequency": float(c.get("frequency", 2.5)),
            "cod_order_count": int(c.get("codOrderCount", c.get("cod_order_count", 0))),
            "cod_ratio": float(c.get("codRatio", c.get("cod_ratio", 40))),
            "rto_count_attributed": int(c.get("rtoCountAttributed", c.get("rto_count_attributed", 0))),
            "delivered_orders_attributed": int(c.get("deliveredOrdersAttributed", c.get("delivered_orders_attributed", 0))),
            "rto_rate_attributed": rto_pct,
            "contribution_margin_after_rto": int(c.get("contributionMarginAfterRto", c.get("contribution_margin_after_rto", 20))),
            "skus": c.get("skus", [])
        })
        
    # Map customer segments
    new_state["customer_segments"] = []
    for s in payload.customerSegments:
        new_state["customer_segments"].append({
            "segment_id": s.get("segmentId", s.get("segment_id", f"seg_{s['name'].lower().replace(' ', '_')}")),
            "name": s["name"],
            "prepaid_ratio": float(s.get("prepaidRatio", s.get("prepaid_ratio", 50))),
            "cod_ratio": float(s.get("codRatio", s.get("cod_ratio", 50))),
            "repeat_rate": float(s.get("repeatRate", s.get("repeat_rate", 15))),
            "return_rate": float(s.get("returnRate", s.get("return_rate", 5))),
            "rto_rate_on_delivered": float(s.get("rtoRateOnDelivered", s.get("rto_rate_on_delivered", 10))),
            "roas_on_placed_orders": float(s.get("roasOnPlacedOrders", s.get("roas_on_placed_orders", 0.0))),
            "roas_on_delivered_orders": float(s.get("roasOnDeliveredOrders", s.get("roas_on_delivered_orders", 0.0)))
        })
        
    new_state["rto_data_present"] = True
    
    # Create snapshot
    snapshot = BusinessSnapshot(
        brand_id=brand_id,
        upload_source="data_sandbox",
        snapshot_version=next_version,
        is_baseline=is_baseline,
        state=new_state
    )
    db.add(snapshot)
    db.flush()
    ensure_default_goals(db, brand_id)
    upsert_unit_economics_from_state(db, brand_id, new_state)
    persist_connector_events(db, brand_id, snapshot, new_state)
    
    # Run Monitoring verification engine
    previous_state = previous_snapshot.state if previous_snapshot else None
    MonitoringEngine.verify_actions(previous_state, new_state, db_session=db)
    
    # Run Signal detection engine
    signals = SignalDetectionEngine.detect(new_state, freshness=1.0)
    
    # Store decisions
    for signal in signals:
        # Check if there is an existing decision for the same rule/title in the database
        # that is currently in 'monitoring' or 'successful' state.
        # If so, carry forward its state and timeline!
        existing_active = db.query(Decision).filter(
            Decision.rule == signal.rule,
            Decision.state.in_(["monitoring", "successful"])
        ).order_by(Decision.created_at.desc()).first()
        
        # Invoke LLM enrichment layer
        try:
            enriched = LLMEnrichmentService.enrich_signal(signal)
        except Exception as llm_exc:
            print(f"⚠️ [LLM LAYER] Error invoking enrichment service: {llm_exc}", flush=True)
            enriched = {}
            
        d_state = "pending"
        d_timeline = [
            {
                "id": f"evt_init_{snapshot.id}",
                "time": datetime.now().strftime("%I:%M %p"),
                "title": f"{signal.issue_type} Detected",
                "description": enriched.get("explanation", signal.explanation),
                "kind": "signal"
            }
        ]
        
        if existing_active:
            d_state = existing_active.state
            d_timeline = existing_active.timeline
            
        decision = Decision(
            snapshot_id=snapshot.id,
            title=enriched.get("title", signal.title),
            issue_type=signal.issue_type,
            severity=signal.severity,
            confidence_score=signal.confidence_score,
            business_impact=signal.business_impact,
            recommendation=enriched.get("recommendation", signal.recommendation),
            affected_campaigns=signal.affected_campaigns,
            affected_skus=signal.affected_skus,
            state=d_state,
            timeline=d_timeline,
            rule=signal.rule,
            explanation=enriched.get("explanation", signal.explanation),
            impact_label=signal.impact_label,
            cross_system_signals=signal.cross_system_signals,
            risk_projection=enriched.get("risk_projection", signal.risk_projection),
            recommended_actions=enriched.get("recommended_actions", signal.recommended_actions),
            verification_signals=signal.verification_signals,
            confidence_explanation=enriched.get("confidence_explanation", signal.confidence_explanation or signal.confidence_explanation),
            relationship_edges=enriched.get("relationship_edges", signal.relationship_edges)
        )
        db.add(decision)
        db.flush()
        persist_ontology(db, brand_id, decision)
        intervention = ensure_intervention(db, brand_id, decision, "recommended")
        ensure_scorecard(db, brand_id, decision, intervention, "pending")
        
    if previous_snapshot:
        carry_forward_active_decisions(db, brand_id, previous_snapshot.id, snapshot.id)
        
    db.commit()
    return {"status": "success", "snapshot_id": snapshot.id}
