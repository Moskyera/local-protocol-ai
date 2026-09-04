import ccxt
import pandas as pd

from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator

# =========================================
# EXCHANGE
# =========================================

exchange = ccxt.binance({
    "enableRateLimit": True
})

# =========================================
# MARKET INDICATORS
# =========================================

def get_market_indicators(
    symbol="BTC/USDT",
    timeframe="1h"
):

    try:

        # =====================================
        # FETCH DATA
        # =====================================

        ohlcv = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=100
        )

        if not ohlcv:

            raise Exception(
                "No OHLCV data received"
            )

        # =====================================
        # DATAFRAME
        # =====================================

        df = pd.DataFrame(
            ohlcv,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        # =====================================
        # TYPE SAFETY
        # =====================================

        numeric_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        df[numeric_cols] = (
            df[numeric_cols]
            .astype(float)
        )

        # =====================================
        # RSI
        # =====================================

        rsi = RSIIndicator(
            close=df["close"],
            window=14
        )

        df["rsi"] = rsi.rsi()

        # =====================================
        # MACD
        # =====================================

        macd = MACD(
            close=df["close"]
        )

        df["macd"] = macd.macd()

        df["macd_signal"] = (
            macd.macd_signal()
        )

        df["macd_histogram"] = (
            macd.macd_diff()
        )

        # =====================================
        # SMA20
        # =====================================

        sma20 = SMAIndicator(
            close=df["close"],
            window=20
        )

        df["sma20"] = (
            sma20.sma_indicator()
        )

        # =====================================
        # DROP NaN
        # =====================================

        df = df.dropna()

        latest = df.iloc[-1]

        # =====================================
        # TREND
        # =====================================

        trend = "BEARISH"

        if latest["close"] > latest["sma20"]:

            trend = "BULLISH"

        # =====================================
        # RESULT
        # =====================================

        return {

            "symbol": symbol,

            "timeframe": timeframe,

            "price": round(
                latest["close"],
                6
            ),

            "rsi": round(
                latest["rsi"],
                2
            ),

            "macd": round(
                latest["macd"],
                4
            ),

            "macd_signal": round(
                latest["macd_signal"],
                4
            ),

            "macd_histogram": round(
                latest["macd_histogram"],
                4
            ),

            "sma20": round(
                latest["sma20"],
                4
            ),

            "trend": trend,

            "volume": round(
                latest["volume"],
                2
            )
        }

    except Exception as e:

        print(
            f"Indicator engine error "
            f"for {symbol}: {e}"
        )

        return {

            "symbol": symbol,

            "error": str(e)
        }