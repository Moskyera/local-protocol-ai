"""
Centralized project paths for MOSKY AI Workstation.

This reduces hardcoded C:\AI strings across the codebase (especially in the agentic layers).
Import from here in openhands_skills/, automation/, openhands_mcp/, etc.

Usage:
    from project_paths import MARKET_AGENT_ROOT, AI_ROOT, get_venv_python
    print(MARKET_AGENT_ROOT)
"""

from pathlib import Path
import os
import sys

# === Core roots ===
MARKET_AGENT_ROOT: Path = Path(__file__).resolve().parent
AI_ROOT: Path = MARKET_AGENT_ROOT.parent

# === Important sub-paths ===
LLAMA_DIR: Path = AI_ROOT / "llama"
MODELS_DIR: Path = AI_ROOT / "models"
VENV_DIR: Path = AI_ROOT / "ai-env"

# Primary venv python (used by launchers and scripts)
VENV_PYTHON: Path = VENV_DIR / "Scripts" / "python.exe"

# Experiments and automation roots (after reorganization)
EXPERIMENTS_DIR: Path = MARKET_AGENT_ROOT / "experiments"
AUTOMATION_DIR: Path = MARKET_AGENT_ROOT / "automation"

# OpenHands related
OPENHANDS_SKILLS_DIR: Path = MARKET_AGENT_ROOT / "openhands_skills"
OPENHANDS_MCP_DIR: Path = MARKET_AGENT_ROOT / "openhands_mcp"
OPENHANDS_MULTIAGENT_V2_DIR: Path = MARKET_AGENT_ROOT / "openhands_multiagent_v2"

# Memory
MEMORY_DIR: Path = MARKET_AGENT_ROOT / "memory"

# Visual generation (ComfyUI workflows for Flux + Wan etc.)
VISUAL_WORKFLOWS_DIR: Path = MARKET_AGENT_ROOT / "workflows" / "visual"

# Wealth mentor / practical economics advisor (real conditions money making strategies, deterministic models)
WEALTH_DIR: Path = MARKET_AGENT_ROOT / "wealth"
WEALTH_KNOWLEDGE_DIR: Path = WEALTH_DIR / "knowledge"

def get_market_agent_root() -> Path:
    """Returns the root of the market-agent project."""
    return MARKET_AGENT_ROOT

def get_ai_root() -> Path:
    """Returns C:\AI (parent of market-agent)."""
    return AI_ROOT

def get_venv_python() -> Path:
    """Returns the full path to the primary ai-env python.exe."""
    return VENV_PYTHON

def ensure_in_path(path: Path | str) -> None:
    """Ensure a directory is at the front of sys.path (idempotent, used by defensive setups)."""
    p = str(Path(path).resolve())
    if p not in sys.path:
        sys.path.insert(0, p)

def add_market_agent_to_path() -> None:
    """Common helper for defensive imports in Docker/host/MCP contexts."""
    ensure_in_path(MARKET_AGENT_ROOT)

# Backwards compatibility helpers for old hardcoded strings (use sparingly)
def old_ai_market_agent_str() -> str:
    """The classic 'C:/AI/market-agent' string for legacy path setups. Prefer the Path versions."""
    return str(MARKET_AGENT_ROOT).replace("\\", "/")

def old_ai_root_str() -> str:
    return str(AI_ROOT).replace("\\", "/")

# Quick sanity when imported directly
if __name__ == "__main__":
    print("MARKET_AGENT_ROOT:", MARKET_AGENT_ROOT)
    print("AI_ROOT:", AI_ROOT)
    print("VENV_PYTHON:", VENV_PYTHON)
    print("Exists:", VENV_PYTHON.exists())
