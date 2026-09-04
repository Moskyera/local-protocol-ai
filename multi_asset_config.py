# =========================================
# MULTI ASSET CONFIG
# =========================================
# BINANCE SYMBOL FORMAT
# =========================================

# =========================================
# MAJOR CRYPTO
# =========================================

MAJOR_CRYPTO = [

    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT"
]

# =========================================
# ALTCOINS
# =========================================

ALTCOINS = [

    "DOGE/USDT",
    "LINK/USDT",
    "AVAX/USDT",

    "MATIC/USDT",
    "DOT/USDT",
    "ATOM/USDT",

    "NEAR/USDT",
    "ARB/USDT",
    "OP/USDT"
]

# =========================================
# MEME / HIGH VOLATILITY
# =========================================

HIGH_RISK_ASSETS = [

    "PEPE/USDT",
    "SHIB/USDT",
    "BONK/USDT"
]

# =========================================
# CUSTOM WATCHLIST
# =========================================
# REMOVED HEX
# =========================================

CUSTOM_SYMBOLS = []

# =========================================
# PULSECHAIN PLACEHOLDERS
# =========================================
# NOT SUPPORTED YET
# FUTURE:
# CoinGecko / DexScreener API
# =========================================

PULSECHAIN_ASSETS = [

    "PLS",
    "PLSX",
    "HAC",
    "HACD"
]

# =========================================
# COMBINED
# =========================================

ALL_SYMBOLS = (

    MAJOR_CRYPTO

    + ALTCOINS

    + HIGH_RISK_ASSETS

    + CUSTOM_SYMBOLS
)