import sys
import os

# Add apps/api to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db import engine, SessionLocal
from app.models import BusinessSnapshot, Brand
from app.rules import SignalDetectionEngine

def test_detection():
    db: Session = SessionLocal()
    try:
        brand_id = "brand_1780130294864"
        brand = db.get(Brand, brand_id)
        if not brand:
            print(f"❌ Error: Brand {brand_id} not found in database!")
            return

        print(f"Found brand: {brand.name} ({brand.id})")

        # Query latest snapshot
        snapshot = db.query(BusinessSnapshot).filter(
            BusinessSnapshot.brand_id == brand_id
        ).order_by(BusinessSnapshot.snapshot_version.desc()).first()

        if not snapshot:
            print("❌ Error: No snapshots found for this brand!")
            return

        print(f"Running detection on snapshot version {snapshot.snapshot_version} uploaded via {snapshot.upload_source}...")

        # Run signal detection
        signals = SignalDetectionEngine.detect(snapshot.state, freshness=1.0)

        print("\n=== DETECTED SIGNALS ===")
        print(f"Total signals detected: {len(signals)}\n")

        detected_types = {}
        for s in signals:
            print(f"Title:        {s.title}")
            print(f"Signal Type:  {s.signal_type}")
            print(f"Issue Type:   {s.issue_type}")
            print(f"Severity:     {s.severity}")
            print(f"ROAS placed:  {s.cross_system_signals[0] if s.cross_system_signals else 'N/A'}")
            print(f"Impact:       {s.impact_label}")
            print(f"Rule checked: {s.rule}")
            print("-" * 50)
            detected_types[s.signal_type] = detected_types.get(s.signal_type, 0) + 1

        print("\n=== SUMMARY OF SIGNAL COUNTS BY TYPE ===")
        for s_type, count in detected_types.items():
            print(f"- {s_type}: {count}")

        # Assert all six expected types are present
        expected = {"InventoryRisk", "CreativeFatigue", "MarginLeakage", "MarginTrap", "NewLaunchRisk", "AOVDilution"}
        missing = expected - set(detected_types.keys())
        if missing:
            print(f"\n❌ FAILED: Missing expected edge-case signals: {missing}")
        else:
            print("\n✅ SUCCESS: All 6 edge cases (including the 3 new custom ones) are successfully detected!")

    finally:
        db.close()

if __name__ == "__main__":
    test_detection()
