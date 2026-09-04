# Local Protocol AI

A working AI agent system that runs entirely on your own computer. No API keys,
no subscriptions, no data leaving your machine.

You give it a task in plain language. It picks the right specialist for the job
— there are 38 of them, from Python and TypeScript to security review, document
analysis, 3D printing and market research — and does the work using a language
model running on your own graphics card.

It is a real system that has been used daily, not a demo. It has 626 tests.

---

## Is this for you?

**Yes, if:** you have a gaming-grade graphics card, you want AI help without
sending your code and documents to a company, and you are comfortable
installing a few things and reading an error message when one appears.

**Probably not, if:** you want something that works in one click, you have no
dedicated graphics card, or you need the quality of a frontier cloud model. A
model that fits on a home graphics card is genuinely good at focused work and
genuinely worse than the big cloud models at hard reasoning. That is the trade.

---

## What you need

**A graphics card with at least 8 GB of video memory, and system RAM to hold
the model.** By default the coding launcher keeps the model's expert weights in
system RAM and puts only the attention layers on the card — measured at 4.7 GB
of video memory on this machine. That is what makes an 8 GB card workable. The
cost moves to RAM: the coding model is a 16.5 GB file loaded whole, so you want
at least 24 GB of RAM with nothing heavy running beside it. With 16 GB of video
memory you can instead put half the experts on the card and roughly double
generation speed; see "About your graphics card" below.

Everything here was built and measured on **Windows 11 with an AMD RX 9070 XT
(16 GB), using Vulkan**. That is a real constraint on how much I can promise:
NVIDIA cards will work — llama.cpp supports CUDA and it is the better-supported
path — but the specific numbers in this guide were measured on AMD, and the
launchers are written for Windows. On Linux or macOS the Python side works
fine; you will need to start the model server yourself.

**About 40 GB of free disk space.** The two models are roughly 16 GB each and
the Python packages add a few more.

**Python 3.11 or newer.** Developed on 3.14.

**Git.**

**Docker Desktop** — optional. Only needed for the older sandboxed agent
interface. The newer one does not use it.

---

## Installing

### 1. Get the code

```bash
git clone https://github.com/Moskyera/local-protocol-ai.git
cd local-protocol-ai
```

Where you put it does not matter. Nothing here assumes a particular folder.

### 2. Make a Python environment and install the packages

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux the activate line is `source .venv/bin/activate`.

There are three smaller requirement files if you want a lighter install:
`requirements-core.txt` is just the market engines and the dashboard,
`requirements-agentic.txt` adds the agent platform, and
`requirements-experiments.txt` adds the voice and web experiments.

### 3. Get llama.cpp

This is the program that actually runs the model. Download a recent release
from [github.com/ggml-org/llama.cpp/releases](https://github.com/ggml-org/llama.cpp/releases)
and extract it into a folder named `llama` **next to** the folder you cloned
into. So if the code is in `D:\projects\local-protocol-ai`, llama.cpp goes in
`D:\projects\llama`.

Pick the build that matches your card:

| Your card | Download the file named |
|---|---|
| AMD | `llama-*-bin-win-vulkan-x64.zip` |
| NVIDIA | `llama-*-bin-win-cuda-*.zip` |
| Any, no GPU | `llama-*-bin-win-cpu-x64.zip` (slow but works) |

If you would rather keep llama.cpp somewhere else, set `LOCAL_AI_LLAMA_DIR` to
that folder.

### 4. Download a model

Models go in a folder named `models`, also next to the code — so
`D:\projects\models`. Or set `LOCAL_AI_MODELS_DIR` to wherever you want them.

You need at least one. Each is about 16 GB, so this takes a while.

**For coding and agent work** (this is the one to start with):

```bash
pip install huggingface_hub
huggingface-cli download unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf --local-dir ../models
```

**For market analysis and general writing** (optional):

```bash
huggingface-cli download unsloth/gemma-4-26B-A4B-it-GGUF gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf --local-dir ../models
```

If 16 GB is tight on your card, download the `Q4_K_M` version instead of
`Q4_K_XL`. It is slightly smaller and slightly worse.

### 5. Set up your configuration

```bash
copy .env.example .env
```

Then open `.env` and read it. Every setting is optional and explained in the
file. If you only want local AI with no external services, you can leave the
whole thing as it is.

### 6. Start it

```bash
start-ai.bat coder
```

Leave off `coder` to start the market model instead.

The first start takes a few minutes while the model loads into your graphics
card. When it is ready you will see the dashboard open in your browser.

---

## What is actually running

| Part | Where | What it does |
|---|---|---|
| The model | `127.0.0.1:8080` | llama.cpp serving an OpenAI-compatible API |
| Tools | `127.0.0.1:8765` | Your own tools, exposed over MCP |
| Dashboard | `127.0.0.1:8501` | Market data and system status |
| Agent interface | `127.0.0.1:3000` | Where you talk to the agents |

**Everything listens on `127.0.0.1` on purpose.** That means only your own
computer can reach it. None of these services asks for a password, so if you
open them to your network, everyone on that network can use your graphics card,
read your files, and run commands as you. Do not change this unless you know
exactly why you are doing it.

---

## About your graphics card, honestly

A 16 GB card holds **one** model at a time. That is why the launcher takes a
`coder` argument instead of running both: switching models means restarting the
backend, and there is no way around it at this memory size.

Both models are Mixture-of-Experts. Most of the file is "experts", of which
only a few fire for any given token. The coding launcher therefore keeps the
experts in system RAM by default (`--cpu-moe`) and puts only the attention
layers on the card. Measured on this machine at a 32,768-token context:

| Configuration | Video memory | Prompt | Generation |
|---|---|---|---|
| Whole layers on the GPU (old default) | 15.4 GB | 310 tok/s | 39 tok/s |
| **Experts in RAM (`--cpu-moe`, default now)** | **4.7 GB** | **361 tok/s** | **22 tok/s** |
| Half the experts on the GPU (`-NCpuMoe 24`) | 12.8 GB | 496 tok/s | 40 tok/s |

The default is the slowest at generating text and the only one with real
headroom on a 16 GB card. It is also the reason an 8 GB card can run this at
all. Prompt processing is actually faster, because every layer's attention now
fits on the GPU. If 22 tokens a second is too slow for you and you have the
video memory, `-NCpuMoe 24` on the coding launcher buys the speed back.

Two warnings, both learned the hard way. Asking for more video memory than the
card has does not produce a polite error; on this machine it produced four
hard crashes with a `VIDEO_TDR_FAILURE` bugcheck, and the launcher's budget
check exists because of them. And the split configurations drive the GPU and
every CPU core flat out at once — the highest power draw the machine can
produce. This machine hard-reset, with no crash dump, seconds after a
benchmark of `-NCpuMoe 24` finished. The cause was not proven. It is recorded
here so you do not run that configuration unattended and find out.

The market model has much heavier attention — 223 KiB of cache per token of
context, 7 GB at a 32,000-token window before any weights load — so its
launcher keeps the old whole-layer behaviour until `--cpu-moe` has been
measured on it. Pass `-CpuMoe` to try it.

---

## The newer agent interface (Agent Canvas)

The Docker-based interface on port 3000 still works, but the project behind it
stopped development in July 2026 and its image is frozen. The replacement is
called Agent Canvas, and it does not need Docker at all.

You need [Node.js 22.12 or newer](https://nodejs.org) and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

The simple way, straight from its own instructions:

```bash
npm install -g @openhands/agent-canvas
agent-canvas
```

If you would rather not install it globally — which is what I did, and it works
the same — put it in its own folder next to everything else:

```bash
mkdir ../agent-canvas
cd ../agent-canvas
npm init -y
npm install @openhands/agent-canvas
node node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs
```

Once it is installed, this project can start the whole thing for you — the
model, your tools and Canvas, with no Docker anywhere:

```bash
start-canvas.bat
```

That is the newer path. `start-ai.bat` is still the Docker one. They share the
model, so run one or the other, not both.

If you start Canvas by hand instead, it opens at `http://localhost:8000`. Then
in Settings, add a provider:

- **Provider:** OpenAI
- **Base URL:** `http://127.0.0.1:8080/v1`
- **API key:** anything at all — `sk-dummy-local` is fine, a local server does
  not check it
- **Model:** `openai/qwen3-coder-30b`

Two things to know before you commit to it:

**It runs without a sandbox.** The agent has full access to your files, with
nothing between it and your disk. The older Docker interface isolates it. The
OpenHands project itself says this is why they are keeping the old one alive.

**It reports usage to its developers**, but it does ask. The first screen is a
consent dialog with a switch you can turn off before clicking through, and
turning it off records a revocation request for the event its own source says
is sent immediately on first use. There is no environment variable or
command-line flag for this at version 1.16 — the dialog is the only control,
and the answer is stored in your browser, so a different browser or a cleared
site data will ask again.

**It also listens on all network interfaces**, unlike everything else here, and
has no option to restrict that — only `--port`. In its default mode the API key
is injected into the page automatically, so anyone who can open the address has
full access to an agent that reads and writes your files. Run this once to shut
that off at the firewall:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\secure-agent-canvas.ps1
```

It asks for administrator rights itself, and your own browser keeps working —
loopback traffic never goes through the firewall.

---

## Connecting your own tools

Agent Canvas reads tool servers from a file. To give it the tools this project
provides, create
`%USERPROFILE%\.openhands\plugins\local-tools\.mcp.json`:

```json
{
  "mcpServers": {
    "local-tools": {
      "transport": "streamable-http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Start the tool server alongside it:

```bash
python -m openhands_mcp.server --transport streamable-http --port 8765
```

---

## Optional extras

None of these are needed. Each one adds a single feature, and if you skip it
that feature reports itself as unconfigured rather than failing strangely.

**Market data.** Free accounts at [Finnhub](https://finnhub.io) (stocks and
currency), [Tavily](https://tavily.com) (web search),
[Finlight](https://finlight.me) (financial news) and
[Moralis](https://moralis.io) (blockchain wallets). Put the keys in `.env`.

**Telegram briefings.** If you want the daily analysis delivered to a chat,
make a bot with [@BotFather](https://t.me/BotFather) and put the token and your
chat ID in `.env`. Nothing is ever sent while those are empty.

**Image generation.** Needs [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
running separately.

---

## When something goes wrong

**"No Python virtualenv found"** — you skipped step 2, or you are not in the
folder you cloned into.

**The backend never becomes ready.** Look at the window the launcher opened. If
the model file is not where it expected, the path is printed. Check that the
`.gguf` file is really in your `models` folder and that the name matches
exactly.

**Your screen goes black and the machine restarts.** You have asked for more
video memory than the card has. Start with a smaller context:
`start-ai.bat coder` then, if it still happens, edit the `-Ctx` default in
`start-llama-coder.ps1` downwards.

**The agent talks instead of doing anything.** The model needs to support tool
calling and the server needs `--jinja` for it to work. The coding launcher
passes it; the market one does not, because that model is for writing.

**"Address already in use"** — something from a previous run is still going.
The launcher clears the ports itself, so just run it again.

**Docker will not start** (only relevant to the older interface). On Windows
its background service is often set to start manually. Open Docker Desktop and
accept the permission prompt, then run the launcher again.

---

## Updates

Every time you start it, it asks GitHub whether there is a newer release and
prints a table of what changed. It never blocks the start, it is cached for an
hour, and if it cannot reach GitHub it says so rather than telling you that you
are up to date.

To update:

```bash
git pull
pip install -r requirements.txt
```

---

## Your privacy

The model runs on your computer. Your prompts, your code and your documents are
not sent anywhere.

The exceptions, all of which are yours to turn on:

- The optional market data services, which see whatever you ask them about
- Telegram, if you configure it
- The update check, which asks GitHub for the release list — that request tells
  GitHub your IP address and nothing else
- Agent Canvas, if you use it, which reports usage to its own developers

`.env` holds your credentials and is excluded from git. Keep it that way.

---

## A word about the market analysis

Part of this system analyses financial markets and can produce something that
looks like a trading recommendation.

**It is not financial advice.** It is a language model with a limited view of a
few data sources, running on a home computer. It can be confidently wrong. Do
not put money on its output. If you are making real financial decisions, talk
to someone qualified.

The scoring code deliberately includes trading costs when it evaluates a
signal, because a strategy that looks profitable at zero fees usually is not.
That honesty is the point — but it does not make the output advice.

---

## What is in here

- **38 specialists** — Python, TypeScript, C++, React, backend, DevOps,
  security review, SEO, accessibility, QA, content, brand, legal, analytics,
  crypto payments, and a set for the Hacash blockchain
- **15 agents** that plan, write, test, review and improve code
- **Market analysis** — indicators, backtesting, news, on-chain wallet
  forensics, signal scoring with costs included
- **Document analysis** — read a PDF, get the chapter structure, ask questions
- **3D printing** — describe a part, get a printable model, checked against
  your printer bed
- **Website building** — a full team of specialists for real sites
- **Voice**, in Greek and English

`ORGANIZATION.md` and `AGENT_UPGRADE_PLAN.md` are older internal notes kept for
history. They describe the machine this was built on and are not instructions.

---

## Contributing

Bug reports are welcome, especially from NVIDIA and Linux users — those paths
are the least tested here.

If you send code, run the tests first:

```bash
python -m pytest tests/ -q
```

All 626 should pass. There is also a check that runs before publishing:

```bash
python scripts/check_publication_ready.py
```

It refuses to let anything personal or unsafe into a public repository, and it
says plainly what it cannot check.

---

## License

MIT. Do what you like with it. See [LICENSE](LICENSE).
