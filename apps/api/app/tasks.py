import os
import pandas as pd
import json
import re
from typing import Any
from datetime import datetime, timezone

from .celery_app import celery_app
from .db import SessionLocal
from .models import BusinessSnapshot, Decision, Brand
from .rules import SignalDetectionEngine, DataFreshnessValidator
from .verification import MonitoringEngine
from .demo_data import DEMO_STATE
from .llm import LLMEnrichmentService
from .operating_layer import (
    ensure_default_goals,
    ensure_intervention,
    ensure_scorecard,
    persist_connector_events,
    persist_ontology,
    upsert_unit_economics_from_state,
)


def display_name_from_brand_id(brand_id: str) -> str:
    clean = re.sub(r"^brand[_-]?", "", brand_id).replace("_", " ").replace("-", " ").strip()
    return clean.title() if clean else "Uploaded Brand"


@celery_app.task(name="app.tasks.process_excel_upload_task", bind=True)
def process_excel_upload_task(self, brand_id: str, upload_source: str, mapping: dict[str, str], file_path: str) -> dict:
    self.update_state(state="PROGRESS", meta={"step": "Parsing Excel workbook sheets"})
    
    db = SessionLocal()
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at {file_path}")
            
        # Load sheets
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        # Fetch the previous snapshot if any
        previous_snapshot = db.query(BusinessSnapshot).filter(
            BusinessSnapshot.brand_id == brand_id
        ).order_by(BusinessSnapshot.snapshot_version.desc()).first()
        
        next_version = 1 if previous_snapshot is None else previous_snapshot.snapshot_version + 1
        is_baseline = previous_snapshot is None
        
        # Initialize new state from previous snapshot's state or DEMO_STATE as a baseline
        if previous_snapshot is not None:
            new_state = json.loads(json.dumps(previous_snapshot.state))
        else:
            new_state = json.loads(json.dumps(DEMO_STATE))
            
        if previous_snapshot is None:
            new_state["brand_name"] = display_name_from_brand_id(brand_id)
        else:
            new_state["brand_name"] = new_state.get("brand_name") or display_name_from_brand_id(brand_id)
        
        # Check if the uploaded file is a custom brand upload by looking at its SKU names
        is_custom_upload = False
        try:
            # Let's inspect the sheets to see if any SKU is not Unigo's SKUs
            test_xls = pd.ExcelFile(file_path)
            for sname in test_xls.sheet_names:
                sdf = pd.read_excel(test_xls, sheet_name=sname)
                sdf.columns = [str(c).strip().lower() for c in sdf.columns]
                sku_col = next((c for c in sdf.columns if "sku" in c or "variant" in c), None)
                if sku_col:
                    unique_skus = sdf[sku_col].dropna().unique()
                    for x in unique_skus:
                        x_str = str(x).strip().lower()
                        if x_str and x_str != "nan" and not any(u in x_str for u in ["velar", "legend", "alpha", "timber", "charge", "cosmos"]):
                            is_custom_upload = True
                            break
                if is_custom_upload:
                    break
        except Exception as e:
            print(f"⚠️ Error checking custom upload SKUs: {e}", flush=True)

        if is_custom_upload:
            print("🚀 [DYNAMIC INGESTION] Custom brand upload detected! Clearing Unigo mock data templates.", flush=True)
            new_state["brand_name"] = display_name_from_brand_id(brand_id)
            new_state["skus"] = []
            new_state["campaigns"] = []
            new_state["customer_segments"] = []
        
        # Check if it's a multi-sheet workbook
        is_multi_sheet = len(sheet_names) > 1 or any(s in sheet_names for s in ["shopify_orders", "meta_ads", "inventory"])
        
        freshness = 1.0 # Default full freshness
        
        print("\n" + "=" * 80, flush=True)
        print(f"🚀 [DYNAMIC INGESTION] STARTED CALCULATIONS FOR BRAND: {brand_id}", flush=True)
        print(f"   📂 File Path: {file_path}", flush=True)
        print(f"   📋 Sheets found: {sheet_names}", flush=True)
        print(f"   ⚙️ Snapshot Version: v{next_version} (is_baseline={is_baseline})", flush=True)
        print("=" * 80 + "\n", flush=True)

        if is_multi_sheet:
            self.update_state(state="PROGRESS", meta={"step": "Ingesting multi-sheet workbook"})
            sheets = {s: pd.read_excel(xls, sheet_name=s) for s in sheet_names}
            
            # --- 1. Parse inventory sheet ---
            # Columns: sku, stock_left, daily_velocity, reorder_level, projected_stockout_days
            if "inventory" in sheets:
                print("🔍 [STEP 1/4] Processing 'inventory' sheet dynamically...", flush=True)
                inv_df = sheets["inventory"]
                inv_df.columns = [str(c).strip().lower() for c in inv_df.columns]
                
                sku_col = next((c for c in inv_df.columns if "sku" in c or "variant" in c), None)
                stock_col = next((c for c in inv_df.columns if "stock" in c or "left" in c or "inventory" in c), None)
                velocity_col = next((c for c in inv_df.columns if "velocity" in c or "daily" in c), None)
                reorder_col = next((c for c in inv_df.columns if "reorder" in c or "level" in c or "threshold" in c), None)
                stockout_col = next((c for c in inv_df.columns if "stockout" in c or "projected" in c), None)
                
                if sku_col:
                    if "skus" not in new_state or not isinstance(new_state["skus"], list):
                        new_state["skus"] = []
                        
                    for _, row in inv_df.iterrows():
                        sku_name = str(row[sku_col]).strip()
                        if not sku_name or sku_name.lower() == "nan":
                            continue
                        
                        sku = next((s for s in new_state["skus"] if s["name"].lower() == sku_name.lower() or s["sku_id"].lower() == sku_name.lower() or s["sku_id"].lower() == f"sku-{sku_name.lower()}"), None)
                        if not sku:
                            sku = {
                                "sku_id": f"SKU-{sku_name.upper()}",
                                "name": sku_name,
                                "inventory_left": 100,
                                "daily_velocity": 10.0,
                                "reorder_threshold": 50,
                                "projected_stockout_days": 10.0,
                                "contribution_margin_after_rto": 25,
                                "spend_growth_percent": 10,
                                "campaigns": []
                            }
                            new_state["skus"].append(sku)
                            
                        if stock_col and pd.notna(row[stock_col]): sku["inventory_left"] = int(row[stock_col])
                        if velocity_col and pd.notna(row[velocity_col]): sku["daily_velocity"] = float(row[velocity_col])
                        if reorder_col and pd.notna(row[reorder_col]): sku["reorder_threshold"] = int(row[reorder_col])
                        
                        if stockout_col and pd.notna(row[stockout_col]):
                            sku["projected_stockout_days"] = float(row[stockout_col])
                        elif sku["daily_velocity"] > 0:
                            sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                        
                        print(f"   📦 SKU '{sku_name}': Stock Left={sku['inventory_left']}, Daily Sales Velocity={sku['daily_velocity']} units/day -> Projected Stockout Days={sku['projected_stockout_days']}", flush=True)
                            
            # --- 2. Parse meta_ads sheet ---
            # Columns: campaign_name, creative_hook, daily_spend, roas, ctr_percent, frequency, cpa, status
            if "meta_ads" in sheets:
                print("\n🔍 [STEP 2/4] Processing 'meta_ads' sheet dynamically...", flush=True)
                ads_df = sheets["meta_ads"]
                ads_df.columns = [str(c).strip().lower() for c in ads_df.columns]
                
                camp_col = next((c for c in ads_df.columns if "campaign" in c or "name" in c), None)
                spend_col = next((c for c in ads_df.columns if "spend" in c or "daily" in c or "amount" in c or "cost" in c), None)
                roas_col = next((c for c in ads_df.columns if "roas" in c), None)
                ctr_col = next((c for c in ads_df.columns if "ctr" in c or "percent" in c), None)
                ctr_drop_col = next((c for c in ads_df.columns if "ctr" in c and ("drop" in c or "decay" in c or "change" in c)), None)
                freq_col = next((c for c in ads_df.columns if "freq" in c), None)
                
                if camp_col:
                    if "campaigns" not in new_state or not isinstance(new_state["campaigns"], list):
                        new_state["campaigns"] = []
                        
                    grouped = ads_df.groupby(camp_col)
                    for camp_name, group in grouped:
                        camp_name_str = str(camp_name).strip()
                        if not camp_name_str or camp_name_str.lower() == "nan":
                            continue
                        
                        campaign = next((c for c in new_state["campaigns"] if c["campaign_name"].lower() == camp_name_str.lower() or c["campaign_id"].lower() == camp_name_str.lower() or c["campaign_id"].lower() == f"cmp_{camp_name_str.lower().replace(' ', '_')}"), None)
                        has_prior_campaign = campaign is not None
                        if not campaign:
                            campaign = {
                                "campaign_id": f"cmp_{camp_name_str.lower().replace(' ', '_')}",
                                "campaign_name": camp_name_str,
                                "spend": 0,
                                "spend_growth_percent": 0,
                                "roas_on_placed_orders": 3.0,
                                "roas_on_delivered_orders": 2.0,
                                "ctr": 0,
                                "ctr_drop_percent": 0,
                                "ctr_drop_source": "missing_baseline",
                                "frequency": 2.5,
                                "cod_order_count": 0,
                                "cod_ratio": 40,
                                "rto_count_attributed": 0,
                                "delivered_orders_attributed": 0,
                                "rto_rate_attributed": 0,
                                "contribution_margin_after_rto": 20,
                                "skus": []
                            }
                            new_state["campaigns"].append(campaign)
                            
                        prev_spend = campaign["spend"]
                        if spend_col:
                            campaign["spend"] = float(group[spend_col].sum())
                            if prev_spend > 0:
                                campaign["spend_growth_percent"] = round(((campaign["spend"] - prev_spend) / prev_spend) * 100, 2)
                        if roas_col: campaign["roas_on_placed_orders"] = float(group[roas_col].mean())
                        if ctr_drop_col:
                            campaign["ctr_drop_percent"] = float(group[ctr_drop_col].mean())
                            campaign["ctr_drop_source"] = ctr_drop_col
                        if ctr_col:
                            prev_ctr = campaign.get("ctr", 0)
                            campaign["ctr"] = float(group[ctr_col].mean())
                            if has_prior_campaign and prev_ctr > 0 and not ctr_drop_col:
                                campaign["ctr_drop_percent"] = round(((prev_ctr - campaign["ctr"]) / prev_ctr) * 100, 2)
                                campaign["ctr_drop_source"] = "previous_snapshot_ctr"
                        if freq_col: campaign["frequency"] = float(group[freq_col].mean())
                        
                        print(f"   📢 Campaign '{camp_name_str}': Total Spend=Rs {campaign['spend']} (Growth={campaign['spend_growth_percent']}%), Placed ROAS={campaign['roas_on_placed_orders']}x, CTR={campaign['ctr']}%, Freq={campaign['frequency']}", flush=True)
                        
            # --- 3. Parse customer_signals sheet ---
            # Columns: sku, repeat_rate_percent, return_rate_percent, review_sentiment, cod_ratio_percent, prepaid_ratio_percent
            if "customer_signals" in sheets:
                print("\n🔍 [STEP 3/4] Processing 'customer_signals' sheet dynamically...", flush=True)
                cust_df = sheets["customer_signals"]
                cust_df.columns = [str(c).strip().lower() for c in cust_df.columns]
                
                sku_col = next((c for c in cust_df.columns if "sku" in c or "variant" in c), None)
                repeat_col = next((c for c in cust_df.columns if "repeat" in c or "rate" in c), None)
                return_col = next((c for c in cust_df.columns if "return" in c or "rto" in c), None)
                cod_col = next((c for c in cust_df.columns if "cod" in c or "ratio" in c), None)
                prepaid_col = next((c for c in cust_df.columns if "prepaid" in c), None)
                
                if sku_col:
                    if "customer_segments" not in new_state or not isinstance(new_state["customer_segments"], list):
                        new_state["customer_segments"] = []
                        
                    for _, row in cust_df.iterrows():
                        sku_name = str(row[sku_col]).strip()
                        if not sku_name or sku_name.lower() == "nan":
                            continue
                            
                        segment = next((s for s in new_state["customer_segments"] if s["name"].lower() == sku_name.lower()), None)
                        if not segment:
                            segment = {
                                "segment_id": f"seg_{sku_name.lower().replace(' ', '_')}",
                                "name": sku_name,
                                "prepaid_ratio": 50,
                                "cod_ratio": 50,
                                "repeat_rate": 15,
                                "return_rate": 0,
                                "rto_rate_on_delivered": 0,
                                "skus": [sku_name],
                                "roas_on_placed_orders": 0.0
                            }
                            # Calculate matching campaign blended ROAS
                            matching_camps = [c for c in new_state.get("campaigns", []) if sku_name.lower() in c["campaign_name"].lower() or c["campaign_name"].lower() in sku_name.lower()]
                            if matching_camps:
                                tot_spend = sum(c.get("spend", 0) for c in matching_camps)
                                tot_rev = sum(c.get("spend", 0) * c.get("roas_on_placed_orders", 0.0) for c in matching_camps)
                                segment["roas_on_placed_orders"] = round(tot_rev / max(tot_spend, 1), 2) if tot_spend > 0 else 0.0
                            
                            new_state["customer_segments"].append(segment)
                            
                        if repeat_col and pd.notna(row[repeat_col]): segment["repeat_rate"] = float(row[repeat_col])
                        if return_col and pd.notna(row[return_col]):
                            segment["return_rate"] = float(row[return_col])
                            if "rto" in return_col or "return" in return_col:
                                segment["rto_rate_on_delivered"] = float(row[return_col])
                        if cod_col and pd.notna(row[cod_col]): 
                            segment["cod_ratio"] = float(row[cod_col])
                        if prepaid_col and pd.notna(row[prepaid_col]): segment["prepaid_ratio"] = float(row[prepaid_col])
                        
                        print(f"   👥 Customer Segment '{sku_name}': COD Mix={segment['cod_ratio']}%, Prepaid Mix={segment['prepaid_ratio']}%, Repeat Rate={segment['repeat_rate']}%, returnRate={segment['return_rate']}%", flush=True)
                        
            # --- 4. Parse shopify_orders sheet ---
            # Columns: order_id, order_date, sku, city, payment_mode, revenue, customer_type
            if "shopify_orders" in sheets:
                print("\n🔍 [STEP 4/4] Processing 'shopify_orders' sheet dynamically...", flush=True)
                orders_df = sheets["shopify_orders"]
                orders_df.columns = [str(c).strip().lower() for c in orders_df.columns]
                
                sku_col = next((c for c in orders_df.columns if "sku" in c or "variant" in c), None)
                pm_col = next((c for c in orders_df.columns if "payment" in c or "mode" in c or "method" in c), None)
                rto_col = next((c for c in orders_df.columns if "rto" in c or "returned" in c or "undelivered" in c), None)
                delivered_col = next((c for c in orders_df.columns if "delivered" in c or "fulfilled" in c), None)
                revenue_col = next((c for c in orders_df.columns if "revenue" in c or "total" in c or "amount" in c or "price" in c), None)
                if revenue_col and len(orders_df) > 0:
                    revenue_values = pd.to_numeric(orders_df[revenue_col], errors="coerce").dropna()
                    if len(revenue_values) > 0:
                        new_state["average_order_value"] = round(float(revenue_values.sum()) / len(orders_df), 2)
                
                if sku_col:
                    grouped = orders_df.groupby(sku_col)
                    for sku_name, group in grouped:
                        sku_name_str = str(sku_name).strip()
                        if not sku_name_str or sku_name_str.lower() == "nan":
                            continue
                            
                        segment = next((s for s in new_state["customer_segments"] if s["name"].lower() == sku_name_str.lower()), None)
                        if segment and pm_col:
                            cod_count = int(group[pm_col].astype(str).str.upper().str.contains("COD|CASH").sum())
                            placed_count = len(group)
                            segment["cod_ratio"] = round((cod_count / max(placed_count, 1)) * 100, 2)
                            segment["prepaid_ratio"] = 100 - segment["cod_ratio"]
                        if segment and revenue_col:
                            segment_revenue = pd.to_numeric(group[revenue_col], errors="coerce").sum()
                            segment["average_order_value"] = round(float(segment_revenue) / max(len(group), 1), 2)
                            
                        for campaign in new_state.get("campaigns", []):
                            if sku_name_str.lower() in campaign["campaign_name"].lower() or campaign["campaign_name"].lower() in sku_name_str.lower():
                                placed_count = len(group)
                                cod_count = int(group[pm_col].astype(str).str.upper().str.contains("COD|CASH").sum()) if pm_col else 0
                                campaign["cod_order_count"] = cod_count
                                campaign["cod_ratio"] = round((cod_count / max(placed_count, 1)) * 100, 2)
                                delivered_count = int(group[delivered_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "DELIVERED", "FULFILLED"]).sum()) if delivered_col else placed_count
                                rto_count = int(group[rto_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "RTO", "RETURNED", "UNDELIVERED"]).sum()) if rto_col else 0
                                campaign["delivered_orders_attributed"] = delivered_count
                                campaign["rto_count_attributed"] = rto_count
                                if campaign["delivered_orders_attributed"] > 0:
                                    campaign["rto_rate_attributed"] = round((campaign["rto_count_attributed"] / campaign["delivered_orders_attributed"]) * 100, 2)
                                
                                print(f"   🛒 Shopify Orders matching campaign '{campaign['campaign_name']}': Total={placed_count}, COD Orders={cod_count} (COD Ratio={campaign['cod_ratio']}%) -> Realized Attributed RTO rate={campaign['rto_rate_attributed']}%", flush=True)
                                    
            # Recalculate stockout days and contribution margins based on returned RTO rates
            print("\n🔄 [RECALCULATING DERIVED METRICS] Week-over-week stockout trends and COD contribution margins...", flush=True)
            for sku in new_state.get("skus", []):
                if sku["daily_velocity"] > 0:
                    sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                else:
                    sku["projected_stockout_days"] = 99.0
                    
            for campaign in new_state.get("campaigns", []):
                rto_pct = campaign.get("rto_rate_attributed", 0)
                if rto_pct > 0:
                    campaign["roas_on_delivered_orders"] = round(campaign["roas_on_placed_orders"] * (1 - (rto_pct / 100)), 2)
                    campaign["contribution_margin_after_rto"] = max(int(28 - (rto_pct * 0.65)), 5)
                    print(f"   📈 Blended Adjustment for '{campaign['campaign_name']}': ROAS On Placed orders {campaign['roas_on_placed_orders']}x compressed to ROAS On Delivered orders {campaign['roas_on_delivered_orders']}x. Margin compressed to {campaign['contribution_margin_after_rto']}%", flush=True)
                    
        else:
            # --- Backward compatible Single Sheet Ingestion ---
            self.update_state(state="PROGRESS", meta={"step": "Ingesting single sheet spreadsheet"})
            df = pd.read_excel(file_path)
            df.columns = [str(c).strip() for c in df.columns]
            
            inv_mapping = {v: k for k, v in mapping.items() if v}
            df_canonical = df.rename(columns=inv_mapping)
            
            # Calculate Data Freshness
            freshness = DataFreshnessValidator.validate(df)
            
            if upload_source == "shopify_orders":
                revenue_col = next((c for c in df_canonical.columns if c in {"revenue", "total", "amount", "price", "order_value"}), None)
                if revenue_col and len(df_canonical) > 0:
                    revenue_values = pd.to_numeric(df_canonical[revenue_col], errors="coerce").dropna()
                    if len(revenue_values) > 0:
                        new_state["average_order_value"] = round(float(revenue_values.sum()) / len(df_canonical), 2)

                # Create segments and SKUs dynamically from the uploaded orders sheet
                if "sku_id" in df_canonical.columns:
                    sku_grouped = df_canonical.groupby("sku_id")
                    for sku_name, group in sku_grouped:
                        sku_name_str = str(sku_name).strip()
                        if not sku_name_str or sku_name_str.lower() == "nan":
                            continue
                            
                        # Calculate daily velocity based on number of unique order dates in the sheet
                        days_count = 1
                        if "order_date" in df.columns:
                            try:
                                days_count = max(df["order_date"].nunique(), 1)
                            except:
                                days_count = 1
                        
                        order_count = len(group)
                        velocity = round(order_count / days_count, 1)
                        
                        # Calculate COD ratio
                        cod_count = 0
                        if "cod_orders" in group.columns:
                            cod_col = group["cod_orders"]
                            cod_count = int(cod_col.astype(str).str.upper().str.contains("COD|CASH").sum())
                        
                        cod_ratio = round((cod_count / max(order_count, 1)) * 100, 2)
                        prepaid_ratio = round(100 - cod_ratio, 2)
                        rto_rate_on_delivered = round(cod_ratio * 0.38, 2)
                        
                        # Find or create SKU
                        sku = next((s for s in new_state.get("skus", []) if s["sku_id"].lower() == sku_name_str.lower() or s["name"].lower() == sku_name_str.lower()), None)
                        if not sku:
                            sku = {
                                "sku_id": f"SKU-{sku_name_str.upper().replace(' ', '_')}",
                                "name": sku_name_str,
                                "inventory_left": 80,  # Default stock level for demonstration
                                "daily_velocity": velocity,
                                "reorder_threshold": 40,
                                "projected_stockout_days": round(80 / max(velocity, 0.1), 1),
                                "contribution_margin_after_rto": 25,
                                "spend_growth_percent": 18.0,  # Force elevated spend growth to trigger stockout risk dynamically
                                "campaigns": []
                            }
                            new_state["skus"].append(sku)
                        else:
                            sku["daily_velocity"] = velocity
                            if sku["daily_velocity"] > 0:
                                sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                        
                        # Find or create customer segment
                        segment = next((s for s in new_state.get("customer_segments", []) if s["name"].lower() == sku_name_str.lower()), None)
                        if not segment:
                            segment = {
                                "segment_id": f"seg_{sku_name_str.lower().replace(' ', '_')}",
                                "name": sku_name_str,
                                "prepaid_ratio": prepaid_ratio,
                                "cod_ratio": cod_ratio,
                                "repeat_rate": 22.0,
                                "return_rate": round(cod_ratio * 0.15, 2),
                                "rto_rate_on_delivered": rto_rate_on_delivered,
                                "skus": [sku_name_str]
                            }
                            new_state["customer_segments"].append(segment)
                        else:
                            segment["cod_ratio"] = cod_ratio
                            segment["prepaid_ratio"] = prepaid_ratio
                            segment["rto_rate_on_delivered"] = rto_rate_on_delivered

                # Create campaigns dynamically as well
                if "campaign_id" in df_canonical.columns:
                    grouped = df_canonical.groupby("campaign_id")
                    for camp_id, group in grouped:
                        camp_id_str = str(camp_id).strip()
                        campaign = next((c for c in new_state.get("campaigns", []) if c["campaign_id"] == camp_id_str or c["campaign_name"] == camp_id_str), None)
                        
                        # Find associated SKU name
                        sku_name_str = ""
                        if "sku_id" in group.columns:
                            sku_name_str = str(group["sku_id"].iloc[0]).strip()
                            
                        placed_count = len(group)
                        cod_count = 0
                        if "cod_orders" in group.columns:
                            cod_col = group["cod_orders"]
                            cod_count = int(cod_col.astype(str).str.upper().str.contains("COD|CASH").sum())
                            
                        cod_ratio = round((cod_count / max(placed_count, 1)) * 100, 2)
                        
                        # Estimate ad spend and metrics if not present
                        spend = 12000
                        if "ad_spend" in group.columns:
                            try:
                                spend = float(group["ad_spend"].sum())
                            except:
                                spend = 12000
                                
                        revenue_sum = 0
                        if "revenue" in group.columns:
                            try:
                                revenue_sum = float(group["revenue"].sum())
                            except:
                                revenue_sum = 0
                                
                        roas = round(revenue_sum / max(spend, 1), 2) if revenue_sum > 0 else 3.0
                        rto_pct = round(cod_ratio * 0.4, 2)
                        if not campaign:
                            campaign = {
                                "campaign_id": camp_id_str,
                                "campaign_name": camp_id_str,
                                "spend": spend,
                                "spend_growth_percent": 5.0,
                                "roas_on_placed_orders": roas,
                                "roas_on_delivered_orders": roas,
                                "frequency": 1.8,
                                "ctr_drop_percent": 0.0,
                                "ctr": 1.5,
                                "cod_order_count": cod_count,
                                "cod_ratio": cod_ratio,
                                "rto_count_attributed": 0,
                                "delivered_orders_attributed": placed_count,
                                "rto_rate_attributed": 0.0,
                                "contribution_margin_after_rto": 25,
                                "skus": [sku_name_str] if sku_name_str else []
                            }
                            new_state["campaigns"].append(campaign)
                        else:
                            campaign["spend"] = spend
                            campaign["roas_on_placed_orders"] = roas
                            campaign["cod_order_count"] = cod_count
                            campaign["cod_ratio"] = cod_ratio
                            
            elif upload_source == "meta_ads":
                if "campaign_id" in df_canonical.columns:
                    for _, row in df_canonical.iterrows():
                        camp_id = str(row["campaign_id"]).strip()
                        campaign = next((c for c in new_state.get("campaigns", []) if c["campaign_id"] == camp_id or c["campaign_name"] == camp_id), None)
                        if not campaign:
                            campaign = {
                                "campaign_id": camp_id,
                                "campaign_name": camp_id,
                                "spend": 0,
                                "spend_growth_percent": 0,
                                "roas_on_placed_orders": 2.5,
                                "roas_on_delivered_orders": 2.0,
                                "frequency": 1.0,
                                "ctr_drop_percent": 0,
                                "ctr": 0,
                                "cod_order_count": 0,
                                "cod_ratio": 0,
                                "rto_count_attributed": 0,
                                "delivered_orders_attributed": 0,
                                "rto_rate_attributed": 0,
                                "contribution_margin_after_rto": 25,
                                "skus": []
                            }
                            new_state["campaigns"].append(campaign)
                        
                        if "ad_spend" in df_canonical.columns:
                            prev_spend = campaign["spend"]
                            campaign["spend"] = float(row["ad_spend"])
                            if prev_spend > 0:
                                campaign["spend_growth_percent"] = round(((campaign["spend"] - prev_spend) / prev_spend) * 100, 2)
                        if "frequency" in df_canonical.columns:
                            campaign["frequency"] = float(row["frequency"])
                        if "ctr" in df_canonical.columns:
                            prev_ctr = campaign.get("ctr", 0)
                            campaign["ctr"] = float(row["ctr"])
                            if prev_ctr > 0:
                                campaign["ctr_drop_percent"] = round(((prev_ctr - campaign["ctr"]) / prev_ctr) * 100, 2)
                                campaign["ctr_drop_source"] = "previous_snapshot_ctr"
                                
            elif upload_source == "inventory":
                if "sku_id" in df_canonical.columns:
                    for _, row in df_canonical.iterrows():
                        sku_id = str(row["sku_id"]).strip()
                        sku = next((s for s in new_state.get("skus", []) if s["sku_id"] == sku_id or s["name"] == sku_id), None)
                        if not sku:
                            sku = {
                                "sku_id": sku_id,
                                "name": sku_id,
                                "inventory_left": 100,
                                "daily_velocity": 10,
                                "reorder_threshold": 50,
                                "projected_stockout_days": 10.0,
                                "contribution_margin_after_rto": 30,
                                "spend_growth_percent": 10,
                                "campaigns": []
                            }
                            new_state["skus"].append(sku)
                        
                        if "inventory_left" in df_canonical.columns:
                            sku["inventory_left"] = int(row["inventory_left"])
                        if "daily_velocity" in df_canonical.columns:
                            sku["daily_velocity"] = float(row["daily_velocity"])
                        
                        if sku["daily_velocity"] > 0:
                            sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                        else:
                            sku["projected_stockout_days"] = 99.0

        # Build / Verify Brand record exists
        brand = db.get(Brand, brand_id)
        if brand is None:
            brand = Brand(id=brand_id, name=new_state.get("brand_name") or display_name_from_brand_id(brand_id))
            db.add(brand)
            db.flush()
        else:
            brand.name = new_state.get("brand_name") or brand.name

        # Dynamically calculate blended ROAS for all customer segments based on matched campaigns
        for segment in new_state.get("customer_segments", []):
            segment_skus = segment.get("skus", [])
            seg_name = segment.get("name", "")
            
            matching_camps = []
            for c in new_state.get("campaigns", []):
                is_match = False
                if seg_name.lower() in c["campaign_name"].lower() or c["campaign_name"].lower() in seg_name.lower():
                    is_match = True
                for s in segment_skus:
                    if s.lower() in c["campaign_name"].lower() or c["campaign_name"].lower() in s.lower() or s in c.get("skus", []):
                        is_match = True
                        
                if is_match:
                    matching_camps.append(c)
                    
            if matching_camps:
                tot_spend = sum(c.get("spend", 0) for c in matching_camps)
                tot_rev = sum(c.get("spend", 0) * c.get("roas_on_placed_orders", 0.0) for c in matching_camps)
                tot_delivered_rev = sum(c.get("spend", 0) * c.get("roas_on_delivered_orders", 0.0) for c in matching_camps)
                segment["roas_on_placed_orders"] = round(tot_rev / max(tot_spend, 1), 2) if tot_spend > 0 else 0.0
                segment["roas_on_delivered_orders"] = round(tot_delivered_rev / max(tot_spend, 1), 2) if tot_spend > 0 else 0.0
                print(f"   📊 [ROAS Sync] Segment '{seg_name}' matched {len(matching_camps)} campaigns. Blended Placed ROAS = {segment['roas_on_placed_orders']}x", flush=True)
            else:
                segment["roas_on_placed_orders"] = 0.0
                segment["roas_on_delivered_orders"] = 0.0

        # Dynamically calculate blended spend growth for all SKUs based on matched campaigns
        for sku in new_state.get("skus", []):
            sku_name = sku.get("name", "")
            matching_camps = []
            for c in new_state.get("campaigns", []):
                is_match = False
                if sku_name.lower() in c["campaign_name"].lower() or c["campaign_name"].lower() in sku_name.lower() or sku_name in c.get("skus", []):
                    is_match = True
                if is_match:
                    matching_camps.append(c)
                    
            if matching_camps:
                tot_spend = sum(c.get("spend", 0) for c in matching_camps)
                if tot_spend > 0:
                    weighted_growth = sum(c.get("spend", 0) * c.get("spend_growth_percent", 0.0) for c in matching_camps) / tot_spend
                    sku["spend_growth_percent"] = round(weighted_growth, 2)
                else:
                    sku["spend_growth_percent"] = 0.0
                print(f"   📈 [Spend Growth Sync] SKU '{sku_name}' matched {len(matching_camps)} campaigns. Blended WoW Spend Growth = {sku['spend_growth_percent']}%", flush=True)
            else:
                sku["spend_growth_percent"] = 0.0

        self.update_state(state="PROGRESS", meta={"step": "Creating Business Snapshot"})
        
        # Save Business Snapshot record
        snapshot = BusinessSnapshot(
            brand_id=brand_id,
            upload_source=upload_source if not is_multi_sheet else "unified_workbook",
            snapshot_version=next_version,
            is_baseline=is_baseline,
            state=new_state,
        )
        db.add(snapshot)
        db.flush()
        ensure_default_goals(db, brand_id)
        upsert_unit_economics_from_state(db, brand_id, new_state)
        persist_connector_events(db, brand_id, snapshot, new_state)
        
        self.update_state(state="PROGRESS", meta={"step": "Running Monitoring & Verification Engine"})
        
        # Run Monitoring Engine for comparison verification
        previous_state = previous_snapshot.state if previous_snapshot else None
        MonitoringEngine.verify_actions(previous_state, new_state, db_session=db)
        
        self.update_state(state="PROGRESS", meta={"step": "Running Signal Detection Engine"})
        
        # Run Signal Detection Engine on current state
        signals = SignalDetectionEngine.detect(new_state, freshness=freshness)
        
        print("\n" + "=" * 80, flush=True)
        print("🧠 [DECISION ENGINE] EVALUATING HEURISTICS AND ONTOLOGICAL SIGNALS...", flush=True)
        print("=" * 80, flush=True)

        self.update_state(state="PROGRESS", meta={"step": "Enriching and generating decisions"})
        
        # Generate decisions and persist to DB
        decisions_created = 0
        for signal in signals:
            print(f"\n⚡ [SIGNAL FOUND] {signal.title}", flush=True)
            print(f"   Severity: {signal.severity.upper()} | Confidence: {int(signal.confidence_score * 100)}%", flush=True)
            print(f"   Impact: {signal.impact_label}", flush=True)
            print(f"   Heuristic Rule: {signal.rule}", flush=True)
            
            # Invoke LLM enrichment layer
            try:
                enriched = LLMEnrichmentService.enrich_signal(signal)
            except Exception as llm_exc:
                print(f"⚠️ [LLM LAYER] Error invoking enrichment service: {llm_exc}", flush=True)
                enriched = {}

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
                state="pending",
                timeline=[
                    {
                        "id": f"evt_init_{snapshot.id}",
                        "time": datetime.now().strftime("%I:%M %p"),
                        "title": f"{signal.issue_type} Detected",
                        "description": enriched.get("explanation", signal.explanation),
                        "kind": "signal"
                    }
                ],
                rule=signal.rule,
                explanation=enriched.get("explanation", signal.explanation),
                
                # UI Rich fields & ontology
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
            decisions_created += 1
            
        print("\n" + "=" * 80, flush=True)
        print(f"🎯 [DECISION PERSISTENCE] Successfully stored {decisions_created} decisions to PostgreSQL.", flush=True)
        print("=" * 80 + "\n", flush=True)

        db.commit()
        
        # Clean up uploaded temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {
            "status": "success",
            "snapshot_id": snapshot.id,
            "snapshot_version": snapshot.snapshot_version,
            "is_baseline": snapshot.is_baseline,
            "decisions_created": decisions_created,
            "message": "Baseline snapshot created. Upload again to enable monitoring." if is_baseline else "Snapshot created and monitoring comparisons executed.",
        }
        
    except Exception as e:
        db.rollback()
        # Clean up temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise e
    finally:
        db.close()
