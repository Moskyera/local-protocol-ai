"""
Analytics Specialist Skill for OpenHands
Professional Analytics & Growth Specialist for serious business websites.
Focus: Measurement strategy, tracking implementation, A/B testing, conversion rate optimization, data visualization, ROI reporting, data-driven iteration.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


from openhands_skills.expert_base import ExpertSkill


class AnalyticsSpecialist(ExpertSkill):
    """
    Senior Analytics & Growth Specialist.
    Turns website traffic into actionable business intelligence and continuous improvement.
    Essential for any serious client project where results matter.
    """

    def __init__(self):
        self.focus = "Making every website a measurable growth engine with professional-grade tracking, testing, and insights."

    def setup_analytics_and_optimization(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Complete measurement plan + implementation + optimization roadmap."""
        log.info(f"AnalyticsSpecialist: Setting up analytics for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " analytics 2026", "web analytics and CRO best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "measurement_strategy": self.measurement_strategy(),
            "tracking_implementation": self.tracking_implementation(),
            "server_side_and_privacy": self.server_side_and_privacy_setup(),
            "a_b_testing_framework": self.ab_testing_framework(),
            "advanced_cro": self.advanced_conversion_optimization(),
            "reporting_dashboard": self.reporting_dashboard(),
            "kpi_examples": self.kpi_examples(task),
            "integration_with_team": self.integration_with_full_team(),  # method defined below
            "research": research[:1200] if research else "2026 privacy-first analytics, server-side tracking, AI-assisted insights, advanced attribution."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("analytics:growth", f"{task} | professional measurement & optimization system")
            except Exception:
                pass

        print("📈 AnalyticsSpecialist: DEEP professional analytics & growth system delivered (with server-side, advanced CRO, team integration).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior analytics engineer expert in tracking, experimentation, attribution and conversion optimisation.")
        self.mark_analysis(result)
        return result

    def server_side_and_privacy_setup(self) -> Dict[str, Any]:
        """Deeper privacy-compliant, server-side tracking for modern regulations and accuracy."""
        return {
            "recommended": "Google Tag Manager Server-side + BigQuery + GA4 + PostHog (self-hosted option for privacy)",
            "consent": "Consent Mode v2, granular CMP (OneTrust/Cookiebot), cookieless where possible (server-side events)",
            "privacy": "GDPR/CCPA ready, data minimization, user deletion flows, no PII in client-side",
            "advanced": "First-party data, enhanced conversions, offline conversion imports, custom dimensions for 3D events",
            "tools": "Segment/RudderStack for routing, Amplitude/Mixpanel for product analytics, Hotjar/Clarity for qualitative"
        }

    def advanced_conversion_optimization(self) -> list:
        """Deeper CRO with AI, multi-armed bandit, personalization."""
        return [
            "Funnel + cohort analysis (where users drop, by device/3D interaction)",
            "Form + microcopy optimization with heatmaps/session replays",
            "CTA, urgency, trust signals A/B + multi-armed bandit testing",
            "Personalization: dynamic content based on traffic source, behavior, 3D engagement (with privacy)",
            "Mobile-specific: thumb-zone CTAs, one-handed flows, progressive loading impact on conversion",
            "AI-assisted: use research tools for winning patterns, predictive LTV models",
            "Full attribution: multi-touch, data-driven, incrementality testing"
        ]

    def measurement_strategy(self) -> Dict[str, Any]:
        return {
            "north_star": "Business outcome (e.g. qualified leads, bookings, signups, revenue)",
            "funnel_stages": ["Awareness", "Interest", "Consideration", "Conversion", "Retention/Advocacy"],
            "key_events": "Page views, scrolls, clicks, form submits, 3D interactions, video plays, add-to-cart, purchases",
            "privacy_compliance": "Consent mode, cookieless tracking where possible, GDPR/CCPA ready"
        }

    def tracking_implementation(self) -> str:
        return """Recommended stack (add to website-builder output):
- Google Analytics 4 (enhanced measurement + server-side)
- Google Tag Manager for flexibility
- Meta Pixel / LinkedIn / other ad pixels (with consent)
- Hotjar / Microsoft Clarity for session recordings & heatmaps
- Custom events for key 3D / interaction moments
- Server-side tagging via Google Tag Manager Server-side or Segment
"""

    def ab_testing_framework(self) -> list:
        return [
            "Hypothesis → Variant → Measurement → Learn → Iterate",
            "Tools: Google Optimize (sunset) → VWO / Optimizely / Convert",
            "Statistical significance rules (min 95%, proper sample size)",
            "Always test one variable at a time for clear learnings",
            "Document everything in a central experiment repo"
        ]

    def conversion_optimization(self) -> list:
        return [
            "Funnel analysis (where users drop off)",
            "Form optimization (fields, friction, microcopy)",
            "CTA testing (placement, copy, color, urgency)",
            "Trust signals (testimonials, guarantees, security badges)",
            "Mobile-specific CRO (thumb reach, load speed, tap targets)"
        ]

    def reporting_dashboard(self) -> str:
        return """Key reports for client:
- Acquisition (channels, campaigns)
- Behavior (top pages, 3D engagement, scroll depth)
- Conversion (funnel, goal completion, revenue if ecom)
- Audience (demographics, devices, new vs returning)
- Experiment results (A/B winner + lift + confidence)
Monthly executive summary + raw data access."""

    def kpi_examples(self, project: str) -> dict:
        """KPIs for THIS project.

        Returned the same five generic rows for every input — including
        "3D interaction rate" for a book publisher. Measured identical for a
        crypto exchange and a children's publisher.
        """
        return self.analyse(
            "Name the KPIs that actually matter for this specific project, and "
            "say for each one why it matters HERE and what a healthy value looks "
            "like. Skip any metric that would be meaningless for this business.",
            {"project": project},
            reference={"generic_web_kpis": {
                "traffic": "Sessions, users, pageviews",
                "engagement": "Avg. session duration, pages/session",
                "conversion": "Form submits, demo requests, purchases / revenue",
                "quality": "Bounce rate, time to first interaction, lead quality score",
                "business": "Cost per acquisition, LTV, ROI on marketing spend",
            }},
            max_tokens=1200,
        )

    def integration_with_full_team(self) -> str:
        """How deeper analytics integrates with the complete professional team. Includes explicit payment events."""
        return """Explicit integration points for full chain (call setup_analytics... early):
- With website-builder / react / threejs: Track custom events for 3D interactions, product views, cart adds from 3D configs. Example: track('3d_config_change', {price: wasmPrice, material: 'gold', risk: wasmRisk})
- With ecommerce-specialist + crypto_payments_expert: Full payment funnel with GATEWAY-SPECIFIC events:
  - 'add_to_cart' (with 3D config metadata)
  - 'checkout_started'
  - 'payment_intent_created' (stripe_id or tx_hash, amount, currency, gateway: 'stripe_crypto' | 'custom_web3' | 'coinbase')
  - 'payment_success' / 'payment_failed' (include on-chain receipt, wasmResult, gasUsed)
  - 'crypto_tx_confirmed' (confirmations, finalPrice)
- With project-manager: Provide analytics dashboard as part of client presentation deliverables; A/B results feed into quality gates; explicit payment funnel report.
- With security/legal: Privacy-compliant tracking only (consent, no PII); audit tracking setup for GDPR; log security events (failed signatures, high risk from WASM).
- With devops/maintenance: Monitoring dashboards (Sentry + analytics) for post-launch; regression alerts on conversion drops or payment failure spikes.
- With brand/content: Event naming aligned with brand voice; content experiments tied to messaging tests.
- With backend/python: Server-side events from API (orders, user actions) for accurate attribution. The python endpoints above should fire analytics.track('payment_event', {...}).
- With cpp/illustration: Performance metrics on heavy asset loads; 3D render times + WASM calc time as custom metrics.
Call analytics-specialist.setup... EARLY in project for baseline, then iteratively with CRO gates. Use server-side events for payment success to avoid client tampering."""

    def payment_events_integration(self) -> str:
        """Explicit code/pattern for logging payment events from the Python backend endpoints + frontend."""
        return """# In your FastAPI /confirm-crypto-payment (or webhook handler):
from analytics_client import track  # your wrapper (PostHog, Segment, GA4 Measurement Protocol, etc.)

@app.post("/api/confirm-crypto-payment")
async def confirm(...):
    # ... verification ...
    track("payment_success", {
        "gateway": "custom_web3" or "stripe_crypto",
        "amount": req.wasm_result["price"],
        "currency": "USDC",
        "tx_hash": req.tx_hash,
        "three_d_config": req.three_d_config,
        "wasm_risk": req.wasm_result["risk"],
        "gas_used": req.wasm_result.get("gas"),
        "user_id": current_user.id,
        "session_id": ...,  # from cookie or header
    }, user_id=...)
    
    # Also track on frontend after success:
    # analytics.track('crypto_tx_confirmed', {txHash, finalPrice, confirmations})

# Frontend (in the payWithEthersCustom / payWithStripeCrypto success):
# analytics.track('payment_intent_created', {clientSecret or tx, amount: configPrice, gateway: useCustomWeb3 ? 'ethers' : 'stripe_crypto', wasmResult})
"""

# Register
analytics_specialist = AnalyticsSpecialist()
print("📈 AnalyticsSpecialist registered. Ready for sub_type='analytics'. Serious projects measure everything.")

# Register
analytics_specialist = AnalyticsSpecialist()
print("📈 AnalyticsSpecialist registered. Ready for sub_type='analytics'. Serious projects measure everything.")