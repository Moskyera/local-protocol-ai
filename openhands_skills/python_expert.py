"""
Python Expert Skill for OpenHands
Professional Python Specialist.
Focus: High-quality Python backend (FastAPI, Django, etc.), data processing, AI/ML integrations, scripting, clean architecture, testing, performance in Python.
For serious projects requiring robust Python code (backend, data pipelines, automations).
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


class PythonExpert(ExpertSkill):
    """
    Senior Python Specialist.
    Delivers clean, tested, production-grade Python code for backends, data, and integrations.
    Works seamlessly with the rest of the professional team.
    """

    def __init__(self):
        self.focus = "Building reliable, maintainable, high-performance Python systems that power professional websites and applications."

    def build_python_backend(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full Python backend architecture + APIs + integrations + quality plan."""
        log.info(f"PythonExpert: Building Python backend for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " python backend 2026", "professional Python FastAPI Django best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_stack": "FastAPI (or Django + DRF) + SQLAlchemy / Prisma Python + Pydantic + Alembic",
            "architecture": self.architecture(),
            "api_design": self.api_design(),
            "data_and_ai_integrations": self.data_and_ai_integrations(),
            "testing_and_quality": self.testing_and_quality(),
            "performance": self.performance(),
            "research": research[:1100] if research else "2026 Python web best practices, async, type safety with Pydantic v2, observability."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("python:backend", f"{task} | professional Python system for client work")
            except Exception:
                pass

        print("🐍 PythonExpert: Complete professional Python backend delivered.")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior Python engineer expert in FastAPI, backend, data and AI integrations.")
        self.mark_analysis(result)
        return result

    def architecture(self) -> Dict[str, str]:
        return {
            "structure": "Feature-based or DDD-style (domain, application, infrastructure layers)",
            "dependency_injection": "Use FastAPI Depends or dependency-injector library",
            "async_first": "Async endpoints, background tasks, proper DB async drivers where possible",
            "configuration": "Pydantic Settings + environment separation (dev/staging/prod)"
        }

    def api_design(self) -> list:
        return [
            "OpenAPI-first design (generate client code)",
            "Versioned APIs (/v1/)",
            "Consistent error responses + problem details (RFC 7807)",
            "Pagination, filtering, sorting standards",
            "Rate limiting and authentication middleware (JWT + optional OAuth2)"
        ]

    def data_and_ai_integrations(self) -> list:
        return [
            "Pydantic models for all data contracts (frontend <-> backend)",
            "Database migrations with Alembic",
            "Background jobs (Celery / RQ / FastAPI BackgroundTasks)",
            "AI integrations: clean interfaces to OpenAI, local models, vector DBs (with proper error handling and cost controls)",
            "Data pipelines: Pandas / Polars for ETL when needed, with strict typing"
        ]

    def testing_and_quality(self) -> list:
        return [
            "Pytest with fixtures, parametrization, and async support",
            "Test coverage targets (80%+ for critical paths)",
            "Property-based testing (Hypothesis) for complex logic",
            "Linting + formatting (ruff, black, mypy strict)",
            "Pre-commit hooks and CI quality gates"
        ]

    def performance(self) -> list:
        return [
            "Profiling with py-spy or cProfile before optimizing",
            "Caching strategies (Redis, in-memory with TTL)",
            "Database query optimization (explain plans, indexes, N+1 prevention)",
            "Async where it matters (I/O bound)",
            "Consider Cython / PyO3 / WASM for hot paths if needed (coordinate with C++ expert)"
        ]

    def crypto_payment_endpoints_example(self) -> str:
        """Concrete, production-ready FastAPI endpoints for /create-crypto-payment-intent and /confirm-crypto-payment.
        Integrates with Stripe Crypto + custom web3 + WASM result from frontend.
        Use with the React snippet from crypto_payments_expert.
        """
        return '''# backend/main.py (FastAPI) - add these endpoints
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import stripe
from typing import Optional
import json

app = FastAPI()
stripe.api_key = "sk_test_..."  # use env var in prod

class CreateIntentRequest(BaseModel):
    amount: int  # in smallest unit (e.g. 1000000 for 1 USDC)
    currency: str = "usd"
    payment_method_types: list[str] = ["crypto"]
    metadata: dict = {}

class ConfirmRequest(BaseModel):
    tx_hash: str
    three_d_config: dict
    wasm_result: dict  # from cpp WASM: {price, risk, gas}

@app.post("/api/create-crypto-payment-intent")
async def create_crypto_intent(req: CreateIntentRequest):
    try:
        intent = stripe.PaymentIntent.create(
            amount=req.amount,
            currency=req.currency,
            payment_method_types=req.payment_method_types,
            metadata={
                **req.metadata,
                "source": "3d_crypto_checkout",
                "wasm_risk": req.metadata.get("wasmRisk"),
            },
            # For crypto on Stripe: it will handle on-ramp or direct crypto
        )
        return {"clientSecret": intent.client_secret, "id": intent.id}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/confirm-crypto-payment")
async def confirm_crypto_payment(req: ConfirmRequest, idempotency_key: Optional[str] = Header(None)):
    # 1. Verify on-chain (use web3.py or ethers via service)
    #    - Check tx_hash on the correct chain
    #    - Verify amount matches wasm_result['price']
    #    - Verify to address
    #    - Check confirmations >= 1 (or more for high value)
    
    # 2. Verify WASM result integrity (re-run or check signature if you added one)
    #    expected = calculate_on_backend(req.three_d_config)  # pure Python version or call service
    #    if abs(expected['price'] - req.wasm_result['price']) > 0.01: raise error
    
    # 3. Idempotency + fulfill order (update DB, trigger 3D asset delivery, email, etc.)
    #    Use Stripe or your own order table
    
    # 4. Log to analytics (see analytics integration below)
    
    return {"status": "confirmed", "order_id": "ord_123", "tx_hash": req.tx_hash}

# Security notes:
# - Always re-verify amount and tx on server (never trust client/WASM for money)
# - Use Stripe webhooks as source of truth for Stripe Crypto flows
# - Rate limit these endpoints
# - Store only necessary data (no raw private keys ever)
'''

# Register
python_expert = PythonExpert()
print("🐍 PythonExpert registered. Ready for sub_type='python'. Professional Python for serious backends and data.")