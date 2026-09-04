import json

from pathlib import Path

from datetime import datetime

# =========================================
# MEMORY FILE
# =========================================

MEMORY_FILE = "market_memory.json"

# =========================================
# LOAD MEMORY
# =========================================

def load_memory():

    path = Path(MEMORY_FILE)

    if not path.exists():

        return []

    try:

        with open(

            MEMORY_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            return json.load(file)

    except Exception:

        return []

# =========================================
# SAVE MEMORY
# =========================================

def save_memory(data):

    with open(

        MEMORY_FILE,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            data,

            file,

            indent=4
        )

# =========================================
# STORE MARKET SNAPSHOT
# =========================================

def store_market_snapshot(

    symbol,

    signal,

    regime,

    probability,

    rsi,

    macd,

    consensus
):

    memory = load_memory()

    snapshot = {

        "timestamp": str(
            datetime.now()
        ),

        "symbol": symbol,

        "signal": signal,

        "regime": regime,

        "probability": probability,

        "rsi": rsi,

        "macd": macd,

        "consensus": consensus
    }

    memory.append(snapshot)

    # =====================================
    # KEEP LAST 100 ENTRIES
    # =====================================

    memory = memory[-100:]

    save_memory(memory)

# =========================================
# ANALYZE MEMORY
# =========================================

def analyze_memory():

    memory = load_memory()

    # =====================================
    # NOT ENOUGH DATA
    # =====================================

    if len(memory) < 2:

        return [

            "Not enough historical "
            "data yet."
        ]

    latest = memory[-1]

    previous = memory[-2]

    insights = []

    # =====================================
    # SIGNAL CHANGE
    # =====================================

    if latest["signal"] != previous["signal"]:

        insights.append(

            f"Signal changed from "
            f"{previous['signal']} "
            f"to {latest['signal']}."
        )

    # =====================================
    # REGIME CHANGE
    # =====================================

    if latest["regime"] != previous["regime"]:

        insights.append(

            f"Market regime shifted "
            f"from {previous['regime']} "
            f"to {latest['regime']}."
        )

    # =====================================
    # RSI MOMENTUM
    # =====================================

    if latest["rsi"] > previous["rsi"]:

        insights.append(

            "RSI momentum improving."
        )

    elif latest["rsi"] < previous["rsi"]:

        insights.append(

            "RSI momentum weakening."
        )

    # =====================================
    # MACD MOMENTUM
    # =====================================

    if latest["macd"] > previous["macd"]:

        insights.append(

            "MACD momentum improving."
        )

    elif latest["macd"] < previous["macd"]:

        insights.append(

            "MACD momentum weakening."
        )

    # =====================================
    # PROBABILITY CHANGE
    # =====================================

    if (

        latest["probability"]

        > previous["probability"]
    ):

        insights.append(

            "AI confidence increasing."
        )

    elif (

        latest["probability"]

        < previous["probability"]
    ):

        insights.append(

            "AI confidence decreasing."
        )

    # =====================================
    # CONSENSUS CHANGE
    # =====================================

    if (

        latest["consensus"]

        != previous["consensus"]
    ):

        insights.append(

            f"Consensus shifted from "
            f"{previous['consensus']} "
            f"to {latest['consensus']}."
        )

    # =====================================
    # DEFAULT
    # =====================================

    if len(insights) == 0:

        insights.append(

            "No major historical "
            "changes detected."
        )

    return insights