---
name: chain-analysis-expert
description: "Απλοποιεί το chain analysis. Δίνει διεύθυνση (address) και παίρνεις: από πού έλαβε, πού έστειλε, τι έκανε (DeFi interactions, contracts), risks, explorer links. Ιδανικό για audits, debugging, contract tracing σε Ethereum/PulseChain."
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

**NATIVE MCP TOOLS (PROFESSIONAL UPGRADE - PREFERRED):**
If analyze_wallet (or fetch_full_wallet_profile) is available as a tool (MCP sidecar), call it **directly using the exact schema**:
- Parameter 1 name MUST be "address" (value = the 0x... string). Example: analyze_wallet with address is 0x000000000000000000000000000000000000dEaD
- Parameter 2 (optional) name "chain" = "pulsechain".
NEVER use "wallet_address" or invent params - the call will be rejected with error like the one you just saw.
Gets the full real-data report (USD risk, PnL, flows, portfolio, persistent memory) without any code execution or browser.

**CRITICAL RULE for OpenHands agent:**
Do NOT use the built-in 'browser' tool (it requires 'security_risk' parameter and causes "Agent encountered an error").
Prefer native MCP tools for on-chain data. Fallback: call the expert via Python code execution in the sandbox (custom runtime + direct imports from /opt or /workspace).

**AUTO-EXECUTE RULE (fallback):**
When user mentions wallet analysis, chain analysis, address on pulsechain, risk, native, pnl etc., immediately use code execution tool to run the v2_entry pattern (see the updated instructions in openhands_v2_entry.md microagent). Do not ask user to provide code.

The custom runtime makes direct imports work.

See openhands_v2_entry.md for the exact auto code to execute (and MCP section for the better native path).

This turns confusing on-chain data into actionable, simple insights for the agent.

New enhancements:
- Better ASCII + Mermaid-ready visualization stubs.
- Expanded known exploit patterns (reentrancy signatures, flash loan attacks, etc.).
- Persistent memory integration: remembers "we've seen this address before" across tasks (stores sightings with risks/timestamps).
- Contract creator/deployer specific analysis.
- Automatic use in larger end-to-end scenarios (audit + trace + viz + bug fix).
- Works seamlessly with PulseChain/Ethereum, market data for value estimation, and the smarter v2 agents (especially Debugger).

