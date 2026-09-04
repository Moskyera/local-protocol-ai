"""
Crypto Payments Expert Skill for OpenHands
Professional Crypto Payments Specialist.
Focus: Crypto payments (Bitcoin, Ethereum, USDC, stablecoins, Lightning Network), on-chain/off-chain, wallets (MetaMask, WalletConnect), gateways (Coinbase Commerce, BitPay, Stripe Crypto, custom web3), KYC/AML, smart contract integration (if needed), security (private keys, audits), integration with React/3D e-commerce, off-ramps, compliance.
For serious projects accepting crypto.
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


class CryptoPaymentsExpert(ExpertSkill):
    """
    Senior Crypto Payments Specialist.
    Builds secure, compliant, high-converting crypto payment flows for modern websites.
    Integrates with React (Three.js product viewers), backend, security auditor, analytics, and even C++ for heavy on-chain computation.
    """

    def __init__(self):
        self.focus = "Professional crypto payment systems that are secure, compliant, user-friendly, and integrated with 3D e-commerce experiences."

    def build_crypto_payment_flow(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full crypto payment architecture + specific gateways + React/3D integration + security/compliance."""
        log.info(f"CryptoPaymentsExpert: Building crypto payments for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " crypto payments 2026", "crypto payments web3 e-commerce best practices 2026")
            except Exception:
                pass

        result = {
            "task": task,
            "crypto_architecture": self.crypto_architecture(),
            "specific_gateways": self.specific_gateways_with_snippets(),
            "react_3d_integration": self.react_3d_integration_snippets(),
            "cpp_heavy_computation_integration": self.cpp_heavy_computation_integration(),
            "security_compliance": self.security_compliance(),
            "conversion_optimization": self.conversion_optimization_crypto(),
            "research": research[:1300] if research else "2026 crypto payments: account abstraction, gasless tx, stablecoins dominance, regulatory compliance (MiCA etc.)."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("crypto:payments", f"{task} | professional crypto payments system for client work")
            except Exception:
                pass

        print("🪙 CryptoPaymentsExpert: Complete professional crypto payments platform delivered (with specific gateways, React+3D snippets, C++ integration).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior engineer expert in crypto payment integrations, security, KYC/AML and web3 UX.")
        self.mark_analysis(result)
        return result

    def crypto_architecture(self) -> Dict[str, str]:
        return {
            "recommended_stack": "Headless React/Next frontend + backend (Python/FastAPI or Node) + crypto provider (Stripe Crypto / Coinbase Commerce / custom web3.py/ethers.js) + on-chain monitoring",
            "key_components": "Crypto cart (multi-currency), payment selection (fiat + crypto), wallet connect, on-chain confirmation UI, off-ramp options, order fulfillment on tx confirmation",
            "integration_points": "React/3D (price in USDC/ETH updated live) ↔ Backend (webhooks for on-chain events) ↔ Analytics (crypto-specific events) ↔ Security (wallet signature verification)"
        }

    def specific_gateways_with_snippets(self) -> Dict[str, Any]:
        """Specific crypto payment gateways with production snippets, pros/cons, integration notes."""
        return {
            "stripe_crypto": {
                "why": "Easiest for existing Stripe users, supports USDC on multiple chains, fiat on/off ramps, strong compliance.",
                "setup": "Enable Crypto in Stripe Dashboard. Use Stripe Elements or Checkout with crypto option.",
                "react_snippet": """// React + Stripe Crypto (with 3D price update)
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_...');

function CryptoCheckout({ productPriceInUSDC, on3DConfigChange }) {
  const [clientSecret, setClientSecret] = useState('');
  // When 3D config changes price
  useEffect(() => {
    // Call backend to create PaymentIntent with crypto
    fetch('/create-crypto-intent', { method: 'POST', body: JSON.stringify({ amount: productPriceInUSDC * 100, currency: 'usd', payment_method_types: ['crypto'] }) })
      .then(res => res.json()).then(data => setClientSecret(data.clientSecret));
  }, [productPriceInUSDC]);

  return (
    <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: 'stripe' } }}>
      <PaymentElement />
      {/* 3D viewer here - price updates trigger new intent */}
    </Elements>
  );
}
""",
                "webhook": "Handle payment_intent.succeeded + crypto-specific events for on-chain confirmation.",
                "pros_cons": "Pros: Familiar API, compliance handled. Cons: Fees, chain support limited vs pure web3."
            },
            "coinbase_commerce": {
                "why": "Direct crypto, supports BTC/ETH/USDC, good for pure crypto brands, hosted checkout easy.",
                "react_snippet": """// Coinbase Commerce button in React + 3D
import { CoinbaseCommerceButton } from 'react-coinbase-commerce';

function CryptoPay({ amountUSDC, on3DSelect }) {
  return (
    <CoinbaseCommerceButton
      chargeId={createCharge(amountUSDC)} // backend creates charge
      onChargeSuccess={(e) => handleOnChainConfirm(e)}
    />
  );
}
""",
                "integration": "Create charge via API with metadata for 3D order. Poll or webhook for confirmed status.",
                "notes": "Supports Lightning for fast BTC."
            },
            "custom_web3": {
                "why": "Full control, lower fees, account abstraction (ERC-4337), gasless options.",
                "react_ethers_snippet": """// React + ethers.js + 3D (MetaMask/WalletConnect)
import { ethers } from 'ethers';
import { useState } from 'react';

async function payWithCrypto(priceInUSDC, threeDConfig) {
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const usdc = new ethers.Contract(USDC_ADDRESS, USDC_ABI, signer);
  
  // Update price from 3D config
  const amount = ethers.parseUnits(priceInUSDC.toString(), 6);
  const tx = await usdc.transfer(RECEIVER, amount);
  await tx.wait();
  // Confirm on backend + update 3D order
}
""",
                "security": "Always verify signature on backend. Use Permit2 for gasless. Audit contracts if custom.",
                "advanced": "Integrate with C++ expert for heavy on-chain computation (e.g. complex pricing oracle or ZK proofs compiled to WASM)."
            }
        }

    def react_3d_integration_snippets(self) -> str:
        """FULL INTEGRATED EXAMPLE: ethers.js (custom web3) + Stripe Crypto + WASM call from C++ expert.
        In a React + @react-three/fiber 3D product configurator.
        3D changes -> heavy calc via WASM (cpp-expert) -> update price -> pay with crypto (ethers or Stripe Crypto).
        """
        return """// FULL: React + Three.js 3D Configurator + ethers (custom) + Stripe Crypto + WASM (from cpp-expert)
// Heavy computation (dynamic pricing, risk, gas) offloaded to C++ WASM for speed/accuracy.

import { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { ethers } from 'ethers';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement } from '@stripe/react-stripe-js';

// Assume WASM module from cpp-expert (compiled C++ for heavy pricing/risk/gas calc)
import initWasm, { calculateHeavyPriceAndRisk } from './cpp_payment_wasm'; // built via cpp-expert

const stripePromise = loadStripe('pk_test_...'); // Stripe with crypto enabled

// USDC on Polygon (example) - or use your chain
const USDC_ADDRESS = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174';
const USDC_ABI = [ /* standard ERC20 ABI */ ];
const RECEIVER = '0xYourMerchantAddress';

async function initCppWasm() {
  await initWasm(); // from cpp-expert WASM build
}

function Full3DCryptoCheckout({ basePriceUSDC, threeDModel }) {
  const [configPrice, setConfigPrice] = useState(basePriceUSDC);
  const [riskScore, setRiskScore] = useState(0);
  const [gasEstimate, setGasEstimate] = useState(0);
  const [clientSecret, setClientSecret] = useState('');
  const [useCustomWeb3, setUseCustomWeb3] = useState(true); // toggle between ethers custom vs Stripe Crypto

  // 3D scene interaction handler
  const handle3DConfigChange = async (newOptions) => {
    // CALL WASM from cpp-expert for HEAVY computation (pricing engine + risk + gas est.)
    // This keeps 3D snappy; heavy math off main thread or in WASM
    const { finalPrice, risk, gas } = await calculateHeavyPriceAndRisk(
      basePriceUSDC,
      newOptions, // e.g. {material: 'gold', complexity: 5}
      Date.now() // for dynamic factors
    );
    
    setConfigPrice(finalPrice);
    setRiskScore(risk);
    setGasEstimate(gas);

    // Create intent on backend (Python/FastAPI recommended) - pass 3D config + WASM result
    const res = await fetch('/api/create-crypto-payment-intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount: Math.round(finalPrice * 1_000_000), // USDC 6 decimals
        currency: 'usd',
        payment_method_types: ['crypto'],
        metadata: { threeDConfig: newOptions, wasmRisk: risk, wasmGas: gas }
      })
    });
    const { clientSecret: secret } = await res.json();
    setClientSecret(secret);
  };

  // ETHERES.JS CUSTOM WEB3 (full control, lower fees, integrate with WASM result)
  const payWithEthersCustom = async () => {
    if (!window.ethereum) throw new Error('Install MetaMask/WalletConnect');
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const usdc = new ethers.Contract(USDC_ADDRESS, USDC_ABI, signer);

    // Use WASM result for exact amount (verified on backend too)
    const amount = ethers.parseUnits(configPrice.toString(), 6);
    
    // Optional: gas estimation can come from WASM too
    const gas = await usdc.transfer.estimateGas(RECEIVER, amount);
    console.log('WASM-assisted gas:', gasEstimate || gas.toString());

    const tx = await usdc.transfer(RECEIVER, amount);
    const receipt = await tx.wait();
    
    // Confirm on backend + update 3D order (pass tx hash + WASM metadata)
    await fetch('/api/confirm-crypto-payment', {
      method: 'POST',
      body: JSON.stringify({ txHash: receipt.hash, threeDConfig: /*...*/, wasmResult: {price: configPrice, risk: riskScore} })
    });
    alert('Crypto payment confirmed on-chain!');
  };

  // STRIPE CRYPTO (easier compliance, hosted or Elements)
  const payWithStripeCrypto = async () => {
    if (!clientSecret) return;
    const stripe = await stripePromise;
    const { error } = await stripe.confirmPayment({
      elements: /* from Elements provider */,
      confirmParams: { return_url: window.location.href },
      // Stripe handles crypto on-ramp / direct crypto payment
    });
    if (error) console.error(error);
  };

  useEffect(() => { initCppWasm(); }, []);

  return (
    <div>
      <Canvas onInteraction={handle3DConfigChange}> {/* Your Three.js 3D model here */} </Canvas>
      
      <div>Price: {configPrice} USDC | Risk: {riskScore} | Est. Gas: {gasEstimate}</div>

      <button onClick={() => setUseCustomWeb3(true)}>Use Custom Web3 (ethers)</button>
      <button onClick={() => setUseCustomWeb3(false)}>Use Stripe Crypto</button>

      {useCustomWeb3 ? (
        <button onClick={payWithEthersCustom} disabled={!window.ethereum}>
          Pay with USDC (MetaMask + WASM price)
        </button>
      ) : (
        clientSecret && (
          <Elements stripe={stripePromise} options={{ clientSecret }}>
            <PaymentElement />
            <button onClick={payWithStripeCrypto}>Pay with Stripe Crypto</button>
          </Elements>
        )
      )}

      {/* Backend (Python) verifies tx + WASM result before fulfilling 3D order */}
    </div>
  );
}
"""

    def cpp_heavy_computation_integration(self) -> str:
        """How to integrate with C++ expert for heavy payment computation (pricing engines, risk models, ZK)."""
        return """Integration with cpp-expert for heavy computation in payments:
- Use C++ expert to build pricing engine or fraud/risk scoring model (complex math, ML inference).
- Compile to WASM via Emscripten (see cpp-expert.build_high_performance_components).
- Expose clean JS API from WASM.
- Call from React 3D configurator or checkout: e.g. heavyPriceCalc(threeDOptions) returns exact USDC amount instantly.
- For crypto: on-chain verification or ZK proof of computation (via cpp-expert WASM module).
- Security: Never trust client calc - always re-verify on backend (Python or C++ service).
- Example handoff: "cpp-expert: build WASM module for dynamic 3D pricing + crypto amount calc with gas estimation"
- Performance: Offload from main thread, use Web Workers.

This keeps the 3D experience snappy while doing heavy lifting client-side where possible, with server verification.
"""

    def security_compliance(self) -> list:
        return [
            "Never store private keys (use wallet connect only)",
            "Verify all on-chain tx on backend (confirmations, amount, to address)",
            "KYC/AML via provider (Coinbase, Circle) for high volume",
            "Smart contract audits if custom (coordinate with security-auditor)",
            "Rate limit wallet connections, monitor for MEV/sandwich attacks in UX",
            "PCI + crypto specific (travel rule for large tx)"
        ]

    def conversion_optimization_crypto(self) -> list:
        return [
            "Show live fiat/crypto price toggle (with 3D total)",
            "Gas fee estimator + 'pay with Lightning for instant'",
            "Multiple currency support (USDC preferred for stability)",
            "Wallet detection + 'connect to pay' in 3D viewer",
            "Abandoned crypto cart recovery (email with payment link + price lock)",
            "Test UX with real wallets on mobile (thumb-friendly connect buttons)"
        ]

# Register
crypto_payments_expert = CryptoPaymentsExpert()
print("🪙 CryptoPaymentsExpert registered. Ready for sub_type='crypto'. Professional crypto payments with React+3D + C++ integration.")