"""
Security & Compliance Guardian Skill.

Πραγματικό πλέον: το scan_for_secrets τρέχει τον ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΟ scanner
(regex + bandit μέσω code_intelligence) σε πραγματικό αρχείο, αντί να τυπώνει
πάντα "No secrets found". Το check_compliance/full_audit δίνουν πραγματική
αξιολόγηση μέσω του security agent.
"""

import os

try:  # opendevin optional — degrade gracefully
    from opendevin.core.schema import ActionType
except Exception:
    ActionType = None

try:
    from openhands_multiagent_v2.security_agent_v2 import security as _security_agent
except Exception:
    _security_agent = None

try:
    from openhands_multiagent_v2.code_intelligence import code_intelligence
except Exception:
    code_intelligence = None


class SecurityGuardian:
    def scan_for_secrets(self, file_path: str) -> str:
        """Real secret/vuln scan on an actual file (regex + bandit)."""
        if not os.path.isfile(file_path):
            return f"🔒 {file_path}: file not found — cannot scan."
        try:
            code = open(file_path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            return f"🔒 {file_path}: could not read ({e})."

        parts = [f"🔒 Security scan: {file_path}"]
        if _security_agent is not None:
            findings = _security_agent.scan_static(code)
            if findings:
                parts.append(f"{len(findings)} regex finding(s):")
                parts += [f"  {f}" for f in findings]
            else:
                parts.append("No regex-pattern secrets/issues found.")
        if code_intelligence is not None:
            try:
                parts.append(code_intelligence.analyze_code(
                    code, security=True, types=False,
                    filename=os.path.basename(file_path),
                ).to_report())
            except Exception as e:
                parts.append(f"(SAST tool error: {e})")
        return "\n".join(parts)

    def check_compliance(self, target: str = "", context: dict = None) -> str:
        """Real compliance review via the security expert."""
        if _security_agent is None:
            return "Security agent unavailable — cannot run compliance review."
        prompt = (
            "Review this code/component for security & compliance best practices: "
            "secrets handling, logging of sensitive data, input validation, error "
            "handling, rate limiting, and dependency risk. List concrete gaps with "
            f"severity and fixes.\n\n{target}"
        )
        return _security_agent.complete(prompt)

    def full_security_audit(self, files=None) -> str:
        """Scan a set of real files (defaults to common config files)."""
        files = files or ["config.py", ".env"]
        reports = [self.scan_for_secrets(f) for f in files if f]
        return "\n\n".join(reports) if reports else "No files to audit."


# Register
security_guardian = SecurityGuardian()
