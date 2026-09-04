"""
PR Review + Triage Expert Skill v4.

Πραγματικό πλέον: delegates σε reviewer + security agents (που τρέχουν
ruff/bandit/mypy + LLM) αντί να επιστρέφει hardcoded "Overall Score: 8.9/10".
Κρατά τα method names (review_pr / triage_issue / full_security_audit).
"""

from logger import log
from openhands_skills.expert_base import ExpertSkill

try:
    from openhands_multiagent_v2.reviewer_agent_v2 import reviewer as _reviewer
except Exception:
    _reviewer = None

try:
    from openhands_multiagent_v2.security_agent_v2 import security as _security
except Exception:
    _security = None


class PRReviewExpert(ExpertSkill):
    ROLE = "pr_review"
    EXPERTISE = (
        "a staff engineer performing rigorous pull-request review and issue triage"
    )

    def review_pr(self, pr_description: str, changed_files: list = None,
                  diff: str = None) -> str:
        """Review a PR — or say why it could not be reviewed.

        The read loop ended in `except Exception: pass`. Every unreadable file
        was skipped in silence, and if ALL of them failed — a wrong path, a
        permissions problem, a branch that was never checked out — `body`
        stayed empty and `material` was reduced to "PR: <description>". The
        reviewer then produced a confident review of the description alone,
        with nothing in the output to say that not one line of code had been
        read.

        full_security_audit, twenty lines below, already did this correctly:
        it appends "(could not read: ...)" per file. This is the same shape.
        """
        log.info(f"PR Review started for: {pr_description}")
        body = diff or ""
        unreadable = []
        read_count = 0

        if not body and changed_files:
            for fp in changed_files[:10]:
                try:
                    body += (f"\n\n# FILE: {fp}\n"
                             + open(fp, encoding="utf-8", errors="replace").read())
                    read_count += 1
                except Exception as e:
                    unreadable.append(f"{fp} ({type(e).__name__}: {str(e)[:80]})")
                    log.warning(f"PR review: could not read {fp}: {e}")

        # Nothing to review is not a review.
        if not body.strip():
            asked_for = len(changed_files or [])
            return (
                "❌ ΔΕΝ έγινε review: δεν διαβάστηκε ούτε ένα αρχείο.\n\n"
                + (f"Ζητήθηκαν {asked_for} αρχεία και απέτυχαν όλα:\n  - "
                   + "\n  - ".join(unreadable) + "\n\n"
                   if unreadable else
                   "Δεν δόθηκε diff ούτε λίστα αρχείων.\n\n")
                + "Η περιγραφή του PR από μόνη της δεν είναι κώδικας, και μια "
                  "κρίση πάνω της θα ήταν εικασία."
            )

        material = f"PR: {pr_description}\n\n{body}".strip()
        review = (_reviewer.review(material) if _reviewer is not None
                  else self.consult(f"Review this pull request thoroughly:\n\n{material}"))

        # A partial read is still a review, but the reader must know its scope.
        if unreadable:
            review += ("\n\n⚠️ Το review καλύπτει "
                       f"{read_count} από {read_count + len(unreadable)} αρχεία. "
                       "ΔΕΝ διαβάστηκαν:\n  - " + "\n  - ".join(unreadable))
        return review

    def triage_issue(self, issue_title: str, issue_body: str) -> str:
        log.info(f"Triage issue: {issue_title}")
        return self.consult(
            "Triage this issue: assign a priority (P0-P3) with justification, a "
            "type (bug/feature/chore/security), suggested labels, likely root-cause "
            "area, and a concrete first action.\n\n"
            f"Title: {issue_title}\n\nBody: {issue_body}",
            temperature=0.2, max_tokens=1500,
        )

    def full_security_audit(self, files: list) -> str:
        log.info("Running full security audit")
        if _security is None:
            return "Security agent unavailable."
        reports = []
        for fp in (files or [])[:10]:
            try:
                code = open(fp, encoding="utf-8", errors="replace").read()
                reports.append(f"### {fp}\n" + _security.audit(code))
            except Exception as e:
                reports.append(f"### {fp}\n(could not read: {e})")
        return "\n\n".join(reports) if reports else "No files provided to audit."


# Register skill
pr_expert = PRReviewExpert()
