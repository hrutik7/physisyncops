# Physisync: Ontology Layer & Entity Relationships Documentation

This document serves as the definitive reference for the **Ontology Layer** in Physisync. It details how the platform models the relationships and dependencies between different e-commerce entities (brands, campaigns, SKUs, and customer segments) and key financial/operational metrics.

---

## 1. Overview of the Ontology Layer

The Ontology Layer is a graph-based representation of the operational relationships inside a D2C business. While standard tables list anomalies (e.g., "high RTO rate"), the Ontology Layer maps **how** those anomalies propagate through the business. It explains:
1. Which campaign or SKU is the **root cause** of an issue.
2. Which customer behaviors or metrics act as the **intermediary triggers**.
3. Which final financial targets (e.g., margins, revenues) are ultimately **impacted**.

By modeling these connections, Physisync can build dynamic dependency graphs that show founders and operators the exact chain of cause and effect behind every decision.

---

## 2. Ontology Data Model (`apps/api/app/models.py`)

The ontology is persisted in the PostgreSQL database using two main SQLAlchemy models:

### 2.1 `OntologyNode`
Represents an entity, dimension, or metric in the graph.
*   **`id`**: Unique UUID.
*   **`brand_id`**: Foreign key linking the node to a specific brand.
*   **`entity_type`**: The category of the entity (e.g., `"derived"` when generated dynamically from decisions).
*   **`entity_key`**: A normalized unique identifier string. It is lowercased, stripped, and spaces are replaced with underscores (e.g., `"prepaid_retargeting"`, `"inventory_pressure"`, `"realized_roas"`).
*   **`label`**: The human-readable name displayed in the UI (e.g., `"Realized ROAS"`).
*   **`properties`**: A JSON payload containing metadata, such as `{"source": "decision_relationship"}`.

### 2.2 `OntologyEdge`
Represents a directed link showing influence or dependency between two nodes.
*   **`id`**: Unique UUID.
*   **`brand_id`**: Foreign key linking the edge to a specific brand.
*   **`from_key`**: The source node's `entity_key` (e.g., `"campaign_name"`).
*   **`to_key`**: The destination node's `entity_key` (e.g., `"cod_orders"`).
*   **`label`**: A descriptive phrase explaining the relationship (e.g., `"drives 65% COD mix"`, `"elevates"`, `"compresses to 12%"`).
*   **`strength`**: The impact strength of the connection (`"strong"`, `"medium"`, `"low"`).
*   **`source_decision_id`**: Foreign key linking the edge to the `Decision` that discovered/generated it. This allows the system to clean up or display edges contextualized by active alerts.

---

## 3. Entity Relationships by Signal Type (`apps/api/app/rules.py`)

Relationships are generated dynamically by the `OntologyLayer.build_relationships` static method inside `rules.py` when an alert is triggered. The templates define how nodes are linked based on the type of signal:

### 3.1 Campaign RTO Spike (`CampaignRTOSpike`)
*   **Context**: A marketing campaign is driving a disproportionate volume of Cash-on-Delivery (COD) orders that end up as Return to Origin (RTO).
*   **Graph Chain**:
    ```
    [Campaign Name] --(drives {cod_ratio}% COD mix)--> [COD orders]
         └─> [COD orders] --(elevates)--> [RTO probability]
              └─> [RTO probability] --(reduces to {delivered_roas}x)--> [Realized ROAS]
                   └─> [Realized ROAS] --(compresses to {margin}%)--> [Margin]
    ```

### 3.2 Inventory Risk (`InventoryRisk`)
*   **Context**: Ad campaign spend is accelerating while SKU inventory cover drops below a critical threshold.
*   **Graph Chain**:
    ```
    [Campaign Name] --(drives demand)--> [{SKU Name} velocity]
         └─> [{SKU Name} velocity] --({SKU Name} stockout in {days} days)--> [Inventory pressure]
    ```

### 3.3 Creative Fatigue (`CreativeFatigue`)
*   **Context**: An ad set's frequency is high, causing Click-Through Rates (CTR) to decay rapidly.
*   **Graph Chain**:
    ```
    [Campaign Name] --({frequency} exposures)--> [Frequency]
         └─> [Frequency] --({ctr_drop}% drop)--> [CTR]
              └─> [CTR] --(destabilizes)--> [CAC stability]
    ```

### 3.4 Scaling Opportunity (`ScalingOpportunity`)
*   **Context**: A campaign exhibits excellent delivered ROAS, low RTO, high repeat rates, and healthy stock levels, indicating it is safe to scale.
*   **Graph Chain**:
    ```
    [Campaign Name] --({rto_rate}% delivered-order RTO)--> [Low RTO]
         └─> [Low RTO] --(supports {roas}x)--> [Realized ROAS]
    [Inventory cover] --({stockout_days} days available)--> [Scale safety]
    ```

### 3.5 Margin Leakage (`MarginLeakage`)
*   **Context**: A segment or SKU appears profitable on ad dashboards but suffers heavy margin erosion from shipping/return logistics fees.
*   **Graph Chain**:
    ```
    [Segment Name] --({cod_ratio}% cash preference)--> [COD Mix]
         └─> [COD Mix] --({rto_rate}% delivered-order RTO)--> [RTO Spike]
    ```

### 3.6 Margin Trap (`MarginTrap`)
*   **Context**: Deep product discounts collapse the realized average selling price (ASP), meaning paper ROAS does not translate to profit.
*   **Graph Chain**:
    ```
    [Campaign Name] --(cuts realized ASP)--> [Discounted Price]
         └─> [Discounted Price] --(collapses to {delivered_roas}x vs {placed_roas}x placed)--> [Realized ROAS]
    ```

### 3.7 New Launch Risk (`NewLaunchRisk`)
*   **Context**: A newly launched ad campaign has extremely low ROAS with low frequency, indicating poor audience/creative fit.
*   **Graph Chain**:
    ```
    [Campaign Name] --(early ad learning phase)--> [Low frequency test]
         └─> [Low frequency test] --({roas}x ROAS with no baseline)--> [Low ROAS]
    ```

### 3.8 AOV Dilution (`AOVDilution`)
*   **Context**: Bundle and combo offers increase placed order numbers but dilute average order value and margins after discounts and delivery returns are counted.
*   **Graph Chain**:
    ```
    [Campaign Name] --(masks individual item margin)--> [Combo bundle push]
         └─> [Combo bundle push] --(drags realized ROAS to {delivered_roas}x vs {placed_roas}x placed)--> [AOV Compression]
    ```

---

## 4. Flow of Persistence & Lifecycle

1.  **Ingestion**: Spreadsheet upload (`tasks.py`) or sandbox update (`main.py`) creates a new `BusinessSnapshot` with current SKUs, Campaigns, and Customer Segments.
2.  **Signal Detection**: `SignalDetectionEngine.detect` runs the heuristic rules on the current state. If a rule triggers, it generates a `Signal` dataclass containing properties and a list of `relationship_edges` built by `OntologyLayer`.
3.  **Enrichment**: The signal is passed through `LLMEnrichmentService.enrich_signal` to add human-like explanations and audit trails.
4.  **Creation of Decision**: A new `Decision` record is saved.
5.  **Ontology Writing**: The system runs `persist_ontology(db, brand_id, decision)`:
    *   Iterates through each edge in `decision.relationship_edges`.
    *   Extracts `from_label` and `to_label`.
    *   Normalizes labels to get `entity_key` strings (e.g., `_node_key("COD orders")` -> `"cod_orders"`).
    *   If a node with that key doesn't exist for the brand, it inserts an `OntologyNode` with `entity_type="derived"`.
    *   Inserts the `OntologyEdge` referencing both keys and the current `source_decision_id`.
6.  **Commit**: The transaction is committed to the database.

---

## 5. Exposing Graph Data via API

The frontend accesses this relationship graph using the Operating Layer endpoint:

```http
GET /brands/{brand_id}/operating-layer
```

This endpoint queries all `OntologyNode` and `OntologyEdge` records for the specified `brand_id`. The response maps them into a graph structure suitable for rendering:

```json
{
  "ontology": {
    "nodes": [
      {
        "id": "node-uuid-1",
        "entityType": "derived",
        "entityKey": "prepaid_retargeting",
        "label": "Prepaid Retargeting",
        "properties": { "source": "decision_relationship" }
      },
      ...
    ],
    "edges": [
      {
        "id": "edge-uuid-1",
        "fromKey": "prepaid_retargeting",
        "toKey": "cod_orders",
        "label": "drives 40% COD mix",
        "strength": "strong",
        "sourceDecisionId": "decision-uuid-abc"
      },
      ...
    ]
  }
}
```

This structured JSON feeds visual canvas graphs, nodes, and links on the frontend dashboard to display the root-cause flow for each triggered alert.
