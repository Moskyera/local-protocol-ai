from strategy_optimizer import (
    optimize_strategy
)

print(
    "\n==================================="
)

print(
    "      AI STRATEGY OPTIMIZER"
)

print(
    "===================================\n"
)

results = optimize_strategy()

print(
    f"Best BUY RSI : "
    f"{results['buy_rsi']}"
)

print(
    f"Best SELL RSI: "
    f"{results['sell_rsi']}"
)

print(
    f"Winning Trades: "
    f"{results['wins']}"
)

print(
    f"Losing Trades : "
    f"{results['losses']}"
)

print(
    f"Accuracy      : "
    f"{results['accuracy']}%"
)

print(
    f"Strategy Return: "
    f"{results['return']}%"
)

print(
    "\n===================================\n"
)