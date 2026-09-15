# run.ps1 - start the agentic-depot services (gateway, wallet, core, ui).
# ASCII only. Uses the repo-local .venv. Checks ports before starting and
# prints the taskkill command instead of failing silently on a conflict.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

$services = @(
    @{ Name = "gateway"; Port = 8080; Module = "gateway.app" },
    @{ Name = "wallet";  Port = 8081; Module = "wallet.app" },
    @{ Name = "core";    Port = 8082; Module = "core.app" }
)
$uiPort = 5174

Write-Host "agentic-depot launcher"
Write-Host "----------------------"

# 1. Port check (three backends + the UI dev server).
$conflict = $false
foreach ($port in @(8080, 8081, 8082, $uiPort)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        $owner = $conn.OwningProcess
        Write-Host ("Port {0} is already in use by PID {1}. Free it with:" -f $port, $owner)
        Write-Host ("    taskkill /PID {0} /F" -f $owner)
        $conflict = $true
    }
}
if ($conflict) {
    Write-Host "One or more ports are in use. Stop the listed processes and re-run run.ps1."
    exit 1
}

# 2. venv check.
if (-not (Test-Path $venvPython)) {
    Write-Host "No .venv found at $venvPython"
    Write-Host "Create it first:  uv sync"
    exit 1
}

# 3. Start the three backend services.
foreach ($svc in $services) {
    Write-Host ("Starting {0} on port {1} ..." -f $svc.Name, $svc.Port)
    Start-Process -FilePath $venvPython -ArgumentList @("-m", $svc.Module) -WorkingDirectory $root | Out-Null
}

# 4. Start the UI (Vite dev server) if scaffolded and npm is available.
# Resolve a runnable npm: Get-Command npm often points at npm.ps1, which
# Start-Process cannot execute (it would shell-open the file). Prefer the
# sibling npm.cmd; fall back to running "npm" through cmd.exe from PATH.
$uiDir = Join-Path $root "ui"
$uiStarted = $false
$npmCmd = $null
$npmArgsPrefix = @()
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    if ($npm.Source -match '\.cmd$') {
        $npmCmd = $npm.Source
    }
    else {
        $candidate = Join-Path (Split-Path $npm.Source) "npm.cmd"
        if (Test-Path $candidate) { $npmCmd = $candidate }
    }
}
if (-not $npmCmd) {
    # Last resort: let cmd.exe resolve npm from PATH.
    $npmCmd = "cmd.exe"
    $npmArgsPrefix = @("/c", "npm")
}

if ((Test-Path (Join-Path $uiDir "package.json")) -and $npm) {
    if (-not (Test-Path (Join-Path $uiDir "node_modules"))) {
        Write-Host "Installing UI dependencies (npm install) ..."
        Start-Process -FilePath $npmCmd -ArgumentList ($npmArgsPrefix + @("install")) -WorkingDirectory $uiDir -Wait -NoNewWindow
    }
    Write-Host ("Starting ui on port {0} (Vite) ..." -f $uiPort)
    # Own window so Vite's output stays visible for troubleshooting.
    Start-Process -FilePath $npmCmd -ArgumentList ($npmArgsPrefix + @("run", "dev")) -WorkingDirectory $uiDir | Out-Null
    $uiStarted = $true
}
else {
    Write-Host "npm or ui/package.json not found; skipping UI (backends only)."
}

# 5. Wait for backend health.
function Test-Health($port) {
    try {
        $r = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $port) -TimeoutSec 2
        return ($r.status -eq "ok")
    }
    catch {
        return $false
    }
}

Write-Host "Waiting for services to become healthy ..."
foreach ($svc in $services) {
    $ok = $false
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Health $svc.Port) { $ok = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if ($ok) {
        Write-Host ("  OK    {0,-8} http://127.0.0.1:{1}/health" -f $svc.Name, $svc.Port)
    }
    else {
        Write-Host ("  FAIL  {0,-8} did not report healthy on port {1}" -f $svc.Name, $svc.Port)
    }
}

# 6. Verify the Vite dev server bound its port (no /health for the UI in Phase 0).
if ($uiStarted) {
    $bound = $false
    for ($i = 0; $i -lt 60; $i++) {
        $c = Get-NetTCPConnection -LocalPort $uiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($c) { $bound = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if ($bound) { Write-Host ("  OK    {0,-8} http://127.0.0.1:{1}" -f "ui", $uiPort) }
    else { Write-Host ("  FAIL  {0,-8} Vite did not bind port {1}" -f "ui", $uiPort) }
}

Write-Host ""
Write-Host "Service processes started in the background. Stop them with taskkill or by closing their windows."
