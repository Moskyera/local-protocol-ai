"""
OpenHands Skills Package
Collection of expert skills for use with OpenHands or custom agents.
Includes market intelligence bridge (tool_integration_hub) and various coding/dev experts.
"""
import sys
import os

# The repository root, derived from this file rather than written down.
# It was the literal string 'C:/AI/market-agent', which is where this
# happens to be checked out and not a fact about anyone else's disk. In a
# container the package is mounted at /workspace, and this resolves to it.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Central UTF-8 hardening (fixes Windows cp1252 crashes) ---
# Many skills print emoji at import time. On a Windows console (cp1252) that
# raises UnicodeEncodeError and hard-kills the import of ~25 skills. Reconfigure
# stdout/stderr to UTF-8 once, here, before any skill module runs its prints.
def _force_utf8_io():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_force_utf8_io()

# Robust auto path setup for OpenHands sandboxes, Docker runtimes, and mixed environments.
# Must be called BEFORE any "import openhands_skills" or "from openhands_skills..." in agent-generated code.
def _auto_path_setup():
    candidates = [
        '/workspace',
        os.environ.get('WORKSPACE_BASE', ''),
        os.getcwd(),
        os.path.expanduser('~/.openhands/skills'),
        _REPO_ROOT,
        os.path.dirname(os.path.abspath(__file__)),  # the package dir itself
    ]
    added = []
    for base in candidates:
        if not base:
            continue
        base = os.path.abspath(base)
        if os.path.isdir(base) and base not in sys.path:
            sys.path.insert(0, base)
            added.append(base)
        # Also add parent if this is the skills dir
        parent = os.path.dirname(base)
        if os.path.isdir(parent) and parent not in sys.path:
            sys.path.insert(0, parent)
            added.append(parent)
    if added:
        # Re-insert workspace variants aggressively
        for extra in ['/workspace', _REPO_ROOT]:
            if os.path.isdir(extra) and extra not in sys.path:
                sys.path.insert(0, extra)

_auto_path_setup()

# Use safe imports so the package can be imported in limited sandbox environments
# (like OpenHands runtime) where some deps (logger, chromadb, etc.) may be missing.
def _safe_import(name, default=None):
    try:
        module = __import__(name, fromlist=[''])
        return module
    except Exception as e:
        print(f"[openhands_skills __init__] Warning: could not import {name}: {e}")
        return default

tool_hub = getattr(_safe_import('openhands_skills.tool_integration_hub'), 'tool_hub', None)
PersistentMemory = getattr(_safe_import('openhands_skills.persistent_memory'), 'PersistentMemory', None)
master_loader = getattr(_safe_import('openhands_skills.master_loader'), 'master_loader', None)
MasterTrigger = getattr(_safe_import('openhands_skills.master_trigger'), 'MasterTrigger', None)
solidity_expert = getattr(_safe_import('openhands_skills.solidity_expert'), 'solidity_expert', None)
pulsechain_expert = getattr(_safe_import('openhands_skills.pulsechain_expert'), 'pulsechain_expert', None)
chain_analysis_expert = getattr(_safe_import('openhands_skills.chain_analysis_expert'), 'chain_analysis_expert', None)
run_task = getattr(_safe_import('openhands_skills.openhands_v2_entry'), 'run_task', None)
get_solidity_expert = getattr(_safe_import('openhands_skills.openhands_v2_entry'), 'get_solidity_expert', None)
get_v2_orchestrator = getattr(_safe_import('openhands_skills.openhands_v2_entry'), 'get_v2_orchestrator', None)
langgraph_orchestrator = _safe_import('openhands_skills.langgraph_orchestrator')
get_wallet_analysis_graph = getattr(_safe_import('openhands_skills.langgraph_orchestrator'), 'get_wallet_analysis_graph', None)
direct_analyze_wallet = getattr(_safe_import('openhands_skills.langgraph_orchestrator'), 'direct_analyze_wallet', None)

__all__ = [
    "tool_hub",
    "PersistentMemory",
    "master_loader",
    "MasterTrigger",
    "solidity_expert",
    "pulsechain_expert",
    "chain_analysis_expert",
    "run_task",
    "get_solidity_expert",
    "get_v2_orchestrator",
    "langgraph_orchestrator",
    "get_wallet_analysis_graph",
    "direct_analyze_wallet",
]
