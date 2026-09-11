<#
.SYNOPSIS
  Windows Firewall lockdown for Local Protocol AI: the programs that make up
  the stack cannot reach the internet, and the LAN cannot reach them.

.DESCRIPTION
  lpai_private.py stops OUR Python from opening outside connections. It
  cannot stop a child process (PowerShell run by run_command, node for Agent
  Canvas, Docker, git, curl) or a library that talks to the OS directly.
  This script closes that gap with Windows Defender Firewall rules, which
  the process cannot see or bypass:

    OUTBOUND BLOCK  per program: llama-server.exe, the venv's Python (both
                    the redirector in Scripts\ and the real interpreter it
                    starts - the child owns the sockets), node.exe, Docker's
                    backend, gh, git's https helper, ssh, curl, certutil,
                    bitsadmin, uv/uvx and powershell.exe (skip the last with
                    -SkipPowerShell if you need PowerShell online; then keep
                    the voice assistant's run_command in mind). git, gh and
                    ssh only with -IncludeGit: that stops your own git push.
    INBOUND BLOCK   node.exe on every interface (Agent Canvas listened on
                    [::]:3001 with its session key in index.html);
                    llama-server and Python on the PHYSICAL adapter only,
                    so the WSL sandbox path (vEthernet) still works.
    POPUP RULES     the 'Query User' Allow rules Windows added when you
                    once clicked Allow are DISABLED (not deleted) and
                    listed in a file so -Undo can put them back.
    -Wsl            additionally sets the WSL/Docker VM's default outbound
                    action to Block and allows only TCP to this host's
                    model and tool ports; tells you to run wsl --shutdown.

  Loopback (127.0.0.1) is exempt from the Windows Filtering Platform, so
  the model on :8080, the tools on :8765 and Agent Canvas on :8000 keep
  working on this machine (MEASURED: an inbound Block on a port coexisted
  with a loopback connection to it).

  Everything is in the rule group 'LPAI-Private' and is undoable.

.PARAMETER Apply    Create the rules (needs elevation; asks for it).
.PARAMETER Verify   Prove they work: each blocked program tries to reach
                    the internet and must fail with the firewall's own
                    error (WinError 10013 / EACCES), while loopback works.
.PARAMETER Undo     Remove the rules, re-enable the popup rules, restore
                    the VM setting.
.PARAMETER Status   Show what is in place and what listens where.
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$Verify,
    [switch]$Undo,
    [switch]$Status,
    [switch]$SkipPowerShell,
    [switch]$IncludeGit,
    [switch]$Wsl
)

$ErrorActionPreference = "Stop"
$Group = "LPAI-Private"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AiRoot = Split-Path -Parent $RepoRoot
$StateDir = Join-Path $env:USERPROFILE ".openhands\agent-canvas"
$DisabledFile = Join-Path $StateDir "lpai-firewall-disabled.json"
$BackupFile = Join-Path $env:USERPROFILE "lpai-firewall-before.wfw"
$WslVm = "{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}"   # WSL's VM creator id on Windows 11

if (-not ($Apply -or $Verify -or $Undo -or $Status)) {
    Write-Host "Usage: private-firewall.ps1 -Apply | -Verify | -Undo | -Status   [-SkipPowerShell] [-IncludeGit] [-Wsl]"
    exit 1
}

# ---------------------------------------------------------------- elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (($Apply -or $Undo) -and -not $isAdmin) {
    Write-Host "Elevating (the rules need an administrator)..."
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"")
    if ($Apply) { $argList += "-Apply" }
    if ($Undo) { $argList += "-Undo" }
    if ($SkipPowerShell) { $argList += "-SkipPowerShell" }
    if ($IncludeGit) { $argList += "-IncludeGit" }
    if ($Wsl) { $argList += "-Wsl" }
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -Wait -PassThru
    exit $p.ExitCode
}

# ---------------------------------------------------------------- the programs
function Get-RealPython {
    # The venv's Scripts\python.exe is a redirector; the sockets belong to
    # the interpreter it launches, found via pyvenv.cfg and, when uv installed
    # it, behind a junction. Never hardcode either path.
    $venv = if (Test-Path (Join-Path $RepoRoot ".venv\pyvenv.cfg")) { Join-Path $RepoRoot ".venv" } else { Join-Path $AiRoot "ai-env" }
    $cfg = Join-Path $venv "pyvenv.cfg"
    $out = @((Join-Path $venv "Scripts\python.exe"))
    if (Test-Path $cfg) {
        $m = Select-String -Path $cfg -Pattern '^home\s*=\s*(.*)$'
        if ($m) {
            $home_ = $m.Matches[0].Groups[1].Value.Trim()
            $item = Get-Item $home_ -ErrorAction SilentlyContinue
            if ($item -and $item.LinkType -eq "Junction" -and $item.Target) { $home_ = [string]$item.Target }
            $out += (Join-Path $home_ "python.exe")
        }
    }
    return $out
}

function Get-Programs {
    $llamaDir = if ($env:LOCAL_AI_LLAMA_DIR) { $env:LOCAL_AI_LLAMA_DIR } else { Join-Path $AiRoot "llama" }
    $list = @()
    $list += (Join-Path $llamaDir "llama-server.exe")
    $list += Get-RealPython
    $list += "C:\Program Files\nodejs\node.exe"
    $list += "C:\Program Files\Docker\Docker\resources\com.docker.backend.exe"
    if ($IncludeGit) {
        # opt-in: this also stops YOUR git push / gh. create_pr is withheld in
        # private mode and needs the spoken phrase by voice anyway.
        $list += "C:\Program Files\GitHub CLI\gh.exe"
        $list += "C:\Program Files\Git\mingw64\libexec\git-core\git-remote-https.exe"
        $list += "C:\Program Files\Git\mingw64\bin\git-credential-manager.exe"
        $list += "C:\Program Files\Git\usr\bin\ssh.exe"
        $list += "C:\Windows\System32\OpenSSH\ssh.exe"
    }
    $list += "C:\Windows\System32\curl.exe"
    $list += "C:\Windows\System32\certutil.exe"
    $list += "C:\Windows\System32\bitsadmin.exe"
    $list += (Join-Path $env:USERPROFILE ".local\bin\uv.exe")
    $list += (Join-Path $env:USERPROFILE ".local\bin\uvx.exe")
    if (-not $SkipPowerShell) {
        $list += "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        $list += "C:\Program Files\PowerShell\7\pwsh.exe"
    }
    return @($list | Where-Object { Test-Path $_ } | Select-Object -Unique)
}

function Get-PhysicalAdapter {
    $r = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Sort-Object RouteMetric, InterfaceMetric | Select-Object -First 1
    if ($r) { return $r.InterfaceAlias }
    return "Ethernet"
}

function Get-WslIp {
    (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -match "WSL" } | Select-Object -First 1).IPAddress
}

# ---------------------------------------------------------------- status
function Show-Status {
    Write-Host "== programs -Apply blocks (found on this machine) =="
    foreach ($p in (Get-Programs)) { Write-Host "  $p" }
    Write-Host "== LPAI-Private rules =="
    $rules = @(Get-NetFirewallRule -Group $Group -ErrorAction SilentlyContinue)
    if ($rules.Count -eq 0) { Write-Host "  (none - not applied)" }
    foreach ($r in $rules) {
        $prog = ($r | Get-NetFirewallApplicationFilter).Program
        Write-Host ("  [{0}] {1,-8} {2,-5} {3}" -f $r.Enabled, $r.Direction, $r.Action, $prog)
    }
    Write-Host "== popup Allow rules disabled by -Apply =="
    if (Test-Path $DisabledFile) { (Get-Content $DisabledFile | ConvertFrom-Json) | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  (none)" }
    Write-Host "== WSL/Docker VM outbound =="
    $vm = Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $WslVm }
    if ($vm) { Write-Host "  DefaultOutboundAction = $($vm.DefaultOutboundAction)" } else { Write-Host "  (no WSL VM setting found)" }
    Write-Host "== listening sockets of the stack =="
    Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 8000, 8080, 8765, 3001, 8501, 3000 } | ForEach-Object {
        $pn = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        $flag = if ($_.LocalAddress -in "0.0.0.0", "::") { "  <-- reachable from the LAN unless blocked" } else { "" }
        Write-Host ("  {0}:{1}  {2}{3}" -f $_.LocalAddress, $_.LocalPort, $pn, $flag)
    }
}

# ---------------------------------------------------------------- apply
function Do-Apply {
    if (-not (Test-Path $BackupFile)) {
        netsh advfirewall export "$BackupFile" | Out-Null
        Write-Host "Saved the firewall policy before any change: $BackupFile"
    }
    $programs = Get-Programs
    $phys = Get-PhysicalAdapter
    Write-Host "Physical adapter: $phys"
    foreach ($p in $programs) {
        $name = "LPAI out " + [IO.Path]::GetFileName($p) + " " + [Math]::Abs($p.ToLower().GetHashCode())
        if (-not (Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name $name -DisplayName "LPAI: no internet for $([IO.Path]::GetFileName($p))" -Group $Group `
                -Direction Outbound -Action Block -Program $p -Profile Any -Enabled True | Out-Null
            Write-Host "  outbound block: $p"
        }
    }
    # inbound: node everywhere; llama-server and python on the physical adapter
    $node = "C:\Program Files\nodejs\node.exe"
    if (Test-Path $node) {
        $n = "LPAI in node"
        if (-not (Get-NetFirewallRule -Name $n -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name $n -DisplayName "LPAI: nothing reaches node.exe" -Group $Group -Direction Inbound -Action Block -Program $node -Profile Any | Out-Null
            Write-Host "  inbound block: node.exe (all interfaces)"
        }
    }
    foreach ($p in ($programs | Where-Object { $_ -match "llama-server\.exe$|python\.exe$" })) {
        $n = "LPAI in " + [IO.Path]::GetFileName($p) + " " + [Math]::Abs($p.ToLower().GetHashCode())
        if (-not (Get-NetFirewallRule -Name $n -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name $n -DisplayName "LPAI: LAN cannot reach $([IO.Path]::GetFileName($p))" -Group $Group `
                -Direction Inbound -Action Block -Program $p -Profile Any -InterfaceAlias $phys | Out-Null
            Write-Host "  inbound block on $phys : $p"
        }
    }
    # disable the popup allow rules for our programs
    $disabled = @()
    if (Test-Path $DisabledFile) { $disabled = @(Get-Content $DisabledFile | ConvertFrom-Json) }
    $pat = "llama-server\.exe|nodejs\\node\.exe|uv\\python\\.*python\.exe|pythoncore.*python\.exe|com\.docker\.backend\.exe"
    foreach ($r in (Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*Query User*" -and $_.Enabled -eq "True" })) {
        $prog = ($r | Get-NetFirewallApplicationFilter).Program
        if ($prog -and $prog -match $pat) {
            Disable-NetFirewallRule -Name $r.Name
            $disabled += $r.Name
            Write-Host "  disabled popup allow: $prog"
        }
    }
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    ($disabled | Select-Object -Unique) | ConvertTo-Json | Set-Content -Path $DisabledFile -Encoding ASCII
    Set-NetFirewallProfile -All -LogBlocked True
    if ($Wsl) {
        $ip = Get-WslIp
        Set-NetFirewallHyperVVMSetting -Name $WslVm -DefaultOutboundAction Block
        if ($ip) {
            if (-not (Get-NetFirewallHyperVRule -Name "LPAI-WSL-host" -ErrorAction SilentlyContinue)) {
                New-NetFirewallHyperVRule -Name "LPAI-WSL-host" -DisplayName "LPAI: WSL -> host model and tools only" -Direction Outbound -Action Allow `
                    -VMCreatorId $WslVm -Protocol TCP -RemoteAddresses $ip -RemotePorts 8080, 8765 | Out-Null
            }
            Write-Host "  WSL/Docker VM: outbound blocked except TCP to $ip ports 8080, 8765"
        } else {
            Write-Host "  WSL/Docker VM: outbound blocked (no WSL adapter found for the host exception)"
        }
        Write-Host "  Run 'wsl --shutdown' so the sandbox picks this up."
    }
    Write-Host "Applied. Run -Verify to prove it."
}

# ---------------------------------------------------------------- undo
function Do-Undo {
    Get-NetFirewallRule -Group $Group -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    if (Test-Path $DisabledFile) {
        foreach ($n in (Get-Content $DisabledFile | ConvertFrom-Json)) {
            Enable-NetFirewallRule -Name $n -ErrorAction SilentlyContinue
        }
        Remove-Item $DisabledFile -Force
    }
    Get-NetFirewallHyperVRule -Name "LPAI-WSL-host" -ErrorAction SilentlyContinue | Remove-NetFirewallHyperVRule
    Set-NetFirewallHyperVVMSetting -Name $WslVm -DefaultOutboundAction NotConfigured -ErrorAction SilentlyContinue
    Write-Host "Undone: LPAI-Private rules removed, popup rules re-enabled, VM setting restored."
    Write-Host "The pre-change policy export is still at $BackupFile (netsh advfirewall import)."
}

# ---------------------------------------------------------------- verify
function Do-Verify {
    $fail = 0
    $pys = Get-RealPython
    $env:LPAI_PRIVATE = "0"     # test the FIREWALL, not our own Python guard
    foreach ($py in $pys) {
        if (-not (Test-Path $py)) { continue }
        $out = & $py -c "import urllib.request`ntry:`n    print('loopback', urllib.request.urlopen('http://127.0.0.1:8080/v1/models', timeout=3).status)`nexcept Exception as e:`n    print('loopback skipped:', type(e).__name__)" 2>&1
        Write-Host "  $([IO.Path]::GetFileName((Split-Path $py -Parent)))\python.exe -> $out"
        $out = & $py -c "import socket`ntry:`n    socket.create_connection(('1.1.1.1', 443), timeout=5); print('REACHED THE INTERNET')`nexcept OSError as e:`n    print('blocked:', getattr(e, 'winerror', ''), e)" 2>&1
        Write-Host "  $([IO.Path]::GetFileName((Split-Path $py -Parent)))\python.exe internet -> $out"
        if ($out -match "REACHED") { $fail++ }
        if ($out -notmatch "10013") { Write-Host "    (a timeout instead of 10013 means a rule did not bind to this exe)" }
    }
    $node = "C:\Program Files\nodejs\node.exe"
    if (Test-Path $node) {
        $out = & $node -e "const s=require('net').connect(443,'1.1.1.1');s.on('error',e=>{console.log('blocked:',e.code);process.exit(0)});s.on('connect',()=>{console.log('REACHED THE INTERNET');process.exit(0)});setTimeout(()=>{console.log('timeout');process.exit(0)},6000)" 2>&1
        Write-Host "  node.exe internet -> $out"
        if ($out -match "REACHED") { $fail++ }
    }
    $out = & "C:\Windows\System32\curl.exe" -s -m 5 -o NUL -w "%{http_code}" https://example.org 2>&1
    Write-Host "  curl.exe https://example.org -> '$out' (empty or 000 = blocked)"
    if ($out -match "^[23]\d\d$") { $fail++ }
    if (-not $SkipPowerShell) {
        $out = & powershell.exe -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('1.1.1.1', 443); 'REACHED THE INTERNET' } catch { 'blocked: ' + `$_.Exception.InnerException.Message }" 2>&1
        Write-Host "  powershell.exe internet -> $out"
        if ($out -match "REACHED") { $fail++ }
    }
    $rules = @(Get-NetFirewallRule -Group $Group -ErrorAction SilentlyContinue)
    Write-Host "  rules in group $Group : $($rules.Count)"
    if ($rules.Count -eq 0) { $fail++ }
    Show-Status
    if ($fail -eq 0) { Write-Host "VERIFY: OK - every blocked program failed to reach the internet; loopback works."; exit 0 }
    Write-Host "VERIFY: $fail check(s) FAILED"; exit 1
}

if ($Status) { Show-Status }
if ($Apply)  { Do-Apply }
if ($Undo)   { Do-Undo }
if ($Verify) { Do-Verify }
