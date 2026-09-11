"""What the agent can DO: the MCP tools on :8765 plus a few local ones.

Every tool is exposed to the model as an OpenAI-style function schema and
carries a risk class from guard.py. The registry is built once at start; if
the MCP server is down the agent says so and runs with the local tools only,
rather than pretending the 35 remote ones exist.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import config
from .guard import Risk, classify


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    risk: Risk
    run: Callable[[dict], str]           # returns text the model will read
    source: str = "local"

    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}


# --------------------------------------------------------------------------- #
# Local tools. Small, honest, and each returns what actually happened.
# --------------------------------------------------------------------------- #

def _current_time(args: dict) -> str:
    now = _dt.datetime.now()
    return now.strftime("%A %d %B %Y, %H:%M")


def _read_clipboard(args: dict) -> str:
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                             capture_output=True, text=True, timeout=10).stdout
        return out.strip()[:4000] or "(clipboard is empty)"
    except Exception as e:
        return f"(could not read clipboard: {type(e).__name__})"


# What the voice assistant may read. The model chooses the path, and the
# model reads what it is told by tool output (P-19), so the reachable set
# must be small: the repo and the owner's Documents by default, and never
# a secrets file by name.
_SECRET_NAMES = re.compile(r"^(\.env.*|.*\.key|.*\.pem|id_[a-z0-9]+|hosts\.yml|api-key\.txt|secret-key\.txt|"
                           r"secrets\.json|mcp-token\.txt|.*\.pfx|.*\.p12|credentials.*|token.*\.txt)$", re.I)


def _read_roots() -> list[Path]:
    raw = config._env("VOICE_READ_ROOTS")
    if raw:
        return [Path(os.path.expanduser(x.strip())).resolve() for x in raw.split(",") if x.strip()]
    return [config.REPO.resolve(), (Path.home() / "Documents").resolve()]


def _refused(p: Path) -> Optional[str]:
    if _SECRET_NAMES.match(p.name):
        return f"(refused: {p.name} looks like a secrets file; the assistant never reads those)"
    roots = _read_roots()
    if not any(p == r or r in p.parents for r in roots):
        return (f"(refused: {p} is outside the folders the assistant may read: "
                + ", ".join(str(r) for r in roots) + ". Set VOICE_READ_ROOTS to change that)")
    return None


def _read_file(args: dict) -> str:
    p = Path(os.path.expanduser(str(args.get("path", "")))).resolve()
    why = _refused(p)
    if why:
        return why
    if not p.is_file():
        return f"(not a file: {p})"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"(could not read: {type(e).__name__})"
    n = min(int(args.get("max_chars", 6000)), config.TOOL_RESULT_MAX_CHARS)
    return text[:n] + (f"\n…({len(text) - n} more characters)" if len(text) > n else "")


def _list_folder(args: dict) -> str:
    p = Path(os.path.expanduser(str(args.get("path", ".")))).resolve()
    why = _refused(p)
    if why:
        return why
    if not p.is_dir():
        return f"(not a folder: {p})"
    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))[:200]
    return "\n".join(("📁 " if x.is_dir() else "📄 ") + x.name for x in items) or "(empty)"


def _write_note(args: dict) -> str:
    notes = config.NOTES_FILE
    notes.parent.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with notes.open("a", encoding="utf-8") as fh:
        fh.write(f"\n- [{stamp}] {str(args.get('text', '')).strip()}\n")
    return f"saved to {notes}"


# MEASURED 2026-09-11: os.startfile on a .bat ran it exactly like a double
# click, and open_path is RISKY (announce, then run), so a script reached this
# way skipped the spoken gate that run_command has. Anything Windows would
# EXECUTE rather than display is refused here and pointed at run_command.
# The list is PATHEXT on this machine plus shortcuts, installers, registry
# and control-panel files; a full path to an .exe counts too. An installed
# application BY NAME ("notepad", "chrome") is still an app launch, which
# guard.py classes as reversible.
_LAUNCH_SUFFIXES = {
    ".com", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh", ".msc",
    ".lnk", ".url", ".pif", ".scf", ".reg", ".cpl", ".msi", ".msp", ".hta", ".jar",
    ".py", ".pyw", ".pyz", ".ps1", ".inf", ".application", ".appref-ms", ".exe", ".scr",
}


def _would_execute(target: str) -> Optional[str]:
    """Why open_path must not touch this target, or None if it is fine."""
    from urllib.parse import urlparse
    t = target.strip()
    scheme = urlparse(t).scheme.lower()
    if len(scheme) > 1:                      # a one-letter scheme is a drive
        if scheme in ("http", "https"):
            return "a web link, and private mode is on (a browser request leaves the machine)" if config.PRIVATE else None
        return f"{scheme}: links are not opened"
    suffix = Path(t.rstrip(" .")).suffix.lower()
    if suffix in _LAUNCH_SUFFIXES:
        bare_app = suffix == ".exe" and not any(sep in t for sep in ("/", chr(92)))
        if not bare_app:
            return "a script, shortcut, installer or executable"
    return None


def _open_path(args: dict) -> str:
    target = os.path.expanduser(str(args.get("path", "")))
    why = _would_execute(target)
    if why:
        return (f"(refused: {target} is {why}; open_path only displays things. "
                f"To RUN it use run_command, which asks the owner first)")
    try:
        os.startfile(target)          # Windows: document, folder, URL or app by name
        return f"opened {target}"
    except Exception as e:
        return f"(could not open {target}: {e})"


def _read_notes(args: dict) -> str:
    """The NEWEST notes. MEASURED: read_file returned the first 6000 chars,
    i.e. the oldest, once the file passed ~70 notes."""
    n = max(1, min(int(args.get("last_n", 10)), 100))
    if not config.NOTES_FILE.is_file():
        return "(no notes yet)"
    lines = [l.rstrip() for l in config.NOTES_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
             if l.startswith("- [")]
    return "\n".join(lines[-n:]) or "(no notes yet)"


def _recall(args: dict) -> str:
    """What was said in earlier sessions, from the per-turn log: compact
    'HH:MM εσύ: … / εγώ: …' lines, newest last, capped at 3000 chars."""
    query = str(args.get("query", "")).strip().lower()
    days = max(1, min(int(args.get("days", 1)), 90))
    last_n = max(1, min(int(args.get("last_n", 20)), 200))
    if not config.LOG_FILE.is_file():
        return "(no log yet)"
    cutoff = (_dt.datetime.now() - _dt.timedelta(days=days)).isoformat(timespec="minutes")
    rows = []
    for line in config.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("when", "") < cutoff or not d.get("heard"):
            continue
        text = f"{d['when'][11:16]} εσύ: {d['heard']} / εγώ: {d.get('final') or ''}"
        if query and query not in text.lower():
            continue
        rows.append(text)
    out = "\n".join(rows[-last_n:]) or "(nothing matching)"
    return out[-3000:]


def _get_system_status(args: dict) -> str:
    """Read-only facts about this machine and the stack, no shell command.
    MEASURED: without it the model asserted 'the MCP server is running'
    without checking, or asked to run a command for it."""
    import shutil, socket, urllib.request
    lines = []
    try:
        with urllib.request.urlopen(config.LLM_BASE_URL + "/models", timeout=2) as r:
            data = json.load(r)
        names = [m.get("id") or m.get("name") for m in (data.get("data") or data.get("models") or [])]
        lines.append(f"model server: up ({', '.join(str(n) for n in names[:3]) or 'unknown model'})")
    except Exception:
        lines.append("model server: DOWN")
    try:
        host, port = config.MCP_URL.split("//", 1)[1].split("/", 1)[0].split(":")
        with socket.create_connection((host, int(port)), timeout=1):
            lines.append("MCP tool server: up")
    except Exception:
        lines.append("MCP tool server: DOWN")
    try:
        du = shutil.disk_usage(str(config.REPO))
        lines.append(f"disk free: {du.free / 1e9:.0f} of {du.total / 1e9:.0f} GB")
    except Exception:
        pass
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "$o=Get-CimInstance Win32_OperatingSystem; '{0:N1} {1:N1}' -f (($o.TotalVisibleMemorySize-$o.FreePhysicalMemory)/1MB),($o.TotalVisibleMemorySize/1MB)"],
                           capture_output=True, text=True, timeout=8)
        used, total = r.stdout.split()
        lines.append(f"RAM used: {used} of {total} GB")
    except Exception:
        pass
    if args.get("include_gpu"):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "((Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage').CounterSamples | Measure-Object CookedValue -Sum).Sum/1GB"],
                               capture_output=True, text=True, timeout=10)
            lines.append(f"VRAM in use: {float(r.stdout.strip().replace(',', '.')):.1f} GB")
        except Exception:
            lines.append("VRAM: could not read")
    lines.append(f"private mode: {'ON (no tool reaches the internet)' if config.PRIVATE else 'OFF'}")
    return "\n".join(lines)


def _run_command(args: dict) -> str:
    """DESTRUCTIVE by class: the gate has already had the owner confirm."""
    cmd = str(args.get("command", "")).strip()
    if not cmd:
        return "(empty command)"
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=int(args.get("timeout", 60)))
        out = (r.stdout + r.stderr).strip()
        return f"exit {r.returncode}\n{out[:4000]}" if out else f"exit {r.returncode} (no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(failed: {type(e).__name__}: {e})"


LOCAL_TOOLS: list[Tool] = [
    Tool("current_time", "The current local date and time.",
         {"type": "object", "properties": {}}, Risk.SAFE, _current_time),
    Tool("read_clipboard", "Read the text currently in the Windows clipboard.",
         {"type": "object", "properties": {}}, Risk.SAFE, _read_clipboard),
    Tool("read_file", "Read a text file from disk.",
         {"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}},
          "required": ["path"]}, Risk.SAFE, _read_file),
    Tool("list_folder", "List the files and folders in a directory.",
         {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
         Risk.SAFE, _list_folder),
    Tool("write_note", "Save a note the owner dictated. Read them back with read_notes.",
         {"type": "object", "properties": {"text": {"type": "string", "description": "the note, as dictated"}}, "required": ["text"]},
         Risk.RISKY, _write_note),
    Tool("read_notes", "The owner's newest dictated notes.",
         {"type": "object", "properties": {"last_n": {"type": "integer", "description": "how many, newest last; default 10"}}},
         Risk.SAFE, _read_notes),
    Tool("recall", "What the owner and you said in earlier sessions (the log), newest last.",
         {"type": "object", "properties": {"query": {"type": "string", "description": "a word to look for; empty = everything"},
                                           "days": {"type": "integer", "description": "how far back; default 1"},
                                           "last_n": {"type": "integer", "description": "at most this many turns; default 20"}}},
         Risk.SAFE, _recall),
    Tool("get_system_status", "Is the model server up, is the tool server up, free disk, RAM in use, private mode. "
                              "include_gpu adds VRAM (+1.5 s).",
         {"type": "object", "properties": {"include_gpu": {"type": "boolean"}}}, Risk.SAFE, _get_system_status),
    Tool("open_path", "Open a document, folder, installed application (by name) or web link. "
                      "Never for scripts, installers or executables: use run_command.",
         {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
         Risk.RISKY, _open_path),
    Tool("run_command", "Run a PowerShell command on this machine. Use only when no other tool fits.",
         {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
          "required": ["command"]}, Risk.DESTRUCTIVE, _run_command),
]


# --------------------------------------------------------------------------- #
# MCP tools, discovered live from the server
# --------------------------------------------------------------------------- #

def _mcp_runner(name: str, confirm_flag: bool = False) -> Callable[[dict], str]:
    def run(args: dict) -> str:
        if confirm_flag:
            # the spoken gate already ran; the server's own yes/no protocol
            # would otherwise ask the MODEL "Do you approve?" in English
            args = {**args, "user_confirmed": True}
        async def call():
            from fastmcp import Client
            async with Client(config.MCP_URL, auth=config.MCP_TOKEN) as c:
                r = await c.call_tool(name, args)
                parts = []
                for item in (r.content or []):
                    t = getattr(item, "text", None)
                    parts.append(t if t is not None else str(item))
                return "\n".join(parts) if parts else "(no result)"
        try:
            return asyncio.run(asyncio.wait_for(call(), timeout=config.MCP_CALL_TIMEOUT_S))
        except asyncio.TimeoutError:
            return f"(tool {name} timed out after {config.MCP_CALL_TIMEOUT_S} s; nothing more will come)"
        except Exception as e:
            return f"(tool {name} failed: {type(e).__name__}: {str(e)[:200]})"
    return run


def clamp_result(text: str) -> str:
    """The model must never see a fragment without knowing it is one: a
    result cut silently at 8000 chars read like a complete file."""
    n = config.TOOL_RESULT_MAX_CHARS
    if len(text) <= n:
        return text
    return text[:n] + f"\n(κόπηκε· άλλοι {len(text) - n} χαρακτήρες / truncated, {len(text) - n} more characters)"


# --------------------------------------------------------------------------- #
# How the 35 MCP tools look by VOICE. MEASURED: the server's descriptions
# arrive as one truncated line ('Post-apply evaluation helper.', "The key
# 'make the closed loop real' tool."), 31 of 42 tools had parameters with
# no description, x_* search returns stubs, research_last_30_days_broad
# ignores its topic, and 19 proposal/PR/supervisor/lab tools cost ~1960
# schema tokens per turn while being useless spoken. So: a sentence per
# tool in the assistant's words, a description per parameter, the
# machinery hidden, and the tools that leave the machine marked EGRESS.
# --------------------------------------------------------------------------- #
VOICE_HIDDEN = {
    "create_pr", "propose_blockchain_improvements_from_lab", "integrate_research_idea", "mcp_github_context",
    "supervise", "apply_proposal", "rollback_proposal", "evaluate_and_rollback_if_degraded",
    "list_pending_proposals", "get_proposal_details", "approve_and_apply_proposal",
    "improve_the_blockchain_expert", "run_scheduled_proactive_research", "get_research_lab_ideas",
    "get_meta_learnings", "fix_tool_call_error", "execute_v2_task", "x_thread_fetch",
    "x_semantic_search", "x_keyword_search",          # stubs: return no real posts
    "research_last_30_days_broad",                    # ignores its topic argument
    "safe_web_research",                              # duplicate of web_research
}
VOICE_EGRESS = {
    "analyze_wallet", "fetch_full_wallet_profile", "check_large_ecosystem_movements",
    "scan_large_ecosystem_movements_on_pulsechain", "scan_and_research_large_ecosystem_movements",
    "get_market_context", "research", "web_research",
}
VOICE_DESCRIPTIONS = {
    "analyze_wallet": ("Forensics of one PulseChain wallet address: holdings, activity, risk. Sends the address to a blockchain data service.",
                       {"address": "the 0x… wallet address", "chain": "chain name, default pulsechain"}),
    "fetch_full_wallet_profile": ("Raw token activity and profit/loss of one PulseChain wallet. Sends the address to a blockchain data service.",
                                  {"address": "the 0x… wallet address", "chain": "chain name, default pulsechain"}),
    "check_large_ecosystem_movements": ("Large recent moves of key PulseChain tokens for one address.",
                                        {"address": "the 0x… wallet address", "min_usd": "ignore moves below this USD value"}),
    "scan_large_ecosystem_movements_on_pulsechain": ("Scan PulseChain for recent large HEX, PLSX and INC movements; no address needed.",
                                                     {"tokens": "token symbols to watch", "min_usd": "ignore moves below this USD value"}),
    "scan_and_research_large_ecosystem_movements": ("The same scan plus a short explanation of the moves.",
                                                    {"tokens": "token symbols to watch", "min_usd": "ignore moves below this USD value"}),
    "get_market_context": ("A snapshot of the owner's watchlist: crypto prices, sentiment, macro. Returns the whole watchlist; the symbol argument is ignored.",
                           {"symbol": "ignored"}),
    "research": ("Searches GitHub repositories and arXiv papers about AI AGENTS only. Not a general web search; not for news, weather or prices.",
                 {"query": "what to look for, in English", "focus": "leave empty"}),
    "web_research": ("Fetch ONE known web page by its URL and answer a question about it. Needs the exact URL; not a search engine.",
                     {"url": "the full http(s) address", "query": "the question to answer from that page", "max_chars": "leave empty"}),
    "analyze_folder": ("Review a whole folder of code on this machine: what is right and what is wrong.",
                       {"path": "the folder", "max_files": "leave empty", "deep": "leave empty"}),
    "get_system_evaluation": ("Health score of this AI stack from its own evaluation harness. Rate-limited: once a minute.", {}),
    "generate_image": ("Make an image with the local ComfyUI; it must be running.", {"prompt": "what to draw, in English"}),
    "generate_video": ("Make a short video with the local ComfyUI; it must be running.", {"prompt": "what to show, in English"}),
    "consult_wealth_mentor": ("Practical money and business advice from the local wealth-mentor knowledge base.",
                              {"prompt": "the question", "context": "leave empty"}),
}


def _voice_schema(t, params: dict) -> dict:
    """The parameter schema the model sees: descriptions added, the
    user_confirmed flag removed (the spoken gate is the confirmation)."""
    props = dict(params.get("properties") or {})
    props.pop("user_confirmed", None)
    helps = VOICE_DESCRIPTIONS.get(t.name, ("", {}))[1]
    for k, v in props.items():
        if isinstance(v, dict) and k in helps and "description" not in v:
            props[k] = {**v, "description": helps[k]}
    out = {k: v for k, v in params.items() if k != "properties"}
    out["properties"] = props
    out["required"] = [r for r in (params.get("required") or []) if r != "user_confirmed"]
    return out


def discover_mcp_tools(for_voice: bool = True) -> tuple[list[Tool], Optional[str]]:
    """Returns (tools, error). Never raises: a dead server is a reportable
    fact, not a crash. for_voice: hide the machinery, describe honestly,
    mark egress, strip user_confirmed."""
    async def fetch():
        from fastmcp import Client
        async with Client(config.MCP_URL, auth=config.MCP_TOKEN) as c:
            return await c.list_tools()
    try:
        raw = asyncio.run(asyncio.wait_for(fetch(), timeout=config.MCP_CONNECT_TIMEOUT_S))
    except Exception as e:
        return [], f"{type(e).__name__}: {str(e)[:120]}"
    tools = []
    for t in raw:
        params = t.inputSchema or {"type": "object", "properties": {}}
        desc = (t.description or "").strip().split("\n")[0][:220]
        risk = classify(t.name)
        confirm_flag = "user_confirmed" in (params.get("properties") or {})
        if for_voice:
            if t.name in VOICE_HIDDEN:
                continue
            desc = VOICE_DESCRIPTIONS.get(t.name, (desc, {}))[0]
            params = _voice_schema(t, params)
            if t.name in VOICE_EGRESS:
                risk = Risk.EGRESS
            elif confirm_flag and risk is Risk.SAFE:
                risk = Risk.RISKY          # the server wanted a confirmation: at least announce
        tools.append(Tool(t.name, desc, params, risk, _mcp_runner(t.name, confirm_flag), source="mcp"))
    return tools, None


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)
    mcp_error: Optional[str] = None

    @classmethod
    def build(cls, with_mcp: bool = True) -> "Registry":
        reg = cls()
        for t in LOCAL_TOOLS:
            reg.tools[t.name] = t
        if with_mcp:
            mcp, err = discover_mcp_tools()
            reg.mcp_error = err
            reg.add_mcp(mcp)
        return reg

    def add_mcp(self, mcp: list[Tool]) -> int:
        """Merge discovered MCP tools, honouring private mode. Builds a new
        dict and swaps it, so a turn iterating schemas() is never bitten."""
        new = dict(self.tools)
        n = 0
        for t in mcp:
            if config.PRIVATE and t.risk is Risk.EGRESS:
                continue
            if t.name not in new:
                new[t.name] = t; n += 1
        self.tools = new
        return n

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def summary(self) -> str:
        by = {r: [] for r in Risk}
        for t in self.tools.values():
            by[t.risk].append(t.name)
        return (f"{len(self.tools)} tools: {len(by[Risk.SAFE])} safe, "
                f"{len(by[Risk.RISKY])} announced, {len(by[Risk.EGRESS])} reach the internet, "
                f"{len(by[Risk.DESTRUCTIVE])} need confirmation"
                + (" | private mode" if config.PRIVATE else ""))
