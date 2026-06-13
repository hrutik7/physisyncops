import os
import pandas as pd
import json
import re
import math
from typing import Any
from datetime import datetime, timezone

from .celery_app import celery_app
from .db import SessionLocal
from .models import BusinessSnapshot, Decision, Brand, UnitEconomics
from .rules import SignalDetectionEngine, DataFreshnessValidator
from .verification import MonitoringEngine
from .llm import LLMEnrichmentService
from .operating_layer import (
    ensure_default_goals,
    ensure_intervention,
    ensure_scorecard,
    persist_connector_events,
    persist_ontology,
    upsert_unit_economics_from_state,
    carry_forward_active_decisions,
)


def display_name_from_brand_id(brand_id: str) -> str:
    clean = re.sub(r"^brand[_-]?", "", brand_id).replace("_", " ").replace("-", " ").strip()
    return clean.title() if clean else "Uploaded Brand"


def empty_uploaded_state(brand_id: str) -> dict[str, Any]:
    return {
        "brand_name": display_name_from_brand_id(brand_id),
        "skus": [],
        "campaigns": [],
        "customer_segments": [],
        "creatives": [],
    }


def calculate_sku_margin_params(db, brand_id: str, sku_name_or_id: str, sku_aov: float):
    # Load Unit Economics from DB
    econ_records = db.query(UnitEconomics).filter(UnitEconomics.brand_id == brand_id).all()
    econ_by_sku = {e.sku_id.lower(): e for e in econ_records if e.sku_id}
    brand_econ = next((e for e in econ_records if not e.sku_id), None)

    def get_sku_economics(sku_name_or_id: str):
        if not sku_name_or_id:
            return brand_econ
        key = sku_name_or_id.lower()
        econ = econ_by_sku.get(key)
        if not econ:
            clean_key = re.sub(r"^sku-", "", key)
            econ = econ_by_sku.get(clean_key)
        if not econ:
            econ = econ_by_sku.get(f"sku-{clean_key}" if "clean_key" in locals() else f"sku-{key}")
        if not econ:
            econ = brand_econ
        return econ

    econ = get_sku_economics(sku_name_or_id)
    sku_aov = max(sku_aov or 500.0, 1.0)
    if econ and (econ.shipping_cost > 0 or econ.rto_cost > 0 or econ.packaging_cost > 0):
        shipping = econ.shipping_cost
        pkg = econ.packaging_cost
        gw = econ.payment_gateway_cost
        rto_shipping = econ.rto_cost
        gm = econ.gross_margin_percent
        
        cm_pre = gm - ((shipping + pkg + gw) / sku_aov) * 100
        impact_factor = (shipping + rto_shipping + pkg) / sku_aov
        waste_mult = (shipping + rto_shipping + pkg) / sku_aov
        
        return round(cm_pre, 2), round(impact_factor, 3), round(waste_mult, 3)
    else:
        return 28.0, 0.65, 0.40


def normalize_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def normalize_sheet_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def find_col(columns, *needles: str):
    normalized = {column: normalize_header(column) for column in columns}
    for needle in needles:
        clean_needle = normalize_header(needle)
        for column, clean_column in normalized.items():
            if clean_column == clean_needle:
                return column
    for needle in needles:
        clean_needle = normalize_header(needle)
        for column, clean_column in normalized.items():
            if clean_needle in clean_column:
                return column
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def safe_series_sum(series: pd.Series, default: float = 0.0) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return default
    return safe_float(values.sum(), default)


def safe_series_mean(series: pd.Series, default: float = 0.0) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return default
    return safe_float(values.mean(), default)


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else 0.0
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def workbook_has_rto_status_sheet(xls: pd.ExcelFile, sheet_names: list[str]) -> tuple[bool, str | None]:
    status_aliases = ("status", "delivery status", "fulfillment status", "rto", "returned", "undelivered")
    for sheet_name in sheet_names:
        if not any(alias in normalize_sheet_name(sheet_name) for alias in ("shopify", "order")):
            continue
        frame = pd.read_excel(xls, sheet_name=sheet_name, nrows=1)
        matched_col = find_col([str(c).strip().lower() for c in frame.columns], *status_aliases)
        if matched_col:
            return True, f"shopify_orders.{matched_col}"
    return False, None


@celery_app.task(name="app.tasks.process_excel_upload_task", bind=True)
def process_excel_upload_task(self, brand_id: str, upload_source: str, mapping: dict[str, str], file_path: str) -> dict:
    self.update_state(state="PROGRESS", meta={"step": "Parsing Excel workbook sheets"})
    
    db = SessionLocal()
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at {file_path}")
            
        def calculate_sku_margin_params_local(sku_name_or_id: str, sku_aov: float):
            return calculate_sku_margin_params(db, brand_id, sku_name_or_id, sku_aov)
            
        # Load sheets
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        # Fetch the previous snapshot if any
        previous_snapshot = db.query(BusinessSnapshot).filter(
            BusinessSnapshot.brand_id == brand_id
        ).order_by(BusinessSnapshot.snapshot_version.desc()).first()
        
        next_version = 1 if previous_snapshot is None else previous_snapshot.snapshot_version + 1
        is_baseline = previous_snapshot is None
        
        # Initialize real uploads from a clean state so demo SKUs/campaigns never leak into decisions.
        if previous_snapshot is not None:
            new_state = json.loads(json.dumps(previous_snapshot.state))
        else:
            new_state = empty_uploaded_state(brand_id)
            
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

        if is_custom_upload or previous_snapshot is None:
            print("🚀 [DYNAMIC INGESTION] Real workbook upload detected! Clearing mock data templates.", flush=True)
            new_state["brand_name"] = display_name_from_brand_id(brand_id)
            new_state["skus"] = []
            new_state["campaigns"] = []
            new_state["customer_segments"] = []
        
        # Check if it's a multi-sheet workbook
        is_multi_sheet = len(sheet_names) > 1 or any(s in sheet_names for s in ["shopify_orders", "meta_ads", "inventory"])
        
        freshness = 1.0 # Default full freshness
        rto_data_present = False
        
        print("\n" + "=" * 80, flush=True)
        print(f"🚀 [DYNAMIC INGESTION] STARTED CALCULATIONS FOR BRAND: {brand_id}", flush=True)
        print(f"   📂 File Path: {file_path}", flush=True)
        print(f"   📋 Sheets found: {sheet_names}", flush=True)
        print(f"   ⚙️ Snapshot Version: v{next_version} (is_baseline={is_baseline})", flush=True)
        print("=" * 80 + "\n", flush=True)

        if is_multi_sheet:
            self.update_state(state="PROGRESS", meta={"step": "Ingesting multi-sheet workbook"})
            sheets = {s: pd.read_excel(xls, sheet_name=s) for s in sheet_names}
            sheet_lookup = {normalize_sheet_name(s): s for s in sheet_names}

            def resolve_sheet(*aliases: str):
                for alias in aliases:
                    clean_alias = normalize_sheet_name(alias)
                    if clean_alias in sheet_lookup:
                        return sheets[sheet_lookup[clean_alias]]
                for sheet_name in sheet_names:
                    clean_sheet = normalize_sheet_name(sheet_name)
                    if any(normalize_sheet_name(alias) in clean_sheet for alias in aliases):
                        return sheets[sheet_name]
                return None
            
            # --- 1. Parse inventory sheet ---
            # Columns: sku, stock_left, daily_velocity, reorder_level, projected_stockout_days
            inv_df = resolve_sheet("inventory", "stock")
            if inv_df is not None:
                print("🔍 [STEP 1/4] Processing 'inventory' sheet dynamically...", flush=True)
                
                # Align headers if the first few columns are Unnamed (e.g. from title rows)
                if any("unnamed" in str(c).lower() for c in inv_df.columns):
                    header_row_idx = None
                    for idx, row in inv_df.iterrows():
                        row_vals = [str(v).strip().lower() for v in row.values if v is not None]
                        if any(h in row_vals for h in ["sr no", "sr no.", "code", "opening stock", "usable stock"]):
                            header_row_idx = idx
                            break
                    if header_row_idx is not None:
                        inv_df.columns = [str(c).strip() for c in inv_df.iloc[header_row_idx]]
                        inv_df = inv_df.iloc[header_row_idx + 1:].reset_index(drop=True)

                inv_df.columns = [str(c).strip().lower() for c in inv_df.columns]
                
                sku_col = next((c for c in inv_df.columns if any(alias in c for alias in ["sku", "variant", "code", "item_code", "sku_code"])), None)
                stock_col = next((c for c in inv_df.columns if "usable" in c), None)
                if not stock_col:
                    stock_col = next((c for c in inv_df.columns if "stock" in c or "left" in c or "inventory" in c or "qty" in c or "available" in c), None)
                velocity_col = next((c for c in inv_df.columns if any(alias in c for alias in ["velocity", "daily", "average", "demand"])), None)
                reorder_col = next((c for c in inv_df.columns if any(alias in c for alias in ["reorder", "level", "threshold", "norms"])), None)
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
                            
                        if stock_col and pd.notna(row[stock_col]):
                            try:
                                sku["inventory_left"] = int(float(row[stock_col]))
                            except (ValueError, TypeError):
                                sku["inventory_left"] = 0
                        if velocity_col and pd.notna(row[velocity_col]):
                            try:
                                sku["daily_velocity"] = float(row[velocity_col])
                            except (ValueError, TypeError):
                                sku["daily_velocity"] = 0.0
                        if reorder_col and pd.notna(row[reorder_col]):
                            try:
                                sku["reorder_threshold"] = int(float(row[reorder_col]))
                            except (ValueError, TypeError):
                                sku["reorder_threshold"] = 0
                        
                        if stockout_col and pd.notna(row[stockout_col]):
                            try:
                                sku["projected_stockout_days"] = float(row[stockout_col])
                            except (ValueError, TypeError):
                                sku["projected_stockout_days"] = 99.0
                        elif sku["daily_velocity"] > 0:
                            sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                        
                        print(f"   📦 SKU '{sku_name}': Stock Left={sku['inventory_left']}, Daily Sales Velocity={sku['daily_velocity']} units/day -> Projected Stockout Days={sku['projected_stockout_days']}", flush=True)
                            
            # --- 2. Parse meta_ads sheet ---
            # Columns: campaign_name, creative_hook, daily_spend, roas, ctr_percent, frequency, cpa, status
            ads_df = resolve_sheet("meta_ads", "meta", "facebook_ads", "ads")
            if ads_df is not None:
                print("\n🔍 [STEP 2/4] Processing 'meta_ads' sheet dynamically...", flush=True)
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
                            campaign["spend"] = safe_series_sum(group[spend_col], campaign.get("spend", 0.0))
                            if prev_spend > 0:
                                campaign["spend_growth_percent"] = round(((campaign["spend"] - prev_spend) / prev_spend) * 100, 2)
                        if roas_col:
                            campaign["roas_on_placed_orders"] = safe_series_mean(group[roas_col], campaign.get("roas_on_placed_orders", 3.0))
                            campaign["roas_source"] = "Meta Ads Manager ('meta_ads' sheet)"
                        else:
                            campaign["roas_source"] = "default baseline"
                        if ctr_drop_col:
                            campaign["ctr_drop_percent"] = safe_series_mean(group[ctr_drop_col], campaign.get("ctr_drop_percent", 0.0))
                            campaign["ctr_drop_source"] = ctr_drop_col
                        if ctr_col:
                            prev_ctr = campaign.get("ctr", 0)
                            campaign["ctr"] = safe_series_mean(group[ctr_col], campaign.get("ctr", 0.0))
                            if has_prior_campaign and prev_ctr > 0 and not ctr_drop_col:
                                campaign["ctr_drop_percent"] = round(((prev_ctr - campaign["ctr"]) / prev_ctr) * 100, 2)
                                campaign["ctr_drop_source"] = "previous_snapshot_ctr"
                        if freq_col: campaign["frequency"] = safe_series_mean(group[freq_col], campaign.get("frequency", 2.5))
                        
                        print(f"   📢 Campaign '{camp_name_str}': Total Spend=Rs {campaign['spend']} (Growth={campaign['spend_growth_percent']}%), Placed ROAS={campaign['roas_on_placed_orders']}x, CTR={campaign['ctr']}%, Freq={campaign['frequency']}", flush=True)
                        
            # --- 3. Parse customer_signals sheet ---
            # Columns: sku, repeat_rate_percent, return_rate_percent, review_sentiment, cod_ratio_percent, prepaid_ratio_percent
            cust_df = resolve_sheet("customer_signals", "customer")
            if cust_df is not None:
                print("\n🔍 [STEP 3/4] Processing 'customer_signals' sheet dynamically...", flush=True)
                cust_df.columns = [str(c).strip().lower() for c in cust_df.columns]
                
                sku_col = next((c for c in cust_df.columns if "sku" in c or "variant" in c), None)
                repeat_col = next((c for c in cust_df.columns if "repeat" in c or "rate" in c), None)
                return_col = next((c for c in cust_df.columns if "return" in c or "rto" in c), None)
                if return_col is not None and len(cust_df) > 0:
                    rto_data_present = True
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
            orders_df = resolve_sheet("shopify_orders", "shopify", "orders")
            if orders_df is not None:
                print("\n🔍 [STEP 4/4] Processing 'shopify_orders' sheet dynamically...", flush=True)
                orders_df.columns = [str(c).strip().lower() for c in orders_df.columns]
                
                sku_col = find_col(orders_df.columns, "sku code", "sku", "variant", "item code")
                pm_col = find_col(orders_df.columns, "payment type", "payment method", "payment mode", "method")
                status_col = find_col(orders_df.columns, "status", "delivery status", "fulfillment status")
                rto_col = find_col(orders_df.columns, "rto", "returned", "undelivered") or status_col
                delivered_col = find_col(orders_df.columns, "delivered", "fulfilled") or status_col
                if rto_col is not None and delivered_col is not None and len(orders_df) > 0:
                    rto_data_present = True
                    new_state["rto_status_source"] = f"shopify_orders.{rto_col}"
                revenue_col = find_col(orders_df.columns, "total amt", "total amount", "revenue", "amount", "price")
                product_col = find_col(orders_df.columns, "name of the product", "product name", "product", "title")
                qty_col = find_col(orders_df.columns, "qty", "quantity", "units")
                order_date_col = find_col(orders_df.columns, "orders date", "order date", "date")
                cust_type_col = next((c for c in orders_df.columns if "customer_type" in c or "user_type" in c or "type" in c), None)
                cust_id_col = next((c for c in orders_df.columns if "customer" in c or "email" in c or "phone" in c or "user" in c), None)

                blended_aov = 1500.0
                if revenue_col and len(orders_df) > 0:
                    revenue_values = pd.to_numeric(orders_df[revenue_col], errors="coerce").dropna()
                    if len(revenue_values) > 0:
                        new_state["average_order_value"] = round(float(revenue_values.sum()) / len(orders_df), 2)
                        blended_aov = new_state["average_order_value"]

                # Calculate overall brand-level RTO fallback
                if delivered_col and rto_col:
                    delivered_mask = orders_df[delivered_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "DELIVERED", "FULFILLED"])
                    rto_mask = orders_df[rto_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "RTO", "RETURNED", "UNDELIVERED"])
                    total_delivered = int(delivered_mask.sum())
                    total_rto = int(rto_mask.sum())
                    total_resolved = total_delivered + total_rto
                    if total_resolved > 0:
                        new_state["brand_rto_rate"] = round((total_rto / total_resolved) * 100, 2)
                        print(f"   📈 Brand-level Blended RTO rate calculated: {new_state['brand_rto_rate']}%", flush=True)

                # Calculate overall brand-level repeat purchase rate
                brand_repeat_rate = 22.0
                if cust_type_col:
                    returning_orders = int(orders_df[cust_type_col].astype(str).str.lower().str.contains("returning|repeat").sum())
                    brand_repeat_rate = round((returning_orders / max(len(orders_df), 1)) * 100, 2)
                elif cust_id_col:
                    customer_order_counts = orders_df[cust_id_col].value_counts()
                    repeat_customers = int((customer_order_counts > 1).sum())
                    total_customers = int(customer_order_counts.nunique())
                    brand_repeat_rate = round((repeat_customers / max(total_customers, 1)) * 100, 2)
                new_state["brand_repeat_rate"] = brand_repeat_rate
                print(f"   📈 Brand-level Repeat Purchase Rate calculated: {brand_repeat_rate}%", flush=True)

                # State-level profitability map (Decision #5)
                if "state" in orders_df.columns and pm_col and status_col:
                    orders_df["is_cod"] = orders_df[pm_col].astype(str).str.upper().str.contains("COD|CASH")
                    orders_df["is_rto"] = orders_df[status_col].astype(str).str.upper().str.contains("RTO|RETURN")
                    
                    state_grp = orders_df.groupby("state")
                    state_list = []
                    for state_name, group in state_grp:
                        tot_ord = len(group)
                        if tot_ord > 5:
                            cod_cnt = int(group["is_cod"].sum())
                            rto_cnt = int(group["is_rto"].sum())
                            cod_pct = round((cod_cnt / tot_ord) * 100, 2)
                            rto_pct = round((rto_cnt / tot_ord) * 100, 2)
                            
                            deliv_rev = 0.0
                            if revenue_col:
                                deliv_mask = ~group[status_col].astype(str).str.upper().str.contains("RTO|RETURN|CANCEL")
                                deliv_rev = round(float(pd.to_numeric(group.loc[deliv_mask, revenue_col], errors="coerce").sum()), 2)
                                
                            state_list.append({
                                "state": str(state_name).strip(),
                                "total_orders": tot_ord,
                                "cod_pct": cod_pct,
                                "rto_pct": rto_pct,
                                "delivered_revenue": deliv_rev
                            })
                    new_state["state_profitability"] = state_list

                # Courier performance ranking (Decision #6)
                courier_col = find_col(orders_df.columns, "courier partner", "courier", "delivery partner", "carrier")
                transit_col = find_col(orders_df.columns, "no of days required", "transit days", "delivery days")
                if courier_col and status_col:
                    orders_df["is_rto"] = orders_df[status_col].astype(str).str.upper().str.contains("RTO|RETURN")
                    if transit_col:
                        orders_df["transit_days"] = pd.to_numeric(orders_df[transit_col].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
                    else:
                        orders_df["transit_days"] = None
                        
                    courier_grp = orders_df.groupby(courier_col)
                    courier_list = []
                    for courier_name, group in courier_grp:
                        tot_ord = len(group)
                        if tot_ord > 5:
                            rto_cnt = int(group["is_rto"].sum())
                            rto_pct = round((rto_cnt / tot_ord) * 100, 2)
                            avg_days = None
                            if "transit_days" in group.columns:
                                days_val = group["transit_days"].dropna()
                                if not days_val.empty:
                                    avg_days = round(float(days_val.mean()), 1)
                                    
                            courier_list.append({
                                "courier": str(courier_name).strip(),
                                "total_orders": tot_ord,
                                "rto_pct": rto_pct,
                                "avg_days": avg_days
                            })
                    new_state["courier_performance"] = courier_list

                if sku_col:
                    grouped = orders_df.groupby(sku_col)
                    for sku_name, group in grouped:
                        sku_name_str = str(sku_name).strip()
                        if not sku_name_str or sku_name_str.lower() == "nan":
                            continue
                            
                        # Calculate SKU-specific AOV
                        sku_aov = blended_aov
                        if revenue_col:
                            sku_rev = pd.to_numeric(group[revenue_col], errors="coerce").sum()
                            sku_orders_count = len(group)
                            sku_aov = round(float(sku_rev) / max(sku_orders_count, 1), 2) if sku_orders_count > 0 else blended_aov
                        
                        sku_entity = next((s for s in new_state.get("skus", []) if s["name"].lower() == sku_name_str.lower() or s["sku_id"].lower() == sku_name_str.lower() or s["sku_id"].lower() == f"sku-{sku_name_str.lower()}"), None)
                        if not sku_entity:
                            product_name = sku_name_str
                            if product_col and product_col in group.columns:
                                product_values = group[product_col].dropna()
                                if not product_values.empty:
                                    product_name = str(product_values.mode().iloc[0] if not product_values.mode().empty else product_values.iloc[0]).strip()
                            qty_values = pd.to_numeric(group[qty_col], errors="coerce").fillna(1) if qty_col and qty_col in group.columns else pd.Series([1] * len(group))
                            days_count = 1
                            if order_date_col and order_date_col in orders_df.columns:
                                date_values = pd.to_datetime(orders_df[order_date_col], errors="coerce").dropna()
                                if not date_values.empty:
                                    days_count = max((date_values.max().date() - date_values.min().date()).days + 1, 1)
                            velocity = round(safe_float(qty_values.sum()) / days_count, 2)
                            sku_entity = {
                                "sku_id": sku_name_str,
                                "name": product_name,
                                "inventory_left": 0,
                                "daily_velocity": velocity,
                                "reorder_threshold": 0,
                                "projected_stockout_days": 99.0,
                                "contribution_margin_after_rto": 25,
                                "average_order_value": sku_aov,
                                "spend_growth_percent": 0.0,
                                "campaigns": [],
                                "inventory_source": "missing_inventory_sheet"
                            }
                            new_state.setdefault("skus", []).append(sku_entity)
                        else:
                            sku_entity["average_order_value"] = sku_aov
                            
                            # Dynamically resolve product name for SKU from inventory
                            if product_col and product_col in group.columns:
                                product_values = group[product_col].dropna()
                                if not product_values.empty:
                                    product_name = str(product_values.mode().iloc[0] if not product_values.mode().empty else product_values.iloc[0]).strip()
                                    sku_entity["name"] = product_name
                            
                            # Dynamic velocity fallback
                            qty_values = pd.to_numeric(group[qty_col], errors="coerce").fillna(1) if qty_col and qty_col in group.columns else pd.Series([1] * len(group))
                            days_count = 1
                            if order_date_col and order_date_col in orders_df.columns:
                                date_values = pd.to_datetime(orders_df[order_date_col], errors="coerce").dropna()
                                if not date_values.empty:
                                    days_count = max((date_values.max().date() - date_values.min().date()).days + 1, 1)
                            velocity = round(safe_float(qty_values.sum()) / days_count, 2)
                            if sku_entity.get("daily_velocity", 0.0) <= 0.0:
                                sku_entity["daily_velocity"] = velocity

                        # Calculate SKU-specific repeat rate
                        sku_repeat_rate = brand_repeat_rate
                        if cust_type_col:
                            ret_orders = int(group[cust_type_col].astype(str).str.lower().str.contains("returning|repeat").sum())
                            sku_repeat_rate = round((ret_orders / max(len(group), 1)) * 100, 2)
                        elif cust_id_col:
                            cust_counts = group[cust_id_col].value_counts()
                            rep_custs = int((cust_counts > 1).sum())
                            tot_custs = int(cust_counts.nunique())
                            sku_repeat_rate = round((rep_custs / max(tot_custs, 1)) * 100, 2)

                        if "customer_segments" not in new_state or not isinstance(new_state["customer_segments"], list):
                            new_state["customer_segments"] = []
                            
                        segment = next((s for s in new_state["customer_segments"] if s["name"].lower() == sku_name_str.lower()), None)
                        
                        # Calculate COD ratios
                        cod_ratio = 50.0
                        prepaid_ratio = 50.0
                        if pm_col:
                            cod_count = int(group[pm_col].astype(str).str.upper().str.contains("COD|CASH").sum())
                            placed_count = len(group)
                            cod_ratio = round((cod_count / max(placed_count, 1)) * 100, 2)
                            prepaid_ratio = 100 - cod_ratio

                        # Calculate RTO rate from order status/delivery status
                        rto_rate_on_delivered = round(cod_ratio * 0.38, 2)
                        if delivered_col and rto_col:
                            delivered_mask = group[delivered_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "DELIVERED", "FULFILLED"])
                            rto_mask = group[rto_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "RTO", "RETURNED", "UNDELIVERED"])
                            total_del = int(delivered_mask.sum())
                            total_r = int(rto_mask.sum())
                            if total_del + total_r > 0:
                                rto_rate_on_delivered = round((total_r / (total_del + total_r)) * 100, 2)

                        product_name = sku_name_str
                        if product_col and product_col in group.columns:
                            product_values = group[product_col].dropna()
                            if not product_values.empty:
                                product_name = str(product_values.mode().iloc[0] if not product_values.mode().empty else product_values.iloc[0]).strip()

                        if not segment:
                            segment = {
                                "segment_id": f"seg_{sku_name_str.lower().replace(' ', '_')}",
                                "name": product_name,
                                "prepaid_ratio": prepaid_ratio,
                                "cod_ratio": cod_ratio,
                                "repeat_rate": sku_repeat_rate,
                                "return_rate": rto_rate_on_delivered,
                                "rto_rate_on_delivered": rto_rate_on_delivered,
                                "average_order_value": sku_aov,
                                "skus": [sku_name_str]
                            }
                            new_state["customer_segments"].append(segment)
                        else:
                            segment["average_order_value"] = sku_aov
                            segment["repeat_rate"] = sku_repeat_rate
                            segment["cod_ratio"] = cod_ratio
                            segment["prepaid_ratio"] = prepaid_ratio
                            segment["rto_rate_on_delivered"] = rto_rate_on_delivered
                            segment["return_rate"] = rto_rate_on_delivered
                            segment["name"] = product_name

                        for campaign in new_state.get("campaigns", []):
                            if sku_name_str.lower() in campaign["campaign_name"].lower() or campaign["campaign_name"].lower() in sku_name_str.lower():
                                placed_count = len(group)
                                cod_count = int(group[pm_col].astype(str).str.upper().str.contains("COD|CASH").sum()) if pm_col else 0
                                campaign["cod_order_count"] = cod_count
                                campaign["cod_ratio"] = round((cod_count / max(placed_count, 1)) * 100, 2)
                                delivered_count = int(group[delivered_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "DELIVERED", "FULFILLED"]).sum()) if delivered_col else placed_count
                                rto_count = int(group[rto_col].astype(str).str.upper().isin(["1", "TRUE", "YES", "RTO", "RETURNED", "UNDELIVERED"]).sum()) if rto_col else 0
                                campaign["placed_orders_attributed"] = placed_count
                                campaign["delivered_orders_attributed"] = delivered_count
                                campaign["rto_count_attributed"] = rto_count
                                resolved_orders = campaign["delivered_orders_attributed"] + campaign["rto_count_attributed"]
                                if resolved_orders > 0:
                                    campaign["rto_rate_attributed"] = round((campaign["rto_count_attributed"] / resolved_orders) * 100, 2)
                                
                                print(f"   🛒 Shopify Orders matching campaign '{campaign['campaign_name']}': Total={placed_count}, COD Orders={cod_count} (COD Ratio={campaign['cod_ratio']}%) -> Realized Attributed RTO rate={campaign['rto_rate_attributed']}%", flush=True)
                                    
            # Recalculate stockout days and contribution margins based on returned RTO rates
            print("\n🔄 [RECALCULATING DERIVED METRICS] Week-over-week stockout trends and COD contribution margins...", flush=True)
            for sku in new_state.get("skus", []):
                if sku["daily_velocity"] > 0:
                    sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                else:
                    sku["projected_stockout_days"] = 99.0
                    
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
                rto_col = next((c for c in df_canonical.columns if "rto" in c or "returned" in c or "undelivered" in c), None)
                delivered_col = next((c for c in df_canonical.columns if "delivered" in c or "fulfilled" in c), None)
                if rto_col is not None and delivered_col is not None and len(df_canonical) > 0:
                    rto_data_present = True
                    new_state["rto_status_source"] = f"shopify_orders.{rto_col}"
                revenue_col = next((c for c in df_canonical.columns if c in {"revenue", "total", "amount", "price", "order_value"}), None)
                blended_aov = 1500.0
                if revenue_col and len(df_canonical) > 0:
                    revenue_values = pd.to_numeric(df_canonical[revenue_col], errors="coerce").dropna()
                    if len(revenue_values) > 0:
                        new_state["average_order_value"] = round(float(revenue_values.sum()) / len(df_canonical), 2)
                        blended_aov = new_state["average_order_value"]

                # Calculate overall brand RTO rate for single sheet
                blended_cod_ratio = 40.0
                if "cod_orders" in df_canonical.columns:
                    cod_col = df_canonical["cod_orders"]
                    cod_count = int(cod_col.astype(str).str.upper().str.contains("COD|CASH").sum())
                    blended_cod_ratio = round((cod_count / max(len(df_canonical), 1)) * 100, 2)
                new_state["brand_rto_rate"] = round(blended_cod_ratio * 0.38, 2)

                # Calculate repeat rate from customer type or customer id
                cust_type_col = next((c for c in df_canonical.columns if "customer_type" in c or "user_type" in c or "type" in c), None) or next((c for c in df.columns if "customer_type" in c or "user_type" in c or "type" in c), None)
                cust_id_col = next((c for c in df_canonical.columns if "customer" in c or "email" in c or "phone" in c or "user" in c), None) or next((c for c in df.columns if "customer" in c or "email" in c or "phone" in c or "user" in c), None)
                
                brand_repeat_rate = 22.0
                df_to_use = df_canonical if (cust_type_col in df_canonical.columns or cust_id_col in df_canonical.columns) else df
                col_type = cust_type_col if cust_type_col in df_to_use.columns else None
                col_id = cust_id_col if cust_id_col in df_to_use.columns else None

                if col_type:
                    returning_orders = int(df_to_use[col_type].astype(str).str.lower().str.contains("returning|repeat").sum())
                    brand_repeat_rate = round((returning_orders / max(len(df_to_use), 1)) * 100, 2)
                elif col_id:
                    customer_order_counts = df_to_use[col_id].value_counts()
                    repeat_customers = int((customer_order_counts > 1).sum())
                    total_customers = int(customer_order_counts.nunique())
                    brand_repeat_rate = round((repeat_customers / max(total_customers, 1)) * 100, 2)
                new_state["brand_repeat_rate"] = brand_repeat_rate

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
                        
                        # Calculate SKU-specific AOV
                        sku_aov = blended_aov
                        if revenue_col:
                            sku_rev = pd.to_numeric(group[revenue_col], errors="coerce").sum()
                            sku_aov = round(float(sku_rev) / max(order_count, 1), 2)

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
                                "average_order_value": sku_aov,
                                "spend_growth_percent": 18.0,  # Force elevated spend growth to trigger stockout risk dynamically
                                "campaigns": []
                            }
                            new_state["skus"].append(sku)
                        else:
                            sku["daily_velocity"] = velocity
                            sku["average_order_value"] = sku_aov
                            if sku["daily_velocity"] > 0:
                                sku["projected_stockout_days"] = round(sku["inventory_left"] / sku["daily_velocity"], 1)
                        
                        # Calculate SKU-specific repeat rate
                        sku_repeat_rate = brand_repeat_rate
                        group_orig = df_to_use.loc[group.index]
                        if col_type:
                            ret_orders = int(group_orig[col_type].astype(str).str.lower().str.contains("returning|repeat").sum())
                            sku_repeat_rate = round((ret_orders / max(len(group_orig), 1)) * 100, 2)
                        elif col_id:
                            cust_counts = group_orig[col_id].value_counts()
                            rep_custs = int((cust_counts > 1).sum())
                            tot_custs = int(cust_counts.nunique())
                            sku_repeat_rate = round((rep_custs / max(tot_custs, 1)) * 100, 2)

                        # Find or create customer segment
                        segment = next((s for s in new_state.get("customer_segments", []) if s["name"].lower() == sku_name_str.lower()), None)
                        if not segment:
                            segment = {
                                "segment_id": f"seg_{sku_name_str.lower().replace(' ', '_')}",
                                "name": sku_name_str,
                                "prepaid_ratio": prepaid_ratio,
                                "cod_ratio": cod_ratio,
                                "repeat_rate": sku_repeat_rate,
                                "return_rate": round(cod_ratio * 0.15, 2),
                                "rto_rate_on_delivered": rto_rate_on_delivered,
                                "average_order_value": sku_aov,
                                "skus": [sku_name_str]
                            }
                            new_state["customer_segments"].append(segment)
                        else:
                            segment["cod_ratio"] = cod_ratio
                            segment["prepaid_ratio"] = prepaid_ratio
                            segment["rto_rate_on_delivered"] = rto_rate_on_delivered
                            segment["repeat_rate"] = sku_repeat_rate
                            segment["average_order_value"] = sku_aov

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
                        roas_src = "Shopify orders matching campaign name" if revenue_sum > 0 else "default baseline"
                        if not campaign:
                            campaign = {
                                "campaign_id": camp_id_str,
                                "campaign_name": camp_id_str,
                                "spend": spend,
                                "spend_growth_percent": 5.0,
                                "roas_on_placed_orders": roas,
                                "roas_source": roas_src,
                                "roas_on_delivered_orders": roas,
                                "frequency": 1.8,
                                "ctr_drop_percent": 0.0,
                                "ctr": 1.5,
                                "cod_order_count": cod_count,
                                "cod_ratio": cod_ratio,
                                "placed_orders_attributed": placed_count,
                                "rto_count_attributed": 0,
                                "delivered_orders_attributed": placed_count,
                                "rto_rate_attributed": rto_pct,
                                "contribution_margin_after_rto": 25,
                                "skus": [sku_name_str] if sku_name_str else []
                            }
                            new_state["campaigns"].append(campaign)
                        else:
                            campaign["spend"] = spend
                            campaign["roas_on_placed_orders"] = roas
                            campaign["roas_source"] = roas_src
                            campaign["cod_order_count"] = cod_count
                            campaign["cod_ratio"] = cod_ratio
                            campaign["rto_rate_attributed"] = rto_pct
                            campaign["placed_orders_attributed"] = placed_count
                            
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

        # Recalculate campaign level metrics (ROAS delivered, CAC, and CM after RTO) for all campaigns
        blended_aov = new_state.get("average_order_value") or 1500.0
        for campaign in new_state.get("campaigns", []):
            rto_pct = campaign.get("rto_rate_attributed", 0.0)
            if not rto_data_present:
                rto_pct = 0.0
                campaign["rto_rate_attributed"] = 0.0
            else:
                if rto_pct == 0.0:
                    rto_pct = new_state.get("brand_rto_rate", 31.0)
                    campaign["rto_rate_attributed"] = rto_pct
            
            campaign_skus = campaign.get("skus", [])
            primary_sku = campaign_skus[0] if campaign_skus else ""
            
            sku_entity = next((s for s in new_state.get("skus", []) if s["name"].lower() == primary_sku.lower()), None)
            sku_aov = sku_entity.get("average_order_value") if sku_entity else blended_aov
            if not sku_aov:
                sku_aov = blended_aov
            
            cm_pre, rto_impact_factor, waste_mult = calculate_sku_margin_params_local(primary_sku or campaign.get("campaign_name", ""), sku_aov)
            
            campaign["roas_on_delivered_orders"] = round(campaign["roas_on_placed_orders"] * (1 - (rto_pct / 100)), 2)
            campaign["contribution_margin_after_rto"] = max(int(cm_pre - (rto_pct * rto_impact_factor)), 5)
            campaign["operational_waste_multiplier"] = waste_mult
            
            # Recalculate CAC
            placed_orders = campaign.get("placed_orders_attributed", 0)
            delivered_orders = campaign.get("delivered_orders_attributed", 0)
            spend = campaign.get("spend", 0)
            
            if spend > 0 and placed_orders > 0:
                campaign["placed_cac"] = round(spend / placed_orders, 2)
            else:
                campaign["placed_cac"] = round(sku_aov / max(campaign["roas_on_placed_orders"], 0.1), 2)
                
            if spend > 0 and delivered_orders > 0:
                campaign["realized_cac"] = round(spend / delivered_orders, 2)
            else:
                campaign["realized_cac"] = round(sku_aov / max(campaign["roas_on_delivered_orders"], 0.1), 2)
            
            # Default roas_source if not set
            if "roas_source" not in campaign:
                if campaign.get("roas_on_placed_orders", 0) > 0 and campaign.get("roas_on_placed_orders", 0) != 3.0:
                    campaign["roas_source"] = "Meta Ads Manager ('meta_ads' sheet)"
                else:
                    campaign["roas_source"] = "default baseline"
            
            print(f"   📈 Dynamic CM for '{campaign['campaign_name']}': ROAS On Placed orders {campaign['roas_on_placed_orders']}x compressed to ROAS On Delivered orders {campaign['roas_on_delivered_orders']}x. Margin compressed to {campaign['contribution_margin_after_rto']}% (using CM_pre={cm_pre}%, RTO_factor={rto_impact_factor}). Placed CAC = Rs {campaign['placed_cac']}, Realized CAC = Rs {campaign['realized_cac']}", flush=True)

        # Build / Verify Brand record exists
        brand = db.get(Brand, brand_id)
        if brand is None:
            brand = Brand(id=brand_id, name=new_state.get("brand_name") or display_name_from_brand_id(brand_id))
            db.add(brand)
            db.flush()
        else:
            brand.name = new_state.get("brand_name") or brand.name

        # Dynamically calculate blended ROAS for all customer segments based on matched campaigns
        blended_aov = new_state.get("average_order_value") or 1500.0
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

            # Calculate Segment level AOV
            seg_aov = segment.get("average_order_value") or blended_aov
            segment["average_order_value"] = seg_aov

            # Calculate Placed and Realized CAC for segment
            placed_roas = segment.get("roas_on_placed_orders", 3.0)
            delivered_roas = segment.get("roas_on_delivered_orders", 2.0)
            segment["placed_cac"] = round(seg_aov / max(placed_roas, 0.1), 2)
            segment["realized_cac"] = round(seg_aov / max(delivered_roas, 0.1), 2)

            # Get SKU-level economics for the segment
            primary_sku = segment_skus[0] if segment_skus else seg_name
            cm_pre, rto_impact_factor, waste_mult = calculate_sku_margin_params_local(primary_sku, seg_aov)
            segment["operational_waste_multiplier"] = waste_mult

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

        if not rto_data_present:
            rto_data_present, rto_status_source = workbook_has_rto_status_sheet(xls, sheet_names)
            if rto_data_present and rto_status_source:
                new_state["rto_status_source"] = rto_status_source
                print(f"   ✅ RTO/delivery status source detected from workbook schema: {rto_status_source}", flush=True)

        new_state["rto_data_present"] = rto_data_present
        new_state = sanitize_json_value(new_state)
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

        if previous_snapshot:
            carry_forward_active_decisions(db, brand_id, previous_snapshot.id, snapshot.id)

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
