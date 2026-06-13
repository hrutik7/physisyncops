from difflib import SequenceMatcher

CANONICAL_COLUMNS: dict[str, list[str]] = {
    "revenue": ["gross_sales", "total_sales", "revenue", "sales_amount", "total_amt", "total_amount", "amount"],
    "rto_count": ["rto", "returned_orders", "undelivered", "return_count", "status"],
    "campaign_id": ["campaign_id", "ad_set_id", "campaign_name", "campaign"],
    "sku_id": ["sku", "sku_code", "product_id", "item_code", "variant_id"],
    "cod_orders": ["cod_count", "cash_orders", "cod", "payment_type", "payment_method"],
    "delivered_orders": ["delivered", "fulfilled", "confirmed_delivered", "status"],
    "order_status": ["status", "delivery_status", "fulfillment_status"],
    "ad_spend": ["spend", "amount_spent", "amount_spent_inr", "campaign_spend"],
}

REQUIRED_FIELDS = {"revenue", "campaign_id", "sku_id", "delivered_orders"}


def normalize_column(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def score(uploaded: str, alias: str) -> float:
    uploaded = normalize_column(uploaded)
    alias = normalize_column(alias)
    if uploaded == alias:
        return 1.0
    if uploaded in alias or alias in uploaded:
        return 0.82
    return SequenceMatcher(None, uploaded, alias).ratio()


def suggest_mappings(columns: list[str]) -> list[dict]:
    suggestions = []
    for canonical, aliases in CANONICAL_COLUMNS.items():
        ranked = sorted(
            (
                {"column": column, "confidence": max(score(column, alias) for alias in aliases)}
                for column in columns
            ),
            key=lambda item: item["confidence"],
            reverse=True,
        )
        best = ranked[0] if ranked else None
        suggestions.append(
            {
                "canonical_field": canonical,
                "uploaded_column": best["column"] if best and best["confidence"] >= 0.42 else None,
                "confidence": best["confidence"] if best else 0,
                "alternatives": [item["column"] for item in ranked[1:4]],
                "required": canonical in REQUIRED_FIELDS,
            }
        )
    return suggestions
