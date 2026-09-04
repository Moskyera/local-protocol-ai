"""
Multi-Agent Orchestrator v2.1 - Το Κεντρικό Εγκεφαλικό Κέντρο
Συντονίζει όλους τους υπεράνθρωπους agents με memory και intelligence
"""

from .advanced_supervisor import advanced_supervisor
from .market_analyst_agent_v2 import market_analyst
from .coder_agent_v2 import coder
from .tester_agent_v2 import tester
from .reviewer_agent_v2 import reviewer
# The debugger import went with the discarded call above: it was invoked
# with a constant string and its result was never read.
from .security_agent_v2 import security
from .strategic_oracle import strategic_oracle
from .hyper_evolution_agent import hyper_evolver
from .self_correcting_coder import self_correcting_coder
from openhands_skills.solidity_expert import solidity_expert
from logger import log

_CODING_KWS = (
    "code", "function", "implement", "script", "refactor", "bug", "fix",
    "class", "api", "algorithm", "python", "javascript", "typescript",
    "program", "module", "backend", "frontend", "endpoint", "parser",
    "regex", "cli", "test", "optimize", "rewrite",
)

class MultiAgentOrchestratorV2:
    #: Asked once per process. Probing on every run costs the full timeout
    #: when the server is down, which is exactly when you least want to wait.
    _slots_cache = None

    @classmethod
    def _slots(cls, timeout: float = 2.0) -> int:
        """How many requests the server will genuinely run at once."""
        if cls._slots_cache is not None:
            return cls._slots_cache
        cls._slots_cache = cls._probe_slots(timeout)
        return cls._slots_cache

    @staticmethod
    def _probe_slots(timeout: float = 2.0) -> int:
        try:
            import json as _json
            import urllib.request
            from config import config
            base = getattr(config, "OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
            url = base.rstrip("/").removesuffix("/v1") + "/props"
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return max(1, int(_json.loads(r.read()).get("total_slots", 1)))
        except Exception:
            return 1

    def _concurrently(self, *named_calls):
        """Run independent model calls together, in the caller's order.

        Falls back to plain sequential execution when the server offers one
        slot, or when anything about the probe fails — the same discipline as
        the document pipeline: match the server, never guess above it.
        """
        n = min(len(named_calls), self._slots())
        if n <= 1:
            return tuple(fn() for _, fn in named_calls)

        from concurrent.futures import ThreadPoolExecutor
        log.info(f"Orchestrator: running {len(named_calls)} independent calls "
                 f"across {n} slots")
        with ThreadPoolExecutor(max_workers=n) as ex:
            futures = [ex.submit(fn) for _, fn in named_calls]
            out = []
            for (name, _), f in zip(named_calls, futures):
                try:
                    out.append(f.result())
                except Exception as e:
                    log.error(f"Orchestrator: {name} failed: {e}")
                    out.append(f"({name} failed: {type(e).__name__}: {e})")
        return tuple(out)

    def run(self, user_task: str):
        log.info(f"Multi-Agent Orchestrator v2.1 started for task: {user_task}")

        print("\n" + "═" * 80)
        print("🚀 MULTI-AGENT ORCHESTRATOR v2.1 - HYPER INTELLIGENT MODE")
        print("═" * 80)

        # Decide task nature up-front, so nothing irrelevant is generated.
        low = user_task.lower()
        is_pulse_or_solidity = any(kw in low for kw in [
            "solidity", "evm", "erc", "smart contract", "defi", "hvm",
            "pulsechain", "pulse", "pls"])
        is_coding = (not is_pulse_or_solidity) and any(kw in low for kw in _CODING_KWS)
        is_market = any(kw in low for kw in [
            "market", "price", "btc", "eth", "crypto", "portfolio", "trade",
            "trading", "regime", "macro", "αγορά", "τιμή"])

        # Step 1: plan. This one is always needed.
        plan = advanced_supervisor.plan_and_orchestrate(user_task)

        # The strategic vision and the market analysis used to run on EVERY
        # task, with no arguments — so a request to refactor a parser produced
        # a BTC/USDT strategic outlook and a market snapshot, at full model
        # cost, and then handed both to the synthesis as context. They run when
        # the task is about the market.
        if is_market:
            vision = strategic_oracle.generate_vision()
            market_data = market_analyst.analyze_market()
        else:
            vision = "(not generated: this task is not about the market)"
            market_data = "(not fetched: this task is not about the market)"

        # Coding tasks go through the self-correcting loop
        # (write → ruff/bandit/mypy/pyflakes + security scan → auto-fix → re-check).
        loop_report = ""
        if is_coding:
            log.info("Orchestrator: routing coding task through self-correcting loop")
            build = self_correcting_coder.build(user_task, max_iterations=3)
            code = build.code
            loop_report = build.to_report()
        else:
            code = coder.write_or_refactor(user_task)

        # These three read the SAME finished `code` and do not read each other,
        # so they were three sequential model calls for no reason. The server
        # reports how many requests it will genuinely run at once; at 1 slot
        # this stays exactly as serial as it was.
        tests, review, security_report = self._concurrently(
            ("tests", lambda: tester.run_tests(user_task)),
            ("review", lambda: reviewer.review(code)),
            ("security", lambda: security.audit(code)),
        )

        # `debug = debugger.debug("Any issues found")` used to sit here. It
        # passed a CONSTANT STRING to the debugger — not the task, not an error,
        # not the code — so the debugger diagnosed the literal phrase "Any
        # issues found". Its result was then never used: `debug` appears in no
        # later expression and is absent from the coordinate() dict below.
        # Measured at 18.6 seconds of model time per run, discarded.

        # Automatic Solidity/EVM/PulseChain support (MAIN for OpenHands smart contract work)
        if is_pulse_or_solidity:
            chain = "pulsechain" if any(p in user_task.lower() for p in ["pulse", "pls", "pulsechain"]) else "ethereum"
            print(f"🔷 Auto-activating FULL Solidity/PulseChain pipeline (target: {chain})")
            solidity_code = solidity_expert.write_solidity_contract(user_task, target_chain=chain)
            solidity_audit = solidity_expert.audit_solidity(solidity_code, target_chain=chain)
            full_project = solidity_expert.generate_full_project(user_task, target_chain=chain)
            code = solidity_code
            # APPEND, do not replace. This used to be `review = solidity_audit`,
            # which threw away the reviewer's real analysis and put a regex
            # pre-screen in its place — one that scored a drainable contract
            # 10.0/10. The pre-screen is a useful extra signal and a terrible
            # substitute.
            review = ((review + chr(10)*2 + '---' + chr(10) + solidity_audit)
                      if review else solidity_audit)
            print("   + Full project scaffold (contract + tests + deploy) generated")

        # Step 3: Hyper Evolution + Smart Reflection
        evolution = hyper_evolver.evolve(user_task, "System executed full multi-agent cycle")
        
        # Extra smart reflection step for complex tasks
        # NO hardcoded reflection. It used to inject the literal string
        # "security checklist passed" into the supervisor's final synthesis for
        # every contract task, and the supervisor was told to trust it — a
        # security verdict nobody ever computed. The real security report is
        # already passed in below under "security"; line 89 supplies the default.

        # Step 4: Final Integration (always produce user-visible output, even in new session)
        final_synthesis = advanced_supervisor.coordinate({
            "vision": vision,
            "market": market_data,
            "code": code,
            "tests": tests,
            "review": review,
            "security": security_report,
            "self_correction": loop_report or "N/A (non-coding task)",
            "reflection": locals().get("reflection", "No extra reflection needed")
        })

        print("\n🎯 FULL MULTI-AGENT CYCLE COMPLETED")
        print("All agents collaborated with memory, reflection and evolution")

        # Always return a clear user-facing string (so OpenHands chat shows something even on first message of new convo)
        user_visible = f"""{final_synthesis}

**Immediate visible response for this session:**
Supervisor + specialists executed for: "{user_task}"
(If this is the first message in a new conversation, the above plan + synthesis is the first output. Further details follow in next turns if needed.)

Ready for your next input."""

        return user_visible

# Register
orchestrator = MultiAgentOrchestratorV2()