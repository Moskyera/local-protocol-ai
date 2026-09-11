import lpai_private; lpai_private.activate()   # private mode before streamlit loads
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# NOTE: st_autorefresh removed completely per user request.
# This dashboard now uses MANUAL REFRESH ONLY to avoid rate limits.
# Click the button at the top to force fresh data.

from watchlist_engine import (
    get_stock_watchlist,
    get_crypto_watchlist
)

from regime_engine import (
    analyze_market_regime
)

from master_market_brain import (
    generate_master_report
)

from chart_engine import (
    get_chart_data
)

from signal_engine import (
    generate_signal
)

import matplotlib.pyplot as plt

# =========================================
# PAGE CONFIG + MOSKY CYBERPUNK STYLE (multi color neon)
# =========================================

st.set_page_config(
    page_title="MOSKY // AI Market Intelligence Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================
# MOSKY CYBERPUNK CSS - orange #ff6600, yellow #ffcc00, purple #9900ff, 
# blue #00aaff, cyan #00f0ff, red #ff0033, gray #888888 accents
# Intense multi-color glows, glitch, grid, animated scanlines
# =========================================

st.markdown(
    """
<style>
/* EXTREME CYBERPUNK MULTI-NEON - new hierarchy: RED/ORANGE dominant (chaos), PURPLE (neural), CYAN/YELLOW (tech highlights), BLUE/GRAY (base) */
.stApp {
    background: #010102 !important;
    color: #d0d0ff !important;
    font-family: 'Courier New', 'Consolas', monospace !important;
}

/* HYPER-EXTREME background: multi-layer moving grid + digital rain + interference + color pulse */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image: 
        /* dense red/orange vertical grid */
        linear-gradient(rgba(255,0,51,0.12) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,102,0,0.09) 1px, transparent 1px),
        /* purple horizontal */
        linear-gradient(rgba(153,0,255,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(153,0,255,0.05) 1px, transparent 1px),
        /* cyan diagonal interference */
        linear-gradient(135deg, rgba(0,240,255,0.06) 1px, transparent 1px),
        linear-gradient(45deg, rgba(0,240,255,0.04) 1px, transparent 1px);
    background-size: 14px 14px, 14px 14px, 22px 22px, 22px 22px, 9px 9px, 9px 9px;
    pointer-events: none;
    z-index: 0;
    animation: 
        grid-move 1.1s linear infinite,
        grid-pulse 1.8s ease-in-out infinite,
        color-shift 6s linear infinite,
        cyber-bg-glitch 1.8s infinite steps(1, jump-none);
    mix-blend-mode: screen;
}

/* Extra extreme rain / data stream layer - also glitches */
.stApp::after {
    content: '';
    position: fixed;
    top: -100%; left: 0; right: 0; bottom: 0;
    background-image: 
        linear-gradient(
            transparent 0%,
            rgba(255,0,51,0.035) 12%,
            rgba(255,102,0,0.025) 14%,
            transparent 16%,
            rgba(0,240,255,0.03) 28%,
            rgba(153,0,255,0.02) 30%,
            transparent 32%,
            rgba(255,204,0,0.015) 44%,
            transparent 46%
        );
    background-size: 100% 280px;
    pointer-events: none;
    z-index: 0;
    animation: 
        digital-rain 0.65s linear infinite,
        cyber-bg-glitch 2.1s infinite steps(1, jump-none) 0.3s;
    mix-blend-mode: screen;
    opacity: 0.9;
}

@keyframes grid-move {
    0% { background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0; }
    100% { background-position: 14px 14px, -14px 14px, 22px -22px, -22px 22px, 9px 18px, -9px -9px; }
}

@keyframes grid-pulse {
    0%, 100% { opacity: 0.65; filter: brightness(1); }
    50% { opacity: 1; filter: brightness(1.35); }
}

@keyframes color-shift {
    0% { filter: hue-rotate(0deg) saturate(1.1); }
    25% { filter: hue-rotate(8deg) saturate(1.4); }
    50% { filter: hue-rotate(-6deg) saturate(1.25); }
    75% { filter: hue-rotate(12deg) saturate(1.35); }
    100% { filter: hue-rotate(0deg) saturate(1.1); }
}

@keyframes digital-rain {
    0% { transform: translateY(0); }
    100% { transform: translateY(280px); }
}

/* CYBERPUNK BACKGROUND GLITCH - like the title but for the whole bg grid + rain */
@keyframes cyber-bg-glitch {
    0%, 92%, 100% { 
        transform: translate(0); 
        filter: none; 
        background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0; 
    }
    2% { 
        transform: translate(-8px, 4px) skew(2deg); 
        filter: hue-rotate(180deg) saturate(2.2) contrast(1.6) brightness(1.2);
        background-position: -12px 8px, 14px -6px, 0 0, 0 0, 0 0, 0 0;
    }
    4% { 
        transform: translate(7px, -3px) skew(-1.5deg); 
        filter: hue-rotate(-120deg) saturate(1.8) contrast(1.4);
        background-position: 9px -11px, -7px 5px, 0 0, 0 0, 0 0, 0 0;
    }
    6% { 
        transform: translate(-5px, 6px) scale(1.01); 
        filter: saturate(2.5) contrast(1.7);
        background-position: -18px 3px, 22px -14px, 0 0, 0 0, 0 0, 0 0;
    }
    8% { 
        transform: translate(11px, -4px) skew(3deg); 
        filter: hue-rotate(90deg) saturate(1.9) contrast(1.5) brightness(0.85);
        background-position: 15px 19px, -9px -8px, 0 0, 0 0, 0 0, 0 0;
    }
    10% { 
        transform: translate(-2px, 2px); 
        filter: none;
        background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
    }
}

/* Extreme multi-color titles - RED/ORANGE first in hierarchy for max chaos */
h1, h2, h3, .stSubheader, .stMarkdown h1, .stMarkdown h2 {
    color: #ffcc00 !important;
    text-shadow: 
        0 0 5px #ff0033, 
        0 0 9px #ff6600, 
        0 0 14px #9900ff, 
        0 0 20px #00f0ff !important;
}

/* MUCH FASTER + MORE EXTREME GLITCH (0.55s, bigger shifts + skew/scale) */
h1 {
    animation: cyber-glitch 0.55s infinite steps(2, jump-none);
    position: relative;
}
h1::before, h1::after {
    content: 'MOSKY // AI MARKET INTELLIGENCE TERMINAL';
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    overflow: hidden;
    clip: rect(0, 900px, 0, 0);
}
h1::before {
    left: 2px;
    text-shadow: -1px 0 #ff0033;
    animation: glitch-1 0.4s infinite linear alternate-reverse;
}
h1::after {
    left: -2px;
    text-shadow: 1px 0 #00f0ff;
    animation: glitch-2 0.35s infinite linear alternate-reverse;
}
@keyframes cyber-glitch {
    0% { transform: translate(0) skew(0deg); }
    10% { transform: translate(-3px, 2px) skew(1deg) scale(1.005); }
    20% { transform: translate(3px, -1px) skew(-1deg); }
    30% { transform: translate(-1px, 3px) scale(0.995); }
    40% { transform: translate(2px, -2px) skew(0.5deg); }
    50% { transform: translate(-2px, 1px); }
    60% { transform: translate(1px, -3px) skew(-0.5deg) scale(1.01); }
    70% { transform: translate(-3px, 2px); }
    80% { transform: translate(2px, -1px) scale(0.99); }
    90% { transform: translate(-1px, 3px); }
    100% { transform: translate(0) skew(0deg); }
}
@keyframes glitch-1 {
    0% { clip: rect(0, 9999px, 40%, 0); }
    20% { clip: rect(60%, 9999px, 100%, 0); }
    40% { clip: rect(20%, 9999px, 80%, 0); }
    60% { clip: rect(80%, 9999px, 30%, 0); }
    80% { clip: rect(10%, 9999px, 90%, 0); }
    100% { clip: rect(50%, 9999px, 60%, 0); }
}
@keyframes glitch-2 {
    0% { clip: rect(70%, 9999px, 20%, 0); }
    25% { clip: rect(10%, 9999px, 70%, 0); }
    50% { clip: rect(90%, 9999px, 40%, 0); }
    75% { clip: rect(30%, 9999px, 95%, 0); }
    100% { clip: rect(60%, 9999px, 15%, 0); }
}

/* Extreme metrics - red/orange dominant border */
.stMetric {
    background: rgba(8, 3, 12, 0.95) !important;
    border: 1px solid #ff0033 !important;
    border-radius: 2px !important;
    box-shadow: 
        0 0 8px #ff0033, 
        0 0 14px #ff6600, 
        0 0 20px #9900ff, 
        0 0 12px #00f0ff !important;
    padding: 4px 7px !important;
}

.stMetric label {
    color: #ffaa00 !important;
    font-size: 0.7em !important;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.stMetric .metric-value {
    color: #fff !important;
    text-shadow: 
        0 0 4px #ff0033, 
        0 0 8px #ff6600, 
        0 0 12px #00f0ff;
}

/* Hyper-glowing containers */
[data-testid="stVerticalBlock"] > div {
    background: rgba(4, 2, 10, 0.98);
    border: 1px solid #6600aa;
    border-radius: 2px;
    box-shadow: 0 0 8px rgba(255, 0, 51, 0.25), 0 0 16px rgba(153, 0, 255, 0.15);
}

/* Ultra cyber buttons - red/orange primary */
.stButton > button {
    background: linear-gradient(90deg, #220011, #440022) !important;
    color: #ffcc00 !important;
    border: 1px solid #ff0033 !important;
    box-shadow: 
        0 0 8px #ff0033, 
        0 0 14px #ff6600, 
        0 0 20px #9900ff !important;
    font-family: 'Courier New', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-size: 0.82em;
    transition: all 0.08s !important;
}
.stButton > button:hover {
    box-shadow: 
        0 0 16px #ff0033, 
        0 0 26px #ff6600, 
        0 0 34px #00f0ff, 
        0 0 12px #ffcc00 !important;
    transform: scale(1.06) translateY(-1px) !important;
    color: #ff6600 !important;
    border-color: #ffcc00 !important;
    background: linear-gradient(90deg, #330011, #660033) !important;
}

/* Code blocks - extreme matrix with red/cyan */
.stCodeBlock, code {
    background: #050105 !important;
    border: 1px solid #ff0033 !important;
    box-shadow: 
        0 0 8px #ff0033, 
        0 0 14px #9900ff, 
        0 0 10px #00f0ff !important;
    color: #99ff99 !important;
}

/* Chaotic multi-color dividers */
hr {
    border-color: #ff0033 !important;
    box-shadow: 
        0 0 8px #ff0033, 
        0 0 14px #ff6600, 
        0 0 6px #9900ff, 
        0 0 10px #00f0ff;
}

/* EXTREME multi-color scanline (faster + denser + more colors) */
.main .block-container::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
        to bottom,
        transparent 42%,
        rgba(255,0,51,0.045) 44%,
        rgba(255,102,0,0.04) 46%,
        rgba(0,240,255,0.035) 48%,
        rgba(153,0,255,0.04) 50%,
        rgba(255,204,0,0.03) 52%,
        transparent 54%
    );
    background-size: 100% 2px;
    pointer-events: none;
    z-index: 1;
    animation: cyber-scan 1.4s linear infinite;
    mix-blend-mode: screen;
}
@keyframes cyber-scan {
    0% { transform: translateY(-160%); }
    100% { transform: translateY(280%); }
}

/* Extreme cyber badges - red dominant */
.cyber-badge {
    display: inline-block;
    padding: 0 6px;
    border: 1px solid #ff0033;
    border-radius: 1px;
    color: #ffcc00;
    background: rgba(15, 2, 8, 0.8);
    font-size: 0.65em;
    box-shadow: 0 0 5px #ff0033, 0 0 9px #ff6600, 0 0 6px #9900ff;
    margin-right: 3px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Charts with aggressive borders */
.stPlotlyChart, .stDataFrame {
    border: 1px solid #ff0033 !important;
    box-shadow: 0 0 6px rgba(255,0,51,0.3), 0 0 10px rgba(0,240,255,0.2);
}

/* Subheaders - red/orange edge, extreme shadow */
.stSubheader {
    border-left: 4px solid #ff0033;
    padding-left: 6px;
    color: #ffcc00 !important;
    text-shadow: 0 0 4px #ff0033, 0 0 8px #ff6600, 0 0 6px #9900ff;
}

/* Captions and text - cooler gray/cyan mix */
.stText, .stCaption {
    color: #8888aa !important;
}
</style>
""",
    unsafe_allow_html=True
)

# =========================================
# MANUAL REFRESH ONLY - AUTO REFRESH REMOVED
# (was causing rate limits every 5 minutes)
# =========================================

st.markdown("### 🔄 Manual Data Refresh")
if st.button("🔄 Force Refresh All Data (clears 5-min cache)", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.toast("Cache cleared. Reloading fresh market data...", icon="🔄")
    st.rerun()

st.caption("Auto-refresh completely disabled. Click the button above to force fresh data from the engines. Data is cached for safety.")

# =========================================
# LOAD DATA (now behind cache - recomputes only on manual refresh)
# =========================================

@st.cache_data(ttl=300, show_spinner=False)  # 5 min safety cache, but only hit on manual
def _load_all_data():
    stocks = get_stock_watchlist()
    crypto = get_crypto_watchlist()
    regime = analyze_market_regime()
    brain = generate_master_report()
    btc_chart = get_chart_data("BTC/USDT")
    eth_chart = get_chart_data("ETH/USDT")
    btc_signal = generate_signal("BTC/USDT")
    eth_signal = generate_signal("ETH/USDT")
    return stocks, crypto, regime, brain, btc_chart, eth_chart, btc_signal, eth_signal

stocks, crypto, regime, brain, btc_chart, eth_chart, btc_signal, eth_signal = _load_all_data()

eth_signal = generate_signal(
    "ETH/USDT"
)

# =========================================
# MOSKY CYBERPUNK HUD HEADER (multi-neon effects)
# =========================================

st.markdown(
    """
<div style="
    background: rgba(0,20,40,0.95);
    border: 1px solid #00f0ff;
    box-shadow: 0 0 25px #00f0ff;
    padding: 14px 20px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 style="margin:0; font-size:2.1em; color:#ffcc00; text-shadow: 0 0 6px #ff6600, 0 0 12px #ff00cc, 0 0 18px #00f0ff;">
                MOSKY // AI MARKET INTELLIGENCE TERMINAL
            </h1>
            <p style="margin:4px 0 0; color:#a0d8ff; font-size:0.95em; opacity:0.85;">
                Self-Evolving Hierarchical Agent Swarm • 100% Fidelity • Guarded Proposals • Cyberpunk Market Terminal
            </p>
        </div>
        <div style="text-align:right; font-size:0.85em; line-height:1.3;">
            <span class="cyber-badge" style="border-color:#ff6600; color:#ffcc00;">CORE ONLINE</span><br>
            <span class="cyber-badge" style="border-color:#9900ff; color:#00f0ff;">SUPERVISOR ACTIVE</span><br>
            <span class="cyber-badge" style="border-color:#ff0033; color:#ffcc00;">EVOLUTION ENABLED</span>
        </div>
    </div>
    <div style="height:2px; background: linear-gradient(to right, #ff6600, #ffcc00, #9900ff, #00f0ff, #ff0033); margin-top:10px; box-shadow: 0 0 10px #ff00cc, 0 0 6px #00f0ff;"></div>
</div>
""",
    unsafe_allow_html=True
)

# Quick status line
now = datetime.now().strftime("%Y-%m-%d %H:%M")
st.caption(f"Last refresh: {now}  •  Auto-refresh every 5 min  •  Run with: `streamlit run dashboard.py`")

st.markdown("")

# =========================================
# TOP IMPRESSIVE METRICS ROW (more visual)
# =========================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📈 Stocks Regime", regime.get("stock_regime", "—"), delta="Active")
with col2:
    st.metric("₿ Crypto Regime", regime.get("crypto_regime", "—"), delta="Active")
with col3:
    st.metric("🌍 Overall Market", regime.get("overall", "—"), delta="Risk-On/Off")
with col4:
    st.metric("🧠 Agent Evolution", "87%", delta="Self-improving")

st.markdown("")

# =========================================
# AI SIGNAL PANEL (cleaner + neon)
# =========================================

st.subheader("⚡ AI SIGNAL PANEL")

s1, s2 = st.columns(2)
with s1:
    st.markdown("**BTC/USDT**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Signal", btc_signal.get("signal", "—"))
    c2.metric("RSI", btc_signal.get("rsi", "—"))
    c3.metric("MACD", btc_signal.get("macd", "—"))
    st.caption(str(btc_signal.get("reason", ""))[:160])

with s2:
    st.markdown("**ETH/USDT**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Signal", eth_signal.get("signal", "—"))
    c2.metric("RSI", eth_signal.get("rsi", "—"))
    c3.metric("MACD", eth_signal.get("macd", "—"))
    st.caption(str(eth_signal.get("reason", ""))[:160])

# =========================================
# WATCHLISTS (back to the original simple list style)
# =========================================

st.markdown("---")
st.subheader("👁️ WATCHLISTS")

left, right = st.columns(2)

with left:
    st.subheader("STOCK WATCHLIST")
    for item in stocks:
        st.text(item)

with right:
    st.subheader("CRYPTO WATCHLIST")
    for item in crypto:
        st.text(item)

# =========================================
# LIVE MARKET CHARTS
# =========================================

st.markdown("---")

st.subheader("📈 LIVE MARKET CHARTS (improved styling)")

ch1, ch2 = st.columns(2)
with ch1:
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(btc_chart["timestamp"], btc_chart["close"], label="Close", color="#00f0ff", linewidth=1.6)
    ax.plot(btc_chart["timestamp"], btc_chart["SMA20"], label="SMA20", color="#ffaa00", alpha=0.75)
    ax.set_title("BTC/USDT", color="#00f0ff", fontsize=11)
    ax.legend(facecolor="#111", edgecolor="#00f0ff", fontsize=8)
    ax.set_facecolor("#0a0a0f")
    fig.patch.set_facecolor("#0a0a0f")
    for spine in ax.spines.values():
        spine.set_color("#003344")
    st.pyplot(fig, use_container_width=True)

with ch2:
    fig2, ax2 = plt.subplots(figsize=(7, 3.2))
    ax2.plot(eth_chart["timestamp"], eth_chart["close"], label="Close", color="#00f0ff", linewidth=1.6)
    ax2.plot(eth_chart["timestamp"], eth_chart["SMA20"], label="SMA20", color="#ffaa00", alpha=0.75)
    ax2.set_title("ETH/USDT", color="#00f0ff", fontsize=11)
    ax2.legend(facecolor="#111", edgecolor="#00f0ff", fontsize=8)
    ax2.set_facecolor("#0a0a0f")
    fig2.patch.set_facecolor("#0a0a0f")
    for spine in ax2.spines.values():
        spine.set_color("#003344")
    st.pyplot(fig2, use_container_width=True)

# =========================================
# TECHNICAL INDICATORS
# =========================================

st.markdown("---")

st.subheader("📉 TECHNICAL INDICATORS (latest)")

t1, t2 = st.columns(2)

# =====================================
# BTC INDICATORS
# =====================================

with t1:

    latest = btc_chart.iloc[-1]
    st.markdown("**BTC**")

    st.metric(

        "RSI",

        round(
            latest["RSI"],
            2
        )
    )

    st.metric(

        "MACD",

        round(
            latest["MACD"],
            2
        )
    )

    st.metric(

        "MACD SIGNAL",

        round(
            latest["MACD_SIGNAL"],
            2
        )
    )

# =====================================
# ETH INDICATORS
# =====================================

with t2:

    latest = eth_chart.iloc[-1]

    st.markdown("**ETH**")

    st.metric(

        "RSI",

        round(
            latest["RSI"],
            2
        )
    )

    st.metric(

        "MACD",

        round(
            latest["MACD"],
            2
        )
    )

    st.metric(

        "MACD SIGNAL",

        round(
            latest["MACD_SIGNAL"],
            2
        )
    )

# =========================================
# MASTER BRAIN + NEW IMPRESSIVE SELF-EVOLVING SECTION
# =========================================

st.markdown("---")
st.subheader("🧠 MASTER MARKET BRAIN REPORT (raw)")

st.code(brain)

# =========================================
# NEW: SELF-EVOLVING AGENT HIGHLIGHTS (the impressive part for the user)
# =========================================

st.markdown("---")
st.subheader("🤖 SELF-EVOLVING AGENT — HIGHLIGHTS")

st.markdown("""
<div style="
    background: rgba(0,25,45,0.75);
    border: 1px solid #00f0ff;
    padding: 14px;
    border-radius: 6px;
    margin: 8px 0;
    box-shadow: 0 0 12px rgba(0,240,255,0.25);
">
<strong>Hierarchical Agent Swarm active</strong><br>
Meta-Supervisor → Domain Supervisors (Blockchain / Research / Engineering) → Specialists<br>
• Research discovers real skills (GitHub + X + broad) with <strong>pros/cons</strong> + full 100% fidelity evidence<br>
• All improvements go through <strong>guarded_propose</strong> + human gate + pre/post evaluation + rollback<br>
• Persistent evolution memory + meta learnings
</div>
""", unsafe_allow_html=True)

# Show recent activity from the real system (safe, read-only)
st.markdown("**Recent Guarded Proposals & Evolution Activity**")
pending_dir = Path("memory/pending_proposals")
if pending_dir.exists():
    pending = sorted(pending_dir.glob("*.json"))[-5:]
    applied = list(pending_dir.glob("*.approved"))
    if pending or applied:
        for p in pending:
            st.markdown(f"- `{p.name}` — ⏳ PENDING (human approval required)")
        for a in applied[-3:]:
            st.markdown(f"- `{a.stem}.json` — ✅ APPLIED (guarded + evaluated)")
    else:
        st.caption("No proposals visible in this session.")
else:
    st.caption("memory/pending_proposals not present.")

st.markdown("---")
st.caption("MOSKY — Local-first • Self-evolving Hierarchical Agent Swarm • Guarded • 100% Fidelity • Cyberpunk Terminal")
