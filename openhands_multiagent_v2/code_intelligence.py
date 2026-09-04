"""
Code Intelligence - το "superhuman eye" των agents.

Ντετερμινιστικό static-analysis layer: τρέχει πραγματικά εργαλεία (ruff, bandit,
mypy, pyflakes, pip-audit) πάνω σε κώδικα ή αρχεία και επιστρέφει ΔΟΜΗΜΕΝΑ
findings. Αυτά τα εργαλεία πιάνουν λεπτά bugs / ευπάθειες / type errors / γνωστά
CVEs που το ανθρώπινο μάτι (και το LLM μόνο του) προσπερνά. Οι agents τα
τροφοδοτούν στο μοντέλο ώστε η ανάλυσή τους να πατάει σε αντικειμενικά δεδομένα,
όχι σε εικασίες.

Κάθε analyzer degrade-άρει χωριστά: αν λείπει ένα εργαλείο, απλά σημειώνεται
"unavailable" αντί να σπάσει το σύνολο. Portable: καλεί τα εργαλεία μέσω
`sys.executable -m <tool>`, οπότε δουλεύει όπου κι αν τρέχει ο agent process.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("code_intelligence")


@dataclass
class Issue:
    tool: str
    severity: str      # CRITICAL / HIGH / MEDIUM / LOW / INFO
    code: str          # rule id (e.g. B602, E501, F401)
    line: int
    message: str
    file: str = ""     # source file (populated on directory scans)

    def __str__(self) -> str:
        loc = f"{os.path.basename(self.file)}:" if self.file else ""
        return f"[{self.severity:<8}] {self.tool}:{self.code} {loc}L{self.line} — {self.message}"


@dataclass
class AnalysisResult:
    issues: List[Issue] = field(default_factory=list)
    tools_run: List[str] = field(default_factory=list)
    tools_skipped: List[str] = field(default_factory=list)

    def by_severity(self) -> dict:
        buckets: dict = {}
        for i in self.issues:
            buckets.setdefault(i.severity, []).append(i)
        return buckets

    def to_report(self) -> str:
        if not self.tools_run:
            return "Code intelligence: no analyzers available (install ruff/bandit/mypy)."
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        issues = sorted(self.issues, key=lambda i: (order.get(i.severity, 9), i.tool, i.line))
        head = (
            f"Ran: {', '.join(self.tools_run)}"
            + (f" | skipped: {', '.join(self.tools_skipped)}" if self.tools_skipped else "")
            + f" | {len(issues)} finding(s)"
        )
        if not issues:
            return head + "\nNo issues detected by the deterministic analyzers. ✅"
        body = "\n".join(str(i) for i in issues[:200])
        return head + "\n" + body


_TIMEOUT = 90

# Heavy dirs to keep bandit out of during whole-tree scans.
_BULK_EXCLUDE = ("*/node_modules/*,*/.venv/*,*/venv/*,*/ai-env/*,*/openbb-env/*,"
                 "*/__pycache__/*,*/backups/*,*/.git/*,*/_cleanup_quarantine_*/*")


def _run(args: List[str]) -> Optional[subprocess.CompletedProcess]:
    """Run a tool via the current interpreter; None if the tool is absent."""
    try:
        return subprocess.run(
            [sys.executable, "-m", *args],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        log.warning(f"code_intelligence: {args[0]} timed out")
        return None
    except Exception as e:
        log.warning(f"code_intelligence: {args[0]} failed: {e}")
        return None


def _has_module(name: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


class CodeIntelligence:
    """Runs deterministic analyzers and normalises their output."""

    # ------------------------------------------------------------------ #
    def analyze_path(self, path: str, *, security: bool = True,
                     types: bool = True) -> AnalysisResult:
        res = AnalysisResult()
        self._ruff(path, res)
        self._pyflakes(path, res)
        if security:
            self._bandit(path, res)
        if types:
            self._mypy(path, res)
        return res

    def analyze_code(self, code: str, *, filename: str = "snippet.py",
                     **kw) -> AnalysisResult:
        """Write a code string to a temp file and analyze it."""
        tmpdir = tempfile.mkdtemp(prefix="codeintel_")
        fpath = os.path.join(tmpdir, filename)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(code)
            return self.analyze_path(fpath, **kw)
        finally:
            try:
                os.remove(fpath)
                os.rmdir(tmpdir)
            except Exception:
                pass

    def analyze_tree(self, path: str, *, security: bool = True) -> AnalysisResult:
        """Fast whole-directory scan: ruff + bandit in ONE pass each.

        For bulk/folder analysis. ruff recurses with built-in venv excludes;
        bandit gets explicit excludes for heavy dirs. mypy/pyflakes are skipped
        here (too slow / noisy across arbitrary trees; ruff covers F-codes).
        """
        res = AnalysisResult()
        self._ruff(path, res)  # ruff auto-excludes .venv/venv/node_modules/__pycache__
        if security and _has_module("bandit"):
            p = _run(["bandit", "-r", path, "-x", _BULK_EXCLUDE, "-f", "json", "-q"])
            if p is None:
                res.tools_skipped.append("bandit")
            else:
                res.tools_run.append("bandit")
                try:
                    sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
                    for r in json.loads(p.stdout or "{}").get("results", []):
                        res.issues.append(Issue(
                            "bandit",
                            sev_map.get(r.get("issue_severity", "LOW"), "LOW"),
                            r.get("test_id", "B?"),
                            r.get("line_number", 0) or 0,
                            r.get("issue_text", ""),
                            file=r.get("filename", "") or "",
                        ))
                except Exception as e:
                    log.warning(f"bandit tree parse: {e}")
        elif security:
            res.tools_skipped.append("bandit")
        return res

    # ------------------------------------------------------------------ #
    # Individual analyzers                                               #
    # ------------------------------------------------------------------ #
    def _ruff(self, path: str, res: AnalysisResult) -> None:
        if not _has_module("ruff"):
            res.tools_skipped.append("ruff")
            return
        p = _run(["ruff", "check", "--output-format=json", "--exit-zero", path])
        if p is None:
            res.tools_skipped.append("ruff")
            return
        res.tools_run.append("ruff")
        try:
            for d in json.loads(p.stdout or "[]"):
                code = d.get("code") or "?"
                # E9xx/F82x = real errors; others style/lint
                sev = "HIGH" if str(code).startswith(("E9", "F8", "F6")) else "LOW"
                res.issues.append(Issue(
                    "ruff", sev, code,
                    (d.get("location") or {}).get("row", 0) or 0,
                    d.get("message", ""),
                    file=d.get("filename", "") or "",
                ))
        except Exception as e:
            log.warning(f"ruff parse: {e}")

    def _pyflakes(self, path: str, res: AnalysisResult) -> None:
        if not _has_module("pyflakes"):
            res.tools_skipped.append("pyflakes")
            return
        p = _run(["pyflakes", path])
        if p is None:
            res.tools_skipped.append("pyflakes")
            return
        res.tools_run.append("pyflakes")
        for line in (p.stdout or "").splitlines():
            # format: path:line:col: message  (path may contain a Windows drive)
            m = re.search(r":(\d+):(?:\d+:)?\s*(.*)$", line)
            if not m:
                continue
            res.issues.append(Issue("pyflakes", "MEDIUM", "F", int(m.group(1)),
                                    m.group(2).strip(), file=line[:m.start()]))

    def _bandit(self, path: str, res: AnalysisResult) -> None:
        if not _has_module("bandit"):
            res.tools_skipped.append("bandit")
            return
        p = _run(["bandit", "-f", "json", "-q", "-r", path])
        if p is None:
            res.tools_skipped.append("bandit")
            return
        res.tools_run.append("bandit")
        try:
            data = json.loads(p.stdout or "{}")
            sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
            for r in data.get("results", []):
                res.issues.append(Issue(
                    "bandit",
                    sev_map.get(r.get("issue_severity", "LOW"), "LOW"),
                    r.get("test_id", "B?"),
                    r.get("line_number", 0) or 0,
                    r.get("issue_text", ""),
                    file=r.get("filename", "") or "",
                ))
        except Exception as e:
            log.warning(f"bandit parse: {e}")

    def _mypy(self, path: str, res: AnalysisResult) -> None:
        if not _has_module("mypy"):
            res.tools_skipped.append("mypy")
            return
        p = _run(["mypy", "--no-error-summary", "--show-column-numbers",
                  "--ignore-missing-imports", "--no-color-output", path])
        if p is None:
            res.tools_skipped.append("mypy")
            return
        res.tools_run.append("mypy")
        for line in (p.stdout or "").splitlines():
            is_err = ": error:" in line
            if not is_err and ": warning:" not in line:
                continue
            m = re.search(r":(\d+):", line)  # drive letter "C:" has no digit after ':'
            ln = int(m.group(1)) if m else 0
            fpath = line[:m.start()] if m else ""
            sev = "HIGH" if is_err else "LOW"
            msg = line.split(": error:" if is_err else ": warning:", 1)[-1].strip()
            res.issues.append(Issue("mypy", sev, "type", ln, msg, file=fpath))

    # ------------------------------------------------------------------ #
    def audit_dependencies(self, requirements_path: str) -> str:
        """Scan a requirements file for known-vulnerable packages (CVEs)."""
        if not _has_module("pip_audit"):
            return "pip-audit unavailable (pip install pip-audit)."
        if not os.path.isfile(requirements_path):
            return f"requirements file not found: {requirements_path}"
        p = _run(["pip_audit", "-r", requirements_path, "-f", "json", "--progress-spinner", "off"])
        if p is None:
            return "pip-audit could not run."
        try:
            data = json.loads(p.stdout or "{}")
            deps = data.get("dependencies", data) if isinstance(data, dict) else data
            vulns = []
            for d in (deps or []):
                for v in d.get("vulns", []):
                    vulns.append(f"{d.get('name')}=={d.get('version')} → {v.get('id')} "
                                 f"(fix: {', '.join(v.get('fix_versions', []) or ['none'])})")
            if not vulns:
                return "pip-audit: no known vulnerabilities in the pinned dependencies. ✅"
            return "pip-audit found known CVEs:\n" + "\n".join(vulns)
        except Exception as e:
            return f"pip-audit parse error: {e}\n{(p.stdout or '')[:500]}"


# Singleton
code_intelligence = CodeIntelligence()
