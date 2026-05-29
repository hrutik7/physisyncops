# Opentra

Operational observability for Indian D2C brands.

## What is included

- Next.js 14, TypeScript, TailwindCSS, Zustand, Recharts, Lucide frontend
- FastAPI backend skeleton with SQLAlchemy models, PostgreSQL, Redis/Celery wiring, Pandas upload preview
- Fuzzy column mapping flow with user confirmation
- Baseline-mode first upload handling
- Deterministic signal thresholds in code
- Campaign-level RTO spike signal as the core demo decision
- Realized ROAS and RTO calculation helpers that use delivered orders only

## Run frontend

```bash
npm install
npm run dev:infra
npm run dev
```

Open `http://localhost:3000`.

## Run backend

```bash
npm run dev:infra
cd apps/api
python3 -m venv .venv
.venv/bin/activate
pip install -r requirements.txt
npm run dev
```

API health check: `http://localhost:8000/health`.

## Non-negotiable commerce rules

- RTO rate is calculated as `returned_orders / delivered_orders * 100`
- Realized ROAS is calculated as `revenue_from_delivered_orders / ad_spend`
- First upload creates a baseline snapshot and does not produce false monitoring inferences
- Signal detection is deterministic and threshold-based for MVP

## Upload Flow

### How It Works
Users can now upload Excel files directly without selecting a source type. The system automatically detects the data source based on sheet names:

- **Shopify Orders**: Sheets containing "shopify" or "order" in the name
- **Meta Ads**: Sheets containing "meta" or "ad" in the name  
- **Inventory**: Sheets containing "inventory" in the name
- **Creative Performance**: Sheets containing "creative" in the name
- **Customer Signals**: Sheets containing "customer" in the name

### Multi-Sheet Uploads
You can include multiple sheets in a single Excel file (e.g., Shopify Orders, Meta Ads, and Inventory all in one workbook). The system will process each sheet according to its name.
