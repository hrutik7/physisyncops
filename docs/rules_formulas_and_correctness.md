# Physisync: Rules, Formulas, & Why Our Calculations Are Correct

This document is a definitive reference for D2C founders, operators, and growth auditors. It explains the exact formulas, rule triggers, and the core mathematical reasons why Physisync's analytical models represent the absolute truth of your business health, whereas traditional dashboards (like Shopify and Meta Ads Manager) systematically misreport your margins.

---

## 1. Metric: Return to Origin (RTO) Rate

### 1.1 The Formulas
*   **Customer Segment / Blended RTO Rate**:
    > **RTO Rate (%)** = `(Returned Orders / Delivered Orders) * 100`
*   **Attributed Campaign RTO Rate**:
    > **Attributed Campaign RTO (%)** = `(Attributed RTO Count / Attributed Delivered Orders) * 100`

### 1.2 Why Physisync is Mathematically Correct
Standard analytics suites (including Shopify and default e-commerce reports) calculate return rate as:
> **Standard Return Rate** = `Returned Orders / Total Placed Orders`

**Why this standard calculation is incorrect and dangerous:**
1.  **Denominator Contamination**: Placed orders include orders that are cancelled pre-fulfillment, failed payments, or unfulfilled due to fraud. Including them dilutes the denominator.
2.  **Operational Mismatch**: A return (RTO) can *only* occur after a shipment has been fulfilled, picked up, and a delivery attempt is made. 
3.  **The Physisync Advantage**: By isolating the denominator to **Delivered (Fulfilled) Orders**, we mathematically isolate fulfillment-level courier and delivery performance from checkout-level cart drop-offs. This prevents a high pre-fulfillment cancellation rate from artificially masking a severe RTO crisis.

---

## 2. Metric: Realized Return on Ad Spend (Realized ROAS)

### 2.1 The Formulas
*   **Primary Calculation**:
    > **Realized ROAS** = `Revenue from Delivered Orders / Ad Spend`
*   **Heuristic Calculation (when converting Placed ROAS)**:
    > **Realized ROAS** = `Placed ROAS * (1 - (RTO Rate (%) / 100))`

### 2.2 Why Physisync is Mathematically Correct
Meta Ads Manager and Google Ads report ROAS using placed checkout values (conversion pixels fired on the "Thank You" page).

**Why standard ad network ROAS is incorrect and dangerous:**
1.  **Paper Revenue vs. Hard Cash**: In India's e-commerce landscape, where Cash on Delivery (COD) typically accounts for 50% to 80% of orders, a substantial portion of ad-reported revenue never materializes into cash because the shipment is returned (RTO).
2.  **The Double-Whammy Cost**: An RTO doesn't just mean zero revenue; it means you paid Meta to acquire a customer, paid a courier forward-shipping fees, and paid return-shipping fees.
3.  **The Physisync Advantage**: Realized ROAS deducts RTO volume to show **actual cash collected per rupee of ad spend**. Scaling a campaign based on standard Placed ROAS while it has a 35% COD RTO rate is the #1 cause of cash-flow insolvency for growing brands.

---

## 3. Metric: Projected Stockout Days

### 3.1 The Formula
> **Projected Stockout Days** = `Inventory Left (Units) / Daily Sales Velocity (Units/Day)`

### 3.2 Why Physisync is Mathematically Correct
Traditional Inventory Management Systems (IMS) and ERPs use static thresholds (e.g., "reorder when stock falls below 50 units").

**Why static inventory alerts are incorrect and dangerous:**
1.  **Ignores Growth Velocity**: If a media buyer triples the ad spend on a campaign today, sales velocity spikes instantly. A static reorder alert of 50 units might have represented 10 days of stock yesterday, but today it represents only 2 days of stock. You will stock out before the inventory purchase order is processed.
2.  **The Physisync Advantage**: Physisync continuously recalculates daily sales velocity in real-time by linking actual Shopify sales volume to active ad spend acceleration. It projects stockouts dynamically, allowing operators to preemptively replenish inventory *before* paid traffic is driven into a dead end.

---

## 4. Metric: Customer Retention & Repeat Purchase Rate

### 4.1 The Formulas
*   **From Customer Type**: `(Returning Orders / Total Orders) * 100`
*   **From Customer Cohorts**: `(Unique Customers with > 1 Orders / Total Unique Customers) * 100`

### 4.2 Why Physisync is Mathematically Correct
Most systems look at lifetime retention or customer cohorts on a store-wide basis. By tracking SKU-specific repeat rates directly from the order streams, Physisync isolates high-LTV hero SKUs from single-purchase acquisition items, giving marketers highly accurate signals on which SKU audiences are safe to scale.

---

## 5. Metric: Customer Acquisition Cost (CAC)

### 5.1 The Formulas
*   **Placed CAC**: `SKU-level AOV / Placed ROAS`
*   **Realized CAC**: `SKU-level AOV / Delivered ROAS`

### 5.2 Why Physisync is Mathematically Correct
Standard platforms only calculate Placed CAC (checkout cost). Physisync provides full visibility of Realized CAC, showing how much hard cash is spent to acquire a successfully delivered, cash-collected customer.

---

## 6. Heuristic Rules & Financial Impact Math

Physisync implements 5 core heuristic rules. Below is the exact logical trigger, the detailed mathematical impact formula, and the justification for why our calculations are correct:

### Rule 6.1: Campaign RTO Spike (High Severity)
*   **Trigger**:
    `Attributed RTO Rate >= 25%` AND `COD Order Count >= 50`

#### 📊 Business Impact Formula (Daily Margin Loss):
```
Daily Spend = Weekly Campaign Spend / 7
Daily Margin Loss = Daily Spend * Placed ROAS * (Contribution Margin % / 100) * max(1 - (Delivered ROAS / Placed ROAS), 0)
```
*(Enforced floor: Rs. 500/day)*
*   **Daily Spend**: Total campaign ad spend divided by 7 (converting weekly snapshot to daily).
*   **Placed ROAS**: The ROAS reported on checkout (placed orders) in Meta Ads.
*   **Delivered ROAS**: Realized ROAS based only on delivered/paid orders.
*   **Contribution Margin %**: Derived dynamically from database unit economics:
    *   `CM_pre = Gross Margin % - ((Shipping Cost + Packaging Cost + Payment Gateway Cost) / SKU AOV) * 100`
    *   `RTO Impact Factor = (Shipping Cost + Return Shipping Cost + Packaging Cost) / SKU AOV`
    *   `Contribution Margin % = CM_pre - (RTO Rate % * RTO Impact Factor)`
    *(Falls back to static benchmark `28 - (RTO Rate * 0.65)` only if unit economics overrides are missing in DB).*
*   **max(1 - (Delivered ROAS / Placed ROAS), 0)**: The fraction of ad revenue wiped out by shipping returns.
*   **Why this calculation is correct**: It isolates the exact cash margin lost on returns daily. Rather than looking at a store-wide RTO, it identifies the specific ad sets bleeding capital and quantifies the exact opportunity cost of not pausing them immediately.

---

### Rule 6.2: Inventory Risk (High Severity)
*   **Trigger**:
    `Projected Stockout Days <= 7 days` AND `Spend Growth >= 15%`

#### 📊 Business Impact Formula (Revenue at Risk):
```
Revenue at Risk = Daily Sales Velocity * SKU AOV * min(Projected Stockout Days, 7)
```
*   **Daily Sales Velocity**: Units sold per day for this specific SKU (from the `inventory` or `shopify_orders` sheet).
*   **SKU AOV (Average Order Value)**: SKU-specific average order value dynamically calculated from the orders sheet. Fallback to store-wide AOV only if SKU-specific data is missing.
*   **min(Projected Stockout Days, 7)**: Capped at a maximum of 7 days (1 week) to represent immediate near-term operational risk.
*   **Why this calculation is correct**: By using SKU-specific AOV instead of a store-wide blended AOV, it prevents underestimating the revenue-at-risk for premium product lines while maintaining accuracy for low-cost lines.

---

### Rule 6.3: Creative Fatigue (Medium Severity)
*   **Trigger**:
    `Creative Frequency >= 4.0` AND `CTR Drop >= 20%`

#### 📊 Business Impact Formula (Spend Efficiency at Risk):
```
Spend Efficiency at Risk = Weekly Campaign Spend * (CTR Drop % / 100)
```
*(Enforced floor: Rs. 1,000)*
*   **Weekly Campaign Spend**: Total campaign ad spend in the last 7 days.
*   **CTR Drop %**: The percentage drop in Click-Through Rate compared to the previous week.
*   **Why this calculation is correct**: A 20% drop in CTR means you are acquiring 20% fewer website visitors for the exact same ad spend. Thus, 20% of your ad spend is completely wasted on an exhausted audience.

---

### Rule 6.4: Margin Leakage (High Severity)
*   **Trigger**:
    `COD Ratio >= 60%` AND `Delivered RTO Rate >= 18%` AND `Placed ROAS >= 3.0`

#### 📊 Business Impact Formula (Margin Leakage):
```
Margin Leakage = Blended Campaign Spend * (RTO Rate % / 100) * Waste Multiplier
```
*(Enforced floor: Rs. 2,000)*
*   **Blended Campaign Spend**: The total ad spend across all ad sets targeting this customer segment/SKU.
*   **RTO Rate %**: The return rate on delivered orders for this segment.
*   **Waste Multiplier**: Derived dynamically from database unit economics:
    *   `Waste Multiplier = (Shipping Cost + Return Shipping Cost + Packaging Cost) / SKU AOV`
    *(Falls back to static benchmark constant `0.40` only if overrides are missing in DB).*
*   **Why this calculation is correct**: Standard platforms celebrate a campaign with >3.0 Placed ROAS. Physisync knows that if COD preference is extremely high and RTO is elevated, a significant portion of the shipping/operational capital is completely burned on returned logistics. We expose this margin leakage so you can shift budget to prepaid retargeting.

---

### Rule 6.5: Scaling Opportunity (Low Severity)
*   **Trigger**:
    `Delivered ROAS >= 4.0` AND `Delivered RTO Rate <= 7%` AND `Repeat Rate >= 25%` AND `Contribution Margin >= 30%` AND `Projected Stockout Days >= 14`

#### 📊 Business Impact Formula (Incremental Revenue Opportunity):
```
Incremental Revenue Opportunity = Weekly Campaign Spend * 0.25 * Delivered ROAS
```
*(Enforced floor: Rs. 5,000)*
*   **Weekly Campaign Spend**: Current weekly ad spend on this campaign.
*   **0.25 (25% Scaling standard)**: The standard conservative budget increase recommended by media buyers to scale campaigns without disrupting the ad delivery algorithm.
*   **Delivered ROAS**: Realized ROAS (actual cash collected).
*   **Why this calculation is correct**: D2C brands are often too conservative when scaling. Physisync checks five distinct pillars (Profitability, Return mix, Retention, Margin, and Stock cover) to mathematically guarantee that a 25% budget increase will yield proportional, highly profitable revenue without stocking out.

---

## 7. Verification: Closed-Loop Accountability

When you take action, standard platforms require you to manually check spreadsheets days later to see if it worked. Physisync automates this:
*   **Paused Campaign Verification**: Confirms that flagged campaign spend dropped by **>= 80%**.
*   **Spend Reduction Verification**: Confirms that spend dropped by **>= 15%**.
*   **Inventory Reorder Verification**: Confirms warehouse stock increased by **>= 25%** AND stockout cover improved by **>= 3 days**.

By comparing the pre-action snapshot against the post-action snapshot, Physisync mathematically verifies that the operational loop was closed successfully.

---
*Send this document to any founder, investor, or operations lead to establish the absolute integrity of Physisync's metrics.*
