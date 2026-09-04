# =========================================
# MARKET DATA SERVICE - CENTRAL CACHING LAYER
# =========================================

import time
from chart_engine import _legacy_get_chart_data
from config import config
from logger import log

# Cache settings
CACHE_TTL = 300  # 5 λεπτά
_cache = {}

def get_chart_data(symbol: str = config.DEFAULT_SYMBOL,
                   timeframe: str = config.DEFAULT_TIMEFRAME,
                   limit: int = config.DEFAULT_LIMIT):
    """Κεντρική συνάρτηση με caching"""
    key = (symbol, timeframe, limit)
    now = time.time()

    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < CACHE_TTL:
            return data

    try:
        df = _legacy_get_chart_data(symbol, timeframe, limit)
        _cache[key] = (df, now)
        log.info(f"Fetched fresh data for {symbol} {timeframe}")
        return df
    except Exception as e:
        log.error(f"MarketDataService error for {symbol}: {e}")
        if key in _cache:
            log.warning(f"Returning cached data for {symbol}")
            return _cache[key][0]
        raise