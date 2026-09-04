---
name: tool-restrictions
description: Strict rules for tool usage in this OpenHands setup for PulseChain/EVM/wallet analysis to avoid errors and use skills efficiently.
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
**MANDATORY TOOL RULES (never violate):**
- ONLY use these tools: execute_bash, execute_ipython_cell, think, finish, str_replace_editor, task_tracker.
- **ABSOLUTELY FORBIDDEN:** 'browser' tool or any web browsing. Calling it causes "Missing required parameters for function 'browser': {'security_risk'}" and agent error. Ignore the browser tool even if listed.
- For any website study/research: Use the native MCP tool **web_research** (exact name). It has built-in confirmation (user_confirmed parameter). First call with user_confirmed=false to get proposal + message_for_human. Show it to the user and wait for explicit "yes" or "yes for study only". Then call the exact same tool again with user_confirmed=true and the same url/query. Never call any tool named "research" or "browser". This gives the user full interactive approval control and includes security_risk.
- **NATIVE MCP TOOLS (PREFERRED for professional use):** If analyze_wallet / execute_v2_task / fetch_full_wallet_profile etc. are available in your tools (MCP sidecar), call them directly with address or task_description. This is the upgraded path — explicit tools, reliable schemas, no refusals or sandbox import hacks for data/chain tasks.
- For using openhands skills / v2_entry / chain analysis (fallback if no MCP tools listed): The microagents will tell you the exact code. When the task matches (wallet/chain/pulse), **immediately execute the code from the v2_entry microagent instructions** using the code execution tool. Do not ask the user to write or provide the Python code.
- Microagents (these .md files) provide the knowledge - follow them automatically.
- Always prefer native MCP tools or code execution for analysis over manual browsing.

