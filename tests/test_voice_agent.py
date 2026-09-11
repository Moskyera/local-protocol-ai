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


class TestWhatTheAgentSaysBeforeActing:
    def test_destructive_announcement_names_the_target_and_asks_for_the_phrase(self):
        s = announce(Risk.DESTRUCTIVE, "delete_folder", {"path": "C:/tmp/old"}, "el")
        assert "C:/tmp/old" in s
        assert "ναι, συνέχισε" in s and "όχι, ακύρωσέ το" in s
        s = announce(Risk.DESTRUCTIVE, "run_command", {"command": "rm -rf build"}, "en")
        assert "rm -rf build" in s and "yes, go ahead" in s

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

    def turn(self, messages, schemas, lang_hint=None):
        self.calls.append([m for m in messages])
        item = self.script.pop(0)
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
        assert any("Προσοχή" in s and "C:/tmp/old" in s for s in spoken), spoken
        assert out == "Έγινε, διέγραψα τον φάκελο."
        # the tool result reached the model on the second call
        assert any(m.get("role") == "tool" and m.get("content") == "deleted" for m in fake.calls[1])

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
        parts = brain.split_sentences("Θέλεις να συνεχίσω; Αν ναι, πες το. Αλλιώς σταματώ.")
        assert parts == ["Θέλεις να συνεχίσω;", "Αν ναι, πες το.", "Αλλιώς σταματώ."]


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


class TestTheMicrophonePath:
    """MEASURED 2026-09-11: `import webrtcvad` raised ModuleNotFoundError
    (pkg_resources) on Python 3.14 + setuptools 82, so the voice path crashed
    on its first line while every text-mode test passed. The VAD is now
    Silero (ONNX, shipped inside faster-whisper); these tests run the real
    thing on real synthesised speech, no microphone needed."""

    def test_audio_module_does_not_import_webrtcvad(self):
        import inspect
        from voice_agent import audio
        assert "import webrtcvad" not in inspect.getsource(audio)

    @pytest.fixture(scope="class")
    def greek_speech_16k(self):
        """A Piper sentence resampled to 16 kHz; skipped if the voice is absent."""
        import numpy as np
        from voice_agent.tts import Speaker, VoiceMissing
        try:
            wav, rate = Speaker().synthesize("Καλημέρα, τι κάνεις σήμερα;", "el")
        except VoiceMissing as e:
            pytest.skip(str(e))
        wav = np.asarray(wav); n = int(len(wav) * config.AUDIO_RATE / rate)
        return np.interp(np.linspace(0, len(wav) - 1, n), np.arange(len(wav)),
                         wav.astype(np.float32)).astype(np.int16)

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
        quiet = np.zeros(F, np.int16)
        for _ in range(10): L._q.put(quiet.copy())
        for i in range(0, len(greek_speech_16k) - F + 1, F): L._q.put(greek_speech_16k[i:i + F].copy())
        for _ in range(40): L._q.put(quiet.copy())          # 1.3 s of silence ends it
        utt = L.listen(timeout_s=3)
        assert utt is not None
        spoken = len(greek_speech_16k) / config.AUDIO_RATE
        assert spoken - 0.3 <= len(utt) / config.AUDIO_RATE <= spoken + 0.6, "pre-roll + tail only"
        assert L.speech_started.is_set()
        assert L.listen(timeout_s=0.3) is None                # silence times out, never blocks
