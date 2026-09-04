import ccxt

from custom_crypto import (
    get_custom_token
)

# =========================================
# EXCHANGES
# =========================================

binance = ccxt.binance()

okx = ccxt.okx()

# =========================================
# CUSTOM TOKENS
# =========================================

CUSTOM_TOKENS = [

    "HEX/USDT",

    "PLS/USDT",

    "PLSX/USDT",

    "HAC/USDT",

    "HACD/USDT"
]

# =========================================
# SAFE PRICE FORMATTER
# =========================================

def safe_price(price):

    if price >= 1:

        return round(price, 2)

    elif price >= 0.01:

        return round(price, 4)

    elif price >= 0.0001:

        return round(price, 6)

    else:

        return round(price, 10)

# =========================================
# GET CRYPTO PRICE
# =========================================

def get_crypto_price(

    symbol="BTC/USDT"
):

    # =====================================
    # CUSTOM TOKENS
    # =====================================

    if symbol in CUSTOM_TOKENS:

        token_symbol = (
            symbol.split("/")[0]
        )

        custom_data = get_custom_token(
            token_symbol
        )

        if custom_data is None:

            raise Exception(
                f"No custom data for {symbol}"
            )

        return {

            "symbol": symbol,

            "price": safe_price(
                float(
                    custom_data["price"]
                )
            ),

            "change": round(

                float(
                    custom_data["change"]
                ),

                2
            ),

            "volume": 0
        }

    # =====================================
    # TRY BINANCE
    # =====================================

    try:

        print(
            f"Using Binance for {symbol}"
        )

        ticker = binance.fetch_ticker(
            symbol
        )

    # =====================================
    # FALLBACK TO OKX
    # =====================================

    except Exception:

        print(
            f"Using OKX for {symbol}"
        )

        ticker = okx.fetch_ticker(
            symbol
        )

    # =====================================
    # SAFE VALUES
    # =====================================

    last_price = ticker.get(
        "last",
        0
    )

    percentage = ticker.get(
        "percentage",
        0
    )

    quote_volume = ticker.get(
        "quoteVolume",
        0
    )

    # =====================================
    # RETURN DATA
    # =====================================

    return {

        "symbol": symbol,

        "price": safe_price(
            float(last_price)
        ),

        "change": round(

            float(percentage),

            2

        ) if percentage is not None else 0,

        "volume": round(

            float(quote_volume),

            2

        ) if quote_volume is not None else 0
    }