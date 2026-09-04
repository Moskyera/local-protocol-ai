"""
Security Auditor Skill for OpenHands
Professional Security Auditor for production websites.
Focus: OWASP Top 10, secure coding audits, authentication/authorization hardening, vulnerability assessment, penetration testing mindset, data protection in transit/rest, API security.
For serious client work where security is non-negotiable.
"""

from logger import log
from typing import Dict, Any

from openhands_skills.expert_base import ExpertSkill

try:
    from llm_client import is_usable
except Exception:  # pragma: no cover - llm_client is always present in-tree
    def is_usable(text):
        return bool((text or "").strip()) and not str(text).startswith("(")

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class SecurityAuditor(ExpertSkill):
    """Senior security reviewer for the user's own web work.

    This class used to return the SAME five hardcoded lists for every input.
    `task` was used for one log line and nothing else, so "audit my login flow"
    and "audit my checkout" produced byte-identical output — and the caller
    filed it under `security_auditor` and called it an audit. A checklist that
    never looked at the code is a reference card, not a review, and presenting
    one as the other is how a real hole gets signed off.

    The static lists are kept, because they are genuinely useful reference
    material — but they are now named for what they are, and the actual review
    of the task is done by the model, like every other working expert here.
    """

    ROLE = "security_auditor"
    EXPERTISE = (
        "a senior application security engineer who reviews web applications: "
        "authentication and session handling, access control, injection, secrets "
        "handling, transport security, and dependency risk"
    )
    RULES = (
        "Review THIS task and nothing else. Name concrete weaknesses you can "
        "actually see in what you were given, and say which OWASP category each "
        "one falls under. If the input does not contain enough to judge "
        "something, say so plainly instead of guessing. Do not pad the answer "
        "with generic advice that applies to every application. If you see "
        "nothing wrong, say that."
    )
    DEFAULT_TEMPERATURE = 0.2

    def __init__(self):
        self.focus = "Protecting professional websites and user data with rigorous security practices and audits."

    def audit_security(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full security audit + hardening plan + secure implementation specs."""
        log.info(f"SecurityAuditor: Auditing security for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " web security 2026", "OWASP secure coding and web app security best practices")
            except Exception:
                pass

        # The actual review of THIS task. Everything below it is reference
        # material that is identical for every input, and is now labelled so.
        review = self.consult(task, context=context or None)
        reviewed = is_usable(review)

        result = {
            "task": task,
            "review": review,
            "review_is_real": reviewed,
            "status": "reviewed" if reviewed else "not_reviewed",
            "reference_only": (
                "Every key below is fixed reference material. It is NOT a finding "
                "about this task and does not depend on the input."
            ),
            "owasp_top10_reference_checklist": self.owasp_top10_checklist(),
            "secure_coding_reference_guidelines": self.secure_coding_guidelines(),
            "auth_hardening_reference": self.auth_hardening(),
            "api_security_reference": self.api_security(),
            "data_protection_reference": self.data_protection(),
            "vulnerability_assessment_reference_process": self.vulnerability_assessment_process(),
            "research": research[:1200] if research else "2026 OWASP, CWE, and modern web security standards."
        }
        if not reviewed:
            result["warning"] = (
                "The model did not return a usable review, so this output is "
                "reference material only. It is not an audit of your code."
            )

        if persistent_memory:
            try:
                persistent_memory.store_learning("security:audit", f"{task} | professional security audit and hardening for client work")
            except Exception:
                pass

        print("🔒 SecurityAuditor: " + ("task reviewed + reference material attached."
                                         if reviewed else
                                         "REVIEW FAILED — reference material only, this is not an audit."))
        return result

    def owasp_top10_checklist(self) -> list:
        return [
            "A01:2021 – Broken Access Control",
            "A02:2021 – Cryptographic Failures",
            "A03:2021 – Injection (SQL, XSS, etc.)",
            "A04:2021 – Insecure Design",
            "A05:2021 – Security Misconfiguration",
            "A06:2021 – Vulnerable and Outdated Components",
            "A07:2021 – Identification and Authentication Failures",
            "A08:2021 – Software and Data Integrity Failures",
            "A09:2021 – Security Logging and Monitoring Failures",
            "A10:2021 – Server-Side Request Forgery (SSRF)"
        ]

    def secure_coding_guidelines(self) -> list:
        return [
            "Input validation & sanitization on all user data (never trust client)",
            "Parameterized queries / ORM to prevent injection",
            "Output encoding to prevent XSS",
            "Use secure headers (CSP, HSTS, X-Frame-Options, etc.)",
            "Least privilege principle for all services and DB users",
            "Regular dependency scanning (Dependabot + Snyk or equivalent)"
        ]

    def auth_hardening(self) -> list:
        return [
            "MFA / 2FA for all admin and sensitive accounts",
            "Strong password policies + password hashing (Argon2id or bcrypt)",
            "Secure session management (httpOnly, Secure, SameSite flags)",
            "JWT best practices: short expiry, refresh tokens, signing algorithms",
            "Rate limiting on login / auth endpoints",
            "Account lockout and breach detection"
        ]

    def api_security(self) -> list:
        return [
            "OAuth2 / OpenID Connect for authentication",
            "API rate limiting, throttling, and quotas",
            "Input validation on all endpoints (Zod / Pydantic / etc.)",
            "CORS properly configured (never *)",
            "API versioning and deprecation strategy",
            "Regular API security testing (e.g., with Postman + scripts or dedicated tools)"
        ]

    def data_protection(self) -> list:
        return [
            "TLS 1.3 everywhere (in transit)",
            "Encryption at rest for sensitive data (AES-256+)",
            "Minimize PII collection and retention",
            "Secure key management (HSM or cloud KMS, never in code)",
            "Regular data classification and DLP policies"
        ]

    def vulnerability_assessment_process(self) -> list:
        return [
            "Automated SAST/DAST in CI (Semgrep, SonarQube, ZAP, etc.)",
            "Dependency vulnerability scanning on every build",
            "Regular manual/automated penetration testing (at least annually or per major release)",
            "Bug bounty or responsible disclosure program for production sites",
            "Incident response plan with clear escalation"
        ]

# Register
security_auditor = SecurityAuditor()
print("🔒 SecurityAuditor registered. Ready for sub_type='security'. Non-negotiable for serious production work.")