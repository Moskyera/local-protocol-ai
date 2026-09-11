#!/usr/bin/env bash
# start-llama.sh — the model server launcher for Linux (and macOS for the CPU
# and Vulkan paths). The same decisions as start-llama-coder.ps1 and
# start-llama-vulkan.ps1 on Windows, made the same way, so the two platforms
# do not drift.
#
#   ./start-llama.sh coder     Qwen3-Coder-30B-A3B  — agents, tool calling
#   ./start-llama.sh market    gemma-4-26B-A4B      — briefings, writing
#
# Nothing in here is guessed. Every number below was measured on the reference
# machine (Windows 11, RX 9070 XT 16 GB, Vulkan) and is carried over unchanged;
# where Linux differs it says so.
#
# WHICH llama.cpp BUILD — llama.cpp ships NO CUDA binary for Linux. Checked
# against the release assets for b9587 and b10816 on 2026-09-05:
#
#   NVIDIA   llama-bNNNN-bin-ubuntu-vulkan-x64.tar.gz   works out of the box
#            or build from source with -DGGML_CUDA=ON     faster, your effort
#   AMD      llama-bNNNN-bin-ubuntu-rocm-*-x64.tar.gz    native, fastest
#            or the vulkan tarball above                   if ROCm is not set up
#   no GPU   llama-bNNNN-bin-ubuntu-x64.tar.gz           slow but works
#
# Extract it into a folder named "llama" NEXT TO the repository (so if the code
# is in ~/local-protocol-ai, the binary is in ~/llama/...), or point
# LOCAL_AI_LLAMA_DIR at wherever you put it — a symlink to a source build's
# bin/ directory is fine. This script finds llama-server anywhere up to three
# levels inside that folder, because the tarballs differ in whether they have
# a top-level directory; with several builds present the highest bNNNN wins.
#
# ENVIRONMENT (all optional)
#   LOCAL_AI_LLAMA_DIR    folder holding llama-server         default: ../llama
#   LOCAL_AI_MODELS_DIR   folder holding the .gguf files      default: ../models
#   LOCAL_AI_MODEL        full path to one .gguf, overriding the model for a mode
#   LOCAL_AI_GPU          nvidia | amd | cpu | auto            default: auto
#   LOCAL_AI_VRAM_GB      your card's memory in GB, if it cannot be read
#   LOCAL_AI_BIND         address to listen on                default: 127.0.0.1
#
# OPTIONS
#   --ctx N            context tokens (coder 32768, market 16384)
#   --parallel N       request slots; the context is DIVIDED between them (1)
#   --reserve-gb X     VRAM left for the desktop and compute buffers (2.0)
#   --vram-gb N        same as LOCAL_AI_VRAM_GB
#   --ngl N            force this many layers on the GPU (0 = compute it)
#   --cpu-moe          keep the expert weights in system RAM (coder: default on)
#   --no-cpu-moe       fit whole layers to the budget instead (market: default)
#   --n-cpu-moe N      middle ground: only the first N layers' experts in RAM
#   --threads N        CPU threads (default: physical cores)
#   --bind ADDR        same as LOCAL_AI_BIND
#   --port N           default 8080
#   --dry-run          print every decision and the full command; start nothing
#   --foreground       run the server in this terminal instead of the background
#
# WHY 127.0.0.1 — the OpenAI-compatible endpoint has no authentication. Bound to
# 0.0.0.0 on a shared network it hands your GPU to everyone on it. Widen it only
# for a container that reaches the host through a bridge, and know why.
#
# WHY --cpu-moe IS THE CODER DEFAULT — measured on the reference card, 32k, one
# slot: whole layers 15.43 GB / 39 t/s; experts in RAM 4.69 GB / 22 t/s and
# faster prompt processing. It is the only configuration with real headroom on
# a 16 GB card and the one an 8 GB card can run at all. The market model keeps
# whole layers until its own comparison is measured (see the .ps1 for numbers).
#
# WHY THE BUDGET REFUSES — asking a card for more memory than it has does not
# produce an error. On the reference machine it produced four hard crashes.
# This script computes what fits and refuses what does not, like the Windows
# one. When it cannot read your VRAM it stops and asks, rather than guessing.
#
# WHAT IS DELIBERATELY NOT MIRRORED — the market .ps1 relaunches a CPU-only
# server if the GPU one is not ready in ten minutes. That is a HIP-era leftover
# whose -c 131072 contradicts that file's own budget; the coder .ps1 has no such
# fallback and neither does this script. Not ready in ten minutes means stop.
#
# ---- end of help ----

set -euo pipefail

# Private mode (the default): nothing this machine runs phones home. Same
# switches as scripts/private-env.bat; see docs/PRIVACY.md.
export LPAI_PRIVATE="${LPAI_PRIVATE:-1}"
if [ "$LPAI_PRIVATE" != "0" ]; then
  export HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 DO_NOT_TRACK=1 VITE_DO_NOT_TRACK=1
  export GRADIO_ANALYTICS_ENABLED=False STREAMLIT_BROWSER_GATHER_USAGE_STATS=false LITELLM_LOCAL_MODEL_COST_MAP=True LITELLM_TELEMETRY=False
  export ANONYMIZED_TELEMETRY=false BROWSER_USE_CLOUD_SYNC=false OH_TELEMETRY_EXPORTER=none OH_TELEMETRY_CONSENT=denied OH_TELEMETRY_CONSENT_MODE=override LOCAL_AI_UPDATE_CHECK=0
fi


# ---------------------------------------------------------------------------
# Where things are
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LLAMA_DIR="${LOCAL_AI_LLAMA_DIR:-$AI_ROOT/llama}"
MODELS_DIR="${LOCAL_AI_MODELS_DIR:-$AI_ROOT/models}"

show_help() { awk 'NR>1 && /^# ---- end of help ----/{exit} NR>1' "$0"; }

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
MODE="${1:-}"
if [[ "$MODE" != "coder" && "$MODE" != "market" ]]; then
  echo "usage: $0 coder|market [options]   (--help for the full list)" >&2
  exit 2
fi
shift

CTX=""; PARALLEL=1; RESERVE_GB=2.0; VRAM_GB="${LOCAL_AI_VRAM_GB:-}"; NGL_FORCE=0
CPU_MOE=""; N_CPU_MOE=0; THREADS=""; BIND="${LOCAL_AI_BIND:-127.0.0.1}"; PORT=8080
DRY_RUN=0; FOREGROUND=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ctx)        CTX="${2:?--ctx needs a value}"; shift 2 ;;
    --parallel)   PARALLEL="${2:?--parallel needs a value}"; shift 2 ;;
    --reserve-gb) RESERVE_GB="${2:?--reserve-gb needs a value}"; shift 2 ;;
    --vram-gb)    VRAM_GB="${2:?--vram-gb needs a value}"; shift 2 ;;
    --ngl)        NGL_FORCE="${2:?--ngl needs a value}"; shift 2 ;;
    --cpu-moe)    CPU_MOE=1; shift ;;
    --no-cpu-moe) CPU_MOE=0; shift ;;
    --n-cpu-moe)  N_CPU_MOE="${2:?--n-cpu-moe needs a value}"; shift 2 ;;
    --threads)    THREADS="${2:?--threads needs a value}"; shift 2 ;;
    --bind)       BIND="${2:?--bind needs a value}"; shift 2 ;;
    --port)       PORT="${2:?--port needs a value}"; shift 2 ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --foreground) FOREGROUND=1; shift ;;
    -h|--help)    show_help; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Per-model facts. LAYERS and the KV cost per token come from each file's
# GGUF header, exactly as in the Windows launchers.
# ---------------------------------------------------------------------------
case "$MODE" in
  coder)
    MODEL_FILE="Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf"
    ALIAS="qwen3-coder-30b"; LAYERS=48; KV_KIB_PER_TOKEN=51.0
    : "${CTX:=32768}"; : "${CPU_MOE:=1}"; JINJA=1 ;;
  market)
    MODEL_FILE="gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf"
    ALIAS="gemma-4-26b-qat"; LAYERS=30; KV_KIB_PER_TOKEN=223.1
    : "${CTX:=16384}"; : "${CPU_MOE:=0}"; JINJA=0 ;;
esac
MODEL_PATH="${LOCAL_AI_MODEL:-$MODELS_DIR/$MODEL_FILE}"

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

say "=== Local Protocol AI — $MODE backend ($ALIAS) ==="

# ---------------------------------------------------------------------------
# The model file. -f follows symlinks; so must stat, or a symlinked model is
# sized at the link's 61 bytes and the budget divides by zero.
# ---------------------------------------------------------------------------
[[ -f "$MODEL_PATH" ]] || die "model not found: $MODEL_PATH
  Download it (see README 'Download a model'), or set LOCAL_AI_MODELS_DIR / LOCAL_AI_MODEL."
MODEL_BYTES=$(stat -L -c %s "$MODEL_PATH" 2>/dev/null || stat -L -f %z "$MODEL_PATH" 2>/dev/null || echo 0)
[[ "$MODEL_BYTES" =~ ^[0-9]+$ && "$MODEL_BYTES" -gt 0 ]] || die "model file is empty or unreadable: $MODEL_PATH"
MODEL_GB=$(awk -v b="$MODEL_BYTES" 'BEGIN{printf "%.2f", b/1073741824}')
say "model   : $MODEL_PATH ($MODEL_GB GB)"

# ---------------------------------------------------------------------------
# The binary. Tarballs differ in layout, so look a few levels down; follow
# symlinks (a build directory is often linked in); with several builds present
# take the highest bNNNN path; fall back to one on PATH.
# ---------------------------------------------------------------------------
SERVER=""
if [[ -d "$LLAMA_DIR" ]]; then
  FOUND=$(find -L "$LLAMA_DIR" -maxdepth 3 -type f -name llama-server -perm -u+x 2>/dev/null | sort -V || true)
  if [[ -n "$FOUND" ]]; then
    SERVER=$(printf '%s\n' "$FOUND" | tail -1)
    n=$(printf '%s\n' "$FOUND" | wc -l | tr -d ' ')
    [[ "$n" -gt 1 ]] && warn "$n llama-server binaries under $LLAMA_DIR; using the highest-versioned path: $SERVER"
  fi
fi
[[ -n "$SERVER" ]] || SERVER=$(command -v llama-server || true)
[[ -n "$SERVER" ]] || die "llama-server not found in $LLAMA_DIR or on PATH.
  Get a build from https://github.com/ggml-org/llama.cpp/releases and extract it there:
    NVIDIA : llama-bNNNN-bin-ubuntu-vulkan-x64.tar.gz  (or build with -DGGML_CUDA=ON)
    AMD    : llama-bNNNN-bin-ubuntu-rocm-*-x64.tar.gz  (or the vulkan one)
    no GPU : llama-bNNNN-bin-ubuntu-x64.tar.gz
  Note: llama.cpp ships no CUDA binary for Linux. That is not this script's doing."
BIN_DIR="$(cd "$(dirname "$SERVER")" && pwd -P)"
# Tarball layouts put the shared libraries beside the binary; make sure a
# freshly extracted build finds them without the user setting anything.
export LD_LIBRARY_PATH="$BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
say "server  : $SERVER"
say "version : $("$SERVER" --version 2>&1 | head -1 || true)"

# ---------------------------------------------------------------------------
# The GPU, and how much memory it has. Read it; never assume it. On AMD, with
# an iGPU beside the discrete card, take the card with the most memory and
# keep using THAT card for the release watch later.
# ---------------------------------------------------------------------------
GPU="${LOCAL_AI_GPU:-auto}"
AMD_DEV=""
pick_amd_card() {
  local best="" bestbytes=0 f b
  for f in /sys/class/drm/card*/device/mem_info_vram_total; do
    [[ -r "$f" ]] || continue
    b=$(cat "$f" 2>/dev/null || echo 0)
    if [[ "$b" =~ ^[0-9]+$ && "$b" -gt "$bestbytes" ]]; then bestbytes=$b; best="$(dirname "$f")"; fi
  done
  AMD_DEV="$best"
}
if [[ "$GPU" == "auto" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then GPU=nvidia
  else
    pick_amd_card
    if [[ -n "$AMD_DEV" ]] || command -v rocm-smi >/dev/null 2>&1; then GPU=amd; else GPU=cpu; fi
  fi
fi
case "$GPU" in nvidia|amd|cpu) ;; *) die "LOCAL_AI_GPU must be nvidia, amd, cpu or auto (got '$GPU')" ;; esac
[[ "$GPU" == "amd" && -z "$AMD_DEV" ]] && pick_amd_card

if [[ -z "$VRAM_GB" && "$GPU" != "cpu" ]]; then
  case "$GPU" in
    nvidia)
      mib=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
      [[ "$mib" =~ ^[0-9]+$ ]] && VRAM_GB=$(awk -v m="$mib" 'BEGIN{printf "%.0f", m/1024}') ;;
    amd)
      if [[ -n "$AMD_DEV" && -r "$AMD_DEV/mem_info_vram_total" ]]; then
        VRAM_GB=$(awk -v b="$(cat "$AMD_DEV/mem_info_vram_total")" 'BEGIN{printf "%.0f", b/1073741824}')
      elif command -v rocm-smi >/dev/null 2>&1; then
        b=$(rocm-smi --showmeminfo vram --csv 2>/dev/null | awk -F, 'NR==2{print $2}' || true)
        [[ "$b" =~ ^[0-9]+$ ]] && VRAM_GB=$(awk -v b="$b" 'BEGIN{printf "%.0f", b/1073741824}')
      fi ;;
  esac
fi
if [[ "$GPU" != "cpu" && ! "$VRAM_GB" =~ ^[0-9]+$ ]]; then
  die "found a $GPU GPU but could not read its memory size.
  Pass --vram-gb N (or LOCAL_AI_VRAM_GB=N). This script will not guess: asking a card
  for more than it has is what hard-crashed the reference machine four times."
fi
say "gpu     : $GPU${VRAM_GB:+ ($VRAM_GB GB)}${AMD_DEV:+  $(basename "$(dirname "$AMD_DEV")")}"

# ---------------------------------------------------------------------------
# Threads: physical cores, like the Windows launchers' -t 16 on a 16-core part.
# The probe must not be able to kill the script: under pipefail a missing lscpu
# makes grep exit 1, and a bare assignment would take the script down with it.
# ---------------------------------------------------------------------------
if [[ -z "$THREADS" ]]; then
  if command -v lscpu >/dev/null 2>&1; then
    THREADS=$(lscpu -p=core 2>/dev/null | grep -v '^#' | sort -u | wc -l | tr -d ' ' || true)
  elif [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]]; then
    THREADS=$(sysctl -n hw.physicalcpu 2>/dev/null || true)
  fi
  [[ "${THREADS:-}" =~ ^[0-9]+$ && "$THREADS" -ge 1 ]] || THREADS=$(( $(nproc 2>/dev/null || echo 4) / 2 ))
  [[ "$THREADS" -ge 1 ]] || THREADS=1
fi

# ---------------------------------------------------------------------------
# The VRAM budget — the .ps1 arithmetic, in ONE awk on the raw byte count, so
# nothing is rounded before the layer count is taken. Rounding the inputs to
# two decimals first was measured to hand out one layer too many on the
# reference 16 GB card, which is the overcommit this whole block exists to
# prevent. The displayed figures are rounded; the decision is not.
# ---------------------------------------------------------------------------
NGL=0; KV_GB=""; USABLE=""; BUDGET=""
if [[ "$GPU" == "cpu" ]]; then
  if [[ "$NGL_FORCE" -gt 0 ]]; then
    NGL=$NGL_FORCE
    warn "no GPU detected; passing --ngl $NGL_FORCE through unchecked, as asked"
    say "budget  : no GPU detected — --ngl $NGL_FORCE forced, --cpu-moe irrelevant"
  else
    say "budget  : no GPU — everything on the CPU (slow; --cpu-moe and --ngl irrelevant)"
  fi
  CPU_MOE=0; N_CPU_MOE=0
else
  read -r NGL_FIT FITS REFUSE KV_GB USABLE BUDGET < <(awk \
    -v bytes="$MODEL_BYTES" -v k="$KV_KIB_PER_TOKEN" -v c="$CTX" \
    -v v="$VRAM_GB" -v r="$RESERVE_GB" -v L="$LAYERS" \
    'BEGIN{ m=bytes/1073741824; kv=k*c/1048576; u=v-r; b=u-kv;
            raw=L*(b/m); n=int(raw); if(n>L)n=L; if(n<0)n=0;
            printf "%d %d %d %.2f %.2f %.2f\n", n, int(raw), (b<=0), kv, u, b }')
  say "budget  : card $VRAM_GB GB, reserved $RESERVE_GB GB -> usable $USABLE GB"
  say "          KV cache at --ctx $CTX (q8_0, flash attention): $KV_GB GB"
  [[ "$REFUSE" == "1" ]] && die "--ctx $CTX needs $KV_GB GB of KV cache, which does not fit in $USABLE GB on its own. Lower --ctx."
  if [[ "$NGL_FORCE" -gt 0 ]]; then
    NGL=$NGL_FORCE
    [[ "$NGL" -le "$FITS" ]] || warn "--ngl $NGL exceeds the $FITS layers that fit; the driver will spill over the bus, which is what causes the hangs."
  else
    NGL=$NGL_FIT
  fi
  if [[ "$CPU_MOE" == "1" || "$N_CPU_MOE" -gt 0 ]]; then
    # With the experts in system RAM only the attention and shared tensors are
    # offloaded — 0.95 GiB of the Qwen file, 2.40 GiB of gemma's — so every
    # layer fits and the whole-file budget above does not apply.
    NGL=$LAYERS
    say "          experts in system RAM; GPU holds the non-expert weights + $KV_GB GB KV"
  else
    ON_GPU=$(awk -v b="$MODEL_BYTES" -v n="$NGL" -v L="$LAYERS" 'BEGIN{printf "%.2f", b/1073741824*n/L}')
    say "          -> offloading $NGL of $LAYERS layers ($ON_GPU GB) + $KV_GB GB KV of $USABLE GB usable"
    [[ "$NGL" -lt "$LAYERS" ]] && say "             ($((LAYERS-NGL)) layers on the CPU. Lower --ctx to buy some back, or use --cpu-moe.)"
  fi
fi

# ---------------------------------------------------------------------------
# Newer builds (b10816+) retired --no-mmap for --load-mode; older ones (b9587)
# do not know --load-mode. Ask the binary once, with no model loaded. Capture
# the whole help text first: piping it into grep -q under pipefail lets grep
# close the pipe on the first match, the binary takes SIGPIPE, the pipeline
# reports 141, and the wrong flag goes out. The .ps1 reads via Out-String for
# the same reason.
# ---------------------------------------------------------------------------
HELP=$("$SERVER" --help 2>&1 || true)
if [[ "$HELP" == *--load-mode* ]]; then LOAD_FLAG=(--load-mode none); else LOAD_FLAG=(--no-mmap); fi

# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------
ARGS=(
  -m "$MODEL_PATH" --alias "$ALIAS" --host "$BIND" --port "$PORT" ${LLAMA_API_KEY:+--api-key "$LLAMA_API_KEY"}
  --n-gpu-layers "$NGL" -c "$CTX"
  --cache-type-k q8_0 --cache-type-v q8_0 -fa on --cache-reuse 256
  -t "$THREADS" --batch-size 256 --ubatch-size 128 --cont-batching
  --parallel "$PARALLEL" --no-warmup "${LOAD_FLAG[@]}"
)
[[ "$JINJA" == "1" ]] && ARGS+=(--jinja)      # tool calls need the model's own template
if   [[ "$N_CPU_MOE" -gt 0 ]]; then ARGS+=(--n-cpu-moe "$N_CPU_MOE")
elif [[ "$CPU_MOE" == "1" ]]; then ARGS+=(--cpu-moe); fi

say "bind    : $BIND:$PORT   threads: $THREADS   slots: $PARALLEL   load: ${LOAD_FLAG[*]}"
say "command : $(printf '%q ' "$SERVER" "${ARGS[@]}")"

if [[ "$DRY_RUN" == "1" ]]; then
  say "dry run : nothing started, nothing stopped."
  exit 0
fi

command -v curl >/dev/null 2>&1 || die "curl is required for the readiness check (apt install curl)"

# ---------------------------------------------------------------------------
# Stop a previous server, then ALWAYS wait for the card to give its memory
# back — whether we killed one or it died some other way. Killing one that
# holds 14 GB and allocating 14 GB a second later is what hung the reference
# machine; the watch mirrors the Windows launcher's Stop-LlamaServerAndWaitForVram.
# An unreadable counter is not "zero in use": it is a five-second wait and a
# visible notice, as on Windows.
# ---------------------------------------------------------------------------
if pgrep -x llama-server >/dev/null 2>&1; then
  say "stopping the previous llama-server..."
  pkill -x llama-server || true
  for _ in $(seq 1 45); do pgrep -x llama-server >/dev/null 2>&1 || break; sleep 1; done
  pgrep -x llama-server >/dev/null 2>&1 && { pkill -9 -x llama-server || true; sleep 2; }
fi
case "$GPU" in
  nvidia)
    used=""
    for _ in $(seq 1 45); do
      used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
      if [[ ! "$used" =~ ^[0-9]+$ ]]; then warn "no GPU memory counter available - waiting 5s instead"; sleep 5; used=""; break; fi
      [[ "$used" -le 2048 ]] && break; sleep 1
    done
    [[ -z "$used" || "$used" -le 2048 ]] || warn "$((used/1024)) GB of VRAM still held after 45s; starting anyway" ;;
  amd)
    f="${AMD_DEV:+$AMD_DEV/mem_info_vram_used}"
    if [[ -n "$f" && -r "$f" ]]; then
      used=0
      for _ in $(seq 1 45); do used=$(cat "$f" 2>/dev/null || echo 0); [[ "$used" -le 2147483648 ]] && break; sleep 1; done
      [[ "$used" -le 2147483648 ]] || warn "$((used/1073741824)) GB of VRAM still held after 45s; starting anyway"
    else
      warn "no GPU memory counter available - waiting 5s instead"; sleep 5
    fi ;;
esac

# ---------------------------------------------------------------------------
# Start, and wait until it actually answers. An IPv6 bind needs brackets in
# the probe URL; the any-address binds route to loopback on Linux.
# ---------------------------------------------------------------------------
LOG="$LLAMA_DIR/llama-$MODE.log"; ERR="$LLAMA_DIR/llama-$MODE.err"
mkdir -p "$LLAMA_DIR"
if [[ "$FOREGROUND" == "1" ]]; then
  exec "$SERVER" "${ARGS[@]}"
fi
nohup "$SERVER" "${ARGS[@]}" >"$LOG" 2>"$ERR" &
PID=$!
say "started : pid $PID   logs: $LOG / $ERR"
H="$BIND"; [[ "$BIND" == *:* ]] && H="[$BIND]"
for _ in $(seq 1 120); do
  if [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://$H:$PORT/health" 2>/dev/null || true)" == "200" ]]; then
    say "READY   : http://$H:$PORT  ($ALIAS)"
    exit 0
  fi
  kill -0 "$PID" 2>/dev/null || die "llama-server exited during load. Last lines of $ERR:
$(tail -20 "$ERR" 2>/dev/null || true)"
  sleep 5
done
die "not ready after 10 minutes. Check $ERR."
