---
name: chain-analysis-expert
description: Απλοποιεί το chain analysis. Δίνει διεύθυνση (address) και παίρνεις: από πού έλαβε, πού έστειλε, τι έκανε (DeFi interactions, contracts), risks, explorer links. Ιδανικό για audits, debugging, contract tracing σε Ethereum/PulseChain.
trigger:
  keywords: ["chain analysis", "analyze address", "wallet trace", "contract activity", "where did it send", "from where received", "tx history", "explorer analysis", "on chain", "address activity"]
---

# Chain Analysis Expert

**How to use (automatic in OpenHands):**
Give natural language like:
- "Analyze this address 0x... on PulseChain for incoming/outgoing and what it did"
- "Chain analysis on the deployer of this contract"
- "Trace flows for this wallet and check for suspicious activity"

It returns structured report with:
- Type (EOA/Contract)
- Direct explorer link (Etherscan / PulseChain scan)
- Incoming flows
- Outgoing flows
- What it did (interactions)
- Risks
- Market context integration for valuing transfers (tokenomics)
- Step-by-step how to dig deeper on explorer
- PulseChain specific notes when relevant

**Integration:**
- Automatically called by Debugger, Reviewer, Solidity Expert when addresses appear in context.
- Uses tool_hub for market data when token values matter.
- Works with v2 multi-agent for full automated tracing during smart contract work.

**CRITICAL RULE for OpenHands agent:**
Do NOT use the built-in 'browser' tool (it requires 'security_risk' parameter and causes "Agent encountered an error. Missing required parameters for function 'browser': {'security_risk'}").
Only analyze on-chain data by calling the expert via Python code execution in the sandbox.

For any need to study or fetch data from websites (even related to tokens/projects):
- Use the dedicated MCP tool **safe_web_research** (the only approved way).
- First call with user_confirmed=False to receive a proposal containing the exact text to show the human ("I would like to safely research ... Approve?").
- Wait for clear user "yes" / "approved for study only".
- Then re-call with user_confirmed=True.
This gives the user full interactive control (green light / red light) with security_risk and confirmation built into the tool. Never use browser.

How to load the expert in the sandbox (runtime has limited /workspace - only .git etc.):

- Use str_replace_editor with path="openhands_skills/chain_analysis_expert.py", command="view" to read the full source.

- Then use execute_ipython_cell to write the class to a temp file or exec the code you read, then instantiate ChainAnalysisExpert and call fetch_real_token_activity etc.

See openhands_v2_entry.md for the high-level run_task pattern and bootstrap code.

This turns confusing on-chain data into actionable, simple insights for the agent.

New enhancements:
- Better ASCII + Mermaid-ready visualization stubs.
- Expanded known exploit patterns (reentrancy signatures, flash loan attacks, etc.).
- Persistent memory integration: remembers "we've seen this address before" across tasks (stores sightings with risks/timestamps).
- Contract creator/deployer specific analysis.
- Automatic use in larger end-to-end scenarios (audit + trace + viz + bug fix).
- Works seamlessly with PulseChain/Ethereum, market data for value estimation, and the smarter v2 agents (especially Debugger).
