"""
Shared tool-call error correction (no MCP / LangGraph dependencies).

Used by openhands_mcp.server and langgraph_orchestrator to avoid circular imports.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def fix_tool_call_error(
    original_tool_name: str,
    attempted_call: dict,
    error_message: str,
    user_intent: str = "",
) -> Dict[str, Any]:
    """
    Analyze a failed tool call and return a corrected call when possible.
    Pure function — safe to import from any layer.
    """
    _ = user_intent  # reserved for future intent-aware fixes
    corrections: dict[str, str] = {}
    normalized: dict[str, Any] = {}

    if original_tool_name == "create_pr":
        for bad, good in [
            ("repo", "repo_name"),
            ("repository", "repo_name"),
            ("repoName", "repo_name"),
            ("owner", "repo_name"),
        ]:
            if bad in attempted_call and "repo_name" not in attempted_call:
                normalized["repo_name"] = attempted_call[bad]
                corrections[bad] = f"→ renamed to {good}"

        for k, v in attempted_call.items():
            if k not in ["repo", "repository", "repoName"]:
                normalized[k] = v

        corrected_call = {
            "name": "create_pr",
            "params": normalized or attempted_call,
        }

        return {
            "fixed": True,
            "original_tool": original_tool_name,
            "corrections_made": corrections,
            "corrected_call": corrected_call,
            "suggested_xml": f"<function_call>\n{json.dumps(corrected_call, indent=2)}\n</function_call>",
            "note": "Use the corrected_call above. If the error persists, call this helper again with the new error.",
            "mcp_tool": "fix_tool_call_error",
        }

    return {
        "fixed": False,
        "message": (
            f"No specific fixer yet for {original_tool_name}. "
            "Common advice: check the exact parameter names in the tool description. "
            "Never use 'repo' for GitHub tools - always 'repo_name'."
        ),
        "original_error": error_message,
        "attempted": attempted_call,
        "hint": (
            "Call get_proposal_details or list_pending_proposals first "
            "if this is related to guarded self-improvement."
        ),
        "mcp_tool": "fix_tool_call_error",
    }