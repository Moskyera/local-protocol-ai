from market_data_service import get_chart_data
from config import config
from logger import log

def generate_backtest_signals(df):
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        rsi = float(row["RSI"])
        macd = float(row["MACD"])
        macd_signal = float(row["MACD_SIGNAL"])

        signal = "NEUTRAL"
        if rsi > 50 and macd > macd_signal:
            signal = "BUY"
        elif rsi < 45 and macd < macd_signal:
            signal = "SELL"
        signals.append(signal)

    df["SIGNAL"] = signals
    return df

def run_backtest(symbol=config.DEFAULT_SYMBOL):
    log.info(f"Running backtest for {symbol}")
    df = get_chart_data(symbol, timeframe="1h", limit=300)
    df = generate_backtest_signals(df)

    wins = losses = neutral = total_return = 0

    for i in range(len(df) - 1):
        current = df.iloc[i]
        nxt = df.iloc[i + 1]
        signal = current["SIGNAL"]
        change = ((nxt["close"] - current["close"]) / current["close"]) * 100

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
        else:
            neutral += 1

    total_trades = wins + losses
    accuracy = round((wins / total_trades * 100), 2) if total_trades > 0 else 0

    log.success(f"Backtest completed | Accuracy: {accuracy}% | Return: {round(total_return, 2)}%")
    return {
        "wins": wins,
        "losses": losses,
        "neutral": neutral,
        "accuracy": accuracy,
        "return": round(total_return, 2)
    }