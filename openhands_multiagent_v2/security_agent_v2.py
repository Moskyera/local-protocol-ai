"""
Security Agent v2 - ΝΕΟΣ. Application security / SAST-style review.

Δεν υπήρχε security agent στο σύστημα. Αυτός συνδυάζει:
  1. Έναν γρήγορο, ντετερμινιστικό static scanner (regex heuristics) που πιάνει
     τα κλασικά (hardcoded secrets, eval/exec, shell=True, SQL concatenation,
     ανασφαλές deserialization, weak crypto κ.λπ.) — μηδέν εξάρτηση από LLM.
  2. Ένα βαθύ LLM-based audit (threat modelling, logic flaws, authz, injection)
     μέσω του τοπικού μοντέλου.
  3. Ειδικό Solidity/DeFi audit (reentrancy, oracle, access control) όταν
     ανιχνεύεται smart-contract κώδικας.

Χρήση:
    from openhands_multiagent_v2 import security
    print(security.audit(code))              # πλήρες report (static + LLM)
    findings = security.scan_static(code)    # μόνο τα ντετερμινιστικά findings
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from logger import log
from .base_llm_agent import BaseLLMAgent

try:
    from openhands_skills.solidity_expert import solidity_expert
except Exception:  # pragma: no cover
    solidity_expert = None

try:
    from .code_intelligence import code_intelligence
except Exception:  # pragma: no cover
    code_intelligence = None


@dataclass
class Finding:
    severity: str          # CRITICAL / HIGH / MEDIUM / LOW
    rule: str
    line: int
    snippet: str
    note: str = ""

    def __str__(self) -> str:
        return f"[{self.severity}] L{self.line} {self.rule}: {self.note}\n    -> {self.snippet.strip()[:160]}"


# Deterministic, language-agnostic-ish heuristics. Intentionally conservative:
# each pattern is a well-known real risk, not style noise. (rule, regex, severity, note)
_STATIC_RULES = [
    ("hardcoded-secret", re.compile(r"""(?i)(api[_-]?key|secret|passwd|password|token|private[_-]?key)\s*[:=]\s*['"][^'"\n]{8,}['"]"""),
     "HIGH", "Possible hardcoded secret/credential — move to env/secret manager."),
    ("aws-key", re.compile(r"AKIA[0-9A-Z]{16}"),
     "CRITICAL", "Looks like an AWS access key ID."),
    ("python-eval-exec", re.compile(r"\b(eval|exec)\s*\("),
     "HIGH", "Dynamic eval/exec — arbitrary code execution risk if input is untrusted."),
    ("shell-injection", re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
     "HIGH", "subprocess with shell=True — command injection risk with untrusted input."),
    ("os-system", re.compile(r"\bos\.system\s*\("),
     "MEDIUM", "os.system with a built command — prefer subprocess with an arg list."),
    ("pickle-load", re.compile(r"\bpickle\.loads?\s*\("),
     "HIGH", "Unsafe deserialization (pickle) — RCE on malicious input."),
    ("yaml-unsafe", re.compile(r"yaml\.load\s*\((?![^)]*Loader)"),
     "MEDIUM", "yaml.load without SafeLoader — use yaml.safe_load."),
    ("sql-fstring", re.compile(r"""(?i)(execute|executemany)\s*\(\s*f?['"].*(select|insert|update|delete).*(\{|\+|%)"""),
     "HIGH", "SQL built via f-string/concat — use parameterised queries."),
    ("weak-hash", re.compile(r"hashlib\.(md5|sha1)\s*\("),
     "MEDIUM", "Weak hash (md5/sha1) — use sha256+ / bcrypt/argon2 for passwords."),
    ("verify-false", re.compile(r"verify\s*=\s*False"),
     "HIGH", "TLS verification disabled (verify=False) — MITM risk."),
    ("debug-true", re.compile(r"(?i)debug\s*=\s*True"),
     "LOW", "Debug mode enabled — ensure it is off in production."),
    ("jwt-none", re.compile(r"""(?i)algorithm[s]?\s*[:=]\s*['"]?none['"]?"""),
     "CRITICAL", "JWT 'none' algorithm — signature bypass."),
]


class SecurityAgent(BaseLLMAgent):
    ROLE = "security"
    DEFAULT_TEMPERATURE = 0.1  # security wants determinism, not creativity
    DEFAULT_MAX_TOKENS = 6144
    SYSTEM_PROMPT = (
        "You are a senior application security engineer performing a code audit. "
        "Identify real, exploitable vulnerabilities. For each: give an OWASP/CWE "
        "category, severity (Critical/High/Medium/Low), the vulnerable location, a "
        "concrete exploit scenario, and a specific remediation with corrected "
        "code. Consider: injection (SQL/command/template), authn/authz flaws, "
        "insecure deserialization, secrets management, SSRF, path traversal, "
        "crypto misuse, race conditions, and unsafe defaults. Report ONLY genuine "
        "issues — if the code is safe, say so and explain why. End with a one-line "
        "risk verdict: SAFE / NEEDS-FIXES / DANGEROUS."
    )

    # ------------------------------------------------------------------ #
    def scan_static(self, code: str) -> List[Finding]:
        """Fast deterministic pass. Never touches the LLM."""
        findings: List[Finding] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            for rule, rx, sev, note in _STATIC_RULES:
                if rx.search(line):
                    findings.append(Finding(sev, rule, i, line, note))
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda f: order.get(f.severity, 9))
        return findings

    def _static_report(self, code: str) -> str:
        findings = self.scan_static(code)
        if not findings:
            return "Static scan: no obvious pattern-based issues found."
        head = f"Static scan: {len(findings)} potential issue(s):"
        return head + "\n" + "\n".join(str(f) for f in findings)

    # ------------------------------------------------------------------ #
    def audit(self, code: str) -> str:
        """Full audit: deterministic static scan + deep LLM review (+ Solidity)."""
        log.info("Security Agent v2: running static scan + LLM audit")

        static = self._static_report(code)

        # Deterministic SAST via real tools (bandit) — the "superhuman eye".
        tool_report = "Code intelligence: unavailable."
        if code_intelligence is not None:
            try:
                tool_report = code_intelligence.analyze_code(
                    code, security=True, types=False
                ).to_report()
            except Exception as e:
                tool_report = f"Code intelligence error: {e}"

        llm = self.complete(
            "Perform a security audit of the following code. A fast regex scanner "
            "AND a real SAST toolchain (bandit) already reported the items below — "
            "confirm/deny each, then find what they missed (logic/authz/"
            "business-flaw issues that tools cannot see).\n\n"
            f"### Regex scanner\n{static}\n\n### SAST tools\n{tool_report}\n\n### Code\n{code}"
        )

        # The first two sections are deterministic and always real. The third
        # is the model's, and its heading must not claim an audit that did not
        # happen — this is a security report.
        report = (
            f"### 🔒 Regex scan (deterministic)\n{static}\n\n"
            f"### 🔬 SAST toolchain (bandit/ruff)\n{tool_report}\n\n"
            + self.section("🔒 Deep security audit (LLM)", llm)
        )

        if solidity_expert is not None and self.looks_like_solidity(code):
            log.info("Security Agent v2: adding Solidity/DeFi audit")
            chain = self.target_chain(code)
            sol = solidity_expert.audit_solidity(code, target_chain=chain)
            report += f"\n\n### 🔷 Solidity / DeFi audit\n{sol}"

        return report


# Register
security = SecurityAgent()
