"""
Telegram Engine - 6 Message AI Briefing
"""

import requests
import os
import re
import time
from logger import log

# ========================================
# HTML safety for parse_mode="HTML"
# ========================================
# Telegram rejects (HTTP 400) any message whose HTML is invalid. LLM-generated
# market text routinely contains bare '&' and '<' — e.g. "S&P 500", "P/E < 15",
# "AT&T" — which makes Telegram DROP that message. The old code ignored the
# return value and printed "6 messages sent successfully" regardless, so those
# losses were invisible.
#
# We escape everything, then restore ONLY the small set of tags Telegram
# actually supports and that our own headers use. Content is unchanged — it
# just renders instead of failing.
_ALLOWED_TAGS = ("b", "strong", "i", "em", "u", "s", "code", "pre", "blockquote")


def _redact(text) -> str:
    """Strip the bot token out of anything we log.

    The Telegram URL embeds the token, and requests' exception messages quote
    the full URL — e.g. "Max retries exceeded with url: /bot123456:AA.../sendMessage".
    A single DNS hiccup would otherwise write the live token into
    logs/market_agent_<date>.log in plaintext.
    """
    s = str(text)
    s = re.sub(r"/bot\d+:[A-Za-z0-9_\-]+", "/bot<REDACTED>", s)
    tok = getattr(config, "TELEGRAM_BOT_TOKEN", None)
    if tok:
        s = s.replace(tok, "<REDACTED>")
    return s


def escape_html_keep_tags(text: str) -> str:
    if not text:
        return ""
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for tag in _ALLOWED_TAGS:
        out = out.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        out = out.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return out


def _split_safely(text: str, limit: int = 3900):
    """Chunk without cutting through an HTML tag or mid-line where avoidable."""
    if len(text) <= limit:
        return [text]
    chunks, buf = [], ""
    for line in text.splitlines(keepends=True):
        if len(buf) + len(line) > limit and buf:
            chunks.append(buf)
            buf = ""
        while len(line) > limit:                      # pathological single line
            cut = line.rfind(" ", 0, limit) or limit
            cut = cut if cut > 0 else limit
            chunks.append(line[:cut])
            line = line[cut:]
        buf += line
    if buf:
        chunks.append(buf)
    # Never end a chunk inside a tag.
    return [c for c in chunks if c.strip()]

# ========================================
# Robust Config & .env Loading
# ========================================
try:
    from config import config
except Exception:
    class _DummyConfig:
        TELEGRAM_BOT_TOKEN = None
        TELEGRAM_CHAT_ID = None
        TELEGRAM_CHANNEL_ID = None
    config = _DummyConfig()

def _load_simple_env(path):
    vals = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = [x.strip() for x in line.split("=", 1)]
                        vals[k.upper()] = v.strip("\"' ")
        except:
            pass
    return vals

_env_path = os.path.join(os.path.dirname(__file__ or "."), ".env")
_env = _load_simple_env(_env_path)
_cwd_env = _load_simple_env(os.path.join(os.getcwd(), ".env"))
_env.update({k: v for k, v in _cwd_env.items() if k not in _env})

if not getattr(config, "TELEGRAM_BOT_TOKEN", None):
    config.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or _env.get("TELEGRAM_BOT_TOKEN")
if not getattr(config, "TELEGRAM_CHAT_ID", None):
    config.TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or _env.get("TELEGRAM_CHAT_ID")
if not getattr(config, "TELEGRAM_CHANNEL_ID", None):
    config.TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID") or _env.get("TELEGRAM_CHANNEL_ID")

# ========================================
# Core Telegram Sender
# ========================================
def send_telegram_message(message: str, chat_id: int = None):
    """Send message with automatic chunking"""
    if not config.TELEGRAM_BOT_TOKEN:
        log.warning("Telegram not configured")
        return False

    # No hardcoded destination. This used to fall back to the author's own
    # channel, which meant a fresh clone with only a bot token set would aim
    # its briefings at a stranger's channel.
    target = (chat_id
              or getattr(config, "TELEGRAM_CHANNEL_ID", None)
              or getattr(config, "TELEGRAM_CHAT_ID", None))
    if not target:
        log.warning("Telegram has a token but no destination: set "
                    "TELEGRAM_CHANNEL_ID or TELEGRAM_CHAT_ID in .env")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    chunks = _split_safely(message)
    success_count = 0

    for i, chunk in enumerate(chunks, 1):
        payload = {"chat_id": target, "text": chunk, "parse_mode": "HTML"}
        for attempt in range(1, 4):                     # up to 3 tries per chunk
            try:
                r = requests.post(url, data=payload, timeout=20)
                if r.status_code == 200:
                    log.success(f"Telegram chunk {i}/{len(chunks)} sent")
                    success_count += 1
                    break
                if r.status_code == 429:                # rate limited — obey retry_after
                    wait = 3
                    try:
                        wait = int(r.json().get("parameters", {}).get("retry_after", 3))
                    except Exception:
                        pass
                    log.warning(f"Telegram rate limited, waiting {wait}s (chunk {i})")
                    time.sleep(wait + 1)
                    continue
                if r.status_code == 400:
                    # Bad HTML — resend the same content as plain text rather
                    # than losing the message entirely.
                    log.error(_redact(f"Telegram 400 on chunk {i}: {r.text[:180]}"))
                    plain = re.sub(r"<[^>]+>", "", chunk)
                    plain = (plain.replace("&amp;", "&").replace("&lt;", "<")
                                  .replace("&gt;", ">"))
                    r2 = requests.post(url, data={"chat_id": target, "text": plain},
                                       timeout=20)
                    if r2.status_code == 200:
                        log.warning(f"Chunk {i} delivered as PLAIN TEXT (HTML was invalid)")
                        success_count += 1
                    break
                log.error(_redact(f"Telegram failed ({r.status_code}) chunk {i}: {r.text[:180]}"))
                break
            except Exception as e:
                log.error(_redact(f"Telegram error chunk {i} attempt {attempt}: {e}"))
                time.sleep(2)
        time.sleep(0.4)                                  # stay under the flood limit

    ok = success_count == len(chunks)
    if not ok:
        log.error(f"Telegram: only {success_count}/{len(chunks)} chunks delivered")
    return ok

# ========================================
# Full AI Briefing - 6 Messages
# ========================================
def send_full_ai_briefing():
    """Send full briefing as 6 separate messages"""
    log.info("🚀 Generating Full AI Market Briefing (6 messages)...")

    # Lazy imports
    from master_market_brain import generate_master_report
    from market_snapshot_engine import generate_market_snapshot
    from macro_tech_report import generate_macro_tech_report
    from ai_advisor_engine import generate_ai_advisor
    from geopolitical_engine import geopolitical_engine
    from corporate_news_engine import corporate_news_engine   # ← NEW

    # Each section is generated INDEPENDENTLY. Previously all six were built
    # before anything was sent, so a single failing generator (or a missing dict
    # key like geo['key_events']) silently killed the ENTIRE briefing.
    try:
        from llm_client import is_llm_error, is_llm_draft
    except Exception:
        def is_llm_error(t):
            return not (t or "").strip() or (t or "").strip().startswith("(LLM error")

        def is_llm_draft(t):
            return False

    # Every failed section carries this. Without it, `delivered` counted
    # MESSAGES SENT rather than sections that actually contained analysis: six
    # placeholder messages deliver perfectly, so all six sections could fail and
    # the log still read "✅ Full AI Briefing sent (6/6 messages)".
    FAILED_MARK = "⚠️​"          # warning sign + zero-width space

    def _safe(label, fn, default="(section unavailable this run)"):
        try:
            out = fn()
        except Exception as e:
            log.error(f"Briefing section '{label}' failed: {type(e).__name__}: {e}")
            return f"{FAILED_MARK}{default}\n[{type(e).__name__}: {str(e)[:200]}]"
        # llm_client.chat() RETURNS an error string instead of raising, so the
        # hand-written fallbacks inside the engines never fire and the raw
        # sentinel used to be published to Telegram as if it were analysis.
        if is_llm_error(str(out)):
            log.error(f"Briefing section '{label}': LLM backend returned an error sentinel")
            return (FAILED_MARK + "This section could not be generated — the "
                    "local LLM backend did not respond. Check that llama-server "
                    "is running with the market model "
                    "(run: powershell -File check-briefing-model.ps1).")

        # A DRAFT is not an answer. The model's scratchpad is recovered when it
        # spends its whole budget reasoning and never writes a reply; it is real
        # text, so it passed the is_llm_error gate and was published under the
        # ADVISOR and MACRO headers as though it were the analysis. It reads
        # like thinking out loud, because that is what it is.
        if is_llm_draft(str(out)):
            log.error(f"Briefing section '{label}': the model returned only a draft")
            return (FAILED_MARK + "This section is NOT analysis — the model spent "
                    "its whole budget reasoning and never wrote an answer. What it "
                    "was working through is below, unedited:\n\n" + str(out))
        return out

    master = _safe("master", lambda: generate_master_report("BTC/USDT"))
    snapshot = _safe("snapshot", generate_market_snapshot)
    macro = _safe("macro", generate_macro_tech_report)
    # generate_ai_advisor(master, snapshot) was called unconditionally. When
    # master failed, `master` held the FAILED_MARK placeholder — "This section
    # could not be generated..." — and that string was handed to the advisor as
    # if it were the market report. The advisor then produced a confident
    # portfolio allocation derived from an error message, under a header the
    # reader trusts. An allocation built on nothing is worse than no allocation.
    _inputs_failed = [name for name, text in (("master", master), ("snapshot", snapshot))
                      if FAILED_MARK in str(text)]
    if _inputs_failed:
        log.error(f"Briefing section 'advisor': refusing to run — "
                  f"{', '.join(_inputs_failed)} failed, so there is nothing to advise on")
        advisor = (FAILED_MARK + "No recommendation was produced: the "
                   f"{' and '.join(_inputs_failed)} section(s) failed, so the advisor "
                   "had no market data to reason about. A position built on a "
                   "missing report would be a guess wearing a header.")
    else:
        advisor = _safe("advisor", lambda: generate_ai_advisor(master, snapshot))
    geo = _safe("geopolitical",
                lambda: geopolitical_engine.analyze_geopolitical_risk()["key_events"])
    corporate = _safe("corporate",
                      lambda: corporate_news_engine.get_corporate_news()["key_corporate_events"])

    # 6 ξεχωριστά μηνύματα. Ο τίτλος μένει ως έχει (δικά μας <b> tags)· μόνο το
    # περιεχόμενο του μοντέλου περνά από escaping ώστε να μη γίνει drop από 400.
    sections = [
        ("🌍 iNFO DUST MARKET BRAIN", master),
        ("📊 MARKET SNAPSHOT", snapshot),
        ("📈 MACRO &amp; TECH SENTIMENT", macro),
        ("🧠 iNFO DUST ADVISOR", advisor),
        ("🌍 GEOPOLITICAL RISK ANALYSIS", geo),
        ("🏢 CORPORATE &amp; EARNINGS NEWS", corporate),
    ]

    generated = sum(1 for _, b in sections if not str(b).startswith(FAILED_MARK))
    delivered = 0
    for title, body in sections:
        try:
            if send_telegram_message(f"<b>{title}</b>\n\n{escape_html_keep_tags(str(body))}"):
                delivered += 1
        except Exception as e:
            log.error(_redact(f"Sending '{title}' raised: {e}"))

    n = len(sections)
    # Two different numbers, and only reporting the second one hid total failure
    # behind a green log line: a placeholder message delivers just as reliably as
    # a real report.
    if generated == n and delivered == n:
        log.success(f"✅ Full AI Briefing sent ({delivered}/{n} messages, "
                    f"{generated}/{n} sections generated)")
        print(f"[telegram_engine] {delivered} messages sent successfully")
    elif generated == 0:
        log.error(f"❌ Briefing produced NO content: 0/{n} sections generated. "
                  f"{delivered}/{n} placeholder messages were delivered.")
        print(f"[telegram_engine] FAILED: no section could be generated")
    else:
        log.error(f"⚠️ Briefing incomplete: {generated}/{n} sections generated, "
                  f"{delivered}/{n} messages delivered")
        print(f"[telegram_engine] WARNING: {generated}/{n} sections, "
              f"{delivered}/{n} messages")
    return generated == n and delivered == n