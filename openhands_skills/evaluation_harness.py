"""
Evaluation Harness for the 3-agent self-improving system.

Part of Phase 5: Professional Polish & making the closed loop measurable.

Provides:
- Quantitative metrics for Blockchain Intelligence (risk scoring quality, latency on sample cases).
- System-level improvement score.
- Pre/post comparison after guarded applies.
- Storage of results to persistent_memory for trend tracking ("how it gets better over time").

This allows us to answer: "Did the last research → engineering → apply actually make the Blockchain agent better?"

All changes strictly limited to allowed paths. No forbidden files touched.
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from openhands_skills.chain_analysis_expert import chain_analysis_expert
except Exception:
    chain_analysis_expert = None

try:
    from openhands_skills.persistent_memory import persistent_memory
except Exception:
    class _DummyMem:
        def store(self, *a, **k): pass
        def retrieve(self, *a, **k): return []
    persistent_memory = _DummyMem()

# ---------------------------------------------------------------------------
# THE FIXTURE THIS HARNESS MEASURES WITH.
#
# It used to hold three cases with PLACEHOLDER addresses — 0x..0001, 0x..0002,
# 0x..0003 — beside a comment saying "logic uses mock data in eval". It did
# not: _run_blockchain_eval called analyze_address over the network on those
# addresses. They are empty wallets, so the expert correctly returned LOW and
# "general wallet risks" for all three. Case 2 expected exactly that and passed
# BY COINCIDENCE; cases 1 and 3 expected HIGH and MEDIUM and could never pass.
#
# So the accuracy was pinned at 33.3%, and the pre/post delta that the
# self-improvement loop reads to decide whether it got better was structurally
# incapable of moving. Improving the risk logic could not raise it, because the
# fixture was asking about wallets that do not exist.
#
# These cases feed activity dictionaries straight to _calculate_risk_score:
# deterministic, offline, no network and no model. Every one is reachable, so
# the number can actually move when the logic changes — which is the only
# reason to have it.
#
# The expectations encode the rules the scorer documents for itself:
#   score >= 70 -> HIGH, >= 45 -> MEDIUM, else LOW
#   the "big PLS receive + low activity + meme bag" pattern fires only when
#   USD > 10000 AND nonce < 20 AND at least two meme-like holdings
# ---------------------------------------------------------------------------

_EVAL_ADDR = "0xaaaabbbbccccddddeeeeffff0000111122223333"


def _activity(*, usd_received: float, pls_price: float, nonce: int,
              memes: int = 0) -> Dict[str, Any]:
    """An activity dict with a KNOWN native USD value.

    The scorer derives the PLS price from a PLS balance row, so the row and the
    transfer are built together to make the dollar figure exact rather than
    approximate.
    """
    return {
        "address": _EVAL_ADDR,
        "native_transfers": [{"to": _EVAL_ADDR,
                              "value": int(usd_received / pls_price)}],
        # The PLS row is deliberately worth more than $50: the scorer counts any
        # holding under $50 as meme-like, so a cheap native balance would count
        # itself as a meme and shift the fixture by one.
        "current_balances": (
            [{"symbol": "PLS", "balance": "10000000",
              "usd": 10_000_000 * pls_price}]
            # Symbols the scorer actually recognises, rather than relying on the
            # under-$50 heuristic.
            + [{"symbol": sym, "balance": "1000", "usd": 120}
               for sym in ("PCOCK", "PTIGER", "OMEGA", "ZELDA")[:memes]]
        ),
        "onchain_nonce": nonce,
        "approvals": [],
        "categories": {"meme": memes},
        "large_ecosystem_movements": [],
    }


_PRICE = 0.00002
_SPECIFIC = "big PLS receive + low activity + meme bag"
_GENERAL = "general wallet risks"

SAMPLE_TEST_CASES: List[Dict[str, Any]] = [
    {
        "name": "very_large_inflow_low_nonce_memes",
        "activity": _activity(usd_received=100_000, pls_price=_PRICE, nonce=6, memes=3),
        "chain": "pulsechain",
        "expected_risk_level": "HIGH",
        "expected_pattern": _SPECIFIC,
        "description": "Over 50k USD received, nonce 6, three meme holdings — "
                       "every condition of the documented pattern is met",
    },
    {
        "name": "large_inflow_low_nonce_memes",
        "activity": _activity(usd_received=25_000, pls_price=_PRICE, nonce=8, memes=2),
        "chain": "pulsechain",
        "expected_risk_level": "MEDIUM",
        "expected_pattern": _SPECIFIC,
        "description": "Over 10k with a low nonce and two memes: the pattern "
                       "fires, and the score still lands below HIGH",
    },
    {
        "name": "notable_inflow_active_wallet",
        "activity": _activity(usd_received=6_000, pls_price=_PRICE, nonce=60),
        "chain": "pulsechain",
        "expected_risk_level": "LOW",
        "expected_pattern": _GENERAL,
        "description": "A notable inflow into an ACTIVE wallet with no memes — "
                       "the pattern must not fire on the dollar figure alone",
    },
    {
        "name": "small_inflow_active_trader",
        "activity": _activity(usd_received=200, pls_price=_PRICE, nonce=450),
        "chain": "pulsechain",
        "expected_risk_level": "LOW",
        "expected_pattern": _GENERAL,
        "description": "The explicit user rule: small inflows ($50-$500) must "
                       "not trigger heavy analysis or high risk flags",
    },
    {
        "name": "many_coins_tiny_value",
        "activity": _activity(usd_received=35, pls_price=0.000007, nonce=3, memes=2),
        "chain": "pulsechain",
        "expected_risk_level": "LOW",
        "expected_pattern": _GENERAL,
        "description": "Five million PLS at $0.000007 is $35. This is the whole "
                       "reason the rule measures USD and not coin count: a low "
                       "nonce and a meme bag must not make $35 look like a "
                       "distribution event",
    },
]

class EvaluationHarness:
    def __init__(self):
        self.last_eval_time = 0
        self.min_interval = 60  # seconds between full evals (rate limit)

    def _run_blockchain_eval(self) -> Dict[str, Any]:
        """Run the core Blockchain Intelligence evaluation on sample cases."""
        if not chain_analysis_expert:
            return {"error": "chain_analysis_expert not available", "cases": []}

        results = []
        total_latency = 0.0
        correct = 0

        for case in SAMPLE_TEST_CASES:
            start = time.time()
            try:
                # _calculate_risk_score, not analyze_address. The old call
                # went to the NETWORK with a placeholder address, so it
                # measured whether an empty wallet looks empty — which it
                # always does, for every case, forever.
                rs = chain_analysis_expert._calculate_risk_score(
                    dict(case["activity"]), case["chain"]) or {}
                latency = time.time() - start
                total_latency += latency

                level = rs.get("level", "UNKNOWN")
                pattern = rs.get("pattern_match", "")

                is_correct = (level == case["expected_risk_level"]) and (
                    pattern == case["expected_pattern"])

                if is_correct:
                    correct += 1

                results.append({
                    "name": case["name"],
                    "expected_level": case["expected_risk_level"],
                    "actual_level": level,
                    "expected_pattern_match": case["expected_pattern"],
                    "actual_pattern": pattern,
                    "correct": is_correct,
                    "latency_sec": round(latency, 3),
                    "native_inflow_usd": rs.get("native_inflow_usd", 0),
                })
            except Exception as e:
                latency = time.time() - start
                results.append({
                    "name": case["name"],
                    "error": str(e)[:150],
                    "latency_sec": round(latency, 3),
                    "correct": False,
                })

        # `total_latency` is only incremented in the success path, so a case that
        # raised contributed 0 seconds. Averaging over ALL cases therefore turned
        # failure into apparent speed, and the scorer paid for speed.
        errored = [r for r in results if r.get("error")]
        succeeded = [r for r in results if not r.get("error")]
        accuracy = (correct / len(SAMPLE_TEST_CASES)) * 100 if SAMPLE_TEST_CASES else 0
        avg_latency = (total_latency / len(succeeded)) if succeeded else 0.0

        return {
            "accuracy_percent": round(accuracy, 1),
            "avg_latency_sec": round(avg_latency, 3),
            "cases": results,
            "num_cases": len(SAMPLE_TEST_CASES),
            "num_errored": len(errored),
            "num_succeeded": len(succeeded),
            "errors": [f"{r['name']}: {r['error']}" for r in errored],
        }

    def run_full_evaluation(self, focus: str = "all") -> Dict[str, Any]:
        """Run the full system evaluation harness.
        Returns structured metrics + stores to persistent_memory (type="system_evaluation").
        """
        now = time.time()
        if now - self.last_eval_time < self.min_interval:
            return {"status": "rate_limited", "next_in": self.min_interval - (now - self.last_eval_time)}

        self.last_eval_time = now

        blockchain = self._run_blockchain_eval()

        # System level metrics (can be expanded with engineering/research stats from memory)
        # EVOLVED: now explicitly references high-level agent evals (SWE-bench style for coding/engineering,
        # process reward, agent-as-judge, safety from research on lm-eval-harness + agent benchmarks).
        # Bonus for proposals that came from evolution_patterns (meta RSI memory).
        # For now, simple aggregate + improvement potential.
        # THE SCORE USED TO GO UP WHEN THE SUBSYSTEM DIED.
        #
        # A case that raised added nothing to total_latency, so a completely dead
        # expert reported avg_latency 0.0s, collected the full 40 speed points
        # against 0 accuracy, and scored 40.0 — the same as a working system at
        # 33% accuracy and 2s, and better than several real states. The one
        # number the self-improvement loop uses to decide whether it got better
        # rewarded total failure.
        #
        # A measurement that could not be taken is not a score. Say so instead.
        if blockchain.get("error") or blockchain.get("num_errored"):
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "eval_failed",
                "blockchain_intelligence": blockchain,
                "errors": (blockchain.get("errors")
                           or [blockchain.get("error", "unknown evaluation error")]),
                "system_improvement_score": None,
                "notes": ("No score was produced: at least one evaluation case failed, "
                          "so there is nothing to compare against. Fix the failure "
                          "before reading this as a health signal."),
            }

        system_score = 0
        if "accuracy_percent" in blockchain:
            system_score += blockchain["accuracy_percent"] * 0.6   # 60% weight on blockchain quality
        # Speed is only worth points when something actually ran and was correct.
        if blockchain.get("num_succeeded") and blockchain.get("accuracy_percent", 0) > 0:
            latency_score = max(0, 40 - (blockchain["avg_latency_sec"] * 10))
            system_score += min(40, latency_score)  # up to 40 points for speed

        # Add bonus from recent successful applies (from memory if available)
        try:
            recent = persistent_memory.retrieve(limit=5, metadata_filter={"type": "guarded_apply_hardened"}) or []
            if recent:
                system_score += min(10, len(recent) * 2)  # small bonus for recent successful guarded improvements
        except Exception:
            pass

        system_score = min(100, max(0, round(system_score, 1)))

        result = {
            "timestamp": datetime.now().isoformat(),
            "blockchain_intelligence": blockchain,
            "system_improvement_score": system_score,
            "notes": "Higher score = better risk quality + lower latency + evidence of successful self-improvements. Run after guarded applies to measure delta.",
        }

        try:
            persistent_memory.store(
                text=str(result),
                metadata={
                    "type": "system_evaluation",
                    "timestamp": result["timestamp"],
                    "system_score": system_score,
                    "blockchain_accuracy": blockchain.get("accuracy_percent", 0),
                }
            )
        except Exception:
            pass

        return result

    def compare_pre_post(self, pre_eval: Dict[str, Any], post_eval: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two evaluations (before/after a self-improvement apply) and compute delta."""
        pre_score = pre_eval.get("system_improvement_score", 0)
        post_score = post_eval.get("system_improvement_score", 0)
        delta = round(post_score - pre_score, 1)

        pre_acc = pre_eval.get("blockchain_intelligence", {}).get("accuracy_percent", 0)
        post_acc = post_eval.get("blockchain_intelligence", {}).get("accuracy_percent", 0)
        acc_delta = round(post_acc - pre_acc, 1)

        return {
            "pre_score": pre_score,
            "post_score": post_score,
            "delta": delta,
            "improved": delta > 0,
            "blockchain_accuracy_delta": acc_delta,
            "summary": f"System score {'improved' if delta > 0 else 'did not improve or regressed'} by {delta} points after the guarded change.",
        }

# Singleton
evaluation_harness = EvaluationHarness()

def run_system_evaluation(focus: str = "all") -> Dict[str, Any]:
    return evaluation_harness.run_full_evaluation(focus=focus)