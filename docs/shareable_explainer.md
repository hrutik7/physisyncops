# Physisync: Business-First Explainer for D2C Founders & Operators

When explaining Physisync to a D2C founder, operator, or growth marketer, you don't want to start with complex code heuristics. Instead, explain the **business problem** we solve, the **core metrics** we fix, and **how the loop closes**.

Below is a ready-to-use cheat sheet and copy-pasteable communication templates you can send them right away.

---

## 1. The High-Level Pitch (The "Why")

> *"Shopify reports order value when a customer clicks 'Buy'. Meta Ads reports ROAS based on that Shopify checkout value. But in India, 60%+ of orders are COD, and up to 30%-40% of those COD orders get returned (RTO). If you are budgeting your ad spend based on Shopify/Meta dashboard metrics, **you are spending real cash on fake revenue.**"*
>
> **Physisync unifies Meta Ads spend with final Shopify delivery statuses in real-time, subtracting RTO rates from your ROAS to show you exactly how much cash you actually collected.**

---

## 2. Copy-Pasteable Templates to Send Founders/Operators

Here are templates you can instantly copy-paste into Slack, WhatsApp, or Email to explain how it works.

### 📧 Template A: Email (Best for D2C Founders / CEO audits)
**Subject:** Quick overview: How Physisync audits our real cash margins (ROAS vs. RTO)

```markdown
Hey [Founder Name],

Just wanted to give you a quick breakdown of how Physisync calculates our performance numbers under the hood. 

In short: it prevents us from scaling campaigns that look profitable on Meta but are actually losing us money due to high Cash on Delivery (COD) returns.

Here is the exact framework the tool uses:

1. Realized ROAS (Cash Collected vs. Ad Spend)
   Standard dashboards show "Placed ROAS". Physisync tracks final Shopify delivery statuses, deducts returned orders, and calculates Realized ROAS:
   Realized ROAS = Placed ROAS × (1 - Attributed RTO Rate)
   If a campaign has a 3.0x Placed ROAS but a 30% RTO rate, Physisync correctly reports it as 2.1x Realized ROAS.

2. True RTO Rates (Calculated on Delivered Orders)
   Most standard platforms skew return rates by dividing returned orders by total placed orders. Physisync calculates RTO rate solely on fulfilled/delivered orders (Returned Orders / Delivered Orders), which gives us a completely accurate assessment of our courier/fulfillment performance.

3. Actionable Heuristic Alerts
   The system continuously scans our unified Meta Ads & Shopify logs to flag 5 critical operational risks:
   - Campaign RTO Spike (High return rates on specific ad sets)
   - Inventory Stockout Risk (High spend acceleration with low stock cover)
   - Creative Fatigue (CTR decays versus exposure frequency)
   - Margin Leakage (COD-heavy customer segments eroding margins)
   - Scaling Opportunities (Highly profitable prepaid cohorts safe to scale)

4. Closed-Loop Verification
   When our operators pause a campaign, reduce spend, or replenish inventory, the tool doesn't just trust that it was done. It runs differential checks between snapshots to verify that the action was taken and successfully resolved the margin leak.

If your ops or marketing team wants to audit the exact math, equations, and thresholds, I can share our detailed Technical Calculations Guide with them.

Let me know if you have any questions!

Best,
[Your Name]
```

---

### 💬 Template B: Slack / WhatsApp (Best for Growth Marketers & Ops Leads)
```markdown
Hey team! Quick breakdown on how Physisync runs calculations so everyone is aligned:

Standard Shopify dashboards show "Placed ROAS" (inflated checkout value). Physisync unifies Meta Ads spend with final Shopify delivery statuses to calculate *Realized ROAS* (cash collected).

Here is the quick logic:
1. Realized ROAS = Placed ROAS × (1 - RTO Rate). (A 3.0x ROAS with a 30% COD return rate is flagged as a 2.1x Realized ROAS).
2. RTO Rate = Returned Orders / Delivered Orders (no unfulfilled orders contamination).
3. The engine alerts us on:
   - Campaign RTO Spikes (when campaign RTO > 25% and COD orders > 50)
   - Inventory Risks (when stock cover is < 7 days and weekly spend growth > 15%)
   - Creative Fatigue (when CTR decays > 20% and frequency > 4.0)
   - Scaling Opportunities (when Realized ROAS > 4x and stock cover is > 14 days)

It also verifies our actions between file uploads (e.g. checks if campaign spend dropped by 80% after we paused it) to ensure we closed the loop.

Let me know if you want the deep-dive PDF with all the equations! 🚀
```

---

## 3. Core Differences Cheat Sheet (Quick Reference)

If a founder asks you: *"How is your calculation different from standard dashboards?"*, send them this comparison:

| Metric | Shopify / Meta default | Physisync Commerce Engine | Why the Physisync Way is Correct |
| :--- | :--- | :--- | :--- |
| **ROAS** | $\frac{\text{Placed Order Value}}{\text{Ad Spend}}$ | $\frac{\text{Delivered Order Value}}{\text{Ad Spend}}$ | Eliminates false scaling of high-RTO campaigns. |
| **RTO Rate** | $\frac{\text{Returned Orders}}{\text{Total Placed Orders}}$ | $\frac{\text{Returned Orders}}{\text{Delivered Orders}}$ | Prevents cancelled/unfulfilled orders from diluting actual return severity. |
| **Inventory Cover** | Total warehouse stock | $\frac{\text{Warehouse Stock}}{\text{Daily Velocity}}$ | Factors in current velocity so you don't scale traffic into stockouts. |
| **Action Loop** | Manual inspection | Automated differential verification | Verifies if spend reductions/reorders were *actually* completed. |

---
*This document is stored in your workspace at `docs/shareable_explainer.md` for easy access.*
