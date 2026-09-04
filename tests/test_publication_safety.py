"""Guards on what a published copy of this repository does to a stranger.

Every test here corresponds to something that was actually wrong before the
first public release: a personal Telegram channel wired in as the default send
target, services published on every network interface with no authentication,
and a launcher that only worked if you happened to have a C:\\AI folder.

They are deliberately structural — they read the files rather than importing
them — because the failure they guard against is a line of configuration, not
a function's behaviour.
"""

import io
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def tracked():
    out = subprocess.run(["git", "-C", ROOT, "ls-files"],
                         capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f.strip()]


# --------------------------------------------------------------------------- #
# Nothing points at the author                                                 #
# --------------------------------------------------------------------------- #

class TestNoPersonalDestination:
    def test_no_hardcoded_telegram_destination(self):
        """A fresh clone that sets only a bot token used to resolve its send
        target to the author's own channel, in two separate places."""
        src = read("telegram_engine.py")
        fallback = re.compile(r"or\s+-?\d{9,}")
        assert not fallback.search(src), (
            "a numeric id is being used as a fallback destination")

    def test_a_token_without_a_destination_refuses_to_send(self):
        """Not a default — a refusal. Picking a destination for someone is how
        a stranger's briefing ends up in somebody else's channel."""
        import ast

        tree = ast.parse(read("telegram_engine.py"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "send_telegram_message")
        body = ast.unparse(fn)
        assert "if not target" in body
        # the refusal must come before the request is built
        assert body.index("if not target") < body.index("api.telegram.org")

    def test_no_tracked_file_hardcodes_a_telegram_chat_id(self):
        """Including the .bat and the scratch scripts beside it."""
        pattern = re.compile(
            r"TELEGRAM_(?:CHANNEL|CHAT)_ID\s*[=:]\s*[\"']?(-\d{9,})")
        # The one value allowed to appear: the placeholder Telegram's own docs
        # use in examples. Shape alone cannot tell a real id from a dummy, so
        # the exception is named rather than the pattern loosened.
        PLACEHOLDER = "-1001234567890"
        offenders = []
        for f in tracked():
            if not f.endswith((".py", ".bat", ".ps1", ".yml", ".yaml",
                               ".json", ".md", ".txt")):
                continue
            for found in pattern.findall(read(f)):
                if found != PLACEHOLDER:
                    offenders.append(f)
        assert offenders == [], offenders


# --------------------------------------------------------------------------- #
# Nothing is exposed to the network                                            #
# --------------------------------------------------------------------------- #

class TestServicesStayOnLoopback:
    """None of these services authenticates its caller. The OpenHands UI can
    run containers as root through the mounted docker socket; the MCP sidecar
    writes files and opens pull requests. On a shared network, publishing them
    on 0.0.0.0 hands that to everyone on it."""

    def test_compose_publishes_only_to_loopback(self):
        compose = read("docker-compose.yml")
        published = re.findall(r'^\s*-\s*"([^"]+:\d+)"\s*$', compose, re.M)
        assert published, "no published ports found - did the format change?"
        for spec in published:
            assert spec.startswith("127.0.0.1:"), (
                f"{spec} is published on every interface")

    def test_the_launcher_publishes_only_to_loopback(self):
        bat = read("start-ai.bat")
        for spec in re.findall(r"-p\s+(\S+)", bat):
            assert spec.startswith("127.0.0.1:"), (
                f"docker run -p {spec} publishes on every interface")

    def test_the_dashboard_is_not_served_to_the_network(self):
        bat = read("start-ai.bat")
        assert "streamlit run" in bat
        assert "--server.address 127.0.0.1" in bat, (
            "streamlit binds 0.0.0.0 unless told otherwise")

    def test_the_mcp_server_defaults_to_loopback(self):
        """The container passes --host 0.0.0.0 explicitly, and must: a process
        bound to a container's own loopback cannot be reached through a
        published port at all. The DEFAULT is what protects a host run."""
        import ast

        tree = ast.parse(read("openhands_mcp/server.py"))
        hosts = [kw.value.value
                 for node in ast.walk(tree) if isinstance(node, ast.Call)
                 for kw in node.keywords
                 if kw.arg == "default" and isinstance(kw.value, ast.Constant)
                 and node.args and isinstance(node.args[0], ast.Constant)
                 and node.args[0].value == "--host"]
        assert hosts == ["127.0.0.1"], hosts

    def test_the_docker_socket_mount_is_explained(self):
        """It grants root-equivalent control of the host. Someone copying this
        file needs to be told, next to the line itself."""
        compose = read("docker-compose.yml")
        i = compose.index("/var/run/docker.sock")
        preceding = compose[max(0, i - 700):i].lower()
        assert "root" in preceding, (
            "the docker.sock mount has no warning above it")


# --------------------------------------------------------------------------- #
# It runs somewhere other than this machine                                    #
# --------------------------------------------------------------------------- #

class TestItWorksFromAnyPath:
    def test_the_launcher_is_in_the_repository(self):
        """It used to be a three-line forwarder to C:\\AI\\start-ai.bat, so a
        clone got a launcher that called a file it did not have."""
        assert "start-ai.bat" in tracked()
        bat = read("start-ai.bat")
        assert len(bat.splitlines()) > 50, "still a forwarder stub"

    def test_the_launcher_derives_its_own_location(self):
        bat = read("start-ai.bat")
        assert "%~dp0" in bat
        assert not re.search(r"^set\s+(AI_ROOT|PROJECT)\s*=\s*[A-Za-z]:", bat, re.M), (
            "an absolute drive path is being assigned")

    def test_no_tracked_source_writes_to_this_machines_layout(self):
        """C:\\AI is where this happens to be checked out, not a fact about
        anyone else's disk. Comments and docs may mention it; code may not."""
        import ast

        offenders = []
        for f in tracked():
            if not f.endswith(".py"):
                continue
            try:
                tree = ast.parse(read(f))
            except SyntaxError:
                continue

            # Drop docstrings before looking. A docstring that says "C:/AI/..."
            # is documentation giving an example, which the rule above allows;
            # only a path the code actually uses is a portability bug.
            for node in ast.walk(tree):
                body = getattr(node, "body", None)
                if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                      ast.AsyncFunctionDef))
                        and body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    body.pop(0)

            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and re.match(r"^[Cc]:[\\/]+AI[\\/]", node.value)):
                    offenders.append(f"{f}: {node.value}")
        assert offenders == [], offenders

    def test_the_home_directory_is_not_written_into_config(self):
        compose = read("docker-compose.yml")
        assert "KQHEX" not in compose


# --------------------------------------------------------------------------- #
# The things a public repository must have                                     #
# --------------------------------------------------------------------------- #

class TestPublicationBasics:
    def test_there_is_a_license(self):
        """Without one, default copyright applies and nobody may legally use,
        fork or run it — which defeats the point of publishing it."""
        path = os.path.join(ROOT, "LICENSE")
        assert os.path.exists(path), "no LICENSE file"
        text = read("LICENSE")
        assert "MIT License" in text

    def test_env_example_lists_every_key_the_code_reads(self):
        """A key the code reads but the example never mentions is a setting
        nobody discovers until the feature silently does nothing."""
        import ast

        example = read(".env.example")
        wanted = set()
        for f in tracked():
            if not f.endswith(".py") or f.startswith("tests/"):
                continue
            try:
                tree = ast.parse(read(f))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and getattr(node.func, "attr", "") in ("getenv", "get")
                        and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", node.args[0].value)):
                    wanted.add(node.args[0].value)

        # Set by the launcher or the runtime, not by the user.
        internal = {"PYTHONUTF8", "PYTHONIOENCODING", "PYTHONPATH", "USERPROFILE",
                    "LOCAL_AI_UPDATE_CACHE", "MOSKY_METRICS_FILE", "MOSKY_DOC_CACHE",
                    "MOSKY_OCR_CACHE", "MOSKY_MAP_WORKERS", "MOSKY_ROUTER",
                    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_URL", "DATABASE_URL",
                    "SIGNAL_HISTORY_FILE", "OPENHANDS_WORKSPACE_BASE"}
        missing = sorted(k for k in wanted - internal
                         if not re.search(rf"^{k}=", example, re.M))
        assert missing == [], missing

    def test_env_example_contains_no_values_for_secrets(self):
        example = read(".env.example")
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID",
                    "FINNHUB_API_KEY", "TAVILY_API_KEY", "FINLIGHT_API_KEY",
                    "MORALIS_API_KEY"):
            m = re.search(rf"^{key}=(.*)$", example, re.M)
            assert m, f"{key} is not listed"
            assert m.group(1).strip() == "", f"{key} has a value in .env.example"

    def test_dotenv_is_ignored_and_untracked(self):
        assert ".env" not in tracked(), ".env is TRACKED"
        r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", ".env"])
        assert r.returncode == 0, ".env is not covered by .gitignore"


class TestThePowerShellLaunchersAreAlsoPortableAndClosed:
    """These were missed by the first pass of guards, which only read .py and
    .bat files — and they were the ones still hardcoding C:\AI\models."""

    LAUNCHERS = ["start-llama-vulkan.ps1", "start-llama-coder.ps1",
                 "start-llama-greek.ps1"]

    @pytest.mark.parametrize("name", LAUNCHERS)
    def test_no_absolute_path_is_assigned(self, name):
        for line in read(name).splitlines():
            assert not re.match(r'^\s*\$\w+\s*=\s*"[A-Za-z]:' + chr(92) + chr(92),
                                line), line.strip()

    @pytest.mark.parametrize("name", LAUNCHERS)
    def test_the_model_and_binary_are_found_relative_to_the_script(self, name):
        src = read(name)
        assert "$MyInvocation.MyCommand.Path" in src
        assert "LOCAL_AI_MODEL" in src, "no environment override documented"

    @pytest.mark.parametrize("name", LAUNCHERS)
    def test_the_inference_server_binds_loopback_by_default(self, name):
        """The endpoint has no authentication. A wider bind hands the GPU to
        everyone on the network, so it has to be asked for explicitly."""
        src = read(name)
        assert '"--host", "0.0.0.0"' not in src, "a hardcoded wide bind survives"

        # Either mechanism is fine — what matters is where it ends up. Two of
        # these take a -BindHost parameter because start-ai.bat has to widen
        # them for the container; the Greek one has no container consumer and
        # simply hardcodes loopback.
        param = re.search(r'\[string\]\$BindHost\s*=\s*"([^"]+)"', src)
        fixed = re.search(r'"--host",\s*"([\d.]+)"', src)
        default = param.group(1) if param else (fixed.group(1) if fixed else None)
        assert default == "127.0.0.1", f"{name} defaults to {default!r}"

    def test_the_only_wide_bind_is_the_one_docker_needs(self):
        """start-ai.bat passes 0.0.0.0 on purpose: a container reaches the host
        through host.docker.internal, which is not loopback. It must say so."""
        lines = read("start-ai.bat").splitlines()
        # The flag appears in its own explanatory comment too, so look for the
        # line that actually RUNS it: a non-comment line in a .bat file.
        used = [n for n, l in enumerate(lines)
                if "-BindHost 0.0.0.0" in l and not l.strip().startswith("::")]
        assert len(used) == 1, f"expected exactly one wide bind, found {len(used)}"
        above = "\n".join(lines[max(0, used[0] - 15):used[0]])
        assert "host.docker.internal" in above, (
            "the wide bind has no explanation in the lines above it")


class TestPowerShellFilesAreReadableByWindowsPowerShell:
    """Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI, not UTF-8.

    A single em-dash in a comment is then two mojibake bytes, and one of them
    can terminate a string early. That is exactly how the firewall script
    shipped broken: it looked fine in every editor and failed to parse on the
    machine it was written for.
    """

    def ps1_files(self):
        return [f for f in tracked() if f.endswith(".ps1")]

    def test_every_powershell_file_is_ascii_or_carries_a_bom(self):
        offenders = []
        for f in self.ps1_files():
            with open(os.path.join(ROOT, f), "rb") as fh:
                raw = fh.read()
            has_bom = raw[:3] == b"\xef\xbb\xbf"
            non_ascii = sum(1 for b in raw[3:] if b > 127)
            if non_ascii and not has_bom:
                offenders.append(f"{f} ({non_ascii} non-ascii bytes, no BOM)")
        assert offenders == [], offenders

    def test_they_all_actually_parse(self):
        """The real test. Ask PowerShell itself, rather than trusting the
        encoding rule above to be the only way to break one."""
        import shutil

        exe = shutil.which("powershell") or shutil.which("pwsh")
        if not exe:
            pytest.skip("no PowerShell on this machine")

        script = (
            "$bad=@(); "
            "Get-ChildItem -Path '{root}' -Filter *.ps1 -Recurse -File | ForEach-Object {{ "
            "  $e=$null; "
            "  $null=[System.Management.Automation.Language.Parser]::ParseFile("
            "$_.FullName,[ref]$null,[ref]$e); "
            "  if($e){{ $bad += $_.Name }} }}; "
            "if($bad){{ Write-Output ($bad -join ',') }}"
        ).format(root=ROOT.replace("'", "''"))

        out = subprocess.run([exe, "-NoProfile", "-Command", script],
                             capture_output=True, text=True, timeout=180)
        assert out.stdout.strip() == "", out.stdout.strip()


class TestTheAgentLauncherGivesTheModelEnoughContext:
    """llama.cpp DIVIDES the context between slots. -Parallel 2 with -Ctx 32768
    gives each request 16384 tokens, which an agent front end's system prompt
    plus tool definitions does not fit into.

    The failure is silent in the worst way: the interface sits on "Thinking"
    while the server log repeats "context window exceeded, triggering
    condensation" forever. It cost a real debugging session to find.
    """

    def test_the_canvas_launcher_uses_a_single_slot(self):
        bat = read("start-canvas.bat")
        m = re.search(r"start-llama-coder\.ps1\"?\s+-Parallel\s+(\d+)", bat)
        assert m, "the model is not started with an explicit -Parallel"
        assert m.group(1) == "1", (
            f"-Parallel {m.group(1)} splits the context {m.group(1)} ways; "
            "one user needs one slot")

    def test_the_reason_is_written_down(self):
        """Someone raising this later needs to know what it breaks."""
        lines = read("start-canvas.bat").splitlines()
        # The flag appears in its own explanatory comment, so find the line
        # that RUNS it — the same trap this file's -BindHost guard fell into.
        used = [n for n, l in enumerate(lines)
                if "-Parallel 1" in l and not l.strip().startswith("::")]
        assert len(used) == 1, f"expected one model start, found {len(used)}"
        above = "\n".join(lines[max(0, used[0] - 20):used[0]]).lower()
        assert "context" in above and "slot" in above, (
            "the -Parallel choice has no explanation above it")


class TestExpertOffloadDefaultsAreTheMeasuredOnes:
    """The MoE launchers' defaults were chosen from measurements taken on
    2026-09-05 (scripts/bench_moe.py), recorded in start-llama-coder.ps1.

    The coding model keeps its experts in system RAM by default: 4.7 GB of
    video memory instead of 15.4, at the cost of generation speed. The market
    model does NOT, because that launcher runs the briefings and the setting
    was never measured on it. These tests keep the defaults where the data put
    them, so a well-meaning flip in either direction has to bring a number.
    """

    def _default(self, name, switch):
        src = read(name)
        m = re.search(r"\[switch\]\$" + switch + r"\s*=\s*\$(true|false)", src)
        assert m, f"{name}: no [switch]${switch} default found"
        return m.group(1)

    def test_the_coding_launcher_keeps_experts_in_ram_by_default(self):
        assert self._default("start-llama-coder.ps1", "CpuMoe") == "true"

    def test_the_market_launcher_does_not_until_it_is_measured(self):
        assert self._default("start-llama-vulkan.ps1", "CpuMoe") == "false"

    @pytest.mark.parametrize("name", ["start-llama-coder.ps1", "start-llama-vulkan.ps1"])
    def test_both_launchers_pass_the_flag_when_asked(self, name):
        src = read(name)
        assert "--cpu-moe" in src, "the switch exists but never reaches llama-server"
        assert "--n-cpu-moe" in src, "the -NCpuMoe middle ground is missing"
        # the middle ground must take precedence, or -NCpuMoe silently does nothing
        i_n = src.index('"--n-cpu-moe"')
        i_all = src.index('"--cpu-moe"')
        assert i_n < i_all, "-NCpuMoe must be checked before -CpuMoe"

    def test_the_measurements_are_written_next_to_the_default(self):
        """A default without its numbers is a guess. The table has to live in
        the launcher, where the next person changing it will actually look."""
        src = read("start-llama-coder.ps1")
        for token in ("4.69 GB", "22.3 t/s", "15.43 GB", "39.2 t/s", "bench_moe.py"):
            assert token in src, f"measurement {token!r} missing from the launcher"

    def test_the_split_configuration_carries_its_warning(self):
        """The machine hard-reset seconds after a -NCpuMoe 24 benchmark. Not
        proven to be the cause, but nobody should make it the default without
        reading that."""
        src = read("start-llama-coder.ps1")
        assert "hard-reset" in src and "-NCpuMoe" in src
