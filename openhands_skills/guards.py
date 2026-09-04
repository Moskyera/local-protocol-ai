"""
Centralized Path Guards & Self-Modification Safety for the 3-agent system.

This is the professional safety foundation. All self-improving / proposal logic
MUST go through these guards.

Non-negotiable rules:
- NEVER allow modifications (or even proposals) to Telegram/briefing engines.
- Only allow changes inside: openhands_skills/, openhands_mcp/, openhands_multiagent_v2/, langgraph_orchestrator.py, automation/, runtime/.
- Proposals must be explicit, auditable, and human-gated.
"""

from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ast
import difflib
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

# === CORE FORBIDDEN LIST (single source of truth) ===
FORBIDDEN_PATHS = [
    "telegram_engine.py",
    "master_market_brain.py",
    "geopolitical_engine.py",
    "corporate_news_engine.py",
    "send_briefing.bat",
    "send_simplex_briefing.py",
    "briefing",
    "daily_report",
    "send_full_ai_briefing",
    # Any file that generates or delivers the 6 daily market messages
]

# === GUARDRAIL PROVIDER (inspired by recent AutoGen proposal + our existing guards) ===
# This centralizes tool call interception for intent + param + security validation.
# All tool calls (MCP web_research, execute_v2_task, direct experts, etc.) should
# eventually go through a formal guardrail layer before dispatch.
# Current implementation: is_allowed_for_modification + validate_proposal + user_confirmed in MCP tools.
# Future: explicit GuardrailProvider class that wraps every tool call with security_risk, schema validation, and human confirmation hooks.

# Allowed roots for self-modification / proposals (relative to project)
ALLOWED_ROOTS = [
    "openhands_skills",
    "openhands_mcp",
    "openhands_multiagent_v2",
    "langgraph_orchestrator.py",
    "automation",
    "automation_examples",  # compat shim → automation/
    "runtime",
]

try:
    from project_paths import MARKET_AGENT_ROOT as _PROJECT_ROOT
except Exception:
    _PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROJECT_ROOT = Path(_PROJECT_ROOT).resolve()
_ALLOWED_DIRECTORIES = {
    root.casefold() for root in ALLOWED_ROOTS if not Path(root).suffix
}
_ALLOWED_FILES = {
    Path(root).as_posix().casefold() for root in ALLOWED_ROOTS if Path(root).suffix
}
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: Dict[str, threading.RLock] = {}


def _get_path_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path))
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


def _relative_project_path(path: str, *, must_exist: bool = False) -> Tuple[Path, Path]:
    """Resolve a path and prove that it remains inside this project."""
    if not isinstance(path, (str, os.PathLike)):
        raise ValueError("Path must be a string or path-like value")
    raw_text = os.fspath(path).strip()
    if not raw_text or chr(0) in raw_text:
        raise ValueError("Path is empty or contains a NUL byte")

    raw = Path(raw_text)
    candidate = raw if raw.is_absolute() else PROJECT_ROOT / raw
    try:
        resolved = candidate.resolve(strict=must_exist)
        relative = resolved.relative_to(PROJECT_ROOT)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("Path escapes the project root or cannot be resolved") from exc

    if not relative.parts:
        raise ValueError("The project root itself is not an editable target")
    return resolved, relative


def resolve_safe_target(path: str, *, must_exist: bool = False) -> Path:
    """Return a canonical file target only inside an explicitly allowed root."""
    resolved, relative = _relative_project_path(path, must_exist=must_exist)
    relative_text = relative.as_posix()
    if is_forbidden_path(relative_text):
        raise PermissionError("Target is in a protected area")

    first_part = relative.parts[0].casefold()
    relative_key = relative_text.casefold()
    if first_part not in _ALLOWED_DIRECTORIES and relative_key not in _ALLOWED_FILES:
        raise PermissionError("Target is outside the allowed self-modification roots")
    if resolved.exists() and resolved.is_dir():
        raise PermissionError("Target must be a file, not a directory")
    return resolved

def _normalize(path: str) -> str:
    return str(path or "").casefold().replace("\\", "/").strip()

def is_forbidden_path(path: str) -> bool:
    """Returns True if the path (file or area) is strictly forbidden for any self-mod or proposal."""
    p = _normalize(path)
    for forbidden in FORBIDDEN_PATHS:
        if forbidden.lower() in p:
            return True
    return False

def is_allowed_for_modification(path: str) -> bool:
    """Returns True only if the target is inside the explicitly allowed areas for agent-driven changes."""
    try:
        resolve_safe_target(path, must_exist=False)
        return True
    except (OSError, PermissionError, ValueError):
        return False

def validate_proposal(proposal: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates a proposal dict coming from Research → Engineering.
    Returns: (allowed: bool, reason: str, sanitized_proposal: dict)
    """
    if not isinstance(proposal, dict):
        return False, "Proposal must be a dict", {}

    suggestion = str(proposal.get("suggestion") or proposal.get("change") or "")
    target_area = str(proposal.get("target_area") or proposal.get("target") or "")

    # SECURITY: collect the target from EVERY place it can come from. This used
    # to read only `target_file`, while apply_proposal also accepts
    # `apply_data.file` — so a proposal that hid the path in apply_data passed
    # validation untouched and was then applied to a forbidden file
    # (verified against telegram_engine.py). Any new field that apply_proposal
    # learns to read MUST be added here too.
    apply_data = proposal.get("apply_data") or {}
    if not isinstance(apply_data, dict):
        apply_data = {}
    target_candidates = [
        proposal.get("target_file"),
        apply_data.get("file"),
        apply_data.get("target_file"),
        apply_data.get("path"),
        proposal.get("file"),
        proposal.get("path"),
    ]
    targets = [str(t) for t in target_candidates if t]
    target_file = targets[0] if targets else ""

    for cand in targets + [target_area, suggestion]:
        if is_forbidden_path(cand):
            return False, f"FORBIDDEN: touches protected area ({cand}). This is non-negotiable.", proposal

    # Every declared target must be inside the allowed roots, not just the first.
    for t in targets:
        if not is_allowed_for_modification(t):
            return False, f"FORBIDDEN: {t} is outside the explicitly allowed project roots.", proposal

    # FAIL CLOSED. A proposal that names no target at all used to be ALLOWED,
    # which is the wrong default for something that edits its own source.
    if not targets:
        return False, ("REJECTED: the proposal does not name a target file. "
                       "Self-modification must state exactly what it changes."), proposal

    # Sanitize / enrich the proposal
    sanitized = dict(proposal)
    sanitized["validated"] = True
    sanitized["validated_at"] = __import__("datetime").datetime.now().isoformat()
    sanitized["guard_version"] = "2.0-contained-paths"

    # Try to infer a concrete target file when possible (helps later application)
    if not sanitized.get("target_file"):
        for root in ALLOWED_ROOTS:
            if root in suggestion.lower() or root in target_area.lower():
                # Heuristic: common patterns
                if "chain_analysis" in suggestion.lower() or "risk" in suggestion.lower() or "parallel" in suggestion.lower():
                    sanitized["target_file"] = "openhands_skills/chain_analysis_expert.py"
                elif "mcp" in suggestion.lower() or "supervise" in suggestion.lower():
                    sanitized["target_file"] = "openhands_mcp/server.py"
                elif "langgraph" in suggestion.lower() or "supervisor" in suggestion.lower():
                    sanitized["target_file"] = "openhands_skills/langgraph_orchestrator.py"
                elif "hyper" in suggestion.lower() or "evolution" in suggestion.lower():
                    sanitized["target_file"] = "openhands_multiagent_v2/hyper_evolution_agent.py"
                break

    return True, "OK", sanitized

def get_forbidden_paths() -> List[str]:
    """For transparency / logging in supervisor outputs."""
    return list(FORBIDDEN_PATHS)

def get_allowed_roots() -> List[str]:
    return list(ALLOWED_ROOTS)

# Convenience for other modules
def enforce_guard(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """Raises on violation, otherwise returns the (possibly enriched) proposal."""
    allowed, reason, sanitized = validate_proposal(proposal)
    if not allowed:
        raise PermissionError(f"Guard violation: {reason}")
    return sanitized

def test_proposal_safety(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hard security/safety test for proposals (unit-style check for the evolution loop).
    Used by supervisor and guarded_propose for "σκληρότερο testing της ασφάλειας".
    Returns a report that can be stored in pending proposals or memory.
    """
    allowed, reason, sanitized = validate_proposal(proposal)
    target = str(proposal.get("target_file") or proposal.get("target_area") or proposal.get("suggestion", ""))

    violations = []
    if not allowed:
        violations.append(reason)
    if is_forbidden_path(target):
        violations.append("Direct forbidden path match in target.")
    if any(x in target.lower() for x in ["telegram", "briefing", "master_market"]):
        violations.append("Explicit reference to protected briefing/telegram area.")

    report = {
        "passed": len(violations) == 0,
        "violations": violations,
        "checked_target": target[:120],
        "sanitized_proposal": sanitized,
        "guard_version": "1.0-central",
    }
    return report

def log_security_violation(proposal: Dict[str, Any], context: str = ""):
    """Records a serious violation attempt in persistent memory for audit."""
    try:
        from openhands_skills.persistent_memory import persistent_memory
        persistent_memory.store(
            text=f"SECURITY VIOLATION ATTEMPT in self-improvement: {context}",
            metadata={
                "type": "security_violation",
                "proposal": str(proposal)[:500],
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        )
    except Exception:
        pass  # never break the guard on logging failure

def perform_guarded_edit(target_file: str, old_text: str, new_text: str, dry_run: bool = True, context: str = "", fuzzy: bool = False, human_approved: bool = False) -> Dict[str, Any]:
    """
    HARDENED safe edit helper (professional RSI - "λιγο πιο σκληρο").
    Multiple layers of defense:
    - Re-validates target with central guards.
    - fuzzy=False by default (dangerous; opt-in only).
    - Real (non-dry) writes **require** human_approved=True (human must have edited the pending proposal json).
    - Always creates .bak before write.
    - .py files: post-edit ast.parse + automatic rollback on syntax error.
    - Hard size limit: refuses |diff| > 8000 chars in one go.
    - Full audit report (backup, fuzzy flag, human_approved, syntax result).
    - Never does git commit. Leaves for human review.
    """
    if is_forbidden_path(target_file) or not is_allowed_for_modification(target_file):
        reason = "Target file is FORBIDDEN or outside allowed self-mod roots."
        log_security_violation({"target_file": target_file}, context=f"perform_guarded_edit blocked: {context}")
        return {"success": False, "dry_run": dry_run, "applied": False, "reason": reason, "target_file": target_file}

    if not dry_run and not human_approved:
        reason = "HARDENED GUARD: Real apply requires human_approved=True (human must edit the pending proposal json to mark approved after review)."
        log_security_violation({"target_file": target_file}, context=f"perform_guarded_edit missing human approval: {context}")
        return {"success": False, "dry_run": dry_run, "applied": False, "reason": reason, "target_file": target_file, "human_approved": False}

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            original = f.read()

        matched = False
        actual_old = old_text
        if old_text in original:
            matched = True
        elif fuzzy:
            # Simple fuzzy: look for a containing block (e.g. function or comment section)
            # Try to find a larger context around the hint
            lines = original.splitlines()
            hint_lower = old_text.lower()[:80]
            for i, line in enumerate(lines):
                if hint_lower in line.lower():
                    start = max(0, i - 3)
                    end = min(len(lines), i + 10)
                    block = "\n".join(lines[start:end])
                    if old_text[:50] in block or any(part in block for part in old_text.split()[:5]):
                        # Use the block as old for replacement
                        actual_old = block
                        matched = True
                        break

        if not matched:
            return {
                "success": False, "dry_run": dry_run, "applied": False,
                "reason": "old_text not found (exact match required for safety). fuzzy=True only with human_approved after review.",
                "target_file": target_file,
            }

        diff_size = len(new_text) - len(actual_old)
        if not dry_run and abs(diff_size) > 3000:
            return {
                "success": False, "dry_run": dry_run, "applied": False,
                "reason": f"Change too large for one hardened guarded edit ({diff_size} chars). Split proposal or obtain extra approval file.",
                "target_file": target_file,
            }

        modified = original.replace(actual_old, new_text, 1)

        diff_preview = {
            "old_text_preview": actual_old[:400] + ("..." if len(actual_old) > 400 else ""),
            "new_text_preview": new_text[:400] + ("..." if len(new_text) > 400 else ""),
            "change_size": diff_size,
            "fuzzy_used": fuzzy and actual_old != old_text,
        }

        if dry_run:
            return {
                "success": True, "dry_run": True, "applied": False,
                "target_file": target_file, "diff_preview": diff_preview,
                "human_approved": human_approved,
                "note": "DRY RUN. For real apply: human sets 'human_approved': true in the pending proposal json, then calls apply_proposal(..., dry_run=False, human_approved=True).",
            }

        # === HARDENED REAL APPLY ===
        backup_path = target_file + ".bak." + __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S%f")
        with open(backup_path, "w", encoding="utf-8") as bf:
            bf.write(original)

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified)

        # Syntax gate + auto-rollback for Python
        syntax_ok = True
        syntax_error = ""
        if target_file.endswith(".py"):
            try:
                import ast
                ast.parse(modified)
            except SyntaxError as se:
                syntax_ok = False
                syntax_error = str(se)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(original)  # rollback

        if not syntax_ok:
            return {
                "success": False, "dry_run": False, "applied": False,
                "reason": f"SYNTAX ERROR after edit - ROLLED BACK. {syntax_error}",
                "target_file": target_file, "backup": backup_path
            }

        # Hardened audit log
        try:
            from openhands_skills.persistent_memory import persistent_memory
            persistent_memory.store(
                text=f"HARDENED GUARDED APPLY on {target_file} (human_approved={human_approved}, fuzzy={fuzzy})",
                metadata={
                    "type": "guarded_apply_hardened",
                    "target_file": target_file,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "change_size": diff_size,
                    "fuzzy": fuzzy,
                    "human_approved": human_approved,
                    "backup": backup_path,
                    "syntax_checked": syntax_ok,
                    "context": (context or "")[:180],
                }
            )
        except Exception:
            pass

        return {
            "success": True, "dry_run": False, "applied": True,
            "target_file": target_file, "diff_preview": diff_preview,
            "backup": backup_path, "syntax_checked": syntax_ok,
            "note": "HARDENED apply done. Backup created. Syntax verified. Human MUST git-review the diff + run tests before commit. No auto-git.",
        }

    except Exception as e:
        return {"success": False, "dry_run": dry_run, "applied": False, "reason": str(e)[:300], "target_file": target_file}


def has_extra_approval(proposal_id: str, proposals_dir: str) -> bool:
    """Extra approval file gate (for even harder human gate).
    Human creates an empty or note file named <proposal_id>.approved next to the pending json.
    """
    if not proposal_id or not proposals_dir:
        return False
    approved_path = os.path.join(proposals_dir, f"{proposal_id}.approved")
    return os.path.exists(approved_path)


def run_pre_apply_safety_tests(target_file: str) -> dict:
    """Mandatory test runner before real apply (harder safety).
    - Always: py_compile
    - For .py: safe import test (via subprocess to avoid polluting)
    - For known domain files (chain_analysis_expert etc.): run quick self-test or automation example if available.
    Returns report with 'passed', 'details'.
    """
    results = {"passed": True, "checks": []}
    import subprocess
    import sys

    # 1. Syntax/compile
    try:
        subprocess.check_output([sys.executable, "-m", "py_compile", target_file], stderr=subprocess.STDOUT)
        results["checks"].append({"name": "py_compile", "passed": True})
    except subprocess.CalledProcessError as e:
        results["passed"] = False
        results["checks"].append({"name": "py_compile", "passed": False, "output": e.output.decode()[:500]})

    # 2. Safe import test (subprocess)
    if target_file.endswith(".py"):
        try:
            # Use -c to import the module by path without executing main
            cmd = [sys.executable, "-c", f"import importlib.util; spec=importlib.util.spec_from_file_location('tmpmod', r'{target_file}'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('IMPORT_OK')"]
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10)
            if b"IMPORT_OK" in out:
                results["checks"].append({"name": "safe_import", "passed": True})
            else:
                results["passed"] = False
                results["checks"].append({"name": "safe_import", "passed": False, "output": out.decode()[:300]})
        except Exception as e:
            results["passed"] = False
            results["checks"].append({"name": "safe_import", "passed": False, "error": str(e)[:200]})

    # 3. Domain-specific quick test (example for our chain expert)
    if "chain_analysis_expert" in target_file:
        try:
            # Run a minimal known-good call via the automation example or direct (non-destructive)
            # For safety, just re-import and call a tiny function if possible, or run the wallet demo in dry-ish way.
            # Here we simulate by running a quick python snippet that exercises the expert lightly.
            test_cmd = [sys.executable, "-c", "from openhands_skills.chain_analysis_expert import chain_analysis_expert; print('CHAIN_EXPERT_OK')"]
            out = subprocess.check_output(test_cmd, stderr=subprocess.STDOUT, timeout=15)
            if b"CHAIN_EXPERT_OK" in out:
                results["checks"].append({"name": "domain_chain_expert_smoke", "passed": True})
        except Exception as e:
            results["checks"].append({"name": "domain_chain_expert_smoke", "passed": False, "error": str(e)[:150]})

    # DERIVE the verdict from the checks instead of trusting a flag every branch
    # has to remember to set. The domain smoke test appended
    # {"name": ..., "passed": False} in its except branch and never touched
    # results["passed"], so a failed smoke test left the gate reporting PASSED
    # and the edit was applied. A safety gate that can forget to fail is not a
    # safety gate.
    failed = [c for c in results["checks"] if not c.get("passed")]
    results["passed"] = not failed
    if failed:
        results["failed_checks"] = [c.get("name", "?") for c in failed]
        results["summary"] = ("Pre-apply safety tests FAILED (" +
                              ", ".join(results["failed_checks"]) +
                              "). Apply blocked for safety.")

    return results


def perform_rollback(target_file: str, backup_path: str = None, context: str = "") -> dict:
    """Rollback to a previous backup (for when a new update no longer satisfies us).
    Finds the latest .bak if not specified, restores the file, logs the rollback.
    Returns report. This is guarded (only allowed paths) and audited.
    """
    if is_forbidden_path(target_file) or not is_allowed_for_modification(target_file):
        return {"success": False, "reason": "Rollback target is forbidden or outside allowed roots."}

    if not backup_path:
        # Find latest .bak for this file
        import glob
        pattern = target_file + ".bak.*"
        candidates = sorted(glob.glob(pattern), reverse=True)
        if not candidates:
            return {"success": False, "reason": "No backup found for rollback."}
        backup_path = candidates[0]

    if not os.path.exists(backup_path):
        return {"success": False, "reason": "Specified backup does not exist."}

    try:
        with open(backup_path, "r", encoding="utf-8") as bf:
            previous = bf.read()
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(previous)

        try:
            from openhands_skills.persistent_memory import persistent_memory
            persistent_memory.store(
                text=f"ROLLED BACK {target_file} to {backup_path}. Context: {context}",
                metadata={
                    "type": "guarded_rollback",
                    "target_file": target_file,
                    "backup_used": backup_path,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "context": (context or "")[:180],
                }
            )
        except Exception:
            pass

        return {
            "success": True,
            "target_file": target_file,
            "restored_from": backup_path,
            "note": "Rollback completed. Review the restored state, run tests, and decide on next steps (new proposal or manual fix)."
        }
    except Exception as e:
        return {"success": False, "reason": str(e)[:300]}


# Re-export for convenience
__all__ = [
    "FORBIDDEN_PATHS", "is_forbidden_path", "is_allowed_for_modification",
    "validate_proposal", "enforce_guard", "test_proposal_safety", "log_security_violation",
    "get_forbidden_paths", "get_allowed_roots", "perform_guarded_edit",
    "has_extra_approval", "run_pre_apply_safety_tests", "perform_rollback",
    "GuardrailProvider", "guardrail_provider",
]


# === GuardrailProvider (Proposal 2: Tool Call Interception Protocol) ===
# Human approved 2026-06-12 (as part of the 3 proposals in AGENT_UPGRADE_PLAN.md).
# Central interception for tool calls before dispatch.
# Validates intent, parameters (incl. security_risk), security context.
# Designed to be integrated into MCP tools and supervisor expert calls.
# Existing code already has pieces (user_confirmed in web_research, guards in proposals).
# This formalizes it as a reusable provider.
class GuardrailProvider:
    def __init__(self):
        self.interceptions = []  # audit log

    def intercept_tool_call(self, tool_name: str, params: dict, context: str = "", security_level: str = "low") -> dict:
        """
        Intercepts a tool call (Proposal 2: Tool Call Interception Protocol / GuardrailProvider).
        Inspired by guardrails-mcp-server and AutoGen guardrails.
        - Normalizes params (e.g. 'query' alias handling).
        - Checks for required fields like 'security_risk', 'user_confirmed' for risky tools.
        - Applies security context validation, intent checks, policy enforcement.
        - Returns sanitized params (or raises on violation).
        - Logs for audit (persistent_memory).
        - Can be extended for PII redaction, rate limiting, etc.
        """
        sanitized = dict(params)  # copy

        # Normalization (robust against LLM param name errors)
        if "research_query" in sanitized and "query" not in sanitized:
            sanitized["query"] = sanitized.pop("research_query")
        if "repo" in sanitized and "repo_name" not in sanitized:  # from create_pr example
            sanitized["repo_name"] = sanitized.pop("repo")

        # Security risk and confirmation for risky tools (web, external, self-mod)
        risky_tools = {"web_research", "browser", "research", "execute_v2_task", "generate_image", "generate_video", "wealth_mentor", "consult_wealth_mentor"}
        if tool_name in risky_tools:
            if "security_risk" not in sanitized:
                sanitized["security_risk"] = security_level
            if tool_name == "web_research" and not sanitized.get("user_confirmed", False):
                if "user_confirmed" not in sanitized:
                    sanitized["user_confirmed"] = False
                # Note: caller must get human yes before True (as per web_research flow)

        # Intent validation (from tool-restrictions.md patterns)
        forbidden_intents = ["browser", "direct file write outside allowed", "bypass guards"]
        intent_str = str(params).lower() + str(context).lower()
        if tool_name == "browser" or any(f in intent_str for f in forbidden_intents):
            raise PermissionError(f"Tool '{tool_name}' or intent forbidden by GuardrailProvider. Use safe alternatives like web_research.")

        # Policy enforcement stub (e.g., rate limit self-improvement proposals)
        if "proposal" in tool_name.lower() or "self_improv" in context.lower():
            # Could check persistent_memory for recent proposals count, but keep simple
            pass

        # Log for audit
        self.interceptions.append({
            "tool": tool_name,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "context": context[:100],
            "sanitized_params": {k: str(v)[:50] for k, v in sanitized.items()},
        })

        return sanitized

    def get_recent_interceptions(self, limit: int = 10):
        return self.interceptions[-limit:]

    def validate_input(self, tool_name: str, input_data: str) -> bool:
        """Input guardrail: detect prompt injection or bad input (inspired by guardrails-mcp-server)."""
        bad_patterns = ["ignore previous", "bypass", "jailbreak", "forget rules"]
        if any(p in input_data.lower() for p in bad_patterns):
            self.interceptions.append({"tool": tool_name, "violation": "input_guardrail", "input": input_data[:50]})
            return False
        return True

    def filter_output(self, tool_name: str, output: str) -> str:
        """Output guardrail: redact PII or sensitive (simple version)."""
        # In real, use regex for emails, keys etc. Here stub.
        return output  # extend as needed


# Global singleton for easy import and use across supervisor/MCP
guardrail_provider = GuardrailProvider()

# Convenience wrapper (can be used in @mcp.tool wrappers or supervisor nodes)
def apply_guardrail(tool_name: str, params: dict, **kwargs) -> dict:
    return guardrail_provider.intercept_tool_call(tool_name, params, **kwargs)
