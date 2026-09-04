"""
Corporate News Engine - Dedicated Finlight (Earnings, Guidance, Company Moves - Last 48h)
"""

from logger import log
from config import config
import os
import html
import re
from datetime import datetime, timedelta, timezone

try:
    from finlight_client import FinlightApi, ApiConfig
    from finlight_client.models import GetArticlesParams
    FINLIGHT_AVAILABLE = True
except ImportError:
    FINLIGHT_AVAILABLE = False


class CorporateNewsEngine:
    def __init__(self):
        self.api_key = getattr(config, "FINLIGHT_API_KEY", None) or os.environ.get("FINLIGHT_API_KEY")

        # Strong corporate / earnings signals we want
        self.corporate_signals = [
            "earnings", "quarterly results", "results beat", "beat estimates", "missed estimates",
            "revenue", "eps", "profit", "guidance", "raised guidance", "lowered guidance",
            "outlook", "forecast", "ceo", "chief executive", "acquisition", "acquires",
            "merger", "launches", "partnership", "record revenue", "price target",
            "earnings preview", "earnings transcript", "q1", "q2", "q3", "q4"
        ]

        # Things we want to aggressively block even if they have "earnings"
        self.blocklist = [
            "crypto", "bitcoin", "nft", "blockchain",
            "war", "iran", "israel", "gaza", "hezbollah", "missile", "strike",
            "russia", "ukraine", "invasion", "escalation",
            "nba", "nfl", "sports", "football", "tennis",
            "ipo", "initial public offering", "spac", "blank check"   # too many noisy IPOs
        ]

        # Our priority universe (tech/AI heavy)
        self.watchlist_tickers = [
            "NVDA", "NVIDIA", "MSFT", "Microsoft", "AAPL", "Apple", "AMZN", "Amazon",
            "META", "GOOGL", "Google", "TSLA", "Tesla", "AMD", "Advanced Micro Devices",
            "AVGO", "Broadcom", "PLTR", "ARM", "SMCI", "INTC", "ORCL", "CRM", "ADBE", "NFLX", "HPE", "PANW"
        ]

        # Broader market context (S&P 500, index movers etc.)
        self.broad_market_terms = [
            "s&p 500", "s&p500", "spx", "s&p", "index", "market movers",
            "s&p 500 earnings", "stocks moving the s&p"
        ]

    def _get_date_range(self):
        """Last 48 hours in YYYY-MM-DD format for Finlight."""
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(hours=48)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        return from_date, to_date

    def _clean_text(self, text: str) -> str:
        """Unescape HTML and basic cleanup."""
        if not text:
            return ""
        text = html.unescape(text)
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
        return text.strip()

    def _clean_title(self, title: str) -> str:
        """Clean common noisy title patterns from news wires."""
        t = self._clean_text(title)
        # Remove leading clickbait ("Why ...", "Earnings Snippet:", "Stock Market Today")
        for bad in ["why ", "stocks to watch:", "earnings snippet:", "📈 earnings snippet:", "stock market today"]:
            if t.lower().startswith(bad):
                t = t[len(bad):].strip()
        # Strip leading date junk like ", June 2: " or "June 2: "
        t = re.sub(r'^[,\s]*[a-zA-Z]+ \d+:\s*', '', t).strip()
        t = re.sub(r'^[,\s]*\d+:\s*', '', t).strip()
        # Remove trailing fluff
        t = t.rstrip("?!., ").strip()
        for fluff in [" today", " right now", " q1 2026", " q2 2026", " q3 2026", " q4 2026"]:
            if t.lower().endswith(fluff):
                t = t[:-len(fluff)].strip()
        # Remove " - Source" if it leaked into the title field
        if " - " in t:
            parts = t.rsplit(" - ", 1)
            if len(parts) == 2 and len(parts[1]) < 40:
                t = parts[0].strip()
        return t.strip()

    def _clean_snippet(self, text: str, max_len: int = 160) -> str:
        """Clean summary for nice display."""
        if not text:
            return ""
        t = self._clean_text(text)

        # Remove common transcript / preview noise
        junk_markers = [
            "transcript", "says thank you", "good afternoon", "good morning",
            "operator", "earnings call", "conference call"
        ]
        low = t.lower()
        for marker in junk_markers:
            if marker in low[:80]:
                idx = low.find(marker)
                if 0 < idx < 120:
                    t = t[idx + len(marker):].strip(" -:•\n,")

        if "\n\n" in t:
            for p in t.split("\n\n"):
                pp = p.strip()
                if len(pp) > 35:
                    t = pp
                    break

        if len(t) > max_len:
            t = t[:max_len].rsplit(" ", 1)[0].strip()
            if t and not t[-1] in ".!?…":
                t += "..."

        return t.strip()

    def _is_relevant_corporate(self, title: str, summary: str) -> bool:
        """Strict filter - only real actionable corporate/earnings news for our focus list."""
        text = f"{title} {summary}".lower()

        # 1. Hard blocks first
        for bad in self.blocklist:
            if bad in text:
                return False

        # 2. Must have strong corporate/earnings signal
        has_signal = any(sig in text for sig in self.corporate_signals)
        if not has_signal:
            return False

        # 3. Must be relevant to us: watchlist ticker OR strong tech/AI OR S&P 500 / broad market context
        has_ticker = any(t.lower() in text for t in self.watchlist_tickers)
        has_strong_tech = any(x in text for x in [
            "nvidia", "broadcom", "avgo", "amd", "ai ", "semiconductor", "data center",
            "cloud computing", "cybersecurity", "generative ai"
        ])
        has_broad_market = any(term in text for term in self.broad_market_terms)

        if not (has_ticker or has_strong_tech or has_broad_market):
            return False

        # 4. Demote pure transcript items for non-major names
        if "transcript" in text and not (has_ticker or has_broad_market):
            return False

        return True

    def get_corporate_news(self):
        log.info("Corporate News Engine: Finlight (last 48h, dedicated earnings & corporate feed)...")

        if not self.api_key or not FINLIGHT_AVAILABLE:
            missing = ("FINLIGHT_API_KEY is not set" if not self.api_key
                       else "the finlight_client library is not installed")
            log.warning(f"Corporate news NOT checked: {missing}")
            return self._fallback(reason=missing, checked=False)

        try:
            client = FinlightApi(config=ApiConfig(api_key=self.api_key))
            from_date, to_date = self._get_date_range()

            params = GetArticlesParams(
                query='earnings OR guidance OR "beat estimates" OR "raised guidance" OR revenue OR CEO OR acquisition OR "price target" OR "s&p 500" OR spx OR "s&p500"',
                from_=from_date,
                to=to_date,
                categories=["business", "markets", "technology", "economy"],
                pageSize=15,
                orderBy="publishDate",
                order="DESC",
                excludeEmptyContent=True
            )

            response = client.articles.fetch_articles(params=params)

            articles = []
            if hasattr(response, 'articles') and response.articles:
                articles = response.articles
            elif hasattr(response, 'data') and response.data:
                articles = response.data

            if not articles:
                # The feed answered; it just had nothing. That is a real result.
                return self._fallback(checked=True)

            events = []
            for article in articles:
                raw_title = getattr(article, "title", "") or getattr(article, "headline", "")
                title = self._clean_title(raw_title)
                summary = self._clean_text(getattr(article, "summary", "") or getattr(article, "description", ""))
                source = getattr(article, "source", "") or ""

                if not title or len(summary) < 20:
                    continue

                # Strict relevance filter
                if not self._is_relevant_corporate(title, summary):
                    continue

                snippet = self._clean_snippet(summary, max_len=155)

                src_display = source.replace("www.", "") if source else ""

                if snippet and len(snippet) > 30 and not title.lower().startswith(snippet[:28].lower()):
                    line = f"• {title}"
                    if src_display:
                        line += f" ({src_display})"
                    line += f"\n  {snippet}"
                    events.append(line)
                else:
                    line = f"• {title}"
                    if src_display:
                        line += f" ({src_display})"
                    events.append(line)

                if len(events) >= 6:
                    break

            if not events:
                # Articles arrived but none qualified after filtering. Also real.
                return self._fallback(checked=True)

            events_text = "\n\n".join(events)
            sentiment = self._assess_sentiment(events_text)

            return {
                "corporate_risk_level": sentiment,
                "key_corporate_events": events_text,
                "market_impact": "Corporate earnings, guidance updates and strategic moves are influencing sector performance and individual names.",
                "ai_adjustment": "Monitor reactions in related tickers and sector rotation."
            }

        except Exception as e:
            log.error(f"Finlight Corporate News error: {e}")
            return self._fallback(reason=f"{type(e).__name__}: {str(e)[:120]}",
                                  checked=False)

    def _assess_sentiment(self, events_text: str) -> str:
        """Simple tone detection based on language in the events."""
        t = events_text.lower()
        positive = ["beat", "raised", "exceeded", "strong", "record", "surge", "pops", "climbed",
                    "jumps", "jumped", "rosy", "soared", "upping", "double beat", "growth", "higher"]
        negative = ["missed", "lowered", "weak", "cut", "downgrade", "falls", "plunges", "disappoint", "lower"]

        pos = sum(1 for w in positive if w in t)
        neg = sum(1 for w in negative if w in t)

        if pos > neg + 1:
            return "POSITIVE"
        if neg > pos:
            return "CAUTIOUS"
        return "NEUTRAL"

    def _fallback(self, reason: str = "", checked: bool = True):
        """Two different answers, because they are two different facts.

        This used to return one dictionary for both: "No major corporate
        earnings or company-specific developments detected in the last 48
        hours." — an affirmative all-clear. It was returned when the Finlight
        key was missing, when the client library was absent, and when the call
        raised. So a dead key published "nothing happened" as a finding, and the
        run reported 6/6 success. Silence from a feed that was never asked is
        not silence from the market.

        Same shape as geopolitical_engine._fallback, for the same reason.
        """
        if checked:
            return {
                "corporate_risk_level": "NEUTRAL",
                "key_corporate_events": "The corporate feed answered and no qualifying earnings or company developments were found in the last 48 hours.",
                "market_impact": "Neutral corporate environment.",
                "ai_adjustment": "No immediate adjustments required.",
                "checked": True,
            }

        why = reason or "the corporate news feed could not be reached"
        return {
            "corporate_risk_level": "UNKNOWN",
            "key_corporate_events": f"⚠️ Δεν ελέγχθηκε: {why}. Αυτό ΔΕΝ σημαίνει ότι δεν υπάρχουν εταιρικά νέα — σημαίνει ότι δεν κοιτάξαμε.",
            "market_impact": "Unknown — no corporate data was retrieved.",
            "ai_adjustment": "Treat the corporate picture as missing, not as calm.",
            "checked": False,
            "reason": why,
        }


# Register
corporate_news_engine = CorporateNewsEngine()
