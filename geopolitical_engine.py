"""
Geopolitical Engine v41 - Pure Tavily Real-Time Search (Last 48h + Strict Filters, No LLM)
"""

from logger import log
from config import config
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


class GeopoliticalEngine:
    def __init__(self):
        self.api_key = getattr(config, "TAVILY_API_KEY", None) or os.environ.get("TAVILY_API_KEY")

        # === STRICT FILTERS FOR PURE GEOPOLITICS (last ~48h only) ===

        # Must contain at least one of these regions/entities
        self.key_entities = [
            "iran", "israel", "gaza", "hamas", "hezbollah", "lebanon", "beirut",
            "russia", "ukraine", "kyiv", "moscow", "donbas",
            "china", "taiwan", "beijing", "south china sea",
            "north korea", "pyongyang", "syria", "yemen", "houthis", "red sea",
            "hormuz", "persian gulf", "middle east", "straits of hormuz",
            # Major actors that were missing entirely. Measured on twelve real
            # conflict headlines: after the blocklist was fixed, four were still
            # discarded for "no entity" — NATO, India/Pakistan, the UN and
            # Turkey/Egypt/Saudi are as geopolitical as anything already listed.
            "nato", "india", "pakistan", "kashmir", "afghanistan", "iraq",
            "turkey", "egypt", "saudi", "united nations", "un security council",
            "venezuela", "sudan", "libya", "somalia", "sahel", "myanmar",
            "armenia", "azerbaijan", "serbia", "kosovo", "belarus", "poland",
            "baltic", "black sea", "suez", "strait of taiwan", "korea"
        ]

        # Must contain at least one conflict / military / escalation action word
        self.conflict_indicators = [
            "war", "conflict", "strike", "airstrike", "missile", "ballistic", "drone",
            "attack", "invasion", "escalat", "tension", "retaliat", "bomb", "shelling",
            "sanction", "ceasefire", "truce", "military", "forces", "troop", "naval",
            "fired", "launched", "clash", "hostilit", "strike on", "retaliatory strike"
        ]

        # Hard blocks: discard immediately if any of these appear (prevents crypto, sports, earnings etc)
        self.blocklist = [
            "crypto", "bitcoin", "btc", "ethereum", "sol", "nft", "blockchain", "web3",
            "earnings", "revenue", "profit", "q1", "q2", "q3", "q4", "results",
            "stock", "shares", "ipo", "merger", "acquisition", "analyst", "price target",
            "nba", "nfl", "mlb", "epl", "football", "tennis", "cricket", "olympics", "fifa",
            "celebrity", "movie", "netflix", "trailer", "award", "music",
            # very generic market noise
            "fed rate", "interest rate decision", "earnings beat"
        ]

        # Domains that are usually off-topic or too crypto/finance focused for pure geo
        self.exclude_domains = [
            "cryptobriefing.com",
            "coindesk.com",
            "cointelegraph.com",
            "decrypt.co",
            "theblock.co",
        ]

    def _parse_date(self, date_str: str):
        """Parse Tavily published_date (e.g. 'Wed, 03 Jun 2026 00:46:36 GMT')."""
        if not date_str:
            return None
        try:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _is_within_48h(self, pub_date_str: str) -> bool:
        """Strict 48-hour (plus small buffer) recency gate."""
        dt = self._parse_date(pub_date_str)
        if dt is None:
            # If no date, still accept (Tavily days=2 should have filtered)
            return True
        now = datetime.now(timezone.utc)
        hours = (now - dt).total_seconds() / 3600
        return hours <= 54  # small buffer for timezone / indexing lag

    def _clean_snippet(self, text: str, max_len: int = 170) -> str:
        """Conservative cleaning: only return real article prose, never start mid-sentence junk."""
        if not text:
            return ""
        t = text.strip()

        # Never start with these
        bad_starts = ("skip to", "advertisement", "sign up", "follow", "add ", "latest news",
                      "world &", "politics &", "u.s.", "global ", "item ", "tap to")
        for _ in range(4):
            low = t.lower()
            if any(low.startswith(bs) for bs in bad_starts) or len(t.split()[0]) < 3:
                # drop first "word/sentence"
                parts = t.split(maxsplit=1)
                t = parts[1] if len(parts) > 1 else ""
            else:
                break
        t = t.strip(" -:•\n,")

        # If after stripping we are left with something that looks like title fragment, drop it
        if len(t) < 40:
            return ""

        # Prefer first paragraph with actual content
        if "\n\n" in t:
            for p in t.split("\n\n"):
                pp = p.strip()
                if len(pp) > 45 and any(w in pp.lower() for w in ["said", "killed", "launched", "strike", "attack", "official", "according"]):
                    t = pp
                    break
            else:
                t = t.split("\n\n")[0].strip()

        # Final length + nice cutoff
        if len(t) > max_len:
            t = t[:max_len].rsplit(" ", 1)[0].strip()
            if t and not t[-1] in ".!?…":
                t += "..."

        low2 = t.lower()
        if any(b in low2[:25] for b in ["advertisement", "skip to", "sign up"]):
            return ""

        return t.strip()

    def _blocked_re(self):
        """One word-boundary regex over the blocklist, compiled once.

        Word boundaries are Unicode-aware and handles the multi-word entries ("fed rate",
        "price target") unchanged.
        """
        if getattr(self, "_blocked_cache", None) is None:
            import re as _re
            parts = sorted((b.lower() for b in self.blocklist), key=len, reverse=True)
            self._blocked_cache = _re.compile(
                r"\b(?:%s)\b" % "|".join(_re.escape(p) for p in parts))
        return self._blocked_cache

    def _is_pure_geopolitical(self, title: str, content: str) -> bool:
        """Multi-layer filter to keep ONLY real geopolitical / conflict news."""
        text = f"{title} {content}".lower()

        # 1. Hard blocklist — WORD BOUNDARIES, not substrings.
        # Measured on twelve real conflict headlines, bare `bad in text` threw
        # away six of them: "nfl" matched inside "conflict" (three times, and
        # "conflict" is itself one of the conflict_indicators this engine looks
        # for), "epl" inside "deployed", "sol" inside "soldiers" and
        # "resolution", "stock" inside "Stockholm". The filter was deleting
        # exactly the coverage it exists to find, silently.
        if self._blocked_re().search(text):
            return False

        # 2. Must mention a relevant geopolitical entity/region
        has_entity = any(entity in text for entity in self.key_entities)
        if not has_entity:
            return False

        # 3. Must mention a conflict, military, sanction or escalation action
        has_conflict = any(indicator in text for indicator in self.conflict_indicators)
        if not has_conflict:
            return False

        return True

    def analyze_geopolitical_risk(self):
        log.info("Geopolitical Engine v41: Pure Tavily real-time search (last 48h + strict geo filters)...")

        if not self.api_key:
            log.warning("No Tavily API key found")
            return self._fallback("δεν έχει οριστεί Tavily API key", checked=False)

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self.api_key)

            # Highly targeted query. Tavily will apply recency via time_range + days
            query = (
                '("middle east" OR iran OR israel OR gaza OR hezbollah OR hamas OR "red sea" OR hormuz OR '
                'russia OR ukraine OR "north korea" OR taiwan OR "south china sea" OR syria OR yemen OR houthis) '
                '(war OR conflict OR strike OR missile OR drone OR escalation OR attack OR invasion OR '
                'tension OR sanctions OR retaliation OR ceasefire OR "military strike" OR clash OR hostilities)'
            )

            response = client.search(
                query=query,
                topic="news",                # critical: news-optimized index + better recency
                time_range="day",
                days=2,                      # last ~48 hours
                search_depth="advanced",
                max_results=12,
                include_answer=False,
                exclude_domains=self.exclude_domains,
            )

            raw_results = response.get("results", []) if response else []

            if not raw_results:
                # The search ran and returned nothing at all — that is a
                # failed query, not a quiet world.
                return self._fallback("η αναζήτηση δεν επέστρεψε κανένα "
                                      "αποτέλεσμα", checked=False)

            events = []
            for r in raw_results:
                title = (r.get("title") or "").strip()
                content = (r.get("content") or "").strip()
                pub_date = r.get("published_date")

                if not title or len(content) < 25:
                    continue

                # === STRICT FILTERS ===
                if not self._is_within_48h(pub_date):
                    continue
                if not self._is_pure_geopolitical(title, content):
                    continue

                # Clean snippet (aggressive boilerplate removal)
                snippet = self._clean_snippet(content, max_len=170)

                # Only append detail line if it adds meaningful new info (not just title repeat)
                title_lower = title.lower()
                # Try to get clean source domain
                source = ""
                try:
                    u = urlparse(r.get("url", ""))
                    if u.netloc:
                        source = u.netloc.replace("www.", "")
                except Exception:
                    pass

                display_title = f"{title} ({source})" if source else title

                # Only show detail line when cleaned text is clearly useful prose (not repeating title or junk)
                show_detail = (
                    snippet and len(snippet) > 38 and
                    not any(j in snippet.lower() for j in ["advertisement", "world & nation", "###", "skip to", "sign up", "item "]) and
                    not title_lower.startswith(snippet[:30].lower())
                )
                if show_detail:
                    events.append(f"• {display_title}\n  {snippet}")
                else:
                    events.append(f"• {display_title}")

                if len(events) >= 6:
                    break

            if not events:
                # Results came back and the filters kept none. This one IS a
                # real answer: we looked, nothing qualified.
                return self._fallback(checked=True)

            events_text = "\n\n".join(events)

            # Lightweight risk heuristic (volume + strong action words) - no LLM
            risk_level = self._calculate_risk_level(events_text)

            return {
                "geopolitical_risk_level": risk_level,
                "key_events": events_text,
                "market_impact": "Recent geopolitical developments (last 48h) are influencing market volatility, risk sentiment and safe-haven demand.",
                "ai_adjustment": "Monitor closely - possible adjustment to risk mode, energy exposure and cash allocation."
            }

        except Exception as e:
            log.error(f"Tavily error: {e}")
            return self._fallback(f"{type(e).__name__}: {str(e)[:80]}",
                                  checked=False)

    def _calculate_risk_level(self, events_text: str) -> str:
        """Simple non-LLM risk scoring based on signal strength."""
        t = events_text.lower()
        high = ["strike", "missile", "attack", "invasion", "escalation", "ballistic", "retaliatory", "killed", "war"]
        medium = ["tension", "sanctions", "drone", "clash", "hostilities", "military"]

        high_count = sum(1 for w in high if w in t)
        med_count = sum(1 for w in medium if w in t)

        # Many strong signals or lots of content → HIGH
        if high_count >= 2 or (high_count >= 1 and len(events_text) > 900):
            return "HIGH"
        if high_count >= 1 or med_count >= 2 or len(events_text) > 550:
            return "MEDIUM"
        return "LOW"

    def _fallback(self, reason: str = "", checked: bool = True):
        """The answer when no events are reported — which is TWO answers.

        This used to return one: risk LOW, "no significant events detected",
        "neutral to low geopolitical risk environment". Byte-identical whether
        the scan ran and found a quiet world, or the API key was missing, or the
        request raised. Three of its four call sites are failures. A reader of
        the daily briefing saw an affirmative all-clear on geopolitical risk
        while nothing had been checked at all.
        """
        if checked:
            return {
                "geopolitical_risk_level": "LOW",
                "key_events": "No significant high-relevance geopolitical events "
                              "detected in the last 48 hours.",
                "market_impact": "Neutral to low geopolitical risk environment.",
                "ai_adjustment": "No immediate adjustment required",
                "scan_performed": True,
            }
        return {
            "geopolitical_risk_level": "UNKNOWN",
            "key_events": f"⚠️ Ο έλεγχος γεωπολιτικού κινδύνου ΔΕΝ ΕΓΙΝΕ "
                          f"({reason or 'unknown reason'}). Αυτό ΔΕΝ σημαίνει "
                          f"ότι δεν υπάρχουν γεγονότα — σημαίνει ότι δεν "
                          f"κοιτάξαμε.",
            "market_impact": "Άγνωστο — δεν ανακτήθηκαν δεδομένα.",
            "ai_adjustment": "Μην βασιστείς σε αυτή την ενότητα αυτή τη φορά.",
            "scan_performed": False,
            "failure_reason": reason,
        }


# Register
geopolitical_engine = GeopoliticalEngine()
