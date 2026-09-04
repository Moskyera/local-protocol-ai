import requests

# =========================================
# CUSTOM TOKEN MAP
# =========================================

TOKEN_IDS = {

    "HEX": "hex",
    "PLS": "pulsechain",
    "PLSX": "pulsex",
    "HAC": "hacash",
    "HACD": "hacash-diamond"
}

# =========================================
# GET CUSTOM TOKEN PRICE
# =========================================

def get_custom_token(symbol):

    if symbol not in TOKEN_IDS:

        return None

    token_id = TOKEN_IDS[symbol]

    url = (
        "https://api.coingecko.com/api/v3/"
        f"coins/{token_id}"
    )

    response = requests.get(url)

    data = response.json()

    market = data["market_data"]

    return {

        "price": market["current_price"]["usd"],

        "change": market[
            "price_change_percentage_24h"
        ]
    }