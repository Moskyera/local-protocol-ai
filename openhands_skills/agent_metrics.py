"""
agent_metrics - ελαφρύ, τοπικό run-log για να ξέρουμε ΤΙ δουλεύει.

ΓΙΑΤΙ: μέχρι τώρα δεν υπήρχε καμία μετρική. Δεν ξέραμε ποιο intent τρέχει πιο
συχνά, πόσες φορές χρειάστηκε retry ο coder, ποιο βήμα αργεί, ούτε αν μια αλλαγή
βελτίωσε ή χειροτέρεψε κάτι. Ό,τι βελτιώσαμε σήμερα (36->94 tok/s) το πετύχαμε
επειδή το ΜΕΤΡΗΣΑΜΕ πρώτα· τα υπόλοιπα τα βελτιώναμε στα τυφλά.

Σχεδιασμός: append-only JSONL, μηδέν εξαρτήσεις, ποτέ δεν πετάει exception, ποτέ
δεν μπλοκάρει τον agent. Αν το logging σπάσει, η δουλειά συνεχίζεται.

Χρήση:
    from openhands_skills.agent_metrics import track
    with track("coder", task="write a parser") as run:
        ...
        run.note(attempts=2, clean=True)

Ανάλυση:
    python -m openhands_skills.agent_metrics          # σύνοψη
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

METRICS_FILE = Path(os.getenv(
    "MOSKY_METRICS_FILE",
    Path(__file__).resolve().parent.parent / "logs" / "agent_runs.jsonl"))


class _Run:
    """Handle passed to the caller so it can attach facts to the record."""

    def __init__(self, agent: str, **fields):
        self.record = {"agent": agent, **fields}

    def note(self, **fields):
        self.record.update(fields)


def _write(record: dict) -> None:
    try:
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # metrics must never break the agent


@contextmanager
def track(agent: str, **fields):
    """Time an agent run and record whether it succeeded."""
    run = _Run(agent, **fields)
    start = time.time()
    ok = True
    err = None
    try:
        yield run
    except Exception as e:
        ok, err = False, f"{type(e).__name__}: {e}"
        raise
    finally:
        run.record.update({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seconds": round(time.time() - start, 2),
            # AND, not "caller's value wins". A caller that optimistically
            # noted ok=True early and then raised was recorded as a success,
            # so the file the system uses as evidence about itself reported
            # 100% success for runs that crashed or returned an error sentinel.
            "ok": bool(run.record.get("ok", True)) and ok,
        })
        if err:
            run.record["error"] = err[:300]
        _write(run.record)


def summary(limit: int = 500) -> str:
    """Human-readable rollup of the recent runs."""
    if not METRICS_FILE.exists():
        return f"No metrics yet ({METRICS_FILE})."
    rows = []
    try:
        with open(METRICS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    except Exception as e:
        return f"Could not read metrics: {e}"
    rows = rows[-limit:]
    if not rows:
        return "No runs recorded yet."

    by_agent: dict = {}
    for r in rows:
        a = r.get("agent", "?")
        d = by_agent.setdefault(a, {"n": 0, "ok": 0, "secs": [], "attempts": []})
        d["n"] += 1
        d["ok"] += 1 if r.get("ok") else 0
        if isinstance(r.get("seconds"), (int, float)):
            d["secs"].append(r["seconds"])
        if isinstance(r.get("attempts"), int):
            d["attempts"].append(r["attempts"])

    def med(xs):
        return sorted(xs)[len(xs) // 2] if xs else 0

    out = [f"Agent runs: {len(rows)}  ({METRICS_FILE})", ""]
    out.append(f"{'agent':<24}{'runs':>6}{'success':>9}{'median s':>10}{'avg tries':>11}")
    out.append("-" * 60)
    for a, d in sorted(by_agent.items(), key=lambda kv: -kv[1]["n"]):
        rate = 100.0 * d["ok"] / d["n"] if d["n"] else 0
        tries = sum(d["attempts"]) / len(d["attempts"]) if d["attempts"] else 0
        out.append(f"{a:<24}{d['n']:>6}{rate:>8.0f}%{med(d['secs']):>10.1f}"
                   f"{tries:>11.1f}")

    worst = [a for a, d in by_agent.items() if d["n"] >= 3 and d["ok"] / d["n"] < 0.7]
    if worst:
        out += ["", f"Below 70% success: {', '.join(worst)} — worth investigating."]
    return "\n".join(out)


if __name__ == "__main__":
    print(summary())
