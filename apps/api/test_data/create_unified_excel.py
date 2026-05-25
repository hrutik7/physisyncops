import pandas as pd
import os

# Create folder for test data
os.makedirs("test_data", exist_ok=True)

# 1. shopify_orders sheet
orders_data = {
    "order_id": ["ORD00002", "ORD00003", "ORD00004", "ORD00005", "ORD00006", "ORD00007", "ORD00008", "ORD00009", "ORD00010", "ORD00011"],
    "order_date": ["2026-04-30", "2026-05-06", "2026-04-19", "2026-04-22", "2026-04-20", "2026-05-08", "2026-04-30", "2026-04-29", "2026-05-05", "2026-04-24"],
    "sku": ["Charge", "Legend", "Velar", "Cosmos", "Charge", "Velar", "Alpha Classic", "Cosmos", "Cosmos", "Velar"],
    "city": ["Mumbai", "Pune", "Hyderabad", "Ahmedabad", "Ahmedabad", "Bangalore", "Ahmedabad", "Delhi", "Pune", "Delhi"],
    "payment_mode": ["Prepaid", "Prepaid", "Prepaid", "Prepaid", "COD", "Prepaid", "COD", "Prepaid", "Prepaid", "Prepaid"],
    "revenue": [2175, 2055, 2220, 2063, 2146, 2057, 1669, 2341, 2296, 2015],
    "customer_type": ["repeat", "repeat", "new", "new", "new", "repeat", "repeat", "new", "new", "repeat"]
}

# 2. meta_ads sheet
ads_data = {
    "campaign_name": ["Alpha Everyday", "Alpha Everyday", "Alpha Everyday", "Velar Comfort", "Timber Craft", "Legend Lifestyle", "Timber Craft", "Cosmos Luxe", "Alpha Everyday", "Charge Slip-On", "Timber Craft", "Velar Comfort", "Charge Slip-On", "Charge Slip-On", "Alpha Everyday"],
    "creative_hook": ["10,000+ Men", "10,000+ Men", "10,000+ Men", "Comfort + Arch Support", "Handcrafted Quality", "All Day Comfort", "Handcrafted Quality", "Premium Suede", "10,000+ Men", "Overtime Feet", "Handcrafted Quality", "Comfort + Arch Support", "Overtime Feet", "Overtime Feet", "10,000+ Men"],
    "daily_spend": [12361, 18476, 13993, 20759, 20798, 4135, 22025, 15273, 5430, 22566, 20076, 23364, 8040, 11175, 22111],
    "roas": [2.41, 4.33, 4.43, 2.44, 4.16, 3.77, 2.13, 4.34, 4.79, 4.17, 3.60, 3.79, 4.47, 4.86, 2.68],
    "ctr_percent": [3.35, 2.77, 1.29, 2.09, 2.94, 2.23, 2.82, 2.98, 1.69, 1.62, 2.25, 3.21, 1.92, 1.32, 3.41],
    "frequency": [4.16, 4.90, 1.81, 3.45, 1.36, 4.15, 1.65, 1.59, 2.59, 3.83, 3.15, 1.90, 4.04, 4.14, 4.33],
    "cpa": [374, 687, 597, 768, 877, 840, 693, 858, 351, 705, 356, 502, 878, 351, 686],
    "status": ["hold", "hold", "scale", "hold", "scale", "hold", "review", "scale", "scale", "hold", "scale", "scale", "hold", "hold", "hold"]
}

# 3. inventory sheet
inv_data = {
    "sku": ["Velar", "Legend", "Alpha Classic", "Timber", "Charge", "Cosmos"],
    "stock_left": [180, 320, 240, 90, 140, 110],
    "daily_velocity": [28, 19, 22, 16, 21, 17],
    "reorder_level": [120, 100, 90, 70, 80, 75],
    "projected_stockout_days": [6.4, 16.8, 10.9, 5.6, 6.7, 6.5]
}

# 4. creative_performance sheet
creative_data = {
    "creative_hook": ["Craftsmanship", "Arch Support", "Everyday Comfort", "Premium Suede", "10,000+ Men", "Overtime Feet"],
    "ctr_percent": [1.34, 2.19, 2.12, 1.67, 1.63, 2.65],
    "conversion_rate": [3.01, 2.58, 2.72, 3.19, 4.38, 4.65],
    "fatigue_score": [76, 78, 46, 69, 85, 36],
    "engagement_rate": [6.73, 3.69, 3.35, 2.98, 7.07, 5.48],
    "recommendation": ["refresh creatives", "refresh creatives", "continue scaling", "continue scaling", "refresh creatives", "continue scaling"]
}

# 5. customer_signals sheet
customer_data = {
    "sku": ["Velar", "Legend", "Alpha Classic", "Timber", "Charge", "Cosmos"],
    "repeat_rate_percent": [31, 24, 29, 21, 18, 26],
    "return_rate_percent": [7, 9, 6, 8, 11, 7],
    "review_sentiment": ["positive", "mixed-positive", "positive", "positive", "mixed", "positive"],
    "cod_ratio_percent": [48, 55, 51, 58, 63, 46],
    "prepaid_ratio_percent": [52, 45, 49, 42, 37, 54]
}

df_orders = pd.DataFrame(orders_data)
df_ads = pd.DataFrame(ads_data)
df_inv = pd.DataFrame(inv_data)
df_creative = pd.DataFrame(creative_data)
df_customer = pd.DataFrame(customer_data)

# Save to unified excel file with multiple sheets
with pd.ExcelWriter("test_data/unified_operator_data.xlsx") as writer:
    df_orders.to_excel(writer, sheet_name="shopify_orders", index=False)
    df_ads.to_excel(writer, sheet_name="meta_ads", index=False)
    df_inv.to_excel(writer, sheet_name="inventory", index=False)
    df_creative.to_excel(writer, sheet_name="creative_performance", index=False)
    df_customer.to_excel(writer, sheet_name="customer_signals", index=False)

print("Unified multi-sheet workbook test_data/unified_operator_data.xlsx generated successfully!")
