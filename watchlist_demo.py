from watchlist_engine import (
    get_stock_watchlist,
    get_crypto_watchlist
)

# =========================================
# STOCKS
# =========================================

stocks = get_stock_watchlist()

print("\n===================================")
print("      STOCK WATCHLIST")
print("===================================\n")

for item in stocks:

    print(item)

# =========================================
# CRYPTO
# =========================================

crypto = get_crypto_watchlist()

print("\n===================================")
print("      CRYPTO WATCHLIST")
print("===================================\n")

for item in crypto:

    print(item)

print("\n===================================\n")