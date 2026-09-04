import finnhub
import time
from config import config
from logger import log

client = finnhub.Client(api_key=config.FINNHUB_API_KEY)

# Simple cache για stocks
_stock_cache = {}
CACHE_TTL = 60  # 60 δευτερόλεπτα

def get_stock_price(symbol: str):
    now = time.time()
    
    # Check cache
    if symbol in _stock_cache:
        data, timestamp = _stock_cache[symbol]
        if now - timestamp < CACHE_TTL:
            return data

    try:
        quote = client.quote(symbol)
        current = quote.get("c", 0)
        previous = quote.get("pc", current) or current

        # Finnhub signals "no data for this symbol" with HTTP 200 and every
        # field zero — an unknown ticker, a symbol outside the plan, a rate
        # limit. Nothing raises, so the exception path below never sees it, and
        # a zeroed quote used to sail through as a real price of $0.00 with a
        # 0% change, which the briefing painted 🟢 GREEN and fed to the vote.
        # The discriminator has to be "is there a price", not "did it raise".
        if not current or current <= 0:
            log.warning(f"Stock engine: {symbol} returned no usable quote "
                        f"(c={quote.get('c')}, pc={quote.get('pc')}, t={quote.get('t')})")
            return {"price": None, "change": None,
                    "error": "no data returned for this symbol"}

        # A real price with no previous close (new listing, missing history) is
        # a known price and an UNKNOWN change. Reporting 0% there would be the
        # same lie in a smaller place, so the change is None and the price
        # survives — `previous = quote.get("pc", current) or current` used to
        # paper over it by substituting the current price, yielding a flat 0%.
        raw_pc = quote.get("pc")
        if not raw_pc or raw_pc <= 0:
            log.warning(f"Stock engine: {symbol} has no previous close "
                        f"(pc={raw_pc}) — price kept, change unknown")
            return {"price": round(current, 2), "change": None,
                    "error": "no previous close, change unknown"}

        previous = raw_pc
        change = ((current - previous) / previous * 100) if previous != 0 else 0

        result = {
            "price": round(current, 2),
            "change": round(change, 2)
        }

        _stock_cache[symbol] = (result, now)
        return result

    except Exception as e:
        # NOT {"price": 0, "change": 0}. A failed fetch is not a flat day, and
        # downstream `if change < 0` painted it 🟢 GREEN at $0 — a stock that was
        # never retrieved rendered as an up-tick in the daily briefing.
        log.warning(f"Stock engine error for {symbol}: {e}")
        return {"price": None, "change": None, "error": str(e)[:120]}