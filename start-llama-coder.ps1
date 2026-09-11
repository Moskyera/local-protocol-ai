# start-llama-coder.ps1
# Coding backend for MOSKY: Qwen3-Coder-30B-A3B (MoE, 3B active) on AMD RX 9070 XT via Vulkan.
#
# ΓΙΑΤΙ ΞΕΧΩΡΙΣΤΟΣ LAUNCHER:
#   Τα 16GB VRAM ΔΕΝ χωράνε gemma-26B ΚΑΙ qwen-30B ταυτόχρονα. Αυτός ο launcher
#   φορτώνει το coding μοντέλο ΑΝΤΙ για το gemma στο ίδιο port (8080). Τρέξ' τον
#   όταν κάνεις coding sessions· τρέξε πάλι το start-llama-vulkan.ps1 για να
#   γυρίσεις στο gemma για τα market briefings.
#
#   Qwen3-Coder-30B-A3B: MoE με μόνο 3B active params → πολύ γρήγορο inference
#   ακόμα και με partial offload, purpose-built για agentic coding + tool use.
#
# DOWNLOAD (μία φορά, ~17GB) — από PowerShell με ενεργό python env:
#   huggingface-cli download unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF `
#     Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf `
#     --local-dir $ModelsDir
#   (Αν το Q4_K_XL είναι οριακό στη VRAM, κατέβασε το Q4_K_M — λίγο μικρότερο.)

param(
    # Which interface the OpenAI-compatible server listens on.
    #
    # 127.0.0.1 means only this machine can reach it, which is what you want:
    # the endpoint has no authentication, so on a shared network a wider bind
    # hands your GPU to everyone on it.
    #
    # The Docker stack is the exception. A container reaches the host through
    # host.docker.internal, which is NOT loopback, so start-ai.bat passes
    # 0.0.0.0 explicitly when it is starting that stack. The npm Agent Canvas
    # path needs no such thing.
    [string]$BindHost = "127.0.0.1",

    # Concurrent request slots. Each slot gets (Ctx / Parallel) tokens.
    [int]$Parallel = 1,

    # Total context across all slots. Qwen3-Coder is far cheaper per token than
    # gemma here: 4 kv-heads and head dim 128 give 51 KiB/token against gemma's
    # 223, so 32k of context costs 1.59 GB instead of 6.97 GB. Context is worth
    # more for coding than for briefings, so the default is higher.
    [int]$Ctx = 32768,

    [int]$VramGB = 16,
    # Covers the desktop, driver overhead and llama.cpp's compute buffers,
    # which the arithmetic below does not model: measured 2026-09-04, the
    # budget predicted 14.28 GB for Qwen and the card reported 14.51 GB.
    [double]$ReserveGB = 2.0,

    # ---- GPU dispatch length -------------------------------------------------
    # Windows resets the GPU if a single dispatch does not finish within
    # TdrDelay, which is 2 seconds at the Windows default. If the reset then
    # fails, the machine bugchecks 0x116 VIDEO_TDR_FAILURE. That has now
    # happened twice on this box with an identical signature (parameter 4 = 0xd
    # both times) and not one event 4101 — the driver never recovers, it goes
    # straight to the bugcheck.
    #
    # ubatch is the PHYSICAL compute batch: the size of one kernel dispatch.
    # Measured here at 449 prompt tok/s aggregate, a 256-token dispatch is
    # roughly half a second of GPU time on its own, and four slots contending
    # push the wall-clock of any single dispatch well past that. 128 halves the
    # exposure at a small throughput cost, which is the right trade when the
    # alternative is a reboot.
    #
    # Raise it only if you are prepared to test under sustained four-slot load.
    [int]$Batch = 256,
    [int]$UBatch = 128,

    # 0 = compute the largest value that fits. Set a number to override.
    [int]$Ngl = 0,

    # Keep the Mixture-of-Experts weights on the CPU.
    #
    # In an MoE model the experts are most of the file, but only a few of
    # them fire per token. With them on the CPU the GPU holds only attention
    # and the shared layers, which is small enough that EVERY layer fits and
    # the KV cache has room to grow. Set -CpuMoe:$false to get the old
    # behaviour of fitting as many whole layers as the budget allows.
    #
    # The trade is generation speed, which depends on your RAM bandwidth.
    # Measure it with scripts/bench_moe.py before deciding either way.
    [switch]$CpuMoe = $true,

    # The middle ground. Keep only the first N layers' experts on the CPU and
    # put the rest on the GPU, trading VRAM back for generation speed. Takes
    # precedence over -CpuMoe when set. 0 = not used.
    [int]$NCpuMoe = 0,

    # Require this key on every request (llama-server --api-key). Set by
    # start-ai.bat, whose 0.0.0.0 bind is reachable from the LAN. Empty =
    # no key, which is fine on a loopback bind.
    [string]$ApiKey = ""
)

$ErrorActionPreference = "Stop"

# Where llama.cpp and the models live. Derived from this script's own location
# so a clone anywhere works without editing the file, with env overrides:
#   LOCAL_AI_LLAMA_DIR   folder holding llama-server.exe
#   LOCAL_AI_MODELS_DIR  folder holding your .gguf files
#   LOCAL_AI_MODEL       full path to one .gguf, overriding both
$RepoRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$AiRoot    = Split-Path -Parent $RepoRoot
$LLAMA_DIR = if ($env:LOCAL_AI_LLAMA_DIR)  { $env:LOCAL_AI_LLAMA_DIR }  else { Join-Path $AiRoot "llama" }
$ModelsDir = if ($env:LOCAL_AI_MODELS_DIR) { $env:LOCAL_AI_MODELS_DIR } else { Join-Path $AiRoot "models" }
$MODEL_PATH = if ($env:LOCAL_AI_MODEL) { $env:LOCAL_AI_MODEL } else { Join-Path $ModelsDir "Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf" }
$SERVER_EXE = Join-Path $LLAMA_DIR "llama-server.exe"
$PORT  = 8080
$ALIAS = "qwen3-coder-30b"

Write-Host "=== MOSKY Coding Backend: Qwen3-Coder-30B-A3B (MoE) on RX 9070 XT / Vulkan ===" -ForegroundColor Cyan

# 1. Check GGUF
if (-not (Test-Path $MODEL_PATH)) {
    Write-Host "ERROR: Coding GGUF not found at $MODEL_PATH" -ForegroundColor Red
    Write-Host "Download it first (see the DOWNLOAD block at the top of this script)." -ForegroundColor Yellow
    Write-Host "Fallback: run start-llama-vulkan.ps1 to keep using gemma until the download finishes." -ForegroundColor Yellow
    exit 1
}
$modelSize = [math]::Round((Get-Item $MODEL_PATH).Length / 1GB, 1)
Write-Host "Model: $MODEL_PATH ($modelSize GB)" -ForegroundColor Green

# 2. Ensure llama-server binary (shared with the gemma launcher)
if (-not (Test-Path $SERVER_EXE)) {
    Write-Host "llama-server.exe not found in $LLAMA_DIR. Extract a win-vulkan-x64 build there." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Stopping the previous server. Added 2026-09-04 after a HARD HANG at 00:45:25
# -- no bugcheck, no minidump, no 4101, and NOTHING written to the event log
# between 00:35 and the freeze. The kernel simply stopped.
#
# What preceded it: three model swaps in forty minutes (gemma -> qwen -> gemma),
# each one `Stop-Process -Force` on a process holding ~14 GB of VRAM, followed
# by `Start-Sleep -Seconds 1` and then an immediate 14 GB allocation by the next
# server. One second is not enough for the AMD driver to reclaim 14 GB from a
# process it did not get to close cleanly, so the incoming server begins
# allocating while the outgoing allocations are still unwinding.
#
# So: ask the process to close first, force it only if it refuses, wait for it
# to actually exit, and then WATCH THE VRAM COUNTER until the driver has handed
# the memory back. The counter is real -- \GPU Adapter Memory(*)\Dedicated
# Usage reads 0.54 GB with no server running and ~14 GB with one loaded.
# ---------------------------------------------------------------------------
function Get-GpuVramInUse {
    $s = (Get-Counter '\GPU Adapter Memory(*)\Dedicated Usage' -ErrorAction SilentlyContinue).CounterSamples
    if (-not $s) { return $null }
    return ($s | Measure-Object -Property CookedValue -Sum).Sum
}

function Stop-LlamaServerAndWaitForVram {
    param([int]$TimeoutSec = 45, [double]$IdleGB = 2.0)

    $procs = @(Get-Process -Name "llama-server" -ErrorAction SilentlyContinue)
    if ($procs.Count -gt 0) {
        Write-Host ("Stopping {0} previous llama-server process(es)..." -f $procs.Count)
        foreach ($p in $procs) { try { $p.CloseMainWindow() | Out-Null } catch {} }
        Start-Sleep -Milliseconds 800
        foreach ($p in $procs) {
            if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
        foreach ($p in $procs) { try { $p.WaitForExit(20000) | Out-Null } catch {} }
    }

    $before = Get-GpuVramInUse
    if ($null -eq $before) {
        Write-Host "  (no GPU memory counter available - falling back to a 5s wait)" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        return
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $t0 = Get-Date
    $used = $before
    while ((Get-Date) -lt $deadline -and $used -gt ($IdleGB * 1GB)) {
        Start-Sleep -Milliseconds 500
        $used = Get-GpuVramInUse
        if ($null -eq $used) { break }
    }
    $waited = ((Get-Date) - $t0).TotalSeconds

    if ($null -ne $used -and $used -gt ($IdleGB * 1GB)) {
        Write-Host ("  WARNING: {0:N2} GB of VRAM is still held after {1:N0}s. Starting anyway, but a swap on top of unreleased memory is what hung the machine on 2026-09-04." -f ($used/1GB), $waited) -ForegroundColor Yellow
    } else {
        Write-Host ("  VRAM released: {0:N2} GB -> {1:N2} GB in {2:N1}s" -f ($before/1GB), ($used/1GB), $waited) -ForegroundColor Green
    }
}

# 3. Kill any old instance (frees the whole GPU before loading the coding model)
Stop-LlamaServerAndWaitForVram
Start-Sleep -Seconds 2

# 4. Launch flags — EMPIRICALLY TUNED (measured on this exact machine, 2026-07).
#
#   Benchmarked results (generation speed, short context):
#     old flags (-ngl 46, q4_0 KV, no flash-attn) ......... 36 tok/s   <- previous
#     -ngl 99 + flash-attn + q8_0 KV ..................... 94 tok/s   <- current (2.6x)
#   Also: prompt eval 809 -> 1049 tok/s, model load 1-5 min -> ~15 s.
#
#   WHY it got faster: the old config was NOT expert-offload-limited, it was
#   KV-cache-limited. Enabling flash attention (-fa on) collapses KV memory, which
#   freed enough VRAM to offload ALL 48 layers (-ngl 99) instead of 46.
#
#   The July note that followed here said --n-cpu-moe "made things strictly worse"
#   (ncmoe 24 -> 36 t/s, 16 -> 49, 8 -> 68, 0 -> 94) and that spilling ~5 GB of
#   experts into shared RAM was "FINE". Both were true only relative to -ngl 99
#   with the card overcommitted - and that overcommit is what bugchecked this
#   machine four times (0x116). The VRAM budget above ended it, and with it the
#   94 t/s. The comparison that matters is now against the SAFE baseline.
#
#   RE-MEASURED 2026-09-05, scripts/bench_moe.py, -c 32768, one slot:
#
#     config                       VRAM      prompt     generate
#     budget-fitted layers (old)  15.43 GB   310 t/s    39.2 t/s   <- at the edge
#     --cpu-moe   (DEFAULT now)    4.69 GB   361 t/s    22.3 t/s   <- huge margin
#     --n-cpu-moe 24              12.75 GB   496 t/s    39.5 t/s
#     --n-cpu-moe 16              15.33 GB   751 t/s    48.0 t/s   <- at the edge
#
#   llama.cpp b10816 (2026-09-04) vs the b9587 this ships with, same --cpu-moe
#   config, same script, side install at C:\AI\llama-b10816, --no-mmap verified
#   honoured (18.6 GB private bytes):
#     b9587                        4.69 GB   361 t/s    22.3 t/s
#     b10816                       4.73 GB   235 t/s    20.8 t/s   <- slower here
#   NOT adopted. One measurement, on one card, with 2 GB of the previous
#   model's VRAM still held at start; a regression signal, not a verdict.
#   Its log is terse by default (-lv 1 restores the device/kernel lines), so
#   which Vulkan path changed is unknown. Re-test before trusting either way.
#
#   --cpu-moe is the default because it is the only row with real headroom on a
#   16 GB card, prompt processing is FASTER (every layer's attention is on the
#   GPU), and it is the configuration an 8 GB card can run at all. The price is
#   generation speed, which now depends on RAM bandwidth.
#
#   -NCpuMoe N is kept as an opt-in, with a warning: the split configurations
#   drive the GPU and all 16 CPU cores flat out at the same time, the highest
#   combined power draw this box can produce. The machine hard-reset - no dump,
#   no bugcheck code - seconds after the -NCpuMoe 24 benchmark completed, with
#   the desktop being unlocked at that moment. Cause not proven; the correlation
#   is recorded here so nobody makes it the default unattended.
#
#   -fa on         : flash attention — the single biggest win.
#   --cache-type-* : q8_0 (better quality than the old q4_0, and now affordable).
#   --cache-reuse  : reuse identical prompt prefixes — agents resend the same system
#                    prompt every turn, so this cuts repeated prompt processing.
#   -t 16          : match the 9950X physical cores.
#   --jinja        : the model's own chat template (correct tool-call/stop handling).
Write-Host "Starting llama-server (Qwen3-Coder) on port $PORT..."
$logOut = Join-Path $LLAMA_DIR "llama-coder.log"
$logErr = Join-Path $LLAMA_DIR "llama-coder.err"
# ---------------------------------------------------------------------------
# VRAM BUDGET -- same treatment as start-llama-vulkan.ps1, which asked a 16 GB
# card for 29.8 GB and bugchecked the machine four times on 2026-09-03
# (0x116 VIDEO_TDR_FAILURE). This launcher had the identical `-ngl 99` with
# `-c 65536`, so it carried the same fault.
#
# Qwen3-Coder is cheap on KV and expensive on weights -- the opposite balance
# to gemma. From the GGUF header: 48 layers, 4 kv-heads, head dim 128.
#
#     weights                             16.45 GB
#     KV cache @ -c 65536, q8_0, -fa on    3.19 GB   (51.0 KiB per token)
#     ------------------------------------------
#     requested                           19.64 GB   from a 16 GB card
#
# The weights alone (16.45 GB) exceed the card, so -ngl 99 cannot work here
# either -- but because the KV cache is small, context is nearly free: 32k
# costs 1.59 GB, where the same context on gemma costs 6.97 GB.
# ---------------------------------------------------------------------------
$LAYERS = 48                       # qwen3moe block_count, from the GGUF header
$KV_KIB_PER_TOKEN = 51.0           # q8_0 with -fa on, derived from that header

$modelGB = (Get-Item $MODEL_PATH).Length / 1GB
$kvGB    = $KV_KIB_PER_TOKEN * $Ctx / 1MB
$usable  = $VramGB - $ReserveGB
$budget  = $usable - $kvGB

Write-Host ""
Write-Host "VRAM budget:" -ForegroundColor Cyan
Write-Host ("  card {0} GB, reserved for the desktop {1} GB -> usable {2:N2} GB" -f $VramGB, $ReserveGB, $usable)
Write-Host ("  KV cache at -c {0} (q8_0, -fa on): {1:N2} GB" -f $Ctx, $kvGB)
Write-Host ("  weights: {0:N2} GB" -f $modelGB)

if ($budget -le 0) {
    Write-Host ""
    Write-Host ("REFUSING TO START: -c $Ctx needs {0:N2} GB of KV cache, which does not fit in {1:N2} GB on its own." -f $kvGB, $usable) -ForegroundColor Red
    exit 1
}

if ($Ngl -gt 0) {
    $NGL = $Ngl
    $fits = [Math]::Floor($LAYERS * ($budget / $modelGB))
    if ($NGL -gt $fits) {
        Write-Host ("  WARNING: -Ngl $NGL exceeds the {0} layers that fit. The driver will spill to system RAM over PCIe, which is what causes the 0x116 hangs." -f $fits) -ForegroundColor Yellow
    }
} else {
    $NGL = [Math]::Floor($LAYERS * ($budget / $modelGB))
    if ($NGL -gt $LAYERS) { $NGL = $LAYERS }
    if ($NGL -lt 0) { $NGL = 0 }
}

if ($CpuMoe -or $NCpuMoe -gt 0) {
    # The budget above sized whole layers, weights and all. With the experts
    # kept on the CPU only the attention and shared tensors are offloaded,
    # a fraction of each layer, so every layer fits and the budget does not
    # apply. What lands on the GPU is now the KV cache plus that fraction.
    $NGL = $LAYERS
    Write-Host ("  -CpuMoe: expert weights stay in system RAM; all {0} layers' attention on the GPU" -f $LAYERS) -ForegroundColor Green
}

$onGpuGB = $modelGB * ($NGL / $LAYERS)
if ($CpuMoe -or $NCpuMoe -gt 0) {
    # The whole-file estimate is wrong here and printing it looked like an
    # overcommit when the card actually held 4.69 GB. Say what is true: the
    # KV cache is the known part, the weight share is the non-expert tensors,
    # and the measured totals are in the table above.
    Write-Host ("  -> experts in system RAM; GPU holds the non-expert weights + {0:N2} GB KV (measured totals in this file's header)" -f $kvGB) -ForegroundColor Green
} else {
    Write-Host ("  -> offloading $NGL of $LAYERS layers ({0:N2} GB) + {1:N2} GB KV = {2:N2} GB of {3:N2} GB usable" -f $onGpuGB, $kvGB, ($onGpuGB + $kvGB), $usable) -ForegroundColor Green
}
if ($NGL -lt $LAYERS) {
    Write-Host ("     ({0} layers run on the CPU. Lower -Ctx to buy back a few.)" -f ($LAYERS - $NGL))
}
Write-Host ""

# Newer llama.cpp (b10816+) deprecates --no-mmap in favour of --load-mode, and
# older builds (b9587) do not know --load-mode at all. Ask the binary which it
# is, once, with no model and no GPU, and pass the flag it understands. The
# README tells people to download a recent release, so both must work.
$loadFlag = @("--no-mmap")
try {
    $help = & $SERVER_EXE --help 2>&1 | Out-String
    if ($help -match "--load-mode") { $loadFlag = @("--load-mode", "none") }
} catch {}

$args = @(
    "-m", $MODEL_PATH,
    "--alias", $ALIAS,
    "--host", $BindHost,
    "--port", $PORT,
    "--n-gpu-layers", $NGL,
    "-c", $Ctx,
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "-fa", "on",
    "--cache-reuse", "256",
    "-t", "16",
    "--jinja",
    "--batch-size", $Batch,
    "--ubatch-size", $UBatch,
    "--cont-batching",
    "--parallel", $Parallel,
    "--no-warmup"
)
$args += $loadFlag
if ($NCpuMoe -gt 0) { $args += @("--n-cpu-moe", $NCpuMoe) }
elseif ($CpuMoe)    { $args += "--cpu-moe" }

if ($ApiKey) { $args += @("--api-key", $ApiKey) }
$proc = Start-Process -FilePath $SERVER_EXE -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
Write-Host "llama-server (coder) started (PID $($proc.Id)). Logs: $logOut / $logErr" -ForegroundColor Green

# 5. Wait for readiness on /v1/models
$ready = $false
for ($i = 0; $i -lt 180; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$PORT/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
    if (($i % 10) -eq 0) { Write-Host "." -NoNewline }
}
Write-Host ""
if ($ready) {
    Write-Host "Qwen3-Coder backend READY on http://localhost:$PORT (alias: $ALIAS)" -ForegroundColor Green
    Write-Host "Dev agents (coder/tester/reviewer/security/debugger) will now use it." -ForegroundColor Cyan
    Write-Host "TIP: set CODING_MODEL=$ALIAS in .env if you change the alias." -ForegroundColor DarkGray
} else {
    Write-Host "Backend did not become ready in time. Check logs: $logErr" -ForegroundColor Yellow
    Write-Host "If VRAM is tight, lower --n-gpu-layers (e.g. 40) or use the Q4_K_M GGUF." -ForegroundColor Yellow
}
