from watchlist_engine import get_stock_watchlist, get_crypto_watchlist
from config import config
from logger import log

#: How many quotes must have arrived before a regime is a finding rather than
#: an accident. A watchlist row whose price failed now renders "⚪ ... δεν
#: ανακτήθηκε" and counts as neither colour — so without this floor, nine
#: failures and one green quote produced "BULLISH", and ten failures produced
#: "MIXED", which reads like a market observation instead of an outage.
MIN_QUOTES = 4

#: A one-vote edge is not a direction. 5-4 is a coin toss with extra steps.
CLEAR_MAJORITY = 0.60


def count_sentiment(items):
    """Returns (bullish, bearish, counted) — how many rows actually had a price.

    The third value is the one that was missing. Two counts alone cannot
    distinguish "the market is flat" from "nothing was retrieved".
    """
    bullish = sum(1 for item in items if "🟢" in item)
    bearish = sum(1 for item in items if "🔴" in item)
    return bullish, bearish, bullish + bearish


def _regime(bullish, bearish, counted, label):
    if counted < MIN_QUOTES:
        log.warning(f"{label} regime UNKNOWN: only {counted} usable quote(s), "
                    f"need {MIN_QUOTES}")
        return "UNKNOWN"
    if bullish >= counted * CLEAR_MAJORITY:
        return "BULLISH"
    if bearish >= counted * CLEAR_MAJORITY:
        return "BEARISH"
    return "MIXED"


def analyze_market_regime():
    log.debug("Analyzing overall market regime")
    stocks = get_stock_watchlist()
    crypto = get_crypto_watchlist()

    stock_bullish, stock_bearish, stock_counted = count_sentiment(stocks)
    crypto_bullish, crypto_bearish, crypto_counted = count_sentiment(crypto)

    stock_regime = _regime(stock_bullish, stock_bearish, stock_counted, "Stocks")
    crypto_regime = _regime(crypto_bullish, crypto_bearish, crypto_counted, "Crypto")

    # UNKNOWN is not MIXED. MIXED says the market is undecided; UNKNOWN says we
    # are, and the two must not be reported with the same word.
    if "UNKNOWN" in (stock_regime, crypto_regime):
        overall = "UNKNOWN"
    elif stock_regime == "BULLISH" and crypto_regime == "BULLISH":
        overall = "RISK-ON"
    elif stock_regime == "BEARISH" and crypto_regime == "BEARISH":
        overall = "RISK-OFF"
    else:
        overall = "MIXED"

    log.info(f"Regime Analysis | Stocks: {stock_regime} ({stock_counted} quotes) | "
             f"Crypto: {crypto_regime} ({crypto_counted} quotes) | Overall: {overall}")
    return {
        "stock_regime": stock_regime,
        "crypto_regime": crypto_regime,
        "overall": overall,
        "stock_bullish": stock_bullish,
        "stock_bearish": stock_bearish,
        "stock_counted": stock_counted,
        "crypto_bullish": crypto_bullish,
        "crypto_bearish": crypto_bearish,
        "crypto_counted": crypto_counted,
        "min_quotes_required": MIN_QUOTES,
    }