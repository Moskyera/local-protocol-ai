"""
Geopolitical Engine v33.3.1 - Dedup + Event Timestamp Layer
"""

from logger import log
from config import config
import os
import hashlib

try:
    from finlight_client import FinlightApi, ApiConfig
    from finlight_client.models import GetArticlesParams
    FINLIGHT_AVAILABLE = True
except ImportError:
    FINLIGHT_AVAILABLE = False


class GeopoliticalEngine:
    def __init__(self):
        self.api_key = getattr(config, "FINLIGHT_API_KEY", None) or os.environ.get("FINLIGHT_API_KEY")

        self.seen_events = set()

        self.conflict_keywords = [
            "war", "conflict", "attack", "strike", "missile",
            "drone", "bombing", "airstrike", "invasion",
            "escalation", "retaliation", "ceasefire", "military"
        ]

        self.entities = [
            "iran", "israel", "usa", "united states", "china",
            "russia", "ukraine", "taiwan", "nato", "hezbollah",
            "north korea", "syria", "lebanon"
        ]

        self.hard_noise = [
            "earnings", "revenue", "profit", "stock", "shares",
            "analyst", "ipo", "merger", "sports", "football",
            "nba", "tennis", "crypto", "bitcoin"
        ]

    # ================= MEMORY =================
    def _fingerprint(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _is_seen(self, fp: str) -> bool:
        return fp in self.seen_events

    def _mark_seen(self, fp: str):
        self.seen_events.add(fp)

    # ================= DATE EXTRACTION =================
    def _get_date(self, article):
        return (
            getattr(article, "published_at", None)
            or getattr(article, "date", None)
            or getattr(article, "time", None)
            or "Unknown date"
        )

    # ================= MAIN =================
    def analyze_geopolitical_risk(self):
        log.info("Geopolitical Engine v33.3.1: dedup + timestamps")

        if not self.api_key or not FINLIGHT_AVAILABLE:
            return self._fallback()

        try:
            client = FinlightApi(config=ApiConfig(api_key=self.api_key))
            params = GetArticlesParams(limit=25)

            response = client.articles.fetch_articles(params=params)

            articles = []
            if hasattr(response, 'articles') and response.articles:
                articles = response.articles
            elif hasattr(response, 'data') and response.data:
                articles = response.data

            if not articles:
                return self._fallback()

            filtered = self._filter(articles)

            if not filtered:
                return self._fallback()

            return self._build(filtered)

        except Exception as e:
            log.error(f"Finlight error: {e}")
            return self._fallback()

    # ================= FILTER =================
    def _filter(self, articles):
        results = []

        for article in articles:
            title = getattr(article, "title", "") or getattr(article, "headline", "")
            summary = getattr(article, "summary", "") or getattr(article, "description", "")

            text = f"{title} {summary}".lower()

            if any(x in text for x in self.hard_noise):
                continue

            has_conflict = any(x in text for x in self.conflict_keywords)
            has_entity = any(x in text for x in self.entities)

            if not (has_conflict and has_entity):
                continue

            fp = self._fingerprint(title.lower().strip())

            if self._is_seen(fp):
                continue

            self._mark_seen(fp)
            results.append(article)

        return results[:5]

    # ================= OUTPUT =================
    def _build(self, articles):
        events = []

        for article in articles:
            title = getattr(article, "title", "") or getattr(article, "headline", "No title")
            summary = getattr(article, "summary", "") or getattr(article, "description", "")

            date = self._get_date(article)

            if summary:
                summary = summary[:135] + "..." if len(summary) > 135 else summary

            events.append(f"• {title} ({date})\n  {summary}")

        return {
            "geopolitical_risk_level": "MEDIUM",
            "key_events": "\n".join(events),
            "market_impact": "Unique geopolitical anchor events (deduplicated stream)",
            "ai_adjustment": "Maintain monitoring stance"
        }

    def _fallback(self):
        return {
            "geopolitical_risk_level": "LOW",
            "key_events": "No valid geopolitical anchor events detected",
            "market_impact": "Neutral environment",
            "ai_adjustment": "No adjustment required"
        }


geopolitical_engine = GeopoliticalEngine()