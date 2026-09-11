"""
configure-openhands-v1.py — points OpenHands v1 at the local llama.cpp backend
and at the MOSKY MCP skills sidecar.

WHY A SCRIPT: v1 settings are NOT the v0 settings.json format. They live under
`agent_settings` and the API refuses plain keys:
    422 "Use *_diff nested settings payloads instead of legacy keys"
so the payload must be {"agent_settings_diff": {...}}. MCP also moved to the
canonical {"mcpServers": {...}} shape. Doing this by hand is error-prone, and it
must re-run every time you switch model (market <-> coding).

Usage:
    python configure-openhands-v1.py <model-alias> [--port 3000] [--mcp-port 8765]
      e.g. python configure-openhands-v1.py gemma-4-26b-qat
           python configure-openhands-v1.py qwen3-coder-30b

Exit 0 on success, 1 on failure (so the .bat can abort).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _post(url: str, payload: dict, timeout: int = 60):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _get(url: str, timeout: int = 30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def wait_ready(base: str, seconds: int = 180) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model", help="model alias served by llama-server, e.g. gemma-4-26b-qat")
    ap.add_argument("--port", type=int, default=3000, help="OpenHands port")
    ap.add_argument("--mcp-port", type=int, default=8765)
    ap.add_argument("--mcp-token", default="", help="bearer token the tool server requires")
    ap.add_argument("--api-key", default="sk-dummy-local", help="the llama-server API key")
    ap.add_argument("--temperature", type=float, default=0.3)
    a = ap.parse_args()

    base = f"http://localhost:{a.port}"
    print(f"[configure] waiting for OpenHands on {base} ...")
    if not wait_ready(base):
        print("[configure] ERROR: OpenHands did not become ready.")
        return 1

    # NOTE: send `llm` and `mcp_config` in SEPARATE requests. Measured: when both
    # are in one agent_settings_diff, v1 stores the llm and silently DROPS
    # mcp_config (settings come back with mcpServers empty). Two posts stick.
    steps = [
        ("llm", {
            # The local llama.cpp server is OpenAI-compatible. The "openai/"
            # prefix tells litellm which provider adapter to use; the alias
            # after it is whatever llama-server is currently serving.
            "llm": {
                "model": f"openai/{a.model}",
                "base_url": "http://host.docker.internal:8080/v1",
                "api_key": a.api_key or "sk-dummy-local",
                "temperature": a.temperature,
            }
        }),
        ("mcp", {
            # Canonical MCP format (v1). This is how every MOSKY skill
            # (analyze_wallet, supervise, research, ...) reaches the agent.
            "mcp_config": {
                "mcpServers": {
                    "mosky-skills": {
                        "url": f"http://host.docker.internal:{a.mcp_port}/mcp",
                        "transport": "http",
                        "timeout": 120,
                        "description": "MOSKY market / on-chain / dev skills",
                        **({"headers": {"Authorization": f"Bearer {a.mcp_token}"}} if a.mcp_token else {}),
                    }
                }
            }
        }),
    ]

    for label, diff in steps:
        try:
            status, body = _post(f"{base}/api/v1/settings",
                                 {"agent_settings_diff": diff})
            print(f"[configure] {label:3} POST -> {status} {body.strip()[:60]}")
        except urllib.error.HTTPError as e:
            print(f"[configure] ERROR {e.code}: {e.read().decode('utf-8','replace')[:300]}")
            return 1
        except Exception as e:
            print(f"[configure] ERROR: {e}")
            return 1

    # Read back and prove it actually stuck (a 200 alone is not proof: v1
    # silently ignores unknown top-level keys).
    try:
        s = _get(f"{base}/api/v1/settings").get("agent_settings", {})
        model = (s.get("llm") or {}).get("model")
        # v1 UNWRAPS the canonical envelope: you POST
        # {"mcp_config": {"mcpServers": {"name": {...}}}} but it stores
        # {"mcp_config": {"name": {...}}}. Accept either shape when verifying.
        raw = s.get("mcp_config") or {}
        mcp = raw.get("mcpServers", raw)
        ok_model = model == f"openai/{a.model}"
        ok_mcp = "mosky-skills" in mcp
        print(f"[configure] model = {model}  {'OK' if ok_model else 'MISMATCH'}")
        print(f"[configure] mcp   = {list(mcp)}  {'OK' if ok_mcp else 'MISSING'}")
        if not (ok_model and ok_mcp):
            return 1
    except Exception as e:
        print(f"[configure] verify failed: {e}")
        return 1

    print("[configure] OpenHands v1 is pointed at the local model + MOSKY skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
