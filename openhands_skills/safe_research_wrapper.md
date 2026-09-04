---
name: safe-research-wrapper
description: Explicit, sticky MCP tools for safe/bounded research on new skills and forced summarization of large tool outputs. Golden mean to prevent context bloat, loops, and errors on meta "increase agent score" tasks.

trigger:
  keywords: ["new skill", "increase the score of our agent", "check github", "github for skills", "research latest agent", "safe research", "compact summary", "force summary", "bounded research"]
---

# Safe Research Wrapper - Explicit MCP Tools

These are **first-class MCP tools** (exposed via the 8765 sidecar) that enforce the safe path for any research/meta-improvement work.

## Available Explicit Tools (use these directly as MCP calls when possible)

- `safe_research_new_skills(topic, max_results=3)`
  - Safe entry for "look for new skills on github", "increase agent score", "research agent patterns".
  - Always uses small max_results.
  - Returns compact summary + recommendation. Never raw dumps.

- `force_compact_summary(large_observation, max_chars=2500)`
  - **Call this IMMEDIATELY after any large MCP result** (research, wallet profile, big JSON, etc.).
  - Forces truncation + instructions to produce 4-8 bullet user summary, then finish or ask user.
  - Prevents 50k+ char blobs from entering history.

- `safe_research_and_evolve(research_topic, max_results=3)`
  - Full golden path for capability evolution tasks.
  - Combines research + analysis + compact proposal.
  - Enforces all rules: proper task_tracker, no chaining on errors, user-facing output + finish.

- `force_summary_before_continue(large_mcp_result)`
  - Compacts and tells the agent: summarize for user now, do not call more research without new input.

## Strict Rules (enforced by these tools + microagent knowledge)

1. For any "new skill / github / increase score" request → use one of the safe_* tools first.
2. After any research or large data tool result → **always** call a force_*_summary tool before any further action.
3. Use correct full `task_list` in every task_tracker "plan" call.
4. On MCP error/timeout/rate_limit → report exactly once and stop. Use memory.
5. Always end with short user summary + `finish()` or one clarifying question. No internal loops.
6. Raw data only to small local files (e.g. research_raw.json), then ignored for context.

These wrappers make the safe behavior "sticky" — the agent is guided to use them, and the Python implementations + instructions prevent the problems seen in previous conversations (880k tokens, repeated schema errors, 30s timeouts, endless integrate/list_pending).

Use via MCP sidecar (preferred for reliability) or via code execution on the self_improving / capability_evolver classes.

This is the controlled way to keep powerful live research (GitHub, LangGraph patterns, etc.) while keeping context healthy and tasks terminating cleanly.

## New: 'research' alias (added to fix "Missing required parameters for function 'research': {'query'}" errors)
- Explicit MCP tool: `research(query="your research topic here", max_results=5)`
- Or use research_topic=... / topic=... (tolerant).
- Always routes through the safe bounded/compaction logic above.
- The LLM or any supervisor step that mentions "research" should now call this (or the longer safe_* names) and **must supply the query parameter**.
- This alias is registered as a first-class discoverable tool so the agent no longer crashes when it (or the project template) triggers a research step.