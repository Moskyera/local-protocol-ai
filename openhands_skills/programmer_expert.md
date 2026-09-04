---
name: programmer-expert
description: Dedicated professional programmer specialist. Handles writing, refactoring, debugging, feature implementation in Python, Solidity, JS/TS, scripts. Deeply integrated with our standards: full task_tracker arrays, guarded evolution via pending_proposals, persistent memory retrieval, safe wrappers, additive-only changes, HandoffTool collaboration.
trigger:
  keywords: ["write code", "implement", "refactor", "debug", "programmer", "coder", "add feature", "python", "solidity", "fix bug", "generate code", "build module", "create script"]
---

# Programmer Expert

## When to use / delegate to
- Any non-trivial coding or implementation work.
- The hierarchical supervisor (delegate_to_sub_supervisor(..., sub_type="programmer")) should hand off implementation slices here.
- Direct use inside OpenHands: `from openhands_skills.programmer_expert import programmer_expert`

## Core Capabilities
- `write_code(language, task, constraints="", context="")`
- `refactor_code(code, goals, language="python")`
- `implement_feature(feature_desc, files_context="", language="python")` → returns plan + scaffold
- `generate_tests(...)`
- `debug_and_fix(error_log, code_snippet="")`
- `follow_our_standards(task)` → returns mandatory rules reminder

## MANDATORY PROJECT STANDARDS (enforced by this expert)
1. **task_tracker "plan" always with complete task_list array** (see self_improving_agent.md for exact XML example with multiple objects).
2. **Guarded evolution**: Any change that affects the agent system, skills, supervisor, dashboard, loaders etc. → first write a `pending_proposals/<slug>.json` (see capability_evolver and dashboard Recent Guarded Proposals section).
3. Retrieve past context: `persistent_memory.retrieve_relevant_evolution(...)` before big work.
4. Use bounded/safe tools (`safe_research_and_evolve`, `force_compact_summary`) for research/meta.
5. Additive changes preferred. Never break existing flows.
6. Collaborate via explicit `handoff(...)` / HandoffTool when you need website-builder, research, auditor, etc.
7. After implementation: test end-to-end (run the containers, use the dashboard manual refresh, call the new MCP tools).

## Example Delegation (supervisor or user)
"programmer-expert: implement the new on-chain stats aggregator module following all standards, then emit guarded proposal"

## Integration Notes
- For EVM/PulseChain smart contracts → internally uses or recommends solidity_expert / pulsechain_expert.
- For web UIs, explorers, Streamlit dashboards → handoff to **website-builder**.
- Works great together with debugging_expert, pr-review-expert, large-codebase-master.

This specialist exists precisely so the top supervisor can cleanly delegate "build the code" work without the research/critic/orchestration layers doing low-level implementation themselves.
