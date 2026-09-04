"""
Large Codebase Master Skill v4.

Πραγματικό πλέον: αντί να τυπώνει hardcoded module list, όντως χαρτογραφεί το
filesystem, τρέχει τους deterministic analyzers (code_intelligence) σε πραγματικά
αρχεία, και συνθέτει architecture/refactoring insights μέσω του μοντέλου.
"""

import os
from pathlib import Path

try:  # opendevin is optional / absent in most runtimes — degrade gracefully
    from opendevin.core.schema import ActionType
    from opendevin.controller.state import State
except Exception:
    ActionType = None
    State = object

from logger import log
from openhands_skills.expert_base import ExpertSkill

try:
    from openhands_multiagent_v2.code_intelligence import code_intelligence
except Exception:
    code_intelligence = None

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
              "backups", ".ruff_cache", "ai-env", "openbb-env"}


class LargeCodebaseMaster(ExpertSkill):
    ROLE = "codebase"
    EXPERTISE = (
        "a principal engineer expert in large-codebase architecture, refactoring, "
        "dependency analysis and technical-debt reduction"
    )

    def __init__(self):
        self.project_root = Path.cwd()

    def _tree(self, root: Path, depth: int) -> str:
        lines = []
        rootlen = len(root.parts)
        for cur, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
            level = len(Path(cur).parts) - rootlen
            if level > depth:
                dirs[:] = []
                continue
            indent = "  " * level
            lines.append(f"{indent}{Path(cur).name}/")
            for fn in sorted(files)[:40]:
                if fn.endswith((".py", ".md", ".bat", ".ps1", ".toml", ".yml", ".yaml")):
                    lines.append(f"{indent}  {fn}")
            if len(lines) > 400:
                lines.append("... (truncated)")
                break
        return "\n".join(lines)

    def map_codebase(self, depth: int = 2, root: str = None) -> str:
        """Real filesystem map + LLM architecture read."""
        base = Path(root) if root else self.project_root
        log.info(f"Mapping codebase at {base} (depth={depth})")
        tree = self._tree(base, depth)
        analysis = self.consult(
            "Given this real directory tree, describe the architecture, identify "
            "the main layers/modules, coupling risks, and concrete structural "
            f"improvements.\n\nTree:\n{tree[:6000]}"
        )
        return f"🗺️ Codebase map ({base}):\n{tree[:3000]}\n\n### Architecture analysis\n{analysis}"

    def suggest_refactoring(self, file_path: str) -> str:
        """Real analyzer findings on an actual file + LLM refactoring plan."""
        if not os.path.isfile(file_path):
            return f"{file_path}: not found."
        findings = ""
        if code_intelligence is not None:
            try:
                findings = code_intelligence.analyze_path(file_path).to_report()
            except Exception as e:
                findings = f"(analyzer error: {e})"
        try:
            code = open(file_path, encoding="utf-8", errors="replace").read()[:8000]
        except Exception as e:
            return f"{file_path}: could not read ({e})."
        plan = self.consult(
            "Propose a concrete, prioritised refactoring plan for this file. Use "
            "the analyzer findings as evidence and address the real issues.\n\n"
            f"### Analyzer findings\n{findings}\n\n### Code\n{code}"
        )
        return f"### Analyzer findings for {file_path}\n{findings}\n\n### Refactoring plan\n{plan}"

    def check_technical_debt(self, root: str = None) -> str:
        """Scan real .py files with analyzers and summarise the debt."""
        base = Path(root) if root else self.project_root
        if code_intelligence is None:
            return "code_intelligence unavailable — cannot scan technical debt."
        pyfiles, total = [], 0
        for cur, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
            for fn in files:
                if fn.endswith(".py"):
                    pyfiles.append(os.path.join(cur, fn))
        report_lines = []
        for f in pyfiles[:60]:  # bound the scan
            try:
                res = code_intelligence.analyze_path(f, types=False)
                n = len(res.issues)
                total += n
                if n:
                    report_lines.append(f"{os.path.relpath(f, base)}: {n} issue(s)")
            except Exception:
                pass
        head = f"🏗️ Technical debt: {total} analyzer findings across {len(pyfiles)} files (scanned {min(len(pyfiles),60)})."
        return head + "\n" + "\n".join(sorted(report_lines, key=lambda x: -int(x.split(":")[1].split()[0]))[:30])

    def full_architecture_audit(self, root: str = None) -> str:
        return self.map_codebase(root=root) + "\n\n" + self.check_technical_debt(root=root)


# Register skill
large_codebase = LargeCodebaseMaster()
