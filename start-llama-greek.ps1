# start-llama-greek.ps1 - SECOND llama-server, on the CPU, alongside the GPU one.
#
# WHY THIS EXISTS
# 16GB of VRAM fits exactly ONE model, so start-llama-vulkan.ps1 and
# start-llama-coder.ps1 both KILL the previous server before starting. That
# makes a two-model pipeline impossible... on the GPU.
#
# But this box has 61.6GB of RAM and a 16-core / 32-thread 9950X that sits idle
# while llama-server works the GPU. A small specialist model runs perfectly well
# there. So this launcher deliberately does the opposite of the other two:
#   * -ngl 0        : NOTHING on the GPU. VRAM untouched, gemma keeps running.
#   * --port 8081   : its own port, so :8080 is undisturbed.
#   * it does NOT kill any existing llama-server.
#
# Point code at it with MOSKY_LLM2_URL=http://127.0.0.1:8081/v1 , or per call
# with llm_client.chat(..., base_url="http://127.0.0.1:8081/v1").
#
# Speed expectation: CPU inference is memory-bandwidth bound. An 8B at Q4 lands
# in single-digit-to-low-teens tokens/sec here. That is fine for a final
# rendering pass over already-computed notes; it is NOT fine for the map stage.

param(
    # Q6_K, not Q4: this model is here for Greek MORPHOLOGY, which is the first
    # thing quantisation damages in an 8B. It lives in RAM, not in the 16GB of
    # VRAM, so the usual size ceiling does not apply.
    # Default resolves next to the repository; LOCAL_AI_MODELS_DIR or a
    # full -Model path override it. It used to name this machine's C:\AI.
    [string]$Model = "",
    [string]$Alias = "krikri-8b-greek",
    [int]$Port = 8081,
    [int]$Threads = 12,          # leave cores for the GPU server's own work
    [int]$Context = 16384
)

$ErrorActionPreference = "Stop"

if (-not $Model) {
    $RepoRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
    $AiRoot    = Split-Path -Parent $RepoRoot
    $ModelsDir = if ($env:LOCAL_AI_MODELS_DIR) { $env:LOCAL_AI_MODELS_DIR } else { Join-Path $AiRoot "models" }
    $Model = Join-Path $ModelsDir "llama-krikri-8b-instruct-q6_k.gguf"
}
$LLAMA_DIR = if ($env:LOCAL_AI_LLAMA_DIR) { $env:LOCAL_AI_LLAMA_DIR } else { Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "llama" }
$SERVER_EXE = Join-Path $LLAMA_DIR "llama-server.exe"

Write-Host "=== MOSKY secondary LLM (CPU) ===" -ForegroundColor Cyan

if (-not (Test-Path $SERVER_EXE)) {
    Write-Host "ERROR: llama-server.exe not found in $LLAMA_DIR" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $Model)) {
    Write-Host "ERROR: model not found: $Model" -ForegroundColor Red
    Write-Host "Download it first, e.g.:" -ForegroundColor Yellow
    Write-Host '  python -c "from huggingface_hub import hf_hub_download; hf_hub_download(''ilsp/Llama-Krikri-8B-Instruct-GGUF'', ''llama-krikri-8b-instruct-q6_k.gguf'', local_dir=r''<your models folder>'')"'
    exit 1
}

# Is something already on this port?
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "Port $Port already has a listener - assuming the secondary is up." -ForegroundColor Yellow
    exit 0
}

# Report what the GPU server is doing, and DO NOT touch it.
$existing = Get-Process -Name "llama-server" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing llama-server PID(s): $($existing.Id -join ', ') - leaving them ALONE." -ForegroundColor Green
} else {
    Write-Host "No llama-server running yet (that is fine; this one is independent)." -ForegroundColor Yellow
}

$sizeGB = [math]::Round((Get-Item $Model).Length / 1GB, 2)
$freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
Write-Host "Model: $Model ($sizeGB GB) | free RAM: $freeGB GB | threads: $Threads"
if ($sizeGB + 2 -gt $freeGB) {
    Write-Host "WARNING: not much RAM headroom. It will still run but may page." -ForegroundColor Yellow
}

$logOut = Join-Path $LLAMA_DIR "llama-server-8081.log"
$logErr = Join-Path $LLAMA_DIR "llama-server-8081.err"

$serverArgs = @(
    "-m", $Model,
    "--alias", $Alias,
    "--host", "127.0.0.1",
    "--port", $Port,
    "--n-gpu-layers", "0",       # THE point: stay off the GPU entirely
    "-c", $Context,
    "-t", $Threads,
    "-fa", "on",
    "--batch-size", "256",
    "--ubatch-size", "128",
    "--parallel", "1",
    "--no-warmup"
)

$proc = Start-Process -FilePath $SERVER_EXE -ArgumentList $serverArgs -WindowStyle Hidden `
                      -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
Write-Host "Started PID $($proc.Id). Logs: $logOut"

$ready = $false
for ($i = 0; $i -lt 120; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
    if (($i % 10) -eq 0) { Write-Host "." -NoNewline }
}
Write-Host ""

if ($ready) {
    Write-Host "READY on http://127.0.0.1:$Port (alias: $Alias, CPU only)" -ForegroundColor Green
    Write-Host "Use it with:  `$env:MOSKY_LLM2_URL = 'http://127.0.0.1:$Port/v1'"
    $gpu = Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/models" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($gpu -and $gpu.StatusCode -eq 200) {
        Write-Host "GPU server on :8080 still healthy - both models are live." -ForegroundColor Green
    }
} else {
    Write-Host "Did not become ready. Check $logErr" -ForegroundColor Red
    exit 1
}
