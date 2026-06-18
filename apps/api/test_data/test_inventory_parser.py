"""Regression tests for operator inventory workbook parsing."""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tasks import (  # noqa: E402
    align_inventory_headers,
    compute_blended_aov,
    is_inventory_placeholder_row,
    resolve_inventory_sku_column,
)
from app.rules import SignalDetectionEngine, is_inventory_placeholder_sku  # noqa: E402


def test_resolve_inventory_sku_column_prefers_variant_code_header():
    columns = ["sr no.", "type", "color", "size", "code", "usable stock", "average"]
    assert resolve_inventory_sku_column(columns) == "code"


def test_placeholder_row_detection():
    assert is_inventory_placeholder_row("Code", "Type") is True
    assert is_inventory_placeholder_row("1010Red6", "Escobar") is False


def test_unigo_workbook_skips_code_header_row():
    workbook = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "unigo final.xlsx")
    )
    if not os.path.exists(workbook):
        return

    inv_df = pd.read_excel(workbook, sheet_name="inventory")
    inv_df = align_inventory_headers(inv_df)
    inv_df.columns = [str(c).strip().lower() for c in inv_df.columns]
    sku_col = resolve_inventory_sku_column(list(inv_df.columns))
    type_col = "type" if "type" in inv_df.columns else None

    parsed_codes = []
    for _, row in inv_df.iterrows():
        sku_code = str(row[sku_col]).strip()
        product_name = str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else sku_code
        if is_inventory_placeholder_row(sku_code, product_name):
            continue
        parsed_codes.append(sku_code.lower())

    assert "code" not in parsed_codes


def test_unigo_brand_aov_uses_valid_revenue_rows_only():
    workbook = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "unigo final.xlsx")
    )
    if not os.path.exists(workbook):
        return

    shopify = pd.read_excel(workbook, sheet_name="shopify")
    revenue = pd.to_numeric(shopify[" Total Amt "], errors="coerce")
    blended = compute_blended_aov(revenue)
    assert blended is not None
    # Old bug divided by all rows (661), including cancelled/zero-revenue rows.
    assert blended != round(float(revenue.sum()) / len(revenue), 2)
    assert revenue.notna().sum() < len(revenue)


def test_inventory_risk_skips_placeholder_sku():
    state = {
        "average_order_value": 3482.5,
        "skus": [
            {
                "sku_id": "Code",
                "name": "Code",
                "inventory_left": 0,
                "daily_velocity": 0.0,
                "projected_stockout_days": 0.0,
                "spend_growth_percent": 0.0,
            }
        ],
        "campaigns": [],
        "customer_segments": [],
    }
    signals = SignalDetectionEngine.detect(state, freshness=1.0)
    inventory_signals = [signal for signal in signals if signal.signal_type == "InventoryRisk"]
    assert inventory_signals == []
    assert is_inventory_placeholder_sku(state["skus"][0]) is True


if __name__ == "__main__":
    test_resolve_inventory_sku_column_prefers_variant_code_header()
    test_placeholder_row_detection()
    test_unigo_workbook_skips_code_header_row()
    test_unigo_brand_aov_uses_valid_revenue_rows_only()
    test_inventory_risk_skips_placeholder_sku()
    print("inventory parser tests passed")