"""The voice agent's safety gate and loop, without a microphone or a model.

The rules under test were MEASURED on 2026-09-11, not designed on paper:
whisper mis-hears single words ("Ναι" -> "Ευχαριστώ", "Όχι" -> "Ποια") and
hears two-word phrases perfectly, so a one-word confirmation must never count.
The loop tests inject `say`/`hear` and a fake model, so they exercise the
exact code path the voice does, including what gets spoken before a risky
tool runs and what happens on silence.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_agent import brain, config  # noqa: E402
from voice_agent.guard import Risk, classify, interpret_confirmation, announce  # noqa: E402


@pytest.fixture(autouse=True)
def _memory_in_tmp(tmp_path, monkeypatch):
    """No test may touch the owner's real notes or log (it happened once:
    a suite run appended 26 KB of fake turns to memory/voice_log.jsonl)."""
    monkeypatch.setattr(config, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(config, "NOTES_FILE", tmp_path / "voice_notes.md")
    monkeypatch.setattr(config, "LOG_FILE", tmp_path / "voice_log.jsonl")


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

class TestEveryToolGetsTheRightClass:
    @pytest.mark.parametrize("name", [
        "delete_folder", "remove_file", "rm_rf", "send_email", "post_tweet",
        "telegram_send", "pay_invoice", "transfer_funds", "buy_token", "create_pr",
        "apply_proposal", "approve_and_apply_proposal", "rollback_proposal",
        "run_command", "execute_v2_task", "shutdown_machine", "install_package",
    ])
    def test_destructive_verbs_are_destructive_whatever_the_description(self, name):
        assert classify(name) is Risk.DESTRUCTIVE

    @pytest.mark.parametrize("name", [
        "get_market_context", "read_file", "list_folder", "search_news",
        "analyze_wallet", "check_large_ecosystem_movements", "x_semantic_search",
        "research", "get_system_evaluation", "safe_web_research", "current_time",
    ])
    def test_read_only_names_are_safe(self, name):
        assert classify(name) is Risk.SAFE

    def test_an_unknown_tool_is_announced_not_trusted(self):
        """Pessimistic by design: something we have never seen gets said aloud
        before it runs, rather than run silently."""
        assert classify("frobnicate_the_widgets") is Risk.RISKY

    def test_the_explicit_table_beats_the_patterns(self):
        # "integrate_research_idea" has no destructive verb but edits code
        assert classify("integrate_research_idea") is Risk.DESTRUCTIVE
        # "generate_image" is not read-only but not destructive either
        assert classify("generate_image") is Risk.RISKY


# --------------------------------------------------------------------------- #
# Spoken confirmation - the measured rules
# --------------------------------------------------------------------------- #

class TestConfirmationNeverAcceptsOneWord:
    """MEASURED: whisper turned "Ναι" into "Ευχαριστώ" and "Όχι" into "Ποια".
    Even a correctly transcribed single word must not confirm anything."""

    @pytest.mark.parametrize("word", ["ναι", "Ναι.", "yes", "Yes!", "ok", "sure", "όχι", "no"])
    def test_single_words_are_unclear(self, word):
        assert interpret_confirmation(word).decision is None

    @pytest.mark.parametrize("phrase", [
        "ναι συνέχισε", "Ναι, συνέχισε.", "ναι, προχώρα", "ΝΑΙ ΚΑΝΤΟ",
        "ναι είμαι σίγουρος", "yes go ahead", "Yes, do it.", "yes continue",
        # whisper's punctuation and accents vary; these must still match
        "Ναι. Συνέχισε!",
    ])
    def test_two_word_confirmations_are_yes(self, phrase):
        v = interpret_confirmation(phrase)
        assert v.decision is True, (phrase, v)

    @pytest.mark.parametrize("phrase", [
        "όχι ακύρωσέ το", "Όχι, σταμάτα.", "όχι μην το κάνεις", "ακύρωσε το",
        "no cancel it", "No, stop.", "never mind", "cancel that",
    ])
    def test_denials_are_no(self, phrase):
        assert interpret_confirmation(phrase).decision is False, phrase

    def test_a_no_inside_a_yes_shaped_sentence_is_a_no(self):
        """"όχι, μη συνεχίσεις" shares words with "ναι, συνέχισε". Fuzzy
        matching alone could call that a yes. The denial word must win."""
        assert interpret_confirmation("όχι, μη συνεχίσεις").decision is False
        assert interpret_confirmation("no, do not go ahead").decision is False

    def test_an_unrelated_sentence_is_unclear_not_a_yes(self):
        for s in ["τι ώρα είναι", "the weather is nice today", "πες μου για τον πληθωρισμό"]:
            assert interpret_confirmation(s).decision is None, s

    def test_the_phrase_lists_themselves_contain_no_single_words(self):
        """The rule is only as good as the lists it matches against."""
        for lang in ("el", "en"):
            for p in config.CONFIRM_PHRASES[lang] + config.DENY_PHRASES[lang]:
                assert len(p.split()) >= 2, p


class TestConfirmationAdversarialRows:
    """MEASURED 2026-09-11 against the first version of the gate: these rows
    were the wrong way round. Every row here reproduced to the digit before
    the fix; the gate must never regress on any of them."""

    @pytest.mark.parametrize("phrase", [
        "ναι συνέχισε", "ναι συνέχισε τώρα", "yes go ahead now", "yes, do it now",
        "εντάξει, συνέχισε", "ok go ahead", "Λοιπόν, ναι συνέχισε", "ε ναι, συνέχισε",
        "ναι ναι, συνέχισε", "συνέχισε, ναι", "οκ ναι κάντο", "ασφαλώς, συνέχισε",
        "σίγουρα, προχώρα", "φυσικά, κάντο", "ok do it",
    ])
    def test_natural_yeses_are_yes(self, phrase):
        assert interpret_confirmation(phrase).decision is True, phrase

    @pytest.mark.parametrize("phrase", [
        # Greek negations the first version accepted as YES (0.72-0.89)
        "δεν είμαι σίγουρος", "μη συνεχίσεις", "ναι, μη συνεχίσεις", "ναι είμαι σίγουρος ότι δεν θέλω",
        # holes closed by the corrected regex
        "go ahead and do nothing", "yes but don't", "ναι, άσ' το", "yes, forget it",
        # a time word declines THIS request
        "ναι, κάντο αύριο", "yes do it later",
        "no, do not go ahead", "yes but not now", "όχι, μη συνεχίσεις", "go ahead and stop the server",
    ])
    def test_negations_and_deferrals_are_no(self, phrase):
        assert interpret_confirmation(phrase).decision is False, phrase

    @pytest.mark.parametrize("phrase", [
        "wait, yes go ahead",            # hesitation: re-ask
        "και συνέχισε", "να συνέχισω;",  # fragments without a yes-word
        "i am sure",                     # no yes-word, no listed phrase near enough
    ])
    def test_fragments_and_hesitation_are_unclear(self, phrase):
        assert interpret_confirmation(phrase).decision is None, phrase


class TestWhatTheAgentSaysBeforeActing:
    def test_destructive_announcement_names_the_target_and_asks_for_the_phrase(self):
        s = announce(Risk.DESTRUCTIVE, "delete_folder", {"path": "C:/tmp/old"}, "el")
        assert "old, inside tmp" in s, "the path is read as words, not slashes"
        assert "ναι, συνέχισε" in s and "όχι, ακύρωσέ το" in s
        s = announce(Risk.DESTRUCTIVE, "run_command", {"command": "rm -rf build"}, "en")
        assert "rm dash rf build" in s and "yes, go ahead" in s

    def test_risky_announcement_is_one_sentence_and_does_not_ask(self):
        s = announce(Risk.RISKY, "open_path", {"path": "notes.txt"}, "el")
        assert "ναι, συνέχισε" not in s and "Προσοχή" not in s
        assert len(s) < 120, "an announcement is one short sentence"


# --------------------------------------------------------------------------- #
# The loop, driven without audio or a model
# --------------------------------------------------------------------------- #

class FakeBrain:
    """Scripted replies. Each item is either text or a list of tool calls."""
    def __init__(self, script):
        self.script = list(script); self.calls = []

    def turn(self, messages, schemas, lang_hint=None, facts=""):
        self.calls.append([m for m in messages])
        item = self.script.pop(0)
        if isinstance(item, brain.Reply):
            return item
        if isinstance(item, str):
            return brain.Reply(text=item)
        return brain.Reply(tool_calls=[brain.ToolCall(f"id{i}", n, a) for i, (n, a) in enumerate(item)])


def make_agent(monkeypatch, script, answers, tmp_path):
    from voice_agent.agent import Agent
    from voice_agent.tools import Registry, Tool
    fake = FakeBrain(script)
    monkeypatch.setattr(brain, "turn", fake.turn)
    spoken, heard_iter = [], iter(answers)
    ag = Agent(voice=False, with_mcp=False,
               say=lambda t, l: spoken.append(t),
               hear=lambda timeout: next(heard_iter, None),
               log=lambda s: None)
    # a destructive tool that records whether it actually ran
    ran = []
    ag.registry.tools["delete_folder"] = Tool(
        "delete_folder", "delete", {"type": "object", "properties": {"path": {"type": "string"}}},
        Risk.DESTRUCTIVE, lambda a: (ran.append(a), "deleted")[1])
    ag.lang = "el"
    return ag, spoken, ran, fake


class TestTheGateInTheLoop:
    def test_a_confirmed_destructive_action_runs_and_is_reported(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "C:/tmp/old"})], "Έγινε, διέγραψα τον φάκελο."],
            answers=["ναι, συνέχισε"], tmp_path=tmp_path)
        out = ag.handle("σβήσε τον φάκελο old")
        assert ran == [{"path": "C:/tmp/old"}]
        assert any("Προσοχή" in s and "old, inside tmp" in s for s in spoken), spoken
        assert out == "Έγινε, διέγραψα τον φάκελο."
        # the tool result reached the model on the second call
        assert any(m.get("role") == "tool" and m.get("content").endswith("\ndeleted") for m in fake.calls[1])

    def test_a_denied_destructive_action_does_not_run(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "C:/tmp/old"})], "Εντάξει."],
            answers=["όχι, ακύρωσέ το"], tmp_path=tmp_path)
        ag.handle("σβήσε τον φάκελο old")
        assert ran == []
        assert any("δεν το έκανα" in s for s in spoken)
        assert any(m.get("role") == "tool" and "NOT performed" in m.get("content", "") for m in fake.calls[1])

    def test_silence_is_a_refusal(self, monkeypatch, tmp_path):
        """No answer within the timeout must never be treated as consent."""
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Εντάξει."],
            answers=[None], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        assert ran == []

    def test_a_one_word_yes_is_reasked_then_refused(self, monkeypatch, tmp_path):
        """The measured rule, end to end: "ναι" alone gets a re-ask, and after
        the re-asks are exhausted with no phrase, nothing runs."""
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Εντάξει."],
            answers=["ναι", "ναι", "ναι"], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        assert ran == []
        assert sum("Δεν το έπιασα" in s for s in spoken) == 2

    def test_a_reask_then_a_proper_phrase_confirms(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Έγινε."],
            answers=["ναι", "ναι, συνέχισε"], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        assert ran == [{"path": "x"}]

    def test_safe_tools_run_without_a_word(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("current_time", {})], "Είναι τρεις το απόγευμα."],
            answers=[], tmp_path=tmp_path)
        out = ag.handle("τι ώρα είναι")
        assert out.startswith("Είναι")
        assert len(spoken) == 1, spoken          # only the answer, no announcement

    def test_an_unparsed_tool_call_is_never_executed_or_spoken(self, monkeypatch, tmp_path):
        """Seen for real: the model emitted '<function=terminal>...' as text.
        That must not be read aloud, and nothing must run."""
        monkeypatch.setattr(brain, "turn", lambda m, s, l=None: brain.Reply(
            text="<tool_call>\n<function=run_command>\n<parameter=command>rm -rf /</parameter>\n</function>\n</tool_call>"))
        # brain.turn is patched below the parsing layer here, so emulate the
        # parser's own behaviour on leaked markup:
        from voice_agent.agent import Agent
        spoken = []
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: spoken.append(t),
                   hear=lambda t: None, log=lambda s: None)
        # the real parser turns leaked markup into an _unparsed_tool_call; assert
        # the gate refuses that name outright
        out = ag._run_gated(brain.ToolCall("u", "_unparsed_tool_call", {"raw": "<function=run_command>"}))
        assert "NOT executed" in out
        assert not any("<function" in s for s in spoken)

    def test_the_model_cannot_loop_on_tools_forever(self, monkeypatch, tmp_path):
        from voice_agent.agent import MAX_TOOL_ROUNDS
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("current_time", {})]] * (MAX_TOOL_ROUNDS + 3),
            answers=[], tmp_path=tmp_path)
        out = ag.handle("loop")
        assert "Σταμάτησα" in out


# --------------------------------------------------------------------------- #
# Speech hygiene
# --------------------------------------------------------------------------- #

class TestNothingUnspeakableReachesTheVoice:
    def test_markup_is_stripped(self):
        s = brain.strip_for_speech("**Καλά.** Δες `x.py`:\n```py\nprint(1)\n```\n- ένα\n- δύο\n[link](http://a.b)")
        assert "**" not in s and "`" not in s and "print(1)" not in s and "http" not in s
        assert "Καλά." in s and "ένα" in s and "link" in s

    def test_reply_language_is_detected_from_the_reply(self):
        assert brain.detect_lang("Ο πληθωρισμός είναι η αύξηση των τιμών.") == "el"
        assert brain.detect_lang("Inflation is the rise of prices.") == "en"
        assert brain.detect_lang("Το Bitcoin ανέβηκε 3% σήμερα.") == "el"   # mixed, mostly Greek

    def test_greek_question_mark_does_not_shred_sentences(self):
        parts = brain.split_sentences("Θέλεις να συνεχίσω; Αν ναι, πες το. Αλλιώς σταματώ τώρα.")
        assert parts == ["Θέλεις να συνεχίσω;", "Αν ναι, πες το.", "Αλλιώς σταματώ τώρα."]


class TestConfigCarriesItsProvenance:
    """A threshold without the measurement behind it is a guess."""

    def test_every_measured_constant_is_annotated(self):
        import io
        src = io.open(os.path.join(os.path.dirname(config.__file__), "config.py"), encoding="utf-8").read()
        for token in ("STT_MIN_UTTERANCE_S", "LLM_THINKING", "TTS_VOICES", "STT_BEAM"):
            assert token in src
        assert src.count("MEASURED") >= 5, "the numbers must say where they came from"


class TestGlitchesFoundAgainstTheRealModel:
    """Both seen in the first end-to-end run on 2026-09-11, not imagined."""

    def test_foreign_scripts_never_reach_the_voice(self):
        """gemma, asked to say a year in words, produced Tamil and Cyrillic
        inside a Greek sentence. Whatever the model does, the voice must not
        read it out."""
        s = brain.strip_for_speech("η ώρα είναι έντεκα του இரண்டтисяν δεύτερου έτους 2026.")
        assert "இ" not in s and "т" not in s
        assert "έντεκα" in s and "2026" in s
        # accented Greek and normal punctuation survive intact
        assert brain.strip_for_speech("Ναί, το «αρχείο» είναι έτοιμο — 100%.") == "Ναί, το «αρχείο» είναι έτοιμο — 100%."

    def test_the_prompt_forbids_years_in_words(self):
        assert "ΨΗΦΙΑ" in brain.SYSTEM_PROMPT and "ολογράφως" in brain.SYSTEM_PROMPT
        # MEASURED 2026-09-12: asked to say 12 in words the model wrote "zwölf"
        # 4/10 times under every sampling setting; so no number is ever written
        # in words by the model - greek.py says them
        assert "ΟΛΟΥΣ τους αριθμούς" in brain.SYSTEM_PROMPT and "12:08" in brain.SYSTEM_PROMPT

    def test_after_a_denial_the_model_is_told_not_to_reask(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Εντάξει."],
            answers=["όχι, ακύρωσέ το"], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        tool_msg = next(m for m in fake.calls[1] if m.get("role") == "tool")
        assert "do not ask again now" in tool_msg["content"]
        # ...but a no cancels THIS request only. Measured: a stronger wording
        # made gemma refuse a fresh explicit request one turn later.
        assert "call the tool again as normal" in tool_msg["content"]

    def test_a_denial_does_not_poison_the_next_request(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Εντάξει.",
                    [("delete_folder", {"path": "x"})], "Έγινε."],
            answers=["όχι, ακύρωσέ το", "ναι, συνέχισε"], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        assert ran == []
        ag.handle("σβήσε το, τώρα σοβαρά")
        assert ran == [{"path": "x"}]          # asked afresh, confirmed, ran


class TestTextModePrintsWhatWouldBeSpoken:
    """Found by running start-voice.bat text: the reply was computed and
    never shown, because a voiceless Agent had nowhere to send it."""

    def test_text_mode_installs_a_printing_say(self, monkeypatch, capsys):
        import voice_agent.__main__ as cli
        captured = {}

        class FakeAgent:
            def __init__(self, **kw):
                captured.update(kw)
            def run_text(self):
                captured["say"]("Γεια.", "el")

        monkeypatch.setattr(cli, "Agent", FakeAgent)
        assert cli.main(["--text", "--no-mcp"]) == 0
        assert captured["voice"] is False and captured["with_mcp"] is False
        assert "el> Γεια." in capsys.readouterr().out


def _piper_16k(text, lang="el"):
    """A Piper sentence resampled to 16 kHz int16, or a pytest skip."""
    import numpy as np
    from voice_agent.tts import Speaker, VoiceMissing
    try:
        wav, rate = Speaker().synthesize(text, lang)
    except VoiceMissing as e:
        pytest.skip(str(e))
    wav = np.asarray(wav); n = int(len(wav) * config.AUDIO_RATE / rate)
    return np.interp(np.linspace(0, len(wav) - 1, n), np.arange(len(wav)),
                     wav.astype(np.float32)).astype(np.int16)


def _feed(listener, sig, pace=None):
    """Push a signal through the PortAudio callback exactly as the driver
    would: 512-sample frames, shape (512, 1). `pace` sleeps per frame."""
    import time as _t
    F = config.AUDIO_FRAME_SAMPLES
    for i in range(0, len(sig) - F + 1, F):
        listener._on_audio(sig[i:i + F].reshape(-1, 1), F, None, None)
        if pace:
            _t.sleep(pace)


@pytest.fixture(scope="module")
def greek_speech_16k():
    return _piper_16k("Καλημέρα, τι κάνεις σήμερα;")


class TestTheMicrophonePath:
    """MEASURED 2026-09-11: `import webrtcvad` raised ModuleNotFoundError
    (pkg_resources) on Python 3.14 + setuptools 82, so the voice path crashed
    on its first line while every text-mode test passed. The VAD is now
    Silero (ONNX, shipped inside faster-whisper) and it runs in the audio
    callback; these tests run the real thing on real synthesised speech."""

    def test_audio_module_does_not_import_webrtcvad(self):
        import inspect
        from voice_agent import audio
        assert "import webrtcvad" not in inspect.getsource(audio)

    def test_silero_separates_speech_from_silence_and_noise(self, greek_speech_16k):
        import numpy as np
        from voice_agent.audio import _SileroVad
        vad = _SileroVad(config.VAD_THRESHOLD)
        F = config.AUDIO_FRAME_SAMPLES
        def probs(sig):
            vad.reset()
            return [vad.prob(sig[i:i + F]) for i in range(0, len(sig) - F + 1, F)]
        assert max(probs(np.zeros(config.AUDIO_RATE, np.int16))) < 0.1
        assert max(probs((np.random.randn(config.AUDIO_RATE) * 3000).astype(np.int16))) < 0.3
        p = probs(greek_speech_16k)
        assert max(p) > 0.9 and sum(x >= config.VAD_THRESHOLD for x in p) > len(p) / 2

    def test_segmentation_returns_the_spoken_part_and_times_out_on_silence(self, greek_speech_16k):
        import numpy as np
        from voice_agent.audio import Listener
        L = Listener()
        F = config.AUDIO_FRAME_SAMPLES
        _feed(L, np.zeros(10 * F, np.int16))
        _feed(L, greek_speech_16k)
        _feed(L, np.zeros(40 * F, np.int16))          # 1.3 s of silence ends it
        assert L.speech_started.is_set(), "the callback itself flags speech, before anyone listens"
        utt = L.listen(timeout_s=3)
        assert utt is not None
        spoken = len(greek_speech_16k) / config.AUDIO_RATE
        assert spoken - 0.3 <= len(utt) / config.AUDIO_RATE <= spoken + 0.6, "pre-roll + tail only"
        assert not L.speech_started.is_set(), "cleared once the utterance is delivered"
        assert L.listen(timeout_s=0.3) is None                # silence times out, never blocks

    def test_flush_forgets_what_was_captured(self, greek_speech_16k):
        from voice_agent.audio import Listener
        L = Listener()
        _feed(L, greek_speech_16k)
        assert L.speech_started.is_set()
        L.flush()
        assert not L.speech_started.is_set()
        assert L.listen(timeout_s=0.3) is None


class TestBargeIn:
    """P-02. MEASURED before the fix: 'Όχι, σταμάτα!' pushed 0.2 s into a
    1.2 s playback -> interrupted=False, 92 frames still queued, and the
    NEXT listen() returned that stale clip as a command. Worse, a stale
    'ναι, συνέχισε κανονικά' queued during the model turn was returned as
    the answer to a destructive question asked afterwards."""

    def _agent_with_fake_speaker(self, monkeypatch, listener, play_s=1.0):
        import time as _t
        from voice_agent.agent import Agent
        events = []
        class FakeSpeaker:
            def __init__(self): self._until = 0; self.stopped_at = None
            @property
            def speaking(self): return _t.monotonic() < self._until
            def say(self, text, lang, block=False):
                events.append(("say", text, lang)); self._until = _t.monotonic() + play_s
            def stop(self): self.stopped_at = _t.monotonic(); self._until = 0
            def preflight(self): pass
        ag = Agent(voice=False, with_mcp=False, log=lambda s: events.append(("log", s)))
        ag.speaker, ag.listener = FakeSpeaker(), listener
        return ag, events

    def test_talking_over_the_agent_stops_it_within_300ms_and_is_heard_next(self, monkeypatch):
        import threading, time as _t
        import numpy as np
        from voice_agent.audio import Listener
        monkeypatch.setattr(config, "SPEAKERS", False)
        stale = _piper_16k("Ναι, συνέχισε κανονικά.")
        denial = _piper_16k("Όχι, σταμάτα!")
        L = Listener()
        _feed(L, stale)                                   # captured while the model was thinking
        ag, events = self._agent_with_fake_speaker(monkeypatch, L, play_s=1.5)
        t_first_speech = {}
        def talk_over():
            _t.sleep(0.3)
            F = config.AUDIO_FRAME_SAMPLES
            for i in range(0, len(denial) - F + 1, F):
                if L.speech_started.is_set() and "t" not in t_first_speech:
                    t_first_speech["t"] = _t.monotonic()
                L._on_audio(denial[i:i + F].reshape(-1, 1), F, None, None)
                _t.sleep(config.AUDIO_FRAME_MS / 1000)   # real-time pace
            _feed(L, np.zeros(40 * F, np.int16))
        th = threading.Thread(target=talk_over); th.start()
        interrupted = ag.say("Προσοχή, θα διαγράψω τον φάκελο old. Πες ναι συνέχισε για να προχωρήσω.", "el")
        th.join()
        assert interrupted is True
        assert ag.speaker.stopped_at is not None
        assert ag.speaker.stopped_at - t_first_speech["t"] < 0.3
        utt = L.listen(timeout_s=2)
        assert utt is not None
        # the stale clip is gone; what comes back is the denial (shorter)
        assert abs(len(utt) / config.AUDIO_RATE - len(denial) / config.AUDIO_RATE) < 0.7
        assert L.listen(timeout_s=0.5) is None

    def test_an_uninterrupted_utterance_flushes_the_queue(self, monkeypatch):
        from voice_agent.audio import Listener
        monkeypatch.setattr(config, "SPEAKERS", False)
        L = Listener()
        _feed(L, _piper_16k("Ναι, συνέχισε κανονικά."))
        ag, events = self._agent_with_fake_speaker(monkeypatch, L, play_s=0.05)
        assert ag.say("Έτοιμος.", "el") is False
        assert L.listen(timeout_s=0.3) is None, "nothing said before or during counts"

    def test_on_speakers_the_mic_is_muted_while_speaking(self, monkeypatch):
        from voice_agent.audio import Listener
        monkeypatch.setattr(config, "SPEAKERS", True)
        L = Listener()
        ag, events = self._agent_with_fake_speaker(monkeypatch, L, play_s=0.05)
        seen = []
        orig = L.mute
        L.mute = lambda on: (seen.append(on), orig(on))
        ag.say("Έτοιμος.", "el")
        assert seen == [True, False]


class TestInterruptedReadBackOnlyAcceptsANo:
    """P-02 gate rule: consent lands only after the target was heard in
    full. An interrupting 'yes' repeats the whole question; an interrupting
    'no' cancels at once; three interruptions cancel."""

    def _agent(self, monkeypatch, script, answers, interrupt_flags):
        from voice_agent.agent import Agent
        from voice_agent.tools import Tool
        fake = FakeBrain(script)
        monkeypatch.setattr(brain, "turn", fake.turn)
        spoken, heard_iter, flags = [], iter(answers), iter(interrupt_flags)
        ag = Agent(voice=False, with_mcp=False,
                   say=lambda t, l: (spoken.append(t), next(flags, False))[1],
                   hear=lambda timeout: next(heard_iter, None), log=lambda s: None)
        ran = []
        ag.registry.tools["delete_folder"] = Tool(
            "delete_folder", "delete", {"type": "object", "properties": {"path": {"type": "string"}}},
            Risk.DESTRUCTIVE, lambda a: (ran.append(a), "deleted")[1])
        ag.lang = "el"
        return ag, spoken, ran

    def test_a_yes_over_the_announcement_repeats_the_full_question(self, monkeypatch):
        ag, spoken, ran = self._agent(monkeypatch,
            [[("delete_folder", {"path": "C:/x"})], "Έγινε."],
            answers=["ναι, συνέχισε", "ναι, συνέχισε"], interrupt_flags=[True, False])
        ag.handle("σβήσε")
        questions = [s for s in spoken if "Προσοχή" in s]
        assert len(questions) == 2, spoken            # asked in full twice, no "δεν το έπιασα"
        assert not any("έπιασα" in s for s in spoken)
        assert ran == [{"path": "C:/x"}]               # the uninterrupted yes ran it

    def test_a_no_over_the_announcement_cancels_at_once(self, monkeypatch):
        ag, spoken, ran = self._agent(monkeypatch,
            [[("delete_folder", {"path": "C:/x"})], "Εντάξει."],
            answers=["όχι, ακύρωσέ το"], interrupt_flags=[True])
        ag.handle("σβήσε")
        assert ran == [] and sum("Προσοχή" in s for s in spoken) == 1

    def test_three_interruptions_cancel(self, monkeypatch):
        ag, spoken, ran = self._agent(monkeypatch,
            [[("delete_folder", {"path": "C:/x"})], "Εντάξει."],
            answers=["ναι, συνέχισε"] * 3, interrupt_flags=[True, True, True])
        ag.handle("σβήσε")
        assert ran == [] and sum("Προσοχή" in s for s in spoken) == 3

    def test_interrupting_a_risky_announcement_stops_it_and_the_rest_of_the_round(self, monkeypatch):
        from voice_agent.tools import Tool
        ag, spoken, ran = self._agent(monkeypatch,
            [[("write_note", {"text": "a"}), ("write_note", {"text": "b"})], "Εντάξει."],
            answers=[], interrupt_flags=[True])
        wrote = []
        ag.registry.tools["write_note"] = Tool("write_note", "x", {"type": "object", "properties": {}},
                                               Risk.RISKY, lambda a: (wrote.append(a), "ok")[1])
        ag.handle("κράτα δύο σημειώσεις")
        assert wrote == []
        assert [e.get("outcome") for e in ag.last.tool_events] == ["cancelled", "skipped"]
        assert any("δεν το έκανα" in s for s in spoken)

    def test_the_confirmation_attempts_are_recorded(self, monkeypatch):
        ag, spoken, ran = self._agent(monkeypatch,
            [[("delete_folder", {"path": "C:/x"})], "Έγινε."],
            answers=["ναι", "ναι, συνέχισε"], interrupt_flags=[])
        ag.handle("σβήσε")
        attempts = ag.last.tool_events[0]["confirm"]
        assert [a["heard"] for a in attempts] == ["ναι", "ναι, συνέχισε"]
        assert [a["decision"] for a in attempts] == [None, True]


class TestShortPhrasesExitWordsAndLanguage:
    """P-05 / P-12. MEASURED: every exit word and 9 of 12 listed phrases
    are under 1.2 s at Piper's pace and were thrown away although whisper
    had them at 0% CER; a 1.5 s confirmation clip rewrote the reply
    language; 1.5 s Greek clips came back as Swedish."""

    def _heard(self, text, lang="el", lang_prob=0.99, avg_logprob=-0.3, secs=1.0, no_speech=0.05):
        from voice_agent.stt import Heard
        return Heard(text, lang, lang_prob, avg_logprob, no_speech, secs, 0.5)

    def test_a_confident_two_word_clip_under_the_gate_is_usable(self):
        assert self._heard("Yes, do it.", "en", 0.99, -0.3, 1.06).usable
        assert self._heard("Όχι, σταμάτα.", "el", 0.98, -0.4, 1.15).usable
        assert not self._heard("Τέλος.", "el", 0.99, -0.3, 0.6).usable          # one word
        assert not self._heard("Ναι, κάντο", "el", 0.41, -0.3, 1.0).usable       # unsure language
        assert not self._heard("Yes, do it", "en", 0.99, -0.9, 1.0).usable       # unsure words

    def test_a_foreign_language_guess_is_never_fed_to_the_model(self):
        for lang in ("sv", "es", "ro", "da"):
            h = self._heard("Men här är det för att hålla.", lang, 0.52, -0.3, 1.5)
            assert not h.usable and h.why_unusable.startswith("language")

    @pytest.mark.parametrize("phrase,want", [
        ("Τέλος για σήμερα.", True), ("That's all, goodbye", True), ("Εντάξει, τέλος, τα λέμε.", True),
        ("We are done, bye", True), ("Ναι, συνέχισε.", False), ("Κλείσε το παράθυρο", False),
        ("Τέλος, πες μου την ώρα", False), ("τέλος", False),
    ])
    def test_exit_phrases(self, phrase, want):
        from voice_agent.guard import is_exit
        assert is_exit(phrase) is want, phrase

    def test_the_keyboard_still_takes_one_word(self):
        from voice_agent.guard import is_exit
        assert is_exit("exit", lenient=True) and is_exit("τέλος", lenient=True)

    def test_the_confirmation_answer_does_not_switch_the_reply_language(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Έγινε."],
            answers=["yes, go ahead"], tmp_path=tmp_path)
        ag.lang = "el"
        ag.handle("σβήσε το")
        assert ran == [{"path": "x"}]
        assert ag.lang == "el"
        # the model was hinted Greek on both calls, not English on the second
        assert all(m["role"] != "system" for m in fake.calls[1])   # brain adds the hint itself


class TestTextModePrintsWhatWouldBeSpoken:
    """Found by running start-voice.bat text: the reply was computed and
    never shown, because a voiceless Agent had nowhere to send it."""

    def test_text_mode_installs_a_printing_say(self, monkeypatch, capsys):
        import voice_agent.__main__ as cli
        captured = {}

        class FakeAgent:
            def __init__(self, **kw):
                captured.update(kw)
            def run_text(self):
                captured["say"]("Γεια.", "el")

        monkeypatch.setattr(cli, "Agent", FakeAgent)
        assert cli.main(["--text", "--no-mcp"]) == 0
        assert captured["voice"] is False and captured["with_mcp"] is False
        assert "el> Γεια." in capsys.readouterr().out


class TestToolOutputIsDataAndBounded:
    """P-19 / P-16. MEASURED: gemma offered to run a command it found on the
    clipboard; a 112 KB read_file result produced a 400 and every following
    turn failed the same way."""

    def test_every_tool_message_starts_with_the_data_marker(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Έγινε."],
            answers=["ναι, συνέχισε"], tmp_path=tmp_path)
        ag.handle("σβήσε το")
        tool_msgs = [m for m in fake.calls[1] if m.get("role") == "tool"]
        assert tool_msgs and all(m["content"].startswith(brain.TOOL_RESULT_MARKER) for m in tool_msgs)

    def test_the_prompt_says_tool_output_is_data(self):
        assert "ΔΕΔΟΜΕΝΑ" in brain.SYSTEM_PROMPT

    def test_a_huge_result_is_cut_with_a_visible_marker(self, monkeypatch, tmp_path):
        from voice_agent.tools import Tool, clamp_result
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("read_big", {})], "Το διάβασα."], answers=[], tmp_path=tmp_path)
        ag.registry.tools["read_big"] = Tool("read_big", "x", {"type": "object", "properties": {}},
                                             Risk.SAFE, lambda a: "x" * 50_000)
        ag.handle("διάβασε το μεγάλο")
        msg = next(m for m in fake.calls[1] if m.get("role") == "tool")["content"]
        assert len(msg) < config.TOOL_RESULT_MAX_CHARS + 300
        assert "κόπηκε" in msg and "42000" in msg
        assert clamp_result("short") == "short"

    def test_open_path_refuses_to_launch_scripts(self, monkeypatch, tmp_path):
        """MEASURED: os.startfile ran a .bat exactly like a double click."""
        from voice_agent import tools
        calls = []
        monkeypatch.setattr(tools.os, "startfile", lambda t: calls.append(t), raising=False)
        probe = tmp_path / "probe.bat"; probe.write_text("echo hi")
        for target in [str(probe), str(probe).upper(), str(probe) + " ", "x.url", "a.lnk", "setup.msi",
                       "file:///C:/x/p.bat", "mailto:x", "ms-settings:display", "C:/dl/setup.exe"]:
            out = tools._open_path({"path": target})
            assert out.startswith("(refused"), (target, out)
            assert "run_command" in out
        assert calls == []
        for target in ["notes.txt", str(tmp_path), "notepad", "chrome.exe"]:
            tools._open_path({"path": target})
        assert len(calls) == 4
        # a web link is a network request: refused in private mode, opened otherwise
        assert tools._open_path({"path": "https://example.org"}).startswith("(refused")
        monkeypatch.setattr(config, "PRIVATE", False)
        tools._open_path({"path": "https://example.org"})
        assert len(calls) == 5


class TestTheSessionSurvivesFailures:
    """P-11. MEASURED: a read timeout, a non-JSON body, odd tool-call
    arguments and a missing voice each killed the process mid-conversation,
    and an HTTP 400 was read aloud with the URL inside a Greek sentence."""

    def _fake_server(self, mode):
        import http.server, threading, json as _json
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
                if mode == "hang":
                    import time as _t; _t.sleep(3); return
                if mode == "nonjson":
                    self.send_response(200); self.end_headers(); self.wfile.write(b"<html>oops</html>"); return
                if mode in ("jinna", "jinja"):
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b'{"error":{"message":"tools param requires --jinja flag"}}'); return
                if mode == "context":
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b'{"error":{"message":"the request exceeds the available context size"}}'); return
                if mode == "truncated":
                    self.send_response(200); self.send_header("Content-Length", "500"); self.end_headers()
                    self.wfile.write(b'{"choices":[{"message":{"content":"x'); return
                body = _json.dumps({"choices": [{"message": {"content": "Γεια σου."}}], "usage": {}}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    @pytest.mark.parametrize("mode", ["hang", "nonjson", "jinja", "context", "truncated"])
    def test_each_failure_becomes_one_spoken_sentence_and_the_history_is_clean(self, monkeypatch, mode):
        from voice_agent.agent import Agent
        srv = self._fake_server(mode)
        monkeypatch.setattr(config, "LLM_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
        monkeypatch.setattr(config, "LLM_TIMEOUT_S", 0.5)
        monkeypatch.setattr(config, "LLM_SLOW_NOTICE_S", 60)
        spoken = []
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: spoken.append(t), log=lambda s: None)
        ag.lang = "el"
        before = list(ag.history)
        out = ag.handle("γεια")
        assert "http" not in out and "127.0.0.1" not in out, out
        assert any(ord(c) > 0x370 for c in out), "spoken in Greek"
        assert ag.history == before, "the failed turn left nothing behind"
        srv.shutdown()

    def test_without_jinja_the_agent_talks_without_tools_and_says_so_once(self, monkeypatch):
        """A server that refuses tools gets the same turn again without them."""
        from voice_agent import brain as b
        seen = []
        def fake_post(body):
            seen.append("tools" in body)
            if "tools" in body:
                raise b.LLMError("jinja", "tools param requires --jinja flag")
            return {"choices": [{"message": {"content": "Γεια."}}], "usage": {}}
        monkeypatch.setattr(b, "_post", fake_post)
        r = b.turn([{"role": "user", "content": "γεια"}], [{"type": "function", "function": {"name": "x", "parameters": {}}}])
        assert seen == [True, False] and r.no_tools and r.text == "Γεια."

    @pytest.mark.parametrize("args_raw", ["null", '"x"', "[1,2]", "{bad json", 7])
    def test_unparseable_arguments_never_reach_the_gate_as_a_half_named_action(self, monkeypatch, tmp_path, args_raw):
        from voice_agent import brain as b
        def fake_post(body):
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "delete_folder", "arguments": args_raw}}]}}], "usage": {}}
        monkeypatch.setattr(b, "_post", fake_post)
        r = b.turn([{"role": "user", "content": "σβήσε"}], [])
        assert [c.name for c in r.tool_calls] == ["_unparsed_tool_call"]
        assert "delete_folder" in r.tool_calls[0].arguments["raw"]

    def test_a_context_overflow_drops_the_largest_result_and_retries(self, monkeypatch, tmp_path):
        from voice_agent import brain as b
        from voice_agent.agent import Agent
        n = {"calls": 0}
        def fake_turn(messages, schemas, lang, facts=""):
            n["calls"] += 1
            if n["calls"] == 1:
                raise b.LLMError("context", "exceeds the available context size")
            return b.Reply(text="Εντάξει.")
        monkeypatch.setattr(b, "turn", fake_turn)
        spoken = []
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: spoken.append(t), log=lambda s: None)
        ag.lang = "el"
        ag.history = [{"role": "user", "content": "διάβασε"},
                      {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
                      {"role": "tool", "tool_call_id": "a", "name": "read_file", "content": "x" * 9000},
                      {"role": "assistant", "content": "ok"}]
        out = ag.handle("και τώρα;")
        assert out == "Εντάξει." and n["calls"] == 2
        assert ag.history[2]["content"].startswith("(result dropped")
        assert any("μνήμη" in s for s in spoken)

    def test_a_crash_inside_the_turn_rolls_the_history_back(self, monkeypatch, tmp_path):
        from voice_agent import brain as b
        from voice_agent.agent import Agent
        monkeypatch.setattr(b, "turn", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        spoken = []
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: spoken.append(t), log=lambda s: None)
        ag.lang = "el"
        out = ag.handle("γεια")
        assert "στραβά" in out and ag.history == []

    def test_run_voice_preflights_the_voices_and_survives_ctrl_c(self, monkeypatch):
        from voice_agent.agent import Agent
        events = []
        class FakeSpeaker:
            speaking = False
            def preflight(self): events.append("preflight")
            def stop(self): events.append("stop")
        class FakeListener:
            def start(self): events.append("start")
            def stop(self): events.append("lstop")
        spoken = []
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: spoken.append(t), log=lambda s: None)
        ag.speaker, ag.listener = FakeSpeaker(), FakeListener()
        answers = iter(["τι ώρα είναι", KeyboardInterrupt()])
        def hear(timeout=0.0):
            a = next(answers)
            if isinstance(a, BaseException): raise a
            return a
        ag._hear_override = hear
        monkeypatch.setattr(brain, "turn", lambda *a, **k: brain.Reply(text="Είναι δέκα."))
        ag.run_voice()                      # must return, not raise
        assert events[0] == "preflight" and "start" in events and "lstop" in events and "stop" in events
        assert spoken[-1] == "Εντάξει, τα λέμε."


class TestWhisperEncodesOnce:
    """P-09. MEASURED: faster-whisper 1.2.1 transcribe(language=None) encodes
    the 30 s window twice (detect_language, then generate_segments); the
    encoder is 73-92% of STT time. One pass: encodes 2 -> 1, byte-identical
    text/avg_logprob/no_speech on Greek, English and a 1.3 s confirmation
    clip, elapsed 0.49-0.54x."""

    def test_the_encoder_output_is_reused_for_detection_and_decoding(self):
        import numpy as np
        from voice_agent.stt import Transcriber
        calls = {"encode": 0, "detect": [], "generate": []}
        class Seg:
            text, avg_logprob, no_speech_prob = "γεια", -0.2, 0.01
        class Inner:
            is_multilingual = True
            def detect_language(self, enc):
                calls["detect"].append(enc); return [[("<|el|>", 0.97)]]
        class FakeModel:
            model = Inner()
            hf_tokenizer = object()
            def feature_extractor(self, audio): return np.zeros((128, 300), np.float32)
            def encode(self, feats): calls["encode"] += 1; return "ENC"
            def generate_segments(self, feats, tokenizer, options, log_progress, encoder_output=None):
                calls["generate"].append(encoder_output); return [Seg()]
        import voice_agent.stt as stt
        real = {}
        import faster_whisper.tokenizer as ftk, faster_whisper.transcribe as ftr
        real["Tokenizer"] = ftk.Tokenizer; real["gst"] = ftr.get_suppressed_tokens
        ftk.Tokenizer = lambda *a, **k: object()
        ftr.get_suppressed_tokens = lambda tok, sup: [-1]
        try:
            segs, lang, prob = Transcriber._one_pass(FakeModel(), np.zeros(16000, np.float32), None)
        finally:
            ftk.Tokenizer = real["Tokenizer"]; ftr.get_suppressed_tokens = real["gst"]
        assert calls["encode"] == 1
        assert calls["detect"] == ["ENC"] and calls["generate"] == ["ENC"]
        assert (lang, prob) == ("el", 0.97) and segs[0].text == "γεια"

    def test_one_pass_matches_the_library_on_real_speech(self):
        """Skips without the Piper voice; with it, compares against
        model.transcribe(language=None) on the same clip."""
        import numpy as np
        from voice_agent.stt import Transcriber
        sig = _piper_16k("Τι ώρα είναι τώρα;").astype(np.float32) / 32768.0
        tr = Transcriber(); model = tr.load()
        segments, info = model.transcribe(sig, language=None, beam_size=config.STT_BEAM,
                                          vad_filter=False, condition_on_previous_text=False)
        a = [(s.text, round(s.avg_logprob, 6)) for s in segments]
        segs, lang, prob = tr._one_pass(model, sig, None)
        b = [(s.text, round(s.avg_logprob, 6)) for s in segs]
        assert a == b and lang == info.language


class TestTheVoiceSpeaksLikeAGreek:
    """P-03 / P-06 / P-13. MEASURED (Piper -> whisper): a Greek sentence with
    a path in it went to the English voice and came back as letter names
    (CER 278%); 'Προσοχή.' alone 0/5; '1.250 ευρώ' 0/5 vs words 4/5; Latin
    tech terms 1/15 vs Greek spelling 9/15."""

    def test_announcement_is_units_with_explicit_voices(self):
        from voice_agent.guard import announce_units
        units = announce_units(Risk.DESTRUCTIVE, "delete_folder",
                               {"path": "C:/Users/you/Documents/old_project"}, "el")
        assert units[0] == ("Προσοχή, θα διαγράψω τον φάκελο:", "el")
        assert units[1] == ("old project, inside Documents.", "en")
        assert units[2][1] == "el" and "ναι, συνέχισε" in units[2][0] and "όχι, ακύρωσέ το" in units[2][0]
        # a Greek argument stays in the Greek voice
        units = announce_units(Risk.RISKY, "write_note", {"text": "πάρε γάλα αύριο"}, "el")
        assert units == [("Κρατάω σημείωση.", "el"), ("πάρε γάλα αύριο", "el")]

    def test_a_long_command_is_never_truncated_before_its_destructive_tail(self):
        from voice_agent.guard import announce
        cmd = "Get-ChildItem C:/x -Recurse | Where-Object { $_.Length -gt 1MB -and $_.Name -like '*.log' } | Remove-Item -Force"
        s = announce(Risk.DESTRUCTIVE, "run_command", {"command": cmd}, "el")
        assert "Remove-Item" in s and "pipe" in s

    def test_every_frame_is_at_least_three_words_and_a_clause(self):
        """'Προσοχή.' alone was unintelligible; each spoken unit must be a clause."""
        from voice_agent.guard import _EL_FRAMES, _EN_FRAMES, announce_units
        for name in list(_EL_FRAMES) + list(_EN_FRAMES) + ["brand_new_tool"]:
            for lang in ("el", "en"):
                for risk in (Risk.RISKY, Risk.DESTRUCTIVE):
                    first = announce_units(risk, name, {"path": "C:/a/b"}, lang)[0][0]
                    assert len(first.split()) >= 2 and not first.startswith("Προσοχή.") and not first.startswith("Careful."), first

    def test_sentences_are_never_one_word_fragments(self):
        assert brain.split_sentences("Προσοχή. Θα διαγράψω τον φάκελο.") == ["Προσοχή. Θα διαγράψω τον φάκελο."]
        assert brain.split_sentences("Έτοιμος. Σε ακούω.") == ["Έτοιμος. Σε ακούω."]
        assert brain.split_sentences("Μπορείς π.χ. να το ανοίξεις. Ή και όχι φυσικά.") == ["Μπορείς π.χ. να το ανοίξεις.", "Ή και όχι φυσικά."]
        assert brain.split_sentences("Το κόστος είναι π.χ. 5 ευρώ κ.λπ. Εντάξει;") == ["Το κόστος είναι π.χ. 5 ευρώ κ.λπ. Εντάξει;"]

    def test_detect_lang_goes_by_words_not_letters(self):
        assert brain.detect_lang("Τρέξε Get-Date στο PowerShell.") == "el"
        assert brain.detect_lang("Ανοίγω το notes.txt τώρα.") == "el"
        assert brain.detect_lang("Inflation is the rise of prices.") == "en"
        assert brain.detect_lang("2026", "en") == "en" and brain.detect_lang("2026") == "el"

    @pytest.mark.parametrize("text,want", [
        ("Κοστίζει 1.250 ευρώ.", "Κοστίζει χίλια διακόσια πενήντα ευρώ."),
        ("1.287,50 ευρώ", "χίλια διακόσια ογδόντα επτά ευρώ και πενήντα λεπτά"),
        ("Η ώρα είναι 11:25.", "Η ώρα είναι έντεκα και είκοσι πέντε."),
        ("Η εντολή έβγαλε 12:09:02.", "Η εντολή έβγαλε δώδεκα και εννέα."),
        ("Βρήκα 12 αρχεία.", "Βρήκα δώδεκα αρχεία."),
        ("Είναι 9:30 και μετά 10:00.", "Είναι εννέα και μισή και μετά δέκα ακριβώς."),
        ("το 2026", "το 2026"),
        ("Ο Docker δεν τρέχει.", "Ο ντόκερ δεν τρέχει."),
        ("Η GPU έχει 16 GB VRAM.", "Η κάρτα γραφικών έχει δεκαέξι γίγα μνήμη της κάρτας γραφικών."),
        ("Άνοιξε το PowerShell και τρέξε το Python script.", "Άνοιξε το πάουερ σελ και τρέξε το πάιθων σκριπτ."),
        ("Το API και το MCP απαντούν.", "Το έιπιάι και το διακομιστής εργαλείων απαντούν."),
        ("Ανέβηκε 3% σήμερα.", "Ανέβηκε τρία τοις εκατό σήμερα."),
        ("Έχω 3 ώρες και 4 μήνες και 21 μέρες.", "Έχω τρεις ώρες και τέσσερις μήνες και είκοσι μία μέρες."),
        ("Βρήκα 42 αρχεία, π.χ. σημειώσεις κ.λπ.", "Βρήκα σαράντα δύο αρχεία, για παράδειγμα σημειώσεις και λοιπά"),
        ("Κάνει $200 ή €15.", "Κάνει διακόσια δολάρια ή δεκαπέντε ευρώ."),
        ("Το Bitcoin πήγε 64.500 δολάρια.", "Το μπιτκόιν πήγε εξήντα τέσσερις χιλιάδες πεντακόσια δολάρια."),
        ("Τηλ. 210 1234567", "τηλέφωνο δύο ένα μηδέν , ένα δύο τρία τέσσερα πέντε έξι επτά"),
        ("Στις 11 Σεπτεμβρίου 2026", "Στις έντεκα Σεπτεμβρίου 2026"),
    ])
    def test_verbalize_el(self, text, want):
        from voice_agent.greek import verbalize_el
        assert verbalize_el(text) == want

    def test_number_to_words_agrees_in_gender(self):
        from voice_agent.greek import number_to_words as n
        assert n(1) == "ένα" and n(1, "f") == "μία" and n(1, "m") == "ένας"
        assert n(213, "f") == "διακόσιες δεκατρείς" and n(101) == "εκατόν ένα" and n(100) == "εκατό"
        assert n(1000, "f") == "χίλιες" and n(2345) == "δύο χιλιάδες τριακόσια σαράντα πέντε"
        assert n(2_500_000) == "δύο εκατομμύρια πεντακόσιες χιλιάδες"

    def test_the_greek_voice_gets_verbalized_text_and_the_english_voice_does_not(self, monkeypatch):
        from voice_agent.agent import Agent
        monkeypatch.setattr(config, "SPEAKERS", False)
        got = []
        class FakeSpeaker:
            speaking = False
            def say(self, text, lang, block=False): got.append((text, lang))
            def stop(self): pass
        class FakeListener:
            import threading as _th
            speech_started = _th.Event()
            def flush(self): pass
            def mute(self, on): pass
        ag = Agent(voice=False, with_mcp=False, log=lambda s: None)
        ag.speaker, ag.listener = FakeSpeaker(), FakeListener()
        ag.say("Κοστίζει 1.250 ευρώ. It costs 1,250 euros.")
        assert got == [("Κοστίζει χίλια διακόσια πενήντα ευρώ.", "el"), ("It costs 1,250 euros.", "en")]


class TestPrivateModeAndKnowledge:
    """The owner: 'never give my data to an external party'. Private mode is
    the default; the tools that reach the internet are not even offered."""

    def _mcp(self, names):
        from voice_agent.tools import Tool
        from voice_agent.guard import Risk as R_
        from voice_agent import tools as T
        out = []
        for n in names:
            risk = R_.EGRESS if n in T.VOICE_EGRESS else classify(n)
            out.append(Tool(n, "x", {"type": "object", "properties": {}}, risk, lambda a: "ok", source="mcp"))
        return out

    def test_private_mode_withholds_every_egress_tool(self, monkeypatch):
        from voice_agent import tools as T
        from voice_agent.tools import Registry
        monkeypatch.setattr(config, "PRIVATE", True)
        reg = Registry(); reg.add_mcp(self._mcp(list(T.VOICE_EGRESS) + ["analyze_folder", "get_system_evaluation"]))
        assert not (set(reg.tools) & T.VOICE_EGRESS)
        assert {"analyze_folder", "get_system_evaluation"} <= set(reg.tools)
        assert "private mode" in reg.summary()

    def test_outside_private_mode_egress_tools_need_the_spoken_phrase(self, monkeypatch, tmp_path):
        from voice_agent.tools import Tool
        monkeypatch.setattr(config, "PRIVATE", False)
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("research", {"query": "πληθωρισμός Ελλάδα σήμερα"})], "Εντάξει."],
            answers=["όχι, ακύρωσέ το"], tmp_path=tmp_path)
        sent = []
        ag.registry.tools["research"] = Tool("research", "x", {"type": "object", "properties": {}},
                                             Risk.EGRESS, lambda a: (sent.append(a), "r")[1], source="mcp")
        ag.handle("ψάξε για τον πληθωρισμό")
        assert sent == []
        ann = next(s for s in spoken if "ίντερνετ" in s or "GitHub" in s)
        assert "πληθωρισμός Ελλάδα σήμερα" in ann, "the exact text that would leave is read back"
        assert ag.last.tool_events[0]["outcome"] == "cancelled"

    def test_an_egress_argument_is_never_shortened(self):
        from voice_agent.guard import announce
        s = announce(Risk.EGRESS, "research", {"query": "ένα πολύ μεγάλο μήνυμα " * 20}, "el")
        assert s.count("μεγάλο") == 20 and "φεύγει από το μηχάνημα" in s

    def test_hidden_machinery_and_honest_descriptions(self, monkeypatch):
        from voice_agent import tools as T
        class Raw:
            def __init__(self, name, desc, props):
                self.name, self.description, self.inputSchema = name, desc, {"type": "object", "properties": props, "required": list(props)}
        raw = [Raw("apply_proposal", "HARDENED apply.", {"proposal_id": {"type": "string"}}),
               Raw("web_research", "SAFE web research tool - the ONLY approved way", {"url": {"type": "string"}, "query": {"type": "string"}, "user_confirmed": {"type": "boolean"}}),
               Raw("consult_wealth_mentor", "Consult", {"prompt": {"type": "string"}, "user_confirmed": {"type": "boolean"}})]
        monkeypatch.setattr(T, "asyncio", type("A", (), {"run": staticmethod(lambda c: raw), "wait_for": staticmethod(lambda c, timeout: c),
                                                            "TimeoutError": TimeoutError})())
        tools, err = T.discover_mcp_tools()
        names = {t.name: t for t in tools}
        assert "apply_proposal" not in names                       # hidden by voice
        wr = names["web_research"]
        assert wr.risk is Risk.EGRESS and "ONE known web page" in wr.description
        assert "user_confirmed" not in wr.parameters["properties"] and "user_confirmed" not in wr.parameters["required"]
        assert wr.parameters["properties"]["url"]["description"]
        assert names["consult_wealth_mentor"].risk is Risk.RISKY    # the server wanted a confirmation: announce

    def test_destructive_verbs_are_anchored(self):
        for n in ["list_skills", "get_information", "get_order_book", "read_messages", "check_installed_packages", "get_formatted_report"]:
            assert classify(n) is not Risk.DESTRUCTIVE, n
        for n in ["delete_folder", "rm_rf", "send_email", "run_command", "kill_process", "format_disk"]:
            assert classify(n) is Risk.DESTRUCTIVE, n

    def test_read_file_is_scoped_and_never_reads_secrets(self, monkeypatch, tmp_path):
        from voice_agent import tools as T
        inside = tmp_path / "in"; inside.mkdir(); (inside / "notes.txt").write_text("hello")
        (inside / ".env").write_text("SECRET=1"); (inside / "api-key.txt").write_text("k")
        outside = tmp_path / "out"; outside.mkdir(); (outside / "x.txt").write_text("x")
        monkeypatch.setenv("VOICE_READ_ROOTS", str(inside))
        assert T._read_file({"path": str(inside / "notes.txt")}) == "hello"
        assert T._read_file({"path": str(inside / ".env")}).startswith("(refused") and "SECRET" not in T._read_file({"path": str(inside / ".env")})
        assert T._read_file({"path": str(inside / "api-key.txt")}).startswith("(refused")
        assert T._read_file({"path": str(outside / "x.txt")}).startswith("(refused")
        assert T._list_folder({"path": str(outside)}).startswith("(refused")
        assert "notes.txt" in T._list_folder({"path": str(inside)})

    def test_the_facts_block_is_true_and_stable_within_a_day(self):
        import datetime
        f = brain.build_facts("9 tools", None, datetime.date(2026, 9, 11), private=True)
        assert str(config.REPO) in f and config.LLM_MODEL in f and "RX 9070 XT" in f
        assert "Παρασκευή 11 Σεπτεμβρίου 2026" in f and "current_time" in f and "ΙΔΙΩΤΙΚΗ" in f
        assert "recall" in f and "read_notes" in f
        assert f == brain.build_facts("9 tools", None, datetime.date(2026, 9, 11), private=True)
        g = brain.build_facts("9 tools", "ConnectError", datetime.date(2026, 9, 11), private=True)
        assert "ΔΕΝ απαντάει" in g and "ConnectError" in g
        assert "ΙΔΙΩΤΙΚΗ" not in brain.build_facts("9 tools", None, datetime.date(2026, 9, 11), private=False)

    def test_the_language_hint_rides_on_the_user_message_not_the_system_text(self, monkeypatch):
        seen = {}
        def fake_post(body):
            seen["body"] = body
            return {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        monkeypatch.setattr(brain, "_post", fake_post)
        brain.turn([{"role": "user", "content": "hello"}], [], "en", facts="FACTS")
        sys_a = seen["body"]["messages"][0]["content"]
        assert "Answer in English" not in sys_a and "FACTS" in sys_a
        assert seen["body"]["messages"][-1]["content"].endswith("(Answer in English.)")
        brain.turn([{"role": "user", "content": "γεια"}], [], "el", facts="FACTS")
        assert seen["body"]["messages"][0]["content"] == sys_a, "byte-identical prefix across a language switch"

    def test_every_turn_is_logged_with_the_whisper_numbers_and_confirmations(self, monkeypatch, tmp_path):
        import json as _json
        from voice_agent.stt import Heard
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("delete_folder", {"path": "x"})], "Έγινε."],
            answers=["ναι", "ναι, συνέχισε"], tmp_path=tmp_path)
        ag._heard = Heard("σβήσε το", "el", 0.99, -0.3, 0.05, 1.8, 0.9)
        ag.handle("σβήσε το")
        rows = [_json.loads(l) for l in config.LOG_FILE.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1
        row = rows[0]
        assert row["heard"] == "σβήσε το" and row["final"] == "Έγινε." and row["error"] is None
        assert row["stt"] == {"lang": "el", "lang_prob": 0.99, "avg_logprob": -0.3, "seconds_audio": 1.8, "seconds_stt": 0.9}
        assert [a["heard"] for a in row["tools"][0]["confirm"]] == ["ναι", "ναι, συνέχισε"]

    def test_a_failed_turn_is_logged_too(self, monkeypatch, tmp_path):
        import json as _json
        from voice_agent.agent import Agent
        monkeypatch.setattr(brain, "turn", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        ag = Agent(voice=False, with_mcp=False, say=lambda t, l: None, log=lambda s: None)
        ag.handle("γεια")
        row = _json.loads(config.LOG_FILE.read_text(encoding="utf-8").splitlines()[-1])
        assert row["error"] == "RuntimeError" and row["heard"] == "γεια"

    def test_read_notes_returns_the_newest_and_recall_reads_the_log(self, monkeypatch):
        from voice_agent import tools as T
        for i in range(80):
            T._write_note({"text": f"note {i:03d}"})
        out = T._read_notes({"last_n": 2})
        assert "note 079" in out and "note 078" in out and "note 000" not in out
        import json as _json, datetime as _d
        config.LOG_FILE.write_text(_json.dumps({"when": _d.datetime.now().isoformat(timespec="seconds"),
                                               "heard": "τι είπαμε", "final": "αυτά"}, ensure_ascii=False) + "\n", encoding="utf-8")
        assert "εσύ: τι είπαμε / εγώ: αυτά" in T._recall({"days": 1})
        assert T._recall({"query": "zzz"}) == "(nothing matching)"

    def test_mcp_reconnects_in_the_background_and_says_so(self, monkeypatch, tmp_path):
        import threading, time as _t
        from voice_agent import agent as A
        from voice_agent.tools import Tool
        calls = {"n": 0, "threads": set()}
        def fake_discover(for_voice=True):
            calls["n"] += 1; calls["threads"].add(threading.current_thread().name)
            if calls["n"] == 1:
                return [], "ConnectError"
            return [Tool("get_system_evaluation", "x", {"type": "object", "properties": {}}, Risk.SAFE, lambda a: "ok", source="mcp")], None
        monkeypatch.setattr(A, "discover_mcp_tools", fake_discover)
        import voice_agent.tools as T
        monkeypatch.setattr(T, "discover_mcp_tools", fake_discover)
        monkeypatch.setattr(config, "MCP_RETRY_S", 0.01)
        monkeypatch.setattr(brain, "turn", lambda *a, **k: brain.Reply(text="ok"))
        spoken = []
        ag = A.Agent(voice=False, with_mcp=True, say=lambda t, l: spoken.append(t), log=lambda s: None)
        assert ag.registry.mcp_error == "ConnectError"
        for _ in range(100):
            if "get_system_evaluation" in ag.registry.tools: break
            _t.sleep(0.02)
        assert "get_system_evaluation" in ag.registry.tools and ag.registry.mcp_error is None
        assert "MainThread" not in calls["threads"] - {"MainThread"} or calls["n"] >= 2
        ag.lang = "el"; ag.handle("γεια")
        assert spoken[0] == "Τα εργαλεία συνδέθηκαν."

    def test_get_system_status_reports_facts_without_a_shell(self, monkeypatch):
        from voice_agent import tools as T
        out = T._get_system_status({})
        assert "model server:" in out and "MCP tool server:" in out and "private mode:" in out
        assert "VRAM" not in out


class TestGlitchesFoundInTheFullRun:
    """2026-09-12, ten scenarios against the real model and tool server."""

    def test_a_word_mixing_latin_and_greek_letters_is_dropped(self):
        assert brain.strip_for_speech("Αυτό mengakτεύει τη μείωση.") == "Αυτό τη μείωση."
        assert brain.strip_for_speech("Το PowerShell και το αρχείο.") == "Το PowerShell και το αρχείο."

    def test_a_lone_word_before_a_tool_call_is_not_spoken(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[brain.Reply(text="been", tool_calls=[brain.ToolCall("c1", "current_time", {})]), "Είναι δέκα."],
            answers=[], tmp_path=tmp_path)
        ag.handle("τι ώρα είναι")
        assert "been" not in spoken and spoken[-1] == "Είναι δέκα."

    def test_an_empty_reply_after_a_tool_is_retried_then_the_result_is_read(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("current_time", {})], "", ""], answers=[], tmp_path=tmp_path)
        out = ag.handle("τι ώρα είναι")
        assert len(fake.calls) == 3, "one retry with a nudge"
        assert fake.calls[2][-1]["role"] == "user" and "Απάντησέ" in fake.calls[2][-1]["content"]
        assert out.startswith("Το εργαλείο επέστρεψε:") and "2026" in out or out.startswith("Το εργαλείο επέστρεψε:")
        assert ag.history[-2]["role"] == "tool", "the nudge is not kept in history"

    def test_the_retry_answer_is_used_when_it_comes(self, monkeypatch, tmp_path):
        ag, spoken, ran, fake = make_agent(monkeypatch,
            script=[[("current_time", {})], "", "Είναι δέκα."], answers=[], tmp_path=tmp_path)
        assert ag.handle("τι ώρα είναι") == "Είναι δέκα."
