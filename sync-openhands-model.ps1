# sync-openhands-model.ps1
# Κρατά το μοντέλο που δείχνει/χρησιμοποιεί το OpenHands συγχρονισμένο με το
# μοντέλο που όντως φορτώνει ο launcher (gemma για market / qwen για coding).
# Καλείται αυτόματα από το start-ai.bat πριν ξεκινήσει ο OpenHands container.
#
# ΣΗΜΑΝΤΙΚΟ: γράφει UTF-8 ΧΩΡΙΣ BOM. Το Set-Content -Encoding utf8 στο PS 5.1
# προσθέτει BOM, που σπάει το json.loads του OpenHands (settings.json). Γι' αυτό
# χρησιμοποιούμε [IO.File]::WriteAllText με UTF8Encoding($false).
param([Parameter(Mandatory = $true)][string]$Model)

$oh = Join-Path $env:USERPROFILE ".openhands"
$settings = Join-Path $oh "settings.json"
$config = Join-Path $oh "config.toml"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (Test-Path $settings) {
    $raw = [System.IO.File]::ReadAllText($settings)
    $raw = $raw -replace "^\xEF\xBB\xBF", ""  # strip any existing BOM char
    $raw = [regex]::Replace($raw, '"llm_model"\s*:\s*"[^"]*"', '"llm_model":"' + $Model + '"')
    [System.IO.File]::WriteAllText($settings, $raw, $utf8NoBom)
    Write-Host "[sync] OpenHands settings.json -> $Model (utf-8, no BOM)" -ForegroundColor Green
}
else {
    Write-Host "[sync] settings.json not found (first run?) - OpenHands uses the LLM_MODEL env default." -ForegroundColor Yellow
}

if (Test-Path $config) {
    $raw = [System.IO.File]::ReadAllText($config)
    $raw = $raw -replace "^\xEF\xBB\xBF", ""
    $raw = [regex]::Replace($raw, '(?m)^\s*model\s*=\s*"[^"]*"', 'model = "' + $Model + '"')
    [System.IO.File]::WriteAllText($config, $raw, $utf8NoBom)
    Write-Host "[sync] OpenHands config.toml -> $Model (utf-8, no BOM)" -ForegroundColor Green
}
