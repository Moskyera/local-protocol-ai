# Agent System Upgrade Plan - Professional Self-Improving Multi-Agent Platform

**Goal**: Build a novel, professional, production-grade "PulseForge" or "ChainForge Agent OS" – a specialized, closed-loop multi-agent system for:
- **Blockchain Intelligence**: World-class on-chain analysis (wallets, risk/PnL with your exact USD tiers, token, whale, DeFi on PulseChain/EVM) that gets better over time.
- **Self-Improving Technical Engineering**: Agents that find bugs/improvements in the market-agent project (focusing on agent skills/MCP/LangGraph/automation), propose, test, and safely apply fixes.
- **Continuous Research & Learning**: Agent that researches web, GitHub, papers, MCP ecosystem, AI advances, and injects improvements into the other agents and itself.

**Core Principles (Non-Negotiable)**:
- **Build on existing foundation**: Leverage openhands_skills (chain_analysis_expert, self_improving, tool_hub, langgraph_orchestrator), openhands_mcp (MCP tools with analyze_wallet etc.), openhands_multiagent_v2 (supervisor, hyper_evolution, market_analyst_v2, coder/debug etc.), persistent_memory, etc. Do not discard.
- **Something that doesn't exist yet**: A tightly integrated domain-specialized (PulseChain on-chain + self-evolving engineering) recursive self-improving system using future trends (MAS orchestration, RSI/Karpathy-style loops, MCP as standard for tools, LangGraph for controllable graphs, continuous research feeding evolution). Not generic; optimized for your use case and "next job" professional quality.
- **Strict boundaries**: ALL changes ONLY in openhands_skills/, openhands_mcp/, openhands_multiagent_v2/, langgraph_orchestrator.py, automation/  # (was automation_examples/ before 2026-06 reorganization), runtime/ (for preloads), related docs/config. 
  - **FORBIDDEN (never touch, never propose edit to)**: Any file related to Telegram/briefings: telegram_engine.py, master_market_brain.py, send_full_ai_briefing*, the 6 daily messages (Master, Snapshot, Macro/Tech, AI Advisor, Geopolitical, Corporate/Earnings), geopolitical_engine.py, corporate_news_engine.py, send_briefing.bat, send_simplex_briefing.py, and any briefing generation logic. Self-improver must have hard-coded exclusion + path guards.

**Latest progress (2026-06, "παμε οπως θες" + "συνεχισε" phase)**:
- Proactive automatic discovery (research_new_technologies_and_skills) now surfaces **100% fidelity** candidates: exact GitHub url + metadata, verbatim `direct_evidence` (README/key file), `credibility_signals` as raw observable facts (no summaries), `x_evidence_examples` with real post URLs + verbatim quotes from 2026 discussions (LangChain officials on interrupts/HIL + real users on "propose edits → experiment → scalar score → commit only winners or revert" loops + production supervisor patterns).
- Supervisor routing robustly detects "integrate the first one", "apply the second", Greek "λεπτομεριες", etc. Resolves and carries the **full raw selected_proactive_idea** object through state.
- When user explicitly approves, _execute_engineering builds a high-fidelity proposal that quotes the source url + direct_evidence + x_evidence directly into apply_data + rationale (zero loss of provenance). Proposal targets the right file (orchestrator/guards) and is ready for the existing guarded_propose + human_approved + .approved + eval_harness + rollback flow.
- Added strict X tools (`x_semantic_search`, `x_thread_fetch`, `x_keyword_search`) to openhands_mcp/server.py with full "CRITICAL CALLING RULES", XML examples, and guidance so the Research agent can natively pull credibility data.
- Cleaned duplicate validation logic. The "details on N" + "integrate the Nth after review" loop is now functional and produces traceable proposals.
- Enhanced _synthesize_supervisor to attach the full selected 100% idea (with all evidence) in the final output under "selected_research_idea_approved_for_integration".
- Extended the dedicated run_blockchain_improvement_cycle to also consume structured new_capability_candidates (using their fit + suggested_apply_data for 100% proposals, not only string actionable).
- Added `integrate_research_idea(idea_index)` high-level helper: one call does intent detection → full raw candidate resolution → high-fidelity proposal generation → guarded_propose. Perfect for chat/MCP/automation.
- All Telegram/briefing files remain 100% untouched. Everything stays inside guards + allowed paths. The "research → 100% review → explicit OK → lossless proposal → guarded human-gated apply + measurable eval" loop is now complete and professional.
- **Focus**: openhands_skills + openhands_mcp + LangGraph as the automatic system. OpenHands UI (via start-ai.bat + MCP sidecar) remains the chat interface for interaction. Direct/LangGraph calls for reliable automation (bypass LLM for critical math like risk/PnL).
- **Professional**: Observable (LangGraph tracing + custom), evaluable (metrics for "better analysis", "successful self-fix"), safe (git branches for proposals, tests, human-in-loop for self-mods, rate limits), reliable (no hallucinations on critical via direct expert calls), local-first (Ollama via your bat), extensible.
- **Future-proof (from 2025-2026 research)**: 
  - Multi-Agent Systems with supervisor + specialists (LangGraph graphs for state/persistence/human-in-loop).
  - Recursive Self-Improvement (RSI) loops: reflect → propose (code/prompt/tool/arch) → experiment (test/metric) → keep if better (inspired by Karpathy AutoResearch, STO, Reflexion, Darwin-Godel, AlphaEvolve).
  - MCP as tool standard (you already have it; use streamable-http for latency).
  - Domain-specific + continuous research agents that feed evolution.
  - Production: observability, evaluation, memory, guardrails.
- **Phased, careful, no rush**: Each phase reviewed by you. Start with audit/harden existing (as you said "improve existing skills"). Measure progress. Build novelty incrementally.
- **"Next job" ready**: Treat as product – docs, CLI/automation entrypoints, monitoring, safety for real use.

## Research Insights Incorporated
- MAS + orchestration dominant in 2026 (LangGraph leads for production).
- Self-evolving/RSI practical now (Karpathy loops for autonomous experiment/improve; papers show reflection + code evolution works in domains like coding/research).
- MCP is the 2025-2026 standard for agent-tool integration (perfect fit).
- Need for research agents + self-improvement with safety.
- Our system can be unique: on-chain domain depth (your USD logic, Pulse specifics, real fallbacks) + engineering self-evolution + research loop in one controllable package.

## Current Foundation Audit (Phase 1 - Completed)
**Strengths (build on these)**:
- **Blockchain Intelligence core**: chain_analysis_expert.py – excellent real-data (Moralis optional + strong public fallbacks: BlockScout, PulseX GraphQL, RPC), your exact USD native inflow tiers/risk ( >50k very large etc.), pnl, pattern "big PLS + low activity + meme bag" ONLY on thresholds, portfolio, flows, persistent memory, explorer links (scan.pulsechain.com). Integrated in MCP as `analyze_wallet` (with strict "address" param schema – no more wallet_address hallucinations). Used in v2 orchestrator and langgraph. Good caching started (lru in MCP).
- **MCP exposure**: openhands_mcp/server.py – native tools (analyze_wallet, execute_v2_task routing to v2 agents, get_market_context, fetch_full). Streamable-http support, path setup, cache for latency. Solves "I cannot", schema issues, sandbox path hell. Perfect for chat interface.
- **Orchestration & Multi-Agent**: langgraph_orchestrator.py – explicit graph, direct expert calls for critical (risk/PnL never through LLM), supports embedding multi v2, MCP interop, persistent checkpointers, human-in-loop, deployable. Explicitly notes "without touching the 6-msg briefing engines". Fallback to direct.
  openhands_multiagent_v2/: advanced_supervisor, multi_agent_orchestrator_v2 (plans agents, auto Pulse/Solidity), coder/debugger/reviewer/tester, market_analyst_v2, hyper_evolution_agent (stores evolutions), strategic_oracle, smart_trigger_system. Hyper evolution + self_improving_agent.py (reflect, store in memory/vector).
- **Self-improvement seeds**: self_improving_agent.py, capability_evolver.py, hyper_evolution_agent.py, prompt_optimizer.py – basic reflection, memory, evolution storage. Good starting point for RSI loops.
- **Other**: tool_integration_hub (market context), persistent_memory (Chroma/JSON), v2_entry for routing, existing prompts/microagents for triggers.
- Launcher: start-ai.bat + runtime/Dockerfile (preloads skills for sandboxes/MCP), MCP sidecar – keeps the "local AI" experience.

**Gaps / Areas for Improvement (harden first)**:
- **Latency/End-to-end for domain tools**: Heavy calls (Moralis + multiple RPC/GraphQL) can take 30-45s+ with timeouts (BlockScout read timeout, Moralis 401 on history for Pulse sometimes). MCP client often 30s timeout before response. Cache helps repeats (0s), but first calls slow. Fallbacks not always fast/parallel enough.
- **Self-improvement**: Mostly storage/reflection, not full RSI (no propose code edit + run experiment + auto-keep if better with metrics/tests). No guardrails for "what can be changed". Hyper evolution basic.
- **Research/Learning**: Almost none. No web/GitHub/arxiv search, paper digestion, injection of new AI patterns (e.g., new reflection technique from research → apply to improve Blockchain accuracy).
- **Orchestration unification**: Existing orchestrators/supervisors good but not explicitly 3 specialized agents (Blockchain/Engineering/Research) with clear delegation, shared evolution state, research feeding loop. Intent parsing/triggers exist but can be stronger for auto "use Blockchain for wallet, Engineering for code fix, Research for latest technique".
- **Novelty/Professional gaps**: No closed-loop "research discovers → engineering evolves → blockchain gets better" with measurable improvement. Limited observability/eval for the system itself. MCP good but can expose specialists better. Self-mod needs safety (allowed paths only, git, tests, human gate). Not yet "product" with docs, CLI, monitoring.
- **Existing skills to improve** (as you said): 
  - chain_analysis_expert: More parallel fetches, shorter adaptive timeouts, better Moralis/Pulse specific (add more known dex/contracts), enhanced caching (beyond lru), output validation to prevent partial data.
  - MCP server: Expose more (e.g., research tools), better error/timeout handling, structured outputs.
  - self_improving/hyper: Evolve to support "propose change" for code.
  - LangGraph/multi v2: Integrate research, add metrics for self-eval.
- **Forbidden**: Any code touching telegram_engine.py, master_market_brain.py, the briefing engines (geopolitical, corporate_news, etc.), send_*.bat, 6-msg daily system. In self-improver: hard exclusion + "if path in forbidden: reject".

**Opportunities for "something that doesn't exist yet"**:
- A domain + self-evolving loop specialized for PulseChain (your USD logic + real data) where Research agent pulls latest AI (e.g., new agent patterns, better on-chain methods) and Engineering applies to make the Blockchain agent more accurate/faster over time (e.g., auto-add new patterns, optimize fetches).
- Full RSI inspired by Karpathy (autonomous experiments with metric "analysis quality" or "fix success rate") + papers, but guarded and domain-focused.
- MCP + LangGraph backbone for reliable chat + automation, with the system "living" and improving its own capabilities as a professional tool.
- This combo (on-chain depth + engineering self-evolution + research) in a local, launchable, observable package is rare/high-value.

## Phased Implementation Plan (Careful, Incremental, Reviewed)

**Phase 1: Audit & Harden Foundation (Current - just completed audit; next: small harden)**
- Improve existing skills first for reliability/latency (fix what we saw in convos).
- Add basic guardrails skeleton.
- Output: This doc + small code updates.

**Phase 2: Design & Research Agent**
- Design the 3-agent supervisor graph (LangGraph evolution of existing orchestrator).
- Implement Research & Learning Agent (add search tools – e.g., web via requests/duckduckgo or add Tavily if key; GitHub API; arxiv; synthesize learnings into persistent memory/knowledge base that Blockchain/Engineering can query).
- Expose via MCP.

**Phase 3: Supervisor + Delegation**
- Evolve/create supervisor that uses smart triggers/intent to delegate (Blockchain for wallet/chain/risk, Engineering for code/debug/fix in project, Research for "latest on X").
- Use direct expert calls for critical (risk/PnL).
- MCP for OpenHands chat access.

**Phase 4: Guarded Self-Improvement Loop**
- Enhance hyper/self_improving to full RSI: reflection on traces, propose changes (only to allowed paths: skills, mcp, multi v2, langgraph, automation; reject others), write to git branch, run tests/eval (e.g., "did risk accuracy improve?"), human approval gate, apply if good.
- Inspired by trends: experiment loop with metrics.

**Phase 5: Professional Polish & Novelty**
- Observability (tracing, logs for evolution), evaluation harness (metrics for each agent, system improvement score).
- Safety, packaging (as product), integration with start-ai.bat/MCP sidecar.
- Make the closed loop real: Research feeds Engineering → improves Blockchain (e.g., auto-add new on-chain pattern discovered in research).
- Docs, examples, "how it gets better over time".

**Novelty Features to Prioritize**:
- Closed research → evolve → better domain performance loop.
- Domain depth (your exact logic preserved/enhanced).
- Professional RSI with real guardrails (not open-ended dangerous self-mod).
- MCP/LangGraph as modern stack.

## Immediate Next Actions (After your "go")
1. Harden chain_analysis_expert + MCP for latency/robustness (e.g., better caching, parallel, timeout handling, update descriptions for model following "chain must be exactly 'pulsechain'").
   **Completed this step (post "κραταμε το νεο qwen και συνεχιζουμε")**:
   - chain_analysis_expert.py: ThreadPoolExecutor (max_workers=3) parallel execution of BlockScout + PulseX GraphQL + RPC eth_getLogs fallbacks inside fetch_real_token_activity (main win for the 30-45s first-call latency). Added explicit USD-tier comments quoting your economic rules.
   - openhands_mcp/server.py: Dramatically reinforced analyze_wallet docstring + added runtime normalizer (catches/fixes "analyze_chain", "wallet_address", "_pulsechain"/"pulse" etc. that appeared in the cb04eacf... diagnostic convo). Same for the `research` tool (strong "NEVER browser" + "MUST call for any research/latest/2026/RSI..." language).
   - Both files: AST-level verified clean. No new deps. Direct attack on the exact failure modes you showed.

2. Start Research Agent skeleton (new file in skills, basic search, integrate to memory).
   **Expanded in this step** (after "ας επεκτείνουμε πρώτα λίγο το research_agent"):
   - Prior research retrieval at start of every research() call (builds cumulative knowledge, avoids repetition).
   - High-signal tracked repos (LangGraph, DSPy, AutoGen, Karpathy patterns, etc.) + targeted GitHub agent searches.
   - `_synthesize_and_extract()` helper that turns sources into clean, deduplicated, tagged `actionable_for_engineering` / `actionable_for_blockchain` + `recommended_experiments`.
   - Stores not only the full bundle but also individual `research_actionable` memory entries (type=research_actionable) for granular consumption.
   - New public method: `get_actionable_for(target="engineering"|"blockchain"|"all")` — direct consumable lists for supervisor / other agents / LangGraph nodes.
   - Enhanced `get_latest_insights` to prefer actionable items.
   - More seeded 2026-relevant insights + focus-aware extraction (MCP strict schemas, parallel patterns, guarded RSI propose-on-branch, etc.).
   - Still 100% defensive + strong FORBIDDEN_PATHS.

   **Additional small expansion (user: 3.2.1)**:
   - Added defensive import of tool_integration_hub (same pattern as chain_analysis_expert).
   - Market context integration: when focus involves onchain/pulse/defi/market/all, calls run_market_snapshot() and injects compact snapshot + targeted actionable items for Blockchain (e.g. "correlate large native inflows with current PLS price level", "make risk scoring market-regime aware").
   - Results now include "market_context" field.
   - Synthesis step updated to generate experiment suggestions that combine research + live market data.
   - Top-level docstring and research() behavior updated to document market-aware research.
   - This closes one more part of the "Research feeds Blockchain with richer, market-aware signals" loop without duplicating heavy market logic.

3. Evolve one existing orchestrator toward the 3-agent supervisor (add routing).
   **Continued in this step** (user: "πρωτα Συνέχεια στον supervisor (πιο robust conditional routing, parallel specialists, καλύτερο engineering integration)"):
   - More robust conditional routing:
     - `_classify_intent` now produces explicit `execution_plan` + `plan_index` for deterministic ordering.
     - Cleaner router functions (`_route_after_inject`, `_route_after_join`) with better handling of multi-specialist cases.
   - Parallel specialists support:
     - When both "research" and "blockchain" are needed, the router returns a list → LangGraph fans out to both nodes concurrently.
     - New `_join_specialists` convergence node (ensures results from parallel branches are collected before engineering or synthesize).
     - Fallback `supervise` path also runs parallel-friendly (research + blockchain can both execute even if order varies).
   - Better engineering integration:
     - `_execute_engineering` now heavily consumes `research_context` to auto-generate concrete, prioritized "proposals" (e.g. "apply ThreadPool more broadly", "inject market_context into risk scoring").
     - Proposals carry "requires_human_approval" + "allowed_paths_note".

   **Immediately after (per user order "και μετα Πιο βαθιά δουλειά στο Engineering/RSI")**:
   - Created professional centralized `openhands_skills/guards.py` (single source of truth):
     - FORBIDDEN_PATHS + is_forbidden_path + is_allowed_for_modification + validate_proposal + enforce_guard.
     - Used by research_agent, hyper_evolution_agent, and langgraph_orchestrator Engineering.
   - All duplication of forbidden logic removed (or safely fallen back).
   - Proposal generation in supervisor now calls central `validate_proposal`, produces file-specific `target_file` hints, and attaches guard metadata.
   - guarded_propose in hyper now uses central validation and writes much richer, auditable pending_proposal json files (with human_action_required steps, guard_validation, etc.).
   - This is the most important "serious system" step: safety is no longer scattered; self-improvement proposals are validated at generation time and at propose time.

   The foundation for trustworthy recursive self-improvement is now in place.

   **Batch of critical professionalization work (user: "κανε ολα τα παραπανω")** - all 4 areas implemented together:
   - **Deeper RSI (more real/actionable proposals)**: Proposals now include `edit_spec`, `search_replace_hint`, `target_file`, and `rationale`. Structured so they can realistically become patches. Generated with concrete hints for files like chain_analysis_expert.py, server.py, langgraph_orchestrator.py.
   - **More observability + metrics**: Rich `evolution_stats` + `evolution_metrics` in every supervisor result (proposals_total, improvement_proposals, blocked_by_guard, research_items_used, passed_to_guarded, which legacy agents were called). Guarded proposals now store counts + safety_failures in persistent_memory.
   - **Better integration of existing self-improving artifacts**: `self_improving_agent.reflect`, `capability_evolver.analyze_and_evolve`, and `security_guardian` (scan on proposed targets) are now called from inside the supervisor's Engineering node when proposals are produced.
   - **Harder security testing of the safety layer**:
     - New `test_proposal_safety()` + `log_security_violation()` in central `guards.py`.
     - Every proposal is safety-tested at generation (supervisor) **and** again in `guarded_propose`.
     - Violations are persisted with type "security_violation". Blocked proposals carry full safety_report.
     - `guards.py` is now the enforced single source of truth (research_agent, hyper_evolution, supervisor all import it).

   All changes stay strictly inside allowed areas. The closed research → proposals → guarded propose loop is now observable, validated at multiple layers, and integrated with prior self-improvement skills.

   **Next step executed (user: "ποιο νομιζεις οτι ειναι το επομενο βημα ? καντο")**:
   - Closed the guarded RSI loop with real **propose → safe apply**.
     - Proposals now carry rich `apply_data` (file, operation, old_string_hint, new_string_hint, description) ready for automated guarded edit.
     - Added `perform_guarded_edit(target_file, old_text, new_text, dry_run=True)` to central guards.py:
       - Always re-validates target.
       - dry_run=True (default): returns diff_preview + report, no write.
       - dry_run=False: performs the replacement only on allowed paths, writes, logs to memory with type "guarded_apply".
     - Implemented `apply_proposal(proposal_id, dry_run=True)` in hyper_evolution_agent:
       - Loads pending json.
       - Re-runs full guard + safety tests (defense in depth).
       - Calls perform_guarded_edit.
       - On real apply: moves file to applied/ subfolder, updates status, full audit report.
     - Exposed as first-class MCP tool: `apply_proposal(proposal_id, dry_run=True)`.
     - Updated supervisor proposals, MCP startup messages, and this plan.
   - The full professional cycle is now usable end-to-end from the chat / automation:
     supervise("research latest... and improve our on-chain expert") 
     → review pending_proposals/ 
     → apply_proposal("proposal_xxx", dry_run=True) for preview 
     → after review/tests: apply_proposal(..., dry_run=False)
   - Default is always safe (dry_run). Human explicit action required for real change. All on allowed paths only.

   The self-improving system now has a complete, observable, heavily guarded propose-apply loop that can actually evolve the allowed codebase safely. This is the key milestone for "something that doesn't exist yet" and professional quality.

   **What I did as "the most important next" (per "κανε οτι νομιζεις συμαντικοτερο")**:
   - Added `run_blockchain_improvement_cycle(focus="onchain")` (and `improve_the_blockchain_expert` convenience) in the supervisor.
     - Runs focused research on on-chain patterns / risk / DeFi forensics.
     - Maps the actionable insights into 1-2 concrete, validated proposals with rich `apply_data` (specific edits to chain_analysis_expert.py: more DEX contracts, market regime injection into risk/PnL).
     - Files them via the full hardened guarded_propose (all gates: extra .approved, tests, human_approved, size, etc.).
     - Runs pre-eval with the harness.
     - Returns proposals + pre score + exact human instructions + expected benefit.
   - Exposed as first-class MCP tool `improve_the_blockchain_expert(focus="onchain")`.
   - This is the "make the closed loop real" piece: Research discovers improvements for the domain expert → Engineering turns them into guarded, measurable proposals → Human gates → Apply → Re-run get_system_evaluation() to see the Blockchain agent (accuracy, system score) actually got better.
   - Updated prints and plan. The demo at the bottom of the orchestrator will show it on next run.

   This is the highest-leverage thing for the user's use case (professional on-chain intelligence that improves itself) and for the "professional self-evolving system" goal. 

   All strictly in allowed areas. No Telegram/briefing touch ever.

   **Next upgrade step (user: move to the next on the list after the hardened RSI/apply/rollback)**:
   - Created dedicated `evaluation_harness.py` (EvaluationHarness):
     - Runs quantitative Blockchain evaluation on sample test cases (risk level accuracy vs expected per user's USD tiers + patterns, latency).
     - Computes `system_improvement_score` (weighted on blockchain quality + speed + evidence of successful guarded applies).
     - `compare_pre_post` for delta after improvements.
     - Stores every run to persistent_memory (type="system_evaluation") for trends.
   - Integrated:
     - After every successful guarded apply in hyper_evolution: automatically runs full eval and attaches `post_apply_system_evaluation` (score + blockchain accuracy) to the record.
     - In supervisor synthesize: attaches `current_system_health` snapshot to every combined output (so supervise calls now show live if the loop is improving the Blockchain agent).
   - Exposed via MCP: `get_system_evaluation()` tool – run it after applies to see measurable improvement.
   - Updated demo and prints.
   - This makes the closed loop *real and measurable*: Research discovers → Engineering proposes/applies (guarded) → Evaluation quantifies if Blockchain got better (accuracy up, latency down, system score up).

   Now we can objectively track "the system is getting better over time" instead of just hoping. Next could be packaging/docs or targeting specific improvements from research into the chain expert.

All changes will be small, reviewed, with comments noting "part of upgrade to 3-agent self-improving system per future trends".

**Forbidden Reminder**: In all code (especially self-improver), hardcode:
forbidden = ["telegram_engine.py", "master_market_brain.py", "geopolitical_engine.py", "corporate_news_engine.py", "send_briefing.bat", "send_simplex_briefing.py", any briefing 6-msg logic]
if any(f in path for f in forbidden): reject.

Let's go! Confirm if you want me to start with specific harden (e.g., improve chain expert now) or the Research skeleton first.

We will build something unique and professional, step by step. 🚀

(Keeping Telegram 100% untouched as always.)

## Latest Milestone (post user "παμε! κανε αυτο που ειπες" - Meta-Supervisor full loop)

**Completed**:
- Full end-to-end guarded self-improvement loop test for the Meta-Supervisor (`test_meta_supervisor_full_guarded_loop`):
  - Dynamic proposal generation from real `get_meta_learnings` + `get_research_lab_ideas`.
  - Same-cycle consumption via `_execute_engineering`.
  - Real `hyper_evolver.guarded_propose` (all central guards + safety tests + pending json written).
  - Exact human approval simulation ( `human_approved=True` + verbatim `user_approval_text` + `<id>.approved` marker file).
  - `apply_proposal(..., dry_run=True)` exercising `perform_guarded_edit` dry path + diff_preview.
  - Pre/post `run_system_evaluation()` + harness `compare_pre_post`.
  - Dedicated `_record_meta_supervisor_reflection` helper + verification that `was_meta_supervisor_self_improvement` flag is stored in persistent_memory (type=meta_learning).
- Minimal safe hardenings:
  - Made `apply_data` hints in meta_sup proposals more literal (exact code block from `_meta_supervise`) so guarded edit matching works for dry-run previews.
  - Extracted reusable reflection helper so credit logic is not locked inside one improvement cycle.

**Verified**:
- All 8 major gates exercised in the test (proposal gen, consumption, guarded propose, pending file, human approval sentence+files, dry apply with diff, eval, reflection flag).
- Zero impact on forbidden paths (Telegram/briefings etc. never referenced except protective notes).
- Blockchain direct logic (USD tiers, risk, PnL, parallel fallbacks) untouched.
- Everything remains strictly guarded (human gate, .approved, pre-tests, dry_run default, rollback paths, 100% fidelity on research data).

This proves the supervisor can now propose improvements to *itself* in a professional, fully-auditable, human-gated way — a key piece of the "self-referential" Hierarchical Agent Swarm vision.

Next natural steps remain: MCP exposure of supervisor tools, or concrete improvements to the Blockchain expert driven by the research lab.

## Recent Progress (alerts + supervisor integration + next plan items)
- Deep integration of large ecosystem alerts (HEX/PLSX/INC on Pulse) into LangGraph supervisor + more automatic scheduled proactive:
  - _classify_intent auto-detects "check this whale", large HEX/PLSX/INC/ecosystem alert intents (flags ecosystem_alerts_requested + scheduled_proactive_requested + adds both blockchain and research specialists).
  - Research execute now auto-uses run_scheduled_proactive_research (lab_mode=True, focus on onchain/pulse) when scheduled flag is set. This makes "scheduled proactive" more automatic for alert/whale queries: user says "check this whale for large HEX moves" -> auto fresh lab ideas for better monitoring patterns + current ecosystem alerts from expert + surface in result.
  - _execute_blockchain continues to focus context and surface the alerts when relevant.
  - Test simulation confirms flags and auto scheduled for such intents.
- Better MCP exposure for alerts:
  - check_large_ecosystem_movements enhanced with note on auto supervisor scheduled trigger.
  - Added to top-level tools list in module doc (alongside run_scheduled_proactive_research).
  - The combination allows the agent in chat to do automatic discovery + focused alerts without manual steps.
- **NEW: No-address chain-wide scan for large movements** (exactly for your request "check this whale for large HEX PLSX INC moves on pulsechain" without giving 0x):
  - New method in expert: `scan_large_ecosystem_movements(tokens, min_usd)` using BlockScout per-token-contract tokentx to find recent big transfers of the tokens (returns from/to addresses, tx, USD value).
  - New strict MCP tool `scan_large_ecosystem_movements_on_pulsechain(tokens, min_usd)` with full CRITICAL RULES + XML example. Returns "large_movements" + "candidate_addresses".
  - Supervisor classify/execute now supports no-address scan requests: if "large ... moves on pulsechain" and no 0x in input, runs the scan and returns the list of addresses with big moves + note "say 'analyze the first one' to start full analysis".
  - This enables the exact flow you described: get the hot addresses from the scan, then start the supervisor analysis on them (risk, PnL, profile, etc.).
- Further items from this query implemented:
  - Guarded proposal created (pending + approved + .approved) for "auto-analyze of top candidates from the scan" (in supervisor scan branch, auto runs analyze on top 2 and includes summaries/risk/alerts in result). Code change applied.
  - More scheduled integration: in scan branch, explicitly runs scheduled research (if not flagged) and attaches "fresh_research_ideas_for_monitoring" to the scan result.
  - Real whale/large test: ran global scan + analyze on real history address (0x38be95f...) with ecosystem focus; shows integration (data limited in env but API ready).
  - MCP for combined scan+research: new strict tool `scan_and_research_large_ecosystem_movements` (calls scan + scheduled, returns candidates + ideas, full CRITICAL + XML).
- All changes respect FORBIDDEN_PATHS, 100% fidelity, guarded human-in-loop, exact USD rules. No telegram/briefing files touched.
- This makes the alert feature (and proactive research) truly automatic in the 3-specialist swarm. The scan + supervisor + scheduled research + auto-analyze + combined MCP now let you discover and analyze large movements without pre-knowing the addresses, with fresh research automatically.

Ready for more (e.g. apply the auto-analyze guarded, test with live data, or next plan item).

## 3 Tasks Completed (user request after meta-sup E2E)

**1. MCP Exposure of supervisor (from chat with strict schema)**
- Added 3 new @mcp.tool with full CRITICAL CALLING RULES + XML examples + notes:
  - `get_research_lab_ideas(limit)`
  - `get_meta_learnings(limit)`
  - `integrate_research_idea(idea_index)`
- Enhanced dummy for research_agent.
- Existing `supervise`, `list_pending_proposals`, `approve_and_apply_proposal` already provide the full loop. Now user/chat can natively list lab ideas, get meta, integrate without Python.

**2. Real Blockchain expert improvement via the loop**
- Added `propose_blockchain_expert_improvements_from_lab(max_ideas=2)` in orchestrator.
- Pulls lab ideas (or fresh lab_mode research), selects high-fit for chain_analysis_expert (parallel fallbacks, PulseX, market in risk/PnL).
- Builds proposals with **exact must_preserve** (USD tiers in $, small amounts low risk, public fallbacks, ThreadPool, guards, human gate, pre/post eval).
- Runs guarded_propose + pre/post eval + reflection.
- Exposed as MCP `propose_blockchain_improvements_from_lab`.
- User can then approve via the standard sentence flow.

**3. Proactive research more automatic (runs without explicit command)**
- In _classify_intent: auto sets `auto_proactive_lab_requested` for any "self / improv / engineering / meta / lab" intent.
- In _inject_research_context: honors the flag, forces `lab_mode=True` + "self_improving" focus, stores full raw candidates as proactive_fitting_ideas (and research agent stores as research_lab_idea).
- Ideas surface automatically in supervisor results; user can immediately "integrate the first one" or ask details.

All changes:
- Strictly in allowed paths only.
- Full guards + 100% fidelity (verbatim evidence, no approx).
- USD economic rules and FORBIDDEN_PATHS preserved 100%.
- MCP tools follow the exact strict pattern used for analyze_wallet / fix_tool_call_error / approve_and_apply.

The system is now more usable from chat and the research→propose→guarded→apply loop for the core Blockchain expert is directly invocable.

## New Approved Enhancements (Human Approved 2026-06-12)

Based on recent research (LangGraph/AutoGen patterns), the following three proposals are approved for implementation. They align with the existing philosophy of explicit graphs, direct experts for critical paths, guards, human-in-loop, and MCP tools. All changes will be in allowed paths only, with full guarded flow, tests, and rollback support.

**Human Approval**: Explicitly granted for all three as a "Durability + Guardrails v2" milestone. No changes to forbidden paths (Telegram/briefings). Use existing guarded_propose + human_approved + .approved + eval harness flow.

### 1. Robust State Persistence & Recovery Mechanism
**Target**: langgraph_orchestrator.py, persistent_memory.py (orchestration layer)
**Description**: Harden LangGraph checkpointing with strict write ordering, persistent (file/SQLite) backends by default, and explicit recovery logic that distinguishes replay vs re-execute. Add checkpoint metadata (version, timestamp, last_successful) to SupervisorState.
**Expected Benefit**: Long-running agents (research loops, multi-turn supervisor) survive crashes/interrupts with safe resumption.
**Implementation Notes** (guarded):
- Default to SqliteSaver or file-based checkpointer in graph setup.
- Add `recover_supervisor_state()` helper.
- Integrate with existing persistent_memory for cross-session recovery.
- All edits guarded, with pre/post eval on supervisor reliability.

### 2. Tool Call Interception Protocol (GuardrailProvider)
**Target**: guards.py, openhands_mcp/server.py, langgraph_orchestrator.py
**Description**: Formalize a GuardrailProvider (inspired by AutoGen) that intercepts ALL tool calls (MCP tools like web_research/analyze_wallet, direct experts, execute_v2_task). Validates: intent match, required params (incl. security_risk where applicable), security context, and applies pre-dispatch hooks (schema normalization, rate limits, confirmation).
**Expected Benefit**: Eliminates schema errors (e.g. browser 'security_risk', wrong param names), reduces bad calls, centralizes security.
**Implementation Notes** (guarded):
- Add GuardrailProvider class in guards.py (central, importable).
- Wrap @mcp.tool() calls and supervisor expert invocations.
- Extend existing validate_proposal + user_confirmed flow.
- Enforce for new tools; backport to critical ones like web_research (already has user_confirmed).
- Add tests in evaluation_harness or new tool_interception tests.

### 3. Explicit Graph-Expert Orchestration
**Target**: langgraph_orchestrator.py (and related .md for microagents)
**Description**: Further explicitize the graph: critical/high-stakes paths (on-chain math/risk, tool dispatch, web research, proposal validation) MUST route to direct Expert nodes/functions, not LLM classification. Use LangGraph nodes/edges for routing decisions where possible. Reduce LLM in classify_intent for these paths.
**Expected Benefit**: Near-zero hallucinations on critical paths (risk/PnL, security, web fetches). Matches existing "direct expert" pattern and recent web_research auto-routing.
**Implementation Notes** (guarded):
- Enhance _classify_intent and _execute_* to have more explicit branches for "web", "critical_security", "risk_calc".
- For web tasks: hard-route to web_research MCP (already partially done).
- Add explicit "expert_node" wrappers that bypass LLM for known critical intents.
- Update tool-restrictions.md and openhands_v2_entry.md to document the explicit graph preference.
- Measure via evaluation_harness (hallucination rate on test cases).

**Approval & Process**:
- All three approved by human (as per this entry).
- Will follow full guarded flow: research-backed proposals, human_approved flag, .approved files, pre-apply tests, post-apply eval (system_improvement_score).
- Changes only in allowed roots.
- After each, run verify + supervisor tests + human review.
- New stable tag after full integration: e.g. stable-2026-06-12-durability-guardrails.

Next: Generate formal guarded proposals for each (using existing integrate/propose flow), then implement incrementally with backups.

### Post code-review fixes (2026-07-07)
Bugs reported by /code-review (χωρις αλλαγες) were fixed:
- server.py: ctx unbound + missing log in analyze_wallet guard path (moved assignment before guard; added defensive logger dummy; standardized error msg).
- langgraph_orchestrator.py: 
  - Persistence: _persistent_savers cache + thread_id threading so MemorySaver is reused across supervise_task calls (real cross-call recover_last_state now possible in-memory).
  - Graceful shutdown: consumption in _classify_intent + pre-check in SupervisorGraph.invoke.
  - Recovery: wrapped recovered state to preserve {combined_output, summary} shape expected by callers.
All changes limited to the two allowed files. verify_system.py still reports "All 16 sections PASSED". Public API (supervise_task with use_persistence) and internal paths smoke-tested.

### Image/Video Generation Improvements (2026-07)
- Added generate_image / generate_video as guarded MCP tools with full user_confirmed proposal flow (like web_research).
- ComfyUI backend (Flux.2 images + Wan 2.2 video) with external workflow JSON loading support via workflows/visual/ (using project_paths).
- Supervisor now detects visual intents and can execute generation (visual_generation_needed flag + post-process call).
- Health check for ComfyUI, prompt injection support, chaining notes to Designer/3D specialists.
- Keeps stubs as fallback; users export real workflows from ComfyUI (no massive hardcoded JSONs).
- Integrated with guards (risky tools). Use reference_image for image-to-video.
