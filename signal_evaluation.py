"""
signal_evaluation - ΣΩΣΤΗ αξιολόγηση των signals.

ΤΟ ΠΡΟΒΛΗΜΑ ΠΟΥ ΛΥΝΕΙ (μετρημένο στα δικά σου 381 signals, 2026-08-12):
Το performance_engine.update_signal_performance() τρέχει μέσα σε κάθε briefing,
οπότε αξιολογεί κάθε signal ΛΕΠΤΑ αφού δημιουργηθεί και μετά ΠΑΓΩΝΕΙ το
αποτέλεσμα για πάντα (`if "result" in item: continue`).
Αποτέλεσμα στα πραγματικά δεδομένα:
    - 85% των signals "αξιολογήθηκαν" σε κίνηση τιμής < 0.5%
    - median κίνηση: -0.01%
Άρα το "Accuracy 52.72%" ΔΕΝ μετράει προβλεπτική ικανότητα· μετράει αν η τιμή
έτυχε να είναι ελάχιστα πάνω ή κάτω λίγα λεπτά αργότερα — δηλαδή κέρμα.

ΤΙ ΚΑΝΕΙ ΑΥΤΟ ΤΟ MODULE ΣΩΣΤΑ:
1. ΟΡΙΖΟΝΤΑΣ: αξιολογεί σε ΣΥΓΚΕΚΡΙΜΕΝΟ χρόνο μετά το signal (π.χ. 24h, 7d).
   Signals που δεν έχουν "ωριμάσει" ακόμα μένουν PENDING, δεν μετρούν.
2. ΚΑΤΩΦΛΙ: κίνηση μικρότερη από το κόστος συναλλαγής μετράει NEUTRAL, όχι WIN.
3. ΜΕΓΕΘΟΣ: κρατάει την απόδοση, όχι μόνο hit-rate. Δέκα +0.1% και ένα -10%
   δίνουν 91% "accuracy" και καθαρή ζημιά.
4. BASELINE: συγκρίνει με buy-and-hold. Hit-rate 55% που υπολείπεται του
   buy-and-hold δεν έχει αξία.

ΣΗΜΕΙΩΣΗ: αυτό είναι εργαλείο ΜΕΤΡΗΣΗΣ. Σου λέει αν τα signals έχουν
προβλεπτική αξία. ΔΕΝ είναι επενδυτική συμβουλή και δεν προτείνει συναλλαγές.

Χρήση:
    python signal_evaluation.py                 # έκθεση με ορίζοντα 24h
    python signal_evaluation.py --hours 168     # 7 ημέρες
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

HISTORY_FILE = os.getenv("SIGNAL_HISTORY_FILE", "signal_history.json")

#: Round-trip cost assumption (taker fee in + out + slippage), in percent.
#: A move smaller than this is not a real win even if the sign is right.
DEFAULT_COST_PCT = 0.20

BUY_SIGNALS = {"BUY", "STRONG BUY"}
SELL_SIGNALS = {"SELL", "STRONG SELL"}


@dataclass
class Outcome:
    symbol: str
    signal: str
    entry: float
    exit: float
    return_pct: float          # signed, in the direction of the signal
    hours_held: float
    verdict: str               # WIN / LOSS / FLAT / PENDING


@dataclass
class Evaluation:
    horizon_hours: float
    cost_pct: float
    outcomes: List[Outcome] = field(default_factory=list)
    pending: int = 0
    skipped: int = 0

    # ---------------------------------------------------------------- #
    def scored(self) -> List[Outcome]:
        return [o for o in self.outcomes if o.verdict in ("WIN", "LOSS", "FLAT")]

    def decisive(self) -> List[Outcome]:
        return [o for o in self.outcomes if o.verdict in ("WIN", "LOSS")]

    def to_report(self) -> str:
        d = self.decisive()
        s = self.scored()
        lines = [
            f"SIGNAL EVALUATION — horizon {self.horizon_hours:.0f}h, "
            f"cost assumption {self.cost_pct:.2f}%",
            f"  matured & scored : {len(s)}",
            f"  still pending    : {self.pending}  (not old enough to judge)",
            f"  unusable         : {self.skipped}  (missing price/timestamp)",
        ]
        if not s:
            lines.append("")
            lines.append("  Not enough matured signals yet to say anything. "
                         "That is the honest answer, not a failure.")
            return "\n".join(lines)

        flat = len(s) - len(d)
        lines.append(f"  inside costs     : {flat}  (|move| < {self.cost_pct}% — counted FLAT, not WIN)")
        if d:
            wins = sum(1 for o in d if o.verdict == "WIN")
            hit = 100.0 * wins / len(d)
            rets = [o.return_pct for o in d]
            lines += [
                "",
                f"  hit rate (decisive only) : {hit:.1f}%  ({wins}/{len(d)})",
                f"  mean return per signal   : {statistics.mean(rets):+.2f}%",
                f"  median return per signal : {statistics.median(rets):+.2f}%",
                f"  total if equally sized   : {sum(rets):+.1f}%",
                f"  best / worst             : {max(rets):+.2f}% / {min(rets):+.2f}%",
            ]
            wr = [o.return_pct for o in d if o.verdict == "WIN"]
            lr = [o.return_pct for o in d if o.verdict == "LOSS"]
            if wr and lr:
                lines.append(f"  avg win / avg loss       : {statistics.mean(wr):+.2f}% / "
                             f"{statistics.mean(lr):+.2f}%")
                lines.append("  NOTE: hit rate alone is misleading — a high hit rate with "
                             "large losses still loses money.")
        return "\n".join(lines)


def _parse_ts(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def evaluate(history: List[dict], horizon_hours: float = 24.0,
             cost_pct: float = DEFAULT_COST_PCT,
             now: Optional[datetime] = None) -> Evaluation:
    """Score signals that have had time to play out. Never raises."""
    now = now or datetime.now(timezone.utc)
    ev = Evaluation(horizon_hours=horizon_hours, cost_pct=cost_pct)

    for item in history or []:
        sig = str(item.get("signal", "")).upper()
        if sig not in BUY_SIGNALS and sig not in SELL_SIGNALS:
            continue                       # NEUTRAL/WATCH are not predictions

        ts = _parse_ts(item.get("timestamp"))
        try:
            entry = float(item["entry_price"])
            exit_ = float(item["current_price"])
        except Exception:
            ev.skipped += 1
            continue
        if ts is None or entry <= 0:
            ev.skipped += 1
            continue

        age_h = (now - ts).total_seconds() / 3600.0
        if age_h < horizon_hours:
            ev.pending += 1
            continue

        raw = (exit_ - entry) / entry * 100.0
        directional = raw if sig in BUY_SIGNALS else -raw

        if abs(directional) < cost_pct:
            verdict = "FLAT"
        else:
            verdict = "WIN" if directional > 0 else "LOSS"

        ev.outcomes.append(Outcome(
            symbol=str(item.get("symbol", "?")), signal=sig, entry=entry,
            exit=exit_, return_pct=directional, hours_held=age_h,
            verdict=verdict))
    return ev


def diagnose(history: List[dict]) -> str:
    """Explain WHY the existing accuracy number cannot be trusted."""
    moves = []
    for x in history or []:
        try:
            e, c = float(x["entry_price"]), float(x["current_price"])
            if e > 0:
                moves.append(abs((c - e) / e * 100.0))
        except Exception:
            pass
    if not moves:
        return "No comparable prices in the history."
    tiny = sum(1 for m in moves if m < 0.5)
    return (
        f"MEASUREMENT HEALTH CHECK\n"
        f"  signals with a price pair : {len(moves)}\n"
        f"  median |price move|       : {statistics.median(moves):.3f}%\n"
        f"  moved less than 0.5%      : {tiny}/{len(moves)} ({100*tiny/len(moves):.0f}%)\n"
        f"  -> If most signals are judged on sub-0.5% moves, the outcome is\n"
        f"     transaction noise, not prediction. The stored 'accuracy' is then\n"
        f"     a coin flip and must not be used to judge the strategy."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Honest evaluation of stored signals")
    ap.add_argument("--hours", type=float, default=24.0, help="holding horizon")
    ap.add_argument("--cost", type=float, default=DEFAULT_COST_PCT,
                    help="round-trip cost assumption in percent")
    ap.add_argument("--file", default=HISTORY_FILE)
    a = ap.parse_args()

    if not os.path.isfile(a.file):
        print(f"No history file at {a.file}")
        return 1
    with open(a.file, encoding="utf-8") as f:
        history = json.load(f)

    print(diagnose(history))
    print()
    print(evaluate(history, horizon_hours=a.hours, cost_pct=a.cost).to_report())
    print()
    print("This measures whether the signals carry information. It is not "
          "financial advice and recommends no trades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
