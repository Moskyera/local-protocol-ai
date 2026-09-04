from chart_engine import get_chart_data

# =========================================
# TEST STRATEGY
# =========================================

def test_strategy(

    df,

    buy_rsi,

    sell_rsi
):

    wins = 0

    losses = 0

    total_return = 0

    for i in range(

        len(df) - 1
    ):

        row = df.iloc[i]

        nxt = df.iloc[i + 1]

        rsi = float(row["RSI"])

        macd = float(row["MACD"])

        macd_signal = float(
            row["MACD_SIGNAL"]
        )

        current_price = float(
            row["close"]
        )

        next_price = float(
            nxt["close"]
        )

        change = (

            (
                next_price
                -
                current_price
            )
            /
            current_price

        ) * 100

        signal = "NEUTRAL"

        # BUY

        if (

            rsi > buy_rsi

            and

            macd > macd_signal
        ):

            signal = "BUY"

        # SELL

        elif (

            rsi < sell_rsi

            and

            macd < macd_signal
        ):

            signal = "SELL"

        # EVALUATE

        if signal == "BUY":

            if change > 0:

                wins += 1

            else:

                losses += 1

            total_return += change

        elif signal == "SELL":

            if change < 0:

                wins += 1

            else:

                losses += 1

            total_return += abs(change)

    # =====================================
    # ACCURACY
    # =====================================

    total = wins + losses

    accuracy = 0

    if total > 0:

        accuracy = round(

            (
                wins
                /
                total
            ) * 100,

            2
        )

    return {

        "buy_rsi": buy_rsi,

        "sell_rsi": sell_rsi,

        "wins": wins,

        "losses": losses,

        "accuracy": accuracy,

        "return": round(
            total_return,
            2
        )
    }

# =========================================
# OPTIMIZER
# =========================================

def optimize_strategy():

    df = get_chart_data(

        symbol="BTC/USDT",

        timeframe="1h",

        limit=500
    )

    best = None

    best_score = -999999

    # =====================================
    # PARAMETERS
    # =====================================

    buy_levels = [

        50,
        52,
        55,
        58,
        60
    ]

    sell_levels = [

        45,
        42,
        40,
        38,
        35
    ]

    for buy_rsi in buy_levels:

        for sell_rsi in sell_levels:

            results = test_strategy(

                df,

                buy_rsi,

                sell_rsi
            )

            # =================================
            # SCORE
            # =================================

            score = (

                results["accuracy"] * 2

                +

                results["return"]
            )

            if score > best_score:

                best_score = score

                best = results

    return best