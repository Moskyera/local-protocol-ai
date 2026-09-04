---
name: openhands-v2-entry
description: Κύριο entry point για OpenHands. Αυτόματα δρομολογεί tasks σε v2 agents + Solidity/PulseChain expert. Ιδανικό για smart contract development σε Ethereum και PulseChain.
triggers:
- chain analysis
- analyze address
- wallet trace
- contract activity
- where did it send
- from where received
- tx history
- explorer analysis
- on chain
- address activity
- openhands
- v2
- full task
- smart contract project
- build evm
- pulsechain contract
- wallet
- pulsechain
- run_task
- full_wallet_profile
- risk score
- native
- pnl
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
    address="0x38be95f628ed004a000ddf8724142a95e3c4b492",
    chain="pulsechain"
)
print(result)  # rich dict with native transfers, balances, risk_score (USD-based), pnl_estimate etc.
```

This ensures the auto path setup runs and the real Moralis + public APIs + PnL/risk logic (with your USD thresholds) execute inside the sandbox.

The first turn after container start or new conversation will take longer (runtime init ~30-60s + first LLM calls). Subsequent turns in the **same conversation** are much faster because the sandbox stays warm.

**CRITICAL - Tool restrictions in OpenHands sandbox:**
The default agent has a 'browser' tool that is dangerous and often causes schema errors (missing 'security_risk' etc.).
**NEVER call the 'browser' tool.** If you see it in available tools, ignore it completely. Only use: execute_bash, execute_ipython_cell, think, finish, str_replace_editor, task_tracker.

To load and use the skills (because the runtime sandbox has limited /workspace view - only git files):

1. Use str_replace_editor tool with path="openhands_skills/xxx.py" (e.g. "openhands_skills/openhands_v2_entry.py" or "openhands_skills/chain_analysis_expert.py") and command="view" or "read" to get the source code/instructions.

2. Then in execute_ipython_cell or bash, use the code you read, or write it to a local file (e.g. /tmp/skill.py) using cat or str_replace_editor with a path in /workspace, then exec(open('/tmp/skill.py').read()).

3. For run_task or experts, after reading the source, execute the relevant class or function in the cell.

**NATIVE MCP TOOLS (PROFESSIONAL UPGRADE - PREFERRED):**
If "analyze_wallet", "execute_v2_task", "fetch_full_wallet_profile" or similar appear in your available tools list (via MCP sidecar on :8765), **use them directly as first-class tools** with simple params. This is the evolved, reliable way:
- analyze_wallet with address is 0x... chain is pulsechain  (exact param names required: first param must be named "address", value the 0x string. Do NOT use wallet_address etc. or call is rejected). → full real USD risk/PnL/portfolio/activity (no sandbox code exec needed for data).
- execute_v2_task(task_description="...") → automatic v2 routing for contracts/DeFi/PulseChain.

These bypass base refusals ("I cannot access blockchain") because the capability is now an explicit registered tool with schema (framework handles security_risk etc.). Microagent knowledge + MCP = professional automatic behavior.

**FALLBACK (if MCP tools not listed): use the AUTO-EXECUTE code execution path below.**
When the user asks for wallet/chain analysis, full_wallet_profile, risk score, native inflows, or similar on a PulseChain address (keywords like wallet, chain analysis, analyze address, pulsechain, run_task), **immediately and automatically** (without asking the user or waiting) use the code execution tool to run the code.

Use **execute_ipython_cell** if available (parameter 'code' = the python code).

Or **execute_bash** with parameter 'command' = 'python -c "the code here"' (DO NOT use 'code' parameter for execute_bash, only 'command').

The code to run:

```python
import sys
import os
sys.path.insert(0, '/workspace')
sys.path.insert(0, '/opt/openhands-skills')

from openhands_skills.openhands_v2_entry import run_task

result = run_task("full_wallet_profile for the address on pulsechain")
print(result)
```

Output the tool call immediately. Do not explain or offer templates. The skill will return the result. Then summarize the key findings from the result (risk level, native inflows in USD, pnl, etc.).

This (MCP preferred, code fallback) is the MAIN professional way to use the v2 skills automatically.

