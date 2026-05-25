import { MappingSuggestion } from "./types";

const CANONICAL_COLUMNS: Record<string, string[]> = {
  revenue: ["gross_sales", "total_sales", "revenue", "sales_amount", "net_revenue"],
  rto_count: ["rto", "returned_orders", "undelivered", "return_count", "rto_orders"],
  campaign_id: ["campaign_id", "ad_set_id", "campaign_name", "utm_campaign"],
  sku_id: ["sku", "product_id", "item_code", "variant_id", "sku_id"],
  cod_orders: ["cod_count", "cash_orders", "cod", "cod_orders"],
  delivered_orders: ["delivered", "fulfilled", "confirmed_delivered", "delivered_orders"],
  order_status: ["status", "fulfillment_status", "delivery_status", "shipment_status"],
  ad_spend: ["spend", "amount_spent", "campaign_spend", "cost"],
  creative_id: ["creative_id", "ad_id", "asset_id", "creative_name"],
  inventory_left: ["inventory", "stock", "available", "inventory_left", "qty_available"]
};

const REQUIRED_FIELDS = new Set(["revenue", "campaign_id", "sku_id", "delivered_orders"]);

function normalizeColumn(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function similarity(a: string, b: string) {
  if (a === b) return 1;
  if (a.includes(b) || b.includes(a)) return 0.82;

  const aParts = new Set(a.split("_"));
  const bParts = new Set(b.split("_"));
  const overlap = Array.from(aParts).filter((part) => bParts.has(part)).length;
  return overlap / Math.max(aParts.size, bParts.size, 1);
}

export function suggestMappings(uploadedColumns: string[]): MappingSuggestion[] {
  const normalizedUploads = uploadedColumns.map((column) => ({
    raw: column,
    normalized: normalizeColumn(column)
  }));

  return Object.entries(CANONICAL_COLUMNS).map(([canonicalField, aliases]) => {
    const ranked = normalizedUploads
      .map((upload) => {
        const confidence = Math.max(...aliases.map((alias) => similarity(upload.normalized, normalizeColumn(alias))));
        return { column: upload.raw, confidence };
      })
      .sort((a, b) => b.confidence - a.confidence);

    const best = ranked[0];

    return {
      canonicalField,
      uploadedColumn: best && best.confidence >= 0.42 ? best.column : null,
      confidence: best?.confidence ?? 0,
      alternatives: ranked.slice(1, 4).map((item) => item.column),
      required: REQUIRED_FIELDS.has(canonicalField)
    };
  });
}
