# bench-llm.ps1 — μετράει την πραγματική ταχύτητα του llama-server στο :8080.
# Χρήση:  powershell -File bench-llm.ps1 [-Label "tuned"]
# Τυπώνει: prompt eval (tok/s), generation (tok/s). Σύγκρινε πριν/μετά από flag αλλαγές.
param([string]$Label = "current", [int]$MaxTokens = 200)

$body = @{
    model       = "qwen3-coder-30b"
    messages    = @(@{ role = "user"; content = "Write a Python class implementing an LRU cache with get and put. Code only, no explanation." })
    max_tokens  = $MaxTokens
    temperature = 0.1
    stream      = $false
} | ConvertTo-Json -Depth 5

try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $r = Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 300
    $sw.Stop()
}
catch {
    Write-Host "ERROR: llama-server not reachable on :8080 ($_)" -ForegroundColor Red
    exit 1
}

$t = $r.timings
Write-Host ""
Write-Host "=== BENCH [$Label] ===" -ForegroundColor Cyan
if ($t) {
    Write-Host ("  prompt eval : {0,7:N1} tok/s  ({1} tokens)" -f $t.prompt_per_second, $t.prompt_n) -ForegroundColor Green
    Write-Host ("  generation  : {0,7:N1} tok/s  ({1} tokens)" -f $t.predicted_per_second, $t.predicted_n) -ForegroundColor Green
}
Write-Host ("  wall clock  : {0,7:N1} s" -f $sw.Elapsed.TotalSeconds)
Write-Host ""
