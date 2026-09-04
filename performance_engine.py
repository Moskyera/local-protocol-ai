import os
import ccxt
from signal_history_engine import load_signals, save_signals
from config import config
from logger import log

binance = ccxt.binance()
okx = ccxt.okx()

def get_current_price(symbol):
    try:
        ticker = binance.fetch_ticker(symbol)
        return float(ticker["last"])
    except Exception:
        try:
            ticker = okx.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as e:
            log.error(f"Failed to get current price for {symbol}: {e}")
            return None

from datetime import datetime, timedelta, timezone

#: A signal is only judged once it has had this long to play out. The old code
#: had NO horizon: it ran inside every briefing, so it graded each signal minutes
#: after creation and then froze that verdict forever. Measured on the real
#: history: 85% of signals were graded on a price move under 0.5% and the median
#: move was 0.118%, i.e. the recorded "accuracy" was transaction noise.
EVAL_HORIZON_HOURS = float(os.getenv("SIGNAL_EVAL_HORIZON_HOURS", 24))

#: Moves smaller than round-trip costs are not wins. Graded FLAT instead.
EVAL_COST_PCT = float(os.getenv("SIGNAL_EVAL_COST_PCT", 0.20))


def _parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def update_signal_performance():
    """Grade signals that have MATURED, and only those.

    Immature signals are left without a `result` so they are graded later at the
    proper horizon. `eval_price` is recorded separately from the old
    `current_price` field so the two are never confused.
    """
    history = load_signals()
    now = datetime.now(timezone.utc)
    updated, graded, pending = [], 0, 0

    for item in history:
        if item.get("result") and item.get("evaluated_at_horizon"):
            updated.append(item)          # already graded properly
            continue

        ts = _parse_ts(item.get("timestamp"))
        signal = str(item.get("signal", "")).upper()
        if signal not in ("BUY", "STRONG BUY", "SELL", "STRONG SELL"):
            updated.append(item)          # NEUTRAL / WATCH are not predictions
            continue

        if ts is None or (now - ts) < timedelta(hours=EVAL_HORIZON_HOURS):
            pending += 1
            updated.append(item)          # too young to judge — leave it alone
            continue

        try:
            entry_price = float(item["entry_price"])
        except Exception:
            updated.append(item)
            continue

        price_now = get_current_price(item.get("symbol", ""))
        if price_now is None or entry_price <= 0:
            updated.append(item)
            continue

        move = (price_now - entry_price) / entry_price * 100.0
        directional = move if signal in ("BUY", "STRONG BUY") else -move

        if abs(directional) < EVAL_COST_PCT:
            result = "FLAT"               # inside costs: not a win, not a loss
        else:
            result = "WIN" if directional > 0 else "LOSS"

        item["eval_price"] = price_now
        item["return_pct"] = round(directional, 3)
        item["result"] = result
        item["evaluated_at_horizon"] = EVAL_HORIZON_HOURS
        item["evaluated_at"] = now.isoformat(timespec="seconds")
        updated.append(item)
        graded += 1

    save_signals(updated)
    log.info(f"Signal performance: graded {graded} matured, {pending} still "
             f"pending (horizon {EVAL_HORIZON_HOURS:.0f}h)")

def analyze_performance():
    """Report performance, counting ONLY signals graded at the proper horizon.

    Legacy rows (graded minutes after creation by the old code) are excluded from
    the headline numbers instead of silently inflating them; they are still
    reported separately as `legacy_untrusted` so nothing is hidden.
    Keys `wins`/`losses`/`neutral`/`accuracy` are preserved for existing callers.
    """
    history = load_signals()
    proper = [i for i in history if i.get("evaluated_at_horizon")]
    legacy = [i for i in history
              if i.get("result") and not i.get("evaluated_at_horizon")]

    wins = sum(1 for i in proper if i.get("result") == "WIN")
    losses = sum(1 for i in proper if i.get("result") == "LOSS")
    flat = sum(1 for i in proper if i.get("result") == "FLAT")
    decisive = wins + losses
    accuracy = round(wins / decisive * 100, 2) if decisive else 0

    rets = [i["return_pct"] for i in proper
            if isinstance(i.get("return_pct"), (int, float))]
    mean_return = round(sum(rets) / len(rets), 3) if rets else 0.0

    if decisive < 30:
        note = (f"Only {decisive} signals have been graded at the "
                f"{EVAL_HORIZON_HOURS:.0f}h horizon — too few to judge the "
                f"strategy. Treat this number as provisional.")
    else:
        note = (f"Based on {decisive} decisive signals graded at "
                f"{EVAL_HORIZON_HOURS:.0f}h, {flat} more moved less than "
                f"{EVAL_COST_PCT}% and were counted FLAT.")

    log.info(f"Performance (horizon-graded): W={wins} L={losses} FLAT={flat} "
             f"acc={accuracy}% mean_return={mean_return}% | "
             f"{len(legacy)} legacy rows excluded")
    return {
        "wins": wins,
        "losses": losses,
        "neutral": flat,
        "accuracy": accuracy,
        "flat": flat,
        "mean_return_pct": mean_return,
        "sample_size": decisive,
        "legacy_untrusted": len(legacy),
        "horizon_hours": EVAL_HORIZON_HOURS,
        "note": note,
    }