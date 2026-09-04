from backtesting_engine import (
    run_backtest
)

print(
    "\n==================================="
)

print(
    "         AI BACKTEST ENGINE"
)

print(
    "===================================\n"
)

results = run_backtest()

print(
    f"Winning Trades : "
    f"{results['wins']}"
)

print(
    f"Losing Trades  : "
    f"{results['losses']}"
)

print(
    f"Neutral Candles: "
    f"{results['neutral']}"
)

print(
    f"Accuracy       : "
    f"{results['accuracy']}%"
)

print(
    f"Strategy Return: "
    f"{results['return']}%"
)

print(
    "\n===================================\n"
)