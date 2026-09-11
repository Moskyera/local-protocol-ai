---
name: openhands-v2-entry
description: Κύριο entry point για OpenHands. Αυτόματα δρομολογεί tasks σε v2 agents + Solidity/PulseChain expert. Ιδανικό για smart contract development σε Ethereum και PulseChain.
trigger:
  keywords: ["openhands", "v2", "full task", "smart contract project", "build evm", "pulsechain contract"]
---

# OpenHands v2 Main Entry

**Recommended way to use with OpenHands (now the MAIN system for smart contracts):**

Call `run_task(your natural language task)` — everything is **automatic**:

- Detects Solidity/EVM/PulseChain/DeFi tasks.
- Smart Triggers + Advanced Supervisor orchestrate v2 agents.
- Enhanced Solidity Expert handles full pipeline (code + vesting/staking/governance/upgradeable + audit + tests + deploy).
- Full PulseChain support (PLS, PulseX, chainId 369, specific gas/security notes).
- Agents are smarter: automatic delegation, chain awareness, structured reasoning + reflection.

Returns rich structured output perfect for OpenHands tool use.

Example automatic tasks:
- "Create a secure ERC20 with team vesting and staking rewards on PulseChain"
- "Full audited governance + staking project for PulseChain with tests and deployment"
- "Audit this contract for reentrancy, front-running and gas optimize for EVM/PulseChain"
- "Chain analysis on 0x... deployed this contract - trace deployer, visualize flows, check if seen before, suggest fixes (larger end-to-end)"

## Important: Using inside OpenHands Docker runtime / sandbox (for local 3000)

The agent (CodeActAgent) runs code inside a separate sandbox container with `/workspace` mounted.

**Always start your code execution with this pattern** (copy-paste into the code the agent will run):

```python
import sys
import os

# Make sure the skills are importable in the sandbox
for p in ['/workspace', os.getcwd()]:
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

from openhands_skills.openhands_v2_entry import run_task

# Example for wallet / chain analysis
result = run_task(
    "full_wallet_profile", 
    address="0x000000000000000000000000000000000000dEaD",
    chain="pulsechain"
)
print(result)  # rich dict with native transfers, balances, risk_score (USD-based), pnl_estimate etc.
```

This ensures the auto path setup runs and the real Moralis + public APIs + PnL/risk logic (with your USD thresholds) execute inside the sandbox.

The first turn after container start or new conversation will take longer (runtime init ~30-60s + first LLM calls). Subsequent turns in the **same conversation** are much faster because the sandbox stays warm.

**CRITICAL - Tool restrictions in OpenHands sandbox (V1+ with custom runtime & .agents/skills/):**
The default agent has a 'browser' tool that is dangerous and often causes schema errors (missing 'security_risk' etc.).
**NEVER call the 'browser' tool.** If you see it in available tools, ignore it completely. Only use: execute_bash, execute_ipython_cell, think, finish, str_replace_editor, task_tracker.

**Web / Browser actions - User approval flow:**
For studying, fetching, or downloading from any website:
- NEVER attempt to call the built-in 'browser' tool yourself (it will fail with the exact error "Missing required parameters for function 'browser': {'security_risk'}").
- Instead, in the conversation, propose clearly to the human: "To study the content of [URL] for [specific reason], I would like to use a safe research method / fetch key excerpts. Do you approve? (Yes = proceed safely, No = skip or provide the data yourself)"
- Wait for the user's explicit "yes" / "no" / "approved for study only, no download" reply before taking any action.
- This gives the user full control to give or deny the "green light" interactively for each site/action.
- Preferred safe methods: use dedicated research MCP tools (run_scheduled_proactive_research, etc.), execute_bash with curl/wget for specific pages (with user approval), or ask the user to paste relevant sections.

**Evolved setup (custom runtime + skills placement):**
- Skills pre-baked in runtime image (PYTHONPATH=/opt/openhands-skills) → direct `from openhands_skills.openhands_v2_entry import run_task` works in code execution!
- Your .md manifests in .agents/skills/ auto-load as microagents (keyword triggers like "wallet", "chain analysis", "pulsechain", "run_task").
- No more constant manual file loading with str_replace_editor for the skill code itself.

Use direct import for full_wallet_profile, risk/PnL etc.

If in limited env, fallback bootstrap:
import sys
import os
sys.path.insert(0, '/workspace')
sys.path.insert(0, os.getcwd())
