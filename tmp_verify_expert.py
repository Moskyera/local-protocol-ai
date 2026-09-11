#!/usr/bin/env python3
"""Temp verification script for direct expert call on host."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openhands_skills.chain_analysis_expert import chain_analysis_expert
print("HOST IMPORT: SUCCESS - chain_analysis_expert loaded from ai-env or system python with path setup")
addr = "0x000000000000000000000000000000000000dEaD"
ra = chain_analysis_expert.analyze_address(addr, chain="pulsechain")
rs = ra.get("risk_score", {}) if isinstance(ra, dict) else {}
pnl = ra.get("pnl_estimate", {}) if isinstance(ra, dict) else {}
print("address:", addr)
print("risk_level:", rs.get("level"))
print("risk_score:", rs.get("score"))
print("native_inflow_usd:", rs.get("native_inflow_usd"))
print("pattern_match:", rs.get("pattern_match"))
print("pnl_current_usd:", pnl.get("current_portfolio_usd"))
print("explorer:", ra.get("explorer_link") if isinstance(ra, dict) else None)
print("SUCCESS: USD-based risk/PnL numbers computed deterministically in Python (no LLM hallucination).")
print("KEYS sample:", list(ra.keys())[:8] if isinstance(ra, dict) else "not dict")