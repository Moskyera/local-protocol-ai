# Stop Agent Canvas being reachable from the network.
#
# Agent Canvas listens on 0.0.0.0:8000 and has no option to change that - only
# --port. Everything else in this project binds to 127.0.0.1, so this is the
# one hole, and it is a real one: in its default mode the API key is injected
# into the page automatically, so anyone who can open the address gets full
# access to an agent that can read and write your files.
#
# This adds a Windows Firewall rule blocking incoming connections to port 8000.
# Your own browser still reaches it, because loopback traffic never touches the
# firewall.
#
# Run it by right-clicking and choosing "Run with PowerShell", or from a normal
# PowerShell window - it will ask for administrator rights itself.

$ErrorActionPreference = "Stop"
$RuleName = "Block Agent Canvas 8000 inbound"
$Port     = 8000

# Re-launch as administrator if we are not already. Creating a firewall rule
# needs it, and failing halfway with an access-denied message helps nobody.
$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Asking for administrator rights..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`""
    )
    return
}

Write-Host ""
Write-Host "Blocking inbound connections to port $Port" -ForegroundColor Cyan
Write-Host ""

$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  The rule already exists. Making sure it is enabled." -ForegroundColor Yellow
    Enable-NetFirewallRule -DisplayName $RuleName
} else {
    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Description "Agent Canvas binds 0.0.0.0:8000 with no way to restrict it. Loopback is unaffected, so your own browser still works." `
        -Direction Inbound `
        -LocalPort $Port `
        -Protocol TCP `
        -Action Block `
        -Profile Any `
        -Enabled True | Out-Null
    Write-Host "  Rule created." -ForegroundColor Green
}

# Say what is actually there now, rather than assuming the call worked.
Write-Host ""
$rule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if (-not $rule) {
    Write-Host "  FAILED - the rule is still not present." -ForegroundColor Red
    Write-Host "  Add it by hand: Windows Defender Firewall with Advanced Security" -ForegroundColor Red
    Write-Host "  -> Inbound Rules -> New Rule -> Port -> TCP 8000 -> Block" -ForegroundColor Red
    Read-Host "`nPress Enter to close"
    exit 1
}

$filter = $rule | Get-NetFirewallPortFilter
Write-Host "  Verified:" -ForegroundColor Green
Write-Host ("    enabled   : {0}" -f $rule.Enabled)
Write-Host ("    direction : {0}" -f $rule.Direction)
Write-Host ("    action    : {0}" -f $rule.Action)
Write-Host ("    profiles  : {0}" -f $rule.Profile)
Write-Host ("    port      : {0}/{1}" -f $filter.LocalPort, $filter.Protocol)
Write-Host ""
Write-Host "  Your own browser still reaches http://localhost:8000 - loopback" -ForegroundColor Gray
Write-Host "  traffic does not go through the firewall. Other machines cannot." -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to close"
