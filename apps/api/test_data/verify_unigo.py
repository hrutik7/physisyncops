import httpx
import json
import time
import os

API_URL = "http://localhost:8000"

def test_pipeline():
    print("1. Sending preview request for unigo final.xlsx...")
    file_path = "../../unigo final.xlsx"
    
    if not os.path.exists(file_path):
        # try root path
        file_path = "unigo final.xlsx"
        if not os.path.exists(file_path):
            print("Error: unigo final.xlsx not found!")
            return
            
    with open(file_path, "rb") as f:
        files = {"file": ("unigo final.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = httpx.post(
            f"{API_URL}/uploads/preview",
            params={"brand_id": "brand_unigo_real", "upload_source": "shopify_orders"},
            files=files
        )
        
    if response.status_code != 200:
        print(f"Error previewing file: {response.text}")
        return
        
    preview_data = response.json()
    print("Preview successful!")
    print(f"Uploaded columns: {preview_data['columns']}")
    print(f"Suggested mappings: {preview_data['suggestions']}")
    
    # Construct mappings from suggestions
    mapping = {}
    for suggestion in preview_data['suggestions']:
        uploaded_col = suggestion.get('uploadedColumn') or suggestion.get('uploaded_column')
        canonical_field = suggestion.get('canonicalField') or suggestion.get('canonical_field')
        if uploaded_col and canonical_field:
            mapping[canonical_field] = uploaded_col
            
    print(f"\n2. Confirming mapping and launching Celery task: {mapping}")
    with open(file_path, "rb") as f:
        files = {"file": ("unigo final.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {
            "brand_id": "brand_unigo_real",
            "upload_source": "shopify_orders",
            "mapping": json.dumps(mapping)
        }
        response = httpx.post(
            f"{API_URL}/uploads/confirm",
            data=data,
            files=files
        )
        
    if response.status_code != 200:
        print(f"Error confirming mapping: {response.text}")
        return
        
    confirm_data = response.json()
    task_id = confirm_data["task_id"]
    print(f"Celery task launched successfully! Task ID: {task_id}")
    
    print("\n3. Polling Celery task status...")
    status = "pending"
    for _ in range(30): # poll for up to 30 seconds
        time.sleep(1)
        response = httpx.get(f"{API_URL}/uploads/status/{task_id}")
        status_data = response.json()
        status = status_data["status"]
        
        print(f"Current task status: {status}")
        if status in ["success", "failure"]:
            break
            
    if status == "success":
        print("\n🎉 PIPELINE SUCCESSFUL!")
        
        # Verify state is updated in DB
        print("\n4. Verifying state loaded from database...")
        state_response = httpx.get(f"{API_URL}/state?brand_id=brand_unigo_real")
        state_data = state_response.json()
        print(f"Latest active snapshot upload source: {state_data['snapshots'][0]['uploadSource']}")
        print(f"Number of generated decisions: {len(state_data['decisions'])}")
        print("\n=== GENERATED DECISIONS ===")
        for d in state_data['decisions']:
            print(f" - [{d['severity'].upper()}] {d['title']} (Confidence: {int(d['confidenceScore']*100)}%, Impact: {d['impactLabel']})")
            print(f"   Explanation: {d['explanation']}")
            print(f"   Signal Type: {d['signalType']}")
            print(f"   Relationship Edges Count: {len(d['relationshipEdges'])}")
            print("-" * 50)
            
    else:
        print(f"\n❌ Pipeline failed or timed out: {status_data}")

if __name__ == "__main__":
    test_pipeline()
