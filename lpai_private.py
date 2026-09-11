"""PRIVATE MODE: nothing this stack runs may send data off the machine.

One switch, LPAI_PRIVATE, honoured in-process. Private is the DEFAULT; the
only way out is an explicit LPAI_PRIVATE=0. Three things happen here:

  apply_env()             The telemetry kill-switches every library reads,
                          assigned (not defaulted) before the library loads,
                          so a line in .env cannot undo them.
  install_egress_guard()  A guard on the three places a Python process can
                          open a network connection - name resolution, the
                          socket connect, and asyncio's Windows Proactor
                          connect - that lets loopback through and refuses
                          everything else with a clear error. This is the
                          honest floor: the stack's own code cannot reach the
                          internet by accident, whatever a library or a
                          model-chosen URL asks for.
  require_local_endpoint  The model endpoint must be local unless the owner
                          says otherwise (LPAI_ALLOW_REMOTE_LLM=1).

What this CANNOT do: reach child processes (PowerShell, node, Docker, WSL),
the browser, or Windows itself. scripts/private-firewall.ps1 covers the
programs; docs/PRIVACY.md says the rest out loud.

MEASURED 2026-09-11 on this box (Windows 11, CPython 3.14): on Windows the
Proactor event loop connects literal IPs through loop.sock_connect and
never calls socket.connect, so the third hook is required; with all three,
asyncio.open_connection, urllib, requests and httpx were all stopped for a
hostname at name resolution while loopback kept working; a blanket
connect-raise breaks asyncio's own socketpair, so loopback MUST stay open.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import sys
from typing import Iterable, Optional


class EgressBlocked(OSError):
    """Raised in place of a network connection that would leave the machine."""


def is_private() -> bool:
    return os.getenv("LPAI_PRIVATE", "1").strip().lower() not in ("0", "false", "no", "off")


# The names are the ones the installed packages actually read (verified
# against site-packages, not memory): huggingface_hub, gradio, streamlit,
# litellm, chromadb, browser-use, OpenHands agent-canvas, our updater.
PRIVATE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "DO_NOT_TRACK": "1",
    "VITE_DO_NOT_TRACK": "1",
    "GRADIO_ANALYTICS_ENABLED": "False",
    "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
    "LITELLM_TELEMETRY": "False",
    "ANONYMIZED_TELEMETRY": "false",
    "BROWSER_USE_CLOUD_SYNC": "false",
    "OH_TELEMETRY_EXPORTER": "none",
    "OH_TELEMETRY_CONSENT": "denied",
    "OH_TELEMETRY_CONSENT_MODE": "override",
    "LOCAL_AI_UPDATE_CHECK": "0",
}

# The MCP tools that send the owner's words or data to external hosts.
# One list, shared by the server (which withholds them) and the voice
# assistant (which announces them when allowed). x_* search and
# consult_wealth_mentor were measured inert and are not here.
EGRESS_TOOLS = frozenset({
    "web_research", "safe_web_research", "research", "research_last_30_days_broad",
    "run_scheduled_proactive_research", "scan_and_research_large_ecosystem_movements",
    "scan_large_ecosystem_movements_on_pulsechain", "check_large_ecosystem_movements",
    "analyze_wallet", "fetch_full_wallet_profile", "get_market_context", "create_pr",
    "mcp_github_context",
})

_LOCAL_NAMES = {"localhost", "localhost.", "127.0.0.1", "::1", "0.0.0.0", "::", ""}


def apply_env() -> None:
    """Set every kill-switch. Assignment, not setdefault: a .env line or an
    inherited shell variable must not switch telemetry back on."""
    if not is_private():
        return
    for k, v in PRIVATE_ENV.items():
        os.environ[k] = v


def allowed_hosts() -> set[str]:
    """Loopback plus what the launcher allowed (the WSL adapter IP for the
    sandbox, host.docker.internal inside a container)."""
    extra = {h.strip().lower() for h in os.getenv("LPAI_ALLOW_HOSTS", "").split(",") if h.strip()}
    return _LOCAL_NAMES | extra


def _is_local_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    h = str(host).strip().lower().rstrip(".")
    if h in allowed_hosts():
        return True
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    try:
        ip = ipaddress.ip_address(h.split("%")[0])
    except ValueError:
        return False                       # a name that is not on the list
    return ip.is_loopback or ip.is_unspecified


_installed = False
_reported: set[str] = set()


def _refuse(host) -> None:
    key = str(host)
    if key not in _reported:
        _reported.add(key)
        print(f"[private mode] blocked a connection to {key}: not local. "
              f"Set LPAI_PRIVATE=0 to allow the internet, or LPAI_ALLOW_HOSTS to allow this host.",
              file=sys.stderr, flush=True)
    raise EgressBlocked(f"private mode: {key} is not local")


def install_egress_guard() -> bool:
    """Wrap the three connection points. Idempotent. Returns True if
    installed, False when private mode is off."""
    global _installed
    if not is_private():
        return False
    if _installed:
        return True

    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if not _is_local_host(host):
            _refuse(host)
        return real_getaddrinfo(host, port, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo

    def _check_address(address) -> None:
        if isinstance(address, (tuple, list)) and address:
            if not _is_local_host(address[0]):
                _refuse(address[0])
        # AF_UNIX paths and anything else are local by construction

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def connect(self, address):
        _check_address(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        _check_address(address)
        return real_connect_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex

    try:
        import asyncio.proactor_events as pe
        real_sock_connect = pe.BaseProactorEventLoop.sock_connect

        async def sock_connect(self, sock, address):
            _check_address(address)
            return await real_sock_connect(self, sock, address)

        pe.BaseProactorEventLoop.sock_connect = sock_connect
    except Exception:                       # not Windows: the socket hook covers it
        pass

    _installed = True
    return True


def require_local_endpoint(url: str, what: str = "the model endpoint") -> str:
    """A URL for the model server must point at this machine unless the
    owner explicitly allows a remote model (LPAI_ALLOW_REMOTE_LLM=1)."""
    from urllib.parse import urlparse
    if os.getenv("LPAI_ALLOW_REMOTE_LLM", "0").strip().lower() in ("1", "true", "yes"):
        return url
    host = urlparse(url).hostname
    if host is None or _is_local_host(host):
        return url
    raise ValueError(f"private mode: {what} {url} is not on this machine. "
                     f"Set LPAI_ALLOW_REMOTE_LLM=1 only if you mean to send every prompt there.")


def disable_library_telemetry() -> None:
    """Runtime switches for libraries that do not read an env var."""
    try:
        import onnxruntime as ort
        ort.disable_telemetry_events()
    except Exception:
        pass


def mcp_token(create: bool = False) -> Optional[str]:
    """The bearer token the MCP tool server requires and its local clients
    send. MCP_TOKEN in the environment wins; otherwise the file next to the
    Agent Canvas session key (owner-only directory). `create` mints one."""
    env = os.getenv("MCP_TOKEN", "").strip()
    if env:
        return env
    from pathlib import Path
    path = Path(os.getenv("MCP_TOKEN_FILE") or (Path.home() / ".openhands" / "agent-canvas" / "mcp-token.txt"))
    try:
        if path.is_file():
            tok = path.read_text(encoding="utf-8").strip()
            if tok:
                return tok
        if create:
            import secrets
            tok = secrets.token_urlsafe(32)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(tok, encoding="utf-8")
            return tok
    except OSError:
        return None
    return None


def egress_tool_error(name: str) -> dict:
    return {"error": f"private mode: {name} sends data to external hosts and is disabled. "
                     f"Set LPAI_PRIVATE=0 to allow it.", "mcp_tool": name, "private_mode": True}


def activate(extra_hosts: Optional[Iterable[str]] = None) -> bool:
    """apply_env + install_egress_guard + disable_library_telemetry. Call
    this first, before importing anything that opens sockets."""
    if extra_hosts:
        os.environ["LPAI_ALLOW_HOSTS"] = ",".join(
            [h for h in os.getenv("LPAI_ALLOW_HOSTS", "").split(",") if h] + list(extra_hosts))
    apply_env()
    disable_library_telemetry()
    return install_egress_guard()
