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

import json
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import brain, config
from .guard import Risk, Verdict, announce, interpret_confirmation
from .tools import Registry

MAX_TOOL_ROUNDS = 6          # a model that keeps calling tools is stopped, not humoured
MAX_CONFIRM_ASKS = 2


@dataclass
class TurnLog:
    heard: str = ""
    lang: str = ""
    tool_events: list[dict] = field(default_factory=list)
    spoken: list[str] = field(default_factory=list)
    seconds: dict = field(default_factory=dict)


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
    def say(self, text: str, lang: Optional[str] = None) -> None:
        lang = lang or brain.detect_lang(text)
        self.last.spoken.append(text)
        if self._say_override:
            self._say_override(text, lang); return
        if self.speaker:
            self._speak_with_bargein(text, lang)

    def _speak_with_bargein(self, text: str, lang: str) -> None:
        # speak sentence by sentence so an interruption lands between them
        # and the owner never waits for a paragraph to finish
        self.listener.speech_started.clear()
        for sentence in brain.split_sentences(text):
            if self.listener.speech_started.is_set():
                self.log("  (interrupted)")
                break
            # each Piper voice phonemises in ONE language (espeak-ng), so an
            # English sentence inside a Greek answer goes to the English voice
            self.speaker.say(sentence, brain.detect_lang(sentence) or lang, block=False)
            while self.speaker.speaking:
                if self.listener.speech_started.is_set():
                    self.speaker.stop(); self.log("  (interrupted)"); return
                time.sleep(0.03)

    def hear(self, timeout_s: float = 0.0) -> Optional[str]:
        """One usable utterance as text, or None. Sets self.lang."""
        if self._hear_override:
            t = self._hear_override(timeout_s)
            if t:
                self.lang = brain.detect_lang(t)
            return t
        audio = self.listener.listen(timeout_s or None)
        if audio is None:
            return None
        h = self.transcriber.transcribe(audio)
        self.last.seconds["stt"] = round(h.seconds_stt, 2)
        if not h.usable:
            self.log(f"  (ignored: {h.why_unusable}: {h.text[:40]!r})")
            return ""
        self.lang = "el" if h.lang == "el" else ("en" if h.lang == "en" else self.lang)
        self.log(f"  heard [{h.lang} {h.lang_prob:.2f}] ({h.seconds_audio:.1f}s -> {h.seconds_stt:.1f}s): {h.text}")
        return h.text

    # -------------------------------------------------------------- a turn
    def handle(self, text: str) -> str:
        """Everything that happens after the owner has spoken. Returns the
        final spoken reply (also spoken)."""
        self.last = TurnLog(heard=text, lang=self.lang)
        self.history.append({"role": "user", "content": text})
        schemas = self.registry.schemas()
        final = ""
        for _round in range(MAX_TOOL_ROUNDS):
            t0 = time.perf_counter()
            try:
                reply = brain.turn(self.history[-24:], schemas, self.lang)
            except brain.LLMError as e:
                msg = ("Δεν μπορώ να μιλήσω με το μοντέλο αυτή τη στιγμή. " if self.lang == "el"
                       else "I cannot reach the model right now. ") + str(e)
                self.say(msg, self.lang); return msg
            self.last.seconds[f"llm{_round}"] = round(reply.seconds, 2)

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
                result = self._run_gated(call)
                self.history.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": result})

        final = ("Σταμάτησα: το μοντέλο ζητούσε συνεχώς εργαλεία χωρίς να καταλήγει."
                 if self.lang == "el" else "I stopped: the model kept asking for tools without concluding.")
        self.say(final); return final

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
        if tool.risk is Risk.SAFE:
            pass
        elif tool.risk is Risk.RISKY:
            self.say(announce(tool.risk, tool.name, call.arguments, self.lang), self.lang)
        else:
            verdict = self._confirm(announce(tool.risk, tool.name, call.arguments, self.lang))
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
                return ("(the owner declined THIS request; the action was NOT performed. "
                        "Acknowledge in one sentence and do not ask again now. If the owner "
                        "asks for it again later, call the tool again as normal.)")

        t0 = time.perf_counter()
        try:
            out = tool.run(call.arguments)
        except Exception as e:
            out = f"(tool raised {type(e).__name__}: {str(e)[:200]})"
        ev["outcome"] = "ran"; ev["seconds"] = round(time.perf_counter() - t0, 2)
        ev["result_head"] = out[:120]
        self.log(f"  tool {call.name} [{tool.risk.value}] -> {out[:80]!r}")
        return out

    def _confirm(self, question: str) -> Verdict:
        """Ask aloud, listen for a PHRASE, re-ask when unclear. Silence = no."""
        for attempt in range(MAX_CONFIRM_ASKS + 1):
            self.say(question if attempt == 0 else self._reask(), self.lang)
            answer = self.hear(timeout_s=config.CONFIRM_TIMEOUT_S)
            if answer is None:
                self.log("  (no answer - treating as no)")
                return Verdict(False, "", 0.0)
            v = interpret_confirmation(answer or "")
            self.log(f"  confirmation {answer!r} -> {v.decision} (match {v.matched!r} {v.score:.2f})")
            if v.decision is not None:
                return v
        return Verdict(False, "", 0.0)

    def _reask(self) -> str:
        return ("Δεν το έπιασα καθαρά. Πες «ναι, συνέχισε» ή «όχι, ακύρωσέ το»." if self.lang == "el"
                else 'I did not catch that. Say "yes, go ahead" or "no, cancel it".')

    # ---------------------------------------------------------------- loops
    def run_voice(self) -> None:
        self.listener.start()
        try:
            self.transcriber.load()
            self.log(f"ready: {self.registry.summary()}"
                     + (f" | MCP unavailable: {self.registry.mcp_error}" if self.registry.mcp_error else ""))
            self.say("Έτοιμος. Σε ακούω.", "el")
            while True:
                text = self.hear()
                if text is None:
                    continue
                if text == "":
                    self.say("Δεν το έπιασα, μπορείς να το ξαναπείς;" if self.lang == "el"
                             else "I did not catch that, could you say it again?", self.lang)
                    continue
                if self._is_exit(text):
                    self.say("Εντάξει, τα λέμε." if self.lang == "el" else "Alright, talk later.", self.lang)
                    break
                self.handle(text)
        finally:
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
            if self._is_exit(text):
                break
            self.lang = brain.detect_lang(text)
            self.handle(text)

    @staticmethod
    def _is_exit(text: str) -> bool:
        t = text.strip().lower().rstrip(".!")
        return t in {"exit", "quit", "τέλος", "έξοδος", "κλείσε", "αντίο", "goodbye", "bye"}
