"""The loop: hear, think, check, act, speak.

    listen -> transcribe -> model turn
        -> for each tool the model wants:
              SAFE         run
              RISKY        say what is happening, run
              DESTRUCTIVE  say what WOULD happen, wait for a spoken phrase,
                           run only on a clear yes
        -> feed results back to the model -> speak the answer

The same loop runs in text mode (no microphone) for tests and for anyone
without a headset; every safety behaviour is identical there, so what the
tests prove is what the voice path does.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import brain, config
from .greek import verbalize_el
from .guard import Risk, Verdict, announce, announce_units, interpret_confirmation, is_exit
from .tools import Registry, clamp_result, discover_mcp_tools

MAX_TOOL_ROUNDS = 6          # a model that keeps calling tools is stopped, not humoured
MAX_CONFIRM_ASKS = 2


@dataclass
class TurnLog:
    heard: str = ""
    lang: str = ""
    tool_events: list[dict] = field(default_factory=list)
    spoken: list[str] = field(default_factory=list)
    seconds: dict = field(default_factory=dict)
    final: str = ""


class Agent:
    def __init__(self, *, voice: bool = True, with_mcp: bool = True,
                 say: Optional[Callable[[str, str], None]] = None,
                 hear: Optional[Callable[[float], Optional[str]]] = None,
                 log: Callable[[str], None] = lambda s: print(s, file=sys.stderr, flush=True)):
        self.log = log
        self.history: list[dict] = []
        self.registry = Registry.build(with_mcp=with_mcp)
        self.lang = config.TTS_DEFAULT_LANG
        self.last: TurnLog = TurnLog()
        self._said_no_tools = False
        self._skip_rest = False
        self._heard = None
        self._facts_day = None
        self._facts = ""
        self._mcp_connected_late = False
        if self.registry.mcp_error:
            self._retry_mcp_in_background()
        # injectable I/O so tests drive the identical loop without audio
        self._say_override = say
        self._hear_override = hear
        self.speaker = self.listener = self.transcriber = None
        if voice:
            from .audio import Listener
            from .stt import Transcriber
            from .tts import Speaker
            self.speaker = Speaker(config.OUTPUT_DEVICE)
            self.listener = Listener(config.INPUT_DEVICE)
            self.transcriber = Transcriber()

    # ------------------------------------------------------------------ I/O
    def say(self, text: str, lang: Optional[str] = None,
            units: Optional[list[tuple[str, str]]] = None) -> bool:
        """Speak. Returns True if the owner talked over it (barge-in).
        `lang` given: every sentence goes to that voice (the agent's own
        fixed phrases). `lang` None: a model reply, each sentence routed by
        its words. `units`: explicit (text, voice) pairs from announce()."""
        self.last.spoken.append(text)
        if self._say_override:
            return bool(self._say_override(text, lang or brain.detect_lang(text, self.lang)))
        if self.speaker:
            if units is None:
                units = [(sent, lang or brain.detect_lang(sent, self.lang))
                         for sent in brain.split_sentences(text)]
            return self._speak_with_bargein(units)
        return False

    def _speak_with_bargein(self, units: list[tuple[str, str]]) -> bool:
        """Unit by unit, so an interruption lands between them and the owner
        never waits for a paragraph. Returns True if interrupted. The mic
        queue is flushed before (nothing said BEFORE a question can answer
        it) and, when nobody interrupted, after (nothing captured DURING the
        utterance is a command). Greek units pass through verbalize_el."""
        L = self.listener
        if config.SPEAKERS:
            L.mute(True)
        else:
            L.flush()
        interrupted = False
        try:
            for sentence, voice in units:
                if L.speech_started.is_set():
                    interrupted = True; break
                if voice == "el":
                    sentence = verbalize_el(sentence)
                self.speaker.say(sentence, voice, block=False)
                while self.speaker.speaking:
                    if L.speech_started.is_set():
                        self.speaker.stop(); interrupted = True; break
                    time.sleep(0.03)
                if interrupted:
                    break
        finally:
            if config.SPEAKERS:
                L.mute(False)
            elif not interrupted:
                L.flush()
        if interrupted:
            self.log("  (interrupted)")
        return interrupted

    def hear(self, timeout_s: float = 0.0, expect_phrase: bool = False) -> Optional[str]:
        """One usable utterance as text, or None on silence. '' means
        something was heard but not trusted. Sets self.lang only when
        whisper is confident about the language. `expect_phrase`: a clip
        too short by the length gate is still accepted when it matches a
        listed confirmation phrase closely (they are all under 1.2 s)."""
        if self._hear_override:
            t = self._hear_override(timeout_s)
            if t:
                self.lang = brain.detect_lang(t)
            return t
        audio = self.listener.listen(timeout_s or None)
        if audio is None:
            return None
        h = self.transcriber.transcribe(audio)
        self._heard = h
        self.last.seconds["stt"] = round(h.seconds_stt, 2)
        if not h.usable:
            phrase_ok = (expect_phrase and h.why_unusable.startswith("too short")
                         and interpret_confirmation(h.text).score >= 0.9)
            if not phrase_ok:
                self.log(f"  (ignored: {h.why_unusable}: {h.text[:40]!r})")
                return ""
        if h.lang in ("el", "en") and h.lang_prob >= config.STT_LANG_ADOPT_PROB:
            self.lang = h.lang
        self.log(f"  heard [{h.lang} {h.lang_prob:.2f}] ({h.seconds_audio:.1f}s -> {h.seconds_stt:.1f}s): {h.text}")
        return h.text

    # -------------------------------------------------------------- a turn
    def handle(self, text: str) -> str:
        """Everything that happens after the owner has spoken. Returns the
        final spoken reply (also spoken). Whatever goes wrong inside, the
        conversation history is rolled back to where this turn started:
        MEASURED, a crash between an assistant tool_call and its tool result
        left a dangling call that gemma's template rendered as an unclosed
        tool-response tag for the next ~12 turns."""
        self.last = TurnLog(heard=text, lang=self.lang)
        n0 = len(self.history)
        error = None
        try:
            if self._mcp_connected_late:
                self._mcp_connected_late = False
                self._say_safely("Τα εργαλεία συνδέθηκαν." if self.lang == "el" else "The tools are connected now.")
            self.last.final = self._handle(text)
            return self.last.final
        except brain.LLMError as e:
            del self.history[n0:]
            error = f"LLMError.{e.kind}"
            self.log(f"  model error [{e.kind}]: {e.detail[:200]}")
            self.last.final = e.spoken(self.lang)
            self._say_safely(self.last.final)
            return self.last.final
        except Exception as e:
            del self.history[n0:]
            error = type(e).__name__
            import traceback
            self.log("  turn failed:\n" + traceback.format_exc())
            self.last.final = ("Κάτι πήγε στραβά, πες το ξανά." if self.lang == "el"
                               else "Something went wrong, say it again.")
            self._say_safely(self.last.final)
            return self.last.final
        finally:
            self._write_log(error)
            self._heard = None

    def _say_safely(self, text: str) -> None:
        try:
            self.say(text, self.lang)
        except Exception as e:      # a TTS failure must not re-raise out of the handler
            self.log(f"  (could not speak: {type(e).__name__}: {e})")

    def _handle(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})
        schemas = self.registry.schemas()
        final = ""
        evicted = False
        for _round in range(MAX_TOOL_ROUNDS):
            self._skip_rest = False
            try:
                reply = self._model_turn(schemas)
            except brain.LLMError as e:
                if e.kind == "context" and not evicted and self._evict_largest_tool_result():
                    evicted = True
                    self._say_safely(e.spoken(self.lang))
                    reply = self._model_turn(schemas)
                else:
                    raise
            self.last.seconds[f"llm{_round}"] = round(reply.seconds, 2)
            if reply.no_tools and not self._said_no_tools:
                self._said_no_tools = True
                self.say(brain.LLMError("jinja").spoken(self.lang), self.lang)

            if not reply.tool_calls:
                final = brain.strip_for_speech(reply.text) or self._empty_reply()
                self.history.append({"role": "assistant", "content": final})
                self.say(final)
                return final

            # the model wants to act: record the assistant turn as the API expects
            self.history.append({"role": "assistant", "content": reply.text or None,
                                 "tool_calls": [{"id": c.id, "type": "function",
                                                 "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
                                                for c in reply.tool_calls]})
            if reply.text:
                self.say(brain.strip_for_speech(reply.text))

            for call in reply.tool_calls:
                result = clamp_result(self._run_gated(call))
                self.history.append({"role": "tool", "tool_call_id": call.id, "name": call.name,
                                     "content": brain.TOOL_RESULT_MARKER + "\n" + result})

        final = ("Σταμάτησα: το μοντέλο ζητούσε συνεχώς εργαλεία χωρίς να καταλήγει."
                 if self.lang == "el" else "I stopped: the model kept asking for tools without concluding.")
        self.say(final); return final

    def _model_turn(self, schemas):
        """One call to the model, with a spoken notice if it takes long:
        with --parallel 1 a request queued behind another client is silent."""
        notice = threading.Timer(config.LLM_SLOW_NOTICE_S, lambda: self._say_safely(
            "Περιμένω ακόμα το μοντέλο." if self.lang == "el" else "Still waiting for the model."))
        notice.daemon = True
        notice.start()
        try:
            return brain.turn(self.history[-24:], schemas, self.lang, facts=self.facts())
        finally:
            notice.cancel()

    def facts(self) -> str:
        """The self-knowledge block, rebuilt once a day or when the tool set
        changes (both rare: each rebuild costs one prompt re-process)."""
        today = _dt.date.today()
        key = (today, self.registry.summary(), self.registry.mcp_error)
        if key != self._facts_day:
            self._facts_day = key
            self._facts = brain.build_facts(self.registry.summary(), self.registry.mcp_error, today, config.PRIVATE)
        return self._facts

    # ---------------------------------------------------------- the record
    def _write_log(self, error: Optional[str] = None) -> None:
        """One JSON line per turn, so a misheard destructive request can be
        read back after the window has closed. Never raises."""
        try:
            h = self._heard
            row = {
                "when": _dt.datetime.now().isoformat(timespec="seconds"),
                "heard": self.last.heard, "lang": self.last.lang,
                "stt": ({"lang": h.lang, "lang_prob": round(h.lang_prob, 2), "avg_logprob": round(h.avg_logprob, 2),
                         "seconds_audio": round(h.seconds_audio, 2), "seconds_stt": round(h.seconds_stt, 2)} if h else None),
                "seconds": self.last.seconds,
                "tools": [{k: v for k, v in e.items() if not (k == "result_head" and e.get("tool") == "read_clipboard")}
                          for e in self.last.tool_events],
                "spoken": self.last.spoken, "final": self.last.final, "error": error,
            }
            config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with config.LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            self.log(f"  (could not write the log: {type(e).__name__}: {e})")

    def _retry_mcp_in_background(self) -> None:
        """The tool server was down at start: keep trying off the turn path
        (a failed attempt costs 2-8 s) and swap the tools in when it appears."""
        def worker():
            deadline = time.monotonic() + config.MCP_RETRY_FOR_S
            while time.monotonic() < deadline:
                time.sleep(config.MCP_RETRY_S)
                tools, err = discover_mcp_tools()
                if err is None:
                    n = self.registry.add_mcp(tools)
                    self.registry.mcp_error = None
                    self._mcp_connected_late = True
                    self.log(f"  MCP connected late: {n} tools added")
                    return
        threading.Thread(target=worker, name="mcp-retry", daemon=True).start()

    def _evict_largest_tool_result(self) -> bool:
        """On a context overflow, drop the content of the biggest tool result
        in the window so the next turns can proceed. Returns False if there
        was nothing to drop."""
        window = self.history[-24:]
        tools = [m for m in window if m.get("role") == "tool" and len(m.get("content") or "") > 200]
        if not tools:
            return False
        biggest = max(tools, key=lambda m: len(m["content"]))
        biggest["content"] = "(result dropped: too large for the model's memory)"
        return True

    def _empty_reply(self) -> str:
        return ("Δεν έχω κάτι να προσθέσω." if self.lang == "el" else "I have nothing to add.")

    # ----------------------------------------------------------- the gate
    def _run_gated(self, call) -> str:
        tool = self.registry.tools.get(call.name)
        ev = {"tool": call.name, "args": call.arguments}
        self.last.tool_events.append(ev)

        if call.name == "_unparsed_tool_call":
            ev["outcome"] = "unparsed"
            return "(the model emitted a tool call the server could not parse; it was NOT executed)"
        if tool is None:
            ev["outcome"] = "unknown"
            return f"(no such tool: {call.name})"

        ev["risk"] = tool.risk.value
        if self._skip_rest:
            ev["outcome"] = "skipped"
            return "(skipped: the owner interrupted an earlier action in this round)"
        if tool.risk is Risk.SAFE:
            pass
        elif tool.risk is Risk.RISKY:
            units = announce_units(tool.risk, tool.name, call.arguments, self.lang)
            if self.say(" ".join(t for t, _ in units), self.lang, units=units):
                # the owner talked over the announcement: that is a stop
                self._skip_rest = True
                self.say("Εντάξει, δεν το έκανα." if self.lang == "el" else "Alright, I did not do it.", self.lang)
                ev["outcome"] = "cancelled"
                return self._DECLINED
        else:   # DESTRUCTIVE or EGRESS: the spoken phrase, nothing less
            verdict = self._confirm(announce_units(tool.risk, tool.name, call.arguments, self.lang), ev)
            ev["confirmed"] = verdict.decision
            if verdict.decision is not True:
                msg = ("Εντάξει, δεν το έκανα." if self.lang == "el" else "Alright, I did not do it.")
                self.say(msg, self.lang)
                ev["outcome"] = "cancelled"
                # MEASURED: with a bare "NOT performed" gemma re-asked "Θέλεις να
                # προχωρήσω;" straight after the owner had said no.
                # MEASURED: "do NOT ask again or offer to retry" then made it refuse
                # a NEW explicit request one turn later without calling the tool.
                # A no cancels this request only.
                return self._DECLINED

        t0 = time.perf_counter()
        try:
            out = tool.run(call.arguments)
        except Exception as e:
            out = f"(tool raised {type(e).__name__}: {str(e)[:200]})"
        ev["outcome"] = "ran"; ev["seconds"] = round(time.perf_counter() - t0, 2)
        ev["result_head"] = out[:120]
        self.log(f"  tool {call.name} [{tool.risk.value}] -> {out[:80]!r}")
        return out

    # MEASURED: with a bare "NOT performed" gemma re-asked "Θέλεις να
    # προχωρήσω;" straight after the owner had said no; "do NOT ask again or
    # offer to retry" then made it refuse a NEW explicit request one turn
    # later. A no cancels this request only.
    _DECLINED = ("(the owner declined THIS request; the action was NOT performed. "
                 "Acknowledge in one sentence and do not ask again now. If the owner "
                 "asks for it again later, call the tool again as normal.)")

    def _confirm(self, question: list[tuple[str, str]], ev: Optional[dict] = None) -> Verdict:
        """Ask aloud, listen for a PHRASE, re-ask when unclear. Silence = no.
        If the owner talks OVER the read-back, only a no is accepted from
        that utterance: consent lands only after the target was heard in
        full, so the whole question is repeated (bounded by MAX_CONFIRM_ASKS)."""
        attempts = [] if ev is None else ev.setdefault("confirm", [])
        lang_before = self.lang          # a 1.5 s answer must not switch the reply language
        units = question
        for _ in range(MAX_CONFIRM_ASKS + 1):
            interrupted = self.say(" ".join(t for t, _ in units), self.lang, units=units)
            answer = self.hear(timeout_s=config.CONFIRM_TIMEOUT_S, expect_phrase=True)
            self.lang = lang_before
            if answer is None:
                self.log("  (no answer - treating as no)")
                attempts.append({"heard": None, "decision": False})
                return Verdict(False, "", 0.0)
            v = interpret_confirmation(answer or "")
            attempts.append({"heard": answer, "decision": v.decision, "matched": v.matched, "score": round(v.score, 2)})
            self.log(f"  confirmation {answer!r} -> {v.decision} (match {v.matched!r} {v.score:.2f})")
            if interrupted:
                if v.decision is False:
                    return v
                units = question             # heard over the read-back: ask again in full
                continue
            if v.decision is not None:
                return v
            units = [(self._reask(), self.lang)]
        return Verdict(False, "", 0.0)

    def _reask(self) -> str:
        return ("Δεν το έπιασα καθαρά. Για να προχωρήσω πες: ναι, συνέχισε. Για να το ακυρώσω πες: όχι, ακύρωσέ το."
                if self.lang == "el"
                else "I did not catch that. To go ahead say: yes, go ahead. To cancel say: no, cancel it.")

    # ---------------------------------------------------------------- loops
    def run_voice(self) -> None:
        # a missing voice is reported before the mic opens and before the
        # 1.6 GB whisper download, not on the first English sentence
        if self.speaker:
            self.speaker.preflight()
        if self.listener:
            self.listener.start()
        try:
            if self.transcriber:
                self.transcriber.load()
            self.log(f"ready: {self.registry.summary()}"
                     + (f" | MCP unavailable: {self.registry.mcp_error}" if self.registry.mcp_error else ""))
            # warm the prompt cache while the greeting plays
            threading.Thread(target=lambda: self.log(f"  prefix warmed in {brain.warm_up(self.registry.schemas(), self.facts()):.1f}s"),
                             name="warm-up", daemon=True).start()
            greeting = "Είμαι έτοιμος, σε ακούω."
            if self.registry.mcp_error:
                greeting += f" Ο διακομιστής εργαλείων δεν απαντάει, έχω μόνο τα {len(self.registry.tools)} τοπικά εργαλεία."
            self.say(greeting, "el")
            while True:
                try:
                    text = self.hear()
                except KeyboardInterrupt:
                    self._say_safely("Εντάξει, τα λέμε." if self.lang == "el" else "Alright, talk later.")
                    break
                if text is None:
                    continue
                if text == "":
                    self.say("Δεν το έπιασα, μπορείς να το ξαναπείς;" if self.lang == "el"
                             else "I did not catch that, could you say it again?", self.lang)
                    continue
                if is_exit(text):
                    self.say("Εντάξει, τα λέμε." if self.lang == "el" else "Alright, talk later.", self.lang)
                    break
                try:
                    self.handle(text)
                except KeyboardInterrupt:
                    self._say_safely("Εντάξει, τα λέμε." if self.lang == "el" else "Alright, talk later.")
                    break
        finally:
            if self.listener:
                self.listener.stop()
            if self.speaker:
                self.speaker.stop()

    def run_text(self) -> None:
        self.log(f"text mode: {self.registry.summary()}"
                 + (f" | MCP unavailable: {self.registry.mcp_error}" if self.registry.mcp_error else ""))
        while True:
            try:
                text = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if is_exit(text, lenient=True):
                break
            self.lang = brain.detect_lang(text)
            self.handle(text)
