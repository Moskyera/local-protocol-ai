from signal_engine import (
    generate_signal
)

from regime_engine import (
    analyze_market_regime
)

from volatility_engine import (
    analyze_volatility
)

from whale_tracker_engine import (
    detect_whale_activity
)

from smart_money_engine import (
    analyze_smart_money
)

from regime_transition_engine import (
    detect_market_phase
)

from ai_scoring_engine import (
    calculate_market_score
)

from priority_engine import (
    calculate_priority_score
)

from multi_asset_config import (
    ALL_SYMBOLS
)

# =========================================
# SAFE ENGINE WRAPPER
# =========================================

def safe_engine_call(

    func,

    default_value,

    *args,

    **kwargs
):

    try:

        return func(
            *args,
            **kwargs
        )

    except Exception as e:

        print(
            f"Engine error: {e}"
        )

        return default_value

# =========================================
# MULTI ASSET AI SCANNER
# =========================================

def scan_market():

    results = []

    # =====================================
    # GLOBAL REGIME
    # =====================================

    regime = safe_engine_call(

        analyze_market_regime,

        {
            "crypto_regime":
            "NEUTRAL"
        }
    )

    # =====================================
    # LOOP
    # =====================================

    for symbol in ALL_SYMBOLS:

        try:

            print(
                f"Scanning {symbol}..."
            )

            # =================================
            # SIGNAL
            # =================================

            signal = generate_signal(
                symbol
            )

            # =================================
            # VOLATILITY
            # =================================

            volatility = safe_engine_call(

                analyze_volatility,

                {
                    "alerts": []
                },

                symbol
            )

            # =================================
            # WHALES
            # =================================

            whale = safe_engine_call(

                detect_whale_activity,

                {
                    "state": "UNKNOWN",
                    "message":
                    "Whale data unavailable."
                },

                symbol
            )

            # =================================
            # SMART MONEY
            # =================================

            smart_money = safe_engine_call(

                analyze_smart_money,

                {
                    "state": "UNKNOWN",
                    "insight":
                    "Smart money data unavailable."
                },

                symbol
            )

            # =================================
            # VOLATILITY STATE
            # =================================

            volatility_state = (
                "STABLE"
            )

            if len(
                volatility["alerts"]
            ) > 1:

                volatility_state = (
                    "ELEVATED"
                )

            # =================================
            # MARKET PHASE
            # =================================

            phase, phase_insight = (

                detect_market_phase(

                    rsi=signal["rsi"],

                    macd=signal["macd"],

                    signal=signal[
                        "signal"
                    ],

                    regime=regime[
                        "crypto_regime"
                    ],

                    volatility=
                    volatility_state
                )
            )

            # =================================
            # SCORE
            # =================================

            score = (

                calculate_market_score(

                    signal=signal[
                        "signal"
                    ],

                    regime=regime[
                        "crypto_regime"
                    ],

                    phase=phase,

                    volatility=
                    volatility_state,

                    smart_money=
                    smart_money["state"],

                    whale_activity=
                    whale["state"],

                    rsi=signal["rsi"],

                    macd=signal["macd"]
                )
            )

            # =================================
            # PRIORITY
            # =================================

            priority = (

                calculate_priority_score(

                    market_score=
                    score["final_score"],

                    signal=
                    signal["signal"],

                    smart_money=
                    smart_money["state"],

                    whale_activity=
                    whale["state"],

                    phase=phase
                )
            )

            # =================================
            # STORE
            # =================================

            results.append({

                "symbol":
                symbol,

                "signal":
                signal["signal"],

                "price":
                signal["price"],

                "rsi":
                signal["rsi"],

                "macd":
                signal["macd"],

                "confidence":
                signal["confidence"],

                "market_phase":
                phase,

                "phase_insight":
                phase_insight,

                "market_score":
                score["final_score"],

                "market_score_insight":
                score["interpretation"],

                "priority_score":
                priority["score"],

                "priority_label":
                priority["label"],

                "smart_money":
                smart_money["state"],

                "smart_money_insight":
                smart_money["insight"],

                "whale_activity":
                whale["state"],

                "whale_insight":
                whale["message"],

                "volatility":
                volatility_state
            })

        except Exception as e:

            print(
                f"Scanner error "
                f"for {symbol}: "
                f"{e}"
            )

    # =====================================
    # SORT
    # =====================================

    results = sorted(

        results,

        key=lambda x:
        x["priority_score"],

        reverse=True
    )

    return results

# =========================================
# REPORT
# =========================================

def generate_scanner_report():

    results = scan_market()

    report = """

===================================
      MULTI-ASSET AI SCANNER
===================================
"""

    rank = 1

    for asset in results:

        report += f"""

#{rank} {asset['symbol']}

-----------------------------------

Signal:
{asset['signal']}

Price:
{asset['price']}

RSI:
{asset['rsi']}

MACD:
{asset['macd']}

Confidence:
{asset['confidence']}%

-----------------------------------

Market Structure:
{asset['market_phase']}

Phase Insight:
{asset['phase_insight']}

Volatility:
{asset['volatility']}

-----------------------------------

Market Quality Score:
{asset['market_score']} / 100

Market Score Insight:
{asset['market_score_insight']}

-----------------------------------

Priority Score:
{asset['priority_score']} / 100

Priority Status:
{asset['priority_label']}

-----------------------------------

Smart Money:
{asset['smart_money']}

Smart Money Insight:
{asset['smart_money_insight']}

-----------------------------------

Whale Activity:
{asset['whale_activity']}

Whale Insight:
{asset['whale_insight']}

===================================
"""

        rank += 1

    return report