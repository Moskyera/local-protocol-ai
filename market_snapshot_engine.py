# =========================================
# MARKET SNAPSHOT ENGINE - PRICES & WATCHLIST
# =========================================

from watchlist_engine import get_crypto_watchlist, get_stock_watchlist
from regime_engine import analyze_market_regime
from config import config
from logger import log

def generate_market_snapshot():
    log.info("Generating Market Snapshot for Telegram")
    
    regime = analyze_market_regime()
    crypto_list = get_crypto_watchlist()
    stock_list = get_stock_watchlist()

    report = f"""
===================================
      MARKET SNAPSHOT
===================================

OVERALL REGIME
-----------------------------------
Stocks : {regime['stock_regime']}
Crypto : {regime['crypto_regime']}
Overall: {regime['overall']}

CRYPTO PRICES (Top)
-----------------------------------
"""
    for item in crypto_list[:10]:   # Top 10 crypto
        report += f"{item}\n"

    report += """
STOCK PRICES (Top)
-----------------------------------
"""
    for item in stock_list[:12]:   # Top 12 stocks
        report += f"{item}\n"

    report += """
===================================
"""
    return report