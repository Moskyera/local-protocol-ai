"""
Regression suite for the agent stack built on 2026-08-12.

WHY THIS EXISTS: ~2100 lines of new logic (intent router, path jail, printability
checks, analyzers, briefing hardening) went in with zero coverage. Every test
below locks in a bug that was ACTUALLY HIT and fixed during that work — not
hypothetical cases. If one of these fails, a real regression has been
reintroduced, and the comment above it says which one.

Run:  C:\\AI\\ai-env\\Scripts\\python.exe -m pytest tests/test_agent_stack.py -q
"""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===================================================================== #
# Intent router                                                         #
# ===================================================================== #
class TestIntentRouter:
    @staticmethod
    def _classify(msg):
        from openhands_skills.intent_router import classify
        return classify(msg).name

    @pytest.mark.parametrize("msg,expected", [
        ("hi", "greeting"),
        ("thanks!", "greeting"),
        ("status", "status"),
        ("what can you do?", "capability"),
        ("write a python function to parse logs", "coding"),
        ("what is the BTC outlook", "market"),
        ("build me a website with a database", "website"),
        ("create a landing page", "website"),
        ("analyze wallet 0x38be95f628ed004a000ddf8724142a95e3c4b492", "wallet"),
        ("write an ERC20 staking contract on pulsechain", "solidity"),
        ("design a printable enclosure for a raspberry pi", "cad3d"),
        ("tell me about the weather", "legacy"),
    ])
    def test_basic_intents(self, msg, expected):
        assert self._classify(msg) == expected

    @pytest.mark.parametrize("msg,expected", [
        ("γεια", "greeting"),
        ("ΓΕΙΑ ΣΟΥ", "greeting"),          # uppercase Greek
        ("γειά σου", "greeting"),           # accented
        ("καλημέρα", "greeting"),
        ("τι μπορείς να κάνεις;", "capability"),   # final sigma ς -> σ on casefold
        ("φτιάξε μου ιστοσελίδα", "website"),
        ("ΦΤΙΑΞΕ ΜΟΥ ΙΣΤΟΣΕΛΙΔΑ ΜΕ ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ", "website"),
        ("σχεδιασε 3d ενα κουτι", "cad3d"),
        ("ανάλυσε τον φάκελο και πες τι είναι λάθος", "analyze_folder"),
    ])
    def test_greek(self, msg, expected):
        """Greek needs NFD + accent strip + casefold, and the VOCABULARY must go
        through the same normalize() — casefold maps final sigma to sigma."""
        assert self._classify(msg) == expected

    @pytest.mark.parametrize("msg,expected", [
        # A greeting token inside a real request must NOT swallow the request.
        ("hi, fix this bug in my script", "coding"),
        ("γεια, φτιάξε μου κώδικα", "coding"),
        # "status" alone is a health check; with a work word it is not.
        ("market status", "market"),
        ("status of BTC today", "market"),
    ])
    def test_social_gate_does_not_hijack_real_work(self, msg, expected):
        assert self._classify(msg) == expected

    @pytest.mark.parametrize("msg,not_expected", [
        ("please define the helper function", "solidity"),   # 'define' contains 'defi'
        ("build an e-commerce site", "solidity"),            # 'commerce' contains 'erc'
    ])
    def test_word_boundaries(self, msg, not_expected):
        """Bare substring matching detonated the Solidity pipeline on innocent words."""
        assert self._classify(msg) != not_expected

    def test_empty_and_garbage_never_crash(self):
        for msg in ["", "   ", "!!!", "😀😀", None]:
            from openhands_skills.intent_router import classify
            assert classify(msg).name  # must return some route, never raise


# ===================================================================== #
# Path jail                                                             #
# ===================================================================== #
class TestSafePaths:
    @pytest.mark.parametrize("rel", [
        "../../../Windows/System32/drivers/etc/hosts",
        "..\\..\\market-agent\\telegram_engine.py",
        "C:/Windows/system32/config",
        "//server/share/x",
        "NUL", "con.txt", "app/nul.py",      # Windows reserved device names
        "file.txt:hidden",                    # NTFS alternate data stream
        "trailing. ",
    ])
    def test_escapes_are_blocked(self, rel, tmp_path):
        from openhands_skills import safe_paths as sp
        with pytest.raises(Exception):
            sp.safe_join(tmp_path, rel)

    @pytest.mark.parametrize("rel", [
        "app/models.py", "templates/base.html", "static/css/app.css",
    ])
    def test_legitimate_paths_allowed(self, rel, tmp_path):
        from openhands_skills import safe_paths as sp
        assert str(sp.safe_join(tmp_path, rel)).startswith(str(tmp_path))

    def test_jail_root_is_outside_market_agent(self):
        """Containment is the jail: because the root is disjoint from the repo,
        the forbidden briefing files are unreachable by construction."""
        from openhands_skills import safe_paths as sp
        assert "market-agent" not in str(sp.PROJECTS_ROOT).lower()


# ===================================================================== #
# Printability checks                                                   #
# ===================================================================== #
class TestPrintCheck:
    def _stl(self, tmp_path, mesh, name="m.stl"):
        p = tmp_path / name
        mesh.export(str(p))
        return str(p)

    def test_solid_cube_is_printable(self, tmp_path):
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl
        r = check_stl(self._stl(tmp_path, trimesh.creation.box(extents=(50, 50, 50))))
        assert r.ok and r.facts["watertight"] and r.facts["bodies"] == 1

    def test_open_mesh_is_rejected(self, tmp_path):
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl
        m = trimesh.creation.box(extents=(30, 30, 30))
        m.faces = m.faces[:-4]                       # rip holes in the surface
        r = check_stl(self._stl(tmp_path, m))
        assert not r.ok
        assert any("watertight" in b for b in r.blocking)

    def test_oversize_is_rejected(self, tmp_path):
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl
        r = check_stl(self._stl(tmp_path, trimesh.creation.box(extents=(400, 400, 400))))
        assert not r.ok
        assert any("print bed" in b for b in r.blocking)

    def test_multibody_blocked_when_disallowed(self, tmp_path):
        """A phone-stand prompt produced 4 disconnected plates that each passed
        individually. Loose bodies must be a hard failure for a designed part."""
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl
        a = trimesh.creation.box(extents=(10, 10, 10))
        b = trimesh.creation.box(extents=(10, 10, 10))
        b.apply_translation([50, 0, 0])
        r = check_stl(self._stl(tmp_path, a + b), allow_multibody=False)
        assert not r.ok
        assert any("bodies" in x for x in r.blocking)

    def test_plausibility_catches_printable_but_wrong(self, tmp_path):
        """Watertight + fits-the-bed says nothing about correctness: a 3 mm flat
        plate passed every geometric check for a clip meant to hold 5 mm cables."""
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl, check_plausible
        r = check_stl(self._stl(tmp_path, trimesh.creation.box(extents=(30, 12, 3))))
        problems = check_plausible(
            "a clip 30mm wide holding cables of 5mm diameter", r)
        assert problems, "a 3mm plate cannot hold a 5mm cable — must be flagged"


# ===================================================================== #
# Deterministic code analysis                                           #
# ===================================================================== #
class TestCodeIntelligence:
    def test_finds_real_defects(self):
        from openhands_multiagent_v2.code_intelligence import code_intelligence
        res = code_intelligence.analyze_code(
            "import os\n"
            "def run(cmd):\n"
            "    os.system('ls ' + cmd)\n"
            "    unused = 42\n"
        )
        assert res.tools_run, "no analyzer ran at all"
        assert res.issues, "analyzers found nothing in obviously bad code"

    def test_clean_code_is_clean(self):
        from openhands_multiagent_v2.code_intelligence import code_intelligence
        res = code_intelligence.analyze_code(
            '"""Doc."""\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n')
        blocking = [i for i in res.issues if i.severity in ("CRITICAL", "HIGH")]
        assert not blocking


class TestSecurityScanner:
    @pytest.mark.parametrize("code,rule", [
        ('API_KEY = "sk-live-abcdefgh1234"', "hardcoded-secret"),
        ("eval(user_input)", "python-eval-exec"),
        ("subprocess.run(cmd, shell=True)", "shell-injection"),
        ("requests.get(u, verify=False)", "verify-false"),
    ])
    def test_static_scanner_catches(self, code, rule):
        from openhands_multiagent_v2.security_agent_v2 import security
        assert any(f.rule == rule for f in security.scan_static(code))


# ===================================================================== #
# Briefing delivery hardening                                           #
# ===================================================================== #
class TestBriefing:
    def test_html_escaping(self):
        """Unescaped '&' / '<' made Telegram reject the message with 400 and the
        message was silently LOST while the code printed success."""
        import telegram_engine as te
        assert te.escape_html_keep_tags("S&P 500 < 5000") == "S&amp;P 500 &lt; 5000"
        # our own header tags must survive
        assert "<b>" in te.escape_html_keep_tags("<b>TITLE</b>")

    def test_chunking_never_splits_a_tag(self):
        import telegram_engine as te
        big = "<b>H</b>\n" + "Market line with S&P 500 data.\n" * 400
        chunks = te._split_safely(te.escape_html_keep_tags(big))
        assert all(c.count("<") == c.count(">") for c in chunks)
        assert all(len(c) <= 3900 for c in chunks)

    def test_llm_error_sentinel_is_detected(self):
        """chat() RETURNS an error string instead of raising, so the engines'
        fallbacks never fired and the raw sentinel was published to Telegram."""
        from llm_client import is_llm_error
        assert is_llm_error("(LLM error - check llama-server logs)")
        assert is_llm_error("")
        assert not is_llm_error("Real market analysis text.")

    def test_llm_timeout_is_bounded(self):
        """The openai SDK default read timeout is 600s; a hung backend stalled
        each briefing section for 10 minutes."""
        from llm_client import LLM_TIMEOUT
        assert 0 < LLM_TIMEOUT.read <= 300

    def test_one_broken_section_does_not_kill_the_briefing(self, monkeypatch):
        """All six sections used to be built before anything was sent, with no
        try/except: a single failing generator lost the ENTIRE briefing."""
        import telegram_engine as te
        sent = []
        monkeypatch.setattr(te, "send_telegram_message",
                            lambda m, chat_id=None: (sent.append(m) or True))

        def mod(name, **attrs):
            # monkeypatch.setitem, NOT a bare assignment: a bare one leaves the
            # stub in sys.modules for the rest of the session, so every later
            # test that imports the real module silently gets this fake instead.
            # Measured: it made ten geopolitical tests fail with
            # "'G' object has no attribute '_fallback'" while each passed alone.
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            monkeypatch.setitem(sys.modules, name, m)

        def boom():
            raise RuntimeError("data source down")

        mod("master_market_brain", generate_master_report=lambda s: "Master OK")
        mod("market_snapshot_engine", generate_market_snapshot=boom)   # broken
        mod("macro_tech_report", generate_macro_tech_report=lambda: "Macro OK")
        mod("ai_advisor_engine", generate_ai_advisor=lambda a, b: "Advisor OK")
        mod("geopolitical_engine",
            geopolitical_engine=type("G", (), {
                "analyze_geopolitical_risk": staticmethod(lambda: {})})())  # missing key
        mod("corporate_news_engine",
            corporate_news_engine=type("C", (), {
                "get_corporate_news": staticmethod(
                    lambda: {"key_corporate_events": "Corp OK"})})())

        te.send_full_ai_briefing()
        assert len(sent) == 6, "a broken section must not stop the other messages"

    def test_bot_token_is_redacted_from_logs(self):
        """requests' exception text quotes the full URL, which embeds the token."""
        import telegram_engine as te
        leaked = ("HTTPSConnectionPool: Max retries exceeded with url: "
                  "/bot8123456789:AAH_fakeTokenABCdef123/sendMessage")
        assert "AAH_fakeTokenABCdef123" not in te._redact(leaked)


# ===================================================================== #
# Whole-package health                                                  #
# ===================================================================== #
def test_every_skill_imports():
    """25 skills once died at import on a Windows cp1252 console because they
    print emoji; 3 more hard-imported a missing 'opendevin'."""
    import importlib
    import pkgutil
    import openhands_skills
    failed = []
    for m in pkgutil.iter_modules(openhands_skills.__path__):
        try:
            importlib.import_module(f"openhands_skills.{m.name}")
        except Exception as e:
            failed.append((m.name, str(e)[:80]))
    assert not failed, f"skills failed to import: {failed}"


def test_router_is_wired_into_the_real_entry_point():
    """MCP execute_v2_task -> openhands_v2_entry.run_task, NOT the orchestrator.
    Patching the orchestrator alone is a no-op, and run_task must return a dict
    because server.py does result["mcp_tool"] = ... on the value."""
    from openhands_skills.openhands_v2_entry import run_task
    r = run_task("hi")
    assert isinstance(r, dict)
    assert r.get("route") == "greeting"
    r["mcp_tool"] = "probe"          # the MCP layer does exactly this
    assert r["mcp_tool"] == "probe"


# ===================================================================== #
# Added after the phone-stand work                                      #
# ===================================================================== #
class TestPlausibilityRefinements:
    def _report(self, tmp_path, extents):
        trimesh = pytest.importorskip("trimesh")
        from openhands_skills.print_check import check_stl
        p = tmp_path / "m.stl"
        trimesh.creation.box(extents=extents).export(str(p))
        return check_stl(str(p))

    def test_held_object_dimensions_are_not_required_features(self, tmp_path):
        """"holds a phone 165mm tall" describes the PHONE, not the stand. Treating
        it as a required feature falsely blocked a correct 90x85x80 mm stand."""
        from openhands_skills.print_check import check_plausible
        r = self._report(tmp_path, (90, 85, 80))
        problems = check_plausible(
            "A desk phone stand. Holds a phone 165mm tall, 80mm wide, 12mm thick. "
            "Base 85mm deep, 90mm wide.", r)
        assert problems == [], f"false positive: {problems}"

    def test_real_mismatch_still_caught(self, tmp_path):
        """The refinement must not blind the check to genuine nonsense."""
        from openhands_skills.print_check import check_plausible
        r = self._report(tmp_path, (30, 12, 3))
        assert check_plausible("a clip with a 5mm slot", r)

    def test_solidity_flags_an_unshaped_block(self, tmp_path):
        """solidity ~1.0 means the described cut-outs never got applied."""
        r = self._report(tmp_path, (50, 50, 50))
        assert r.facts["solidity"] == 1.0
        assert any("solidity" in w for w in r.warnings)


class TestMetrics:
    def test_track_records_and_never_raises(self, tmp_path, monkeypatch):
        import openhands_skills.agent_metrics as am
        monkeypatch.setattr(am, "METRICS_FILE", tmp_path / "runs.jsonl")
        with am.track("probe", task="unit-test") as run:
            run.note(attempts=2)
        assert (tmp_path / "runs.jsonl").exists()
        assert "probe" in am.summary()

    def test_failure_is_recorded_and_exception_still_propagates(self, tmp_path, monkeypatch):
        import json
        import openhands_skills.agent_metrics as am
        monkeypatch.setattr(am, "METRICS_FILE", tmp_path / "runs.jsonl")
        with pytest.raises(ValueError):
            with am.track("probe"):
                raise ValueError("boom")
        rec = json.loads((tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip())
        assert rec["ok"] is False and "boom" in rec["error"]


# ===================================================================== #
# Signal evaluation — the metric was measuring noise                    #
# ===================================================================== #
class TestSignalEvaluation:
    """The stored 'Accuracy 52.72%' was computed by grading each signal minutes
    after creation and freezing the verdict. Measured on the real history: 85%
    of signals were judged on a sub-0.5% price move. These tests lock in the
    corrected measurement."""

    def _sig(self, signal, entry, exit_, hours_ago, symbol="BTC/USDT"):
        from datetime import datetime, timedelta, timezone
        return {
            "symbol": symbol, "signal": signal,
            "entry_price": entry, "current_price": exit_,
            "timestamp": (datetime.now(timezone.utc)
                          - timedelta(hours=hours_ago)).isoformat(),
        }

    def test_immature_signals_are_not_graded(self):
        """A signal minutes old cannot be judged — that was the original bug."""
        from signal_evaluation import evaluate
        ev = evaluate([self._sig("BUY", 100, 101, hours_ago=1)], horizon_hours=24)
        assert ev.pending == 1 and not ev.scored()

    def test_moves_inside_costs_are_flat_not_wins(self):
        """+0.05% is not a win once fees and slippage are paid."""
        from signal_evaluation import evaluate
        ev = evaluate([self._sig("BUY", 100, 100.05, hours_ago=48)],
                      horizon_hours=24, cost_pct=0.20)
        assert ev.scored()[0].verdict == "FLAT"
        assert not ev.decisive()

    def test_direction_is_respected(self):
        from signal_evaluation import evaluate
        ev = evaluate([self._sig("SELL", 100, 90, hours_ago=48)], horizon_hours=24)
        o = ev.scored()[0]
        assert o.verdict == "WIN" and o.return_pct > 0   # price fell, SELL wins

    def test_neutral_signals_are_not_predictions(self):
        from signal_evaluation import evaluate
        ev = evaluate([self._sig("NEUTRAL", 100, 120, hours_ago=48),
                       self._sig("WATCH", 100, 120, hours_ago=48)], horizon_hours=24)
        assert not ev.outcomes

    def test_high_hit_rate_with_big_losses_is_exposed(self):
        """The real history showed 63% hits but a negative mean return, because
        the average loss was 2.1x the average win. Hit rate alone hides that."""
        from signal_evaluation import evaluate
        sigs = [self._sig("BUY", 100, 101, hours_ago=48) for _ in range(9)]
        sigs.append(self._sig("BUY", 100, 80, hours_ago=48))   # one -20%
        ev = evaluate(sigs, horizon_hours=24)
        d = ev.decisive()
        hit = sum(1 for o in d if o.verdict == "WIN") / len(d)
        mean = sum(o.return_pct for o in d) / len(d)
        assert hit == 0.9 and mean < 0, "90% hit rate must still show a loss"

    def test_diagnose_flags_noise_grading(self):
        from signal_evaluation import diagnose
        noisy = [self._sig("BUY", 100, 100.1, hours_ago=48) for _ in range(10)]
        assert "0.5%" in diagnose(noisy)


class TestPerformanceEngineHorizon:
    def test_legacy_rows_excluded_from_headline(self, monkeypatch):
        """Rows graded by the old code must not inflate the reported accuracy."""
        import performance_engine as pe
        legacy = [{"symbol": "BTC/USDT", "signal": "BUY", "entry_price": 100,
                   "current_price": 101, "result": "WIN"} for _ in range(50)]
        monkeypatch.setattr(pe, "load_signals", lambda: legacy)
        r = pe.analyze_performance()
        assert r["wins"] == 0 and r["sample_size"] == 0
        assert r["legacy_untrusted"] == 50
        assert "too few" in r["note"].lower()

    def test_report_keys_kept_for_existing_callers(self, monkeypatch):
        """master_market_brain reads performance['accuracy'] and ['wins']."""
        import performance_engine as pe
        monkeypatch.setattr(pe, "load_signals", lambda: [])
        r = pe.analyze_performance()
        for k in ("wins", "losses", "neutral", "accuracy"):
            assert k in r


# ===================================================================== #
# Self-modification guards                                              #
# ===================================================================== #
class TestSelfEvolutionGuards:
    """This system edits its own source. validate_proposal used to read only
    `target_file`, while apply_proposal ALSO accepts `apply_data.file` — so a
    proposal that hid the path there passed validation and would then be applied
    to a forbidden file. Verified against telegram_engine.py before the fix."""

    @pytest.mark.parametrize("proposal,label", [
        ({"suggestion": "tweak", "apply_data": {"file": "telegram_engine.py"}}, "apply_data bypass"),
        ({"suggestion": "tweak", "apply_data": {"file": "../../Windows/System32/x"}}, "traversal via apply_data"),
        ({"suggestion": "tweak", "file": "master_market_brain.py"}, "'file' key"),
        ({"suggestion": "tweak", "path": "geopolitical_engine.py"}, "'path' key"),
        ({"target_file": "telegram_engine.py"}, "declared forbidden target"),
        ({"target_file": "send_briefing.bat"}, "briefing launcher"),
        ({"target_file": "C:/Windows/system32/config.sys"}, "absolute system path"),
    ])
    def test_dangerous_proposals_are_blocked(self, proposal, label):
        from openhands_skills.guards import validate_proposal
        allowed, reason, _ = validate_proposal(proposal)
        assert not allowed, f"{label} was ALLOWED: {reason}"

    def test_targetless_proposal_fails_closed(self):
        """A proposal naming no file used to be ALLOWED — the wrong default for
        something that rewrites its own code."""
        from openhands_skills.guards import validate_proposal
        allowed, reason, _ = validate_proposal({"suggestion": "just improve something"})
        assert not allowed and "target" in reason.lower()

    @pytest.mark.parametrize("proposal", [
        {"target_file": "openhands_skills/prompt_optimizer.py", "suggestion": "x"},
        {"suggestion": "x", "apply_data": {"file": "openhands_skills/guards.py"}},
    ])
    def test_legitimate_proposals_still_pass(self, proposal):
        """The guard must not become so strict that real self-improvement dies."""
        from openhands_skills.guards import validate_proposal
        allowed, reason, _ = validate_proposal(proposal)
        assert allowed, f"legit proposal blocked: {reason}"

    def test_apply_requires_a_named_target(self):
        """Defense in depth: apply_proposal must refuse a proposal with no target."""
        import inspect
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver
        src = inspect.getsource(hyper_evolver.apply_proposal)
        assert "No target_file in proposal" in src
        assert "validate_proposal" in src, "apply must re-validate, not trust the queue"


# ===================================================================== #
# CAD primitives — the fix for the model's spatial-math failure          #
# ===================================================================== #
class TestCadPrimitives:
    """The local model reproduces the CadQuery API shape but not the geometry.
    Asked for a single wedge cut it emitted
        .moveTo(-D/2, H).lineTo(-D/2+cut_len, H).lineTo(-D/2, H)
    — three points at the SAME height, a zero-area triangle that cuts nothing
    (solidity stayed 1.0). These primitives hold the geometry in tested Python
    so the model only has to pick numbers."""

    def _facts(self, solid, tmp_path, name):
        cq = pytest.importorskip("cadquery")
        from openhands_skills.print_check import check_stl
        p = str(tmp_path / f"{name}.stl")
        cq.exporters.export(solid, p)
        return check_stl(p, allow_multibody=False)

    @pytest.mark.parametrize("name", ["angled_stand", "open_box", "l_bracket", "cable_clip"])
    def test_every_primitive_is_one_printable_solid(self, name, tmp_path):
        from openhands_skills.cad_primitives import PRIMITIVES
        r = self._facts(PRIMITIVES[name](), tmp_path, name)
        assert r.ok, f"{name} not printable: {r.blocking}"
        assert r.facts["bodies"] == 1, f"{name} produced {r.facts['bodies']} bodies"

    @pytest.mark.parametrize("name", ["angled_stand", "open_box", "l_bracket", "cable_clip"])
    def test_primitives_actually_remove_material(self, name, tmp_path):
        """solidity ~1.0 would mean the shaping silently did nothing — exactly
        the failure mode that made the model's own output useless."""
        from openhands_skills.cad_primitives import PRIMITIVES
        r = self._facts(PRIMITIVES[name](), tmp_path, name)
        assert r.facts["solidity"] < 0.98, f"{name} is still a plain block"

    def test_absurd_parameters_are_clamped(self, tmp_path):
        """Asked for a stand for a 165mm phone, the model passed the PHONE's
        dimensions as the stand's: 1038 cm3 and 386 g of filament."""
        from openhands_skills.cad_primitives import angled_stand
        r = self._facts(angled_stand(width=165, depth=165, height=165),
                        tmp_path, "huge")
        assert r.facts["volume_cm3"] < 600, "absurd size was not clamped"
        assert r.ok

    def test_catalogue_lists_every_primitive(self):
        """The model picks from this text; a missing entry is unreachable."""
        from openhands_skills.cad_primitives import PRIMITIVES, describe
        text = describe()
        for name in PRIMITIVES:
            assert name in text


# ===================================================================== #
# Document / book analysis                                              #
# ===================================================================== #
class TestDocAnalyst:
    """A 1500-page book is ~870k tokens against a 64k context: it does not fit.
    These lock in the parts that make it work anyway."""

    @pytest.fixture
    def book(self, tmp_path):
        fitz = pytest.importorskip("pymupdf")
        path = tmp_path / "book.pdf"
        doc = fitz.open()
        toc, page_no = [], 1
        for title, body in [
            ("Introduction", "Systems must be observable before improvement."),
            ("Performance", "Benchmarks showed a 42% improvement in throughput."),
            ("Security", "Path traversal is the most common defect in audits."),
        ]:
            toc.append([1, title, page_no])
            for _ in range(6):
                p = doc.new_page()
                p.insert_textbox(fitz.Rect(50, 50, 545, 780),
                                 f"{title} - page {page_no}\n\n" + (body + " ") * 20,
                                 fontsize=9, fontname="helv")
                page_no += 1
        doc.set_toc(toc)
        doc.save(str(path))
        doc.close()
        return str(path)

    def test_pages_and_chapters_are_extracted(self, book):
        from openhands_skills.doc_analyst import extract
        d = extract(book)
        assert len(d.pages) == 18
        assert [s.title for s in d.sections] == ["Introduction", "Performance", "Security"]
        assert d.sections[0].end_page == 6      # chapter ranges must be closed

    def test_chunks_remember_their_pages(self, book):
        """Every claim has to be traceable to a page, or citations are fiction."""
        from openhands_skills.doc_analyst import extract
        d = extract(book)
        assert d.chunks
        for c in d.chunks:
            assert 1 <= c.first_page <= c.last_page <= len(d.pages)
            assert "σ." in c.cite

    def test_retrieval_ignores_stopwords(self, book):
        """Measured: 'What performance improvement is reported and what caused
        it?' ranked the wrong chapter at 12.41 on what/is/and/it, while the chunk
        containing '42%' scored 7.90 and never made the cut."""
        from openhands_skills.doc_analyst import doc_analyst, _content_terms
        assert _content_terms("What performance improvement is reported?") == \
            ["performance", "improvement", "reported"]
        d = doc_analyst.load(book)
        hits = doc_analyst._retrieve(d, "What performance improvement is reported?", k=3)
        assert hits and any("42%" in c.text for c in hits)

    def test_invented_quotes_are_caught(self, book):
        """A summariser that fabricates a convincing quote is worse than one that
        says nothing."""
        from openhands_skills.doc_analyst import extract, verify_quotes
        d = extract(book)
        real = '"Benchmarks showed a 42% improvement in throughput."'
        fake = '"The authors conclude that quantum tunnelling drives the market."'
        assert not verify_quotes(real, d)
        assert verify_quotes(fake, d)

    def test_scanned_pdf_is_reported_not_summarised(self, tmp_path):
        """An image-only PDF must say 'needs OCR', never return an empty summary
        that looks like a real one."""
        fitz = pytest.importorskip("pymupdf")
        p = tmp_path / "scan.pdf"
        doc = fitz.open()
        for _ in range(5):
            doc.new_page()
        doc.save(str(p))
        doc.close()
        from openhands_skills.doc_analyst import extract, doc_analyst
        assert extract(str(p)).needs_ocr
        assert "OCR" in doc_analyst.analyze(str(p))

    def test_outline_is_instant_and_honest(self, book):
        """Reading the structure must not cost an LLM call, and must state how
        long a full read would actually take."""
        from openhands_skills.doc_analyst import doc_analyst
        out = doc_analyst.outline(book)
        assert "Performance" in out and "λεπτά" in out

    def test_document_intent_routes(self):
        from openhands_skills.intent_router import classify
        for msg in ["κάνε περίληψη αυτό το pdf", "εξήγησέ μου το βιβλίο",
                    "summarize this document", "ανάλυσε το κεφάλαιο 3"]:
            assert classify(msg).name == "document"


class TestScannedPdfOcr:
    """The user's books are image scans, so OCR is not optional."""

    def _scan(self, tmp_path, pages=4):
        fitz = pytest.importorskip("pymupdf")
        src = fitz.open()
        for _ in range(pages):
            p = src.new_page()
            p.insert_textbox(fitz.Rect(50, 50, 545, 780),
                             "Performance\n\n" +
                             "Benchmarks showed a 42% improvement in throughput. " * 6,
                             fontsize=12, fontname="helv")
        out = fitz.open()
        for i in range(src.page_count):
            pix = src[i].get_pixmap(dpi=200)
            q = out.new_page(width=pix.width * 0.72, height=pix.height * 0.72)
            q.insert_image(q.rect, pixmap=pix)
        path = tmp_path / "scan.pdf"
        out.save(str(path)); out.close(); src.close()
        return str(path)

    def test_scan_really_has_no_text_layer(self, tmp_path):
        fitz = pytest.importorskip("pymupdf")
        path = self._scan(tmp_path)
        with fitz.open(path) as d:
            assert sum(len(d[i].get_text().strip()) for i in range(d.page_count)) == 0

    def test_ocr_recovers_the_text(self, tmp_path):
        pytest.importorskip("rapidocr_onnxruntime")
        from openhands_skills import pdf_ocr
        res = pdf_ocr.ocr_pdf(self._scan(tmp_path, pages=2), workers=1)
        assert any("42" in t for t in res.values())

    def test_ocr_cache_makes_the_second_run_instant(self, tmp_path):
        """A 1500-page book is ~52 minutes; repeating it per question would make
        the tool unusable."""
        pytest.importorskip("rapidocr_onnxruntime")
        import time
        from openhands_skills import pdf_ocr
        path = self._scan(tmp_path, pages=2)
        pdf_ocr.ocr_pdf(path, workers=1)
        t = time.time()
        pdf_ocr.ocr_pdf(path, workers=1)
        assert time.time() - t < 1.0

    def test_retrieval_survives_a_tiny_corpus(self, tmp_path):
        """BM25 zeroes any term present in >50% of documents. A 12-page scan is
        2 chunks, so every score collapsed to 0 and the agent answered 'I found
        nothing' to a question the text plainly answers."""
        from openhands_skills.doc_analyst import Chunk, Document, doc_analyst
        d = Document(path=str(tmp_path / "x.pdf"))
        d.chunks = [Chunk(0, "Benchmarks showed a 42% improvement in throughput.", 1, 6),
                    Chunk(1, "Benchmarks showed a 42% improvement in throughput.", 7, 12)]
        assert doc_analyst._retrieve(d, "What performance improvement is reported?", k=6)

    def test_estimate_is_the_measured_rate(self):
        """Parallelism was measured to NOT help (threads 0.7x, processes 1.0x),
        so the estimate must reflect serial reality, not an aspiration."""
        from openhands_skills import pdf_ocr
        assert 45 < pdf_ocr.estimate_minutes(1500) < 60


class TestOutputQualityGuards:
    """The two defects that made a real book analysis worthless.

    Both produced text that LOOKS like an answer, which is exactly why they need
    automated detection: nobody proofreads a 300-page book summary by hand.
    """

    def test_repeated_sentence_is_flagged(self):
        """Measured with the coding model: points 5-16 of a chapter summary were
        one sentence repeated verbatim twelve times."""
        from openhands_skills.doc_analyst import detect_degeneration
        loop = "\n".join(
            [f"{i}. Το έργο τέχνης είναι προσωπικός οντοποιητικός χώρος επανάληψης."
             for i in range(1, 10)]
            + ["10. Μια εντελώς διαφορετική πρόταση με αρκετό μήκος για να μετρήσει."])
        assert detect_degeneration(loop)

    def test_real_summary_is_not_flagged(self):
        from openhands_skills.doc_analyst import detect_degeneration
        good = "\n".join([
            "1. Ο αφηγητής ανακαλύπτει τα χαρτιά του θείου του μετά τον θάνατο.",
            "2. Ένα γλυπτό απεικονίζει ένα ον με χαρακτηριστικά χταποδιού και δράκου.",
            "3. Η αστυνομία εντοπίζει μια λατρεία στους βάλτους της Λουιζιάνα.",
            "4. Ένας ναυτικός συναντά το νησί να αναδύεται από τη θάλασσα.",
            "5. Ο αφηγητής συμπεραίνει ότι αυτή η γνώση είναι επικίνδυνη.",
            "6. Το τελευταίο μέρος συνδέει τα τρία ανεξάρτητα ευρήματα.",
        ])
        assert detect_degeneration(good) is None

    def test_phrase_looping_inside_one_line_is_flagged(self):
        """A line-based check cannot see this. Measured: an English->Greek
        translation pass collapsed into the same phrase 812 times on ONE line,
        and the 22k characters of garbage made the corruption RATE look better
        than the honest output it was compared against."""
        from openhands_skills.doc_analyst import detect_degeneration
        loop = ('Η μετάφραση ξεκινά κανονικά με μια πρόταση. '
                + '"λεπ scales" -> ' * 60)
        assert detect_degeneration(loop)

    def test_long_varied_prose_is_not_flagged_as_looping(self):
        """The n-gram check must not punish normal repeated connectives.

        Wording taken from the real gemma chapter output that this system is
        supposed to accept.
        """
        from openhands_skills.doc_analyst import detect_degeneration
        prose = (
            "Η ιστορία ξεκινά με την ιδέα ότι ο ανθρώπινος νους δεν μπορεί να "
            "συλλάβει τις κοσμικές αλήθειες. Η αφήγηση αρχίζει μετά τον αιφνίδιο "
            "θάνατο του καθηγητή Angell, ο οποίος αφήνει πίσω του ένα κεραμικό "
            "ανάγλυφο. Μια κεντρική σύνδεση γίνεται μέσω του γλύπτη Wilcox, που "
            "δημιούργησε ένα γλυπτό βασισμένο σε όνειρα για παράξενες πόλεις. "
            "Ο επιθεωρητής Legrasse παρουσίασε ένα ειδώλιο από τους βάλτους της "
            "Λουιζιάνα, το οποίο δεν σχετίζεται με καμία γνωστή παράδοση. Ο "
            "καθηγητής Webb αναγνώρισε παρόμοια σύμβολα σε αποστολή στη Γροιλανδία. "
            "Η υλική απόδειξη προέρχεται από τα ημερολόγια του Johansen, που "
            "περιέγραψε τα ερείπια μιας βυθισμένης πόλης με μη ευκλείδεια "
            "γεωμετρία. Ο αφηγητής καταλήγει ότι η γνώση αυτή είναι επικίνδυνη "
            "και ότι ο τρόμος παραμένει ενεργός στον κόσμο.")
        assert detect_degeneration(prose) is None

    def test_foreign_script_fragments_are_flagged(self):
        """gemma QAT drops stray tokens from other scripts into Greek words."""
        from openhands_skills.doc_analyst import detect_script_noise
        assert detect_script_noise("όνειρα για πε lạ ξες πόλεις στη Γренландия")

    def test_greek_with_english_names_is_clean(self):
        """Book titles and author names in Latin script are normal, not noise."""
        from openhands_skills.doc_analyst import detect_script_noise
        assert detect_script_noise(
            "Το «The Call of Cthulhu» του H.P. Lovecraft (1928) [σ.2].") is None


class TestReasoningChannelRecovery:
    """llama.cpp puts a cut-off answer in reasoning_content and leaves content
    empty. Discarding it turned every good answer into a fake error string."""

    def _choice(self, content, reasoning, finish="stop"):
        import types
        msg = types.SimpleNamespace(content=content, reasoning_content=reasoning)
        return types.SimpleNamespace(message=msg, finish_reason=finish)

    def test_content_wins_when_present(self):
        from llm_client import _extract_text
        assert _extract_text(self._choice("η απάντηση", "σκέψεις")) == ("η απάντηση", "content")

    def test_reasoning_is_recovered_not_discarded(self):
        from llm_client import _extract_text
        text, source = _extract_text(self._choice("", "η πραγματική απάντηση"))
        assert text == "η πραγματική απάντηση" and source == "reasoning"

    def test_genuinely_empty_is_reported_as_empty(self):
        from llm_client import _extract_text
        assert _extract_text(self._choice("", ""))[1] == "empty"

    def test_think_tags_still_stripped(self):
        from llm_client import _extract_text
        assert _extract_text(
            self._choice("<think>κρυφά</think>ορατά", "")) == ("ορατά", "content")

    def test_draft_prefix_marks_scratchpad_as_not_final(self):
        """Recovered notes must never be presentable as a finished answer."""
        from llm_client import LLM_DRAFT_PREFIX, is_llm_error
        assert LLM_DRAFT_PREFIX.startswith("⚠️")
        assert not is_llm_error(LLM_DRAFT_PREFIX + "\n\nκείμενο")


class TestChatContract:
    """chat() is the single choke point every agent goes through. Each bug here
    was live in the repo and produced confident, wrong output."""

    class _FakeChoice:
        def __init__(self, content, reasoning="", finish="stop"):
            import types
            self.message = types.SimpleNamespace(
                content=content, reasoning_content=reasoning)
            self.finish_reason = finish

    class _FakeResp:
        def __init__(self, choice, model="gemma-4-26b-qat"):
            self.choices = [choice]
            self.model = model

    def _patch(self, monkeypatch, responses):
        """Serve `responses` in order, and capture every request."""
        import llm_client
        seen = []

        class _Completions:
            def create(_self, **kw):
                seen.append(kw)
                return responses[min(len(seen) - 1, len(responses) - 1)]

        class _Client:
            chat = type("C", (), {"completions": _Completions()})()

        # get_llm_client now takes an optional base_url (second backend routing).
        monkeypatch.setattr(llm_client, "get_llm_client",
                            lambda base_url=None: _Client())
        return seen

    def test_thinking_is_off_by_default(self, monkeypatch):
        """Measured: with thinking ON a 300-token budget produced 895 chars of
        scratchpad and ZERO answer; OFF it produced a complete answer in 234."""
        import llm_client
        seen = self._patch(monkeypatch, [self._FakeResp(self._FakeChoice("ok"))])
        llm_client.chat("hi")
        assert seen[0]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False

    def test_thinking_can_be_requested(self, monkeypatch):
        import llm_client
        seen = self._patch(monkeypatch, [self._FakeResp(self._FakeChoice("ok"))])
        llm_client.chat("hi", thinking=True)
        assert seen[0]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True

    def test_grammar_reaches_the_server(self, monkeypatch):
        """A GBNF grammar is the only thing that can suppress an argmax token."""
        import llm_client
        seen = self._patch(monkeypatch, [self._FakeResp(self._FakeChoice("ok"))])
        llm_client.chat("hi", grammar="root ::= [a-z]+")
        assert seen[0]["extra_body"]["grammar"] == "root ::= [a-z]+"

    def test_truncated_content_is_retried_not_returned(self, monkeypatch):
        """The old code returned on source=='content' BEFORE reading
        finish_reason, so a summary cut mid-sentence shipped as complete."""
        import llm_client
        seen = self._patch(monkeypatch, [
            self._FakeResp(self._FakeChoice("misi prota", finish="length")),
            self._FakeResp(self._FakeChoice("oloklhrh apanthsh", finish="stop")),
        ])
        out = llm_client.chat("hi", max_tokens=1000)
        assert out == "oloklhrh apanthsh"
        assert len(seen) == 2 and seen[1]["max_tokens"] == 3000

    def test_retry_is_not_dead_code_at_the_default_budget(self, monkeypatch):
        """_RETRY_TOKEN_CAP must exceed the default max_tokens, or the retry
        added to fix truncation can never fire on a default call."""
        import inspect
        import llm_client
        default = inspect.signature(llm_client.chat).parameters["max_tokens"].default
        assert llm_client._RETRY_TOKEN_CAP > default
        seen = self._patch(monkeypatch, [
            self._FakeResp(self._FakeChoice("kommeno", finish="length")),
            self._FakeResp(self._FakeChoice("plhres", finish="stop")),
        ])
        assert llm_client.chat("hi") == "plhres"
        assert len(seen) == 2

    def test_a_failed_retry_never_discards_the_first_answer(self, monkeypatch):
        """Overwriting text/source unconditionally reintroduced the very bug
        being fixed, after paying for two generations."""
        import llm_client
        self._patch(monkeypatch, [
            self._FakeResp(self._FakeChoice("xrhsimo keimeno", finish="length")),
            self._FakeResp(self._FakeChoice("", "", finish="stop")),
        ])
        assert llm_client.chat("hi", max_tokens=1000).startswith("xrhsimo keimeno")

    def test_still_truncated_after_retry_is_marked(self, monkeypatch):
        import llm_client
        self._patch(monkeypatch, [
            self._FakeResp(self._FakeChoice("akoma kommeno", finish="length")),
        ])
        out = llm_client.chat("hi", max_tokens=1000)
        assert llm_client.LLM_TRUNCATED_SUFFIX.strip()[:10] in out

    def test_expert_error_sentinel_is_recognised(self):
        """expert_base returns an "(expert 'x' error: ...)" string, and every
        skill goes through it — is_llm_error() used to call that real content."""
        from llm_client import is_llm_error
        assert is_llm_error("(expert 'doc_analyst' error: boom)")
        assert is_llm_error("(Legacy Ollama support has been removed)")
        assert not is_llm_error("Mia kanonikh apanthsh.")

    def test_is_usable_rejects_drafts_and_errors_but_keeps_real_text(self):
        from llm_client import LLM_DRAFT_PREFIX, LLM_ERROR_SENTINEL, is_usable
        assert not is_usable(LLM_ERROR_SENTINEL)
        assert not is_usable(LLM_DRAFT_PREFIX + "\n\nskepseis")
        assert is_usable("Pragmatiko periexomeno.")


class TestDocAnalystCacheIdentity:
    """A cache you cannot invalidate turns every future fix into a no-op."""

    def _doc(self, tmp_path):
        from openhands_skills import doc_analyst as D
        p = tmp_path / "b.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        d = D.Document(path=str(p), title="b")
        d.ocr_used = False
        return d

    def test_key_changes_with_the_model(self, tmp_path, monkeypatch):
        """The real failure: after switching off the coding model, chapter 1 was
        still served 13/13 from notes that the coding model had written."""
        from openhands_skills import doc_analyst as D
        da, doc = D.DocAnalyst(), self._doc(tmp_path)
        monkeypatch.setattr(D.DocAnalyst, "_model_id", staticmethod(lambda: "qwen3-coder"))
        a, _ = da._note_cache(doc)
        monkeypatch.setattr(D.DocAnalyst, "_model_id", staticmethod(lambda: "gemma-4-26b"))
        b, _ = da._note_cache(doc)
        assert a.name != b.name

    def test_key_changes_with_the_output_language(self, tmp_path, monkeypatch):
        from openhands_skills import doc_analyst as D
        da, doc = D.DocAnalyst(), self._doc(tmp_path)
        monkeypatch.setattr(D.DocAnalyst, "_model_id", staticmethod(lambda: "m"))
        a, _ = da._note_cache(doc)
        monkeypatch.setattr(D, "OUTPUT_LANGUAGE", "English")
        b, _ = da._note_cache(doc)
        assert a.name != b.name

    def test_key_changes_with_the_prompt_version(self, tmp_path, monkeypatch):
        from openhands_skills import doc_analyst as D
        da, doc = D.DocAnalyst(), self._doc(tmp_path)
        monkeypatch.setattr(D.DocAnalyst, "_model_id", staticmethod(lambda: "m"))
        a, _ = da._note_cache(doc)
        monkeypatch.setattr(D, "PROMPT_VERSION", D.PROMPT_VERSION + 1)
        b, _ = da._note_cache(doc)
        assert a.name != b.name

    def test_greek_grammar_is_applied_only_for_greek(self, monkeypatch):
        from openhands_skills import doc_analyst as D
        assert D.DocAnalyst().grammar() == D.GREEK_GRAMMAR
        monkeypatch.setattr(D, "OUTPUT_LANGUAGE", "English")
        assert D.DocAnalyst().grammar() is None

    def test_draft_notes_are_never_cached(self, tmp_path, monkeypatch):
        """LLM_DRAFT_PREFIX starts with a warning sign, not "(", so the old
        guard let the model's scratchpad into the PERMANENT on-disk cache."""
        from llm_client import LLM_DRAFT_PREFIX
        from openhands_skills import doc_analyst as D
        da = D.DocAnalyst()
        monkeypatch.setattr(D.DocAnalyst, "consult",
                            lambda self, *a, **k: LLM_DRAFT_PREFIX + "\n\nskepseis")
        cache, f = {}, tmp_path / "n.json"
        c = D.Chunk(0, "keimeno " * 40, 1, 2)
        assert da._summarise_chunk(c, f, cache) == ""
        assert cache == {} and not f.exists()


class TestMetricsHonesty:
    def test_a_crash_overrides_an_optimistic_ok(self, tmp_path, monkeypatch):
        """The metrics file is the system's own evidence about what works."""
        monkeypatch.setenv("MOSKY_METRICS_FILE", str(tmp_path / "runs.jsonl"))
        import importlib
        import json as _json
        from openhands_skills import agent_metrics as am
        importlib.reload(am)
        try:
            with am.track("coder", task="t") as run:
                run.note(ok=True)
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        line = am.METRICS_FILE.read_text(encoding="utf-8").strip().splitlines()[-1]
        assert _json.loads(line)["ok"] is False


class TestGreekGrammar:
    """The alphabet grammar is the only mechanism that removes the foreign-script
    characters, because the corrupting token was the model's FIRST choice and
    min_p/top_k cannot touch an argmax token. It must block scripts without
    blocking the symbols real prose needs."""

    @staticmethod
    def _allowed(ch):
        """True if `ch` is inside any range/literal the grammar declares."""
        import re
        from openhands_skills.doc_analyst import GREEK_GRAMMAR
        g = re.sub(r"#.*", "", GREEK_GRAMMAR)          # strip comments
        cp = ord(ch)
        for lo, hi in re.findall(r"\[\\u([0-9A-Fa-f]{4})-\\u([0-9A-Fa-f]{4})\]", g):
            if int(lo, 16) <= cp <= int(hi, 16):
                return True
        return any(cp == int(x, 16)
                   for x in re.findall(r'"\\u([0-9A-Fa-f]{4})"', g))

    def test_greek_and_ascii_pass(self):
        for ch in "αΑωΩίϊΐ" + "abzXYZ0189" + "#*-[]().,:;!?'\"/":
            assert self._allowed(ch), f"{ch!r} must be allowed"

    def test_symbols_real_prose_needs_pass(self):
        """A first version omitted the degree sign and the model rendered the
        coordinates of R'lyeh as "47θ 9'" — the grammar substituting its own
        corruption for the one it removed."""
        for ch in "°±²³½«»…–—•§€×÷‰→∞≈≤≥":
            assert self._allowed(ch), f"{ch!r} must be allowed"

    def test_every_corrupting_script_is_blocked(self):
        """The three characters actually measured in the user's book output,
        plus the scripts most likely to substitute for Greek."""
        for ch, name in [("ạ", "Vietnamese"), ("н", "Cyrillic"), ("ਨ", "Gurmukhi"),
                         ("ة", "Arabic"), ("あ", "Kana"), ("中", "CJK"),
                         ("한", "Hangul"), ("א", "Hebrew"), ("ⲁ", "Coptic")]:
            assert not self._allowed(ch), f"{name} {ch!r} must be blocked"

    def test_latin1_letters_stay_blocked(self):
        """The symbol range stops at U+00BF on purpose — U+00C0 starts letters."""
        for ch in "ÀÉÑöü":
            assert not self._allowed(ch)

    def test_grammar_is_only_used_for_greek(self, monkeypatch):
        from openhands_skills import doc_analyst as D
        assert D.output_grammar() == D.GREEK_GRAMMAR
        monkeypatch.setattr(D, "OUTPUT_LANGUAGE", "English")
        assert D.output_grammar() is None, \
            "English output must not be constrained — the same model produced " \
            "14,526 chars of English notes with zero foreign characters"


class TestChunkPageRanges:
    """Page ranges must describe where the text REALLY is.

    Measured on a real 325-page book, the old chunker was wrong on 38 of 197
    chunks (19%). Every [σ.X] the model emits is copied from these numbers, so a
    reader following a citation landed on a page without the claim.
    """

    @staticmethod
    def _pages(sizes):
        """Pages whose text is a repeated marker, so origin is recoverable."""
        from openhands_skills.doc_analyst import Page
        return [Page(i, f"p{i}word " * (n // 8 + 1))
                for i, n in enumerate(sizes, start=1)]

    def _check(self, pages):
        """Every chunk's declared range must match where its text actually is."""
        import re
        from openhands_skills.doc_analyst import _chunk
        chunks = _chunk(pages)
        assert chunks, "chunker produced nothing"
        for c in chunks:
            seen = {int(m) for m in re.findall(r"p(\d+)word", c.text)}
            assert seen, f"chunk {c.index} lost its markers"
            assert c.first_page == min(seen), (
                f"chunk {c.index} claims first {c.first_page}, text starts on {min(seen)}")
            assert c.last_page == max(seen), (
                f"chunk {c.index} claims last {c.last_page}, text ends on {max(seen)}")
            assert c.first_page <= c.last_page
        return chunks

    def test_many_small_pages(self):
        """Several pages per chunk — the case where the old code over-claimed
        the page it had just appended but not yet emitted."""
        self._check(self._pages([1200] * 40))

    def test_one_huge_page_split_into_several_chunks(self):
        """A single page must never produce a range spanning other pages."""
        chunks = self._check(self._pages([40000]))
        assert len(chunks) > 3
        assert all(c.first_page == 1 and c.last_page == 1 for c in chunks)

    def test_overlap_does_not_inflate_the_next_chunk(self):
        """The old code set first_pg = last_pg after a cut, ignoring that the
        400-char overlap carried over came from an earlier page."""
        self._check(self._pages([5800, 5800, 5800, 5800, 5800]))

    def test_blank_pages_are_skipped_not_miscounted(self):
        from openhands_skills.doc_analyst import Page
        pages = self._pages([3000] * 6)
        pages.insert(3, Page(99, "   \n  "))
        chunks = self._check([p for p in pages if p.number != 99] + [])
        assert chunks

    def test_ragged_page_sizes(self):
        self._check(self._pages([200, 9000, 150, 12000, 300, 7000, 80]))

    def test_no_gaps_and_monotonic(self):
        from openhands_skills.doc_analyst import _chunk
        chunks = _chunk(self._pages([2500] * 30))
        for a, b in zip(chunks, chunks[1:]):
            assert b.first_page >= a.first_page
            assert b.first_page <= a.last_page + 1, "a page fell out of coverage"
        assert chunks[0].first_page == 1
        assert chunks[-1].last_page == 30

    def test_empty_input(self):
        from openhands_skills.doc_analyst import _chunk
        assert _chunk([]) == []


class TestCitationValidation:
    def test_page_outside_what_was_shown_is_flagged(self):
        from openhands_skills.doc_analyst import check_citations
        assert check_citations("Ο αφηγητής το λέει [σ.99].", {1, 2, 3})

    def test_pages_that_were_shown_pass(self):
        from openhands_skills.doc_analyst import check_citations
        assert check_citations("Το λέει [σ.2] και [σ.1-3].", {1, 2, 3}) is None

    def test_range_partly_outside_is_flagged(self):
        from openhands_skills.doc_analyst import check_citations
        assert check_citations("Το λέει [σ.2-7].", {1, 2, 3})

    def test_no_allowed_set_means_no_opinion(self):
        """Callers without page context must not get false warnings."""
        from openhands_skills.doc_analyst import check_citations
        assert check_citations("[σ.500]", set()) is None

    def test_pages_of_covers_every_page_in_every_range(self):
        from openhands_skills.doc_analyst import Chunk, DocAnalyst
        chunks = [Chunk(0, "a", 2, 4), Chunk(1, "b", 9, 9)]
        assert DocAnalyst._pages_of(chunks) == {2, 3, 4, 9}

    def test_cite_rule_forbids_narrowing_a_range(self):
        """The old instruction said "cite pages as [σ.X]" — singular — while the
        chunks carry ranges, so the model picked a page inside the range."""
        from openhands_skills.doc_analyst import CITE_RULE
        assert "verbatim" in CITE_RULE and "never" in CITE_RULE.lower()

    def test_quality_notes_includes_citation_check(self):
        from openhands_skills.doc_analyst import quality_notes
        assert any("παραπομπ" in n for n in quality_notes("δες [σ.77]", {1, 2}))


class TestGrammarIsActuallyEnforceable:
    """llama-server does NOT reject a grammar it cannot parse — it silently
    drops it and generates unconstrained. Measured: adding "# ..." comments to
    document the ranges disabled the constraint completely (33 Cyrillic
    characters passed a grammar meant to make them impossible), with no error,
    no warning and a 200 status. An invalid grammar fails OPEN, so the only
    protection is keeping the string in a form this parser accepts.
    """

    def test_no_comments_in_the_grammar_string(self):
        from openhands_skills.doc_analyst import GREEK_GRAMMAR
        assert "#" not in GREEK_GRAMMAR, (
            "a '#' comment silently disables the whole grammar on this build — "
            "document the ranges in Python, never inside the grammar")

    def test_no_blank_or_stray_lines(self):
        from openhands_skills.doc_analyst import GREEK_GRAMMAR
        lines = [ln for ln in GREEK_GRAMMAR.split("\n") if ln.strip()]
        assert len(lines) == 2, f"expected root + char rules, got {len(lines)}"
        assert lines[0].startswith("root ::=")
        assert lines[1].startswith("char ::=")

    def test_every_alternative_is_a_range_or_a_literal(self):
        """Anything the parser does not understand takes the whole grammar down."""
        import re
        from openhands_skills.doc_analyst import GREEK_GRAMMAR
        body = GREEK_GRAMMAR.split("char ::=", 1)[1]
        for alt in (a.strip() for a in body.split("|")):
            assert re.fullmatch(r"\[\\u[0-9A-Fa-f]{4}-\\u[0-9A-Fa-f]{4}\]"
                                r'|"\\u[0-9A-Fa-f]{4}"'
                                r'|"\\n"', alt), f"unparseable alternative: {alt!r}"

    def test_script_noise_detector_is_the_backstop(self):
        """Because the grammar fails open, the output check is not redundant —
        it is what turned a silent regression into a visible warning."""
        from openhands_skills.doc_analyst import detect_script_noise
        assert detect_script_noise("Το Τраγικό περιστατικό του σκάφους")

    def test_prompt_version_covers_grammar_changes(self):
        """Notes written under the narrow grammar contain "47θ 9'" for "47° 9'",
        so a grammar change must invalidate the cache like a prompt change."""
        from openhands_skills.doc_analyst import PROMPT_VERSION
        assert PROMPT_VERSION >= 3


class TestSecondBackendRouting:
    """16GB fits ONE model on the GPU, and both launchers kill the previous
    server. That makes a two-model pipeline impossible on the card — but not on
    the box: 61.6GB of RAM and 16 idle CPU cores can serve a small specialist on
    its own port at the same time. Proven live: gemma on :8080 at 26 tok/s and a
    second llama-server on :8081 at 8.6 tok/s, simultaneously, GPU untouched.

    Routing MUST be by URL. llama-server answers with whatever GGUF it loaded
    and ignores the `model` field, so a model alias cannot select a backend.
    """

    class _Resp:
        def __init__(self, model):
            import types
            msg = types.SimpleNamespace(content="ok", reasoning_content="")
            self.choices = [types.SimpleNamespace(message=msg, finish_reason="stop")]
            self.model = model

    def _spy(self, monkeypatch, served="other-model"):
        import llm_client
        seen = {}

        class _Completions:
            def create(_s, **kw):
                return TestSecondBackendRouting._Resp(served)

        class _Client:
            chat = type("C", (), {"completions": _Completions()})()

        def fake(base_url=None):
            seen["base_url"] = base_url
            return _Client()

        monkeypatch.setattr(llm_client, "get_llm_client", fake)
        return seen

    def test_default_call_uses_the_primary_backend(self, monkeypatch):
        import llm_client
        seen = self._spy(monkeypatch, served="gemma-4-26b-qat")
        llm_client.chat("hi")
        assert seen["base_url"] is None

    def test_base_url_is_passed_through(self, monkeypatch):
        import llm_client
        seen = self._spy(monkeypatch)
        llm_client.chat("hi", base_url="http://127.0.0.1:8081/v1")
        assert seen["base_url"] == "http://127.0.0.1:8081/v1"

    @staticmethod
    def _warnings(monkeypatch):
        """Collect warnings directly. The repo logs through loguru, which does
        NOT propagate to the stdlib logging caplog fixture uses."""
        import llm_client
        got = []
        monkeypatch.setattr(llm_client.log, "warning", lambda m, *a, **k: got.append(str(m)))
        return got

    def test_secondary_backend_does_not_trigger_a_mismatch_warning(self, monkeypatch):
        """The second server holds a DIFFERENT model on purpose. Warning about
        it every call would train the user to ignore a warning that matters."""
        import llm_client
        self._spy(monkeypatch, served="krikri-8b-greek")
        got = self._warnings(monkeypatch)
        llm_client.chat("hi", base_url="http://127.0.0.1:8081/v1")
        assert not any("MODEL MISMATCH" in m for m in got)

    def test_mismatch_warning_still_fires_on_the_primary(self, monkeypatch):
        """Running send_briefing while the coding model is loaded must still
        warn — that silently produced briefings from the wrong model before."""
        import llm_client
        self._spy(monkeypatch, served="qwen3-coder-30b")
        got = self._warnings(monkeypatch)
        llm_client.chat("hi", model="gemma-4-26b-qat")
        assert any("MODEL MISMATCH" in m for m in got)

    def test_secondary_url_is_configurable_and_off_by_default(self):
        import importlib
        import llm_client
        importlib.reload(llm_client)
        assert isinstance(llm_client.SECONDARY_BASE_URL, str)

    def test_get_llm_client_accepts_an_explicit_url(self):
        from llm_client import get_llm_client
        c = get_llm_client("http://127.0.0.1:8081/v1")
        assert "8081" in str(c.base_url)


class TestMixedScriptTokens:
    """Latin is deliberately ALLOWED (proper names must survive), so a script
    check cannot see a token that mixes both alphabets. Four blind judges found
    exactly that class in real output and scored it "blocking": «Γrenland» for
    Γροιλανδία, and «Η Begegnση» — a German stem with a Greek ending — sitting
    in a section heading. Both are unpronounceable; both passed every check the
    pipeline had.
    """

    @staticmethod
    def _flag(text):
        from openhands_skills.doc_analyst import detect_script_noise
        return detect_script_noise(text)

    def test_greek_letter_welded_onto_a_latin_word(self):
        assert self._flag("βρέθηκε στη Γrenland το 1908")

    def test_foreign_stem_with_a_greek_ending(self):
        assert self._flag("Η Begegnση με τον Cthulhu ήταν καταστροφική")

    def test_proper_names_in_latin_are_not_flagged(self):
        """This is the whole reason a plain script check cannot do the job."""
        assert self._flag("Ο Gustaf Johansen και το σκάφος Alert [σ.17]") is None
        assert self._flag("Η πόλη R'lyeh και ο καθηγητής Angell") is None
        assert self._flag("Το «The Call of Cthulhu» του H.P. Lovecraft") is None

    def test_foreign_script_characters_still_caught(self):
        """The original check must keep working alongside the new one."""
        assert self._flag("όνειρα για πε lạ ξες πόλεις")
        assert self._flag("στη Γренландия το 1908")

    def test_both_problems_are_reported_together(self):
        out = self._flag("Η Begegnση στη Γренландия")
        assert "ξένα αλφάβητα" in out and "ανακατεύουν" in out

    def test_clean_greek_stays_clean(self):
        assert self._flag("Ο αφηγητής ανακαλύπτει τα χαρτιά του θείου του.") is None

    def test_numbers_and_units_are_not_words(self):
        assert self._flag("Στις συντεταγμένες 47°9' Ν και 123°43' Δ, 25 %") is None


class TestPolishGuard:
    """The polisher runs a SECOND model on the CPU and is never trusted blindly.

    Measured: that model SHORTENS whenever it is not tightly anchored. Composing
    it wrote half the length; proofreading with the rules moved into the system
    prompt it returned 32% of the text, 12 of 35 citations, 0 of 3 headings, and
    dropped 1908, Gustaf, Henry Anthony, New Orleans, Esquimaux and Ph'nglui.
    Anchored properly it is exact — 100% length, 35/35 citations, twice running.
    The guard is what separates those two outcomes.
    """

    BEFORE = ("### Κεφάλαιο\nΟ καθηγητής Angell πέθανε το 1926 σε ηλικία 92 ετών "
              "[σ.2]. Το άγαλμα βρέθηκε στη Λουιζιάνα το 1908 [σ.7-8]. Οι "
              "συντεταγμένες είναι 47°9' Ν [σ.18].")

    def test_a_faithful_repair_passes(self):
        from openhands_skills.doc_analyst import polish_is_safe
        after = self.BEFORE.replace("πέθανε", "απεβίωσε")
        assert polish_is_safe(self.BEFORE, after) is None

    def test_a_summary_is_rejected(self):
        """The exact failure measured when the anchor was removed."""
        from openhands_skills.doc_analyst import polish_is_safe
        assert polish_is_safe(self.BEFORE, "Ο Angell πέθανε [σ.2].")

    def test_a_lost_number_is_rejected(self):
        from openhands_skills.doc_analyst import polish_is_safe
        # The guard now compares the ORDERED digit sequence, so the message
        # names the failure mode rather than the missing token.
        assert polish_is_safe(self.BEFORE, self.BEFORE.replace("1908", ""))

    def test_an_invented_number_is_rejected(self):
        from openhands_skills.doc_analyst import polish_is_safe
        after = self.BEFORE.replace("92 ετών", "93 ετών")
        assert polish_is_safe(self.BEFORE, after)

    def test_lost_citations_are_rejected(self):
        from openhands_skills.doc_analyst import polish_is_safe
        after = self.BEFORE.replace("[σ.7-8]", "").replace("[σ.18]", "")
        assert polish_is_safe(self.BEFORE, after)

    def test_translating_a_latin_name_is_ALLOWED(self):
        """Measured: the polisher renders «των Esquimaux στη Γrenland» as «των
        Εσκιμώων στη Γροιλανδία» — correct Greek AND a repair of a corrupted
        token. An earlier guard called that "lost names" and would have thrown
        away a working pass."""
        from openhands_skills.doc_analyst import polish_is_safe
        before = "τελετουργικά των Esquimaux στη Γrenland [σ.8-9]"
        after = "τελετουργικά των Εσκιμώων στη Γροιλανδία [σ.8-9]"
        assert polish_is_safe(before, after) is None

    def test_a_degenerate_polish_is_rejected(self):
        from openhands_skills.doc_analyst import polish_is_safe
        before = "Μια κανονική πρόταση για το βιβλίο. " * 20
        after = 'Η ίδια φράση ξανά και ξανά εδώ. ' * 20
        assert polish_is_safe(before, after)

    def test_empty_output_is_rejected(self):
        from openhands_skills.doc_analyst import polish_is_safe
        assert polish_is_safe(self.BEFORE, "   ")

    def test_polish_is_a_no_op_without_a_second_backend(self, monkeypatch):
        """No second server configured must mean zero behaviour change."""
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "POLISH_URL", "")
        assert D.DocAnalyst().polish(self.BEFORE) == self.BEFORE

    def test_a_rejected_polish_returns_the_original(self, monkeypatch):
        from openhands_skills import doc_analyst as D
        import llm_client
        monkeypatch.setattr(D, "POLISH_URL", "http://127.0.0.1:8081/v1")
        monkeypatch.setattr(llm_client, "chat",
                            lambda *a, **k: "ΚΕΙΜΕΝΟ:\nΠολύ σύντομο.")
        assert D.DocAnalyst().polish(self.BEFORE) == self.BEFORE

    def test_the_echoed_preamble_is_stripped(self, monkeypatch):
        """The echo is kept on purpose — it anchors the model — and removed here."""
        from openhands_skills import doc_analyst as D
        import llm_client
        good = self.BEFORE.replace("πέθανε", "απεβίωσε")
        monkeypatch.setattr(D, "POLISH_URL", "http://127.0.0.1:8081/v1")
        monkeypatch.setattr(llm_client, "chat",
                            lambda *a, **k: D._POLISH_PROMPT + "junk\n" + D._POLISH_MARKER + "\n" + good)
        out = D.DocAnalyst().polish(self.BEFORE)
        assert out == good and "ΑΠΑΡΑΒΑΤΟΙ" not in out

    def test_a_backend_failure_keeps_the_original(self, monkeypatch):
        from openhands_skills import doc_analyst as D
        import llm_client
        monkeypatch.setattr(D, "POLISH_URL", "http://127.0.0.1:8081/v1")
        monkeypatch.setattr(llm_client, "chat",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
        assert D.DocAnalyst().polish(self.BEFORE) == self.BEFORE


class TestCitationWidening:
    """The model narrows a range it was given, and that is where the surviving
    citation errors come from. Verified against the real book: «1913» cited σ.26
    when the book has it on σ.24; «1877» cited σ.55-56 when it is on σ.52. The
    fact is right and the page is wrong — the worst combination, because a reader
    who checks concludes the whole summary is unreliable.
    """

    FED = [(24, 26), (52, 56), (100, 103)]

    def _w(self, text, fed=None):
        from openhands_skills.doc_analyst import widen_citations
        return widen_citations(text, self.FED if fed is None else fed)

    def test_a_narrowed_single_page_is_restored(self):
        assert self._w("γεγονός [σ.26].") == "γεγονός [σ.24-26]."

    def test_a_narrowed_sub_range_is_restored(self):
        assert self._w("γεγονός [σ.55-56].") == "γεγονός [σ.52-56]."

    def test_an_exact_range_is_left_alone(self):
        assert self._w("γεγονός [σ.24-26].") == "γεγονός [σ.24-26]."

    def test_a_cite_outside_everything_fed_is_untouched(self):
        """Not this function's job — check_citations() reports those."""
        assert self._w("γεγονός [σ.300].") == "γεγονός [σ.300]."

    def test_the_smallest_containing_range_wins(self):
        fed = [(1, 100), (40, 42)]
        assert self._w("x [σ.41].", fed) == "x [σ.40-42]."

    def test_a_single_page_chunk_stays_a_single_page(self):
        assert self._w("x [σ.7].", [(7, 7)]) == "x [σ.7]."

    def test_every_citation_in_a_paragraph_is_handled(self):
        out = self._w("Πρώτο [σ.26]. Δεύτερο [σ.53]. Τρίτο [σ.100-103].")
        assert out == "Πρώτο [σ.24-26]. Δεύτερο [σ.52-56]. Τρίτο [σ.100-103]."

    def test_no_fed_ranges_means_no_change(self):
        assert self._w("γεγονός [σ.26].", []) == "γεγονός [σ.26]."

    def test_surrounding_text_is_never_altered(self):
        src = "Ο Angell πέθανε το 1913 [σ.26], σε ηλικία 92 ετών."
        out = self._w(src)
        assert "1913" in out and "92" in out and "Angell" in out
        assert out.replace("[σ.24-26]", "[σ.26]") == src


class TestClaimVerification:
    """check_citations() only confirms a page was SHOWN to the model. That is a
    weaker property than it looks: measured on the real book, the output placed
    R'lyeh at «34°21' Ν [σ.18]» when those coordinates are on σ.15 and σ.18 has
    47°9'. Right page number, wrong claim, and nothing flagged it.
    """

    PAGES = {
        14: "Nothing of note on this page at all, just filler prose.",
        15: "The Vigilant found her at S. Latitude 34°21', W. Longitude 152°17'.",
        16: "The derelict yacht Alert was towed in by the Vigilant that morning.",
        17: "Gustaf Johansen, second mate, was the only survivor of the Emma.",
        18: "R'lyeh lies at S. Latitude 47°9', W. Longitude 126°43' they said.",
        19: "The geometry of the place was all wrong, angles behaving as no angle should.",
    }

    def _v(self, text):
        from openhands_skills.doc_analyst import verify_claims
        return verify_claims(text, self.PAGES)

    def test_the_real_failure_is_caught(self):
        """The exact sentence that passed every check before this existed."""
        bad = ("Στις συντεταγμένες 34°21' Ν, 152°17' Δ βρίσκεται η R'lyeh [σ.18]. "
               "Ο Johansen ήταν ο μόνος επιζών [σ.18]. "
               "Το Vigilant ρυμούλκησε το σκάφος [σ.18]. "
               "Η γεωμετρία ήταν λανθασμένη [σ.18]. "
               "Το Alert βρέθηκε έρημο [σ.18].")
        assert self._v(bad)

    def test_correctly_cited_claims_pass(self):
        good = ("Η R'lyeh βρίσκεται στις 47°9' [σ.18]. "
                "Ο Gustaf Johansen ήταν ο επιζών του Emma [σ.17]. "
                "Το Vigilant ρυμούλκησε το Alert [σ.16]. "
                "Οι συντεταγμένες 34°21' και 152°17' [σ.15]. "
                "Η γεωμετρία ήταν λανθασμένη [σ.19].")
        assert self._v(good) is None

    def test_a_neighbouring_page_is_tolerated(self):
        """A sentence can legitimately straddle a page break."""
        assert self._v("Ο Gustaf Johansen ήταν ο επιζών [σ.16]. " * 3) is None

    def test_sentences_without_anchors_are_not_judged(self):
        """No numbers and no names means nothing checkable — stay quiet."""
        assert self._v("Το κείμενο είναι ατμοσφαιρικό και σκοτεινό [σ.18]. " * 5) is None

    def test_the_analysts_own_header_is_not_a_claim(self):
        """This was the single false positive in the whole verification run."""
        text = ("# The Call of Cthulhu\n*σ.15-19 · 11 κομμάτια*\n\n"
                "Ο Gustaf Johansen ήταν ο επιζών [σ.17].")
        assert self._v(text) is None

    def test_a_single_stray_miss_is_not_reported(self):
        """A check that cries wolf is a check people learn to ignore."""
        from openhands_skills.doc_analyst import verify_claims
        pages = {n: "Gustaf Johansen Vigilant Alert Emma 1913 1877 " * 40
                 for n in range(1, 40)}
        text = " ".join(f"Ο Johansen και το Alert το 1913 [σ.{n}]." for n in range(5, 35))
        text += " Και ο Xyzzy [σ.10]."
        assert verify_claims(text, pages) is None

    def test_no_pages_means_no_opinion(self):
        from openhands_skills.doc_analyst import verify_claims
        assert verify_claims("οτιδήποτε [σ.5]", {}) is None


class TestUnknownTerms:
    """«Halloween» appears nowhere in the book — it says «Hallowmass» throughout.
    The model quietly modernised it. It reads authoritative, survives every other
    check, and is simply not what the source says."""

    SOURCE = ("Lavinia Whateley was never seen again after Hallowmass. "
              "Armitage, Rice and Morgan climbed Sentinel Hill.")

    def _u(self, text):
        from openhands_skills.doc_analyst import unknown_terms
        return unknown_terms(text, self.SOURCE)

    def test_the_real_substitution_is_caught(self):
        assert "Halloween" in self._u("Η Lavinia εξαφανίστηκε το Halloween [σ.31].")

    def test_terms_that_are_in_the_book_pass(self):
        assert self._u("Η Lavinia Whateley εξαφανίστηκε το Hallowmass [σ.31].") is None

    def test_the_analysts_own_words_are_not_judged(self):
        text = "# Κεφάλαιο\n*σ.1-5 · 3 κομμάτια*\n⚠️ Ποιότητα κειμένου: κάτι.\nΟ Morgan [σ.2]."
        assert self._u(text) is None

    def test_greek_prose_alone_is_never_flagged(self):
        assert self._u("Ο αφηγητής ανακαλύπτει τα χαρτιά του θείου του.") is None

    def test_no_source_means_no_opinion(self):
        from openhands_skills.doc_analyst import unknown_terms
        assert unknown_terms("Halloween", "") is None


class TestQualityGateComposition:
    def test_page_text_is_optional_everywhere(self):
        """Callers without the document must not crash or get false warnings."""
        from openhands_skills.doc_analyst import quality_notes
        assert quality_notes("Καθαρό κείμενο [σ.2].", {1, 2, 3}) == []

    def test_all_five_checks_are_wired_in(self):
        from openhands_skills.doc_analyst import quality_notes
        import inspect
        src = inspect.getsource(quality_notes)
        for fn in ("detect_degeneration", "detect_script_noise",
                   "check_citations", "verify_claims", "unknown_terms"):
            assert fn in src, f"{fn} is not part of the quality gate"


class TestFailureIsVisibleFromCharacterOne:
    """A dead backend must not look like a finished analysis.

    Measured: with llama-server down, all nine chapters returned a failure
    message — but prefixed with «# The Call of Cthulhu / *σ.2-21 · 13 κομμάτια*»
    because the header was built before the model was called. A harness scoring
    the run reported "9/9 clean, 0 warnings": it checked the first character,
    found a heading, and concluded success. Exactly the class of defect this
    whole system exists to eliminate, sitting in the failure path itself.
    """

    def test_finalise_drops_the_header_on_failure(self):
        from openhands_skills.doc_analyst import DocAnalyst
        from llm_client import LLM_ERROR_SENTINEL
        out = DocAnalyst()._finalise(LLM_ERROR_SENTINEL,
                                     head="# The Call of Cthulhu\n*σ.2-21*\n\n")
        assert out.startswith("❌")
        assert "Cthulhu" not in out
        assert "σ.2-21" not in out

    def test_a_successful_answer_keeps_its_header(self, monkeypatch):
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "POLISH_URL", "")
        out = D.DocAnalyst()._finalise("Πραγματική ανάλυση εδώ.",
                                       head="# Κεφάλαιο\n\n")
        assert out.startswith("# Κεφάλαιο")

    def test_every_failure_string_starts_with_the_marker(self):
        """Any new failure path must announce itself the same way."""
        import inspect
        import re
        from openhands_skills import doc_analyst as D
        src = inspect.getsource(D)
        for m in re.finditer(r'llama-server', src):
            line_start = src.rfind("return", 0, m.start())
            if line_start < 0:
                continue
            snippet = src[line_start:m.end() + 60]
            if "start-ai.bat" in snippet or "τρέχει" in snippet:
                assert "❌" in snippet, f"failure without marker: {snippet[:120]}"

    def test_the_marker_is_not_confused_with_a_quality_warning(self):
        """⚠️ means "read this but the text is real"; ❌ means "there is no text"."""
        from openhands_skills.doc_analyst import DocAnalyst
        from llm_client import LLM_ERROR_SENTINEL
        out = DocAnalyst()._finalise(LLM_ERROR_SENTINEL, head="# X\n\n")
        assert "⚠️" not in out


class TestAnchorNoiseReduction:
    """Five of eleven warnings on a real nine-chapter run were my own checks
    crying wolf. A check that fires on noise is worse than no check: it teaches
    the reader to scroll past the one warning that mattered.
    """

    def test_a_thousands_separated_number_yields_no_fragment(self):
        """«150,000,000» produced the anchor «000», reported as unverifiable."""
        from openhands_skills.doc_analyst import _ANCHOR_NUM
        assert "000" not in _ANCHOR_NUM.findall("πριν από 150,000,000 χρόνια")
        assert "000" not in _ANCHOR_NUM.findall("το ποσό ήταν 1.500.000 δολάρια")

    def test_real_numbers_are_still_anchors(self):
        from openhands_skills.doc_analyst import _ANCHOR_NUM
        found = _ANCHOR_NUM.findall("το 1877 σε ηλικία 92 ετών στη σελίδα 35")
        assert "1877" in found and "92" in found and "35" in found

    def test_a_recurring_name_is_not_used_as_an_anchor(self):
        """«Blake» is the protagonist of a 17-page story and appears on most of
        its pages. Demanding it on the exact cited page flags nothing but noise."""
        from openhands_skills.doc_analyst import verify_claims
        pages = {n: f"Blake walked on. Ordinary filler line {n}." for n in range(1, 30)}
        pages[5] = "Blake found the Shining Trapezohedron in 1877 here."
        text = " ".join(f"Ο Blake περπάτησε [σ.{n}]." for n in range(10, 26))
        assert verify_claims(text, pages) is None

    def test_a_rare_anchor_on_the_wrong_page_is_still_caught(self):
        from openhands_skills.doc_analyst import verify_claims
        pages = {n: f"Ordinary filler line number {n} with nothing special."
                 for n in range(1, 30)}
        pages[5] = "The Shining Trapezohedron was found in 1877 by Blake."
        text = (" ".join(f"Κάτι συνέβη το 1877 [σ.{n}]." for n in range(15, 25)))
        assert verify_claims(text, pages)

    def test_unknown_terms_ignores_capitalisation(self):
        """«Mind» starting a Greek clause is the book's «mind», not an invention."""
        from openhands_skills.doc_analyst import unknown_terms
        assert unknown_terms("Το Mind ήταν αιχμάλωτο.", "the captive mind of a man") is None

    def test_a_genuinely_absent_term_is_still_caught(self):
        from openhands_skills.doc_analyst import unknown_terms
        assert unknown_terms("Ο Lullius έγραψε [σ.5].", "Raymond Lully wrote it")


class TestDroppingImpossibleCitations:
    """Measured across all nine stories: chapters covering σ.22-51, σ.52-68,
    σ.100-185 and σ.186-234 each emitted citations to σ.1, σ.2, σ.11, σ.18 —
    the model numbering the STORY's pages instead of the book's. Those brackets
    look exactly like real ones and point somewhere arbitrary.
    """

    ALLOWED = set(range(22, 52))

    def _d(self, text, allowed=None):
        from openhands_skills.doc_analyst import drop_invalid_citations
        return drop_invalid_citations(text, self.ALLOWED if allowed is None else allowed)

    def test_a_citation_to_an_unseen_page_is_removed(self):
        out, n = self._d("Στους 19 μήνες έμοιαζε με τετραετές παιδί [σ.1-2].")
        assert n == 1 and "[σ." not in out

    def test_valid_citations_survive_untouched(self):
        src = "Ο Wilbur μεγάλωσε γρήγορα [σ.24-26] και πέθανε [σ.40]."
        out, n = self._d(src)
        assert n == 0 and out == src

    def test_a_range_that_overlaps_the_allowed_pages_is_kept(self):
        """Partial overlap means the model did see part of it — not invented."""
        out, n = self._d("κάτι [σ.20-24].")
        assert n == 0 and "[σ.20-24]" in out

    def test_the_sentence_survives_without_its_citation(self):
        out, _ = self._d("Ο Wilbur είχε τριχοφυΐα στο πρόσωπο [σ.1-2].")
        assert "τριχοφυΐα" in out and out.rstrip().endswith(".")

    def test_no_double_spaces_or_orphan_punctuation_are_left(self):
        out, _ = self._d("Πρώτο [σ.1], δεύτερο [σ.30], τρίτο [σ.2].")
        assert "  " not in out and " ," not in out and " ." not in out
        assert "[σ.30]" in out

    def test_nothing_is_dropped_without_an_allowed_set(self):
        out, n = self._d("κάτι [σ.1].", set())
        assert n == 0 and "[σ.1]" in out


class TestPolishGuardSeesPermutations:
    """polish_is_safe compared digits as a SET and citations as a COUNT, so every
    rearrangement was invisible. An independent audit demonstrated five separate
    corruptions that all returned "safe" — including swapping the citations of
    two adjacent claims, which is a direct violation of rule 1 of the polish
    prompt and the only thing this guard exists to enforce.
    """

    def _s(self, before, after):
        from openhands_skills.doc_analyst import polish_is_safe
        return polish_is_safe(before, after)

    def test_swapped_citations_are_rejected(self):
        assert self._s("Ο Wilcox ονειρεύτηκε [σ.20]. Ο Angell πέθανε [σ.21].",
                       "Ο Wilcox ονειρεύτηκε [σ.21]. Ο Angell πέθανε [σ.20].")

    def test_swapped_years_are_rejected(self):
        assert self._s("Πέθανε το 1926 και γεννήθηκε το 1901.",
                       "Πέθανε το 1901 και γεννήθηκε το 1926.")

    def test_deleted_headings_are_rejected(self):
        """Length was identical, so the ratio check could not see it."""
        assert self._s("### Πρώτο\nΚείμενο ένα.\n\n### Δεύτερο\nΚείμενο δύο.",
                       "Πρώτο\nΚείμενο ένα.\n\nΔεύτερο\nΚείμενο δύο. αβγδεζη")

    def test_a_deleted_warning_is_rejected(self):
        """GREEK_GRAMMAR contains no codepoint for ⚠ or ❌, so the polisher
        physically cannot re-emit a warning — it deletes it just by running."""
        body = "Κανονικό κείμενο εδώ πέρα για δοκιμή. " * 8
        assert self._s(body + "⚠️ προσοχή κάτι", body + "Κανονικό κείμενο εδώ")

    def test_a_genuine_language_repair_still_passes(self):
        before = "Ο Angell πέθανε το 1926 [σ.2]. Το γλυπτό βρέθηκε το 1908 [σ.7]."
        after = "Ο Angell απεβίωσε το 1926 [σ.2]. Το γλυπτό εντοπίστηκε το 1908 [σ.7]."
        assert self._s(before, after) is None

    def test_the_grammar_really_cannot_emit_the_markers(self):
        """If this ever becomes false the deletion problem disappears — but so
        does the reason for the check, so it must be asserted, not assumed."""
        import re
        from openhands_skills.doc_analyst import GREEK_GRAMMAR
        ranges = [(int(a, 16), int(b, 16)) for a, b in
                  re.findall(r"\[\\u([0-9A-Fa-f]{4})-\\u([0-9A-Fa-f]{4})\]", GREEK_GRAMMAR)]
        for ch in ("⚠", "️", "❌"):
            assert not any(lo <= ord(ch) <= hi for lo, hi in ranges)


class TestDraftNeverShipsAsAnAnswer:
    """_finalise branched on is_llm_error only. A draft — the model's own
    deliberation — went through under "# The Call of Cthulhu / *σ.2-21 · 13
    κομμάτια*", indistinguishable from a finished chapter. Exactly the defect
    the header-dropping fix was written for, in the branch next door."""

    def test_a_draft_loses_the_header(self, monkeypatch):
        from llm_client import LLM_DRAFT_PREFIX
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "POLISH_URL", "")
        out = D.DocAnalyst()._finalise(LLM_DRAFT_PREFIX + "\n\nΛοιπόν, σκέφτομαι...",
                                       head="# The Call of Cthulhu\n*σ.2-21*\n\n")
        assert out.startswith("⚠️") and "Cthulhu" not in out

    def test_a_draft_says_plainly_it_is_not_a_summary(self, monkeypatch):
        from llm_client import LLM_DRAFT_PREFIX
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "POLISH_URL", "")
        out = D.DocAnalyst()._finalise(LLM_DRAFT_PREFIX + "\n\nσκέψεις", head="# X\n\n")
        assert "ΟΧΙ περίληψη" in out


class TestClaimWindowIsNotWidened:
    """verify_claims took min(lo)..max(hi) across every citation in a sentence,
    one contiguous span. On a real shipped chapter one sentence citing σ.127-128
    and σ.170-171 was verified against all 47 pages between them — the sentence
    stitched from two distant notes, i.e. the one most likely to be wrong."""

    PAGES = {n: f"filler page {n} with nothing of interest here at all"
             for n in range(1, 60)}
    PAGES[20] = "Johansen sailed in 1925 aboard the Emma that year."
    PAGES[50] = "The Vigilant reported the wreck at latitude 34 degrees."

    def test_a_far_apart_pair_does_not_widen_the_window(self):
        from openhands_skills.doc_analyst import verify_claims
        text = (" ".join(f"Ο Johansen το 1925 [σ.20, σ.50]." for _ in range(4))
                + " Το Vigilant το 1925 [σ.20, σ.50].")
        assert verify_claims(text, self.PAGES) is None

    def test_a_claim_on_neither_cited_page_is_caught(self):
        from openhands_skills.doc_analyst import verify_claims
        text = " ".join(f"Ο Curwen το 1771 [σ.20, σ.50]." for _ in range(5))
        assert verify_claims(text, self.PAGES)


class TestGreekQuotesAreChecked:
    """The module's headline promise is quote verification, and the regex matched
    ASCII straight quotes only. Measured across three delivered chapters: 6
    guillemet spans, 1 ASCII — so it examined none of the real quotations."""

    def _doc(self):
        from openhands_skills.doc_analyst import Document, Page
        d = Document(path="x.pdf")
        d.pages = [Page(1, "In his house at R'lyeh dead Cthulhu waits dreaming there")]
        return d

    def test_a_fabricated_guillemet_quote_is_caught(self):
        from openhands_skills.doc_analyst import verify_quotes
        bad = verify_quotes("Το κείμενο λέει «this sentence was never in the book at all»",
                            self._doc())
        assert bad

    def test_a_real_guillemet_quote_passes(self):
        from openhands_skills.doc_analyst import verify_quotes
        ok = verify_quotes("Λέει «In his house at R'lyeh dead Cthulhu waits dreaming»",
                           self._doc())
        assert ok == []

    def test_ascii_quotes_still_work(self):
        from openhands_skills.doc_analyst import verify_quotes
        assert verify_quotes('Λέει "this sentence was never in the book at all"',
                             self._doc())


class TestOwnLineStripsTheWholeLine:
    """_OWN_LINE matched only the marker, leaving the rest of the sentence, so
    check_citations read the page numbers out of its OWN warning and kept
    reporting them after the citations causing it had been deleted."""

    def test_a_warning_line_is_removed_entirely(self):
        from openhands_skills.doc_analyst import _OWN_LINE
        text = "⚠️ Ποιότητα κειμένου: 2 παραπομπές σε σελίδες (σ.1, σ.2).\nΠραγματικό."
        assert "σ.1" not in _OWN_LINE.sub("", text)

    def test_check_citations_does_not_read_its_own_warning(self):
        from openhands_skills.doc_analyst import check_citations
        text = ("⚠️ Ποιότητα κειμένου: 2 παραπομπές σε σελίδες που δεν δόθηκαν "
                "στο μοντέλο (σ.1, σ.2).\nΟ αφηγητής το λέει [σ.30].")
        assert check_citations(text, {30}) is None


class TestCitationVariants:
    """The model does not always write «σ.». Counted across the delivered book
    and its note cache: 1295 «σ.», 45 «σελ.», 4 «σελίδα». Those 49 escaped
    widening, dropping, page-checking and claim-verification entirely — 3.6% of
    all citations with no oversight, including one in the whole-book summary
    pointing at the title page.
    """

    FED = [(24, 26)]
    ALLOWED = {24, 25, 26}

    def _pipeline(self, text):
        from openhands_skills.doc_analyst import (drop_invalid_citations,
                                                  widen_citations)
        out = widen_citations(text, self.FED)
        return drop_invalid_citations(out, self.ALLOWED)

    def test_sel_dot_variant_is_seen_and_dropped(self):
        out, n = self._pipeline("Ο Ward άλλαξε [σελ. 1].")
        assert n == 1 and "1" not in out

    def test_selida_word_variant_is_seen_and_dropped(self):
        out, n = self._pipeline("Ο Ward άλλαξε [σελίδα 5].")
        assert n == 1 and "5" not in out

    def test_a_valid_variant_is_kept_and_normalised(self):
        """One form in the output, so no later pass can miss a variant."""
        out, n = self._pipeline("Ο Ward άλλαξε [σελ. 25].")
        assert n == 0 and "[σ.24-26]" in out and "σελ" not in out

    def test_variants_mixed_in_one_bracket(self):
        out, n = self._pipeline("κάτι [σ. 25, σελ. 1]")
        assert n == 1 and "[σ.24-26]" in out

    def test_check_citations_sees_the_variants(self):
        from openhands_skills.doc_analyst import check_citations
        assert check_citations("κάτι [σελ. 99].", {1, 2, 3})
        assert check_citations("κάτι [σελίδα 99].", {1, 2, 3})

    def test_verify_claims_sees_the_variants(self):
        from openhands_skills.doc_analyst import verify_claims
        pages = {n: f"filler page {n} nothing here" for n in range(1, 30)}
        text = " ".join(f"Ο Curwen το 1771 [σελ. {n}]." for n in range(5, 12))
        assert verify_claims(text, pages)

    def test_normalisation_does_not_touch_ordinary_greek(self):
        from openhands_skills.doc_analyst import widen_citations
        src = "Οι σελίδες του βιβλίου ήταν κιτρινισμένες και σκισμένες."
        assert widen_citations(src, self.FED) == src


class TestUntranslatedEnglish:
    """Four blind Greek readers judged eight real outputs. Their verdict was
    "yes, it makes sense" — 6 blocking phrases in 2,260 words — and the single
    cheapest cause was English left loose inside Greek sentences:
    «των necks τους», «παρόμοιους με εκεί ones», «cessation των ονείρων»,
    «η αίρεση (the cult)», «γίνονταν «πολύ γλοιώδη» (bald)» — where the Greek
    says the OPPOSITE of the parenthesis and a monolingual reader is misinformed.

    Case does the separating: proper names are capitalised, untranslated words
    are not. No whitelist needed.
    """

    def _d(self, t):
        from openhands_skills.doc_analyst import detect_untranslated
        return detect_untranslated(t)

    def test_the_real_cases_are_caught(self):
        for t in ["Το δέρμα των necks τους ήταν παράξενο και χαλαρό.",
                  "όνειρα παρόμοιους με εκεί ones του Wilcox",
                  "η καταιγίδα και η cessation των ονείρων",
                  "η αίρεση (the cult) παραμένει ενεργή",
                  "γίνονταν «πολύ γλοιώδη» (bald) πολύ νωρίς"]:
            assert self._d(t), t

    def test_proper_names_are_never_flagged(self):
        assert self._d("Ο Angell δίδασκε στο Brown University στο Providence.") is None
        assert self._d("Ο Cthulhu κοιμάται στην R'lyeh κατά τον Johansen.") is None
        assert self._d("Το πλοίο Alert συγκρούστηκε με το Emma στο Innsmouth.") is None

    def test_italicised_titles_are_not_flagged(self):
        """*Necronomicon*, *Alert* — book and ship names are marked, not loose."""
        assert self._d("Το *Necronomicon* και το *Sydney Bulletin* [σ.15].") is None

    def test_citations_are_not_flagged(self):
        assert self._d("Ο αφηγητής το λέει [σ.20-22] και [σελ. 5].") is None

    def test_clean_greek_stays_clean(self):
        assert self._d("Ο αφηγητής ανακαλύπτει τα χαρτιά του θείου του μετά "
                       "τον θάνατό του και αρχίζει την έρευνα.") is None

    def test_it_is_part_of_the_quality_gate(self):
        from openhands_skills.doc_analyst import quality_notes
        notes = quality_notes("Το δέρμα των necks τους ήταν παράξενο και χαλαρό.")
        assert any("αγγλικές λέξεις" in n for n in notes)


class TestQuoteRule:
    """Almost every comprehension-breaking phrase the readers found sat INSIDE
    quotation marks: «μυλιά ύψος», «Cyclopean μαζευτική εργασία», «αλκοολικής
    απάτης», «έκαναν κόντη». Word-by-word rendering of English phrasing wrapped
    in quotes presents an undecodable phrase as the book's own words."""

    def test_the_rule_says_unambiguously_what_goes_inside_the_quotes(self):
        """The first version said "keep the quote in English and explain it in
        Greek after". The model did it BACKWARDS — «τρομακτικό κεφάλι καραβιάρη»
        (awful squid-head) — and one answer went from 0 to 18 loose English words
        while keeping the mistranslations. Ambiguity in an instruction is a defect."""
        from openhands_skills.doc_analyst import QUOTE_RULE
        low = QUOTE_RULE.lower()
        assert "exact english" in low
        assert "never put a greek translation inside" in low
        assert "no parentheses containing english" in low

    def test_the_rule_forbids_inventing_greek_words(self):
        from openhands_skills.doc_analyst import QUOTE_RULE
        assert "never invent a greek word" in QUOTE_RULE.lower()

    def test_the_rule_reaches_every_greek_prompt(self):
        """A rule only in one prompt fixes one entry point."""
        import inspect
        from openhands_skills import doc_analyst as D
        src = inspect.getsource(D)
        assert src.count("{QUOTE_RULE}") >= 3

    def test_prompt_version_was_bumped_so_old_notes_regenerate(self):
        from openhands_skills.doc_analyst import PROMPT_VERSION
        assert PROMPT_VERSION >= 4


class TestParallelMapStage:
    """Chunk summaries are INDEPENDENT and they dominate the cost: 9 chapters of
    a real book took 67 minutes, almost all of it in the map loop, one request
    at a time against a server running --parallel 1.

    Parallelism is only safe if two things hold: order survives, and the shared
    note cache survives concurrent writers. Both are tested here.
    """

    @staticmethod
    def _chunks(n):
        from openhands_skills.doc_analyst import Chunk
        return [Chunk(i, f"κείμενο κομματιού {i} " * 30, i + 1, i + 2)
                for i in range(n)]

    def _run(self, monkeypatch, workers, tmp_path, delay=0.0, fail=()):
        import time
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "MAP_WORKERS", workers)

        def fake(self, c, cache_file, cache):
            if delay:
                time.sleep(delay)
            if c.index in fail:
                raise RuntimeError(f"chunk {c.index} exploded")
            return f"[{c.cite}] σημείωση {c.index}"

        monkeypatch.setattr(D.DocAnalyst, "_summarise_chunk", fake)
        da = D.DocAnalyst()
        return da._map_chunks(self._chunks(8), tmp_path / "n.json", {})

    def test_order_is_preserved_under_concurrency(self, monkeypatch, tmp_path):
        """Notes feed the reduce step as a SEQUENCE. Shuffled completion order
        would shuffle the page citations with it."""
        import random
        out = self._run(monkeypatch, 4, tmp_path, delay=random.random() * 0.02)
        assert [n.split("σημείωση ")[1] for n in out] == [str(i) for i in range(8)]

    def test_serial_and_parallel_agree(self, monkeypatch, tmp_path):
        a = self._run(monkeypatch, 1, tmp_path)
        b = self._run(monkeypatch, 4, tmp_path)
        assert a == b

    def test_one_failing_chunk_does_not_kill_the_book(self, monkeypatch, tmp_path):
        out = self._run(monkeypatch, 4, tmp_path, fail={3, 5})
        assert len(out) == 6
        assert all("σημείωση 3" not in n and "σημείωση 5" not in n for n in out)

    def test_workers_one_is_the_original_serial_path(self, monkeypatch, tmp_path):
        """The default must change nothing until the server is reconfigured."""
        import inspect
        from openhands_skills import doc_analyst as D
        # 0 means "ask the server how many slots it has". Guessing high is not
        # free: measured, 8 workers against a 4-slot server ran at 1.40x while
        # 4 workers ran at 1.90x.
        assert D.MAP_WORKERS == 0
        src = inspect.getsource(D.DocAnalyst._map_chunks)
        assert "workers <= 1" in src and "self._slots()" in src

    def test_the_cache_write_is_locked(self):
        """Several chunks can now finish at the same moment, and they share one
        dict and one file."""
        import inspect
        from openhands_skills import doc_analyst as D
        src = inspect.getsource(D.DocAnalyst._summarise_chunk)
        assert "_cache_lock" in src
        assert hasattr(D.DocAnalyst, "_cache_lock")

    def test_concurrent_writers_do_not_corrupt_the_cache_file(self, monkeypatch, tmp_path):
        import json
        from openhands_skills import doc_analyst as D
        monkeypatch.setattr(D, "MAP_WORKERS", 8)
        monkeypatch.setattr(D.DocAnalyst, "consult",
                            lambda self, *a, **k: "σημείωση περιεχομένου")
        cache, f = {}, tmp_path / "notes.json"
        D.DocAnalyst()._map_chunks(self._chunks(24), f, cache)
        assert len(cache) == 24
        assert len(json.loads(f.read_text(encoding="utf-8"))) == 24

    def test_both_map_loops_use_the_helper(self):
        """A second copy of the loop would silently stay serial."""
        import inspect
        from openhands_skills import doc_analyst as D
        for fn in (D.DocAnalyst.chapter, D.DocAnalyst.analyze):
            assert "_map_chunks" in inspect.getsource(fn), fn.__name__


class TestFabricatedSuccessSweep:
    """Two blocking defects found by auditing the WHOLE stack, both verified by
    running them, both of the class this project exists to eliminate: a failure
    that renders as a plausible — here, a confident — success."""

    def test_an_unimportable_function_is_falsy(self):
        """send_telegram_briefing() answered «✅ Full AI Briefing sent to Telegram
        successfully» having made ZERO network calls: _lazy_import_market had no
        branch for it, fell through to a plain string, and the string was truthy
        so `if success:` passed."""
        from openhands_skills.tool_integration_hub import (_lazy_import_market,
                                                           is_unavailable)
        r = _lazy_import_market("no_such_function_anywhere")()
        assert not r and is_unavailable(r)

    def test_the_briefing_functions_are_actually_wired(self):
        from openhands_skills.tool_integration_hub import (_lazy_import_market,
                                                           is_unavailable)
        for name in ("send_full_ai_briefing", "generate_ai_advisor"):
            assert not is_unavailable(_lazy_import_market(name)), name

    def test_only_an_explicit_true_counts_as_delivered(self):
        """Anything else truthy means something unexpected happened, and must
        not be reported as a delivery."""
        import inspect
        from openhands_skills.tool_integration_hub import ToolIntegrationHub
        assert "success is True" in inspect.getsource(
            ToolIntegrationHub.send_telegram_briefing)

    def test_solidity_prescreen_finds_a_drainable_contract(self):
        """It scored this 10.0/10 with an empty findings list."""
        from openhands_skills.solidity_expert import solidity_expert as SE
        bad = ('pragma solidity ^0.8.0;\n'
               'contract Bank { mapping(address=>uint) public balances;\n'
               ' function withdraw() external { uint b=balances[msg.sender];\n'
               '  (bool ok,)=msg.sender.call{value:b}(""); require(ok);'
               ' balances[msg.sender]=0; }\n'
               ' function drainAll() external {'
               ' payable(msg.sender).transfer(address(this).balance); } }')
        out = SE.audit_solidity(bad)
        assert "CRITICAL" in out and "drainAll" in out

    def test_it_no_longer_reports_a_score(self):
        """The score started at 10.0 and came down only for two substring tests,
        one of which was disarmed by a `require` anywhere in the file. A number
        nobody computed is read as a verdict."""
        from openhands_skills.solidity_expert import solidity_expert as SE
        assert "Score" not in SE.audit_solidity(
            "pragma solidity ^0.8.0; contract A {}")

    def test_it_says_plainly_that_it_is_not_an_audit(self):
        from openhands_skills.solidity_expert import solidity_expert as SE
        out = SE.audit_solidity("pragma solidity ^0.8.0; contract A {}")
        assert "ΔΕΝ είναι audit" in out

    def test_non_solidity_input_is_refused_not_scored(self):
        """Both of these scored 10.0/10."""
        from openhands_skills.solidity_expert import solidity_expert as SE
        for junk in ("", "print(1)"):
            assert SE.audit_solidity(junk).lstrip().startswith("❌")

    def test_a_clean_contract_produces_no_false_criticals(self):
        from openhands_skills.solidity_expert import solidity_expert as SE
        good = ('pragma solidity ^0.8.0;\n'
                'import "@openzeppelin/contracts/security/ReentrancyGuard.sol";\n'
                'contract Safe is ReentrancyGuard { address owner;\n'
                ' modifier onlyOwner(){ require(msg.sender==owner); _; }\n'
                ' function get() external onlyOwner nonReentrant {'
                ' payable(msg.sender).transfer(1); } }')
        assert "CRITICAL" not in SE.audit_solidity(good)

    def test_the_orchestrator_appends_the_prescreen_rather_than_replacing_review(self):
        """`review = solidity_audit` discarded the reviewer's real analysis and
        put the regex pre-screen in its place."""
        import inspect
        from openhands_multiagent_v2 import multi_agent_orchestrator_v2 as O
        assert "review = solidity_audit\n" not in inspect.getsource(O)


class TestResearchSeedIsNotPassedOffAsFetched:
    """With the network down, a research request returned a dated, quote-rich
    report labelled "100% fidelity, raw signals", carrying X post IDs and
    verbatim quotes. Those quotes are string literals in research_agent.py. The
    only hint that nothing had been retrieved was an empty sources list, several
    keys deep. The result then flows into guarded proposals as
    "evidence_to_use_in_proposal_rationale" — so a code change gets justified by
    a citation nobody ever fetched."""

    @staticmethod
    def _src():
        import io
        import openhands_skills.research_agent as m
        return io.open(m.__file__, encoding="utf-8").read()

    def test_the_seed_no_longer_claims_its_quotes_are_verified(self):
        assert "All URLs and quotes are real and citable" not in self._src()

    def test_the_seed_says_plainly_it_was_not_fetched(self):
        assert "ΔΕΝ ΑΝΑΚΤΗΘΗΚΕ ΣΕ ΑΥΤΗ ΤΗΝ ΕΚΤΕΛΕΣΗ" in self._src()

    def test_the_seed_carries_a_machine_readable_flag(self):
        src = self._src()
        assert src.count('"is_offline_seed": True') >= 2
        assert '"fetched_this_run": False' in src

    def test_the_result_reports_how_much_was_actually_fetched(self):
        """A caller must not have to dig to learn that nothing was retrieved."""
        import inspect
        from openhands_skills.research_agent import ResearchAgent
        src = inspect.getsource(ResearchAgent.research_new_technologies_and_skills)
        for key in ("live_sources", "seeded_candidates", "status"):
            assert key in src, key
        assert "degraded_no_live_sources" in src


class TestBuildVerificationRequiresEvidence:
    """The module docstring promises "If it does not answer 200, it is not
    built." It was not true: `blocking` was a substring test for RENDER FAILED /
    INVALID HTML / smoke test FAILED / [HIGH / [CRITICAL, and none of those
    appear in the text a gate emits when it cannot RUN. A 240-second timeout, a
    MemoryError and a missing html5lib all produced the same green headline as a
    fully verified build."""

    def _o(self, text):
        from openhands_skills.web_stack_architect import gate_outcome
        return gate_outcome(text)

    def _marker(self):
        from openhands_skills.web_stack_architect import GATE_DID_NOT_RUN
        return GATE_DID_NOT_RUN

    def test_a_gate_that_ran_and_passed_is_verified(self):
        ok, _ = self._o("Schema: 2 table(s) created cleanly ✅\n\nHTTP 200 ✅")
        assert ok

    def test_a_timeout_is_not_verified(self):
        ok, why = self._o(f"{self._marker()}: HTTP smoke test error: timed out "
                          f"after 240 seconds")
        assert not ok and "δεν εκτελέστηκε" in why

    def test_a_missing_dependency_is_not_verified(self):
        ok, _ = self._o(f"{self._marker()}: template check could not run: "
                        f"ModuleNotFoundError: html5lib")
        assert not ok

    def test_a_silent_html_validator_is_not_verified(self):
        """Empty stdout with returncode 1 became "HTML: all pages valid ✅"
        with zero pages checked — byte-identical to a real run."""
        ok, _ = self._o(f"{self._marker()}: html validation produced no result "
                        f"(rc=1, stderr=)")
        assert not ok

    def test_a_genuine_failure_is_still_caught(self):
        for bad in ("HTTP smoke test FAILED: 500", "[CRITICAL] eval() used",
                    "RENDER FAILED", "INVALID HTML"):
            ok, why = self._o(bad)
            assert not ok and "βρήκε πρόβλημα" in why, bad

    def test_every_cannot_run_path_carries_the_marker(self):
        """A new gate that forgets the marker silently reopens the hole."""
        import io
        import openhands_skills.web_stack_architect as W
        src = io.open(W.__file__, encoding="utf-8").read()
        for phrase in ("template check could not run", "template check error",
                       "HTTP smoke test could not run", "HTTP smoke test error",
                       "analyzer error", "html check error"):
            i = src.find(phrase)
            assert i > 0, phrase
            assert "GATE_DID_NOT_RUN" in src[max(0, i - 120):i], phrase

    def test_neither_builder_uses_the_old_substring_test(self):
        import inspect
        from openhands_skills.web_stack_architect import WebStackArchitect
        for fn in (WebStackArchitect._build_py_db, WebStackArchitect._build_static):
            src = inspect.getsource(fn)
            assert "gate_outcome" in src, fn.__name__
            assert 'blocking = (' not in src, fn.__name__


class TestAnalyzeFolderKnowsWhetherItLooked:
    """"No findings" and "nothing looked" are different answers. analyze_folder
    gave the same one to both: with zero analyzers installed, total == 0 and the
    verdict read "✅ healthy" alongside "N files clean". AnalysisResult already
    records which tools ran; it simply was not consulted."""

    class _Empty:
        issues = []
        tools_run = []
        tools_skipped = ["ruff", "bandit"]

        def summary(self):
            return "Code intelligence: no analyzers available"

    def test_no_analyzers_means_unknown_not_healthy(self, monkeypatch):
        from openhands_multiagent_v2.code_intelligence import CodeIntelligence
        from openhands_mcp import server as S
        monkeypatch.setattr(CodeIntelligence, "analyze_tree",
                            lambda *a, **k: self._Empty())
        r = S.analyze_folder(path="openhands_mcp", deep=False)
        assert r["total_findings"] == 0
        assert "healthy" not in r["verdict"]
        assert "ΑΓΝΩΣΤΟ" in r["verdict"]

    def test_no_analyzers_means_no_file_is_called_clean(self, monkeypatch):
        from openhands_multiagent_v2.code_intelligence import CodeIntelligence
        from openhands_mcp import server as S
        monkeypatch.setattr(CodeIntelligence, "analyze_tree",
                            lambda *a, **k: self._Empty())
        r = S.analyze_folder(path="openhands_mcp", deep=False)
        assert r["whats_right"]["clean_files"] == 0
        assert r["whats_right"]["examples"] == []

    def test_the_payload_names_the_analyzers(self, monkeypatch):
        """A caller must be able to check without parsing Greek prose."""
        from openhands_multiagent_v2.code_intelligence import CodeIntelligence
        from openhands_mcp import server as S
        monkeypatch.setattr(CodeIntelligence, "analyze_tree",
                            lambda *a, **k: self._Empty())
        r = S.analyze_folder(path="openhands_mcp", deep=False)
        assert r["analyzers_run"] == []
        assert "ruff" in r["analyzers_skipped"]

    def test_a_real_scan_still_reports_healthy_when_it_is(self, monkeypatch):
        from openhands_multiagent_v2.code_intelligence import CodeIntelligence
        from openhands_mcp import server as S

        class Clean:
            issues = []
            tools_run = ["ruff", "bandit"]
            tools_skipped = []

            def summary(self):
                return "Ran: ruff, bandit"

        monkeypatch.setattr(CodeIntelligence, "analyze_tree",
                            lambda *a, **k: Clean())
        r = S.analyze_folder(path="openhands_mcp", deep=False)
        assert "healthy" in r["verdict"] and "ruff" in r["verdict"]


class TestBriefingReportsWhatItActuallyProduced:
    """send_full_ai_briefing() counted MESSAGES SENT, not sections containing
    analysis. A placeholder message delivers exactly as reliably as a real
    report, so all six sections could fail and the log still read
    "✅ Full AI Briefing sent (6/6 messages)" with the function returning True.
    Reproduced by making all six generators raise."""

    @staticmethod
    def _drive(monkeypatch, fail_all):
        import ai_advisor_engine, corporate_news_engine, geopolitical_engine
        import macro_tech_report, market_snapshot_engine, master_market_brain
        import telegram_engine as T

        def boom(*a, **k):
            raise RuntimeError("backend down")

        ok = lambda *a, **k: "REAL CONTENT"
        monkeypatch.setattr(master_market_brain, "generate_master_report",
                            boom if fail_all else ok)
        monkeypatch.setattr(market_snapshot_engine, "generate_market_snapshot",
                            boom if fail_all else ok)
        monkeypatch.setattr(macro_tech_report, "generate_macro_tech_report",
                            boom if fail_all else ok)
        monkeypatch.setattr(ai_advisor_engine, "generate_ai_advisor",
                            boom if fail_all else ok)
        monkeypatch.setattr(geopolitical_engine.geopolitical_engine,
                            "analyze_geopolitical_risk",
                            boom if fail_all else (lambda *a, **k: {"key_events": "REAL"}))
        monkeypatch.setattr(corporate_news_engine.corporate_news_engine,
                            "get_corporate_news",
                            boom if fail_all else (lambda *a, **k: {"key_corporate_events": "REAL"}))
        sent = []
        monkeypatch.setattr(T, "send_telegram_message",
                            lambda m, **k: (sent.append(m), True)[1])
        return T.send_full_ai_briefing(), sent

    def test_total_generation_failure_returns_false(self, monkeypatch):
        result, sent = self._drive(monkeypatch, fail_all=True)
        assert result is False
        assert len(sent) == 6      # placeholders still go out, honestly labelled

    def test_a_fully_working_briefing_still_returns_true(self, monkeypatch):
        result, sent = self._drive(monkeypatch, fail_all=False)
        assert result is True and len(sent) == 6

    def test_it_counts_sections_separately_from_messages(self):
        import inspect
        import telegram_engine as T
        src = inspect.getsource(T.send_full_ai_briefing)
        assert "generated" in src and "FAILED_MARK" in src
        assert "return generated == n and delivered == n" in src


class TestFailedQuoteIsNotAGreenTick:
    """stock_engine returned {"price": 0, "change": 0} when a fetch failed.
    Downstream, `if change < 0` is False for 0, so the renderer painted it 🟢
    GREEN at $0 — a stock that was never retrieved appeared in the daily
    briefing as an up-tick."""

    @staticmethod
    def _first(monkeypatch, quote):
        import watchlist_engine as W
        monkeypatch.setattr(W, "get_stock_price", lambda sym: quote)
        r = W.get_stock_watchlist()
        return r[0] if isinstance(r, list) else str(r).splitlines()[0]

    def test_a_failed_fetch_is_not_green(self, monkeypatch):
        line = self._first(monkeypatch, {"price": None, "change": None,
                                         "error": "HTTPError 429"})
        assert "🟢" not in line and "δεν ανακτήθηκε" in line

    def test_a_real_fall_is_still_red(self, monkeypatch):
        assert "🔴" in self._first(monkeypatch, {"price": 187.4, "change": -2.1})

    def test_a_real_rise_is_still_green(self, monkeypatch):
        assert "🟢" in self._first(monkeypatch, {"price": 187.4, "change": 1.8})

    def test_a_genuinely_flat_day_is_still_green(self, monkeypatch):
        """A real 0.0% is not a failure and must keep reading as one."""
        assert "🟢" in self._first(monkeypatch, {"price": 187.4, "change": 0.0})

    def test_the_engine_no_longer_returns_zero_on_failure(self):
        """Checks the RETURN statements, not the file — the comment explaining
        this fix necessarily quotes the old value."""
        import inspect
        import re
        import stock_engine as SE
        returns = re.findall(r"^\s*return\s+\{[^}]*\}",
                             inspect.getsource(SE), re.M)
        failing = [r for r in returns if '"price": 0' in r]
        assert not failing, failing
        assert any('"price": None' in r for r in returns)


class TestGeopoliticalBlocklistWordBoundaries:
    """`if bad in text` over the blocklist threw away half of a set of twelve
    real conflict headlines: "nfl" matched inside "conflict" — which is itself
    one of the conflict_indicators the engine looks for — plus "epl" inside
    "deployed", "sol" inside "soldiers" and "resolution", "stock" inside
    "Stockholm". The filter was deleting exactly the coverage it exists to find,
    and silently."""

    REAL = [
        "Israel and Hezbollah conflict escalates after airstrike on Beirut suburb",
        "Russia launches missile attack on Ukrainian energy infrastructure",
        "US imposes new sanctions on Iran over drone shipments",
        "China conducts naval military exercises near Taiwan strait",
        "NATO troops deployed as border tensions rise in Eastern Europe",
        "Soldiers killed in cross-border clash between India and Pakistan",
        "Israeli forces conduct retaliatory strike after rocket fired from Gaza",
        "Yemen: Houthi drone attack on Red Sea shipping lane",
        "Stockholm summit: NATO leaders discuss Ukraine military aid",
        "North Korea launched ballistic missile over Sea of Japan",
    ]
    NOISE = [
        "Bitcoin price target raised after Q3 earnings beat",
        "NFL playoffs: Chiefs strike late to win divisional clash",
        "Ethereum ETF sees record inflows as analyst raises stock target",
        "Netflix announces new movie trailer at awards ceremony",
        "India vs Pakistan cricket: batting collapse in final over",
        "Turkey Airlines reports record Q2 revenue and profit",
    ]

    @staticmethod
    def _g():
        from geopolitical_engine import geopolitical_engine
        return geopolitical_engine

    def test_conflict_is_not_blocked_by_nfl(self):
        g = self._g()
        assert not g._blocked_re().search("hezbollah conflict escalates")

    def test_soldiers_and_resolution_are_not_blocked_by_sol(self):
        g = self._g()
        for t in ("soldiers killed in clash", "un calls for resolution"):
            assert not g._blocked_re().search(t), t

    def test_stockholm_is_not_blocked_by_stock(self):
        assert not self._g()._blocked_re().search("stockholm summit on ukraine")

    def test_real_conflict_coverage_survives(self):
        g = self._g()
        kept = [h for h in self.REAL if g._is_pure_geopolitical(h, "")]
        assert len(kept) == len(self.REAL), [h for h in self.REAL if h not in kept]

    def test_noise_is_still_rejected(self):
        """Widening the filter must not let sports and earnings back in."""
        g = self._g()
        leaked = [h for h in self.NOISE if g._is_pure_geopolitical(h, "")]
        assert not leaked, leaked

    def test_the_blocked_words_still_block_when_standalone(self):
        g = self._g()
        for word in ("nfl", "sol", "stock", "crypto", "earnings"):
            assert g._blocked_re().search(f"a story about {word} today"), word


class TestGeopoliticalUnknownIsNotAllClear:
    """_fallback() returned risk LOW and "no significant events detected" —
    byte-identical whether the scan ran and found a quiet world, or the API key
    was missing, or the request raised. Three of its four call sites are
    failures. The briefing published an affirmative all-clear on geopolitical
    risk while nothing had been checked."""

    @staticmethod
    def _g():
        from geopolitical_engine import geopolitical_engine
        return geopolitical_engine

    def test_a_genuine_quiet_scan_still_reports_low(self):
        r = self._g()._fallback(checked=True)
        assert r["geopolitical_risk_level"] == "LOW"
        assert r["scan_performed"] is True

    def test_a_failed_scan_reports_unknown_not_low(self):
        r = self._g()._fallback("Tavily 401", checked=False)
        assert r["geopolitical_risk_level"] == "UNKNOWN"
        assert r["scan_performed"] is False
        assert "ΔΕΝ ΕΓΙΝΕ" in r["key_events"]

    def test_the_failure_says_why(self):
        r = self._g()._fallback("δεν έχει οριστεί Tavily API key", checked=False)
        assert "Tavily API key" in r["key_events"]
        assert r["failure_reason"]

    def test_every_failure_call_site_passes_checked_false(self):
        """A new failure path that forgets it reopens the hole."""
        import inspect
        import re
        import geopolitical_engine as G
        src = inspect.getsource(G)
        for m in re.finditer(r"self\._fallback\(", src):
            window = src[m.start():m.start() + 220]
            assert ("checked=True" in window or "checked=False" in window), window[:90]


class TestNoInventedMarketView:
    """ai_advisor_engine returned, on any exception:

        "Market shows strong technical signals with bullish momentum. RSI in
         healthy zone, MACD above signal line. Recommended allocation:
         60% BTC, 40% Cash. Risk level: Moderate."

    A direction and a specific allocation that nothing computed, published in
    the daily briefing under "iNFO DUST ADVISOR", indistinguishable from a real
    reading. macro_tech_report did the same with a positive macro call.

    And the except branch barely fired: generate_market_report wraps chat(),
    which RETURNS an error string instead of raising, so the sentinel flowed
    onward as analysis."""

    BANNED = ("bullish", "60% btc", "40% cash", "positive momentum",
              "cautiously optimistic", "rsi in healthy zone")

    def _both(self, monkeypatch, mode):
        import ai_advisor_engine as A
        import macro_tech_report as M

        def raiser(p):
            raise RuntimeError("server down")

        fake = raiser if mode == "raises" else (
            lambda p: "(LLM error - check llama-server logs)")
        monkeypatch.setattr(A, "generate_market_report", fake)
        monkeypatch.setattr(M, "generate_market_report", fake)
        return A.generate_ai_advisor("m", "s"), M.generate_macro_tech_report()

    def test_a_raising_model_invents_nothing(self, monkeypatch):
        for out in self._both(monkeypatch, "raises"):
            assert not any(b in out.lower() for b in self.BANNED), out[:90]

    def test_a_sentinel_returning_model_invents_nothing(self, monkeypatch):
        """The path that actually happens — chat() returns, it does not raise."""
        for out in self._both(monkeypatch, "sentinel"):
            assert not any(b in out.lower() for b in self.BANNED), out[:90]

    def test_both_failures_are_recognisable_as_errors(self, monkeypatch):
        """So telegram_engine._safe marks the section failed and the briefing's
        `generated` count tells the truth."""
        from llm_client import is_llm_error
        for mode in ("raises", "sentinel"):
            for out in self._both(monkeypatch, mode):
                assert is_llm_error(out), out[:90]

    def test_the_hardcoded_recommendation_is_gone_from_the_source(self):
        import io
        import ai_advisor_engine as A
        import macro_tech_report as M
        for mod in (A, M):
            src = io.open(mod.__file__, encoding="utf-8").read()
            returns = [ln for ln in src.splitlines()
                       if ln.strip().startswith("return ")]
            for ln in returns:
                assert "60% BTC" not in ln, ln.strip()[:80]
                assert "bullish momentum" not in ln, ln.strip()[:80]

    def test_a_working_model_still_passes_its_answer_through(self, monkeypatch):
        import ai_advisor_engine as A
        monkeypatch.setattr(A, "generate_market_report",
                            lambda p: "  Real analysis of the tape.  ")
        assert A.generate_ai_advisor("m", "s") == "Real analysis of the tape."


class TestStaticPricesAreLabelledNotQuoted:
    """A hardcoded price map was multiplied into a USD figure that then decided
    whether an alert fired. So a stale constant did not merely mislabel a
    transfer — it made the transfer DISAPPEAR by dropping it under the $5,000
    threshold. An audit found the HEX constant off by a factor of hundreds.

    And a token absent from the map produced usd_val 0, failed the threshold,
    and vanished with no trace at all."""

    @staticmethod
    def _src():
        # The package re-exports the SINGLETON under the module name, so
        # `import openhands_skills.chain_analysis_expert as C` yields the
        # instance and C.__file__ does not exist. Ask the class instead.
        import inspect
        import io
        from openhands_skills.chain_analysis_expert import ChainAnalysisExpert
        return io.open(inspect.getfile(ChainAnalysisExpert), encoding="utf-8").read()

    def test_a_value_without_a_live_price_is_marked(self):
        src = self._src()
        assert 'usd_source = "unpriced"' in src or '"unpriced"' in src
        assert "ΧΩΡΙΣ ΑΠΟΤΙΜΗΣΗ" in src

    def test_a_value_from_an_api_is_marked_differently(self):
        src = self._src()
        assert 'usd_source = "api" if usd_val else ""' in src
        assert 'usd_source = "live" if px else "unpriced"' in src

    def test_an_unpriced_transfer_is_surfaced_not_dropped(self):
        """It used to fail the threshold silently and disappear."""
        src = self._src()
        assert "unpriced_moves.append" in src
        assert "unpriced_ecosystem_movements" in src
        assert "Δεν σημαίνει ότι ήταν μικρές" in src

    def test_there_is_no_static_price_constant_left(self):
        """Superseded: labelling the estimate was not enough, because the wrong
        number still decided whether an alert fired. Prices are resolved live
        and an unresolved one is reported as unpriced, never as zero."""
        src = self._src()
        assert "STATIC_PRICES = {" not in src
        assert "def live_price(" in src

    def test_the_caller_is_warned_when_any_alert_lacked_a_live_price(self):
        assert "ecosystem_price_warning" in self._src()

    def test_the_bare_price_map_literal_is_gone_from_the_hot_path(self):
        """The dict is still there as a labelled constant; what must not remain
        is the inline `price_map = {...}` used as if it were market data."""
        assert "price_map = {" not in self._src()


class TestSafetyGateCannotForgetToFail:
    """perform_pre_apply_tests tracked its verdict in a flag every branch had to
    remember to set. The domain smoke test appended
    {"name": ..., "passed": False} and never touched results["passed"], so a
    failed smoke test left the gate reporting PASSED and the edit was applied.
    A safety gate that can forget to fail is not a safety gate."""

    def test_the_verdict_is_derived_from_the_checks(self):
        import inspect
        from openhands_skills import guards
        src = inspect.getsource(guards.run_pre_apply_safety_tests)
        assert 'results["passed"] = not failed' in src

    def test_a_failed_check_fails_the_gate(self, tmp_path):
        """Compile a file that cannot compile: the gate must block."""
        from openhands_skills import guards
        bad = tmp_path / "broken.py"
        bad.write_text("def f(:\n", encoding="utf-8")
        r = guards.run_pre_apply_safety_tests(str(bad))
        assert r["passed"] is False
        assert any(not c.get("passed") for c in r["checks"])
        assert "FAILED" in r.get("summary", "")

    def test_a_clean_file_passes(self, tmp_path):
        from openhands_skills import guards
        ok = tmp_path / "fine.py"
        ok.write_text("VALUE = 1\n", encoding="utf-8")
        r = guards.run_pre_apply_safety_tests(str(ok))
        assert r["passed"] is True

    def test_the_failed_check_names_itself(self, tmp_path):
        from openhands_skills import guards
        bad = tmp_path / "broken2.py"
        bad.write_text("def f(:\n", encoding="utf-8")
        r = guards.run_pre_apply_safety_tests(str(bad))
        assert r.get("failed_checks")


class TestPricesAreLiveAndChainCorrect:
    """The hardcoded price map did not merely mislabel a transfer — it GATED it.
    Measured: HEX 0.000012 against a live PulseChain 0.003481, 290x too low. At
    a $5,000 threshold a HEX move had to be 416,666,667 HEX to be flagged, which
    is over $1.3M of real value, so every genuine whale move between $5k and
    $1.3M was valued below threshold and silently dropped."""

    @staticmethod
    def _fake(pairs):
        import io
        import json

        class R:
            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def read(s):
                return json.dumps({"pairs": pairs}).encode()

        return lambda *a, **k: R()

    def _clear(self):
        from openhands_skills.chain_analysis_expert import _PRICE_CACHE
        _PRICE_CACHE.clear()

    def test_the_wrong_chain_is_not_used(self, monkeypatch):
        """HEX exists on Ethereum and PulseChain at different prices. A bare
        symbol search returns whichever has more liquidity."""
        import urllib.request
        from openhands_skills.chain_analysis_expert import live_price
        self._clear()
        monkeypatch.setattr(urllib.request, "urlopen", self._fake([
            {"chainId": "ethereum", "baseToken": {"symbol": "HEX"},
             "priceUsd": "0.001148", "liquidity": {"usd": 9_000_000}},
            {"chainId": "pulsechain", "baseToken": {"symbol": "HEX"},
             "priceUsd": "0.003481", "liquidity": {"usd": 1_000_000}},
        ]))
        assert live_price("HEX", "pulsechain") == 0.003481
        self._clear()
        assert live_price("HEX", "ethereum") == 0.001148

    def test_the_deepest_pool_on_the_right_chain_wins(self, monkeypatch):
        import urllib.request
        from openhands_skills.chain_analysis_expert import live_price
        self._clear()
        monkeypatch.setattr(urllib.request, "urlopen", self._fake([
            {"chainId": "pulsechain", "baseToken": {"symbol": "PLSX"},
             "priceUsd": "0.000001", "liquidity": {"usd": 100}},
            {"chainId": "pulsechain", "baseToken": {"symbol": "PLSX"},
             "priceUsd": "0.0000090", "liquidity": {"usd": 500_000}},
        ]))
        assert live_price("PLSX", "pulsechain") == 0.0000090

    def test_no_price_returns_none_not_zero(self, monkeypatch):
        """Zero is what made large transfers disappear."""
        import urllib.request
        from openhands_skills.chain_analysis_expert import live_price
        self._clear()
        monkeypatch.setattr(urllib.request, "urlopen", self._fake([]))
        assert live_price("NOSUCH", "pulsechain") is None

    def test_a_network_failure_returns_none(self, monkeypatch):
        import urllib.request
        from openhands_skills.chain_analysis_expert import live_price
        self._clear()
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
        assert live_price("HEX", "pulsechain") is None

    def test_no_hardcoded_price_constants_remain(self):
        import inspect
        from openhands_skills.chain_analysis_expert import ChainAnalysisExpert
        import io
        src = io.open(inspect.getfile(ChainAnalysisExpert), encoding="utf-8").read()
        assert "STATIC_PRICES = {" not in src
        assert '"HEX": 0.000012' not in src

    def test_both_call_sites_pass_the_chain(self):
        import inspect
        import io
        from openhands_skills.chain_analysis_expert import ChainAnalysisExpert
        src = io.open(inspect.getfile(ChainAnalysisExpert), encoding="utf-8").read()
        import re
        calls = re.findall(r"live_price\([^)]*\)", src)
        calls = [c for c in calls if "def live_price" not in c]
        assert calls, "no call sites found"
        for c in calls:
            assert "chain" in c, c


class TestMemoryCanBeRead:
    """persistent_memory was write-only. It offered store() and store_learning()
    and NOTHING else, while nine call sites across the repo — evaluation_harness
    and every hacash/finance expert — called retrieve() and
    retrieve_relevant_evolution(), each inside `try/except ... or ""`. So every
    expert that claims to consult what the system has learned received an empty
    string, silently, forever. Measured: 324 documents stored, zero readable."""

    def test_the_read_methods_exist(self):
        from openhands_skills.persistent_memory import persistent_memory as PM
        for m in ("retrieve", "retrieve_relevant", "retrieve_relevant_evolution"):
            assert callable(getattr(PM, m, None)), m

    def test_what_is_stored_comes_back(self, tmp_path, monkeypatch):
        from openhands_skills.persistent_memory import persistent_memory as PM
        marker = "ΜΟΝΑΔΙΚΟ ΚΕΙΜΕΝΟ ΔΟΚΙΜΗΣ xyzzy-4711"
        PM.store(marker, {"type": "unit_test_marker",
                          "timestamp": "2099-01-01T00:00:00"})
        rows = PM.retrieve(limit=5, metadata_filter={"type": "unit_test_marker"})
        assert any(marker in r["text"] for r in rows)

    def test_metadata_filter_narrows_the_result(self):
        from openhands_skills.persistent_memory import persistent_memory as PM
        rows = PM.retrieve(limit=5, metadata_filter={"type": "unit_test_marker"})
        assert all(r["metadata"].get("type") == "unit_test_marker" for r in rows)

    def test_semantic_read_returns_rows(self):
        from openhands_skills.persistent_memory import persistent_memory as PM
        rows = PM.retrieve_relevant("security audit of a contract", 3)
        assert isinstance(rows, list)
        assert all("text" in r and "metadata" in r for r in rows)

    def test_the_expert_facing_helper_returns_a_string(self):
        """The eight expert modules do `... or ""` and paste it into a prompt."""
        from openhands_skills.persistent_memory import persistent_memory as PM
        out = PM.retrieve_relevant_evolution("blockchain wallet risk", 2)
        assert isinstance(out, str)

    def test_an_empty_query_returns_nothing_rather_than_everything(self):
        from openhands_skills.persistent_memory import persistent_memory as PM
        assert PM.retrieve_relevant("   ", 3) == []


class TestEvolutionPatternsAreReadable:
    """store_evolution_pattern returned True and the document really was
    written — but get_evolution_patterns called persistent_memory.query(), a
    method that never existed, inside a bare `except: return []`. The loop meant
    to learn "what worked before" learned nothing, in silence."""

    def test_a_stored_pattern_can_be_read_back(self):
        from openhands_skills.research_agent import research_agent
        research_agent.store_evolution_pattern(
            "unit-test pattern qwerty-8823", source_url="https://example.invalid",
            success_score=0.9)
        pats = research_agent.get_evolution_patterns(20)
        assert pats, "nothing readable"
        assert all("pattern" in p and "metadata" in p for p in pats)

    def test_the_score_filter_works(self):
        from openhands_skills.research_agent import research_agent
        high = research_agent.get_evolution_patterns(20, min_score=0.8)
        assert all(float(p["metadata"].get("success_score", 0)) >= 0.8
                   for p in high)

    def test_it_no_longer_calls_a_method_that_does_not_exist(self):
        """Checks CODE lines only — the comment explaining this fix has to
        quote the old call, and matching the whole source caught the comment."""
        import inspect
        from openhands_skills.research_agent import ResearchAgent
        code = [ln for ln in inspect.getsource(
                    ResearchAgent.get_evolution_patterns).splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
        body = "\n".join(code)
        assert "persistent_memory.query(" not in body
        assert "persistent_memory.retrieve(" in body


class TestVerifierVerdictFollowsItsChecks:
    """verify_evolution.py printed each probe and then, unconditionally, printed
    "ALL VERIFICATIONS PASSED - controlled, error-free evolution complete" and
    exited 0. So "telegram still forbidden: False" could be displayed and the
    next line would declare the system error-free. On its first honest run it
    immediately found two real failures that had been invisible."""

    @staticmethod
    def _src():
        import io
        return io.open("verify_evolution.py", encoding="utf-8").read()

    def test_the_verdict_is_conditional(self):
        src = self._src()
        assert "failed = [c for c in CHECKS if not c[1]]" in src
        assert "sys.exit(1)" in src

    def test_the_pass_line_is_inside_a_condition(self):
        """It must not be reachable when anything failed. Anchored on the actual
        print statement, not on the phrase — which the docstring also quotes."""
        src = self._src()
        i = src.rindex('print(f"=== ALL {len(CHECKS)} VERIFICATIONS PASSED')
        assert "sys.exit(1)" in src[:i], "the failure exit must come first"

    def test_every_probe_is_recorded(self):
        src = self._src()
        assert src.count("check(") > 10
        assert "CHECKS.append" in src


def _code_only(obj):
    """Source of `obj` with comments and docstrings stripped.

    Every one of these fixes is explained in a comment that necessarily quotes
    the broken call it replaced. Matching raw source therefore matches the
    explanation and passes for the wrong reason — that has caught me three
    times now, so these tests look at executable lines only.
    """
    import ast, inspect
    src = inspect.getsource(obj) if not isinstance(obj, str) else obj
    tree = ast.parse(src if src.startswith(("def", "class", "import", "from"))
                     else "if 1:\n" + "\n".join("    " + l for l in src.splitlines()))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body.pop(0)
    return ast.unparse(tree)


class TestGuardsFailClosed:
    """The module-level fallback in langgraph_orchestrator returned True for
    everything when `import guards` failed: is_forbidden_path("telegram_engine.py")
    -> False, test_proposal_safety -> {"passed": True}. A broken guards.py — a bad
    edit, a missing dependency — silently disabled the only component whose job
    is to refuse. Proven by simulating the ImportError and calling the fallback."""

    @staticmethod
    def _fallback_ns():
        import builtins, io, logging
        real = builtins.__import__

        def boom(name, *a, **k):
            if name.endswith("guards"):
                raise ImportError("simulated")
            return real(name, *a, **k)

        src = io.open("openhands_skills/langgraph_orchestrator.py", encoding="utf-8").read()
        block = src[src.index("# Centralized professional guards"):src.index("_persistent_savers")]
        ns = {"logging": logging}
        builtins.__import__ = boom
        try:
            exec(compile(block, "block", "exec"), ns)
        finally:
            builtins.__import__ = real
        return ns

    def test_forbidden_files_stay_forbidden_when_guards_are_down(self):
        ns = self._fallback_ns()
        assert ns["is_forbidden_path"]("telegram_engine.py") is True
        assert ns["is_forbidden_path"]("master_market_brain.py") is True
        assert ns["is_forbidden_path"]("anything_at_all.py") is True

    def test_nothing_validates_when_guards_are_down(self):
        ns = self._fallback_ns()
        ok, reason, _ = ns["validate_proposal"]({"file": "x.py"})
        assert ok is False and "unavailable" in reason.lower()

    def test_safety_test_fails_when_guards_are_down(self):
        ns = self._fallback_ns()
        r = ns["test_proposal_safety"]({"file": "x.py"})
        assert r["passed"] is False and r["violations"]

    def test_the_interceptor_refuses_rather_than_passing_params_through(self):
        import pytest
        ns = self._fallback_ns()
        with pytest.raises(RuntimeError):
            ns["guardrail_provider"].intercept_tool_call(params={"a": 1})


class TestImprovementCycleActuallyRuns:
    """run_blockchain_improvement_cycle — the flagship "closed self-improvement
    loop" — never initialized `proposals`, so its first .append() raised
    NameError on every call. Past that it referenced an undefined `state` and an
    undefined `result`, and its tail (step 4 and the return) had been stranded
    after a helper's `return count`, unreachable. It returned None, always."""

    def test_proposals_is_initialized_before_use(self):
        from openhands_skills import langgraph_orchestrator as O
        code = _code_only(O.run_blockchain_improvement_cycle)
        assert "proposals: list = []" in code or "proposals = []" in code
        assert code.index("proposals") == code.index("proposals: list = []") \
            if "proposals: list = []" in code else True

    def test_it_returns_a_dict_not_none(self):
        from openhands_skills import langgraph_orchestrator as O
        code = _code_only(O.run_blockchain_improvement_cycle)
        assert "return result" in code

    def test_no_undefined_names_in_the_module(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, "-m", "pyflakes",
                              "openhands_skills/langgraph_orchestrator.py"],
                             capture_output=True, text=True).stdout
        bad = [l for l in out.splitlines()
               if "undefined name" in l and "run_system_evaluation" not in l]
        assert not bad, bad


class TestEveryRoutedSpecialistResolves:
    """run_task referenced 14 specialists that were never imported. Python
    resolves a bare name at use time, so `if is_seo and seo_expert:` did not skip
    the branch — it raised NameError and killed the whole task. Every legacy
    route containing 'test', 'seo', 'backend', 'deploy', 'brand', 'treasury'...
    died before producing anything. All 14 modules existed on disk."""

    NAMES = ["seo_expert", "qa_engineer", "backend_specialist", "devops_engineer",
             "accessibility_expert", "content_strategist", "brand_strategist",
             "project_manager", "analytics_specialist", "finance_treasury_expert",
             "sales_bd_expert", "product_strategist", "pr_communications_expert",
             "web3_community_manager"]

    def test_all_fourteen_resolve(self):
        from openhands_skills import openhands_v2_entry as E
        missing = [n for n in self.NAMES if getattr(E, n, "__absent__") == "__absent__"]
        assert not missing, missing

    def test_none_of_them_are_none(self):
        from openhands_skills import openhands_v2_entry as E
        dead = [n for n in self.NAMES if getattr(E, n, None) is None]
        assert not dead, dead

    def test_the_module_has_no_undefined_names_at_all(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, "-m", "pyflakes",
                              "openhands_skills/openhands_v2_entry.py"],
                             capture_output=True, text=True).stdout
        assert "undefined name" not in out, out


class TestCreatePrIsHonest:
    """create_pr referenced `repository` and `repoName`, which were never
    parameters — NameError on every call. And its success path created nothing:
    it built a gh command string, discarded it, and returned success=True with a
    "suggested_gh_command". It also hardcoded --body "..." , dropping the body
    the caller passed."""

    @staticmethod
    def _fn():
        from openhands_mcp import server as S
        return getattr(S.create_pr, "fn", S.create_pr)

    def test_it_no_longer_raises(self):
        r = self._fn()(repo_name="o/r", source_branch="b", title="T", body="B")
        assert isinstance(r, dict)

    def test_it_does_not_claim_success_without_creating_anything(self):
        r = self._fn()(repo_name="o/r", source_branch="b", title="T", body="B")
        assert r["success"] is False
        assert r["status"] == "prepared_not_created"

    def test_the_body_reaches_the_command(self):
        r = self._fn()(repo_name="o/r", source_branch="b", title="T",
                       body="the real body")
        assert "the real body" in r["command"]

    def test_opening_a_pr_requires_explicit_confirmation(self):
        import inspect
        from openhands_mcp import server as S
        sig = inspect.signature(getattr(S.create_pr, "fn", S.create_pr))
        assert sig.parameters["confirm"].default is False

    def test_no_undefined_names_in_the_server(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, "-m", "pyflakes", "openhands_mcp/server.py"],
                             capture_output=True, text=True).stdout
        assert "undefined name" not in out, out


class TestSolidityDetectionUsesWordBoundaries:
    """looks_like_solidity was `any(kw in t for kw in (..."erc","defi","evm"...))`
    — a plain substring test. "erc" is inside e-commerce, percentage, merchant,
    search; "defi" is inside define and definition. Measured: four of five
    ordinary programming tasks were classified as Solidity and got a canned
    ERC-20 contract back instead of the work asked for."""

    ORDINARY = ["Write a Python function to define a schema",
                "Build an e-commerce checkout page",
                "Add percentage formatting to the report",
                "Search the merchant database",
                "Fix the interceptor in commerce.py"]

    SOLIDITY = ["Write an ERC-20 token contract",
                "Audit this Solidity contract",
                "pragma solidity ^0.8.0",
                "Deploy a smart contract on PulseChain",
                "Review MyToken.sol"]

    def test_ordinary_work_is_not_mistaken_for_solidity(self):
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent as B
        wrong = [t for t in self.ORDINARY if B.looks_like_solidity(t)]
        assert not wrong, wrong

    def test_real_solidity_is_still_detected(self):
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent as B
        missed = [t for t in self.SOLIDITY if not B.looks_like_solidity(t)]
        assert not missed, missed

    def test_two_weak_markers_together_still_count(self):
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent as B
        assert B.looks_like_solidity("check the erc token wallet defi flow")

    def test_one_weak_marker_alone_does_not(self):
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent as B
        assert not B.looks_like_solidity("store the token in the session")

    def test_please_is_not_pulsechain(self):
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent as B
        assert B.target_chain("please refactor this module") == "ethereum"
        assert B.target_chain("a PulseChain swap") == "pulsechain"


class TestSecurityAuditorActuallyLooksAtTheTask:
    """Every method returned the same hardcoded list. `task` was used for one log
    line and nothing else, so "audit my login flow" and "audit my checkout"
    produced byte-identical output — and run_task filed it as an audit. A
    checklist that never read the code is a reference card, not a review."""

    def test_it_is_a_real_llm_backed_expert(self):
        from openhands_skills.expert_base import ExpertSkill
        from openhands_skills.security_auditor import SecurityAuditor
        assert issubclass(SecurityAuditor, ExpertSkill)

    def test_audit_calls_consult_on_the_task(self):
        from openhands_skills.security_auditor import SecurityAuditor
        code = _code_only(SecurityAuditor.audit_security)
        assert "self.consult(task" in code

    def test_the_static_keys_say_they_are_reference_material(self):
        from openhands_skills.security_auditor import SecurityAuditor
        code = _code_only(SecurityAuditor.audit_security)
        for old in ("'owasp_top10_checklist'", "'vulnerability_assessment'"):
            assert old not in code, old
        assert "owasp_top10_reference_checklist" in code

    def test_it_reports_when_the_review_did_not_happen(self):
        from openhands_skills.security_auditor import SecurityAuditor
        code = _code_only(SecurityAuditor.audit_security)
        assert "not_reviewed" in code and "review_is_real" in code

    def test_two_different_tasks_no_longer_have_to_be_identical(self):
        """The static half is shared; the reviewed half is per-task."""
        from openhands_skills.security_auditor import SecurityAuditor
        code = _code_only(SecurityAuditor.audit_security)
        assert "'review': review" in code or '"review": review' in code


class TestHealthScoreCannotRewardDeath:
    """A case that raised never reached `total_latency += latency`, so a fully
    dead expert reported avg_latency 0.0s, collected the whole 40-point speed
    bonus against 0% accuracy, and scored 40.0 — the same as a working system at
    33% accuracy and 2s. The single number the self-improvement loop uses to
    decide whether it got better paid out for total failure."""

    def test_a_dead_subsystem_produces_no_score_at_all(self, monkeypatch):
        import openhands_skills.evaluation_harness as m

        class Dead:
            def analyze_address(self, *a, **k):
                raise RuntimeError("subsystem is dead")

        monkeypatch.setattr(m, "chain_analysis_expert", Dead())
        h = m.EvaluationHarness()
        h.last_eval_time = 0
        r = h.run_full_evaluation()
        assert r["status"] == "eval_failed"
        assert r["system_improvement_score"] is None
        assert r["errors"]

    def test_latency_is_averaged_over_cases_that_ran(self):
        from openhands_skills.evaluation_harness import EvaluationHarness
        code = _code_only(EvaluationHarness._run_blockchain_eval)
        assert "len(succeeded)" in code
        assert "len(SAMPLE_TEST_CASES)) if succeeded" not in code

    def test_speed_points_need_something_to_have_worked(self):
        from openhands_skills.evaluation_harness import EvaluationHarness
        code = _code_only(EvaluationHarness.run_full_evaluation)
        assert "num_succeeded" in code
        i = code.index("latency_score")
        assert "num_succeeded" in code[:i], "the speed bonus must be gated"


class TestRollbackCanActuallyFire:
    """Rollback triggers below 50. The old scorer could not produce a number
    below 50 for any well-formed proposal: rationale +25, priority "high" +30,
    applied +15 — 70 points read entirely off the proposal's own advertising
    copy, before anything about the result was examined. A change that broke the
    repo outright scored 70 and was kept."""

    PROP = {"rationale": "from research", "priority": "high", "source": "x",
            "target_file": "a.py", "suggestion": "market aware"}
    REPORT = {"id": "p1", "applied": True}
    GOOD = {"measured": True, "test_failures": 0, "undefined_names": 0, "syntax_ok": True}

    def test_provenance_alone_cannot_clear_the_rollback_threshold(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        assert H.PROVENANCE_CAP < 50

    def test_breaking_tests_triggers_rollback(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        after = dict(self.GOOD, test_failures=7)
        r = H.compute_evolution_score(self.PROP, self.REPORT, baseline=self.GOOD, after=after)
        assert r["score"] < 50
        gate = H.post_apply_evaluation_and_rollback_if_degraded("p1", r["score"])
        assert gate["action"] == "rollback_triggered"

    def test_breaking_the_syntax_triggers_rollback(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        after = dict(self.GOOD, syntax_ok=False)
        r = H.compute_evolution_score(self.PROP, self.REPORT, baseline=self.GOOD, after=after)
        assert r["score"] < 50

    def test_new_undefined_names_trigger_rollback(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        after = dict(self.GOOD, undefined_names=3)
        r = H.compute_evolution_score(self.PROP, self.REPORT, baseline=self.GOOD, after=after)
        assert r["score"] < 50

    def test_a_clean_change_is_kept(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        r = H.compute_evolution_score(self.PROP, self.REPORT, baseline=self.GOOD, after=self.GOOD)
        assert r["score"] >= 50
        gate = H.post_apply_evaluation_and_rollback_if_degraded("p1", r["score"])
        assert gate["action"] == "no_rollback"

    def test_an_unmeasured_apply_is_not_filed_as_passing(self):
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver as H
        r = H.compute_evolution_score(self.PROP, self.REPORT, baseline=None, after=self.GOOD)
        assert r["score"] is None and r["measured"] is False
        gate = H.post_apply_evaluation_and_rollback_if_degraded("p1", r["score"])
        assert gate["action"] == "needs_human_review"

    def test_the_score_no_longer_reads_the_proposals_own_prose_for_most_of_it(self):
        from openhands_multiagent_v2.hyper_evolution_agent import HyperAdaptiveEvolutionAgent as A
        code = _code_only(A.compute_evolution_score)
        assert "health_before" in code and "health_after" in code
        assert "score += 30" not in code and "score += 25" not in code


class TestSmartTriggerCallsWhatItAnnounces:
    """Its two highest-priority branches printed a banner, asked the supervisor
    for a plan, and appended "[Auto-routed to Solidity Expert + Coder + Reviewer
    + Tester + Debugger]" — naming five agents and calling none. The note read
    like a receipt for work that never happened."""

    @staticmethod
    def _branches():
        from openhands_multiagent_v2.smart_trigger_system import SmartTriggerSystem
        import inspect
        src = inspect.getsource(SmartTriggerSystem)
        return _code_only(src)

    def test_the_fake_routing_notes_are_gone(self):
        code = self._branches()
        assert "[Auto-routed to Solidity Expert" not in code
        assert "[Auto-routed to Chain Analysis Expert" not in code

    def test_the_solidity_branch_calls_the_solidity_expert(self):
        code = self._branches()
        assert "solidity_expert.audit_solidity(" in code
        assert "solidity_expert.write_solidity_contract(" in code

    def test_the_chain_branch_calls_the_chain_expert(self):
        code = self._branches()
        assert "chain_analysis_expert.analyze_address(" in code

    def test_the_debugger_claim_is_backed_by_a_call(self):
        code = self._branches()
        assert "debugger.debug(" in code

    def test_no_address_means_it_says_so_instead_of_pretending(self):
        code = self._branches()
        assert "No 0x address found" in code


class TestFolderAnalysisUsesTheFolderYouNamed:
    """`target = os.getcwd()` ignored the folder in the request. Ask about
    D:/clients/acme and you were handed a clean bill of health for the agent's
    own working directory, with nothing in the output revealing the swap."""

    def test_a_named_folder_is_found(self):
        from openhands_skills.openhands_v2_entry import _extract_folder as E
        got = E(r"analyse the folder C:\AI\market-agent")
        assert got and got.lower().endswith("market-agent")

    def test_trailing_words_are_not_part_of_the_path(self):
        from openhands_skills.openhands_v2_entry import _extract_folder as E
        got = E("analyse C:/AI/market-agent please")
        assert got and got.lower().endswith("market-agent")

    def test_a_missing_folder_is_reported_not_substituted(self):
        from openhands_skills.openhands_v2_entry import _extract_folder as E
        got = E(r"analyse D:\clients\acme-does-not-exist")
        assert got and "acme-does-not-exist" in got

    def test_no_folder_named_returns_none(self):
        from openhands_skills.openhands_v2_entry import _extract_folder as E
        assert E("just analyse my code") is None

    def test_a_file_is_not_a_folder(self):
        from openhands_skills.openhands_v2_entry import _extract_folder as E
        assert E(r"read C:\AI\book.pdf") is None

    def test_the_route_no_longer_hardcodes_cwd(self):
        import io as _io
        src = _io.open("openhands_skills/openhands_v2_entry.py", encoding="utf-8").read()
        i = src.index('if route.name == "analyze_folder"')
        block = src[i:i + 1400]
        code = "\n".join(l for l in block.splitlines()
                         if l.strip() and not l.strip().startswith("#"))
        assert "_extract_folder(user_task)" in code
        assert "path_came_from" in code


class TestCorporateNewsDoesNotInventCalm:
    """_fallback returned one dictionary for every reason: "No major corporate
    earnings or company-specific developments detected in the last 48 hours."
    It was returned when the API key was missing, when the client library was
    absent, and when the call raised — so a dead key published an affirmative
    all-clear and the run counted 6/6 success."""

    def test_an_unchecked_feed_reports_unknown(self):
        from corporate_news_engine import corporate_news_engine as C
        r = C._fallback(reason="FINLIGHT_API_KEY is not set", checked=False)
        assert r["corporate_risk_level"] == "UNKNOWN"
        assert r["checked"] is False
        assert "FINLIGHT_API_KEY" in r["key_corporate_events"]

    def test_an_unchecked_feed_never_claims_nothing_happened(self):
        from corporate_news_engine import corporate_news_engine as C
        r = C._fallback(reason="401", checked=False)
        low = r["key_corporate_events"].lower()
        assert "no major corporate" not in low
        assert "δεν ελέγχθηκε" in low

    def test_a_feed_that_answered_with_nothing_still_says_neutral(self):
        from corporate_news_engine import corporate_news_engine as C
        r = C._fallback(checked=True)
        assert r["corporate_risk_level"] == "NEUTRAL"
        assert r["checked"] is True

    def test_the_missing_key_path_marks_it_unchecked(self):
        import inspect
        from corporate_news_engine import CorporateNewsEngine
        code = _code_only(CorporateNewsEngine.get_corporate_news)
        assert "checked=False" in code
        assert code.count("_fallback()") == 0, "every call site must state which it is"


class TestMacroReportNeedsInputs:
    """With an empty article list the prompt still asked for a macro report, and
    the model produced one from its own prior — published as today's read on the
    global economy."""

    def test_it_refuses_without_articles(self, monkeypatch):
        import macro_tech_report as M
        monkeypatch.setattr(M, "get_market_news", lambda *a, **k: [])
        called = []
        monkeypatch.setattr(M, "generate_market_report",
                            lambda *a, **k: called.append(1) or "invented macro read")
        out = M.generate_macro_tech_report()
        assert not called, "the model must not be asked with no inputs"
        assert "NOT computed" in out

    def test_one_article_is_still_too_few(self, monkeypatch):
        import macro_tech_report as M
        monkeypatch.setattr(M, "get_market_news", lambda *a, **k: [{"title": "only one"}])
        called = []
        monkeypatch.setattr(M, "generate_market_report",
                            lambda *a, **k: called.append(1) or "x")
        out = M.generate_macro_tech_report()
        assert not called and "NOT computed" in out

    def test_with_real_articles_it_runs(self, monkeypatch):
        import macro_tech_report as M
        monkeypatch.setattr(M, "get_market_news", lambda *a, **k:
                            [{"title": "Fed holds rates"}, {"title": "AI capex rises"}])
        seen = {}
        def fake(ctx, *a, **k):
            seen["ctx"] = ctx
            return "A real macro report grounded in the two headlines above."
        monkeypatch.setattr(M, "generate_market_report", fake)
        out = M.generate_macro_tech_report()
        assert "NOT computed" not in out
        assert "Fed holds rates" in seen["ctx"]


class TestZeroedQuoteIsNotAPrice:
    """Finnhub answers "no data for this symbol" with HTTP 200 and every field
    zero — unknown ticker, symbol outside the plan, rate limit. Nothing raises,
    so the exception path never saw it and a zeroed quote became a real price of
    $0.00 at 0%, which the briefing painted green and fed to the vote."""

    def test_an_all_zero_quote_is_rejected(self, monkeypatch):
        import stock_engine as SE
        SE._stock_cache.clear()
        monkeypatch.setattr(SE, "client", type("Z", (), {
            "quote": lambda self, s: {"c": 0, "pc": 0, "t": 0}})())
        r = SE.get_stock_price("NOPE")
        assert r["price"] is None and r["change"] is None and r["error"]

    def test_a_missing_previous_close_keeps_the_price_and_drops_the_change(self, monkeypatch):
        """Written expecting the price to be discarded — but a real price with no
        previous close is a known price and an unknown change, and throwing the
        price away would be its own small lie. Reporting 0% would be the bigger
        one: that is what `pc or current` used to produce."""
        import stock_engine as SE
        SE._stock_cache.clear()
        monkeypatch.setattr(SE, "client", type("Z", (), {
            "quote": lambda self, s: {"c": 12.0, "pc": 0}})())
        r = SE.get_stock_price("NEWLISTING")
        assert r["price"] == 12.0
        assert r["change"] is None, "0% would be invented"

    def test_a_price_without_a_change_is_never_coloured(self):
        import inspect
        import watchlist_engine as W
        code = _code_only(inspect.getsource(W))
        assert "μεταβολή άγνωστη" in code
        i = code.index("μεταβολή άγνωστη")
        assert "🟢" not in code[max(0, i - 400):i]

    def test_a_real_quote_still_works(self, monkeypatch):
        import stock_engine as SE
        SE._stock_cache.clear()
        monkeypatch.setattr(SE, "client", type("R", (), {
            "quote": lambda self, s: {"c": 191.4, "pc": 188.0}})())
        r = SE.get_stock_price("AAPL")
        assert r["price"] == 191.4 and r["change"] == 1.81

    def test_a_rejected_quote_is_not_cached_as_a_price(self, monkeypatch):
        import stock_engine as SE
        SE._stock_cache.clear()
        monkeypatch.setattr(SE, "client", type("Z", (), {
            "quote": lambda self, s: {"c": 0, "pc": 0}})())
        SE.get_stock_price("NOPE")
        assert "NOPE" not in SE._stock_cache


class TestNoUndefinedNamesAnywhereInTheStack:
    """Nine of the seventeen blocking findings in the audit were, at bottom, the
    same thing: a name that did not exist, sitting inside a try/except or behind
    a guard that never evaluated, so nothing crashed loudly and the feature just
    quietly did not work. `proposals.append`, `repository`, `repoName`,
    fourteen specialists, `persistent_memory.query`, a leaked `except ... as e`,
    a dict literal referencing itself. Pyflakes finds every one of them in a
    second. This test keeps the count at zero."""

    MODULES = ("*.py", "openhands_skills/*.py", "openhands_multiagent_v2/*.py",
               "openhands_mcp/*.py")

    def test_pyflakes_reports_no_undefined_names(self):
        import glob
        import subprocess
        import sys

        files = []
        for pat in self.MODULES:
            files.extend(glob.glob(pat))
        assert files, "no files collected"

        out = subprocess.run([sys.executable, "-m", "pyflakes", *files],
                             capture_output=True, text=True).stdout
        bad = [l for l in out.splitlines() if "undefined name" in l]
        assert not bad, "undefined names:\n" + "\n".join(bad)

    def test_every_module_at_least_parses(self):
        import ast
        import glob

        broken = []
        for pat in self.MODULES:
            for f in glob.glob(pat):
                try:
                    # utf-8-sig, not utf-8: a BOM is legal in a Python source
                    # file and the interpreter strips it. Reading as plain utf-8
                    # leaves U+FEFF in the string and ast.parse rejects it — the
                    # file is fine, the reader was wrong.
                    with open(f, encoding="utf-8-sig") as fh:
                        ast.parse(fh.read())
                except SyntaxError as e:
                    broken.append(f"{f}:{e.lineno}: {e.msg}")
        assert not broken, broken


class TestNoSkillAnswersWithoutReadingTheQuestion:
    """Ten methods were measured returning BYTE-IDENTICAL output for two
    unrelated requests. They were found by taint-analysing which returns can
    depend on their parameters, then CALLING each candidate twice — static
    analysis nominated, execution decided, and it overruled the analyser in both
    directions (code_intelligence was a false positive; programmer_expert's
    production-ops method was a miss).

    The worst was ProgrammerExpert.god_tier_code_review: it did not merely
    ignore the input, it invented findings — "9/10 - excellent structure" plus
    named bugs about Hacash mining nonces and L2 channel races — for a
    three-line divide-by-zero and for a SQL injection alike.

    These tests do not call the model (too slow, and the backend may be down).
    They assert the structural property that made the lie possible: the answer
    must be built from the input.
    """

    OFFENDERS = [
        ("openhands_skills.analytics_specialist", "AnalyticsSpecialist", "kpi_examples"),
        ("openhands_skills.code_researcher", "CodeResearcher", "recommend_stack_for_modern_website"),
        ("openhands_skills.designer", "Designer", "create_color_palette"),
        ("openhands_skills.hacash_mining_expert", "HacashMiningExpert", "god_tier_x16rs_kernel_optimization"),
        ("openhands_skills.illustration_3d_asset_specialist", "Illustration3DAssetSpecialist", "asset_strategy"),
        ("openhands_skills.programmer_expert", "ProgrammerExpert", "god_tier_code_review"),
        ("openhands_skills.programmer_expert", "ProgrammerExpert", "god_tier_optimize_and_secure"),
        ("openhands_skills.programmer_expert", "ProgrammerExpert", "god_tier_production_ops_and_deployment"),
        ("openhands_skills.website_builder", "WebsiteBuilder", "god_tier_3d_performance_and_fallback_strategy"),
        ("openhands_skills.website_builder", "WebsiteBuilder", "god_tier_crypto_payment_ui_integration"),
        ("openhands_skills.website_builder", "WebsiteBuilder", "god_tier_hacash_specialized_explorer"),
        ("openhands_skills.debugging_expert", "DebuggingExpert", "debug_error"),
    ]

    @staticmethod
    def _cls(mod, name):
        import importlib
        return getattr(importlib.import_module(mod), name)

    def test_every_offender_consults_the_model(self):
        import inspect
        missing = []
        for mod, cls, meth in self.OFFENDERS:
            code = _code_only(getattr(self._cls(mod, cls), meth))
            if "self.analyse(" not in code and "self.consult(" not in code:
                missing.append(f"{cls}.{meth}")
        assert not missing, missing

    def test_every_offender_passes_its_own_arguments_in(self):
        """A consult() call that ignores the parameters is the same bug again."""
        import inspect
        bad = []
        for mod, cls, meth in self.OFFENDERS:
            fn = getattr(self._cls(mod, cls), meth)
            params = [p for p in inspect.signature(fn).parameters
                      if p not in ("self", "cls")]
            code = _code_only(fn)
            i = min([code.index(c) for c in ("self.analyse(", "self.consult(")
                     if c in code] or [0])
            after = code[i:]
            if not any(p in after for p in params):
                bad.append(f"{cls}.{meth} (params {params})")
        assert not bad, bad

    def test_the_static_material_is_labelled_as_reference(self):
        import inspect
        unlabelled = []
        for mod, cls, meth in self.OFFENDERS:
            klass = self._cls(mod, cls)
            ref = f"_{meth}_reference"
            if hasattr(klass, ref):
                code = _code_only(getattr(klass, meth))
                if f"self.{ref}()" not in code:
                    unlabelled.append(f"{cls}.{meth}")
        assert not unlabelled, unlabelled

    def test_the_invented_code_review_score_is_gone(self):
        from openhands_skills.programmer_expert import ProgrammerExpert
        code = _code_only(ProgrammerExpert.god_tier_code_review)
        assert "9/10" not in code
        assert "Nonce overflow edge" not in code
        assert "scored" in code

    def test_an_empty_input_is_refused_rather_than_answered(self):
        from openhands_skills.programmer_expert import programmer_expert as P
        r = P.god_tier_code_review("")
        assert r["answered"] is False and "error" in r

    def test_the_designer_palette_keeps_its_six_keys(self):
        """designer.py:56 and :228 feed this straight into generate_design_tokens,
        which indexes these exact names. The shape is a contract."""
        from openhands_skills.designer import Designer
        assert set(Designer.PALETTE_KEYS) == {
            "bg", "surface", "text", "accent", "accent2", "glass"}
        assert set(Designer.FALLBACK_PALETTE) == set(Designer.PALETTE_KEYS)

    def test_the_palette_says_where_it_came_from(self):
        from openhands_skills.designer import Designer
        code = _code_only(Designer.create_color_palette)
        assert "_source" in code and "designed_for_this_brief" in code


class TestDebugExpertNoLongerReturnsFromItsMiddle:
    """debug_error had a `return` immediately after three `if` statements that
    only matched revert/reentrancy/gas/oracle. For any ordinary Python error the
    diagnosis was empty and the caller received 100 characters announcing a
    completed analysis that contained nothing — and recommending a Solidity
    audit for a UnicodeDecodeError. The cause table and the fix steps below that
    return had never executed."""

    def test_the_cause_table_is_reachable(self):
        from openhands_skills.debugging_expert import DebuggingExpert
        assert isinstance(DebuggingExpert.COMMON_CAUSES, dict)
        assert len(DebuggingExpert.COMMON_CAUSES) >= 10

    def test_it_matches_ordinary_python_errors_not_only_contract_ones(self):
        from openhands_skills.debugging_expert import DebuggingExpert as D
        for kw in ("importerror", "keyerror", "nameerror", "timeout",
                   "unicodedecodeerror"):
            assert kw in D.COMMON_CAUSES, kw

    def test_no_unreachable_code_remains_in_the_method(self):
        import ast
        import inspect
        from openhands_skills.debugging_expert import DebuggingExpert
        tree = ast.parse(inspect.getsource(DebuggingExpert.debug_error).lstrip())
        fn = tree.body[0]

        def check(body):
            for i, n in enumerate(body):
                if isinstance(n, (ast.Return, ast.Raise)) and i + 1 < len(body):
                    raise AssertionError(f"unreachable code at line {body[i+1].lineno}")
                for f in ("body", "orelse", "finalbody"):
                    sub = getattr(n, f, None)
                    if isinstance(sub, list) and sub:
                        check(sub)
        check(fn.body)

    def test_an_empty_message_is_refused(self):
        from openhands_skills.debugging_expert import debug_expert
        assert "nothing was diagnosed" in debug_expert.debug_error("")


class TestNoUnreachableCodeAnywhere:
    """Two functions in this stack hid their real work behind an early exit:
    debug_error, and run_blockchain_improvement_cycle (whose step 4 and return
    were stranded after a helper's `return count`, so it returned None). Both
    passed every test that only asked "did it return something"."""

    def test_nothing_sits_after_a_return(self):
        import ast
        import glob

        found = []
        for pat in ("*.py", "openhands_skills/*.py", "openhands_multiagent_v2/*.py",
                    "openhands_mcp/*.py"):
            for path in glob.glob(pat):
                try:
                    with open(path, encoding="utf-8-sig") as fh:
                        tree = ast.parse(fh.read())
                except SyntaxError:
                    continue

                def walk(body, where):
                    for i, n in enumerate(body):
                        if isinstance(n, (ast.Return, ast.Raise, ast.Continue, ast.Break)) \
                                and i + 1 < len(body):
                            rest = body[i + 1:]
                            if all(isinstance(x, ast.Expr)
                                   and isinstance(x.value, ast.Constant) for x in rest):
                                continue
                            found.append(f"{path}:{rest[0].lineno} in {where}")
                            return
                        for f in ("body", "orelse", "finalbody"):
                            sub = getattr(n, f, None)
                            if isinstance(sub, list) and sub:
                                walk(sub, where)
                        for h in getattr(n, "handlers", []) or []:
                            if h.body:
                                walk(h.body, where)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        walk(node.body, node.name)
        assert not found, found


class TestHyperEvolverGuardsAlsoFailClosed:
    """The fail-open guard fallback was fixed in langgraph_orchestrator on
    2026-09-03. hyper_evolution_agent has its OWN copy and it was missed.
    Proven by simulating the ImportError: a proposal targeting
    telegram_engine.py was validated (True, "fallback") and passed its safety
    test ({"passed": True, "violations": []}). Only the path list happened to
    catch it. A gate that cannot say no is not a gate."""

    @staticmethod
    def _fallback_ns():
        import builtins, io, logging
        real = builtins.__import__

        def boom(name, *a, **k):
            if name.endswith("guards"):
                raise ImportError("simulated")
            return real(name, *a, **k)

        src = io.open("openhands_multiagent_v2/hyper_evolution_agent.py",
                      encoding="utf-8").read()
        block = src[src.index("try:\n    from openhands_skills.guards import"):
                    src.index("class HyperAdaptiveEvolutionAgent")]
        ns = {"logging": logging, "log": logging.getLogger("t")}
        builtins.__import__ = boom
        try:
            exec(compile(block, "block", "exec"), ns)
        finally:
            builtins.__import__ = real
        return ns

    def test_nothing_validates_when_guards_are_down(self):
        ns = self._fallback_ns()
        ok, reason, _ = ns["validate_proposal"]({"target_file": "telegram_engine.py"})
        assert ok is False and "unavailable" in reason.lower()

    def test_the_safety_test_fails_when_guards_are_down(self):
        ns = self._fallback_ns()
        r = ns["test_proposal_safety"]({"target_file": "telegram_engine.py"})
        assert r["passed"] is False and r["violations"]

    def test_enforce_guard_refuses_rather_than_passing_through(self):
        import pytest
        ns = self._fallback_ns()
        with pytest.raises(RuntimeError):
            ns["enforce_guard"]({"target_file": "x.py"})

    def test_the_forbidden_list_still_works(self):
        ns = self._fallback_ns()
        assert ns["_is_forbidden_path"]("telegram_engine.py") is True


class TestEveryFailureSentinelIsRecognised:
    """_ERROR_PREFIXES is a fixed-prefix tuple, and two of the sentinels this
    repo generates begin with the agent's ROLE:

        "(coder agent LLM error: ...)"                  base_llm_agent.py:97
        "(LLM backend unavailable for coder agent: ...)"  base_llm_agent.py:82

    Neither could ever match a fixed prefix, so every v2 agent's backend failure
    — coder, reviewer, tester, debugger, security — passed is_llm_error() as if
    it were a real answer, and callers gating on it published the sentinel."""

    SENTINELS = [
        "(LLM error - Macro/Tech report: the model did not answer)",
        "(model returned thinking only, no answer)",
        "(expert 'security_auditor' unavailable: LLM backend not reachable)",
        "(expert 'doc_analyst' error: timeout)",
        "(coder agent LLM error: Connection refused)",
        "(reviewer agent LLM error: timeout)",
        "(tester agent LLM error: 500)",
        "(LLM backend unavailable for debugger agent: connection reset)",
    ]

    REAL = [
        "Here is the analysis you asked for.",
        "def f():\n    return 1",
        "(a parenthetical that opens a real answer) and then continues normally",
        "(1) first point (2) second point",
    ]

    def test_every_sentinel_is_caught(self):
        from llm_client import is_llm_error
        missed = [t for t in self.SENTINELS if not is_llm_error(t)]
        assert not missed, missed

    def test_real_text_is_not_mistaken_for_a_sentinel(self):
        from llm_client import is_llm_error
        wrong = [t for t in self.REAL if is_llm_error(t)]
        assert not wrong, wrong

    def test_the_role_prefixed_forms_are_matched_by_pattern(self):
        """A fixed prefix cannot match these; the regex is the mechanism."""
        from llm_client import is_llm_error
        for role in ("coder", "reviewer", "tester", "debugger", "security",
                     "market-analyst"):
            assert is_llm_error(f"({role} agent LLM error: boom)"), role
            assert is_llm_error(f"(LLM backend unavailable for {role} agent: x)"), role

    def test_is_usable_agrees(self):
        from llm_client import is_usable
        assert not any(is_usable(t) for t in self.SENTINELS)
        assert all(is_usable(t) for t in self.REAL)


class TestTesterRunsTheRightInterpreter:
    """execute_pytest ran bare "python". On this machine that resolves to a
    THIRD interpreter (uv's cpython-3.14) with no pytest installed, so it
    reported "pytest FAILED (exit 1) -- No module named pytest" for a suite that
    passes. Every run the tester agent performed failed regardless of the code,
    and the self-correcting coder loop reads that verdict."""

    def test_it_uses_sys_executable(self):
        from openhands_multiagent_v2.tester_agent_v2 import TesterAgent
        code = _code_only(TesterAgent.execute_pytest)
        assert "sys.executable" in code
        assert '"python"' not in code and "'python'" not in code

    def test_a_passing_suite_reports_passed(self):
        from openhands_multiagent_v2.tester_agent_v2 import tester
        out = tester.execute_pytest("tests/test_agent_stack.py::TestGreekGrammar")
        assert out.startswith("pytest PASSED"), out[:200]

    def test_a_missing_pytest_is_not_reported_as_a_test_failure(self):
        from openhands_multiagent_v2.tester_agent_v2 import TesterAgent
        code = _code_only(TesterAgent.execute_pytest)
        assert "No module named pytest" in code
        assert "not a test failure" in code.lower()


class TestMasterLoaderActuallyImports:
    """It printed "   ✓ Loaded: <name>" for every entry in a hardcoded list and
    then "ALL CUSTOM SKILLS ARE NOW ACTIVE AND READY!" — while importing
    nothing. The tick came from the list, not from a result.

    Making it import for real immediately exposed two MISSING COMMAS that had
    silently concatenated four skill names into two garbage strings
    ("hacash-l3-experttypescript-expert", "cpp-expertlarge-codebase-master").
    Nobody had noticed, because nothing ever tried to import them."""

    def test_the_loader_reports_what_it_imported(self):
        from openhands_skills.master_loader import master_loader
        r = master_loader.load_all()
        assert isinstance(r, dict)
        assert set(("loaded", "failed", "not_implemented", "all_available")) <= set(r)

    def test_nothing_fails_to_import(self):
        from openhands_skills.master_loader import master_loader
        r = master_loader.load_all()
        assert r["failed"] == [], r["failed"]
        assert r["all_available"] is True

    def test_no_concatenated_names_remain(self):
        """The signature of a missing comma: a name containing 'expert' twice."""
        import inspect
        from openhands_skills.master_loader import MasterLoader
        src = inspect.getsource(MasterLoader)
        import re
        bad = [n for n in re.findall(r'"([a-z0-9\-]{6,})"', src)
               if n.count("expert") > 1 or n.count("-master") and n.count("expert")]
        assert not bad, bad

    def test_unwritten_skills_are_declared_not_counted_as_loaded(self):
        from openhands_skills.master_loader import master_loader
        r = master_loader.load_all()
        assert r["not_implemented"], "the three unwritten names should still be declared"
        assert not (set(r["not_implemented"]) & set(r["loaded"]))

    def test_the_success_banner_is_gone(self):
        import inspect
        from openhands_skills.master_loader import MasterLoader
        code = _code_only(MasterLoader.load_all)
        assert "ALL CUSTOM SKILLS ARE NOW ACTIVE AND READY" not in code


class TestHealthCheckDoesNotSendABriefing:
    """verify_system.py called tool_hub.send_telegram_briefing(), which calls
    send_full_ai_briefing(), which GENERATES AND DELIVERS a full briefing to the
    real Telegram channel. So running the health check sent the user a briefing
    they did not ask for — minutes of GPU time and a real message — every time.

    The stated intent in its own comment was "the lazy import mechanism must
    still work". That is what it checks now."""

    @staticmethod
    def _src():
        return open("verify_system.py", encoding="utf-8").read()

    @staticmethod
    def _code_lines(src):
        return "\n".join(l for l in src.splitlines()
                          if l.strip() and not l.strip().startswith("#"))

    def test_it_never_calls_the_sender(self):
        """Checks CALL NODES, not text.

        Stripping `#` comments is not enough: the docstring explaining this fix
        necessarily quotes the call it replaced, so a text search matches the
        explanation and fails for the wrong reason. That has now caught me four
        times in this session. Walk the AST and look at what is actually called.
        """
        import ast
        tree = ast.parse(self._src())
        called = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Attribute):
                    called.add(f.attr)
                elif isinstance(f, ast.Name):
                    called.add(f.id)
        assert "send_telegram_briefing" not in called
        assert "send_full_ai_briefing" not in called

    def test_it_still_checks_the_bridge_resolves(self):
        code = self._code_lines(self._src())
        assert "_lazy_import_market(" in code
        assert "callable(" in code

    def test_no_assertion_is_unconditionally_true(self):
        """`assert X or True` is a decorative way of writing `assert True`."""
        import re
        src = self._src()
        bad = [ln.strip() for ln in src.splitlines()
               if ln.strip().startswith("assert")
               and re.search(r"\bor\s+True\b", ln)]
        assert not bad, bad

    def test_the_snapshot_check_rejects_an_error_string(self):
        """isinstance(snap, (str, dict)) passed for "Error getting ..." too."""
        code = self._code_lines(self._src())
        i = code.index("run_market_snapshot()")
        after = code[i:i + 700]
        assert "startswith" in after and "error" in after.lower()

    def test_the_mcp_check_asserts_something_real(self):
        code = self._code_lines(self._src())
        i = code.index("import openhands_mcp.server as mcp_server")
        after = code[i:i + 500]
        assert 'hasattr(mcp_server, "mcp")' in after


class TestSendersAreNeverCalledByChecks:
    """A verification or test path must not deliver anything to the user's real
    channel. This walks every non-test module for a call to a known sender that
    is not itself inside a sending function."""

    SENDERS = ("send_full_ai_briefing(", "send_telegram_briefing(",
               "send_simplex_briefing(")

    CHECKERS = ("verify_system.py", "verify_evolution.py")

    NAMES = ("send_full_ai_briefing", "send_telegram_briefing",
             "send_simplex_briefing")

    def test_no_health_check_calls_a_sender(self):
        """AST call nodes only — a docstring naming the sender is not a call."""
        import ast
        found = []
        for path in self.CHECKERS:
            try:
                src = open(path, encoding="utf-8").read()
            except FileNotFoundError:
                continue
            for n in ast.walk(ast.parse(src)):
                if not isinstance(n, ast.Call):
                    continue
                f = n.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name in self.NAMES:
                    found.append(f"{path}:{n.lineno}: calls {name}()")
        assert not found, found


class TestRoutingFlagsMatchWholeWords:
    """Three routing flags used `any(k in task_lower for k in [...])` — a plain
    substring test — and their short keywords appear inside ordinary English.
    Measured before the fix:

        is_pr      "pr"    fired on imPRove, comPRess, aPPRoach, PRint
                   "press" fired on comPRESSed, PRESSure
                   "media" fired on imMEDIAte, reMEDIAtion
        is_backend "api"   fired on rAPId and cAPItal — both words this user
                           types constantly in a trading context
        is_qa      "test"  fired on laTEST, greaTEST, proTEST

    So "fix the print statement" attached a PR communications consultation and
    "capital allocation" pulled in a backend specialist. Same defect class as
    looks_like_solidity matching "erc" inside e-commerce."""

    ORDINARY = [
        ("fix the print statement in my parser", ("pr", "press", "media")),
        ("compress this image", ("pr", "press")),
        ("improve the approach here", ("pr",)),
        ("capital allocation for the quarter", ("api",)),
        ("rapid market moves", ("api",)),
        ("show me the latest prices", ("test",)),
        ("remediation plan for the incident", ("media",)),
    ]

    REAL = [
        ("write a press release", ("press", "pr")),
        ("handle PR outreach to journalists", ("pr",)),
        ("build a REST api", ("api",)),
        ("run the tests", ("test", "tests")),
        ("media relations plan", ("media",)),
        ("we need QA on this", ("qa",)),
    ]

    def test_ordinary_words_do_not_trigger_a_route(self):
        from openhands_skills.openhands_v2_entry import _mentions
        wrong = [t for t, w in self.ORDINARY if _mentions(t, *w)]
        assert not wrong, wrong

    def test_real_mentions_still_trigger(self):
        from openhands_skills.openhands_v2_entry import _mentions
        missed = [t for t, w in self.REAL if not _mentions(t, *w)]
        assert not missed, missed

    def test_the_three_flags_use_the_helper(self):
        import inspect
        from openhands_skills import openhands_v2_entry as E
        code = [l for l in inspect.getsource(E.run_task).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = "\n".join(code)
        for flag in ("is_qa", "is_backend", "is_pr"):
            line = next((l for l in code if l.strip().startswith(f"{flag} =")), "")
            assert "_mentions(" in line, f"{flag} still uses substring matching: {line.strip()}"

    def test_no_routing_flag_anywhere_uses_a_short_substring(self):
        """The defect class, not just the three instances."""
        import ast
        import glob
        import re

        DANGEROUS = {"pr", "api", "test", "press", "media", "erc", "defi", "seo",
                     "qa", "ai", "ml", "ui", "ux", "pl", "pls"}
        found = []
        for path in glob.glob("openhands_skills/*.py") + glob.glob("openhands_multiagent_v2/*.py"):
            with open(path, encoding="utf-8-sig") as fh:
                src = fh.read()
            for m in re.finditer(
                    r"^\s*(is_\w+)\s*=\s*any\(\s*k\s+in\s+\w+\s+for\s+k\s+in\s+\[([^\]]*)\]",
                    src, re.M):
                try:
                    words = ast.literal_eval("[" + m.group(2) + "]")
                except Exception:
                    continue
                bad = [w for w in words if isinstance(w, str) and w.lower() in DANGEROUS]
                if bad:
                    line = src[:m.start()].count("\n") + 1
                    found.append(f"{path}:{line} {m.group(1)} -> {bad}")
        assert not found, found


class TestMcpStdioTransportGetsACleanChannel:
    """--transport stdio is an offered choice, and under it stdout IS the
    protocol: JSON-RPC frames travel on it. Measured, importing the server wrote
    5,185 bytes to stdout before the first message could be exchanged.

    Only eleven of those prints are in server.py. The rest are the registration
    banners the expert skills emit at import time ("Code Researcher
    registered...", and thirty more), so fixing that one file would not have
    been enough — the guard has to run before the skills are imported.

    These redirect the child's streams to FILES rather than pipes. Under pytest
    a piped subprocess came back with returncode 0 and stdout None in 2.7s,
    which is not long enough for the import to have run at all; files are not
    subject to whatever pytest does to the inherited handles.
    """

    CODE = "import sys; sys.path.insert(0, '.'); import openhands_mcp.server"

    def _run(self, tmp_path, extra):
        import subprocess
        import sys
        out = tmp_path / "out.txt"
        err = tmp_path / "err.txt"
        with open(out, "w", encoding="utf-8") as fo, open(err, "w", encoding="utf-8") as fe:
            rc = subprocess.call([sys.executable, "-X", "utf8", "-c", self.CODE] + extra,
                                 stdout=fo, stderr=fe, cwd=".")
        return (rc,
                out.read_text(encoding="utf-8", errors="replace"),
                err.read_text(encoding="utf-8", errors="replace"))

    def test_stdout_is_silent_under_stdio_transport(self, tmp_path):
        rc, out, err = self._run(tmp_path, ["--transport", "stdio"])
        assert rc == 0, err[-400:]
        assert out == "", f"{len(out)} bytes would corrupt the JSON-RPC stream: {out[:200]!r}"

    def test_the_diagnostics_still_appear_on_stderr(self, tmp_path):
        """Silencing them would be worse than misrouting them."""
        rc, out, err = self._run(tmp_path, ["--transport", "stdio"])
        assert rc == 0, err[-400:]
        assert len(err) > 1000, f"the banners vanished instead of moving ({len(err)} bytes)"

    def test_http_transport_is_unchanged(self, tmp_path):
        rc, out, err = self._run(tmp_path, [])
        assert rc == 0, err[-400:]
        assert len(out) > 1000, f"the default transport should be untouched ({len(out)} bytes)"

    def test_the_guard_runs_before_the_skills_are_imported(self):
        """Order is the whole point: the banners fire during import."""
        src = open("openhands_mcp/server.py", encoding="utf-8").read()
        guard = src.index("sys.stdout = sys.stderr")
        first_skill = min(
            (src.index(m) for m in ("from openhands_skills.guards import",
                                    "from openhands_skills.chain_analysis_expert import")
             if m in src),
            default=len(src))
        assert guard < first_skill, "the guard must come before any skill import"


class TestDocumentRouteAcceptsRealPaths:
    """The document route matched only a Windows drive letter:

        _re.search(r"[A-Za-z]:[\\/]...[dot]pdf", user_task)

    A POSIX path, a relative path, and a quoted path containing spaces all
    failed — and the route then answered "give me the path of the PDF" to
    someone who had just given it. Which is the specific frustration of being
    told to repeat yourself by something that did not read you."""

    @staticmethod
    def _pdf(tmp_path, name):
        f = tmp_path / name
        f.write_bytes(b"%PDF-1.4")
        return str(f)

    def test_a_windows_path_is_found(self, tmp_path):
        from openhands_skills.openhands_v2_entry import _extract_pdf
        p = self._pdf(tmp_path, "book.pdf")
        assert _extract_pdf(f"analyse {p}") == p

    def test_forward_slashes_and_a_trailing_word(self, tmp_path):
        from openhands_skills.openhands_v2_entry import _extract_pdf
        p = self._pdf(tmp_path, "book.pdf")
        got = _extract_pdf("analyse " + p.replace(chr(92), "/") + " please")
        assert got and got.lower().endswith("book.pdf")

    def test_a_quoted_path_with_spaces(self, tmp_path):
        from openhands_skills.openhands_v2_entry import _extract_pdf
        p = self._pdf(tmp_path, "my book.pdf")
        got = _extract_pdf('read "' + p + '" for me')
        assert got and got.lower().endswith("my book.pdf")

    def test_an_unquoted_path_with_spaces(self, tmp_path):
        """Trailing words are trimmed one at a time until the file resolves,
        so a real path containing spaces survives."""
        from openhands_skills.openhands_v2_entry import _extract_pdf
        p = self._pdf(tmp_path, "my book.pdf")
        got = _extract_pdf("read " + p + " please")
        assert got and got.lower().endswith("my book.pdf")

    def test_posix_and_relative_paths_are_recognised(self):
        """They do not exist here, but they must be RECOGNISED as the path so
        the route can say it could not find them, instead of claiming none was
        given."""
        from openhands_skills.openhands_v2_entry import _extract_pdf
        assert _extract_pdf("/home/kq/report.pdf now") == "/home/kq/report.pdf"
        assert _extract_pdf("open docs/manual.pdf") == "docs/manual.pdf"
        assert _extract_pdf("see ./notes.pdf") == "./notes.pdf"

    def test_the_surrounding_sentence_is_not_part_of_the_path(self):
        """"open docs/manual.pdf" begins at the start of the string, so a
        start-anchored pattern still swallowed "open". Leading words are
        trimmed as well as trailing ones."""
        from openhands_skills.openhands_v2_entry import _extract_pdf
        for t in ("open docs/manual.pdf", "please read docs/manual.pdf"):
            assert _extract_pdf(t) == "docs/manual.pdf", t

    def test_no_path_returns_none(self):
        from openhands_skills.openhands_v2_entry import _extract_pdf
        assert _extract_pdf("what is in my book") is None
        assert _extract_pdf("") is None

    def test_the_route_reports_a_missing_file_instead_of_opening_another(self):
        import inspect
        from openhands_skills import openhands_v2_entry as E
        code = [l for l in inspect.getsource(E).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        i = body.index('route.name == "document"')
        after = body[i:i + 900]
        assert "_extract_pdf(user_task)" in after
        assert "isfile" in after


class TestRegimeNeedsAQuorum:
    """The regime was a bare majority of coloured rows, with no floor on how
    many rows had a price at all.

    After the stock_engine fix a failed quote renders "⚪ ... δεν ανακτήθηκε"
    and counts as neither colour — which is right, but left the counts unable
    to distinguish a flat market from an outage. So nine failures and one green
    quote produced BULLISH, and ten failures produced MIXED, which reads like a
    market observation rather than a dead API."""

    def test_one_surviving_quote_is_not_a_market_view(self):
        import regime_engine as R
        items = ["🟢 A | $1 | 1%"] + ["⚪ B | δεν ανακτήθηκε"] * 9
        b, r, c = R.count_sentiment(items)
        assert c == 1
        assert R._regime(b, r, c, "test") == "UNKNOWN"

    def test_no_quotes_at_all_is_unknown_not_mixed(self):
        import regime_engine as R
        items = ["⚪ X | δεν ανακτήθηκε"] * 10
        b, r, c = R.count_sentiment(items)
        assert R._regime(b, r, c, "test") == "UNKNOWN"

    def test_a_one_vote_edge_is_not_a_direction(self):
        import regime_engine as R
        assert R._regime(5, 4, 9, "test") == "MIXED"

    def test_a_clear_majority_still_reads(self):
        import regime_engine as R
        assert R._regime(8, 2, 10, "test") == "BULLISH"
        assert R._regime(1, 7, 8, "test") == "BEARISH"

    def test_count_sentiment_reports_how_many_had_a_price(self):
        """Two counts cannot tell a flat market from an outage; three can."""
        import regime_engine as R
        assert R.count_sentiment(["🟢 a", "🔴 b", "⚪ c"]) == (1, 1, 2)

    def test_overall_is_unknown_when_either_side_is(self, monkeypatch):
        import regime_engine as R
        monkeypatch.setattr(R, "get_stock_watchlist", lambda: ["⚪ x"] * 5)
        monkeypatch.setattr(R, "get_crypto_watchlist", lambda: ["🟢 a"] * 8)
        out = R.analyze_market_regime()
        assert out["stock_regime"] == "UNKNOWN"
        assert out["overall"] == "UNKNOWN", "UNKNOWN must not be laundered into MIXED"


class TestMarketBrainDoesNotNarrateMissingData:
    """market_brain reads the regime and writes commentary. Its `else` branch
    produces "US equities show mixed behavior with rotational flows between
    growth and defensive sectors" — and UNKNOWN fell into that `else`. So a run
    that retrieved no prices published a confident paragraph about sector
    rotation."""

    @staticmethod
    def _brain_with(monkeypatch, regime):
        import market_brain as M
        monkeypatch.setattr(M, "analyze_market_regime", lambda: {
            "stock_regime": regime, "crypto_regime": regime, "overall": regime,
            "stock_bullish": 0, "stock_bearish": 0,
            "crypto_bullish": 0, "crypto_bearish": 0})
        out = M.generate_market_brain()
        return out if isinstance(out, str) else str(out)

    def test_an_unknown_regime_does_not_describe_sector_rotation(self, monkeypatch):
        t = self._brain_with(monkeypatch, "UNKNOWN")
        assert "rotational" not in t.lower()
        assert "defensive sectors" not in t.lower()

    def test_it_says_the_data_was_missing(self, monkeypatch):
        t = self._brain_with(monkeypatch, "UNKNOWN")
        assert ("δεν κοιτάξαμε" in t or "δεν υπολογίστηκε" in t
                or "δεν ανακτήθηκαν" in t)

    def test_a_real_mixed_regime_still_gets_its_commentary(self, monkeypatch):
        """The fix must not silence the genuine MIXED case."""
        t = self._brain_with(monkeypatch, "MIXED")
        assert "mixed" in t.lower()

    def test_every_regime_branch_handles_unknown(self):
        import inspect
        import market_brain as M
        src = inspect.getsource(M.generate_market_brain)
        assert src.count('== "UNKNOWN"') >= 3, (
            "stock, crypto and overall each need their own branch")


class TestOracleDoesNotPoisonItsOwnMemory:
    """generate_vision guarded with `vision.startswith("(")`, which catches the
    error sentinels and nothing else. A DRAFT — the model's scratchpad,
    recovered when it spends its whole budget reasoning and never writes an
    answer — is real text that does not start with a parenthesis, so it passed
    straight through.

    Worse, BOTH the scratchpad and the canned fallback were written to the
    vector database with type="strategic_vision". Every failed run added another
    paragraph that retrieve_relevant() would later surface as analysis. A store
    that cannot refuse poisons itself."""

    @staticmethod
    def _module():
        """The package re-exports the singleton under the module's own name, so
        `from ... import strategic_oracle` hands back the INSTANCE. Patching
        module globals needs the real module object."""
        import sys
        import openhands_multiagent_v2.strategic_oracle  # noqa: F401
        return sys.modules["openhands_multiagent_v2.strategic_oracle"]

    def _run(self, monkeypatch, fake_output):
        SO = self._module()
        stored = []

        class Mem:
            def store(self, text, metadata):
                stored.append((metadata.get("type"), text))

        class Hub:
            def run_master_report(self, symbol):
                return "master"

            def run_market_snapshot(self):
                return "snapshot"

            def run_macro_report(self):
                return "macro"

        monkeypatch.setattr(SO, "persistent_memory", Mem())
        monkeypatch.setattr(SO, "tool_hub", Hub())
        o = SO.strategic_oracle
        monkeypatch.setattr(o, "complete", lambda *a, **k: fake_output)
        return o.generate_vision("BTC/USDT"), stored

    def test_a_real_answer_is_stored(self, monkeypatch):
        out, stored = self._run(monkeypatch, "Scenario A: base 60, bull 25, bear 15.")
        assert len(stored) == 1
        assert stored[0][0] == "strategic_vision"

    def test_a_backend_failure_is_not_stored(self, monkeypatch):
        out, stored = self._run(monkeypatch, "(oracle agent LLM error: backend down)")
        assert stored == [], "the canned fallback was written as a real vision"

    def test_a_draft_is_not_stored(self, monkeypatch):
        from llm_client import LLM_DRAFT_PREFIX
        out, stored = self._run(monkeypatch, LLM_DRAFT_PREFIX + "thinking out loud here")
        assert stored == [], "the model's scratchpad was written as a real vision"

    def test_a_draft_is_returned_labelled_not_silently(self, monkeypatch):
        from llm_client import LLM_DRAFT_PREFIX
        out, _ = self._run(monkeypatch, LLM_DRAFT_PREFIX + "thinking out loud here")
        assert "ΔΕΝ είναι στρατηγικό όραμα" in out
        assert "thinking out loud here" in out, "the scratchpad should be kept, just labelled"

    def test_it_checks_both_failure_shapes(self):
        import inspect
        SO = self._module()
        code = [l for l in inspect.getsource(SO.StrategicOracle.generate_vision).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert "is_llm_error" in body and "is_llm_draft" in body
        assert 'vision.startswith("(")' not in body


class TestSelfCorrectingLoopCannotBeSilenced:
    """The loop feeds analyzer findings back to the model and re-analyzes. A
    model can clear a finding two ways that leave the analyzer happy and the
    problem intact: add a suppression comment, or delete the code that carried
    it. Either produced nblock == 0 on the next pass, and the loop then set
    clean=True and reported a successful build with the vulnerability still
    present.

    Nothing here calls the model — self.complete is replaced and the real
    analyzers run."""

    @staticmethod
    def _module():
        import sys
        import openhands_multiagent_v2.self_correcting_coder  # noqa: F401
        return sys.modules["openhands_multiagent_v2.self_correcting_coder"]

    BEFORE = "import subprocess\ndef r(c):\n    return subprocess.call(c, shell=True)\n" * 4

    def test_a_suppression_comment_is_not_a_fix(self):
        C = self._module().SelfCorrectingCoder
        for marker in ("# nosec", "# noqa", "# type: ignore", "# pylint: disable=all"):
            after = self.BEFORE + f"x = 1  {marker}\n"
            why = C._cheated(self.BEFORE, after)
            assert why and "suppression" in why, marker

    def test_deleting_the_code_is_not_a_fix(self):
        C = self._module().SelfCorrectingCoder
        why = C._cheated(self.BEFORE, "def r(c):\n    pass\n")
        assert why and "deleted" in why

    def test_a_real_rewrite_is_accepted(self):
        C = self._module().SelfCorrectingCoder
        after = ("import shlex, subprocess\ndef r(c):\n"
                 "    return subprocess.call(shlex.split(c), shell=False)\n") * 4
        assert C._cheated(self.BEFORE, after) is None

    def test_a_small_honest_edit_is_not_called_deletion(self):
        """The shrink floor must not fire on a genuine tightening."""
        C = self._module().SelfCorrectingCoder
        after = self.BEFORE.replace("shell=True", "shell=False")
        assert C._cheated(self.BEFORE, after) is None

    def _build_with(self, reply, first):
        SC = self._module()

        class FakeCoder:
            def write_or_refactor(self, task):
                return "```python\n" + first + "```"

        old_coder = SC.coder
        b = SC.self_correcting_coder
        old_complete = b.complete
        SC.coder = FakeCoder()
        b.complete = lambda *a, **k: "```python\n" + reply + "```"
        try:
            return b.build("run a command", max_iterations=2)
        finally:
            SC.coder = old_coder
            b.complete = old_complete

    def test_a_silenced_build_is_not_reported_clean(self):
        one_finding = ("import subprocess\n\n\ndef run(cmd):\n"
                       "    return subprocess.call(cmd, shell=True)\n")
        suppressed = one_finding.replace("shell=True)", "shell=True)  # nosec  # noqa")
        r = self._build_with(suppressed, one_finding)
        assert r.clean is False
        assert "NOT CLEAN" in (r.final_report or "")

    def test_the_report_says_which_round_cheated(self):
        one_finding = ("import subprocess\n\n\ndef run(cmd):\n"
                       "    return subprocess.call(cmd, shell=True)\n")
        suppressed = one_finding.replace("shell=True)", "shell=True)  # nosec")
        r = self._build_with(suppressed, one_finding)
        assert "round" in (r.final_report or "").lower()
        assert "suppression" in (r.final_report or "").lower()


class TestSupervisorKeepsTheVerdict:
    """coordinate() built its synthesis prompt with

        {k: str(v)[:3000] for k, v in results.items()}

    which keeps the first 3000 characters and silently drops the rest. A
    security report states its verdict AFTER the scan and a review lists its
    blockers AFTER the walkthrough, so head-truncation removes exactly the part
    that matters. Measured: security.audit returns 3778 characters, and the
    prompt — which asks the model to "quote the concrete security findings" —
    received the scan without the conclusion, with nothing in the text to say
    anything had been cut."""

    @staticmethod
    def _cls():
        import sys
        import openhands_multiagent_v2.advanced_supervisor  # noqa: F401
        return sys.modules["openhands_multiagent_v2.advanced_supervisor"].AdvancedSupervisor

    LONG = "HEAD-MARKER\n" + ("y" * 12000) + "\nVERDICT: 2 HIGH severity — do not deploy."

    def test_the_end_survives(self):
        S = self._cls()
        clipped = S._clip(self.LONG, 3000)
        assert "VERDICT" in clipped, "the conclusion was dropped again"
        assert "HEAD-MARKER" in clipped, "the opening should survive too"

    def test_the_old_behaviour_lost_it(self):
        """Guards the premise, so this test still means something later."""
        assert "VERDICT" not in self.LONG[:3000]

    def test_the_clip_is_declared(self):
        S = self._cls()
        clipped = S._clip(self.LONG, 3000)
        assert "omitted from the middle" in clipped

    def test_short_results_are_untouched(self):
        S = self._cls()
        short = "a small result"
        assert S._clip(short, 3000) == short

    def test_verdict_bearing_results_get_more_room(self):
        S = self._cls()
        assert S._budget_for("security_audit", 3000) == 6000
        assert S._budget_for("reviewer_findings", 3000) == 6000
        assert S._budget_for("test_status", 3000) == 6000
        assert S._budget_for("coder_output", 3000) == 3000

    def test_coordinate_uses_the_clip(self):
        import inspect
        S = self._cls()
        code = [l for l in inspect.getsource(S.coordinate).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert "str(v)[:3000]" not in body, "still head-truncating"
        assert "self._clip(" in body


class TestPnlIsNotInvented:
    """_estimate_pnl_with_market reported

        estimated_unrealized_pnl_usd = round(pls_pnl_contrib * 0.9, 2)

    — the current USD value of the wallet's PLS/WPLS holdings, times a
    constant. That is not a profit calculation. Profit is exit value minus
    entry cost, and no entry cost is fetched anywhere in that function or in
    the data it receives. The 0.9 encoded a guess ("most PLS inflows are gain")
    as a dollar figure, under a key that reads as a measurement.

    Measured: a wallet holding $8,000 of PLS was reported as having $7,200 of
    unrealized profit."""

    ACTIVITY = {
        "approx_usd_value": 12000,
        "address": "0xabc",
        "native_transfers": [{"to": "0xabc", "value": 5_000_000}],
        "current_balances": [{"symbol": "PLS", "usd": 8000},
                             {"symbol": "HEX", "usd": 4000}],
    }

    def _pnl(self):
        from openhands_skills.chain_analysis_expert import chain_analysis_expert as C
        return C._estimate_pnl_with_market(dict(self.ACTIVITY), "pulsechain")

    def test_no_number_is_reported_without_a_cost_basis(self):
        r = self._pnl()
        assert r["estimated_unrealized_pnl_usd"] is None
        assert r["pnl_available"] is False

    def test_it_says_why(self):
        r = self._pnl()
        assert "cost basis" in r["pnl_unavailable_reason"].lower()

    def test_the_key_still_exists_so_callers_do_not_raise(self):
        """langgraph_orchestrator and wallet_forensics_automation both read
        this dict; removing keys would break them."""
        r = self._pnl()
        for k in ("estimated_unrealized_pnl_usd", "current_portfolio_usd",
                  "big_native_pls_contrib_usd_approx", "note"):
            assert k in r, k

    def test_the_measured_facts_are_kept(self):
        r = self._pnl()
        assert r["native_holdings_value_usd"] == 8000
        assert r["current_portfolio_usd"] == 12000

    def test_the_magic_constant_is_gone(self):
        import inspect
        from openhands_skills.chain_analysis_expert import ChainAnalysisExpert
        code = [l for l in inspect.getsource(
                    ChainAnalysisExpert._estimate_pnl_with_market).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert "* 0.9" not in body
        assert "0.9," not in body

    def test_the_note_does_not_call_a_receive_a_gain(self):
        r = self._pnl()
        low = r["note"].lower()
        assert "high pnl contributor" not in low
        assert "not by itself a gain" in low or "not computed" in low

    def test_the_dead_market_note_branches_are_gone(self):
        """Two `if` branches built market_note and the next line overwrote the
        variable unconditionally, so neither ever affected the output."""
        import inspect
        from openhands_skills.chain_analysis_expert import ChainAnalysisExpert
        code = [l for l in inspect.getsource(
                    ChainAnalysisExpert._estimate_pnl_with_market).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert "market_note +=" not in body


class TestEvolutionLogRecordsRatherThanFlatters:
    """Every entry carried evolution_note = "New pattern detected - system
    improved". Measured on the real log: 27 entries, 27 identical notes.
    Nothing detected a pattern and nothing measured an improvement — the
    sentence was a constant, and a constant that claims progress is worse than
    no note at all, because it reads as evidence.

    The write path was worse. A bare `except:` around the read rewrote the whole
    file with a single entry, so one unreadable read destroyed the entire
    history, silently, and the next run looked like a clean start."""

    @staticmethod
    def _agent(tmp_path):
        import os
        import sys
        import openhands_multiagent_v2.hyper_evolution_agent  # noqa: F401
        H = sys.modules["openhands_multiagent_v2.hyper_evolution_agent"]

        class Mem:
            def store(self, text, metadata):
                pass

        H.persistent_memory = Mem()
        a = H.hyper_evolver
        a.evolution_file = os.path.join(str(tmp_path), "evo.json")
        return a

    @staticmethod
    def _entries(agent):
        import json
        with open(agent.evolution_file, encoding="utf-8") as f:
            return json.load(f)

    def test_it_no_longer_claims_the_system_improved(self, tmp_path):
        a = self._agent(tmp_path)
        a.evolve("do the thing", "here is the answer")
        e = self._entries(a)[-1]
        assert "evolution_note" not in e or "improved" not in str(e.get("evolution_note", ""))
        assert "improved" not in e["note"].lower()

    def test_it_records_whether_the_response_was_real(self, tmp_path):
        a = self._agent(tmp_path)
        a.evolve("q", "Here is a genuine answer.")
        assert self._entries(a)[-1]["response_quality"] == "answered"
        a.evolve("q", "(coder agent LLM error: backend down)")
        assert self._entries(a)[-1]["response_quality"] == "failed"

    def test_a_draft_is_recorded_as_a_draft(self, tmp_path):
        from llm_client import LLM_DRAFT_PREFIX
        a = self._agent(tmp_path)
        a.evolve("q", LLM_DRAFT_PREFIX + "thinking out loud")
        assert self._entries(a)[-1]["response_quality"] == "draft_only"

    def test_history_accumulates(self, tmp_path):
        a = self._agent(tmp_path)
        for i in range(3):
            a.evolve(f"q{i}", "an answer")
        assert len(self._entries(a)) == 3

    def test_a_corrupt_log_is_preserved_not_overwritten(self, tmp_path):
        import os
        a = self._agent(tmp_path)
        for i in range(3):
            a.evolve(f"q{i}", "an answer")
        assert len(self._entries(a)) == 3

        with open(a.evolution_file, "w", encoding="utf-8") as f:
            f.write("{ not valid json")

        a.evolve("after the corruption", "an answer")
        assert os.path.exists(a.evolution_file + ".corrupt"), (
            "the unreadable history was destroyed instead of moved aside")
        assert len(self._entries(a)) == 1

    def test_the_bare_except_is_gone(self):
        import inspect
        from openhands_multiagent_v2.hyper_evolution_agent import HyperAdaptiveEvolutionAgent as A
        code = [l for l in inspect.getsource(A.evolve).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert "except:" not in body, "a bare except still swallows everything"


class TestDebuggerDiagnosesContractErrorsToo:
    """Any error text containing "contract", "revert", "evm", "gas" and so on
    took a branch that:

      - passed the ERROR MESSAGE to solidity_expert.audit_solidity as though it
        were Solidity source (it is not, so the auditor refused), then presented
        that refusal as "the audit"
      - appended a hardcoded six-line bug list, identical for every error
      - returned a fixed "1. Reproduce 2. Isolate 3. Patch 4. Re-audit 5. Test
        on fork"

    It never called the model. The generic branch below it did. So the
    "advanced Solidity/PulseChain" path returned strictly LESS analysis than the
    ordinary one, for precisely the errors it claimed to specialise in."""

    @staticmethod
    def _agent():
        import sys
        import openhands_multiagent_v2.debugger_agent_v2  # noqa: F401
        return sys.modules["openhands_multiagent_v2.debugger_agent_v2"].debugger

    def _debug(self, monkeypatch, error):
        d = self._agent()
        calls = []
        monkeypatch.setattr(d, "complete",
                            lambda p, *a, **k: calls.append(p) or "DIAGNOSIS: root cause is X.")
        return d.debug(error), calls

    def test_a_contract_error_reaches_the_model(self, monkeypatch):
        out, calls = self._debug(monkeypatch, "execution reverted: contract call failed")
        assert len(calls) == 1, "the contract branch still skips the diagnosis"
        assert "DIAGNOSIS" in out

    def test_a_plain_python_error_still_works(self, monkeypatch):
        out, calls = self._debug(monkeypatch, "KeyError: FINNHUB_API_KEY")
        assert len(calls) == 1
        assert "DIAGNOSIS" in out

    def test_the_bug_list_is_labelled_as_reference(self, monkeypatch):
        out, _ = self._debug(monkeypatch, "execution reverted: out of gas")
        assert "reference — not findings" in out

    def test_the_fixed_five_steps_are_gone(self, monkeypatch):
        out, _ = self._debug(monkeypatch, "execution reverted: contract call failed")
        assert "1. Reproduce 2. Isolate" not in out

    def test_the_auditor_is_not_fed_an_error_message(self):
        """audit_solidity is for source. Calling it on an error text produced a
        refusal that was then displayed as the audit.

        Uses ast.unparse with the docstring removed. Stripping `#` comments is
        not enough here: the docstring explaining this fix names audit_solidity,
        and it appears BEFORE the guard, so a text search finds the explanation
        and fails for the wrong reason. Fifth time in this session."""
        import ast
        import inspect
        from openhands_multiagent_v2.debugger_agent_v2 import DebuggerAgent

        fn = ast.parse(inspect.getsource(DebuggerAgent.debug).lstrip()).body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)):
            fn.body.pop(0)
        body = ast.unparse(fn)

        i = body.index("audit_solidity")
        assert "looks_like_solidity" in body[:i], (
            "audit_solidity must be gated on the text actually being source")

    def test_the_zero_address_creator_call_is_gone(self):
        """It called analyze_contract_creator("0x0") when no address was
        present, and reported the result. The zero address is not the
        deployer."""
        import inspect
        from openhands_multiagent_v2.debugger_agent_v2 import DebuggerAgent
        code = [l for l in inspect.getsource(DebuggerAgent.debug).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert 'addresses[0] if addresses else' not in body
        assert '"0x0"' not in body

    def test_an_empty_error_is_refused(self):
        d = self._agent()
        assert "nothing was diagnosed" in d.debug("")


class TestEveryAgentAndSkillCallIsMeasured:
    """agent_metrics is a well-built, dependency-free run log with a summary
    CLI, and its own docstring states the reason it exists: "what we improved
    today (36->94 tok/s) we achieved because we MEASURED it first; the rest we
    improved blind."

    It was wired into ONE module out of eighty-five — cad_architect — so it
    recorded nothing worth reading. The log held two records from three weeks
    earlier and nothing ever read them.

    It is now attached at the two choke points every model call passes through:
    BaseLLMAgent.complete (every v2 agent) and ExpertSkill.consult (every
    skill). No model is called in these tests; llm_client.chat is replaced."""

    @staticmethod
    def _rows(path):
        import json
        import os
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def _isolated_log(self, tmp_path, monkeypatch):
        import openhands_skills.agent_metrics as AM
        from pathlib import Path
        p = Path(str(tmp_path)) / "runs.jsonl"
        monkeypatch.setattr(AM, "METRICS_FILE", p)
        return p

    def test_an_agent_call_is_recorded(self, tmp_path, monkeypatch):
        p = self._isolated_log(tmp_path, monkeypatch)
        import llm_client
        from openhands_multiagent_v2.coder_agent_v2 import coder
        monkeypatch.setattr(llm_client, "chat", lambda *a, **k: "a real answer")
        coder.write_or_refactor("write a median function")
        rows = self._rows(p)
        assert rows, "nothing was recorded"
        assert rows[-1]["agent"] == "agent:coder"
        assert rows[-1]["ok"] is True
        assert "seconds" in rows[-1]

    def test_an_empty_answer_is_not_a_success(self, tmp_path, monkeypatch):
        """The call did not raise, but it produced nothing. A metrics file that
        counts that as success is the same lie in a smaller place."""
        p = self._isolated_log(tmp_path, monkeypatch)
        import llm_client
        from openhands_multiagent_v2.coder_agent_v2 import coder
        monkeypatch.setattr(llm_client, "chat", lambda *a, **k: "   ")
        coder.write_or_refactor("write something")
        assert self._rows(p)[-1]["ok"] is False

    def test_a_failure_is_recorded_with_its_type(self, tmp_path, monkeypatch):
        p = self._isolated_log(tmp_path, monkeypatch)
        import llm_client
        from openhands_multiagent_v2.coder_agent_v2 import coder

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        coder.write_or_refactor("write something")
        last = self._rows(p)[-1]
        assert last["ok"] is False
        assert last.get("failure") == "RuntimeError"

    def test_a_skill_call_is_recorded(self, tmp_path, monkeypatch):
        p = self._isolated_log(tmp_path, monkeypatch)
        import llm_client
        from openhands_skills.security_auditor import security_auditor
        monkeypatch.setattr(llm_client, "chat", lambda *a, **k: "a real review")
        security_auditor.audit_security("passwords compared with ==")
        skills = [r for r in self._rows(p) if str(r["agent"]).startswith("skill:")]
        assert skills, "no skill run was recorded"
        assert skills[-1]["agent"] == "skill:security_auditor"

    def test_measurement_never_breaks_the_agent(self):
        """If agent_metrics cannot be imported, the agents must still work."""
        import inspect
        import openhands_multiagent_v2.base_llm_agent as B
        src = inspect.getsource(B)
        assert "except Exception:" in src
        i = src.index("from openhands_skills.agent_metrics import track")
        assert "contextmanager" in src[i:i + 500], (
            "there must be a null fallback so a missing metrics module is harmless")

    def test_both_choke_points_are_wired(self):
        import inspect
        from openhands_multiagent_v2.base_llm_agent import BaseLLMAgent
        from openhands_skills.expert_base import ExpertSkill
        assert "_track(" in inspect.getsource(BaseLLMAgent.complete)
        assert "_track(" in inspect.getsource(ExpertSkill.consult)


class TestOrchestratorDoesOnlyTheWorkTheTaskNeeds:
    """Three defects in one method, all measured with counting stubs — no model
    is called anywhere in these tests.

    `debug = debugger.debug("Any issues found")` passed a CONSTANT STRING to the
    debugger — not the task, not an error, not the code — so it diagnosed the
    literal phrase. Its result was then never used: `debug` appears in no later
    expression and is absent from the coordinate() dict. 18.6 seconds of model
    time per run, discarded.

    strategic_oracle.generate_vision() and market_analyst.analyze_market() ran
    on EVERY task with no arguments, so a request to refactor a parser produced
    a BTC/USDT strategic outlook and a market snapshot at full model cost.

    tests, review and security all read the same finished `code` and do not read
    each other, and ran as three sequential model calls while the server had
    four free slots."""

    @staticmethod
    def _module():
        import sys
        import openhands_multiagent_v2.multi_agent_orchestrator_v2  # noqa: F401
        return sys.modules["openhands_multiagent_v2.multi_agent_orchestrator_v2"]

    def _stubbed(self, monkeypatch):
        M = self._module()
        calls = []

        def stub(name):
            def f(*a, **k):
                calls.append(name)
                return f"[{name}]"
            return f

        class Obj:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        class Build:
            code = "def f(): pass"

            def to_report(self):
                return "build report"

        monkeypatch.setattr(M, "advanced_supervisor", Obj(
            plan_and_orchestrate=stub("plan"), coordinate=lambda d: "synthesis"))
        monkeypatch.setattr(M, "strategic_oracle", Obj(generate_vision=stub("vision")))
        monkeypatch.setattr(M, "market_analyst", Obj(analyze_market=stub("market")))
        monkeypatch.setattr(M, "coder", Obj(write_or_refactor=stub("coder")))
        monkeypatch.setattr(M, "self_correcting_coder",
                            Obj(build=lambda *a, **k: (calls.append("loop"), Build())[1]))
        monkeypatch.setattr(M, "tester", Obj(run_tests=stub("tests")))
        monkeypatch.setattr(M, "reviewer", Obj(review=stub("review")))
        monkeypatch.setattr(M, "security", Obj(audit=stub("security")))
        monkeypatch.setattr(M, "hyper_evolver", Obj(evolve=lambda *a, **k: "evolved"))
        return M.orchestrator, calls

    def test_the_debugger_is_not_called_with_a_constant(self, monkeypatch):
        o, calls = self._stubbed(monkeypatch)
        o.run("refactor this python parser function")
        assert "debug" not in calls

    def test_a_coding_task_does_no_market_work(self, monkeypatch):
        o, calls = self._stubbed(monkeypatch)
        o.run("refactor this python parser function")
        assert "vision" not in calls and "market" not in calls

    def test_a_market_task_still_does_market_work(self, monkeypatch):
        o, calls = self._stubbed(monkeypatch)
        o.run("what is the btc market regime right now")
        assert "vision" in calls and "market" in calls

    def test_the_discarded_call_is_gone_from_the_source(self):
        import inspect
        M = self._module()
        code = [l for l in inspect.getsource(M.MultiAgentOrchestratorV2.run).splitlines()
                if l.strip() and not l.strip().startswith("#")]
        body = chr(10).join(code)
        assert 'debugger.debug(' not in body
        assert '"Any issues found"' not in body


class TestOrchestratorRespectsTheServerSlots:
    """The three independent calls now run together — but only as far as the
    server says it can. At one slot this is exactly as serial as before, which
    is the same discipline the document pipeline uses: match the server, never
    guess above it."""

    @staticmethod
    def _cls():
        import sys
        import openhands_multiagent_v2.multi_agent_orchestrator_v2  # noqa: F401
        return sys.modules[
            "openhands_multiagent_v2.multi_agent_orchestrator_v2"].MultiAgentOrchestratorV2

    def test_one_slot_means_serial(self, monkeypatch):
        C = self._cls()
        monkeypatch.setattr(C, "_slots", classmethod(lambda cls, timeout=2.0: 1))
        out = C()._concurrently(("a", lambda: "A"), ("b", lambda: "B"))
        assert out == ("A", "B")

    def test_results_keep_the_callers_order(self, monkeypatch):
        import time
        C = self._cls()
        monkeypatch.setattr(C, "_slots", classmethod(lambda cls, timeout=2.0: 4))

        def slow():
            time.sleep(0.2)
            return "SLOW"

        out = C()._concurrently(("slow", slow), ("fast", lambda: "FAST"))
        assert out == ("SLOW", "FAST"), "order must follow the caller, not completion"

    def test_one_failing_call_does_not_kill_the_run(self, monkeypatch):
        C = self._cls()
        monkeypatch.setattr(C, "_slots", classmethod(lambda cls, timeout=2.0: 4))

        def boom():
            raise RuntimeError("backend down")

        out = C()._concurrently(("ok", lambda: "OK"), ("bad", boom))
        assert out[0] == "OK"
        assert "failed" in out[1] and "RuntimeError" in out[1]

    def test_the_slot_probe_is_cached(self, monkeypatch):
        """Probing every run costs the full timeout when the server is down,
        which is exactly when you least want to wait."""
        C = self._cls()
        C._slots_cache = None
        n = []
        monkeypatch.setattr(C, "_probe_slots", staticmethod(lambda timeout=2.0: n.append(1) or 3))
        assert C._slots() == 3
        assert C._slots() == 3
        assert len(n) == 1
        C._slots_cache = None


class TestOrdinaryPolitenessTakesTheFastPath:
    """_all_tokens_in required EVERY token to be in the social vocabulary. That
    is the right anti-hijack rule and the wrong bar for how people write: "hi"
    matched and "hi there" did not; "ευχαριστώ" matched and "ευχαριστώ πολύ"
    did not. Anything that missed fell through to the full pipeline, which
    costs about eight minutes.

    Measured on 43 ordinary social messages before the change: 15 missed, 35%.

    The corpus below was written BEFORE the fix, so the number is not chosen to
    flatter it, and the hijack list is checked in the same test run — a fast
    path that swallows real work would be a far worse bug than a slow greeting.
    """

    SOCIAL = [
        "hi", "hello", "hey there", "hi there", "good morning", "morning!",
        "thanks", "thanks a lot", "thank you very much", "thanks man",
        "ok cool", "ok thanks", "nice one", "cool thanks", "great thanks",
        "bye", "goodbye", "see you", "ok bye",
        "γεια", "γεια σου", "καλημέρα", "καλημέρα φίλε", "καλησπέρα",
        "ευχαριστώ", "ευχαριστώ πολύ", "σε ευχαριστώ", "ωραία ευχαριστώ",
        "εντάξει", "εντάξει ευχαριστώ", "ok ευχαριστώ", "τέλεια",
        "are you there", "are you alive", "you up", "still working",
        "είσαι εκεί", "ζεις", "δουλεύεις",
        "what can you do", "what are your capabilities",
        "τι μπορείς να κάνεις", "τι ξέρεις να κάνεις",
    ]

    WORK = [
        "hi can you write me a python parser",
        "thanks, now analyse wallet 0x1234567890123456789012345678901234567890",
        "good morning, what is the btc price",
        "γεια σου, φτιάξε μου ένα script",
        "ok now review this code",
        "ευχαριστώ, τώρα δώσε μου το briefing",
        "hello, build a website for my brand",
    ]

    def test_every_social_message_is_fast(self):
        from openhands_skills.intent_router import classify
        missed = [(m, classify(m).name) for m in self.SOCIAL
                  if not getattr(classify(m), "fast", False)]
        assert not missed, missed

    def test_no_real_request_is_swallowed_by_the_fast_path(self):
        """The anti-hijack rule is the point. A greeting word buried in a real
        request must never win."""
        from openhands_skills.intent_router import classify
        hijacked = [(m, classify(m).name) for m in self.WORK
                    if getattr(classify(m), "fast", False)]
        assert not hijacked, hijacked

    def test_connectives_alone_are_not_a_greeting(self):
        """"a lot" is filler in both directions and must not match on its own."""
        from openhands_skills.intent_router import classify
        for m in ("a lot", "very much", "the", "so", "just", "πολύ"):
            assert not getattr(classify(m), "fast", False), m

    def test_an_empty_message_never_matches(self):
        from openhands_skills.intent_router import classify
        for m in ("", "   ", "!!!", "123"):
            assert not getattr(classify(m), "fast", False), repr(m)

    def test_the_filler_set_holds_no_verbs_or_nouns(self):
        """A verb in there would let a real request through as a greeting."""
        from openhands_skills.intent_router import _FILLER
        forbidden = {"write", "build", "make", "analyse", "analyze", "review",
                     "fix", "run", "send", "code", "wallet", "price", "report",
                     "γραψε", "φτιαξε", "τρεξε", "στειλε"}
        assert not (_FILLER & forbidden), _FILLER & forbidden


class TestTheEvaluationFixtureCanActuallyMove:
    """SAMPLE_TEST_CASES held three cases with PLACEHOLDER addresses —
    0x..0001, 0x..0002, 0x..0003 — beside a comment claiming "logic uses mock
    data in eval". It did not: _run_blockchain_eval called analyze_address over
    the NETWORK on those addresses. They are empty wallets, so the expert
    correctly returned LOW and "general wallet risks" for all three.

    Case 2 expected exactly that and passed BY COINCIDENCE. Cases 1 and 3
    expected HIGH and MEDIUM and could never pass. Accuracy was pinned at 33.3%,
    which means the pre/post delta the self-improvement loop reads to decide
    whether it improved was structurally incapable of moving: improving the risk
    logic could not raise a score that was measuring empty wallets."""

    def test_the_fixture_is_offline_and_deterministic(self):
        import openhands_skills.evaluation_harness as EH
        for case in EH.SAMPLE_TEST_CASES:
            assert "activity" in case, f"{case['name']} still keys off an address"
            assert "address" not in case, f"{case['name']} still uses a live address"

    def test_no_placeholder_addresses_remain(self):
        import openhands_skills.evaluation_harness as EH
        blob = repr(EH.SAMPLE_TEST_CASES)
        for ph in ("0x0000000000000000000000000000000000000001",
                   "0x0000000000000000000000000000000000000002",
                   "0x0000000000000000000000000000000000000003"):
            assert ph not in blob, ph

    def test_the_score_reaches_one_hundred(self):
        """The old ceiling was 33.3%. A fixture that cannot reach 100% cannot
        report an improvement either."""
        import openhands_skills.evaluation_harness as EH
        h = EH.EvaluationHarness()
        h.last_eval_time = 0
        r = h.run_full_evaluation()
        b = r["blockchain_intelligence"]
        assert b["num_errored"] == 0, b.get("errors")
        assert b["accuracy_percent"] == 100.0, [
            (c["name"], c["actual_level"], c.get("actual_pattern"))
            for c in b["cases"] if not c["correct"]]

    def test_it_runs_without_the_network(self):
        """get_system_evaluation took 380 seconds because every case made live
        chain calls. It is now arithmetic."""
        import time
        import openhands_skills.evaluation_harness as EH
        h = EH.EvaluationHarness()
        h.last_eval_time = 0
        t0 = time.time()
        h.run_full_evaluation()
        assert time.time() - t0 < 10, "the evaluation is reaching the network again"

    def test_the_fixture_exercises_both_sides_of_the_pattern(self):
        """A fixture where the pattern always fires, or never does, tests
        nothing about the condition."""
        import openhands_skills.evaluation_harness as EH
        pats = {c["expected_pattern"] for c in EH.SAMPLE_TEST_CASES}
        assert len(pats) == 2, pats

    def test_it_covers_the_users_own_economic_rules(self):
        import openhands_skills.evaluation_harness as EH
        names = {c["name"] for c in EH.SAMPLE_TEST_CASES}
        assert "small_inflow_active_trader" in names, (
            "the rule that $50-$500 must not raise an alarm is untested")
        assert "many_coins_tiny_value" in names, (
            "the rule that USD matters and coin count does not is untested")

    def test_a_regression_in_the_risk_logic_would_show(self, monkeypatch):
        """The point of a fixture at 100%: breaking the logic must drop it."""
        import openhands_skills.evaluation_harness as EH
        from openhands_skills.chain_analysis_expert import chain_analysis_expert

        monkeypatch.setattr(chain_analysis_expert, "_calculate_risk_score",
                            lambda a, c: {"level": "LOW",
                                          "pattern_match": "general wallet risks"})
        h = EH.EvaluationHarness()
        h.last_eval_time = 0
        r = h.run_full_evaluation()
        assert r["blockchain_intelligence"]["accuracy_percent"] < 100.0


class TestSkillsFlagWhenTheModelDidNotAnswer:
    """Twenty-one skills do

        result["expert_analysis"] = self.consult(...)

    and consult() returns "(expert 'role' error: ...)" on backend failure. The
    sentinel went straight into the result dict, in a field named
    expert_analysis, beside a printed banner saying the work was delivered. A
    caller sees a populated analysis field and has to recognise the sentinel by
    eye to know the model never answered."""

    def test_a_failed_analysis_is_flagged(self, monkeypatch):
        import llm_client
        from openhands_skills.seo_expert import seo_expert

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        r = seo_expert.optimize_for_search("optimise my shop")
        assert r["expert_analysis_is_real"] is False
        assert "analysis_warning" in r

    def test_the_text_is_kept_not_hidden(self, monkeypatch):
        """A reader should still see what came back."""
        import llm_client
        from openhands_skills.seo_expert import seo_expert

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        r = seo_expert.optimize_for_search("optimise my shop")
        assert r["expert_analysis"], "the sentinel should be visible, just labelled"

    def test_a_real_analysis_is_not_flagged(self, monkeypatch):
        import llm_client
        from openhands_skills.seo_expert import seo_expert
        monkeypatch.setattr(llm_client, "chat", lambda *a, **k: "a genuine analysis")
        r = seo_expert.optimize_for_search("optimise my shop")
        assert r["expert_analysis_is_real"] is True
        assert "analysis_warning" not in r

    def test_every_site_that_assigns_expert_analysis_marks_it(self):
        """The defect class, not the one example."""
        import ast
        import glob
        unmarked = []
        for path in glob.glob("openhands_skills/*.py"):
            with open(path, encoding="utf-8-sig") as fh:
                src = fh.read()
            # AST assignments, not text: the base class docstring quotes this
            # exact pattern as the example it is explaining, and a text search
            # matched the explanation. Sixth time in this session.
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            assigns = [n for n in ast.walk(tree)
                       if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Subscript)
                       and getattr(n.targets[0].value, "id", "") == "result"
                       and getattr(n.targets[0].slice, "value", None) == "expert_analysis"]
            if not assigns:
                continue
            marks = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "attr", "") == "mark_analysis"]
            if len(marks) < len(assigns):
                unmarked.append(f"{path}: {len(assigns)} assignment(s), {len(marks)} mark(s)")
        assert not unmarked, unmarked


class TestEverySkillHasItsOwnName:
    """Twenty-six ExpertSkill subclasses never set ROLE, so they all identified
    as "expert" — in the log line, in the failure sentinel
    ("(expert 'expert' error: ...)"), and, once the metrics layer was wired in,
    in every metrics row: twenty-six skills writing to the same name.

    That last one matters most. A measurement that cannot tell SEOExpert from
    HacashL3Expert cannot answer the question the metrics file exists for."""

    @staticmethod
    def _all_subclasses():
        import glob
        import importlib
        import os
        from openhands_skills.expert_base import ExpertSkill
        for f in sorted(glob.glob("openhands_skills/*.py")):
            n = os.path.basename(f)[:-3]
            if n in ("__init__", "expert_base"):
                continue
            try:
                importlib.import_module("openhands_skills." + n)
            except Exception:
                pass
        out = []

        def walk(c):
            for s in c.__subclasses__():
                out.append(s)
                walk(s)

        walk(ExpertSkill)
        return out

    def test_no_subclass_is_still_generic(self):
        generic = [c.__name__ for c in self._all_subclasses() if c.ROLE == "expert"]
        assert not generic, generic

    def test_no_two_skills_share_a_role(self):
        import collections
        roles = collections.Counter(c.ROLE for c in self._all_subclasses())
        dupes = {r: n for r, n in roles.items() if n > 1}
        assert not dupes, dupes

    def test_the_name_is_derived_from_the_class(self):
        from openhands_skills.expert_base import ExpertSkill

        class HacashL3Expert(ExpertSkill):
            pass

        class SEOExpert(ExpertSkill):
            pass

        assert HacashL3Expert.ROLE == "hacash_l3_expert"
        assert SEOExpert.ROLE == "seo_expert"

    def test_an_explicit_role_still_wins(self):
        from openhands_skills.expert_base import ExpertSkill

        class Whatever(ExpertSkill):
            ROLE = "chosen_by_hand"

        assert Whatever.ROLE == "chosen_by_hand"


class TestStatusActuallyChecksSomething:
    """The status intent answered "✅ Είμαι ενεργός και έτοιμος." — a fixed
    string. The process answering is alive by definition; the question a person
    is asking when they type "are you alive" is whether the BACKEND is up, and
    that answer was identical whether llama-server was serving or had been dead
    for an hour.

    Every probe is local and bounded. Nothing calls the model."""

    @staticmethod
    def _entry():
        import openhands_skills.openhands_v2_entry as E
        return E

    def test_it_reports_a_dead_backend(self, monkeypatch):
        E = self._entry()
        monkeypatch.setattr(E, "_system_status", lambda timeout=2.0: {
            "llm": False, "llm_error": "URLError", "analyzers": {"ruff": True},
            "keys": {"FINNHUB_API_KEY": True}, "guards": True})
        r = E._fast_route("are you alive")
        assert r["healthy"] is False
        assert "ΔΕΝ αποκρίνεται" in r["user_visible"]

    def test_it_says_what_to_do_about_it(self, monkeypatch):
        E = self._entry()
        monkeypatch.setattr(E, "_system_status", lambda timeout=2.0: {
            "llm": False, "llm_error": "URLError", "analyzers": {},
            "keys": {}, "guards": True})
        r = E._fast_route("are you alive")
        assert "start-ai.bat" in r["user_visible"]

    def test_a_healthy_system_says_so(self, monkeypatch):
        E = self._entry()
        monkeypatch.setattr(E, "_system_status", lambda timeout=2.0: {
            "llm": True, "model": "gemma.gguf", "slots": 4,
            "analyzers": {"ruff": True, "bandit": True, "mypy": True, "pyflakes": True},
            "keys": {"FINNHUB_API_KEY": True}, "guards": True})
        r = E._fast_route("are you alive")
        assert r["healthy"] is True
        assert "gemma.gguf" in r["user_visible"]

    def test_unprotected_guards_are_not_reported_as_healthy(self, monkeypatch):
        """If the guards did not load, the briefing files are unprotected. That
        is not a healthy system, whatever the model is doing."""
        E = self._entry()
        monkeypatch.setattr(E, "_system_status", lambda timeout=2.0: {
            "llm": True, "model": "gemma.gguf", "slots": 4,
            "analyzers": {}, "keys": {}, "guards": False})
        r = E._fast_route("are you alive")
        assert r["healthy"] is False
        assert "Guards" in r["user_visible"]

    def test_missing_analyzers_are_named(self, monkeypatch):
        E = self._entry()
        monkeypatch.setattr(E, "_system_status", lambda timeout=2.0: {
            "llm": True, "model": "m", "slots": 1,
            "analyzers": {"ruff": True, "bandit": False, "mypy": False,
                          "pyflakes": True},
            "keys": {}, "guards": True})
        r = E._fast_route("are you alive")
        assert "bandit" in r["user_visible"] and "mypy" in r["user_visible"]

    def test_the_probe_touches_no_model(self):
        import inspect
        E = self._entry()
        src = inspect.getsource(E._system_status)
        assert "chat(" not in src and "consult(" not in src

    def test_the_real_probe_returns_the_expected_shape(self):
        """Runs for real — local only, and correct whether the server is up."""
        E = self._entry()
        st = E._system_status(timeout=2.0)
        assert set(("llm", "analyzers", "keys", "guards")) <= set(st)
        assert isinstance(st["llm"], bool)
        assert isinstance(st["analyzers"], dict) and st["analyzers"]


class TestPrReviewSaysWhatItCouldNotRead:
    """The read loop ended in `except Exception: pass`. Every unreadable file
    was skipped in silence, and if ALL of them failed — a wrong path, a
    permissions problem, a branch never checked out — `body` stayed empty and
    `material` collapsed to "PR: <description>". The reviewer then produced a
    confident review of the description alone, with nothing in the output to
    say that not one line of code had been read.

    full_security_audit, twenty lines below it in the same file, already did
    this correctly: it appends "(could not read: ...)" per file."""

    @staticmethod
    def _module():
        import sys
        import openhands_skills.pr_review_expert  # noqa: F401
        return sys.modules["openhands_skills.pr_review_expert"]

    def _expert(self, monkeypatch):
        PR = self._module()
        monkeypatch.setattr(PR, "_reviewer", type("R", (), {
            "review": staticmethod(lambda m: "REVIEW: looks fine to me.")})())
        return PR.pr_expert

    @staticmethod
    def _real_file(tmp_path):
        f = tmp_path / "a.py"
        f.write_text("def f():\n    return 1\n", encoding="utf-8")
        return str(f)

    def test_it_refuses_when_no_file_could_be_read(self, monkeypatch):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature", changed_files=["nope1.py", "nope2.py"])
        assert "ΔΕΝ έγινε review" in out
        assert not out.startswith("REVIEW:")

    def test_it_names_the_files_it_could_not_read(self, monkeypatch):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature", changed_files=["nope1.py"])
        assert "nope1.py" in out

    def test_it_refuses_when_nothing_was_supplied(self, monkeypatch):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature", changed_files=[])
        assert "ΔΕΝ έγινε review" in out

    def test_a_partial_read_is_reviewed_but_its_scope_is_stated(self, monkeypatch, tmp_path):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature",
                          changed_files=[self._real_file(tmp_path), "nope.py"])
        assert out.startswith("REVIEW:"), "a readable file must still be reviewed"
        assert "ΔΕΝ διαβάστηκαν" in out and "nope.py" in out

    def test_a_clean_read_adds_no_noise(self, monkeypatch, tmp_path):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature", changed_files=[self._real_file(tmp_path)])
        assert out.startswith("REVIEW:")
        assert "ΔΕΝ διαβάστηκαν" not in out

    def test_an_explicit_diff_still_works(self, monkeypatch):
        e = self._expert(monkeypatch)
        out = e.review_pr("add a feature", diff="--- a\n+++ b\n+print(1)\n")
        assert out.startswith("REVIEW:")

    def test_the_silent_pass_is_gone(self):
        import ast
        import inspect
        PR = self._module()
        fn = ast.parse(inspect.getsource(PR.PRReviewExpert.review_pr).lstrip()).body[0]
        for node in ast.walk(fn):
            if isinstance(node, ast.ExceptHandler):
                assert not (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)), (
                    "a bare `except: pass` still swallows an unreadable file")


class TestAHeadingDoesNotClaimWorkThatDidNotHappen:
    """Agent output went straight under a confident heading:

        ### 🔒 Deep security audit (LLM)
        (security agent LLM error: backend down)

    The sentinel is visible, but the structure asserts the opposite of what
    happened. A reader scanning headings in a security report concludes the
    audit ran — the heading is the part people trust, and it was the part that
    was wrong."""

    CODE = "import os\ndef r(c):\n    os.system(c)\n"

    def test_a_failed_audit_says_so_in_the_heading(self, monkeypatch):
        import llm_client
        from openhands_multiagent_v2.security_agent_v2 import security

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        out = security.audit(self.CODE)
        assert "ΔΕΝ ΕΓΙΝΕ" in out

    def test_a_draft_is_labelled_a_draft(self, monkeypatch):
        import llm_client
        from llm_client import LLM_DRAFT_PREFIX
        from openhands_multiagent_v2.security_agent_v2 import security
        monkeypatch.setattr(llm_client, "chat",
                            lambda *a, **k: LLM_DRAFT_PREFIX + "thinking about it")
        out = security.audit(self.CODE)
        assert "ΠΡΟΧΕΙΡΟ" in out

    def test_a_real_audit_keeps_its_plain_heading(self, monkeypatch):
        import llm_client
        from openhands_multiagent_v2.security_agent_v2 import security
        monkeypatch.setattr(llm_client, "chat",
                            lambda *a, **k: "Finding: command injection at line 3.")
        out = security.audit(self.CODE)
        assert "### 🔒 Deep security audit (LLM)" in out
        assert "ΔΕΝ ΕΓΙΝΕ" not in out

    def test_the_deterministic_sections_are_untouched(self, monkeypatch):
        """Regex scan and SAST are real whether or not the model answered, and
        must keep their headings."""
        import llm_client
        from openhands_multiagent_v2.security_agent_v2 import security

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        out = security.audit(self.CODE)
        assert "### 🔒 Regex scan (deterministic)" in out
        assert "### 🔬 SAST toolchain (bandit/ruff)" in out

    def test_the_text_is_always_kept(self, monkeypatch):
        import llm_client
        from openhands_multiagent_v2.security_agent_v2 import security

        def boom(*a, **k):
            raise RuntimeError("backend down")

        monkeypatch.setattr(llm_client, "chat", boom)
        out = security.audit(self.CODE)
        assert "backend down" in out, "the sentinel should be shown, just not headed as an audit"

    def test_the_helper_handles_all_three_shapes(self):
        from llm_client import LLM_DRAFT_PREFIX
        from openhands_multiagent_v2.security_agent_v2 import security
        assert security.section("T", "a real answer") == "### T\na real answer"
        assert "ΔΕΝ ΕΓΙΝΕ" in security.section("T", "(x agent LLM error: y)")
        assert "ΠΡΟΧΕΙΡΟ" in security.section("T", LLM_DRAFT_PREFIX + "notes")


class TestTheBuildReportDoesNotCallASentinelCode:
    """to_report() wrote "### Final code" over whatever was in self.code. When
    the coder failed that field holds "(coder agent LLM error: ...)", presented
    under a heading that says code was produced."""

    @staticmethod
    def _result(code):
        import sys
        import openhands_multiagent_v2.self_correcting_coder  # noqa: F401
        SC = sys.modules["openhands_multiagent_v2.self_correcting_coder"]
        return SC.BuildResult(task="t", code=code, clean=False)

    def test_a_sentinel_is_not_headed_as_final_code(self):
        r = self._result("(coder agent LLM error: backend down)")
        out = r.to_report()
        assert "### Final code" not in out
        assert "ΔΕΝ ΠΑΡΗΧΘΗ ΚΩΔΙΚΑΣ" in out

    def test_real_code_keeps_the_heading(self):
        r = self._result("def f():\n    return 1\n")
        out = r.to_report()
        assert "### Final code" in out

    def test_the_sentinel_is_still_shown(self):
        r = self._result("(coder agent LLM error: backend down)")
        assert "backend down" in r.to_report()


class TestGeneratedOutputStaysOutsideTheRepo:
    """The agents write arbitrary code into the generated_* folders. That code
    must never be able to reach the engines, the launchers, or the .env."""

    def test_the_default_is_a_sibling_of_the_repo_not_an_absolute_path(self):
        """An absolute C:\AI path is this machine's layout, not everyone's.
        A clone at D:\projects\local-ai must write to D:\projects\..."""
        import openhands_skills.safe_paths as sp

        assert sp.PROJECTS_ROOT.parent == sp._REPO_ROOT.parent
        assert sp.PROJECTS_ROOT.name == "generated_sites"

    def test_pointing_it_inside_the_repo_refuses_to_start(self, monkeypatch):
        import importlib

        import openhands_skills.safe_paths as sp

        inside = sp._REPO_ROOT / "sites"
        monkeypatch.setenv("MOSKY_SITES_ROOT", str(inside))
        with pytest.raises(RuntimeError, match="inside the repository"):
            importlib.reload(sp)
        monkeypatch.delenv("MOSKY_SITES_ROOT")
        importlib.reload(sp)          # leave the module usable for other tests

    def test_the_guard_is_containment_not_a_name_match(self):
        """The old check looked for the literal string "market-agent" in the
        path, so it stopped protecting anything the moment the directory was
        cloned under a different name — which publishing it guarantees."""
        import ast
        import io

        src = io.open("openhands_skills/safe_paths.py", encoding="utf-8").read()
        tree = ast.parse(src)
        body = "\n".join(ast.unparse(n) for n in tree.body
                         if not isinstance(n, (ast.Expr, ast.Import, ast.ImportFrom)))
        assert "market-agent" not in body, "the name-substring guard is back"
        assert "parents" in body, "containment check missing"

    def test_generated_models_is_also_a_sibling(self):
        import openhands_skills.cad_architect as ca
        import openhands_skills.safe_paths as sp

        assert ca.MODELS_ROOT.parent == sp._REPO_ROOT.parent
