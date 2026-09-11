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
    # HOW, and why exactly this way. The first version ran
    #   icacls <dir> /inheritance:r /grant:r "me:(OI)(CI)F" ... /t
    # and left 5,236 files with an EMPTY ACL: /t strips inheritance from
    # every file too, but a grant carrying folder flags (OI)(CI) is not
    # applied to a file, so the files kept nothing - not even the owner
    # could read them (MEASURED 2026-09-12; repaired with takeown + /reset).
    # Now the explicit ACL goes on the TOP item only, and the children are
    # reset to INHERIT from it. A file target gets plain F.
    $grantsDir = @("${me}:(OI)(CI)F", "SYSTEM:(OI)(CI)F", "BUILTIN\Administrators:(OI)(CI)F")
    $grantsFile = @("${me}:F", "SYSTEM:F", "BUILTIN\Administrators:F")
    foreach ($t in $targets) {
        $isDir = (Get-Item $t).PSIsContainer
        $grants = if ($isDir) { $grantsDir } else { $grantsFile }
        icacls "$t" /inheritance:r /grant:r $grants /q | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Host "  FAILED: $t (exit $LASTEXITCODE)"; continue }
        # strangers with their own explicit entry (MEASURED: KQ\CodexSandboxUsers
        # on ~\.openhands survived /grant:r) are removed by name
        foreach ($ace in (Get-Acl $t).Access) {
            $id = [string]$ace.IdentityReference
            if ($id -notmatch "SYSTEM|BUILTIN\\Administrators" -and $id -ne $me) {
                icacls "$t" /remove:g "$id" /q | Out-Null
                Write-Host "  removed: $id"
            }
        }
        if ($isDir) {
            # children inherit the locked folder's ACL; /c keeps going past
            # files owned by another account (Docker created some)
            icacls "$t\*" /reset /t /c /q | Out-Null
        }
        Write-Host "  locked: $t"
    }
    # prove it: the owner can still read a file under every locked folder
    $broken = 0
    foreach ($t in $targets) {
        $sample = if ((Get-Item $t).PSIsContainer) { Get-ChildItem $t -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 } else { Get-Item $t }
        if ($sample) {
            try { [IO.File]::OpenRead($sample.FullName).Close() }
            catch { $broken++; Write-Host "  CANNOT READ $($sample.FullName) - undoing this folder"; icacls "$t" /reset /t /c /q | Out-Null }
        }
    }
    if ($broken -eq 0) { Write-Host "Done: you still read everything, nobody else does. Re-run with -Status to see it." }
    else { Write-Host "Something is off with $broken folder(s); they were reset to inherited. Run -Status and tell me." }
}
if ($Undo) {
    Write-Host "== restoring inheritance =="
    foreach ($t in $targets) {
        icacls "$t" /reset /t /c /q | Out-Null
        Write-Host "  restored: $t"
    }
}
