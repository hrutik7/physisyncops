import pandas as pd
import os

# Create folder for test data
os.makedirs("test_data", exist_ok=True)

# 1. Generate shopify_orders_test.xlsx
orders_data = {
    "Order ID": [f"ORD-{1000 + i}" for i in range(100)],
    "Gross Sales": [1200 + (i * 20) % 800 for i in range(100)],
    "Undelivered": [1 if i % 3 == 0 else 0 for i in range(100)], # ~33% RTO rate
    "utm_campaign": ["Tier2-COD-Lookalike-May" if i % 2 == 0 else "Velar-Static-V1" for i in range(100)],
    "Variant SKU": ["Velar Runner" if i % 2 == 0 else "Metro Slip-On" for i in range(100)],
    "Payment Method": ["COD" if i % 3 != 1 else "Prepaid" for i in range(100)], # ~67% COD mix
    "Delivered": [1 if i % 10 != 0 else 0 for i in range(100)],
    "Amount Spent": [50 for _ in range(100)],
    "Date": ["2026-05-20 10:00:00" for _ in range(100)]
}
df_orders = pd.DataFrame(orders_data)
df_orders.to_excel("test_data/shopify_orders_test.xlsx", index=False)

# 2. Generate meta_ads_test.xlsx
ads_data = {
    "campaign_id": ["Tier2-COD-Lookalike-May", "Velar-Static-V1", "Prepaid-Metro-Retargeting"],
    "Amount Spent": [25000, 10500, 35000],
    "frequency": [4.5, 5.8, 2.1], # fatigue threshold > 4
    "ctr": [0.9, 1.0, 3.8],
    "Date": ["2026-05-20 10:00:00" for _ in range(3)]
}
df_ads = pd.DataFrame(ads_data)
df_ads.to_excel("test_data/meta_ads_test.xlsx", index=False)

# 3. Generate inventory_test.xlsx
inv_data = {
    "sku_id": ["Velar Runner", "Metro Slip-On"],
    "inventory_left": [90, 800],
    "daily_velocity": [25, 40],
    "Date": ["2026-05-20 10:00:00" for _ in range(2)]
}
df_inv = pd.DataFrame(inv_data)
df_inv.to_excel("test_data/inventory_test.xlsx", index=False)

print("Test spreadsheets created in test_data/ successfully.")
