import requests

# =========================================
# PULSECHAIN TOKENS
# =========================================

TOKENS = {

    "HEX": "0x2b591e99afe9f32eaa6214f7b7629768c40eeb39",
    "PLS": "0xa1077a294dde1b09bb078844df40758a5d0f9a27",
    "PLSX": "0x95b303987a60c71504d99aa1b13b4da07b0790ab"
}

# =========================================
# GET TOKEN DATA
# =========================================

def get_pulsechain_token(symbol):

    if symbol not in TOKENS:

        return None

    address = TOKENS[symbol]

    url = (
        "https://api.dexscreener.com/latest/dex/tokens/"
        f"{address}"
    )

    response = requests.get(url)

    data = response.json()

    pair = data["pairs"][0]

    return {

        "price": float(pair["priceUsd"]),

        "change": float(
            pair["priceChange"]["h24"]
        )
    }