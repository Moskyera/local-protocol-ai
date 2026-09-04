"""Verify the controlled self-evolution additions actually work.

THIS SCRIPT USED TO LIE. It printed the result of each probe and then, with no
condition attached, printed

    === ALL VERIFICATIONS PASSED - controlled, error-free evolution complete ===

and exited 0. So "telegram still forbidden: False" — the protection on the
briefing files being gone — was displayed, and the very next line declared
everything error-free. A verifier whose verdict does not depend on its checks is
worse than no verifier: it manufactures confidence.

Every probe is now recorded, the verdict is derived from them, and the exit code
is non-zero when anything fails, so a scheduled run can be trusted.
"""

import sys

CHECKS = []


def check(name, value, expect=True, detail=""):
    """Record a probe. `value` is the measured thing; `expect` is what it must be."""
    ok = (value is expect) if isinstance(expect, bool) else (value == expect)
    CHECKS.append((name, ok, value, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name}: {value}{(' — ' + detail) if detail else ''}")
    return ok


print("=== VERIFICATION OF SYSTEM EVOLUTION (controlled additions) ===")
print("Importing...")

try:
    from openhands_skills.research_agent import research_agent
    check("research_agent imports", True)
    check("store_evolution_pattern exists",
          hasattr(research_agent, "store_evolution_pattern"))
    check("get_evolution_patterns exists",
          hasattr(research_agent, "get_evolution_patterns"))
except Exception as e:
    check("research_agent imports", False, detail=f"{type(e).__name__}: {e}")
    research_agent = None

try:
    # The module exposes module-level functions, not a singleton — every real
    # caller in the repo imports them by name.
    from openhands_skills.langgraph_orchestrator import (_meta_supervise,
                                                         supervise_task)
    check("orchestrator supervise_task imports", callable(supervise_task))
    check("orchestrator _meta_supervise imports", callable(_meta_supervise))
except Exception as e:
    check("orchestrator imports", False, detail=f"{type(e).__name__}: {e}")

try:
    from openhands_mcp import server as mcp
    check("mcp server imports", True)
    check("mcp_github_context exists", hasattr(mcp, "mcp_github_context"))
except Exception as e:
    check("mcp server imports", False, detail=f"{type(e).__name__}: {e}")

try:
    from openhands_skills import evaluation_harness  # noqa: F401
    check("evaluation_harness imports", True)
except Exception as e:
    check("evaluation_harness imports", False, detail=f"{type(e).__name__}: {e}")

if research_agent:
    print("\nFunctional test (research with high-level focus)...")
    try:
        res = research_agent.research_new_technologies_and_skills(
            max_results=2, focus="self improving langgraph supervisor mcp",
            lab_mode=True)
        cands = res.get("new_capability_candidates", [])
        check("research returned candidates", len(cands) > 0,
              detail=f"{len(cands)} candidates")
        check("all candidates carry pros_cons",
              all("pros_cons" in c for c in cands) if cands else False)
        # The seed is real output, but it is not research. Say which it was.
        seeded = sum(1 for c in cands if isinstance(c, dict)
                     and c.get("is_offline_seed"))
        print(f"  [note] live_sources={res.get('live_sources')} "
              f"seeded={seeded} status={res.get('status')}")
    except Exception as e:
        check("research functional test", False, detail=f"{type(e).__name__}: {e}")

    print("\nEvolution patterns storage test...")
    try:
        ok = research_agent.store_evolution_pattern(
            "test high-level pattern from langgraph-supervisor + github-mcp",
            source_url="https://github.com/langchain-ai/langgraph-supervisor-py",
            success_score=0.85)
        check("store_evolution_pattern succeeded", bool(ok))
        pats = research_agent.get_evolution_patterns(2)
        check("patterns can be read back", len(pats) > 0,
              detail=f"{len(pats)} patterns")
    except Exception as e:
        check("evolution pattern storage", False, detail=f"{type(e).__name__}: {e}")

print("\nGuards check (no forbidden touched)...")
try:
    from openhands_skills.guards import FORBIDDEN_PATHS, is_forbidden_path
    check("forbidden list is non-empty", len(FORBIDDEN_PATHS) > 0,
          detail=f"{len(FORBIDDEN_PATHS)} entries")
    check("telegram_engine.py is still forbidden",
          is_forbidden_path("telegram_engine.py"))
    check("master_market_brain.py is still forbidden",
          is_forbidden_path("master_market_brain.py"))
except Exception as e:
    check("guards import", False, detail=f"{type(e).__name__}: {e}")

failed = [c for c in CHECKS if not c[1]]
print("\n" + "=" * 70)
if failed:
    print(f"=== {len(failed)} OF {len(CHECKS)} VERIFICATIONS FAILED ===")
    for name, _, value, detail in failed:
        print(f"    FAIL {name}: {value}{(' — ' + detail) if detail else ''}")
    sys.exit(1)

print(f"=== ALL {len(CHECKS)} VERIFICATIONS PASSED ===")
sys.exit(0)
