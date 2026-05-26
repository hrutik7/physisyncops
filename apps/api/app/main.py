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
from .models import Brand, BusinessSnapshot, Decision, MappingTemplate
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
def get_state(brand_id: str = "brand_unigo", db: Session = Depends(get_db)):
    # Query latest snapshot
    snapshot = db.scalars(
        select(BusinessSnapshot)
        .where(BusinessSnapshot.brand_id == brand_id)
        .order_by(BusinessSnapshot.snapshot_version.desc())
    ).first()
    
    if snapshot is None:
        return {
            "brandName": "Unigo Footwear",
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
    
    snapshot_ids = [s.id for s in all_snapshots]
    all_decisions = db.scalars(
        select(Decision)
        .where(Decision.snapshot_id.in_(snapshot_ids))
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
        dec_list.append({
            "id": d.id,
            "title": d.title,
            "signalType": d.issue_type.replace(" ", ""),
            "issueType": d.issue_type,
            "severity": d.severity,
            "confidenceScore": d.confidence_score,
            "businessImpact": d.business_impact,
            "impactLabel": d.impact_label or f"Rs {d.business_impact} impact",
            "explanation": d.explanation,
            "rule": d.rule,
            "recommendation": d.recommendation,
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
            "relationshipEdges": d.relationship_edges
        })
        
    for d in dec_list:
        if d["issueType"] == "Campaign-level RTO spike":
            d["signalType"] = "CampaignRTOSpike"
        elif d["issueType"] == "Inventory pressure":
            d["signalType"] = "InventoryRisk"
        elif d["issueType"] == "Creative fatigue":
            d["signalType"] = "CreativeFatigue"
        elif d["issueType"] == "Margin leakage":
            d["signalType"] = "MarginLeakage"
        elif d["issueType"] == "Scaling opportunity":
            d["signalType"] = "ScalingOpportunity"
            
    brand_name = snapshot.state.get("brand_name", "Unigo Footwear") if snapshot else "Unigo Footwear"
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
                "rtoRateOnDelivered": s.get("rto_rate_on_delivered", 10)
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
    
    is_multi_sheet = len(sheet_names) > 1 or any(s in sheet_names for s in ["shopify_orders", "meta_ads", "inventory"])
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


@app.post("/decisions/{decision_id}/state")
def update_decision_state(decision_id: str, payload: DecisionStateRequest, db: Session = Depends(get_db)) -> dict:
    from sqlalchemy.orm.attributes import flag_modified
    from datetime import datetime as dt

    allowed = {"monitoring", "ignored", "snoozed", "verified", "successful", "unsuccessful"}
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
    db.commit()
    return {"decision_id": decision.id, "state": decision.state}


@app.post("/monitoring/compare")
def compare_snapshots(previous: dict | None, latest: dict) -> dict:
    return {"inferences": infer_execution(previous, latest)}


@app.post("/reset")
def reset_database(db: Session = Depends(get_db)) -> dict:
    db.query(Decision).delete()
    db.query(BusinessSnapshot).delete()
    db.query(Brand).delete()
    db.commit()
    return {"status": "success", "message": "Database reset successfully."}


class SandboxUpdatePayload(BaseModel):
    skus: list
    campaigns: list
    customerSegments: list


@app.post("/state/sandbox/update")
def update_state_sandbox(payload: SandboxUpdatePayload, db: Session = Depends(get_db)):
    from datetime import datetime
    import json
    
    brand_id = "brand_unigo"
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
        
    new_state["brand_name"] = "Unigo Footwear"
    
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
            "rto_rate_on_delivered": float(s.get("rtoRateOnDelivered", s.get("rto_rate_on_delivered", 10)))
        })
        
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
        
    db.commit()
    return {"status": "success", "snapshot_id": snapshot.id}
