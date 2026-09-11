# Privacy: what leaves this machine, and how to make sure nothing does

Local Protocol AI runs the model, the speech recognition, the voices and
the tools on your own computer. That is the point of it. But "runs
locally" is not the same as "sends nothing anywhere": the market tools
call price APIs, the research tools search GitHub, third-party components
ship with telemetry switched on, and an AI agent that can run a shell
command can be talked into sending things. This page says exactly what
can leave, what stops it, how to prove it, and what cannot be promised.

Everything here was measured on the reference machine on 2026-09-11 by an
audit of the whole stack (five independent auditors, fifty findings,
sixteen serious ones confirmed by separate refuters). Nothing is a guess.

## The short version

**Private mode is on by default.** With it on:

- No Python process of this stack can open a connection that is not to
  this machine. Name lookups and socket connects to anything else fail with
  a clear error (`private mode: <host> is not local`).
- Every telemetry switch the installed libraries read is forced off before
  the library loads: Hugging Face Hub, Streamlit, Gradio, litellm's price
  map, chromadb, browser-use, the OpenHands / Agent Canvas telemetry, and
  this project's own update check.
- The tool server withholds the 13 tools that send your words or data to
  external hosts (wallet forensics, market data, web pages, research, pull
  requests). They are not in the tool list and they refuse direct calls.
- The tool server requires a bearer token, so nothing else on the machine
  (a container, a sandbox, a web page in your browser) can drive it.
- The voice assistant never offers an internet tool. If you turn private
  mode off for a session (`start-voice.bat online`), every such tool reads
  back **the exact text that would leave** and waits for "ναι, συνέχισε"
  before it runs.

Turning it off is one line: `LPAI_PRIVATE=0` in `.env` or the shell.
Then market data, briefings and research work again, and the table below
tells you what each one sends.

## What can leave, and when

| What | To whom | What is sent | On by default? | Off switch |
|---|---|---|---|---|
| Wallet forensics (`analyze_wallet`, `fetch_full_wallet_profile`, `check_/scan_*`) | Moralis (with your API key), PulseChain RPC and explorer, DexScreener, Finnhub, Binance, OKX, CoinGecko | the wallet address you typed or spoke; 605 requests per analysis | no (private mode withholds them) | `LPAI_PRIVATE=1` |
| Research (`research`, `research_last_30_days_broad`, the supervisor's automatic research) | api.github.com, export.arxiv.org, hn.algolia.com, reddit.com | your message, verbatim, in the URL | no | `LPAI_PRIVATE=1` |
| Web page fetch (`web_research`) | any URL the model puts in the call | the URL and whatever the model put in it | no | `LPAI_PRIVATE=1` |
| Market snapshot (`get_market_context`, the dashboard, the briefings) | Finnhub, Binance, OKX, CoinGecko, DexScreener, Tavily, Finlight | your watchlists and your API keys' identities; not your text | no | `LPAI_PRIVATE=1`; blank keys in `.env` |
| Telegram briefings | api.telegram.org | the generated briefing text | no (manual scripts only) | blank `TELEGRAM_BOT_TOKEN` |
| Pull requests (`create_pr`) | github.com, under your GitHub login | a model-written PR | no (withheld; destructive by voice) | `LPAI_PRIVATE=1` |
| Update check | api.github.com | that this machine runs the stack | no in private mode | `LOCAL_AI_UPDATE_CHECK=0` |
| Model / voice downloads | huggingface.co | which model you asked for | no in private mode (`HF_HUB_OFFLINE=1`; the files are cached) | run once with private mode off to download |
| Agent Canvas telemetry | PostHog (z.openhands.dev) | install/usage events with your machine's profile | **was on** | `DO_NOT_TRACK=1`, `VITE_DO_NOT_TRACK=1`, `OH_TELEMETRY_*` (set by the launchers) |
| OpenHands (Docker) analytics | PostHog | usage events | **was on** (`user_consents_to_analytics: true`) | set to false by `scripts/canvas_mcp_config.py` |
| Streamlit dashboard | Streamlit's metrics service | an installation id derived from your MAC address | **was on** | `.streamlit/config.toml`, `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` |
| litellm (inside Agent Canvas) | raw.githubusercontent.com | nothing of yours; it fetches a price table at import | **was on** | `LITELLM_LOCAL_MODEL_COST_MAP=True` |
| A shell command the agent runs (`run_command` by voice, the Canvas agent's terminal) | anywhere | anything the command sends | only after you say "ναι, συνέχισε" to the command read back in full | the firewall lockdown below |

The complete list of external hosts named anywhere in the code, each with
its purpose, is in `tests/test_privacy.py::ALLOWED_HOSTS`. A new host
cannot be added without a documented reason: the test fails.

## The three layers

1. **In-process guard** (`lpai_private.py`, always on in private mode).
   The honest floor: our own Python cannot reach the internet by accident,
   whatever a library or a model-chosen URL asks for. It cannot see child
   processes.
2. **Windows Firewall lockdown** (`scripts\private-firewall.ps1`, you run
   it). Per-program rules the process cannot bypass: the model server, the
   venv's Python (both the launcher in `Scripts\` and the real interpreter
   behind the junction), node, Docker, curl, certutil, bitsadmin, uv, and
   PowerShell cannot open outbound connections; nothing on the LAN can reach
   node, the model or Python. Loopback is exempt, so everything on
   `127.0.0.1` keeps working.
3. **Files** (`scripts\private-files.ps1`, you run it). Your `.env`,
   `memory\`, `logs\`, backups and the key directory become readable by you
   only. Today every local account can read them.

## Prove it

```bash
powershell -ExecutionPolicy Bypass -File scripts\private-firewall.ps1 -Status
```

shows what is in place and which of the stack's ports listen on which
address (`0.0.0.0` is flagged). Then:

```bash
powershell -ExecutionPolicy Bypass -File scripts\private-firewall.ps1 -Apply
```

```bash
powershell -ExecutionPolicy Bypass -File scripts\private-firewall.ps1 -Verify
```

`-Verify` makes each blocked program try to reach the internet and demands
the firewall's own error (`WinError 10013`); a timeout means a rule did not
bind. It also checks that the model still answers on loopback. `-Undo`
puts everything back, including the "allow" rules Windows had added when
you once clicked Allow on a popup (they are disabled, not deleted, and
listed in a file).

`-IncludeGit` also blocks git, gh and ssh — that stops your own `git push`,
so it is opt-in. `-Wsl` blocks the WSL/Docker virtual machine's outbound
traffic except to this host's model and tool ports (run `wsl --shutdown`
afterwards).

```bash
powershell -ExecutionPolicy Bypass -File scripts\private-files.ps1 -Status
```

reports who can read your data, any stray copy of `.env`, and any backup
zip that contains one. `-Apply` fixes the permissions; the stray copies and
backups are yours to delete.

And the tests: `python -m pytest tests\test_privacy.py -q`. The whole test
suite runs with the egress guard installed, so a test that reaches the
internet fails instead of leaking (one did, before).

## When you need something from the internet

- Market data, briefings, research: `LPAI_PRIVATE=0` in `.env`, then start
  the stack. The table above is what leaves.
- One voice session with the internet tools: `start-voice.bat online`.
  Each tool announces its destination and reads back the text before
  sending; you confirm by voice or it does not run.
- Downloading a model or a voice: set `LPAI_PRIVATE=0` for that one command.
- Updating packages: the firewall lockdown blocks `pip`/`uv` in the venv;
  `-Undo`, update, `-Apply`.

## What cannot be promised

Honesty is the whole value of this page, so:

- **Windows itself.** Diagnostic data, Defender sample submission and the
  ONNX Runtime's Windows event provider are outside this repository. On
  this machine the diagnostics service was stopped; a feature update can
  restart it. Windows Home cannot go below "Required" diagnostic data.
- **Docker Desktop** has its own analytics and crash reporting; its
  traffic path could not be measured (the daemon was off). The `-Wsl`
  rules cover the VM it runs in.
- **Your browser** runs vendor JavaScript (the Canvas PostHog bundle,
  Streamlit's metrics). The launchers' environment switches stop them; the
  proof is the Network tab of your browser's developer tools, not a test.
- **A shell run by an agent.** The in-process guard does not reach child
  processes and Windows program rules do not inherit to them. Only the
  firewall lockdown (which blocks PowerShell, curl, node...) and the WSL
  sandbox with `-Wsl` make a prompt-injected command harmless. By voice,
  `run_command` runs only after you hear the whole command and say yes.
- **The in-process guard** is bypassable by native code and by any
  interpreter other than the venv's. It is the honest-error layer; the
  firewall is the enforcement.
- **What already left.** Before this work the repository was public with
  a wallet address in 13 files and memory files with typed tasks; Moralis
  knows which wallets this key looked at; PostHog has one install event;
  the commits carry the author's e-mail. GitHub keeps history. Rotating
  keys limits the future, not the past.
- **Claude Code / Claude Desktop**, if you use them on this folder, send
  what they read to Anthropic by design.
- **Metadata.** Even with everything else off, DNS names go to your router
  in plaintext and your ISP sees the IPs you connect to whenever private
  mode is off.

## Owner-only settings (no code can do these)

Windows Settings → Privacy & security → Diagnostics & feedback: Required
only; Windows Security → Virus & threat protection → Automatic sample
submission: off; Docker Desktop → Settings → "Send usage statistics": off;
a DNS-over-HTTPS resolver in your network adapter settings; and in your
browser, clear the site data for `localhost:8000` once so the old PostHog
first-use flag is gone.
