import os
import json
import urllib.request
import urllib.error
from typing import Any
from .rules import Signal

class LLMEnrichmentService:
    @staticmethod
    def enrich_signal(signal: Signal) -> dict[str, Any]:
        """
        Enriches a mathematically detected signal with deep e-commerce strategic narrative.
        Queries live OpenAI if configured; otherwise gracefully falls back
        to a highly specific e-commerce domain mockup.
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        
        # Build prompt that forces structured JSON output
        prompt = f"""
        You are a seasoned, elite e-commerce growth strategist and supply chain analyst.
        We have mathematically detected an anomaly in our e-commerce operations with these parameters:
        - Signal Type: {signal.signal_type}
        - Issue Category: {signal.issue_type}
        - Title: {signal.title}
        - Severity: {signal.severity}
        - Heuristic Rule triggered: {signal.rule}
        - Mathematical Explanation: {signal.explanation}
        - Core Telemetry Metrics: {", ".join(signal.cross_system_signals)}
        - Affected Campaigns: {signal.affected_campaigns}
        - Affected SKUs: {signal.affected_skus}

        Based on these facts, perform a multi-system business impact analysis and generate enriched strategic recommendations.
        Your response MUST be a single, valid JSON object with the exact keys described below:
        {{
            "title": "A highly readable, impact-oriented title for the decision card",
            "explanation": "A concise paragraph explaining exactly how this issue impacts margins, customer cohorts, and supply-chain efficiency.",
            "recommendation": "A professional executive summary of the primary suggested business action.",
            "confidence_explanation": "A thorough explanation of the data points and alignments confirming the confidence score.",
            "recommended_actions": [
                "Concrete step 1 (e.g. adjust bid, launch specific copy, allocate inventory)",
                "Concrete step 2",
                "Concrete step 3"
            ],
            "risk_projection": [
                {{"horizon": "24 hr", "impact": "Immediate impact description"}},
                {{"horizon": "48 hr", "impact": "Medium-term progression"}},
                {{"horizon": "72 hr", "impact": "Long-term compound failure mode if ignored"}}
            ],
            "relationship_edges": [
                {{"from": "Entity A", "to": "Entity B", "label": "causal action label", "strength": "strong/medium/weak"}}
            ]
        }}

        Do NOT wrap the output in markdown code blocks like ```json ... ```. Output raw JSON ONLY.
        """

        if openai_key:
            print(f"🔮 [LLM LAYER] Live query routed to OpenAI...", flush=True)
            result = LLMEnrichmentService._query_openai(prompt, openai_key)
            if result:
                return result

        # Graceful fallback logic (acts as a premium mock generator)
        print(f"🔮 [LLM LAYER] Running offline mock fallback enrichment for {signal.signal_type}...", flush=True)
        return LLMEnrichmentService._generate_fallback(signal)

    @staticmethod
    def _query_openai(prompt: str, api_key: str) -> dict[str, Any] | None:
        url = "https://api.openai.com/v1/chat/completions"
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional e-commerce operations strategist. Respond ONLY in valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_content = res_body["choices"][0]["message"]["content"]
                return json.loads(text_content.strip())
        except Exception as e:
            print(f"⚠️ [LLM LAYER] OpenAI API call failed: {e}. Falling back...", flush=True)
            return None

    @staticmethod
    def _generate_fallback(signal: Signal) -> dict[str, Any]:
        """Generates top-tier e-commerce insights tailored to each specific rule type when offline."""
        sku = signal.affected_skus[0] if signal.affected_skus else "Products"
        campaign = signal.affected_campaigns[0] if signal.affected_campaigns else "Marketing campaigns"
        
        if signal.signal_type == "InventoryRisk":
            spend_signal = next((s for s in signal.cross_system_signals if "spend growth" in s.lower()), "")
            spend_growth = 0.0
            if spend_signal and ":" in spend_signal:
                try:
                    spend_growth = float(spend_signal.split(":", 1)[1].strip().replace("%", ""))
                except ValueError:
                    spend_growth = 0.0
            cover_signal = next((s for s in signal.cross_system_signals if "inventory cover" in s.lower()), "")
            cover_days = "limited"
            if cover_signal and ":" in cover_signal:
                cover_days = cover_signal.split(":", 1)[1].strip().replace("days", "").strip()
            if spend_growth >= 15:
                explanation = (
                    f"{sku} has approximately {cover_days} day(s) of inventory cover remaining while ad spend "
                    f"accelerated {spend_growth:.1f}% week over week. Stockout risk is elevated without confirmed inbound inventory."
                )
            else:
                explanation = (
                    f"{sku} has approximately {cover_days} day(s) of inventory cover remaining based on recent sales velocity. "
                    "Without confirmed inbound inventory, stockout risk is elevated. Revenue realization may be constrained "
                    "if demand continues at current levels."
                )
            return {
                "title": signal.title,
                "explanation": explanation,
                "recommendation": (
                    "Submit a priority restock order immediately. Reduce prospecting spend until inbound inventory is confirmed."
                ),
                "confidence_explanation": (
                    "Inventory and velocity are verified from the latest upload, but open POs, supplier lead times, "
                    "and inbound shipment ETAs are unavailable — confidence is capped until restock visibility improves."
                ),
                "recommended_actions": signal.recommended_actions,
                "risk_projection": signal.risk_projection,
                "relationship_edges": signal.relationship_edges,
            }
            
        elif signal.signal_type == "CampaignRTOSpike":
            return {
                "title": f"Action Required: High cash return RTO rate spike on {campaign}",
                "explanation": (
                    f"The ad campaign {campaign} has crossed into an unprofitable mix of Cash-on-Delivery (COD) "
                    f"orders. The high volume of cash orders is driving a major increase in customer RTO "
                    f"(Return-to-Origin), which compresses net profit margins due to high double-sided courier logistics fees."
                ),
                "recommendation": f"Pause campaign {campaign} immediately, or restrict the targeting parameters to prepaid-only audiences.",
                "confidence_explanation": (
                    "Attributed Shopify order verification confirms RTO rate exceeds 25%, with the COD order ratio "
                    "staying above 50% across matching attribution channels."
                ),
                "recommended_actions": [
                    f"Pause {campaign} to immediately halt margin leakage",
                    "Add an attractive 10% discount incentive on Checkout page for prepaid UPI payments",
                    "Narrow audience targeting to exclude historically high-RTO geographical regions"
                ],
                "risk_projection": [
                    {"horizon": "24 hr", "impact": f"Rs 6,200 additional cash-based margins eroded by delivery returns"},
                    {"horizon": "48 hr", "impact": "Unclaimed returned packages compound, tying up vital working capital"},
                    {"horizon": "72 hr", "impact": "Blended margin for the footwear collection drops to critical single digits"}
                ],
                "relationship_edges": [
                    {"from": campaign, "to": "COD Orders", "label": "drives high cash mix", "strength": "strong"},
                    {"from": "COD Orders", "to": "RTO Shipments", "label": "increases returns", "strength": "strong"},
                    {"from": "RTO Shipments", "to": "Realized Margins", "label": "compresses returns overhead", "strength": "strong"}
                ]
            }
            
        elif signal.signal_type == "CreativeFatigue":
            roas_signal = next((s for s in signal.cross_system_signals if "ROAS is" in s), "")
            return {
                "title": f"Refresh Campaign Creatives: High ad exposure frequency on {campaign}",
                "explanation": (
                    f"Ad frequency within campaign {campaign} has reached saturated exposure thresholds. "
                    f"CTR decay indicates creative fatigue, but {roas_signal or 'ROAS may still be holding'}. "
                    f"This is a refresh decision, not a pause decision: keep the campaign economics under review while rotating creative."
                ),
                "recommendation": "Launch fresh creative variations and refresh active hooks; do not pause unless delivered ROAS also falls below target.",
                "confidence_explanation": (
                    "Dynamic analysis confirms ad frequency exceeds 4.0 exposures and click-through rates "
                    "have experienced a steep decay of 20% compared to baseline averages."
                ),
                "recommended_actions": [
                    "Deploy two new visual and text hook angles in the main campaign",
                    "De-prioritize and cap budget on the fatiguing static asset",
                    "Promote successful user-generated content (UGC) into the ad set"
                ],
                "risk_projection": [
                    {"horizon": "24 hr", "impact": "Ad auction costs rise; traffic acquisition quality drops"},
                    {"horizon": "48 hr", "impact": "CTR decay triggers optimization penalty in ad platforms"},
                    {"horizon": "72 hr", "impact": "Campaign target return on spend erodes below profitable limits"}
                ],
                "relationship_edges": [
                    {"from": campaign, "to": "High Exposure", "label": "saturates viewers", "strength": "strong"},
                    {"from": "High Exposure", "to": "CTR Decay", "label": "causes visual fatigue", "strength": "strong"},
                    {"from": "CTR Decay", "to": "CAC Inflation", "label": "raises click acquisition cost", "strength": "medium"}
                ]
            }
            
        elif signal.signal_type == "NewLaunchRisk":
            freq_signal = next((s for s in signal.cross_system_signals if "frequency" in s.lower()), "")
            spend_signal = next((s for s in signal.cross_system_signals if "spend" in s.lower()), "")
            return {
                "title": signal.title,
                "explanation": (
                    "Newly launched ad set is currently performing below target ROAS while remaining in a low-frequency learning phase. "
                    "Additional delivery data is required before determining whether underperformance is driven by creative, audience, "
                    "offer, or landing-page factors."
                ),
                "recommendation": (
                    "Early launch performance is below target. Continue gathering delivery data while reviewing creatives, "
                    "offer positioning, and audience targeting. Limit spend escalation until ROAS stabilizes."
                ),
                "confidence_explanation": (
                    "Launch rule inputs are verified from Meta spend and placed ROAS, but campaign-level delivery attribution "
                    "and historical baseline comparisons are incomplete. Confidence is capped until more delivery data is collected."
                ),
                "recommended_actions": [
                    "Collect more delivery data before major creative changes",
                    "Review audience targeting and offer-page conversion",
                    "Cap spend until frequency exceeds 1.5 and ROAS stabilizes",
                ],
                "risk_projection": signal.risk_projection,
                "relationship_edges": signal.relationship_edges,
            }

        elif signal.signal_type == "StateRTOLeakage":
            state_name = signal.cross_system_signals[0].split(":", 1)[1].strip() if signal.cross_system_signals else "the flagged state"
            orders_signal = next((s for s in signal.cross_system_signals if "Total orders" in s), "")
            brand_rto_signal = next((s for s in signal.cross_system_signals if "Brand average RTO" in s), "")
            cod_signal = next((s for s in signal.cross_system_signals if "COD mix" in s), "")
            delta_signal = next((s for s in signal.cross_system_signals if "State RTO delta" in s), "")
            monitor_case = "Regional COD Risk" in signal.title
            return {
                "title": signal.title,
                "explanation": signal.explanation,
                "recommendation": signal.recommendation if not monitor_case else (
                    f"Monitor {state_name} COD dependence ({cod_signal.split(':', 1)[1].strip() if cod_signal else 'high COD'}). "
                    f"Test prepaid incentives before restricting shipping — regional RTO ({delta_signal.split(':', 1)[1].strip() if delta_signal else 'near brand average'}) "
                    "does not yet prove a uniquely poor state profile."
                ),
                "confidence_explanation": (
                    f"{orders_signal or 'Limited order volume'} in this state means the regional RTO rate can swing sharply "
                    f"with a few delivery-status changes. {brand_rto_signal or 'Brand benchmark'} provides comparison context, "
                    "but confidence remains capped until sample size grows."
                ),
                "recommended_actions": signal.recommended_actions,
                "risk_projection": signal.risk_projection,
                "relationship_edges": signal.relationship_edges,
            }

        elif signal.signal_type == "AudienceAudit":
            campaign = signal.affected_campaigns[0] if signal.affected_campaigns else "flagged campaign"
            return {
                "title": signal.title,
                "explanation": signal.explanation,
                "recommendation": signal.recommendation,
                "confidence_explanation": (
                    "Spend and placed ROAS are verified from Meta, but delivered revenue and campaign RTO rely on "
                    "brand-level fallback until campaign mapping completes — confidence is capped accordingly."
                ),
                "recommended_actions": signal.recommended_actions,
                "risk_projection": signal.risk_projection,
                "relationship_edges": signal.relationship_edges,
            }

        elif signal.signal_type == "MarginLeakage":
            return {
                "title": f"Margin Alert: COD leakage on {sku}",
                "explanation": (
                    f"Orders for {sku} are heavily favoring Cash-on-Delivery (COD) over prepaid options. "
                    f"While topline numbers look positive, high return rates for cash delivery "
                    f"are absorbing potential profits, leading to major margin leakage."
                ),
                "recommendation": "Incentivize digital and UPI payment options at checkout for this SKU and reduce COD-heavy demand.",
                "confidence_explanation": (
                    "Heuristics confirm segment cash preference exceeds 60% and return-on-delivered "
                    "metrics indicate severe profit erosion."
                ),
                "recommended_actions": [
                    "Implement a prominent '5% extra discount for online payments' Checkout promotion",
                    "Send automatic WhatsApp confirmations to confirm delivery address for COD orders",
                    "Limit active prospecting ad budgets targeting COD-heavy audiences"
                ],
                "risk_projection": [
                    {"horizon": "24 hr", "impact": "Additional returns overhead reduces segment contribution margins"},
                    {"horizon": "48 hr", "impact": "Increased package returns burden the logistics warehouse"},
                    {"horizon": "72 hr", "impact": "Segment profit contribution erodes completely, leaving zero net return"}
                ],
                "relationship_edges": [
                    {"from": sku, "to": "COD Preference", "label": "prefers cash on delivery", "strength": "strong"},
                    {"from": "COD Preference", "to": "Returned Shipments", "label": "drives return risk", "strength": "strong"},
                    {"from": "Returned Shipments", "to": "Net Margin", "label": "compresses returns cost", "strength": "strong"}
                ]
            }
            
        # Default fallback if signal type is unexpected
        return {
            "title": signal.title,
            "explanation": signal.explanation,
            "recommendation": signal.recommendation,
            "confidence_explanation": signal.confidence_explanation,
            "recommended_actions": signal.recommended_actions,
            "risk_projection": signal.risk_projection,
            "relationship_edges": signal.relationship_edges
        }
