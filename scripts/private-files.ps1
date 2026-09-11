<#
.SYNOPSIS
  Make the files that hold your secrets and your data readable by YOU only.

.DESCRIPTION
  MEASURED 2026-09-11: .env, memory\, logs\ and the Agent Canvas key files
  inherited 'Authenticated Users: read' from C:\ - every local account on
  this PC, including sandbox accounts other tools create, could read the
  API keys, the dictated notes, the per-turn voice log and the vector DB.

  -Apply  removes inheritance on those paths and grants full control to
          you, SYSTEM and Administrators only (icacls; no elevation needed
          for files you own). Also reports stray copies of .env and backup
          zips that contain one, so you can delete them yourself.
  -Status only reports.
  -Undo   restores inheritance on the same paths.

  Docker bind mounts and the WSL sandbox still see what the launcher mounts
  for them; this script does not change that (see docs/PRIVACY.md).
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$Status,
    [switch]$Undo
)
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AiRoot = Split-Path -Parent $RepoRoot
$me = [Security.Principal.WindowsIdentity]::GetCurrent().Name

if (-not ($Apply -or $Status -or $Undo)) {
    Write-Host "Usage: private-files.ps1 -Apply | -Status | -Undo"
    exit 1
}

$targets = @(
    (Join-Path $RepoRoot ".env"),
    (Join-Path $RepoRoot "memory"),
    (Join-Path $RepoRoot "logs"),
    (Join-Path $RepoRoot "simplex_briefings"),
    (Join-Path $RepoRoot "backups"),
    (Join-Path $env:USERPROFILE ".openhands\agent-canvas"),
    (Join-Path $env:USERPROFILE ".openhands"),
    (Join-Path $env:USERPROFILE ".openhands-v1")
) | Where-Object { Test-Path $_ }

function Show-Acl($path) {
    $acl = Get-Acl $path
    $others = @($acl.Access | Where-Object { $_.IdentityReference -notmatch "SYSTEM|Administrators|$([regex]::Escape($me.Split('\')[-1]))" })
    $flag = if ($others.Count -gt 0) { "  <-- readable by: " + (($others | ForEach-Object { $_.IdentityReference }) -join ", ") } else { "  (you, SYSTEM, Administrators only)" }
    Write-Host ("  {0}{1}" -f $path, $flag)
}

Write-Host "== who can read your data (owner: $me) =="
foreach ($t in $targets) { Show-Acl $t }

Write-Host "== stray copies of .env =="
$strays = Get-ChildItem -Path $AiRoot -Recurse -Force -Filter ".env" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -ne (Join-Path $RepoRoot ".env") -and $_.FullName -notmatch "node_modules|site-packages" }
if ($strays) { $strays | ForEach-Object { Write-Host "  $($_.FullName)  <-- another copy of your keys" } } else { Write-Host "  (none besides the repo's own)" }
$zips = Get-ChildItem -Path (Join-Path $RepoRoot "backups") -Filter "*.zip" -ErrorAction SilentlyContinue
foreach ($z in $zips) {
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $entries = [IO.Compression.ZipFile]::OpenRead($z.FullName).Entries | Where-Object { $_.FullName -match '(^|/)\.env$|vector_db' }
        if ($entries) { Write-Host "  $($z.FullName) contains: $(($entries | ForEach-Object { $_.FullName }) -join ', ')  <-- plaintext keys in a backup" }
    } catch {}
}

if ($Apply) {
    Write-Host "== applying owner-only ACLs =="
    foreach ($t in $targets) {
        icacls "$t" /inheritance:r /grant:r "${me}:(OI)(CI)F" "SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" /t /q | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Host "  locked: $t" } else { Write-Host "  FAILED: $t (exit $LASTEXITCODE)" }
    }
    Write-Host "Done. Re-run with -Status to see the result."
}
if ($Undo) {
    Write-Host "== restoring inheritance =="
    foreach ($t in $targets) {
        icacls "$t" /inheritance:e /t /q | Out-Null
        Write-Host "  restored: $t"
    }
}
