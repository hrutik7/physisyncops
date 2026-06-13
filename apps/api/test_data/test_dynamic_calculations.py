import sys
import os

# Add apps/api to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Brand, UnitEconomics, BusinessSnapshot
from app.tasks import calculate_sku_margin_params
from app.rules import SignalDetectionEngine

def test_dynamic_calculations():
    db: Session = SessionLocal()
    try:
        # Create a mock brand if not exists
        brand_id = "test_dynamic_brand"
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            brand = Brand(id=brand_id, name="Dynamic Test Brand")
            db.add(brand)
            db.commit()

        # Delete any existing unit economics for this test brand
        db.query(UnitEconomics).filter(UnitEconomics.brand_id == brand_id).delete()
        db.commit()

        # 1. Test Fallback Behavior (No Unit Economics record)
        print("Testing fallback behavior when UnitEconomics record is missing...")
        fallback_params = calculate_sku_margin_params(db, brand_id, "SKU-TEST", 1500.0)
        
        # Test CM Pre calculation (should use default 28%)
        cm_pre_fall, impact_factor_fall, waste_mult_fall = fallback_params
        
        assert cm_pre_fall == 28.0, f"Expected fallback cm_pre to be 28.0, got {cm_pre_fall}"
        assert impact_factor_fall == 0.65, f"Expected fallback rto_impact_factor to be 0.65, got {impact_factor_fall}"
        assert waste_mult_fall == 0.40, f"Expected fallback waste_multiplier to be 0.40, got {waste_mult_fall}"
        print("✅ Fallback assertions passed!")

        # 2. Test Custom Unit Economics Overrides (Premium SKU: high AOV)
        print("\nTesting overrides with Premium SKU (high AOV)...")
        premium_econ = UnitEconomics(
            brand_id=brand_id,
            sku_id="SKU-PREMIUM",
            gross_margin_percent=75.0, # 75% gross margin
            shipping_cost=150.0,       # 150 forward shipping
            rto_cost=100.0,            # 100 return shipping
            packaging_cost=50.0,       # 50 packaging
            payment_gateway_cost=80.0  # 80 payment gateway cost
        )
        db.add(premium_econ)
        db.commit()
        
        premium_aov = 4000.0
        premium_params = calculate_sku_margin_params(db, brand_id, "SKU-PREMIUM", premium_aov)
        cm_pre_prem, impact_factor_prem, waste_mult_prem = premium_params
        
        # Gross margin is 75%. Shipping + packaging = 150 + 50 = 200. Gateway fee = 80.
        # Total pre-RTO cost = 200 + 80 = 280. 280 / 4000 * 100 = 7.0%.
        # cm_pre = 75 - 7 = 68.0%
        # rto_impact_factor = (shipping + rto_shipping + packaging) / AOV = (150 + 100 + 50) / 4000 = 300 / 4000 = 0.075
        # Waste multiplier = rto_impact_factor = 0.075
        assert abs(cm_pre_prem - 68.0) < 0.1, f"Expected premium cm_pre to be 68.0, got {cm_pre_prem}"
        assert abs(impact_factor_prem - 0.075) < 0.001, f"Expected premium rto_impact_factor to be 0.075, got {impact_factor_prem}"
        assert abs(waste_mult_prem - 0.075) < 0.001, f"Expected premium waste_multiplier to be 0.075, got {waste_mult_prem}"
        print("✅ Premium SKU assertions passed!")

        # 3. Test Custom Unit Economics Overrides (Budget SKU: low AOV)
        print("\nTesting overrides with Budget SKU (low AOV)...")
        budget_econ = UnitEconomics(
            brand_id=brand_id,
            sku_id="SKU-BUDGET",
            gross_margin_percent=65.0, # 65% gross margin
            shipping_cost=150.0,       # 150 forward shipping
            rto_cost=100.0,            # 100 return shipping
            packaging_cost=50.0,       # 50 packaging
            payment_gateway_cost=20.0  # 20 PG cost
        )
        db.add(budget_econ)
        db.commit()
        
        budget_aov = 1000.0
        budget_params = calculate_sku_margin_params(db, brand_id, "SKU-BUDGET", budget_aov)
        cm_pre_budg, impact_factor_budg, waste_mult_budg = budget_params
        
        # Gross margin is 65%. Shipping + packaging = 150 + 50 = 200. Gateway fee = 20.
        # Total pre-RTO cost = 200 + 20 = 220. 220 / 1000 * 100 = 22.0%.
        # cm_pre = 65 - 22 = 43.0%
        # rto_impact_factor = (shipping + rto_shipping + packaging) / AOV = (150 + 100 + 50) / 1000 = 300 / 1000 = 0.3
        # Waste multiplier = rto_impact_factor = 0.3
        assert abs(cm_pre_budg - 43.0) < 0.1, f"Expected budget cm_pre to be 43.0, got {cm_pre_budg}"
        assert abs(impact_factor_budg - 0.3) < 0.001, f"Expected budget rto_impact_factor to be 0.3, got {impact_factor_budg}"
        assert abs(waste_mult_budg - 0.3) < 0.001, f"Expected budget waste_multiplier to be 0.3, got {waste_mult_budg}"
        print("✅ Budget SKU assertions passed!")

        # 4. Test Rule Engine integration with SKU-level AOV
        print("\nTesting Rule Engine integration with SKU-level AOV...")
        mock_state = {
            "average_order_value": 1500.0,
            "brand_repeat_rate": 25.0,
            "skus": [
                {
                    "sku_id": "sku-premium",
                    "name": "Premium Product",
                    "inventory_left": 10,
                    "daily_velocity": 5.0,
                    "projected_stockout_days": 2.0,
                    "average_order_value": 4000.0,  # SKU-level AOV
                    "spend_growth_percent": 20.0
                }
            ],
            "campaigns": []
        }
        signals = SignalDetectionEngine.detect(mock_state, freshness=1.0)
        
        # Verify that InventoryRisk is generated and uses SKU-level AOV
        inventory_signals = [s for s in signals if s.signal_type == "InventoryRisk"]
        assert len(inventory_signals) == 1, "Expected 1 InventoryRisk signal"
        inv_sig = inventory_signals[0]
        
        # Revenue at risk = daily_velocity (5.0) * SKU AOV (4000.0) * (7 - stockout (2.0))
        # = 5.0 * 4000.0 * 5.0 = 100,000
        assert inv_sig.business_impact == 100000, f"Expected business impact of 100,000, got {inv_sig.business_impact}"
        assert "SKU-level AOV is Rs 4,000.00" in inv_sig.cross_system_signals, "Expected SKU-level AOV in cross system signals"
        print("✅ Rule Engine integration with SKU-level AOV passed!")

        # Clean up database
        db.query(UnitEconomics).filter(UnitEconomics.brand_id == brand_id).delete()
        db.query(Brand).filter(Brand.id == brand_id).delete()
        db.commit()
        print("\n🏆 ALL DYNAMIC CALCULATION TESTS PASSED!")

    finally:
        db.close()

if __name__ == "__main__":
    test_dynamic_calculations()
