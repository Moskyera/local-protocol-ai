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


def _read_file(args: dict) -> str:
    p = Path(os.path.expanduser(str(args.get("path", "")))).resolve()
    if not p.is_file():
        return f"(not a file: {p})"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"(could not read: {type(e).__name__})"
    n = int(args.get("max_chars", 6000))
    return text[:n] + (f"\n…({len(text) - n} more characters)" if len(text) > n else "")


def _list_folder(args: dict) -> str:
    p = Path(os.path.expanduser(str(args.get("path", ".")))).resolve()
    if not p.is_dir():
        return f"(not a folder: {p})"
    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))[:200]
    return "\n".join(("📁 " if x.is_dir() else "📄 ") + x.name for x in items) or "(empty)"


def _write_note(args: dict) -> str:
    notes = config.REPO / "memory" / "voice_notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with notes.open("a", encoding="utf-8") as fh:
        fh.write(f"\n- [{stamp}] {str(args.get('text', '')).strip()}\n")
    return f"saved to {notes}"


def _open_path(args: dict) -> str:
    target = os.path.expanduser(str(args.get("path", "")))
    try:
        os.startfile(target)          # Windows: file, folder, URL or app
        return f"opened {target}"
    except Exception as e:
        return f"(could not open {target}: {e})"


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
    Tool("write_note", "Save a note the owner dictated, to memory/voice_notes.md.",
         {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
         Risk.RISKY, _write_note),
    Tool("open_path", "Open a file, folder, application or URL with its default program.",
         {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
         Risk.RISKY, _open_path),
    Tool("run_command", "Run a PowerShell command on this machine. Use only when no other tool fits.",
         {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
          "required": ["command"]}, Risk.DESTRUCTIVE, _run_command),
]


# --------------------------------------------------------------------------- #
# MCP tools, discovered live from the server
# --------------------------------------------------------------------------- #

def _mcp_runner(name: str) -> Callable[[dict], str]:
    def run(args: dict) -> str:
        async def call():
            from fastmcp import Client
            async with Client(config.MCP_URL) as c:
                r = await c.call_tool(name, args)
                parts = []
                for item in (r.content or []):
                    t = getattr(item, "text", None)
                    parts.append(t if t is not None else str(item))
                return "\n".join(parts) if parts else "(no result)"
        try:
            return asyncio.run(call())[:8000]
        except Exception as e:
            return f"(tool {name} failed: {type(e).__name__}: {str(e)[:200]})"
    return run


def discover_mcp_tools() -> tuple[list[Tool], Optional[str]]:
    """Returns (tools, error). Never raises: a dead server is a reportable
    fact, not a crash."""
    async def fetch():
        from fastmcp import Client
        async with Client(config.MCP_URL) as c:
            return await c.list_tools()
    try:
        raw = asyncio.run(asyncio.wait_for(fetch(), timeout=config.MCP_CONNECT_TIMEOUT_S))
    except Exception as e:
        return [], f"{type(e).__name__}: {str(e)[:120]}"
    tools = []
    for t in raw:
        params = t.inputSchema or {"type": "object", "properties": {}}
        # models are given a short description; the full one wastes context
        desc = (t.description or "").strip().split("\n")[0][:220]
        tools.append(Tool(t.name, desc, params, classify(t.name), _mcp_runner(t.name), source="mcp"))
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
            for t in mcp:
                reg.tools.setdefault(t.name, t)
        return reg

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def summary(self) -> str:
        by = {r: [] for r in Risk}
        for t in self.tools.values():
            by[t.risk].append(t.name)
        return (f"{len(self.tools)} tools: {len(by[Risk.SAFE])} safe, "
                f"{len(by[Risk.RISKY])} announced, {len(by[Risk.DESTRUCTIVE])} need confirmation")
