"""Point Agent Canvas / OpenHands at the local tool server WITH the bearer
token it now requires, and turn their analytics consent off.

    python scripts/canvas_mcp_config.py [--port 8765]

Writes (merging, never clobbering other entries):
  %USERPROFILE%\\.openhands\\plugins\\local-tools\\.mcp.json
      mcpServers.local-tools = {transport: streamable-http, url, headers}
  %USERPROFILE%\\.openhands-v1\\settings.json   (only if it exists)
      user_consents_to_analytics = false
      (MEASURED 2026-09-11: it was true, and the OpenHands v1 UI fires
      PostHog events while it is)

The token comes from MCP_TOKEN or the file next to the Canvas session key
(lpai_private.mcp_token). Safe to run at every start.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lpai_private  # noqa: E402


def _merge_json(path: Path, mutate) -> str:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except ValueError:
            backup = path.with_suffix(path.suffix + ".broken")
            path.replace(backup)
            data = {}
    before = json.dumps(data, sort_keys=True)
    mutate(data)
    after = json.dumps(data, sort_keys=True)
    if before == after:
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "written"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv)
    token = lpai_private.mcp_token(create=True)
    if not token:
        print("[canvas config] no MCP token could be read or minted", file=sys.stderr)
        return 1
    home = Path(os.path.expanduser("~"))

    def plugin(d):
        servers = d.setdefault("mcpServers", {})
        entry = servers.setdefault("local-tools", {})
        entry["transport"] = "streamable-http"
        entry["url"] = f"http://{a.host}:{a.port}/mcp"
        entry["headers"] = {"Authorization": f"Bearer {token}"}
    r1 = _merge_json(home / ".openhands" / "plugins" / "local-tools" / ".mcp.json", plugin)
    print(f"[canvas config] local-tools plugin with bearer token: {r1}")

    v1 = home / ".openhands-v1" / "settings.json"
    if v1.is_file():
        r2 = _merge_json(v1, lambda d: d.__setitem__("user_consents_to_analytics", False))
        print(f"[canvas config] OpenHands v1 analytics consent off: {r2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
