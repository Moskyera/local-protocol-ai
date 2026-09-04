from stock_engine import (
    get_stock_price
)

from market_agent import (
    get_crypto_price
)

from watchlists import (
    STOCKS,
    CRYPTO
)

from pulsechain_engine import (
    get_pulsechain_token
)

# =========================================
# STOCK MARKET
# =========================================

def get_stock_watchlist():

    report = []

    for symbol in STOCKS:

        try:

            data = get_stock_price(
                symbol
            )

            current = data["price"]

            change = data["change"]

            # A quote that never arrived must not be coloured. Green at $0 read
            # as an up-tick and was counted as one.
            if current is None:

                report.append(
                    f"⚪ {symbol} | δεν ανακτήθηκε "
                    f"({data.get('error', 'no data')[:40]})"
                )

            elif change is None:

                # The price arrived; the change did not. Say exactly that
                # rather than throwing away a real number or inventing 0%.
                report.append(
                    f"⚪ {symbol} | ${current} | μεταβολή άγνωστη"
                )

            else:

                emoji = "🔴" if change < 0 else "🟢"

                report.append(

                    f"{emoji} {symbol} | "

                    f"${current} | "

                    f"{change}%"
                )

        except Exception:

            report.append(

                f"⚠️ {symbol} unavailable"
            )

    return report

# =========================================
# CRYPTO MARKET
# =========================================

def get_crypto_watchlist():

    report = []

    for symbol in CRYPTO:

        try:

            clean_symbol = (

                symbol
                .replace("/USDT", "")
            )

            # =====================================
            # PULSECHAIN TOKENS
            # =====================================

            if (

                clean_symbol == "HEX"

                or clean_symbol == "PLS"

                or clean_symbol == "PLSX"
            ):

                data = get_pulsechain_token(
                    clean_symbol
                )

            # =====================================
            # CUSTOM TOKENS
            # =====================================

            elif (

                clean_symbol == "HAC"

                or clean_symbol == "HACD"
            ):

                from custom_crypto import (
                    get_custom_token
                )

                data = get_custom_token(
                    clean_symbol
                )

            # =====================================
            # NORMAL TOKENS
            # =====================================

            else:

                data = get_crypto_price(
                    symbol
                )

            # =====================================
            # PRICE FORMAT
            # =====================================

            raw_price = data["price"]

            if raw_price >= 1:

                price = f"{raw_price:.2f}"

            elif raw_price >= 0.01:

                price = f"{raw_price:.4f}"

            else:

                price = f"{raw_price:.8f}"

            if data.get("change") is None:

                report.append(
                    f"⚪ {symbol} | δεν ανακτήθηκε "
                    f"({data.get('error', 'no data')[:40]})"
                )

            else:

                change = round(data["change"], 2)

                emoji = "🔴" if change < 0 else "🟢"

                report.append(

                    f"{emoji} {symbol} | "

                    f"${price} | "

                    f"{change}%"
                )

        except Exception:

            report.append(

                f"⚠️ {symbol} unavailable"
            )

    return report