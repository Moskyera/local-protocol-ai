"""Measure what a launcher configuration actually costs and delivers.

Sends the same fixed prompt to the running llama-server and reads the timings
the server itself reports, so the numbers are the server's, not a stopwatch.
Then reads the GPU's dedicated memory in use. Prints one line, so two runs can
be compared side by side.

    python scripts/bench_moe.py "label"
"""

import json
import subprocess
import sys
import time
import urllib.request

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
URL = "http://127.0.0.1:8080"

# Long enough that prompt processing is measurable, fixed so runs compare.
PROMPT = ("Write a Python function that parses an ISO-8601 date string and "
          "returns a datetime, handling timezone offsets and fractional seconds. "
          "Include docstring and three usage examples. ") * 6


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def vram_gb():
    ps = ("$c=Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage' -EA SilentlyContinue; "
          "if($c){ (($c.CounterSamples|Sort-Object CookedValue -Desc|Select-Object -First 1)"
          ".CookedValue/1GB) }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=30).stdout.strip()
    try:
        return float(out.replace(",", "."))
    except ValueError:
        return float("nan")


def wait_ready(seconds=600):
    """/props answers while the model is still loading; /health does not.
    A 503 from the first request means we asked too early, not that it
    failed, so wait for the server to say it is actually ready."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL + "/health", timeout=5) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(5)
    raise SystemExit("server never became ready")


def main():
    wait_ready()
    props = json.load(urllib.request.urlopen(URL + "/props", timeout=10))
    n_ctx = props.get("default_generation_settings", {}).get("n_ctx")

    # warm-up so the first-call cost does not land in the measurement
    post("/completion", {"prompt": "hi", "n_predict": 8, "temperature": 0})

    runs = []
    for _ in range(2):
        r = post("/completion", {"prompt": PROMPT, "n_predict": 160,
                                 "temperature": 0, "cache_prompt": False})
        t = r.get("timings", {})
        runs.append((t.get("prompt_per_second", 0), t.get("predicted_per_second", 0),
                     t.get("prompt_n", 0), t.get("predicted_n", 0)))
    pp = sum(x[0] for x in runs) / len(runs)
    tg = sum(x[1] for x in runs) / len(runs)
    v = vram_gb()

    print(f"{LABEL:28} ctx={n_ctx:6}  prompt {pp:7.1f} tok/s   "
          f"generate {tg:6.1f} tok/s   VRAM {v:5.2f} GB")


if __name__ == "__main__":
    main()
