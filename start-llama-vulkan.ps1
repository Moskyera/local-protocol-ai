# start-llama-vulkan.ps1  (renamed for clarity - now the reliable choice for your RX 9070 XT)

# Reliable high-performance backend for MOSKY using llama.cpp + Vulkan on AMD RX 9070 XT (RDNA4 / gfx1201).

# This is now the RECOMMENDED primary backend (HIP prebuilts had kernel incompatibilities on this card).

# Vulkan gives solid GPU offload on Windows AMD without ROCm headaches.

# Target: good tok/s for the 26B QAT MoE + reliable OpenAI-compatible server for OpenHands.



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

    # Concurrent request slots. The document pipeline summarises chunks that are
    # INDEPENDENT of each other, so raising this turns a serial queue into real
    # throughput. Each slot gets (Ctx / Parallel) tokens; a 6000-char chunk plus
    # a 900-token answer needs roughly 2400. Set MOSKY_MAP_WORKERS to match.
    [int]$Parallel = 1,

    # Total context across all slots. THIS IS THE MAIN VRAM DIAL — see the
    # budget block below. It was 65536, which alone asks for 13.95 GB of KV
    # cache on a 16 GB card, on top of a 15.84 GB model.
    [int]$Ctx = 16384,

    # Physical VRAM. Win32_VideoController reports 4 GB for this card (the old
    # 32-bit AdapterRAM truncation), so it cannot be queried reliably.
    [int]$VramGB = 16,

    # Left for the Windows desktop, the compositor, driver overhead AND
    # llama.cpp's own compute buffers, which the arithmetic below does not
    # model. Measured 2026-09-04: the budget predicted 14.28 GB for Qwen and
    # the card actually reported 14.51 GB in use, so the shortfall is real.
    # Taking this to zero is what makes the GPU hang.
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

    # 0 = compute the largest value that actually fits. Set a number to override.
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
    #
    # MEASURED 2026-09-05 on this file, -c 32768, one slot (scripts/bench_moe.py):
    #   -CpuMoe : 5.54 GB VRAM, prompt 282 t/s, generate 22.9 t/s
    # Read from the GGUF header: 13.43 GiB of the 15.83 GiB file is experts;
    # the non-expert weights that go to the GPU are only 2.40 GiB. The heavy
    # part of gemma on the GPU is not its weights, it is the KV cache - 223 KiB
    # per token, 6.97 GB at 32k - and that is the same with or without -CpuMoe.
    #
    # Still OFF by default, for one reason only: the old whole-layer config has
    # not been benchmarked on gemma with the same script, so there is no number
    # to say whether 22.9 t/s is a gain or a loss for the briefings this
    # launcher exists to produce. Measure that, then decide. Not before.
    [switch]$CpuMoe = $false,

    # The middle ground. Keep only the first N layers' experts on the CPU and
    # put the rest on the GPU, trading VRAM back for generation speed. Takes
    # precedence over -CpuMoe when set. 0 = not used.
    [int]$NCpuMoe = 0,

    # Native tool calling. MEASURED 2026-09-11: with --jinja, llama.cpp b9587
    # renders gemma-4's own chat template and parses its <|tool_call> syntax
    # into structured tool_calls; without it the model prints the call as
    # text and nothing runs. Required by the voice agent (start-voice.bat).
    # OFF here because the briefings and Agent Canvas were measured without
    # it and nothing in this launcher's own numbers was taken with it.
    [switch]$Jinja = $false,

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
$MODEL_PATH = if ($env:LOCAL_AI_MODEL) { $env:LOCAL_AI_MODEL } else { Join-Path $ModelsDir "gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf" }


$SERVER_EXE = Join-Path $LLAMA_DIR "llama-server.exe"

$PORT = 8080

$ALIAS = "gemma-4-26b-qat"



Write-Host "=== MOSKY Reliable LLM Backend: llama.cpp (Gemma 4 26B-A4B QAT MoE on AMD RX 9070 XT) ===" -ForegroundColor Cyan

Write-Host "Note: Using latest win-vulkan-x64 prebuilt (switched from HIP because of kernel incompatibilities on RX 9070 XT / gfx1201). Vulkan is currently the most reliable GPU backend for your card on Windows." -ForegroundColor Yellow

Write-Host "Primary for OpenHands + all market tools. (Ollama fully removed from boot - voice not used.)" -ForegroundColor Yellow



# 1. Check GGUF

if (-not (Test-Path $MODEL_PATH)) {

    Write-Host "ERROR: GGUF not found at $MODEL_PATH" -ForegroundColor Red

    Write-Host "Run the download step first (see previous instructions or python hf_hub_download)."

    exit 1

}

$modelSize = [math]::Round((Get-Item $MODEL_PATH).Length / 1GB, 1)

Write-Host "Model: $MODEL_PATH ($modelSize GB) - Unsloth QAT for best speed/quality on AMD" -ForegroundColor Green



# 2. Ensure llama-server binary (Vulkan build)

# We switched from the problematic HIP radeon prebuilt to the official Vulkan one (much better compatibility on RX 9070 XT).

if (-not (Test-Path $SERVER_EXE)) {

    Write-Host ""

    Write-Host "llama-server.exe not found in $LLAMA_DIR." -ForegroundColor Red

    Write-Host "Please extract a recent 'llama-bxxxx-bin-win-vulkan-x64.zip' into $LLAMA_DIR."

    Write-Host "Latest recommended: https://github.com/ggml-org/llama.cpp/releases (look for win-vulkan-x64)"

    exit 1

}



# Validate the modern packaging (tiny launcher exe + large llama-server-impl.dll + backend DLLs/kernels).

# The "llama-server.exe" in b9585+ win-* zips is intentionally a small loader (~0.01 MB). The real code is in the -impl.dll.

$implDll = Join-Path $LLAMA_DIR "llama-server-impl.dll"

$hasLauncher = Test-Path $SERVER_EXE

$hasImpl = Test-Path $implDll

$implSize = if ($hasImpl) { [math]::Round( (Get-Item $implDll).Length / 1MB , 1) } else { 0 }



if (-not $hasLauncher -or -not $hasImpl -or $implSize -lt 5) {

    Write-Host "ERROR: Missing proper launcher or impl DLL (impl=$implSize MB). The backend files are incomplete." -ForegroundColor Red

    Write-Host "Run the extraction/merge step again (use the full self-contained block for your Vulkan or CPU zip)." -ForegroundColor Yellow

    exit 1

}

Write-Host "Backend packaging OK: launcher present + impl DLL $implSize MB (Vulkan backend DLLs)." -ForegroundColor Green

$vulkanDll = Join-Path $LLAMA_DIR "ggml-vulkan.dll"

if (Test-Path $vulkanDll) {

    $vMB = [math]::Round( (Get-Item $vulkanDll).Length / 1MB , 0 )

    Write-Host "Vulkan: ggml-vulkan.dll present ($vMB MB) - ready for GPU offload on RX 9070 XT." -ForegroundColor Green

} else {

    Write-Host "Note: Vulkan support is in the main ggml.dll + vulkan runtime (no separate ggml-vulkan.dll in newer builds)." -ForegroundColor Yellow

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

# 3. Kill any old instance

Stop-LlamaServerAndWaitForVram



# 4. Launch the server with optimized flags for this MoE model + AMD (Vulkan)

# Vulkan handles offloading automatically and is currently the most reliable GPU path for RX 9070 XT on Windows.

# --n-gpu-layers is computed above. 'Vulkan will use what it can' was the
# problem, not the design: what it 'uses' beyond VRAM is system RAM over
# PCIe, and that spill is what hangs the GPU.

# -c 8192 : reduced for much faster initial load of the 15.8 GB model on 16 GB card.

# After the server is up, you can restart the PS1 with higher -c if you need more context.

# --batch-size etc. for good agent throughput.

Write-Host "Starting llama-server on port $PORT (Vulkan / AMD RX 9070 XT)..."

$logOut = Join-Path $LLAMA_DIR "llama-server.log"

$logErr = Join-Path $LLAMA_DIR "llama-server.err"

# TUNED 2026-07 (same physics as the coder launcher, measured on this machine):

#   Enabling flash attention (-fa on) collapses KV-cache memory, which frees enough

#   VRAM to offload ALL layers (-ngl 99) instead of 50. Measured: gemma runs at

#   ~63 tok/s with this config. q8_0 KV is also BETTER quality than the old q4_0.

#   Context reduced 128k -> 64k: measured to make no speed difference, and the

#   OpenHands condenser keeps prompts well under it.

# ---------------------------------------------------------------------------
# VRAM BUDGET  --  added 2026-09-03 after four bugchecks in one day.
#
# The previous configuration was -ngl 99 with -c 65536, described in a comment
# as "request full offload (Vulkan will use what it can)". What it actually
# asked for, measured from the GGUF header and the model file:
#
#     weights                        15.84 GB
#     KV cache @ 65536, q8_0, -fa    13.95 GB   (223.1 KiB per token:
#                                                30 layers, 25x8 + 5x2 kv-heads,
#                                                head dim 512, k and v)
#     -------------------------------------
#     total requested                29.79 GB   from a 16 GB card
#
# Even at -c 4096 the weights alone (15.84 GB) do not leave room on a 16 GB
# card, so -ngl 99 was never viable here. The AMD driver hides this by spilling
# to system RAM over PCIe: it works, slowly, until a large eviction stalls the
# GPU past the TDR timeout. Windows then resets the GPU, the reset fails, and
# the machine bugchecks 0x116 VIDEO_TDR_FAILURE. That happened four times on
# 2026-09-03 (12:12, 17:06, 17:11, 17:26) and there is not a single event 4101
# in the log, meaning the driver never once recovered.
#
# So the launcher now computes what fits and offloads exactly that many layers.
# ---------------------------------------------------------------------------
$LAYERS = 30                       # gemma4 block_count, from the GGUF header
$KV_KIB_PER_TOKEN = 223.1          # q8_0 with -fa on, derived from that header

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
    Write-Host "Lower -Ctx. Every doubling of context doubles the KV cache." -ForegroundColor Yellow
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
    # overcommit ("22.81 GB of 14.00 usable") when the card actually held
    # 5.54 GB. Say what is true: the KV cache is the known part, the weight
    # share is the non-expert tensors, and the measured total lives up top.
    Write-Host ("  -> experts in system RAM; GPU holds the non-expert weights + {0:N2} GB KV (measured total in this file's header)" -f $kvGB) -ForegroundColor Green
} else {
    Write-Host ("  -> offloading $NGL of $LAYERS layers ({0:N2} GB) + {1:N2} GB KV = {2:N2} GB of {3:N2} GB usable" -f $onGpuGB, $kvGB, ($onGpuGB + $kvGB), $usable) -ForegroundColor Green
}
if ($NGL -lt $LAYERS) {
    Write-Host ("     ({0} layers run on the CPU. That is the price of not crashing; raise -Ctx down or -VramGB up if you have headroom.)" -f ($LAYERS - $NGL))
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
    "--batch-size", $Batch,

    "--ubatch-size", $UBatch,

    "--cont-batching",

    "--parallel", $Parallel,

    "--no-warmup"
)
$args += $loadFlag
if ($NCpuMoe -gt 0) { $args += @("--n-cpu-moe", $NCpuMoe) }
elseif ($CpuMoe)    { $args += "--cpu-moe" }
if ($Jinja)          { $args += "--jinja" }



if ($ApiKey) { $args += @("--api-key", $ApiKey) }
$proc = Start-Process -FilePath $SERVER_EXE -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru

Write-Host "llama-server started (PID $($proc.Id)). Logs: $logOut / $logErr . First load of 15.8GB model can take 1-5+ min..."

Write-Host "Context and offload are computed above from the model size and the card. If you need more context, raise -Ctx and expect fewer layers on the GPU; the launcher will refuse a value that cannot fit."



# 5. Wait for server to be ready (health check on /v1/models)

$ready = $false

$maxWait = 240  # up to ~8 minutes for first-time 16GB model load

for ($i = 0; $i -lt $maxWait; $i++) {

    try {

        $resp = Invoke-WebRequest -Uri "http://localhost:$PORT/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop

        if ($resp.StatusCode -eq 200) {

            $ready = $true

            break

        }

    } catch {}

    Start-Sleep -Seconds 2

    if (($i % 10) -eq 0) { Write-Host "." -NoNewline }

}

Write-Host ""

if ($ready) {

    Write-Host "llama.cpp backend READY on http://localhost:$PORT (model alias: $ALIAS)" -ForegroundColor Green

    Write-Host "OpenHands will connect via host.docker.internal:$PORT (OpenAI compatible)"

} else {

    Write-Host "GPU/HIP attempt did not become ready in time (common with current prebuilts on RX 9070 XT)." -ForegroundColor Yellow

    Write-Host "Falling back to reliable CPU mode (still fully functional for agent + tools)..."

    Get-Process -Name "llama-server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

    Start-Sleep 2

    $cpuArgs = @("-m", $MODEL_PATH, "--alias", $ALIAS, "--host", $BindHost, "--port", $PORT, "--n-gpu-layers", "0", "-c", "131072", "--batch-size", "128", "--cont-batching")

    $proc = Start-Process -FilePath $SERVER_EXE -ArgumentList $cpuArgs -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru

    Write-Host "CPU fallback started (PID $($proc.Id)). Waiting for readiness..."

    for ($i = 0; $i -lt 60; $i++) {

        try {

            $resp = Invoke-WebRequest -Uri "http://localhost:$PORT/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop

            if ($resp.StatusCode -eq 200) { $ready = $true; break }

        } catch {}

        Start-Sleep 3

    }

    if ($ready) {

        Write-Host "✅ CPU fallback READY on http://localhost:$PORT" -ForegroundColor Green

    } else {

        Write-Host "WARNING: Even CPU fallback slow. Check logs." -ForegroundColor Yellow

    }

}



# Keep the script alive a bit so the caller sees the status, then exit (server runs in background)

Start-Sleep -Seconds 3

if ($ready) {

    Write-Host "Backend ready for OpenHands. The start-ai.bat should now proceed to start the containers." -ForegroundColor Cyan

} else {

    Write-Host "The llama starter timed out. The start-ai.bat will keep waiting (or timeout). Check logs for 'loading model' progress." -ForegroundColor Yellow

}



