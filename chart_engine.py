import ccxt
import pandas as pd

# =========================================
# EXCHANGES
# =========================================

binance = ccxt.binance()
okx = ccxt.okx()

# =========================================
# RAW FETCH (μόνο εσωτερική χρήση)
# =========================================

def fetch_ohlcv_data(symbol="BTC/USDT", timeframe="1h", limit=100):
    # Normalize symbol for exchanges (Binance/OKX prefer BTC/USDT not BTC-USD)
    norm_symbol = symbol.replace("-", "/").replace("USD", "USDT") if "USD" in symbol and "USDT" not in symbol else symbol
    if norm_symbol != symbol:
        print(f"Normalized symbol {symbol} -> {norm_symbol}")
        symbol = norm_symbol
    try:
        print(f"Using Binance for {symbol}")
        data = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if data:
            return data
        raise ValueError("Empty data from Binance")
    except Exception as e:
        print(f"Binance failed for {symbol} ({e}), trying OKX...")
        try:
            data = okx.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return data
        except Exception as e2:
            print(f"OKX also failed for {symbol}: {e2}")
            return None  # upper layer will handle gracefully

# =========================================
# LEGACY / RAW FUNCTION (χρησιμοποιείται από το service)
# =========================================

def _legacy_get_chart_data(symbol="BTC/USDT", timeframe="1h", limit=100):
    ohlcv = fetch_ohlcv_data(symbol, timeframe, limit)
    
    if not ohlcv:
        raise Exception(f"No valid chart data for {symbol} (fetch returned empty)")
    
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # SMA20
    df["SMA20"] = df["close"].rolling(20).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df = df.dropna()
    if df.empty:
        raise Exception(f"No valid chart data for {symbol}")
    return df

# =========================================
# PUBLIC API (για backward compatibility)
# =========================================

def get_chart_data(symbol="BTC/USDT", timeframe="1h", limit=100):
    """Παλιά συνάρτηση - τώρα περνάει από το service"""
    from market_data_service import get_chart_data as cached_get
    return cached_get(symbol, timeframe, limit)