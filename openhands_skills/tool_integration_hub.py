"""
Tool Integration Hub v3 for OpenHands
Πλήρης σύνδεση του OpenHands με το market-agent project σου

Note: All heavy market imports are lazy (inside methods) so this module can be safely imported
in isolated environments like OpenHands sandbox without the full market-agent installed.
Fallbacks return informative messages.
"""

def _get_log():
    try:
        from logger import log
        return log
    except Exception:
        class _DummyLog:
            def info(self, *a, **k): pass
            def error(self, *a, **k): pass
            def warning(self, *a, **k): pass
        return _DummyLog()

def _lazy_import_market(func_name):
    """Lazy import to avoid top-level dependency on market engines.
    (Sacred briefing files are protected by guards; this bridge is intentionally in the allowed skills area.)
    """
    try:
        if func_name == "generate_market_snapshot":
            from market_snapshot_engine import generate_market_snapshot
            return generate_market_snapshot
        elif func_name == "generate_master_report":
            from master_market_brain import generate_master_report
            return generate_master_report
        elif func_name == "generate_macro_tech_report":
            from macro_tech_report import generate_macro_tech_report
            return generate_macro_tech_report
        # These two were missing, which is how a briefing could be reported as
        # sent without anything being sent. Importing from telegram_engine is
        # fine — that file is read-only, not untouchable.
        elif func_name == "send_full_ai_briefing":
            from telegram_engine import send_full_ai_briefing
            return send_full_ai_briefing
        elif func_name == "generate_ai_advisor":
            from ai_advisor_engine import generate_ai_advisor
            return generate_ai_advisor
        # add others as needed (keep lazy so sandbox/Docker contexts don't explode)
    except Exception as exc:
        err = str(exc)
        def _fail(*a, **k):
            return Unavailable(f"[{func_name}] Not available in this environment: "
                               f"{err}. (Expected in the OpenHands sandbox; use "
                               f"public APIs for chain data.)")
        return _fail
    return lambda *a, **k: Unavailable(f"[{func_name}] not wired into "
                                       f"_lazy_import_market.")

class Unavailable(str):
    """A function that could not be imported returns THIS, not a plain string.

    Measured: _lazy_import_market had no branch for send_full_ai_briefing, so it
    fell through to a plain string. The string was truthy, `if success:` passed,
    and send_telegram_briefing() answered "✅ Full AI Briefing sent to Telegram
    successfully" having made zero network calls. A green tick on a delivery
    that never happened is the worst failure this repo can produce.

    Subclassing str keeps every existing caller working — the text still reads
    the same — while __bool__ makes the truthiness test tell the truth.
    """

    def __bool__(self) -> bool:
        return False


def is_unavailable(x) -> bool:
    return isinstance(x, Unavailable)


class ToolIntegrationHub:
    def run_master_report(self, symbol: str = "BTC/USDT"):
        """Τρέχει το Master AI Market Brain Report"""
        log = _get_log()
        log.info(f"[Tool Hub] Master Report requested for {symbol}")
        try:
            generate_master_report = _lazy_import_market("generate_master_report")
            report = generate_master_report(symbol)
            print(report)
            return report
        except Exception as e:
            log.error(f"Master Report failed: {e}")
            return f"Error generating Master Report: {e} (market engines may not be available in OpenHands env)"

    def run_market_snapshot(self):
        """Τρέχει το Market Snapshot (τιμές crypto + stocks)"""
        log = _get_log()
        log.info("[Tool Hub] Market Snapshot requested")
        try:
            generate_market_snapshot = _lazy_import_market("generate_market_snapshot")
            snapshot = generate_market_snapshot()
            print(snapshot)
            return snapshot
        except Exception as e:
            log.error(f"Market Snapshot failed: {e}")
            return f"Error generating Market Snapshot: {e} (using on-chain data only)"

    def run_macro_report(self):
        """Τρέχει το Macro & Tech Sentiment Report"""
        log = _get_log()
        log.info("[Tool Hub] Macro & Tech Report requested")
        try:
            generate_macro_tech_report = _lazy_import_market("generate_macro_tech_report")
            macro = generate_macro_tech_report()
            print(macro)
            return macro
        except Exception as e:
            log.error(f"Macro Report failed: {e}")
            return f"Error generating Macro Report: {e} (market engines may not be available in OpenHands env)"

    def run_ai_advisor(self):
        """Τρέχει το AI Advisor (Reasoning + Portfolio)"""
        log = _get_log()
        log.info("[Tool Hub] AI Advisor requested")
        try:
            generate_ai_advisor = _lazy_import_market("generate_ai_advisor")
            advisor = generate_ai_advisor("Master Report", "Snapshot")
            print(advisor)
            return advisor
        except Exception as e:
            log.error(f"AI Advisor failed: {e}")
            return f"Error generating AI Advisor: {e} (market engines may not be available in OpenHands env)"

    def send_telegram_briefing(self):
        """Στέλνει πλήρες briefing στο Telegram"""
        log = _get_log()
        log.info("[Tool Hub] Full Telegram Briefing requested")
        try:
            send_full_ai_briefing = _lazy_import_market("send_full_ai_briefing")
            success = send_full_ai_briefing()
            if is_unavailable(success):
                return f"❌ Δεν στάλθηκε τίποτα — {success}"
            # Only an explicit True counts. telegram_engine returns a bool; any
            # other truthy value means something unexpected happened and must
            # NOT be reported as a delivery.
            if success is True:
                return "✅ Full AI Briefing sent to Telegram successfully"
            return f"❌ Failed to send Telegram briefing (returned {success!r})"
        except Exception as e:
            log.error(f"Telegram briefing failed: {e}")
            return f"Error sending Telegram briefing: {e} (telegram may not be configured in this env)"

    def get_current_signal(self, symbol: str = "BTC/USDT"):
        """Επιστρέφει το τρέχον signal"""
        log = _get_log()
        log.info(f"[Tool Hub] Current signal requested for {symbol}")
        try:
            from signal_engine import generate_signal
            signal = generate_signal(symbol)
            print(signal)
            return signal
        except Exception as e:
            log.error(f"Signal generation failed: {e}")
            return f"Error getting signal: {e} (signal engine may not be available)"

# Register the hub
tool_hub = ToolIntegrationHub()