"""
Self-Correcting Coder - το κλειστό loop "γράψε → ανάλυσε → διόρθωσε → ξανα-έλεγξε".

Αυτό είναι το βήμα που κάνει τους agents πραγματικά "έξυπνους": δεν βγάζουν
απλά κώδικα και τελείωσε. Ο κώδικας περνά από ντετερμινιστικούς analyzers
(ruff/bandit/mypy/pyflakes) + τον regex security scanner· όσο μένουν
HIGH/CRITICAL findings, το ίδιο το μοντέλο καλείται να τα διορθώσει με βάση τα
ΑΚΡΙΒΗ tool findings — και ξανα-ελέγχεται. Επαναλαμβάνεται μέχρι να καθαρίσει ή
να εξαντληθούν τα iterations.

Το ανθρώπινο μάτι δεν τρέχει bandit+mypy σε κάθε αναθεώρηση· αυτό το loop το
κάνει σε κάθε γύρο, οπότε συγκλίνει σε κώδικα που περνά αντικειμενικούς ελέγχους.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from logger import log
from .base_llm_agent import BaseLLMAgent
from .coder_agent_v2 import coder
from .code_intelligence import code_intelligence

try:
    from .security_agent_v2 import security
except Exception:  # pragma: no cover
    security = None

_BLOCKING = {"CRITICAL", "HIGH"}


@dataclass
class Iteration:
    n: int
    blocking: int
    total: int
    summary: str


@dataclass
class BuildResult:
    task: str
    code: str
    clean: bool
    iterations: List[Iteration] = field(default_factory=list)
    final_report: str = ""

    def to_report(self) -> str:
        status = "✅ CLEAN (analyzers satisfied)" if self.clean else "⚠️ residual findings remain"
        hist = "\n".join(
            f"  round {it.n}: {it.blocking} blocking / {it.total} total — {it.summary}"
            for it in self.iterations
        )
        # "### Final code" over a failure sentinel reads as delivered code.
        try:
            from llm_client import is_llm_error
        except Exception:  # pragma: no cover
            def is_llm_error(t):
                return not (t or "").strip() or str(t).strip().startswith("(")

        code_section = (
            f"### Final code\n{self.code}" if not is_llm_error(self.code)
            else ("### ⚠️ ΔΕΝ ΠΑΡΗΧΘΗ ΚΩΔΙΚΑΣ\nΤο μοντέλο δεν απάντησε. "
                  f"Αυτό ΔΕΝ είναι κώδικας:\n\n{self.code}")
        )
        return (
            f"Self-correcting build — {status} after {len(self.iterations)} round(s)\n"
            f"{hist}\n\n### Final analyzer report\n{self.final_report}\n\n"
            + code_section
        )


class SelfCorrectingCoder(BaseLLMAgent):
    ROLE = "self_correcting_coder"
    SYSTEM_PROMPT = (
        "You are a meticulous senior engineer fixing code to satisfy automated "
        "analyzers (ruff, bandit, mypy, pyflakes) and a security scanner. Apply "
        "the MINIMAL correct change for each reported issue without altering "
        "intended behaviour. Return the COMPLETE corrected file in one fenced "
        "code block — no commentary before or after."
    )

    def _blocking_findings(self, code: str):
        res = code_intelligence.analyze_code(code)
        blocking = [i for i in res.issues if i.severity in _BLOCKING]
        # add regex security criticals/highs the linters may miss
        sec_lines = []
        if security is not None:
            for f in security.scan_static(code):
                if f.severity in _BLOCKING:
                    sec_lines.append(f"security:{f.rule} L{f.line} {f.note}")
        return res, blocking, sec_lines

    #: Ways to make an analyzer stop complaining without fixing anything.
    _SUPPRESSORS = ("# noqa", "#noqa", "# nosec", "#nosec", "# type: ignore",
                    "#type:ignore", "# pylint: disable", "# ruff: noqa",
                    "# flake8: noqa", "# mypy: ignore-errors")

    #: Below this fraction of the previous size, a "fix" has deleted the work.
    _SHRINK_FLOOR = 0.55

    @classmethod
    def _suppression_count(cls, code: str) -> int:
        low = (code or "").lower()
        return sum(low.count(m) for m in cls._SUPPRESSORS)

    @classmethod
    def _cheated(cls, before: str, after: str):
        """Did this round silence the detector instead of fixing the code?

        The loop feeds findings back and re-analyzes. A model can clear a
        finding two ways that leave the analyzer happy and the problem intact:
        add a suppression comment, or delete the code that carried it. Either
        one produces `nblock == 0` on the next pass, and the loop then set
        clean=True and reported success.

        Returns a reason string, or None when the round looks like real work.
        """
        added = cls._suppression_count(after) - cls._suppression_count(before)
        if added > 0:
            return (f"added {added} analyzer-suppression comment(s) "
                    f"(noqa / nosec / type: ignore) instead of fixing the finding")

        before_n = len((before or "").strip())
        after_n = len((after or "").strip())
        if before_n > 200 and after_n < before_n * cls._SHRINK_FLOOR:
            pct = 100 * (1 - after_n / before_n)
            return (f"deleted {pct:.0f}% of the code ({before_n} -> {after_n} chars); "
                    f"an analyzer cannot complain about code that is gone")
        return None

    def build(self, task: str, *, language: str = "python",
              max_iterations: int = 3) -> BuildResult:
        """Generate code, then loop analyze→fix until clean or budget spent."""
        log.info(f"Self-correcting build: {task[:70]} (lang={language}, max={max_iterations})")

        raw = coder.write_or_refactor(task)
        code = self.extract_code(raw)
        result = BuildResult(task=task, code=code, clean=False)

        # Non-Python: analyzers don't apply — return the coder's output as-is.
        if language.lower() not in ("python", "py"):
            result.final_report = "(analyzer loop skipped: non-Python target)"
            result.clean = True
            result.iterations.append(Iteration(1, 0, 0, "non-python, no analyzer loop"))
            return result

        cheated_rounds = []
        for n in range(1, max_iterations + 1):
            res, blocking, sec = self._blocking_findings(code)
            total = len(res.issues) + len(sec)
            nblock = len(blocking) + len(sec)
            result.final_report = res.to_report() + (
                "\n" + "\n".join(sec) if sec else ""
            )
            result.iterations.append(Iteration(
                n, nblock, total,
                "clean" if nblock == 0 else f"{nblock} blocking to fix",
            ))

            if nblock == 0:
                result.code = code
                result.clean = not cheated_rounds
                if cheated_rounds:
                    log.warning(f"Self-correcting build: analyzers quiet after round "
                                f"{n}, but the detector was silenced, not satisfied")
                    result.final_report += (
                        "\n\n⚠️ NOT CLEAN — the analyzers stopped complaining because "
                        "the detector was silenced, not because the code was fixed:\n  "
                        + "\n  ".join(cheated_rounds)
                        + "\nRead the code before trusting this build."
                    )
                else:
                    log.info(f"Self-correcting build clean after round {n}")
                return result

            # Feed the EXACT findings back and ask for a minimal fix.
            findings_txt = "\n".join(str(i) for i in blocking) + \
                ("\n" + "\n".join(sec) if sec else "")
            fixed = self.complete(
                "The following analyzer/security findings must be fixed in the "
                f"code below.\n\n### Findings\n{findings_txt}\n\n### Code\n{code}"
            )
            new_code = self.extract_code(fixed)
            cheat = self._cheated(code, new_code)
            if cheat:
                log.warning(f"Self-correcting build round {n}: {cheat}")
                cheated_rounds.append(f"round {n}: {cheat}")
            code = new_code
            result.code = code

        # Final re-check after the last fix.
        res, blocking, sec = self._blocking_findings(code)
        result.final_report = res.to_report() + ("\n" + "\n".join(sec) if sec else "")
        analyzers_happy = (len(blocking) + len(sec)) == 0

        # An analyzer that was silenced is not an analyzer that passed.
        result.clean = analyzers_happy and not cheated_rounds
        # Reported whether or not the analyzers ended up happy. An attempt to
        # silence the detector is worth knowing about even when some OTHER
        # finding kept the build from passing anyway.
        if cheated_rounds:
            result.final_report += (
                "\n\n⚠️ NOT CLEAN — the analyzers stopped complaining because the "
                "detector was silenced, not because the code was fixed:\n  "
                + "\n  ".join(cheated_rounds)
                + "\nRead the code before trusting this build."
            )
        return result


# Register
self_correcting_coder = SelfCorrectingCoder()
