import json

from pathlib import Path

from datetime import datetime

# =========================================
# SIGNAL DATABASE
# =========================================

SIGNAL_FILE = "signal_history.json"

# =========================================
# LOAD SIGNALS
# =========================================

def load_signals():

    path = Path(SIGNAL_FILE)

    if not path.exists():

        return []

    try:

        with open(

            SIGNAL_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            return json.load(file)

    except Exception:

        return []

# =========================================
# SAVE SIGNALS
# =========================================

def save_signals(data):

    with open(

        SIGNAL_FILE,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            data,

            file,

            indent=4
        )

# =========================================
# STORE SIGNAL
# =========================================

def store_signal(

    symbol,

    signal,

    price,

    regime,

    probability
):

    history = load_signals()

    entry = {

        "timestamp": str(
            datetime.now()
        ),

        "symbol": symbol,

        "signal": signal,

        "entry_price": price,

        "regime": regime,

        "probability": probability
    }

    history.append(entry)

    # KEEP LAST 500 ENTRIES

    history = history[-500:]

    save_signals(history)

# =========================================
# ANALYZE SIGNAL HISTORY
# =========================================

def analyze_signal_history():

    history = load_signals()

    if len(history) == 0:

        return {

            "total": 0,

            "buy_signals": 0,

            "sell_signals": 0,

            "neutral_signals": 0,

            "bullish_regime": 0,

            "bearish_regime": 0
        }

    buy_count = 0

    sell_count = 0

    neutral_count = 0

    bullish_regime = 0

    bearish_regime = 0

    # =====================================
    # COUNT SIGNALS
    # =====================================

    for item in history:

        signal = item["signal"]

        regime = item["regime"]

        if signal in [

            "BUY",

            "STRONG BUY"
        ]:

            buy_count += 1

        elif signal in [

            "SELL",

            "STRONG SELL"
        ]:

            sell_count += 1

        else:

            neutral_count += 1

        if regime == "BULLISH":

            bullish_regime += 1

        elif regime == "BEARISH":

            bearish_regime += 1

    # =====================================
    # RETURN ANALYSIS
    # =====================================

    return {

        "total": len(history),

        "buy_signals": buy_count,

        "sell_signals": sell_count,

        "neutral_signals": neutral_count,

        "bullish_regime": bullish_regime,

        "bearish_regime": bearish_regime
    }