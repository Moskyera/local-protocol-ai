"""
E-commerce Specialist Skill for OpenHands
Professional E-commerce Specialist.
Focus: Payment integrations (Stripe, PayPal, etc.), cart & checkout flows, inventory management, taxes/VAT, shipping, PCI DSS compliance, fraud prevention, conversion optimization for e-commerce websites.
For serious commercial projects.
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


class EcommerceSpecialist:
    """
    Senior E-commerce Specialist.
    Builds secure, high-converting, compliant e-commerce experiences.
    Integrates deeply with backend, security, frontend (React/3D), and analytics.
    """

    def __init__(self):
        self.focus = "Turning websites into professional, secure, and profitable e-commerce platforms ready for real business."

    def build_ecommerce_platform(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full e-commerce architecture + payment flows + compliance + optimization plan."""
        log.info(f"EcommerceSpecialist: Building e-commerce for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " e-commerce 2026", "modern e-commerce platform best practices payments PCI")
            except Exception:
                pass

        result = {
            "task": task,
            "ecommerce_architecture": self.ecommerce_architecture(),
            "payment_integration_guide": self.payment_integration_guide(),
            "checkout_flow_optimization": self.checkout_flow_optimization(),
            "inventory_taxes_shipping": self.inventory_taxes_shipping(),
            "pci_compliance_checklist": self.pci_compliance_checklist(),
            "fraud_prevention": self.fraud_prevention(),
            "conversion_optimization": self.conversion_optimization(),
            "research": research[:1200] if research else "2026 e-commerce trends: headless commerce, subscription models, global payments, AI fraud detection."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("ecommerce:platform", f"{task} | professional e-commerce system for client work")
            except Exception:
                pass

        print("🛒 EcommerceSpecialist: Complete professional e-commerce platform plan delivered.")
        return result

    def ecommerce_architecture(self) -> Dict[str, str]:
        return {
            "recommended_stack": "Headless (Next.js/React frontend + Stripe/Shopify/Commercetools backend) or full custom with secure backend",
            "key_components": "Product catalog, cart (persistent), checkout (multi-step or one-page), payments, order management, customer accounts",
            "integration_points": "Frontend (React/3D product viewers) ↔ Backend ↔ Payment providers ↔ Analytics ↔ Inventory/ERP"
        }

    def payment_integration_guide(self) -> Dict[str, Any]:
        """Specific payment gateways with production-ready details, code patterns, security notes."""
        return {
            "stripe": {
                "why": "Most flexible, excellent docs, global coverage, strong fraud tools (Radar)",
                "key_features": "Payment Intents (recommended), Stripe Elements (custom UI), Checkout (hosted), Subscriptions, Connect for marketplaces",
                "react_3d_integration_snippet": """// Stripe Elements + React + Three.js 3D (price updates from 3D config)
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement } from '@stripe/react-stripe-js';
import { useState, useEffect } from 'react';

const stripePromise = loadStripe('pk_test_...');

function Stripe3DCheckout({ basePrice, on3DConfigUpdate }) {
  const [price, setPrice] = useState(basePrice);
  const [clientSecret, setClientSecret] = useState('');

  // Called from Three.js scene when user changes options (color, material)
  const handle3DPriceChange = (newConfig) => {
    const newPrice = calculateDynamicPrice(basePrice, newConfig); // can delegate to cpp-expert WASM for heavy math
    setPrice(newPrice);
    
    fetch('/api/create-payment-intent', {
      method: 'POST',
      body: JSON.stringify({ amount: newPrice * 100, currency: 'usd' })
    }).then(res => res.json()).then(data => setClientSecret(data.clientSecret));
  };

  return (
    <>
      {/* Three.js Canvas here - on interaction call handle3DPriceChange */}
      {clientSecret && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <PaymentElement />
        </Elements>
      )}
    </>
  );
}
""",
                "webhooks": "Listen to payment_intent.succeeded, invoice.paid etc. for order fulfillment. Verify signatures.",
                "security": "Never handle raw card data. Use Elements or Checkout. Enable 3DS. Use Radar for fraud.",
                "example_setup": "Create PaymentIntent server-side (Python/FastAPI), confirm on client with clientSecret. Handle next_action for 3DS."
            },
            "paypal": {
                "why": "High trust, good for international, Pay Later options",
                "integration": "PayPal JS SDK or Braintree. Hosted fields or full redirect.",
                "react": "paypal-react or custom buttons. Trigger after cart/3D selection.",
                "webhooks": "PAYMENT.CAPTURE.COMPLETED etc.",
                "notes": "Good fallback alongside Stripe."
            },
            "apple_pay_google_pay": {
                "why": "Fastest mobile conversion",
                "implementation": "Via Stripe/PayPal/Braintree. Domain verification required.",
                "react": "Use stripe or paypal SDK with canMakePayment check. Perfect for 3D mobile experiences.",
                "security": "Tokenized, no card data exposed."
            },
            "local_international": {
                "europe": "iDEAL, Bancontact, Sofort, Giropay via Stripe/Mollie/Adyen",
                "india": "UPI, Razorpay",
                "latam": "Mercado Pago",
                "asia": "Alipay, WeChat Pay (via Stripe)",
                "recommendation": "Use Stripe or Adyen for unified global coverage with local methods."
            },
            "crypto_payments": {
                "note": "See dedicated crypto-payments-expert for full details (Stripe Crypto, Coinbase, custom web3 with React+3D snippets and C++ integration for heavy pricing/risk calc).",
                "integration": "Call crypto_payments_expert.build_crypto_payment_flow() alongside this for hybrid fiat/crypto checkout. 3D price in USDC/ETH updated live."
            },
            "general_best_practices": [
                "Tokenization always",
                "3D Secure / SCA where required",
                "Webhooks for reliable fulfillment (idempotency keys)",
                "Test thoroughly with test cards/tokens",
                "PCI SAQ-A or higher if custom fields",
                "Integrate with analytics for payment funnel drop-off",
                "Heavy computation (dynamic pricing, risk): delegate to cpp-expert for WASM module"
            ]
        }

    def checkout_flow_optimization(self) -> list:
        return [
            "Guest checkout by default (account optional)",
            "Address autofill + validation (Google Places / Loqate)",
            "Real-time shipping rates and tax calculation",
            "Express checkout (Apple Pay / Google Pay / PayPal)",
            "Abandoned cart recovery emails + retargeting",
            "Progress indicators and trust signals (security badges, reviews)"
        ]

    def inventory_taxes_shipping(self) -> list:
        return [
            "Real-time inventory sync (avoid overselling)",
            "Multi-warehouse support if scaling",
            "Automated tax calculation (Avalara / TaxJar / built-in for EU VAT)",
            "Shipping rules engine (weight, destination, carrier APIs)",
            "International: duties, customs, localized checkout"
        ]

    def pci_compliance_checklist(self) -> list:
        return [
            "Use PCI-compliant payment provider (never store PAN yourself)",
            "HTTPS everywhere (TLS 1.3+)",
            "Regular vulnerability scans and penetration tests (SAQ or ROC depending on volume)",
            "Secure coding for any custom payment flows",
            "Logging without sensitive data (no card numbers in logs)"
        ]

    def fraud_prevention(self) -> list:
        return [
            "3D Secure / Strong Customer Authentication",
            "Address Verification Service (AVS) + CVV checks",
            "Device fingerprinting and behavioral signals",
            "Velocity checks and blacklists",
            "Machine learning fraud models (via Stripe Radar or similar)"
        ]

    def conversion_optimization(self) -> list:
        return [
            "A/B test checkout steps, payment methods, upsells",
            "One-click reordering for logged-in users",
            "Personalized recommendations (with privacy compliance)",
            "Clear return policy and trust badges",
            "Mobile-first checkout (thumb-friendly, minimal typing)"
        ]

# Register
ecommerce_specialist = EcommerceSpecialist()
print("🛒 EcommerceSpecialist registered. Ready for sub_type='ecommerce'. Professional e-commerce ready for real revenue.")