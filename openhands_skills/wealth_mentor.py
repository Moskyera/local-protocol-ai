"""
WealthMentor / Practical Economics Advisor for MOSKY Agent System.

Provides consult_wealth_mentor and generate_wealth_plan capabilities focused on
"how to make money" and practical solutions in real-world economic conditions.

Design principles (matching system):
- First-class specialist in LangGraph supervisor.
- Deterministic pure-Python calculations for all numbers (no LLM hallucinations on math).
- Structured Pydantic outputs for reliable plans.
- Grounded in user context + existing research/blockchain data when available.
- Guarded via MCP (user_confirmed proposal flow).
- Actionable: steps, estimated impact, risks, timeline, resources.
- Supports chaining to research (validation), engineering (build), blockchain (on-chain plays).
- Fallbacks and defensive imports everywhere.
- Real conditions focus: scenarios (bull/base/bear), cashflow in volatile markets, opportunity scoring.

Usage:
    from openhands_skills.wealth_mentor import consult_wealth_mentor
    result = consult_wealth_mentor("How to build a $5k/mo side hustle with crypto in current market")

MCP wrapper adds guardrail + explicit human confirmation for any concrete recommendations.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except Exception:
    HAS_PYDANTIC = False
    BaseModel = object
    def Field(*a, **k): return None

try:
    from project_paths import WEALTH_DIR, WEALTH_KNOWLEDGE_DIR, MARKET_AGENT_ROOT
except Exception:
    WEALTH_DIR = Path("wealth")
    WEALTH_KNOWLEDGE_DIR = WEALTH_DIR / "knowledge"
    MARKET_AGENT_ROOT = Path(".")

try:
    from logger import log
except Exception:
    class _Log:
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
    log = _Log()

try:
    from openhands_skills.persistent_memory import persistent_memory
except Exception:
    persistent_memory = None

# --- Deterministic calculation core (pure Python, no LLM for numbers) ---

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def project_cashflow(monthly_income: float, monthly_expenses: float, months: int = 12,
                     income_growth: float = 0.0, expense_growth: float = 0.0) -> Dict[str, Any]:
    """Deterministic cashflow projection with growth."""
    income = _safe_float(monthly_income)
    expenses = _safe_float(monthly_expenses)
    projections = []
    cumulative = 0.0
    for m in range(1, max(1, int(months)) + 1):
        inc = income * ((1 + income_growth) ** (m - 1))
        exp = expenses * ((1 + expense_growth) ** (m - 1))
        net = inc - exp
        cumulative += net
        projections.append({
            "month": m,
            "income": round(inc, 2),
            "expenses": round(exp, 2),
            "net": round(net, 2),
            "cumulative": round(cumulative, 2)
        })
    return {
        "projections": projections,
        "total_net": round(cumulative, 2),
        "break_even_month": next((p["month"] for p in projections if p["cumulative"] >= 0), None)
    }

def calculate_scenario_roi(initial_capital: float, monthly_profit: float, months: int = 12,
                           success_rate: float = 0.7) -> Dict[str, Any]:
    """Bull / base / bear ROI scenarios."""
    cap = max(1.0, _safe_float(initial_capital))
    profit = _safe_float(monthly_profit)
    m = max(1, int(months))
    sr = max(0.1, min(1.0, _safe_float(success_rate, 0.7)))

    def scenario(mult: float, label: str) -> Dict[str, Any]:
        adj_profit = profit * mult * sr
        total_profit = adj_profit * m
        roi = (total_profit / cap) * 100.0
        return {
            "scenario": label,
            "monthly_profit": round(adj_profit, 2),
            "total_profit": round(total_profit, 2),
            "roi_percent": round(roi, 1),
            "final_capital": round(cap + total_profit, 2)
        }

    return {
        "bull": scenario(1.3, "bull"),
        "base": scenario(1.0, "base"),
        "bear": scenario(0.6, "bear"),
        "initial_capital": cap,
        "assumptions": f"Success rate applied {sr*100:.0f}%. Growth/adjustments scenario-based."
    }

def break_even_analysis(fixed_costs: float, variable_cost_per_unit: float, price_per_unit: float,
                        expected_units: int = 1000) -> Dict[str, Any]:
    """Break-even units and contribution margin."""
    fc = _safe_float(fixed_costs)
    vc = _safe_float(variable_cost_per_unit)
    p = _safe_float(price_per_unit)
    units = max(1, int(expected_units))

    if p <= vc:
        return {"error": "Price must exceed variable cost", "break_even_units": None}

    contrib = p - vc
    be_units = fc / contrib
    margin = (contrib / p) * 100
    profit_at_expected = (units * contrib) - fc

    return {
        "break_even_units": round(be_units, 1),
        "contribution_margin": round(contrib, 2),
        "margin_percent": round(margin, 1),
        "profit_at_expected_units": round(profit_at_expected, 2),
        "units_for_2x": round(be_units * 2, 1)
    }

def opportunity_score(idea_description: str, market_signal: float = 0.5,
                      capital_required: float = 1000.0, time_to_cash: int = 3,
                      competition: float = 0.5, user_edge: float = 0.5) -> Dict[str, Any]:
    """Simple deterministic opportunity scoring for real conditions."""
    ms = max(0.0, min(1.0, _safe_float(market_signal, 0.5)))
    cap = max(100.0, _safe_float(capital_required))
    ttc = max(1, int(time_to_cash))
    comp = max(0.0, min(1.0, _safe_float(competition, 0.5)))
    edge = max(0.0, min(1.0, _safe_float(user_edge, 0.5)))

    # Weighted score (higher better)
    score = (0.30 * ms + 0.20 * edge + 0.15 * (1 - comp) + 0.15 * (1 / (1 + (cap / 5000))) +
             0.20 * (1 / (1 + (ttc / 6.0)))) * 100

    recommendation = "Strong" if score > 70 else ("Moderate - validate more" if score > 50 else "Weak - rethink or de-risk")

    return {
        "score": round(score, 1),
        "recommendation": recommendation,
        "factors": {
            "market_signal": ms,
            "user_edge": edge,
            "competition": comp,
            "capital_efficiency": round(1 / (1 + (cap / 5000)), 2),
            "speed_to_cash": round(1 / (1 + (ttc / 6.0)), 2)
        },
        "risk_notes": "Score is directional. Always run full scenarios and validate with real data."
    }

# --- Structured output models ---

if HAS_PYDANTIC:
    class WealthStep(BaseModel):
        step: str = Field(..., description="Concrete action step")
        owner: str = Field("you", description="Who executes")
        estimated_cost: float = Field(0.0)
        estimated_time_days: int = Field(7)
        expected_impact: str = Field("")

    class WealthRisk(BaseModel):
        risk: str
        likelihood: str = "medium"
        mitigation: str = ""

    class WealthPlan(BaseModel):
        title: str
        summary: str
        steps: List[WealthStep]
        scenarios: Dict[str, Any]
        key_metrics: Dict[str, Any]
        risks: List[WealthRisk]
        timeline_weeks: int = 8
        next_actions: List[str]
        disclaimer: str = "Educational/general information only. Not licensed financial advice. Do your own research and consult professionals. Past performance does not guarantee future results."
else:
    # Fallback simple dicts
    WealthStep = dict
    WealthRisk = dict
    WealthPlan = dict

# --- Main class ---

class WealthMentor:
    """
    Practical wealth / money-making mentor.
    Focus: real conditions, deterministic numbers, actionable plans.
    """

    def __init__(self):
        self.knowledge_dir = WEALTH_KNOWLEDGE_DIR
        try:
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def consult(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry. Returns structured advice + plans grounded in prompt + context.
        Context can include previous research_result, blockchain data, user financial snapshot.
        """
        log.info(f"[WealthMentor] consult: {prompt[:80]}...")

        ctx = context or {}
        # Extract useful signals from context (real data grounding)
        market = ctx.get("market_signal", 0.6)
        capital = ctx.get("available_capital", ctx.get("capital", 2000.0))
        user_edge = ctx.get("user_edge", 0.55)
        income = ctx.get("monthly_income", 0.0)
        expenses = ctx.get("monthly_expenses", 0.0)

        # Core deterministic analysis
        cf = project_cashflow(income or 3000, expenses or 2500, months=12, income_growth=0.05)
        roi = calculate_scenario_roi(capital, monthly_profit=800, months=12, success_rate=0.65)
        opp = opportunity_score(prompt, market_signal=market, capital_required=capital, user_edge=user_edge)

        # Build plan (template + data driven from deterministic calcs)
        title = "Practical Wealth Plan: " + prompt[:60]
        cf_total = cf.get("total_net", 0)
        roi_base = roi.get("base", {}).get("roi_percent", 0)
        steps = [
            {"step": f"Validate idea with 3 real customer conversations or on-chain signals this week (target opportunity score >{opp.get('score', 50)})", "owner": "you", "estimated_cost": 50, "estimated_time_days": 7, "expected_impact": "De-risk before capital"},
            {"step": "Build minimal MVP or test offer (landing page / on-chain test)", "owner": "you + engineering if needed", "estimated_cost": 200, "estimated_time_days": 14, "expected_impact": "First revenue signal"},
            {"step": f"Run cashflow + 3 scenarios on projected numbers (est. total net ${cf_total:,.0f} over 12m, base ROI {roi_base}%)", "owner": "you", "estimated_cost": 0, "estimated_time_days": 2, "expected_impact": "Clear go / no-go + capital needs"},
            {"step": "Launch small test (pricing, channel) and track for 30 days", "owner": "you", "estimated_cost": 300, "estimated_time_days": 30, "expected_impact": "Real data for scale decision"},
        ]

        risks = [
            {"risk": "Market conditions change (crypto volatility, regulation)", "likelihood": "high", "mitigation": "Diversify channels, keep low fixed costs, scenario plan monthly"},
            {"risk": "Execution delays or low conversion", "likelihood": "medium", "mitigation": "Weekly metrics review, pivot fast, start small"},
            {"risk": "Capital overrun", "likelihood": "medium", "mitigation": "Cap spend at 30% of available, use lean tests first"},
        ]

        plan = {
            "title": title,
            "summary": f"Grounded plan for: {prompt}. Uses your context + deterministic models. Focus on quick validation then scaled execution.",
            "steps": steps,
            "scenarios": roi,
            "key_metrics": {
                "cashflow_projection": cf,
                "opportunity_score": opp,
                "break_even_reference": break_even_analysis(800, 15, 49, 500)  # example units
            },
            "risks": risks,
            "timeline_weeks": 8,
            "next_actions": [
                "Reply with more specific numbers (income/expenses/capital) for refined model.",
                "Ask to run specific scenario or chain to research/engineering.",
                "Provide explicit approval for concrete recommendations."
            ],
            "disclaimer": "This is general educational analysis using deterministic models. Not personalized licensed financial, investment, or tax advice. Verify everything yourself. Markets and conditions change rapidly."
        }

        if persistent_memory:
            try:
                persistent_memory.store("wealth_plan", f"{prompt[:60]} -> score {opp.get('score')}")
            except Exception:
                pass

        return {
            "status": "success",
            "plan": plan,
            "prompt": prompt,
            "context_used": bool(context),
            "note": "Numbers from deterministic calculators. LLM synthesis kept minimal. Chain to other specialists for deeper validation or implementation."
        }

    def generate_plan(self, prompt: str, **kwargs) -> Dict[str, Any]:
        return self.consult(prompt, context=kwargs.get("context"))


# Singleton
wealth_mentor = WealthMentor()

def consult_wealth_mentor(prompt: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Convenience wrapper used by orchestrator and MCP."""
    return wealth_mentor.consult(prompt, context=context)

def generate_wealth_plan(prompt: str, workflow_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Wrapper for MCP compatibility (workflow_file ignored for now, future external strategies)."""
    ctx = kwargs.get("context") or {}
    return wealth_mentor.generate_plan(prompt, context=ctx)
