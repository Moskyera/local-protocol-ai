---
name: website-builder
description: Specialist for websites, explorers, dashboards and UIs. Especially powerful for PulseChain Explorer, wallet visualizers, guarded proposals dashboards, and anything that surfaces tx_narrator, contract_auditor, onchain_monitor, and pending_proposals data. Supports Streamlit, standalone HTML/JS, and React/Vite scaffolds.
trigger:
  keywords: ["website", "explorer", "dashboard", "ui", "build website", "pulsechain explorer", "make a site", "streamlit", "react", "frontend", "html explorer", "proposals list", "wallet ui"]
---

# Website Builder Expert

## Purpose
This is the dedicated specialist the hierarchical supervisor delegates to when the task is "make me a website", "PulseChain explorer", "beautiful dashboard for the proposals and wallet narration", etc.

It was added exactly because you asked: "μπορουμε να προσθεσουμε agents προγραμματηστες και ειδικους για κατασκευη κωδικα ή και website ?"

## Main Entry Points
- `build_pulsechain_explorer(task="...", features=[...])` → returns ready Streamlit code + standalone HTML + React scaffold + instructions. Perfect match for the current "Create PulseChain Explorer Website" conversation you are monitoring.
- `build_streamlit_dashboard(...)`
- `build_standalone_html_explorer(...)`
- `build_vite_react_scaffold(...)`
- `build_generic_website(...)`

## Deep Integration (this is what makes it special)
It knows about and wires:
- **tx_narrator** → "Swapped 12450 HEX on PulseX (2026-..) tx:0x..." beautiful stories inside the UI
- **contract_auditor** → address-based (or source) audits directly in the page
- **onchain_monitor** → can drive live sections or evolution triggers
- **Guarded Proposals** → the `pending_proposals/*.json` list with manual refresh (exactly the feature you requested and we implemented)
- **persistent_memory** + evolution activity
- Existing dashboard.py patterns (1-hour autorefresh + manual button)

## How the Supervisor Uses It
In advanced_supervisor (hierarchical):
- delegate_to_sub_supervisor( task, sub_type="website" )
- Then handoff from ProgrammerSupervisor or Orchestration to WebsiteBuilderSupervisor / the expert.

Direct usage inside OpenHands:
from openhands_skills.website_builder import website_builder
result = website_builder.build_pulsechain_explorer("Full PulseChain Explorer with narrated txs and proposals")

## Recommended Workflow (for the current website task)
1. The agent (or you) calls website-builder for the explorer.
2. It produces the Streamlit version → you can save it and run it.
3. It also produces a gorgeous static HTML single-file you can open instantly or host.
4. Any evolution of the explorer itself that touches core agent behavior should still create a guarded proposal.

## Stacks Produced
- Streamlit (fastest to run with our existing stack, reuses our :8501 patterns)
- Single-file Tailwind HTML/JS (zero deps, deploy anywhere)
- React + Vite + TS + Tailwind scaffold (for when you want a real frontend app)

Run the Streamlit one alongside the existing dashboard for maximum power (Recent Guarded Proposals will be live with the manual refresh button we added).

This specialist + the programmer-expert + the hierarchical supervisor with handoffs = the full "programmers and website specialists" capability you asked for.

**Flawless modern output (after detailed polish):**
- React projects now ship with complete runnable scaffolding (vite.config, tailwind.config, postcss, tsconfig, proper index.html, main.tsx, beautiful App with glass + framer + optional real Three.js).
- Standalone HTML is zero-dep, highly polished, production quality (particles, magnetic, scroll reveals, variable fonts, glass).
- Always pulls Code Researcher ideas when available.
- Explicitly supports **any website** (completely unrelated themes are first-class).
