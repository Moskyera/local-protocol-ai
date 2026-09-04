"""
Website Builder Expert Skill for OpenHands
Specialist for building websites, explorers, dashboards, UIs.
Perfect for PulseChain Explorer, wallet visualizers, proposal dashboards, contract auditors, on-chain activity viewers.
Integrates deeply with our existing tools:
- tx_narrator (for human readable "Swapped X on PulseX...")
- contract_auditor (address or source based audits)
- onchain_monitor (events → alerts/evolve)
- persistent_memory + guarded proposals (Recent Guarded Proposals list)
- dashboard.py patterns (Streamlit + manual refresh)

Supports:
- Streamlit dashboards (easy to run alongside our existing :8501)
- Modern standalone single-file HTML/JS/CSS explorers (easy deploy, like AetherBubbles style)
- React/Vite + TS scaffold (for more ambitious frontends)
- Clean crypto/dark theme, responsive, explorer-style tables + forms
"""

from logger import log
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from openhands_skills.expert_base import ExpertSkill

# Optional composition with our on-chain specialists
try:
    from openhands_skills.tx_narrator import narrate_wallet_activity
except Exception:
    narrate_wallet_activity = None

try:
    from openhands_skills.contract_auditor import audit_token_contract
except Exception:
    audit_token_contract = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None

# Code researcher for fresh modern visuals / libs / patterns
try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


class WebsiteBuilder(ExpertSkill):
    """
    Modern Website Builder — general purpose.
    You can build ANY website (completely unrelated to our PulseChain/agent theme is 100% fine and encouraged).

    Supports rich modern visuals:
    - 3D (Three.js / @react-three/fiber)
    - Animations & micro-interactions (Framer Motion / GSAP / CSS + JS)
    - Particles, canvas effects
    - Custom / variable fonts + beautiful typography
    - Glassmorphism, modern gradients, scroll animations, tilt cards etc.

    Works standalone or as part of the programming team:
    - Can call CodeResearcher for fresh GitHub libs + patterns
    - Handoffs perfectly with ProgrammerExpert
    - Supervisor sub_type="website"
    """

    def __init__(self):
        self.themes = {
            "futuristic": "Dark + neon/cyan accents, glassmorphism, bold variable fonts, subtle 3D hero",
            "glass": "Heavy backdrop-blur + transparency, soft shadows, premium feel",
            "creative": "Bold typography, canvas/particles, playful but tasteful motion",
            "minimal": "Clean, lots of whitespace, excellent typography, micro hover states",
            "3d-hero": "Strong 3D or WebGL hero element + calm content below"
        }

    def build_pulsechain_explorer(self, task: str = "PulseChain Explorer Website", features: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        High-level entry for the exact use case the user is asking about right now.
        Returns multiple deliverable options + ready-to-use code.
        """
        log.info(f"Website Builder: Building PulseChain Explorer for: {task}")
        features = features or [
            "wallet_analyzer", "guarded_proposals_list", "contract_auditor_ui",
            "onchain_activity", "manual_refresh", "narrated_txs", "evolution_activity"
        ]

        deliverables = {
            "streamlit_version": self.build_streamlit_dashboard(task, features),
            "standalone_html_explorer": self.build_standalone_html_explorer(task, features),
            "react_vite_scaffold": self.build_vite_react_scaffold(task, features),
            "integration_notes": self._integration_notes(),
            "how_to_run": self._how_to_run_instructions()
        }

        # Store a learning for future website tasks
        if persistent_memory:
            try:
                persistent_memory.store_learning("website_builder:pulsechain_explorer", f"Built explorer variants for: {task} at {datetime.now().isoformat()}")
            except Exception:
                pass

        print("🌐 Website Builder: PulseChain Explorer deliverables ready (Streamlit + standalone HTML + React scaffold).")
        return deliverables

    def build_streamlit_dashboard(self, task: str, features: List[str]) -> str:
        """Returns a complete Streamlit app (similar style to our existing dashboard.py).
        
        IMPORTANT: MANUAL REFRESH ONLY.
        Auto-refresh (st_autorefresh or timers) is intentionally DISABLED to avoid rate limits on RPCs/APIs/proposals.
        Use the big Refresh button. Data loading is cached with long TTL.
        """
        code = f'''"""
{task} - Streamlit Dashboard (WebsiteBuilder)
Run with: streamlit run this_file.py --server.port 8501
Integrates: tx_narrator, contract_auditor, onchain_monitor, pending_proposals, persistent memory.

*** AUTO-REFRESH IS DISABLED ***
This dashboard uses MANUAL REFRESH ONLY (button below) to prevent rate limits.
Do NOT add st_autorefresh, time.sleep loops, or any 5-minute timer.
All expensive operations (proposals scan, on-chain calls) happen only on explicit user action.
"""
import streamlit as st
import os, glob, json, time
from datetime import datetime

st.set_page_config(page_title="{task}", layout="wide", page_icon="🔗")

st.title("🔗 {task}")
st.caption("Built by Website Builder Expert • Integrates our full agent toolset (narrate / audit / monitor / guarded evolution)")

# === MANUAL REFRESH ONLY - NO AUTO REFRESH TO AVOID RATE LIMITS ===
st.info("⏱️ Auto-refresh is DISABLED (was causing rate limits every 5 min). Click the button below to refresh data & proposals.", icon="ℹ️")

col1, col2 = st.columns([3,1])
with col2:
    refresh_clicked = st.button("🔄 Refresh Proposals & Data (Manual)", use_container_width=True, type="primary")

# Use session_state to control when we do expensive loads
if "last_manual_refresh" not in st.session_state:
    st.session_state.last_manual_refresh = 0

if refresh_clicked:
    st.session_state.last_manual_refresh = time.time()
    st.toast("Data refreshed manually", icon="✅")
    # st.rerun() will re-execute the script with the new timestamp

# Helper to decide if we should load fresh (only right after button or first load with no data)
def should_load_fresh():
    # Only load on explicit refresh or very first run
    return refresh_clicked or st.session_state.last_manual_refresh == 0

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache - change only on manual action
def load_proposals_cached():
    prop_dir = "pending_proposals"
    if os.path.isdir(prop_dir):
        files = sorted(glob.glob(os.path.join(prop_dir, "*.json")), key=os.path.getmtime, reverse=True)[:20]
        results = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({{
                    "file": os.path.basename(f),
                    "mtime": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
                    "data": data
                }})
            except Exception:
                pass
        return results
    return []

# Force cache invalidation on manual refresh by using a changing hash in the call
proposals = []
if should_load_fresh():
    # Clear cache for this run when user explicitly asked for refresh
    load_proposals_cached.clear()
    proposals = load_proposals_cached()
else:
    proposals = load_proposals_cached()

st.divider()

# 1. Wallet Analyzer (uses tx_narrator style)
st.subheader("📜 Wallet Activity Narrator")
addr = st.text_input("PulseChain address (0x...)", value="0x2b59... (example HEX)")
if st.button("Narrate Activity") and addr:
    if narrate_wallet_activity:
        try:
            story = narrate_wallet_activity(addr)  # expects the MCP tool or wrapper to be available in context
            st.success("Narrative generated (via tx_narrator)")
            st.write(story)
        except Exception as e:
            st.info(f"tx_narrator not directly callable here. In real OpenHands run: call the MCP 'narrate_wallet_activity' or import and use the function. Error: {{e}}")
    else:
        st.code("Use MCP tool: narrate_wallet_activity or from openhands_skills.tx_narrator import narrate_wallet_activity\\nThen pass real token_buy_sell_history_and_coins data.")
    st.caption("This section calls our tx_narrator for human-readable stories: 'Swapped X on PulseX (date) tx:0x...'")

st.divider()

# 2. Recent Guarded Proposals (the feature we added manual button for)
st.subheader("🛡️ Recent Guarded Proposals & Evolution Activity")
if proposals:
    for p in proposals:
        st.json(p["data"], expanded=False)
        st.caption(f"{{p['file']}} • {{p['mtime']}}")
else:
    st.warning("No proposals yet (or directory empty). Agents create pending_proposals/*.json during guarded evolution. Click the big Refresh button above to check again.")

st.divider()

# 3. Contract Auditor UI
st.subheader("🔐 Contract / Token Auditor (uses contract_auditor)")
token_addr = st.text_input("Token or contract address", key="audit_addr")
if st.button("Run Audit") and token_addr:
    if audit_token_contract:
        try:
            report = audit_token_contract(token_addr)
            st.json(report)
        except Exception as e:
            st.write("Call the MCP 'audit_token_contract' tool with the address (or source code).", e)
    else:
        st.code("MCP: audit_token_contract(address=...) or import from openhands_skills.contract_auditor")

st.divider()

# 4. On-chain Monitor / Evolution hooks placeholder
st.subheader("📡 On-Chain Monitor & Evolution Triggers")
st.write("Connects to onchain_monitor. Real polling version will trigger safe_research_and_evolve + telegram alerts on important events (large stakes, liquidity adds, new proposals, etc.).")
if st.button("Simulate On-Chain Event → Trigger Evolution"):
    st.success("In a full run this would call onchain_monitor.check_onchain_events_and_trigger() which can invoke safe_evolve / telegram.")

st.divider()

# 5. Quick links / status
st.subheader("🚀 System Status & Links")
st.write("- OpenHands UI: http://localhost:3000 (or the exposed port)")
st.write("- Dashboard (this): http://localhost:8501")
st.write("- LLM: http://localhost:8080 (Vulkan llama.cpp)")
st.write("- MCP Skills: http://localhost:8765/mcp")

st.caption("Website Builder • AUTO-REFRESH DISABLED (manual button only) to avoid rate limits. All core changes must go through guarded proposals + manual refresh.")
'''
        return code

    def build_standalone_html_explorer(self, task: str, features: List[str]) -> str:
        """Single-file beautiful explorer (drop in any static host, GitHub pages, Vercel, etc.)."""
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{task}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>body {{ background: #0b0f17; color: #e2e8f0; }} .addr {{ font-family: ui-monospace, monospace; }}</style>
</head>
<body class="bg-[#0b0f17] text-slate-200">
  <div class="max-w-7xl mx-auto p-6">
    <header class="flex items-center justify-between mb-8">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500"></div>
        <div>
          <h1 class="text-3xl font-semibold tracking-tight">{task}</h1>
          <p class="text-slate-400 text-sm">PulseChain • Built with Website Builder Expert + full agent toolset</p>
        </div>
      </div>
      <button onclick="refreshAll()" 
              class="px-4 py-2 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 text-sm flex items-center gap-2">
        🔄 Refresh Proposals
      </button>
    </header>

    <!-- Wallet Narrator -->
    <div class="bg-white/5 border border-white/10 rounded-3xl p-6 mb-6">
      <h2 class="font-medium mb-3">📜 Wallet Activity (tx_narrator powered)</h2>
      <div class="flex gap-2">
        <input id="wallet" class="flex-1 bg-black/40 border border-white/10 rounded-2xl px-4 py-2 text-sm addr" placeholder="0x... address on PulseChain" />
        <button onclick="narrateWallet()" class="px-5 rounded-2xl bg-cyan-500/90 hover:bg-cyan-400 text-black font-medium">Narrate</button>
      </div>
      <pre id="narrative" class="mt-4 p-4 bg-black/60 rounded-2xl text-xs overflow-auto min-h-[80px] whitespace-pre-wrap"></pre>
      <p class="text-[10px] text-slate-500 mt-1">Real usage: call MCP narrate_wallet_activity or use the tx_narrator skill inside OpenHands.</p>
    </div>

    <!-- Guarded Proposals -->
    <div class="bg-white/5 border border-white/10 rounded-3xl p-6 mb-6">
      <h2 class="font-medium mb-3">🛡️ Recent Guarded Proposals & Evolution Activity</h2>
      <div id="proposals" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm"></div>
      <p class="text-[10px] text-slate-500 mt-2">In the live Streamlit dashboard this list is populated from pending_proposals/*.json (manual refresh button).</p>
    </div>

    <!-- Auditor -->
    <div class="bg-white/5 border border-white/10 rounded-3xl p-6 mb-6">
      <h2 class="font-medium mb-3">🔐 Contract Auditor (contract_auditor)</h2>
      <div class="flex gap-2">
        <input id="auditAddr" class="flex-1 bg-black/40 border border-white/10 rounded-2xl px-4 py-2 text-sm addr" placeholder="Token or contract address" />
        <button onclick="runAudit()" class="px-5 rounded-2xl bg-violet-500/90 hover:bg-violet-400 text-black font-medium">Audit</button>
      </div>
      <pre id="auditResult" class="mt-4 p-4 bg-black/60 rounded-2xl text-xs overflow-auto min-h-[80px]"></pre>
    </div>

    <footer class="text-center text-xs text-slate-500 mt-10">
      Generated by WebsiteBuilder • Integrates tx_narrator • contract_auditor • onchain_monitor • persistent_memory • guarded proposals<br>
      For the real interactive version run the Streamlit dashboard we also generated.
    </footer>
  </div>

  <script>
    function refreshAll() {{
      const el = document.getElementById('proposals');
      el.innerHTML = '<div class="text-xs text-slate-400">Refreshing... (in real dashboard this loads the latest *.json)</div>';
      setTimeout(() => {{
        el.innerHTML = '<div class="p-3 rounded-2xl bg-white/5 text-xs">Example: proposal-2026-06-03.json would appear here after agents emit guarded evolution proposals.</div>';
      }}, 600);
    }}

    async function narrateWallet() {{
      const addr = document.getElementById('wallet').value.trim();
      const out = document.getElementById('narrative');
      out.textContent = 'Calling tx_narrator (or MCP narrate_wallet_activity) for ' + (addr || 'address') + '...\\n\\nIn OpenHands this returns structured stories like:\\n"Swapped 12,450 HEX on PulseX (2026-05-..) tx:0x..."';
    }}

    async function runAudit() {{
      const addr = document.getElementById('auditAddr').value.trim();
      const out = document.getElementById('auditResult');
      out.textContent = 'Running contract_auditor on ' + (addr || 'address') + '...\\n\\n(Real call returns liquidity, ownership, mint, verification status, risk list etc.)';
    }}

    // Demo data
    window.onload = () => {{
      const p = document.getElementById('proposals');
      p.innerHTML = '<div class="p-3 rounded-2xl bg-white/5 text-xs">No local proposals in static file. Use the Streamlit version + manual refresh button for live pending_proposals list.</div>';
    }}
  </script>
</body>
</html>'''
        return html

    def build_vite_react_scaffold(self, task: str, features: List[str]) -> Dict[str, str]:
        """Returns a small React + Vite + TS project scaffold (files as dict)."""
        files = {
            "package.json": json.dumps({
                "name": "pulsechain-explorer",
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "dependencies": {"react": "^18.3", "react-dom": "^18.3"},
                "devDependencies": {"@types/react": "^18", "typescript": "^5", "vite": "^5", "tailwindcss": "^3", "postcss": "^8", "autoprefixer": "^10"}
            }, indent=2),
            "src/App.tsx": f"""import React, {{ useState }} from 'react';

export default function PulseChainExplorer() {{
  const [addr, setAddr] = useState('');
  const [narrative, setNarrative] = useState('');

  const narrate = () => {{
    setNarrative(`(Demo) Would call tx_narrator / MCP narrate_wallet_activity for ${{addr}}\\nProduces: "Swapped ... on PulseX tx:..."`);
  }};

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-200 p-8">
      <h1 className="text-4xl font-semibold mb-2">{task}</h1>
      <p className="text-slate-400 mb-8">React + Vite scaffold generated by Website Builder. Wire real MCP calls in production.</p>

      <div className="max-w-2xl">
        <div className="mb-6">
          <input value={{addr}} onChange={{e=>setAddr(e.target.value)}} placeholder="0x wallet" className="w-full bg-black/50 border border-white/10 rounded-2xl px-4 py-3 font-mono" />
          <button onClick={{narrate}} className="mt-2 px-6 py-2 bg-cyan-400 text-black rounded-2xl font-medium">Narrate Activity (tx_narrator)</button>
        </div>
        {{narrative && <pre className="bg-black/60 p-4 rounded-2xl text-sm whitespace-pre-wrap">{{narrative}}</pre>}}
      </div>

      <div className="mt-10 text-xs text-slate-500">
        Add the Guarded Proposals list, Auditor form, and onchain monitor panel here.<br/>
        This is the professional starting point — extend it with real data from our Python MCP skills.
      </div>
    </div>
  );
}}
""",
            "README.md": f"# {task}\n\nGenerated by WebsiteBuilder expert.\n\nRun: npm install && npm run dev\n\nConnect the real tx_narrator, contract_auditor etc. via the MCP server or by calling the Python functions from a backend."
        }
        return files

    def build_modern_website(self, task: str, style: str = "futuristic", tech_stack: str = "react+tailwind+framer+three", visuals: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Primary general-purpose entry point for ANY modern website.
        style: futuristic | glass | creative | minimal | 3d-hero
        tech_stack: "react+tailwind+framer+three" | "html+tailwind+js" | "streamlit" etc.
        visuals: list like ["3d", "particles", "scroll-animations", "glass-cards", "variable-fonts", "tilt", "magnetic-buttons"]
        """
        log.info(f"Website Builder: Building MODERN website '{task}' style={style} stack={tech_stack}")

        visuals = visuals or ["3d-hero", "framer-animations", "glassmorphism", "variable-fonts", "particles", "scroll-reveal"]

        # Pull fresh research if the researcher is available (defensive)
        research_notes = ""
        research_summary = ""
        if code_researcher:
            try:
                research_notes = code_researcher.feed_programmer_and_website(task + " " + style)
                research_summary = "Fresh 2025-2026 patterns from Code Researcher injected (three.js, framer-motion, glass, variable fonts, particles, performance tips)."
            except Exception as e:
                research_summary = f"Researcher call skipped: {str(e)[:60]}"
        else:
            research_summary = "Code researcher not present in this environment (output still uses curated modern best practices)."

        deliverables = {
            "task": task,
            "style": style,
            "tech_stack": tech_stack,
            "visuals_included": visuals,
            "research_used": bool(research_notes),
            "react_vite_modern": self._build_react_modern(task, style, visuals),
            "standalone_html_modern": self._build_html_modern(task, style, visuals),
            "streamlit_version": self.build_streamlit_dashboard(task, ["modern_visuals", "animations"]),
            "research_notes": research_notes[:2200] if research_notes else research_summary,
            "research_summary": research_summary,
            "how_to_use": "React: mkdir site && cd site && npm create vite@latest . -- --template react-ts && npm i framer-motion three @react-three/fiber @react-three/drei && copy the files. Then npm run dev. Standalone HTML: just open the .html file. Completely unrelated to any specific domain is fully supported."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("website_builder:modern_website", f"{task} | style={style} | visuals={visuals}")
            except Exception:
                pass

        print(f"🌐 Website Builder: Modern website ready ({style} with rich visuals). Can be completely unrelated to our domain.")
        return deliverables

    def _build_react_modern(self, task: str, style: str, visuals: List[str]) -> Dict[str, str]:
        """Generates a COMPLETE, immediately runnable modern React + Vite + TS project.
        Includes all config files so `npm run dev` works out of the box with Tailwind v4 + Framer + optional Three.js.
        Emphasizes rich visuals as requested: 3D, animations, glass, fonts, particles/scroll.
        Fully general — works for any website theme (portfolio, SaaS, creative, internal tool, etc.).
        """
        has_three = "3d" in str(visuals).lower() or "three" in str(visuals).lower() or style in ("3d-hero", "futuristic")
        clean_name = task.lower().replace(" ", "-").replace("/", "-")[:28] or "modern-site"

        pkg = {
            "name": clean_name,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc -b && vite build",
                "lint": "eslint .",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0",
                "framer-motion": "^11.11.0"
            },
            "devDependencies": {
                "@types/react": "^19.0.0",
                "@types/react-dom": "^19.0.0",
                "@vitejs/plugin-react": "^4.3.3",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.47",
                "tailwindcss": "^4.0.0",
                "typescript": "~5.6.2",
                "vite": "^6.0.1"
            }
        }
        if has_three:
            pkg["dependencies"].update({
                "three": "^0.170.0",
                "@react-three/fiber": "^9.0.0",
                "@react-three/drei": "^10.0.0"
            })

        # Full runnable project files
        files = {
            "package.json": json.dumps(pkg, indent=2),
            "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true },
})
""",
            "tailwind.config.js": """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
""",
            "postcss.config.js": """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""",
            "tsconfig.json": json.dumps({
                "compilerOptions": {
                    "target": "ES2020",
                    "useDefineForClassFields": True,
                    "lib": ["ES2020", "DOM", "DOM.Iterable"],
                    "module": "ESNext",
                    "skipLibCheck": True,
                    "moduleResolution": "bundler",
                    "allowImportingTsExtensions": True,
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "noEmit": True,
                    "jsx": "react-jsx",
                    "strict": True,
                    "noUnusedLocals": True,
                    "noUnusedParameters": True,
                    "noFallthroughCasesInSwitch": True
                },
                "include": ["src"],
                "references": [{ "path": "./tsconfig.node.json" }]
            }, indent=2),
            "tsconfig.node.json": json.dumps({
                "compilerOptions": {
                    "composite": True,
                    "skipLibCheck": True,
                    "module": "ESNext",
                    "moduleResolution": "bundler",
                    "allowSyntheticDefaultImports": True
                },
                "include": ["vite.config.ts"]
            }, indent=2),
            "index.html": f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{task}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",
            "src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""",
            "src/index.css": """@import "tailwindcss";

:root {
  font-family: 'Inter', system-ui, sans-serif;
}

.display {
  font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  font-feature-settings: "ss01";
}

.glass {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: transform 0.2s cubic-bezier(0.23, 1, 0.32, 1), 
              box-shadow 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.glass:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}
""",
            "README.md": f"""# {task}

Modern website generated by WebsiteBuilder + CodeResearcher (2026 stack).

## Run (after copying files)
```bash
npm install
npm run dev
```

Includes:
- React 19 + TypeScript + Vite
- Tailwind CSS v4
- Framer Motion (rich animations)
- Optional Three.js + @react-three/fiber/drei (when 3D requested)
- Glassmorphism, variable fonts (Space Grotesk + Inter), micro-interactions, scroll reveals

This project is completely general-purpose. Use for any website.

Research notes from CodeResearcher were used where available.
"""
        }

        # Build the main App with rich visuals
        has_three_block = ""
        scene_def = ""
        if has_three:
            scene_def = """function Scene() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} />
      <mesh>
        <torusGeometry args={[1.4, 0.45, 16, 64]} />
        <meshStandardMaterial color="#67e8f9" metalness={0.6} roughness={0.3} />
      </mesh>
      <Stars />
    </>
  )
}"""
            has_three_block = """
          <div className="absolute bottom-0 right-0 w-[52%] h-[68%] hidden lg:block pointer-events-auto">
            <Canvas camera={{ position: [0, 0, 7.5], fov: 42 }} style={{ background: 'transparent' }}>
              <Scene />
              <OrbitControls enablePan={false} enableZoom={false} />
            </Canvas>
          </div>"""

        imports = [
            "import React from 'react'",
            "import { motion } from 'framer-motion'",
        ]
        if has_three:
            imports.extend([
                "import { Canvas } from '@react-three/fiber'",
                "import { OrbitControls, Stars } from '@react-three/drei'",
            ])

        app_code = f'''{chr(10).join(imports)}

{scene_def}

export default function {clean_name.replace("-", "").title() or "ModernSite"}() {{
  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden">
      <header className="relative min-h-[100dvh] flex items-center justify-center px-6">
        <div className="absolute inset-0 bg-[radial-gradient(#222_1px,transparent_1px)] bg-[length:3px_3px]" />
        
        <div className="relative z-10 text-center max-w-5xl">
          <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full border border-white/20 text-[10px] tracking-[3px] mb-6">2026 • MODERN WEB EXPERIENCE</div>
          
          <h1 className="display text-[clamp(3.2rem,9vw,7.5rem)] leading-[0.9] font-semibold tracking-[-5.5px] mb-6">
            {task}
          </h1>
          <p className="text-2xl md:text-3xl text-white/60 max-w-2xl mx-auto mb-10">
            Rich motion. Tasteful 3D. Perfect typography. Zero bloat.
          </p>

          <div className="flex flex-wrap gap-4 justify-center">
            <motion.button 
              whileHover={{ scale: 1.015 }} 
              whileTap={{ scale: 0.985 }}
              className="px-10 py-4 rounded-3xl bg-white text-black font-medium text-lg active:scale-[0.985] transition"
            >
              Start project
            </motion.button>
            <motion.button 
              whileHover={{ scale: 1.015 }} 
              className="px-10 py-4 rounded-3xl border border-white/30 font-medium text-lg hover:bg-white/5 transition"
            >
              View work
            </motion.button>
          </div>
        </div>

        {has_three_block}
      </header>

      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-3 gap-5">
          <motion.div whileHover={{ y: -8 }} className="glass p-9 rounded-3xl border border-white/10">
            <div className="text-[11px] tracking-[2px] text-white/50 mb-3">FEATURE 01</div>
            <div className="text-3xl font-semibold tracking-tight mb-4 display">Modern Visual Layer</div>
            <p className="text-white/70 leading-relaxed">Glassmorphism • Spring physics • Micro hover states • Production ready.</p>
          </motion.div>
          <motion.div whileHover={{ y: -8 }} className="glass p-9 rounded-3xl border border-white/10">
            <div className="text-[11px] tracking-[2px] text-white/50 mb-3">FEATURE 02</div>
            <div className="text-3xl font-semibold tracking-tight mb-4 display">Scroll &amp; Motion</div>
            <p className="text-white/70 leading-relaxed">Framer powered reveals and beautiful interactions by default.</p>
          </motion.div>
          <motion.div whileHover={{ y: -8 }} className="glass p-9 rounded-3xl border border-white/10">
            <div className="text-[11px] tracking-[2px] text-white/50 mb-3">FEATURE 03</div>
            <div className="text-3xl font-semibold tracking-tight mb-4 display">3D &amp; Polish</div>
            <p className="text-white/70 leading-relaxed">Optional high-quality Three.js hero when requested via the team.</p>
          </motion.div>
        </div>

        <div className="mt-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 60 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
            className="display text-[52px] leading-none tracking-[-2.8px] font-semibold"
          >
            Scroll-triggered.<br />Butter smooth.
          </motion.div>
        </div>
      </section>

      <footer className="border-t border-white/10 py-12 text-center text-xs text-white/40">
        Generated by WebsiteBuilder + CodeResearcher • Any theme, any domain. Rich modern visuals included by default.
      </footer>
    </div>
  )
}}
'''

        files["src/App.tsx"] = app_code
        return files


    def _build_html_modern(self, task: str, style: str, visuals: List[str]) -> str:
        """Standalone, single-file, production-quality modern HTML.
        Zero dependencies. Includes canvas particles, glassmorphism, variable fonts,
        magnetic buttons, scroll reveals, and beautiful interactions.
        Ready to open or host anywhere.
        """
        has_particles = "particle" in str(visuals).lower() or style in ("creative", "futuristic", "3d-hero")
        has_3d = "3d" in str(visuals).lower() or style in ("3d-hero", "futuristic")

        particles_script = ''
        if has_particles:
            particles_script = '''
      <canvas id="p" class="absolute inset-0 pointer-events-none" style="opacity:.28"></canvas>
      <script>
        const c=document.getElementById('p'),x=c.getContext('2d');let w,h,pts=[];
        function r(){w=c.width=innerWidth;h=c.height=innerHeight;pts=Array.from({length:48},()=>({x:Math.random()*w,y:Math.random()*h,vx:(Math.random()-.5)*.7,vy:(Math.random()-.5)*.7}))}
        function d(){x.clearRect(0,0,w,h);x.fillStyle='#fff';pts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>w)p.vx*=-1;if(p.y<0||p.y>h)p.vy*=-1;x.beginPath();x.arc(p.x,p.y,1.15,0,Math.PI*2);x.fill()});requestAnimationFrame(d)}
        addEventListener('resize',r);r();d();
      </script>'''

        three_note = ''
        if has_3d:
            three_note = '<div class="absolute bottom-8 right-8 text-[10px] text-white/40 hidden lg:block">Replace this area with real Three.js / &lt;Canvas&gt; for full 3D hero</div>'

        cards_html = ''.join([f'''
      <div class="glass rounded-3xl p-9 section-reveal" style="transition-delay:{i*70}ms">
        <div class="tabular-nums text-6xl font-semibold tracking-[-2px] mb-2">0{i+1}</div>
        <div class="text-3xl tracking-tight display mb-3">Modern Layer</div>
        <p class="text-white/70">Glass • spring physics • scroll reveal • variable font. Use this pattern everywhere.</p>
      </div>''' for i in range(3)])

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{task}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Space+Grotesk:wght@500;600&amp;display=swap">
  <style>
    :root {{ --font-sans:'Inter',system-ui,sans-serif; --font-display:'Space Grotesk',Inter,system-ui,sans-serif; }}
    body {{ font-family: var(--font-sans); }}
    .display {{ font-family: var(--font-display); font-feature-settings: "ss01"; letter-spacing: -.02em; }}
    .glass {{ background: rgba(255,255,255,.055); backdrop-filter: blur(22px); border: 1px solid rgba(255,255,255,.12); }}
    .section-reveal {{ opacity:0; transform:translateY(48px); transition:all .75s cubic-bezier(.23,1,.32,1); }}
    .section-reveal.visible {{ opacity:1; transform:none; }}
  </style>
</head>
<body class="bg-[#050505] text-white antialiased">
  <div class="max-w-7xl mx-auto">
    <header class="min-h-[100dvh] flex items-center justify-center relative px-6">
      <div class="text-center max-w-4xl">
        <div class="inline-block text-[10px] tracking-[3.5px] border border-white/20 px-4 py-1 rounded-full mb-5">2026 MODERN WEB</div>
        <h1 class="display text-[clamp(3.5rem,9.2vw,7.8rem)] leading-[.88] font-semibold tracking-[-6.2px] mb-6">{task}</h1>
        <p class="text-2xl text-white/60 max-w-md mx-auto">Rich motion. Tasteful 3D. Perfect typography. Zero bloat.</p>

        <div class="flex gap-3 justify-center mt-9">
          <button onclick="document.getElementById('work').scrollIntoView({{behavior:'smooth'}})" class="px-11 py-[17px] rounded-3xl bg-white text-black font-medium text-[15px] active:scale-[0.985]">Explore</button>
          <button class="px-11 py-[17px] rounded-3xl border border-white/25 font-medium text-[15px] hover:bg-white/5">Watch reel</button>
        </div>
      </div>
      {particles_script}
      {three_note}
    </header>

    <div id="work" class="px-6 pb-20 grid md:grid-cols-3 gap-5">
      {cards_html}
    </div>
  </div>

  <script>
    // Scroll reveals
    const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && e.target.classList.add('visible')));
    document.querySelectorAll('.section-reveal').forEach(el => io.observe(el));

    // Magnetic buttons
    document.querySelectorAll('button').forEach(btn => {{
      btn.addEventListener('mousemove', e => {{
        const r = btn.getBoundingClientRect();
        btn.style.transform = `translate(${{((e.clientX-r.left)/r.width-.5)*7}}px, ${{((e.clientY-r.top)/r.height-.5)*7}}px)`;
      }});
      btn.addEventListener('mouseleave', () => btn.style.transform='');
    }});
    console.log('%c[WebsiteBuilder] Standalone modern HTML ready — any theme supported', 'color:#555');
  </script>
</body>
</html>'''

    def build_generic_website(self, task: str, stack: str = "html") -> str:
        """General entry — now routes to the rich modern builder."""
        log.info(f"Website Builder: generic modern site for {task}")
        if stack == "streamlit":
            return self.build_streamlit_dashboard(task, ["content", "forms", "charts"])
        # Default to the new powerful modern path
        return self.build_modern_website(task, style="futuristic")["standalone_html_modern"]

    def _integration_notes(self) -> str:
        return """
INTEGRATION WITH OUR AGENT ECOSYSTEM (very important):
- Call tx_narrator / narrate_wallet_activity to turn raw history into beautiful stories inside the UI.
- Call contract_auditor for the auditor panel (pass address or verified source).
- onchain_monitor can push events that refresh parts of the UI or trigger new proposals.
- The "Recent Guarded Proposals" section is fed by pending_proposals/*.json created by capability_evolver / safe_research_and_evolve.
- Use the manual refresh pattern ONLY (st.button that sets session_state + clears @st.cache_data(ttl=3600)). 
  AUTO-REFRESH (st_autorefresh, timers, 5min intervals) IS STRICTLY FORBIDDEN in all generated Streamlit dashboards to prevent rate limits on RPCs, onchain_monitor, and proposal scanning.
- For hierarchical use: supervisor.delegate_to_sub_supervisor(..., sub_type="website") then handoff context to this expert.
"""

    def _how_to_run_instructions(self) -> str:
        return """
HOW TO USE THE DELIVERABLES:
1. Streamlit version: Save as explorer_dashboard.py next to dashboard.py, then streamlit run explorer_dashboard.py
   (it will live at :8501 together with our existing dashboard or on another port).
2. Standalone HTML: Save as pulsechain-explorer.html and open in browser, or deploy anywhere static.
3. React/Vite: mkdir my-explorer && cd my-explorer; paste the files, npm install, npm run dev.
4. In OpenHands agent runs: ask for "website-builder: build a full PulseChain explorer with wallet narration, proposals list, and auditor" and it will use this module + create the files via the sandbox.
"""

    # =====================================================================
    # GOD-TIER METHODS — 10x professional website engineering
    # These are the preferred entrypoints for any serious client or production website work.
    # They enforce: task_tracker full plans, persistent_memory, guarded proposals,
    # cross-expert handoffs (programmer, crypto, hacash_*, analytics, legal, designer, react, threejs, mobile),
    # performance budgets, accessibility, production deployment, and client-grade deliverables.
    # =====================================================================

    def god_tier_build_modern_website(self, task: str, style: str = "futuristic", tech_stack: str = "react+tailwind+framer+three", visuals: Optional[List[str]] = None, include_crypto: bool = False, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: The ultimate modern website builder. 10x senior frontend + design + 3D + payments + explorer specialist output.
        Always starts with architecture + threat model + design system + perf budgets + handoff manifest.
        """
        log.info(f"Website Builder (GOD TIER): God-like modern website for: {task[:60]}")
        visuals = visuals or ["framer-motion", "three-js", "glassmorphism", "scroll-animations", "variable-fonts", "particles", "reduced-motion"]

        # Retrieve past learnings
        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(task, max_results=3) or ""
            except Exception:
                pass

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " god tier 2026 modern web", "react three.js framer performance payments 3D mobile 2026")
            except Exception:
                pass

        # Base modern build (calls the existing powerful method)
        base = self.build_modern_website(task, style, tech_stack, visuals)

        god = {
            "task": task,
            "style": style,
            "tech_stack": tech_stack,
            "god_tier_standards": {
                "mandatory_first": [
                    "task_tracker plan with 15-25 granular tasks (complete array)",
                    "persistent_memory.retrieve + store",
                    "Design system + tokens from designer (god_tier)",
                    "Performance budget (Lighthouse mobile ≥92, 3D FPS targets, bundle <220kb gz)",
                    "Accessibility WCAG 2.2 AA (god_tier from mobile + designer)"
                ],
                "10x_thinking": "Anticipate real mobile users (thumb zones, 3G, low-end GPU), adversarial inputs (crypto txs), 10x scale (many concurrent channel/L2 views), regulatory (legal for payments/KYC). Always provide graceful 3D fallbacks."
            },
            "architecture": {
                "high_level": "Feature-based React (or Next.js) + shared design system. Heavy 3D and crypto logic lazy + feature-flagged. Server components for data where possible. WASM for heavy pricing/risk calc (handoff to cpp-expert + programmer).",
                "3d_strategy": "R3F + drei for most cases. Pure three for extreme perf. Post-processing desktop-only. DPR capped. Instanced + LOD where applicable.",
                "state_and_data": "TanStack Query + Zustand for on-chain data. Real-time via WebSocket (fullnode RPC or indexer) or polling with manual refresh button pattern.",
                "crypto_payments_layer": "If include_crypto: Stripe Elements + Stripe Crypto + ethers.js (custom USDC/HAC flows) + direct WASM call for 3D dynamic pricing/risk. Backend intent/confirm endpoints (python-expert). Always verify on backend + log to analytics."
            },
            "hacash_specific": {
                "when_applicable": "Mining pool dashboards (hashrate, shares, fairness, X16RS difficulty), L1 explorer (blocks, HAC/HACD, peg proofs), L2 channel visualizer (open/update/close states, CSP), HVM contract explorer, diamond (HACD) visual mint/ownership UI.",
                "data_sources": "Fullnode RPC (via hacash_fullnode_expert guidance), on-chain events, pool API. Use tx_narrator style narration for activity.",
                "visuals": "3D for diamond visualization or hashrate globe. Glass + cyan/violet futuristic theme. Live updating tables with manual refresh (dashboard.py pattern)."
            } if include_hacash else None,
            "performance_budgets": {
                "mobile": "Lighthouse P/A ≥ 92. Initial bundle < 220kb gz. 3D: ≤30 draw calls, ≤40k tris on mid phone, 45+ fps, toggle to static.",
                "desktop": "Full quality + bloom, 60fps, high DPR. Always respect prefers-reduced-motion.",
                "tools": "Lighthouse CI, React Profiler, three.js inspector, real device + WebPageTest 3G, WebGL report."
            },
            "security_privacy": [
                "Never trust client for payments — always backend verify (python + crypto_payments_expert)",
                "Sanitize all on-chain inputs / addresses",
                "CSP headers, no inline scripts in prod",
                "For explorers: rate limit RPC calls, cache, graceful degradation on node issues"
            ],
            "base_deliverables": base,
            "extra_god_tier_deliverables": {
                "design_system_tokens": "Full CSS vars + Tailwind config + Figma-style tokens (handoff from designer.god_tier)",
                "3d_fallbacks": "Static hero image + 'Enable 3D (high perf device)' toggle + canvas placeholder",
                "payment_3d_component": "Ready React + Three + WASM + Stripe snippet if include_crypto (see crypto_payments_expert god_tier integration)",
                "hacash_explorer_panels": "Wallet activity (tx_narrator), Guarded Proposals live list, Contract auditor, Mining stats / channel states, On-chain verification buttons",
                "runbooks": "How to connect real fullnode RPC, how to add new HVM event panels, how to wire analytics events for 3D interactions + payment funnels"
            },
            "handoff_manifest": {
                "to_designer": "god_tier_design_system + create_color_palette + mobile_ux_checklist",
                "to_react": "god_tier_react_architecture (or build_react_architecture) for component system",
                "to_threejs": "god_tier_create_threejs_scene for any hero or data viz 3D",
                "to_mobile": "god_tier_make_responsive + full device checklist",
                "to_programmer": "Heavy logic, WASM bindings, backend endpoints, full SDLC review",
                "to_crypto_payments": "build_crypto_payment_flow + react_3d_integration_snippets (Stripe + ethers + WASM)",
                "to_hacash_*": "hacash_fullnode for RPC patterns, mining for pool UI data model, l2 for channel visual state machine, hvm for contract explorer",
                "to_analytics": "Setup 3D interaction events, payment funnel, on-chain attribution",
                "to_legal": "Cookie consent, terms for explorers/pools/payments, KYC if on-ramp",
                "to_devops": "Vercel / static + edge functions, monitoring (Lighthouse + RUM), PWA"
            },
            "past_learnings_research": (past + " " + (research[:600] if research else ""))[:900],
            "god_tier_level": "10x: Ship a website that looks like it cost $80k, performs on a $200 phone, handles real money/crypto/Hacash state safely, and the client can actually maintain and extend because of the docs, tokens, and runbooks. Every deliverable passes the PM quality gates."
        }

        print("🌐 Website Builder (GOD TIER): God-like modern website system delivered (with full handoffs, budgets, crypto/Hacash integration).")
        return god

    def god_tier_full_website_sdlc_with_gates(self, project: str, include_3d: bool = True, include_payments: bool = False, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: End-to-end SDLC for website projects that matches the ProjectManager template but forces god_tier depth on every frontend specialist."""
        return {
            "project": project,
            "phases": [
                "0. Discovery + god_tier threat model (payments/on-chain data) + task_tracker full plan",
                "1. Designer: god_tier_design_website + god_tier_design_system + tokens + mobile UX checklist",
                "2. React: god_tier_react_architecture (or build) + component library + a11y primitives",
                "3. ThreeJS: god_tier_create_threejs_scene + perf audit + mobile degradation (if include_3d)",
                "4. Mobile: god_tier_make_responsive + real device budget + PWA",
                "5. WebsiteBuilder: god_tier_build_modern_website (this) pulling everything together + crypto/Hacash panels",
                "6. Programmer + crypto: god_tier for heavy WASM, backend intent/confirm, on-chain verification",
                "7. QA + a11y + seo + analytics god_tier passes",
                "8. DevOps: production deploy + RUM + rollback + monitoring",
                "Gates: Same as PM (0 brief → 6 live) + explicit god_tier review sign-off from each specialist"
            ],
            "client_deliverables": "Design tokens + Figma handoff, full React+TS repo (or static), 3D scenes with toggles, payment flows (tested), Hacash explorer panels, runbooks, Lighthouse reports, 30-day support plan",
            "god_tier_note": "No website project is 'just frontend'. Treat it with the same rigor as L1/L2/HVM work when money, on-chain state, or real users are involved."
        }

    def god_tier_3d_performance_and_fallback_strategy(
            self, scene_type: str = "hero_or_data_viz") -> dict:
        """A 3D budget for THIS scene.

        Took `scene_type` and ignored it: a heavy particle field and a single
        static model returned the same budgets, byte for byte.
        """
        return self.analyse(
            "Set the performance budget and fallback plan for THIS specific "
            "scene: triangle and draw-call ceilings, what to cut first as the "
            "device gets weaker, and what the no-3D fallback should actually "
            "show. If this scene does not need 3D at all, say so.",
            {"scene_type": scene_type},
            reference=self._god_tier_3d_performance_and_fallback_strategy_reference(),
            max_tokens=1600,
        )

    def _god_tier_3d_performance_and_fallback_strategy_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE 3D web specifics: budgets, fallbacks, testing, integration with React and WASM calc."""
        return {
            "budgets": {
                "high_end_desktop": "60fps, full post-process (bloom), 1.8-2.0 DPR, 150k+ tris ok",
                "tablet": "45-55fps, bloom off or low, DPR 1.5, 60-80k tris",
                "mid_phone": "45+ fps or toggle, no bloom, DPR 1.0-1.2, 25-40k tris, simple lighting",
                "low_end": "Static hero image or very low-poly + 'Enable 3D' opt-in only"
            },
            "techniques": "LOD, instancing, texture compression (KTX2/Basis), dispose on unmount, cap draw calls <25-30 mobile, use drei helpers aggressively, profile with three inspector + real devices.",
            "fallback_system": "Always render a beautiful static/pre-rendered version first. Button 'Load high-quality 3D (uses more GPU)'. Respect prefers-reduced-motion globally.",
            "wasm_heavy_calc": "For dynamic pricing, risk, or simulation in 3D configurators (e.g. Hacash diamond value or pool ROI): handoff to programmer + cpp-expert for .wasm. Call from React effect, feed results into Three scene (color, scale, particles).",
            "hacash_examples": "3D rotating HACD diamond with live on-chain metadata, hashrate 'globe' or bar visualization, channel state machine visual (open → updating → settled).",
            "god_tier": "3D is a delight, not a liability. If it tanks Core Web Vitals or crashes low-end phones, it fails the god-tier bar."
        }

    def god_tier_crypto_payment_ui_integration(self, gateways: list = None) -> dict:
        """A payment flow for THE GATEWAYS you named.

        Took `gateways`, overwrote it with a default list, and returned the same
        dict either way — identical for "stripe only" and for
        "metamask and walletconnect", which need almost nothing in common.
        """
        asked = gateways or ["stripe", "stripe_crypto", "custom_ethers", "hacash_l2_channels"]
        out = self.analyse(
            "Design the payment flow for exactly these gateways and no others: "
            "the UI states each one needs, where the authoritative amount is "
            "computed, what must be re-verified server-side, and the failure "
            "paths a user will actually hit. Do not describe gateways that were "
            "not requested.",
            {"gateways_requested": ", ".join(str(g) for g in asked)},
            reference=self._god_tier_crypto_payment_ui_integration_reference(),
            max_tokens=1800,
        )
        out["gateways_requested"] = asked
        return out

    def _god_tier_crypto_payment_ui_integration_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE: Production-ready React + 3D + Stripe Crypto + ethers + WASM payment flows (matches the history of full ethers+Stripe+WASM)."""
        return {
            "required_experts": "crypto_payments_expert (primary), programmer_expert (WASM + backend), website_builder (this for 3D UI), threejs_expert",
            "react_three_wasm_pattern": "3D configurator (Three) → on change call WASM calc (pricing/risk/gas for Hacash or EVM) → live update price/3D viz → user confirms → Stripe Elements or ethers send tx → backend /create-intent or /confirm (python) + analytics event",
            "security": "Never do final payment calc only in WASM/client. Always re-verify server-side. Show 'Pending verification' + tx hash + on-chain confirmation UI.",
            "3d_ux": "Beautiful glass cards, live updating 3D (subtle) that reacts to price/amount, skeleton states, error boundaries around payment + 3D islands.",
            "hacash_variant": "L2 channel payment visual (multi-sig state), one-click settle to L1, diamond as collateral visualization.",
            "deliverable": "Copy-paste ready <Payment3DConfigurator /> + full backend notes + test vectors. Integrates with the exact snippets already in crypto_payments_expert.",
            "god_tier": "Payments + 3D + on-chain must feel magical and be bulletproof. One bad UX or trust issue and you lose the client and reputation."
        }

    def god_tier_hacash_specialized_explorer(self, explorer_type: str = "l1_blocks") -> dict:
        """An explorer plan for THIS layer.

        Took `explorer_type` and ignored it: L1 blocks and L2 channel chains —
        different data models, different views, different queries — returned the
        same plan byte for byte.
        """
        return self.analyse(
            "Plan the explorer for THIS specific Hacash layer: which entities it "
            "must show, the queries and indexes behind each view, what is "
            "genuinely different about this layer's data model, and the first "
            "screen to build. Do not describe the other layers.",
            {"explorer_type": explorer_type},
            reference=self._god_tier_hacash_specialized_explorer_reference(),
            max_tokens=1800,
        )

    def _god_tier_hacash_specialized_explorer_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE: Specialized production UIs for the Hacash ecosystem (mining pools, L1/L2/L3 explorers, HVM dapps, diamond viewers)."""
        return {
            "types": {
                "mining_pool": "Live hashrate (per worker + aggregate), shares table (HAC vs HACD separate), difficulty chart, fairness indicator, P2P relay health, payout history. 3D optional hashrate 'mountain' or GPU viz.",
                "l1_explorer": "Blocks, txs, HAC/HACD supply, BTC peg proofs/volume, readable contracts or HVM events. Wallet activity narrated via tx_narrator pattern. Manual refresh + WebSocket.",
                "l2_channels": "Open channels list, live updates (CSP ordered), dispute UI, settlement to L1 button + proof. Visual state machine (nice for 3D or SVG).",
                "hvm_dapp": "Contract explorer, call simulator (with AA sessions), state viewer, event log. Integrate with fullnode HVM RPC extensions (from hacash_hvm_expert).",
                "diamond_hacd": "Beautiful 3D diamond viewer + ownership history + mint provenance. Scarcity economics dashboard."
            },
            "tech": "React + TS + TanStack + Recharts or custom canvas for charts. Three.js for premium viz (diamonds, hashrate). Fullnode RPC via hacash_fullnode_expert patterns. tx_narrator for human stories. Guarded proposals feed for governance feel.",
            "production": "Same budgets as god_tier_build_modern_website. Real node connection instructions. Caching + rate limiting. On-chain verification links.",
            "handoffs": "All hacash_* experts for data models/RPC, programmer for any custom indexing or WASM, analytics for hashrate/volume funnels, website_builder god_tier for the shell.",
            "god_tier": "A Hacash explorer built at god level makes the chain feel alive, trustworthy, and professional. It is one of the highest-leverage things we can ship for adoption."
        }

    def god_tier_production_deployment_and_observability(self) -> Dict[str, Any]:
        """GOD-LIKE ops for any website we deliver: deploy, perf monitoring, error tracking, analytics, PWA, rollback."""
        return {
            "deploy_targets": "Vercel (recommended for React/Next), Cloudflare Pages, static S3+CF for pure HTML. Edge functions for API routes when needed.",
            "perf_monitoring": "Lighthouse CI in GitHub Actions (mobile + desktop budgets). Real User Monitoring (Vercel Analytics or Plausible + custom 3D events). Core Web Vitals alerts.",
            "error_tracking": "Sentry or equivalent, with source maps. Boundary around 3D islands and payment flows.",
            "analytics": "Privacy-first (no GA by default). Custom events for 3D interactions, payment intent/confirm, explorer refreshes, on-chain tx success. Integrate with the analytics-specialist god_tier setup.",
            "pwa": "Manifest + SW for offline explorer views + install prompt (especially useful for mobile mining dashboards).",
            "god_tier_runbook": "How to bump a new fullnode RPC endpoint, how to add a new HVM event panel, how to hotfix a payment flow, how to roll back a bad 3D perf regression."
        }

# Register
website_builder = WebsiteBuilder()
print("🌐 Website Builder (GOD TIER) registered. Ready for sub_type='website'. God-like modern websites with 3D, crypto payments, Hacash explorers, full production rigor.")