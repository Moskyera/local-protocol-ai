"""
Hyper-Adaptive Evolution Agent v2.1 - Ο Αυτο-Εξελισσόμενος Υπεράνθρωπος
Με Persistent Memory + Vector Database

Now with initial guarded RSI support (propose-on-branch style) as part of the supervisor-driven Engineering specialist.
"""

from logger import log
from openhands_skills.persistent_memory import persistent_memory
import io
import json
import os
from datetime import datetime

# Use the single source of truth for all guards across the 3-agent system
try:
    from openhands_skills.guards import (
        FORBIDDEN_PATHS,
        is_forbidden_path as _is_forbidden_path,
        validate_proposal,
        enforce_guard,
        get_forbidden_paths,
        test_proposal_safety,
        log_security_violation,
    )
except Exception:
    FORBIDDEN_PATHS = ["telegram_engine.py", "master_market_brain.py", "geopolitical_engine.py",
                       "corporate_news_engine.py", "send_briefing.bat", "send_simplex_briefing.py",
                       "briefing", "daily_report"]
    def _is_forbidden_path(p): 
        pl = (p or "").lower()
        return any(f.lower() in pl for f in FORBIDDEN_PATHS)
    # FAIL CLOSED. These two used to return True for everything when guards.py
    # could not be imported: validate_proposal -> (True, "fallback") and
    # test_proposal_safety -> {"passed": True, "violations": []}. Proven by
    # simulating the ImportError — a proposal targeting telegram_engine.py was
    # validated and passed its safety test, and only the path list below
    # happened to catch it. The same fallback in langgraph_orchestrator was
    # fixed on 2026-09-03; this copy was missed.
    #
    # A gate that cannot say no is not a gate.
    _GUARDS_DOWN = "guards module unavailable — refusing (fallback)"

    def validate_proposal(p):
        log.error("GUARDS UNAVAILABLE: refusing proposal %s", str(p)[:120])
        return False, _GUARDS_DOWN, p

    def enforce_guard(p):
        raise RuntimeError(_GUARDS_DOWN)

    def get_forbidden_paths(): return list(FORBIDDEN_PATHS)

    def test_proposal_safety(p):
        return {"passed": False, "violations": [_GUARDS_DOWN], "checked_target": "",
                "sanitized_proposal": p, "guard_version": "fallback-fail-closed"}

    def log_security_violation(p, context=""):
        log.error("SECURITY VIOLATION (guards down): %s %s", str(p)[:120], context)
        return None

class HyperAdaptiveEvolutionAgent:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.evolution_file = os.path.join(base_dir, "memory", "hyper_evolution.json")
        self.proposals_dir = os.path.join(base_dir, "memory", "pending_proposals")
        os.makedirs(self.proposals_dir, exist_ok=True)

    def evolve(self, user_input: str, system_response: str):
        """Record an interaction. Recording is not improving.

        Every entry used to carry evolution_note = "New pattern detected -
        system improved". Measured on the real log: 27 entries, 27 identical
        notes. Nothing detected a pattern and nothing measured an improvement;
        the sentence was a constant, and a constant that claims progress is
        worse than no note at all, because it reads as evidence.

        What is recorded now is what is observable: how long the exchange was,
        and whether the response was a real answer, a failure sentinel or a
        draft. Whether the system improved is not knowable from one interaction
        and is no longer asserted.
        """
        log.info("Hyper-Adaptive Evolution Agent: recording interaction")

        try:
            from llm_client import is_llm_error, is_llm_draft
        except Exception:  # pragma: no cover
            def is_llm_error(t):
                return not (t or "").strip() or str(t).strip().startswith("(")

            def is_llm_draft(t):
                return False

        resp = system_response or ""
        if is_llm_error(resp):
            quality = "failed"
        elif is_llm_draft(resp):
            quality = "draft_only"
        else:
            quality = "answered"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "system_response": system_response,
            "response_quality": quality,
            "input_chars": len(user_input or ""),
            "response_chars": len(resp),
            "note": "Interaction recorded. This is a log entry, not evidence of improvement.",
        }

        persistent_memory.store(
            text=f"Input: {user_input}\nResponse: {system_response}",
            metadata={"type": "evolution", "timestamp": entry["timestamp"],
                      "response_quality": quality},
        )

        # The old fallback was a bare `except:` that rewrote the whole file with
        # a single entry — so one unreadable read destroyed the entire history,
        # silently, and the next run looked like a fresh start. History is never
        # discarded now: an unreadable file is moved aside first.
        data = []
        try:
            with open(self.evolution_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            data = loaded if isinstance(loaded, list) else []
        except FileNotFoundError:
            data = []
        except Exception as e:
            broken = self.evolution_file + ".corrupt"
            try:
                os.replace(self.evolution_file, broken)
                log.error(f"Evolution log unreadable ({e}); moved to {broken} "
                          f"rather than overwritten. Starting a new log.")
            except Exception as move_err:
                log.error(f"Evolution log unreadable ({e}) and could not be "
                          f"preserved ({move_err}); refusing to overwrite it.")
                return ("Evolution NOT recorded: the log is unreadable and could "
                        "not be backed up, so it was left untouched.")
            data = []

        data.append(entry)
        with open(self.evolution_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"🧬 Interaction recorded ({quality}, {len(data)} entries in the log). "
              f"Recorded, not learned — improvement is measured elsewhere.")
        return f"Interaction recorded ({quality}). Log now holds {len(data)} entries."

    def guarded_propose(self, proposals: list, originating_task: str = "") -> dict:
        """
        Professional guarded propose-on-branch.
        Uses the central guards.py for validation.
        Writes rich pending_proposal_*.json files (human gate + audit trail).
        Never applies changes itself.
        """
        log.info("Hyper-Adaptive Evolution: Guarded propose phase (central guards)")

        accepted = []
        rejected = []
        safety_failures = 0

        for raw_p in proposals:
            allowed, reason, sanitized = validate_proposal(raw_p)
            safety = test_proposal_safety(raw_p)

            if not allowed or _is_forbidden_path(str(raw_p)) or not safety.get("passed"):
                if not safety.get("passed"):
                    safety_failures += 1
                    log_security_violation(raw_p, context="guarded_propose safety test failed")
                rejected.append({
                    "proposal": raw_p,
                    "reason": reason or "FORBIDDEN_PATH - strictly blocked (Telegram/briefings or outside allowed roots).",
                    "safety_report": safety
                })
                continue

            # Richer record for serious use
            proposal_id = f"proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(accepted)}"
            proposal_file = os.path.join(self.proposals_dir, f"{proposal_id}.json")

            proposal_record = {
                "id": proposal_id,
                "timestamp": datetime.now().isoformat(),
                "originating_task": originating_task,
                "proposal": sanitized,
                "status": "PENDING_HUMAN_APPROVAL",
                "guard_validation": {"allowed": True, "reason": reason},
                "human_action_required": [
                    "1. Review this file carefully.",
                    "2. git checkout -b evolution/<short-desc>",
                    "3. Implement only the suggested change (prefer search_replace or manual edit on allowed file).",
                    "4. Run relevant tests / automation_examples / supervisor examples.",
                    "5. Only after verification: git add + commit. Optionally call a future apply_proposal()."
                ],
                "forbidden_note": "Any edit touching FORBIDDEN_PATHS is an immediate policy violation.",
            }

            try:
                with open(proposal_file, "w", encoding="utf-8") as f:
                    json.dump(proposal_record, f, indent=2, ensure_ascii=False)
                accepted.append({
                    "id": proposal_id,
                    "pending_file": proposal_file,
                    "sanitized_proposal": sanitized,
                })
            except Exception as e:
                rejected.append({"proposal": sanitized, "reason": f"Write failed: {e}"})

        result = {
            "accepted_proposals": accepted,
            "rejected_proposals": rejected,
            "safety_failures": safety_failures,
            "human_gate": "Pending proposals written to memory/pending_proposals/. Human review + git branch + tests required before any apply.",
            "next_steps": "git checkout -b evolution/xxx ; inspect the json ; make the minimal safe change ; test ; commit only if it improves metrics.",
            "forbidden_paths": get_forbidden_paths(),
        }

        persistent_memory.store(
            text=f"Guarded RSI proposals (central guard + safety tests): {originating_task}. Accepted={len(accepted)} Rejected={len(rejected)} SafetyFails={safety_failures}",
            metadata={
                "type": "guarded_rsi_proposal",
                "timestamp": datetime.now().isoformat(),
                "accepted": len(accepted),
                "rejected": len(rejected),
                "safety_failures": safety_failures
            }
        )

        print(f"🛡️ Guarded RSI: {len(accepted)} proposals filed safely. {len(rejected)} rejected. {safety_failures} failed extra safety tests.")
        return result

    # Rollback fires when the evolution score drops below 50. The old scorer
    # could not produce a number below 50 for any well-formed proposal: a
    # rationale was worth +25, priority "high" +30, "applied" +15 — 70 points
    # before a single line of the result was looked at. Every input came from
    # the proposal's own advertising copy. A change that broke the repo outright
    # scored 70 and was kept, because nothing in the score could ever notice.
    #
    # Provenance is still tracked, but it is now capped at 25 — deliberately
    # below the rollback threshold, so it can never on its own keep a bad change
    # alive. The rest of the score comes from measuring the repo.

    PROVENANCE_CAP = 25

    def _measure_health(self, target_file: str = None, timeout: int = 420) -> dict:
        """Facts about the repo as it stands right now, not claims about it."""
        import re as _re
        import subprocess as _sp
        import sys as _sys

        out = {"measured": False, "test_failures": None, "test_passed": None,
               "undefined_names": None, "syntax_ok": None, "detail": ""}

        if target_file and os.path.exists(target_file):
            try:
                import ast as _ast
                _ast.parse(io.open(target_file, encoding="utf-8").read())
                out["syntax_ok"] = True
            except SyntaxError as e:
                out["syntax_ok"] = False
                out["detail"] += f"syntax error in {target_file}: {e}; "
            except Exception:
                pass

            try:
                r = _sp.run([_sys.executable, "-m", "pyflakes", target_file],
                            capture_output=True, text=True, timeout=120)
                out["undefined_names"] = r.stdout.count("undefined name")
            except Exception as e:
                out["detail"] += f"pyflakes unavailable: {e}; "

        try:
            r = _sp.run([_sys.executable, "-m", "pytest", "-q", "--no-header", "-p",
                         "no:cacheprovider", "tests/"],
                        capture_output=True, text=True, timeout=timeout)
            tail = (r.stdout or "") + (r.stderr or "")
            m_f = _re.search(r"(\d+) failed", tail)
            m_p = _re.search(r"(\d+) passed", tail)
            out["test_failures"] = int(m_f.group(1)) if m_f else (0 if m_p else None)
            out["test_passed"] = int(m_p.group(1)) if m_p else None
            out["measured"] = out["test_failures"] is not None
        except Exception as e:
            out["detail"] += f"pytest not run: {e}; "

        return out

    def compute_evolution_score(self, proposal: dict, apply_report: dict,
                                baseline: dict = None, after: dict = None) -> dict:
        """Score an apply by what it did to the repo, not by what it claimed.

        `baseline` is a _measure_health() taken before the edit. Without one
        there is nothing to compare against, and the score is None — which the
        rollback path treats as "unconfirmed", not as "fine".
        """
        provenance, reasons = 0, []

        if proposal.get("rationale") or proposal.get("source"):
            provenance += 10
            reasons.append("Grounded in recent research")
        prio = str(proposal.get("priority", "")).lower()
        if "high" in prio:
            provenance += 10
            reasons.append("High priority from research")
        elif "medium" in prio:
            provenance += 5
        if "market" in str(proposal).lower():
            provenance += 5
            reasons.append("Market-aware improvement")
        provenance = min(self.PROVENANCE_CAP, provenance)

        target = proposal.get("target_file") or (apply_report.get("edit_result") or {}).get("target_file")
        applied = bool(apply_report.get("applied"))

        if not applied:
            return {"score": None, "measured": False, "provenance_points": provenance,
                    "reasons": reasons + ["Not applied — nothing to measure"],
                    "proposal_id": apply_report.get("id"),
                    "timestamp": datetime.now().isoformat(), "target": target}

        if after is None:
            after = self._measure_health(target)

        if not baseline or not baseline.get("measured") or not after.get("measured"):
            record = {"score": None, "measured": False, "provenance_points": provenance,
                      "reasons": reasons + ["No usable before/after measurement — score withheld"],
                      "health_after": after, "health_before": baseline,
                      "proposal_id": apply_report.get("id"),
                      "timestamp": datetime.now().isoformat(), "target": target}
            self._store_score(record)
            return record

        outcome = 50
        if after.get("syntax_ok") is False:
            outcome = 0
            reasons.append("The edited file no longer parses")
        else:
            d_fail = (after["test_failures"] or 0) - (baseline["test_failures"] or 0)
            if d_fail > 0:
                outcome = 0
                reasons.append(f"{d_fail} test(s) that passed before now fail")
            elif d_fail < 0:
                outcome = 75
                reasons.append(f"{-d_fail} previously failing test(s) now pass")
            else:
                reasons.append("No test regressed")

            b_und, a_und = baseline.get("undefined_names"), after.get("undefined_names")
            if b_und is not None and a_und is not None and a_und > b_und:
                outcome = 0
                reasons.append(f"{a_und - b_und} new undefined name(s) introduced")

        record = {
            "score": min(100, max(0, provenance + outcome)),
            "measured": True,
            "provenance_points": provenance,
            "outcome_points": outcome,
            "reasons": reasons,
            "health_before": baseline,
            "health_after": after,
            "proposal_id": apply_report.get("id"),
            "timestamp": datetime.now().isoformat(),
            "target": target,
        }
        self._store_score(record)
        return record

    def _store_score(self, record: dict) -> None:
        try:
            persistent_memory.store(
                text=f"Evolution score {record.get('score')}/100 for {record.get('proposal_id')} "
                     f"(measured={record.get('measured')})",
                metadata={"type": "evolution_score",
                          **{k: v for k, v in record.items()
                             if isinstance(v, (str, int, float, bool)) or v is None}},
            )
        except Exception:
            pass

    def apply_proposal(self, proposal_id: str, dry_run: bool = True, force: bool = False, fuzzy: bool = False) -> dict:
        """
        Safe apply for a pending proposal (the closing of the guarded RSI loop).
        - Re-loads the pending json from memory/pending_proposals/
        - Re-runs all central guards + safety tests (defense in depth).
        - Uses perform_guarded_edit (dry_run by default).
        - Only applies on allowed paths.
        - On success (non-dry): moves the file to applied/ or marks status.
        - Returns full audit report.
        """
        log.info(f"Hyper-Adaptive Evolution: apply_proposal {proposal_id} (dry_run={dry_run})")

        proposal_file = os.path.join(self.proposals_dir, f"{proposal_id}.json")
        if not os.path.exists(proposal_file):
            return {"success": False, "reason": "Proposal file not found", "id": proposal_id}

        try:
            with open(proposal_file, "r", encoding="utf-8") as f:
                record = json.load(f)
        except Exception as e:
            return {"success": False, "reason": f"Failed to read proposal: {e}", "id": proposal_id}

        proposal = record.get("proposal", {})
        target_file = proposal.get("target_file") or proposal.get("apply_data", {}).get("file")

        if not target_file:
            return {"success": False, "reason": "No target_file in proposal", "id": proposal_id}

        # Re-validate hard (defense in depth)
        allowed, reason, sanitized = validate_proposal(proposal)
        safety = test_proposal_safety(proposal)

        if not allowed or not safety.get("passed"):
            log_security_violation(proposal, context=f"apply_proposal {proposal_id} blocked on re-validation")
            return {
                "success": False,
                "reason": "Re-validation failed",
                "guard_reason": reason,
                "safety_report": safety,
                "id": proposal_id,
            }

        # HARDENED: for real (non-dry) apply the pending json must have been manually approved by human
        human_approved = bool(record.get("human_approved", False)) or bool(record.get("proposal", {}).get("human_approved", False))
        if not dry_run and not human_approved:
            return {
                "success": False,
                "reason": "HARDENED: Real apply blocked. Human must edit the pending proposal json and set 'human_approved': true after full review + tests.",
                "id": proposal_id,
                "human_approved": False,
            }

        # Extra approval file gate (even harder human signal)
        # For larger changes, require the extra file even more strictly.
        if not dry_run:
            from openhands_skills.guards import has_extra_approval
            _apply_data = proposal.get("apply_data", {})
            _old_hint = _apply_data.get("old_string_hint", "")
            _new_hint = _apply_data.get("new_string_hint", "")
            change_size = len(_new_hint) - len(_old_hint)
            requires_extra = (not has_extra_approval(proposal_id, self.proposals_dir)) or (abs(change_size) > 1500)
            if requires_extra and not has_extra_approval(proposal_id, self.proposals_dir):
                return {
                    "success": False,
                    "reason": "EXTRA APPROVAL FILE REQUIRED (and mandatory for changes >1500 chars): Create <proposal_id>.approved file in pending_proposals/ after review.",
                    "id": proposal_id,
                }

        # Mandatory pre-apply safety tests (test runner)
        if not dry_run:
            from openhands_skills.guards import run_pre_apply_safety_tests
            test_report = run_pre_apply_safety_tests(target_file)
            if not test_report.get("passed"):
                return {
                    "success": False,
                    "reason": "PRE-APPLY SAFETY TESTS FAILED",
                    "test_report": test_report,
                    "id": proposal_id,
                }

        apply_data = proposal.get("apply_data", {})
        if not apply_data:
            return {
                "success": False,
                "reason": "Proposal has no apply_data. Manual implementation required or regenerate with apply_data.",
                "id": proposal_id,
                "apply_data": apply_data,
            }

        old_text = apply_data.get("old_string_hint", "")
        new_text = apply_data.get("new_string_hint", "")

        if not old_text or not new_text:
            return {
                "success": False,
                "reason": "apply_data missing concrete old/new hints for automated edit. Provide exact strings or use search_replace_hint manually.",
                "id": proposal_id,
                "apply_data": apply_data,
            }

        # Perform the guarded edit (hardened version with human_approved)
        from openhands_skills.guards import perform_guarded_edit
        # Measured before the edit, so the scorer has something to compare against.
        _baseline = (self._measure_health(target_file)
                     if not dry_run and human_approved else None)

        edit_result = perform_guarded_edit(
            target_file=target_file,
            old_text=old_text,
            new_text=new_text,
            dry_run=dry_run,
            context=f"apply_proposal {proposal_id} from task: {record.get('originating_task')}",
            fuzzy=fuzzy,
            human_approved=human_approved
        )

        score_record = {}
        if edit_result.get("applied") or (dry_run and edit_result.get("success")):
            score_record = self.compute_evolution_score(
                proposal,
                {"id": proposal_id, "applied": edit_result.get("applied"),
                 "dry_run": dry_run, "edit_result": edit_result},
                baseline=_baseline)

        if edit_result.get("applied"):
            record["status"] = "APPLIED"
            record["applied_at"] = __import__("datetime").datetime.now().isoformat()
            record["applied_dry_run"] = False
            record["evolution_score"] = score_record

            # Run post-apply evaluation to measure if the Blockchain/system actually got better
            try:
                from openhands_skills.evaluation_harness import run_system_evaluation
                post_eval = run_system_evaluation()
                record["post_apply_system_evaluation"] = {
                    "system_score": post_eval.get("system_improvement_score"),
                    "blockchain_accuracy": post_eval.get("blockchain_intelligence", {}).get("accuracy_percent"),
                }
            except Exception as e:
                record["post_apply_eval_error"] = str(e)[:100]

            applied_dir = os.path.join(self.proposals_dir, "applied")
            os.makedirs(applied_dir, exist_ok=True)
            applied_file = os.path.join(applied_dir, f"{proposal_id}.json")

            try:
                with open(applied_file, "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)
                os.remove(proposal_file)
            except Exception as e:
                record["status"] = "APPLIED_BUT_MOVE_FAILED"
                record["move_error"] = str(e)

            try:
                with open(proposal_file, "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        report = {
            "success": edit_result.get("success", False),
            "id": proposal_id,
            "dry_run": dry_run,
            "applied": edit_result.get("applied", False),
            "target_file": target_file,
            "edit_result": edit_result,
            "re_validated": True,
            "safety_passed": safety.get("passed"),
            "evolution_score": score_record,
            "note": "Always review the diff, run tests, and commit on a dedicated branch. This is a guarded operation. Use fuzzy=True for smarter section matching if exact hint fails.",
        }

        persistent_memory.store(
            text=f"APPLY_PROPOSAL {proposal_id} dry_run={dry_run} applied={report['applied']} on {target_file} score={score_record.get('score',0)}",
            metadata={"type": "guarded_apply_attempt", "id": proposal_id, "dry_run": dry_run, "applied": report["applied"], "score": score_record.get("score", 0)}
        )

        return report

    def rollback_proposal(self, proposal_id: str, context: str = "manual or degraded update") -> dict:
        """Rollback the changes from a previous apply for this proposal.
        Uses the latest backup for the target file. Updates the proposal record status.
        This directly answers: yes, we can rollback if a new update no longer satisfies us (e.g. metrics/score drop, or human decision after new research).
        """
        proposal_file = os.path.join(self.proposals_dir, f"{proposal_id}.json")
        if not os.path.exists(proposal_file):
            return {"success": False, "reason": "Proposal file not found", "id": proposal_id}

        try:
            with open(proposal_file, "r", encoding="utf-8") as f:
                record = json.load(f)
        except Exception as e:
            return {"success": False, "reason": f"Failed to read: {e}", "id": proposal_id}

        proposal = record.get("proposal", {})
        target_file = proposal.get("target_file") or proposal.get("apply_data", {}).get("file")
        if not target_file:
            return {"success": False, "reason": "No target file in proposal", "id": proposal_id}

        from openhands_skills.guards import perform_rollback
        rb = perform_rollback(target_file, context=context + f" for proposal {proposal_id}")

        if rb.get("success"):
            record["status"] = "ROLLED_BACK"
            record["rolled_back_at"] = __import__("datetime").datetime.now().isoformat()
            record["rollback_context"] = context
            try:
                with open(proposal_file, "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            persistent_memory.store(
                text=f"ROLLED BACK proposal {proposal_id} on {target_file}. Reason: {context}",
                metadata={"type": "rollback", "proposal_id": proposal_id, "target": target_file, "context": context}
            )

        return rb

    def post_apply_evaluation_and_rollback_if_degraded(self, proposal_id: str, current_evolution_score: int, degradation_threshold: int = 50, context: str = "score dropped after new update") -> dict:
        """After a new update/apply, if the evolution score is now low (new research shows previous change is no longer good), trigger rollback.
        This provides the mechanism: yes, we can automatically (or on call) rollback if a newer update means the previous one no longer satisfies us.
        """
        # A withheld score (None) means the change could not be measured. That is
        # not the same as a passing grade, and it must not be filed as one.
        if current_evolution_score is None:
            return {"action": "needs_human_review",
                    "score": None, "threshold": degradation_threshold,
                    "reason": "The apply was not measured, so degradation could neither be "
                              "confirmed nor ruled out. Review before trusting this change."}

        if current_evolution_score >= degradation_threshold:
            return {"action": "no_rollback", "score": current_evolution_score, "threshold": degradation_threshold}

        rb = self.rollback_proposal(proposal_id, context=context)
        return {"action": "rollback_triggered", "score": current_evolution_score, "threshold": degradation_threshold, "rollback_result": rb}

# Register
hyper_evolver = HyperAdaptiveEvolutionAgent()