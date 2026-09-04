<#
.SYNOPSIS
    Creates a timestamped backup of the current working state of the MOSKY project.
    Focuses on source code and configuration (not the 15GB+ model or huge venvs).

.DESCRIPTION
    Run this BEFORE doing risky experiments, agent self-modifications, or big changes.
    It will create a zip in the "backups" folder with everything needed to restore the "flawless" state.

    The sacred Telegram/briefing part is always protected anyway.

.EXAMPLE
    .\backup_current_state.ps1
#>

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupDir = "backups"
$zipName = "mosky-stable-$timestamp.zip"
$zipPath = Join-Path $backupDir $zipName

Write-Host "Creating backup of current working state..." -ForegroundColor Cyan

# Create backups folder if it doesn't exist
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

# What to include (the important parts after reorganization)
$include = @(
    "."
)

# What to exclude (huge or temporary)
$excludePatterns = @(
    "ai-env",
    "openbb-env",
    "llama",
    "llama-backup-*",
    "models",
    "backups",
    "__pycache__",
    "*.log",
    "logs",
    ".git",           # git history is already in the repo
    "*.gguf",
    "*.bin",
    "*.zip",
    "*.7z",
    "memory/openhands/vector_db"
)

# Build exclusion arguments for Compress-Archive (we'll use robocopy or manual filter for better control)
# For simplicity and reliability on Windows, we'll use a temp copy approach.

$tempDir = Join-Path $env:TEMP "mosky-backup-$timestamp"
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host "Copying files (this may take a minute)..." -ForegroundColor Yellow

# Use robocopy for fast copy with exclusions
$source = (Get-Location).Path

robocopy $source $tempDir `
    /MIR `
    /XD ai-env openbb-env llama "llama-backup*" models backups __pycache__ logs ".git" memory\openhands\vector_db `
    /XF *.gguf *.bin *.log *.zip *.7z *.tmp /NFL /NDL /NJH /NJS /NC /NS > $null

# Also exclude any remaining large binary folders if they slipped
Get-ChildItem $tempDir -Directory -Recurse | Where-Object { $_.Name -like "llama*" -or $_.Name -eq "models" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Create the zip
Write-Host "Compressing to $zipPath ..." -ForegroundColor Yellow
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force

# Cleanup temp
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "✅ Backup created successfully!" -ForegroundColor Green
Write-Host "   File: $zipPath"
Write-Host "   Size: $sizeMB MB"
Write-Host ""
Write-Host "To restore this state later:"
Write-Host "  1. Close all related processes (llama, Docker containers, Streamlit)"
Write-Host "  2. Extract the zip over your current market-agent folder (or rename current folder first)"
Write-Host "  3. Run: start-ai.bat"
Write-Host ""
Write-Host "For code-level rollback (recommended): use Git"
Write-Host "  git checkout stable-2026-06-12"
Write-Host ""
