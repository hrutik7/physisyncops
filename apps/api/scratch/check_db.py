import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import SessionLocal
from app.models import BusinessSnapshot

db = SessionLocal()
try:
    snapshot = db.query(BusinessSnapshot).filter(
        BusinessSnapshot.brand_id == "brand_unigo_real"
    ).order_by(BusinessSnapshot.snapshot_version.desc()).first()
    
    if snapshot:
        print(f"Snapshot ID: {snapshot.id}")
        print(f"Version: {snapshot.snapshot_version}")
        print(f"Upload Source: {snapshot.upload_source}")
        
        state = snapshot.state
        print("\n--- SKUs ---")
        for sku in state.get("skus", []):
            print(f"- SKU: {sku.get('sku_id')} | Name: {sku.get('name')} | AOV: {sku.get('average_order_value')}")
            
        print("\n--- Campaigns ---")
        for camp in state.get("campaigns", []):
            print(f"- Campaign: {camp.get('campaign_name')} | Spend: {camp.get('spend')} | Placed ROAS: {camp.get('roas_on_placed_orders')} | Delivered ROAS: {camp.get('roas_on_delivered_orders')} | RTO rate: {camp.get('rto_rate_attributed')} | COD: {camp.get('cod_order_count')}")
            
        print("\n--- Customer Segments ---")
        for seg in state.get("customer_segments", []):
            print(f"- Segment: {seg.get('name')} | RTO Rate: {seg.get('rto_rate_on_delivered')} | COD Ratio: {seg.get('cod_ratio')}")
            
    else:
        print("No snapshot found for brand_unigo_real")
finally:
    db.close()
