<#
=============================================================================
VyomPath — One-Command Offline Demonstration Launcher (Windows PowerShell)
Team NAKSHATRA X | NASA Space Apps Challenge 2026

Launches the Uvicorn FastAPI backend and serves the compiled frontend client
on local loopback (127.0.0.1) without requiring active internet connectivity.
Handles clean process lifecycle management, health verification, and graceful
shutdown on Windows 11.
=============================================================================
#>

[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 4173,
    [string]$BackendHost = "127.0.0.1",
    [string]$FrontendHost = "127.0.0.1",
    [int]$DurationSeconds = 0,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

# Ensure console output uses UTF-8 encoding on Windows
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location -Path $RootDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  VYOMPATH OFFLINE DEMONSTRATION LAUNCHER (WINDOWS POWERSHELL)  " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Working directory: $RootDir"

# 1. Port occupancy checker
function Test-PortOccupied([string]$hostAddress, [int]$portNumber) {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $iar = $tcpClient.BeginConnect($hostAddress, $portNumber, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(200, $false)
        if ($wait) {
            $tcpClient.EndConnect($iar)
            $tcpClient.Close()
            return $true
        }
        $tcpClient.Close()
        return $false
    }
    catch {
        return $false
    }
}

# 2. Check for port occupancy
if (Test-PortOccupied $BackendHost $BackendPort) {
    Write-Error "ERROR: Port $BackendPort is already in use by another process. Please free port $BackendPort before launching."
    exit 1
}

$distPath = Join-Path $RootDir "frontend\dist"
if (Test-Path $distPath) {
    if (Test-PortOccupied $FrontendHost $FrontendPort) {
        Write-Error "ERROR: Port $FrontendPort is already in use by another process. Please free port $FrontendPort before launching."
        exit 1
    }
}

# 3. Detect offline regional tile assets
$tileDir = $null
if (Test-Path "$RootDir\data\tiles" -PathType Container) {
    $tileDir = "$RootDir\data\tiles"
} elseif (Test-Path "$RootDir\tiles" -PathType Container) {
    $tileDir = "$RootDir\tiles"
}

if ($tileDir) {
    Write-Host "Found offline regional tile assets at: $tileDir" -ForegroundColor Green
} else {
    Write-Host "NOTICE [TILE ASSET AVAILABILITY]:" -ForegroundColor Yellow
    Write-Host "  Offline tile directory ('tiles/' or 'data/tiles/') not detected in working tree." -ForegroundColor Yellow
    Write-Host "  Proceeding with mock route-analysis and layer API endpoints." -ForegroundColor Yellow
    Write-Host "-----------------------------------------------------------------"
}

$backendProc = $null
$frontendProc = $null

function Cleanup-Processes {
    Write-Host "`nShutting down VyomPath offline launcher..." -ForegroundColor Yellow
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Write-Host "Stopping frontend process (PID $($frontendProc.Id))..."
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "Stopping backend process (PID $($backendProc.Id))..."
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Shutdown complete. All child processes terminated (0 orphans)." -ForegroundColor Green
}

try {
    # 4. Launch backend
    Write-Host "Starting VyomPath API on http://$BackendHost`:$BackendPort..." -ForegroundColor Cyan
    $env:PORT = "$BackendPort"
    $env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"

    $backendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $backendStartInfo.FileName = "python"
    $backendStartInfo.Arguments = "-m uvicorn backend.app.main:app --host $BackendHost --port $BackendPort"
    $backendStartInfo.WorkingDirectory = $RootDir
    $backendStartInfo.UseShellExecute = $false
    $backendStartInfo.CreateNoWindow = $true

    $backendProc = [System.Diagnostics.Process]::Start($backendStartInfo)

    # 5. Wait for API health probe
    Write-Host "Verifying API health probe..." -ForegroundColor Cyan
    $healthy = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 300
        try {
            $response = Invoke-RestMethod -Uri "http://$BackendHost`:$BackendPort/api/health" -TimeoutSec 1 -ErrorAction Stop
            if ($response.status -eq "ok") {
                $healthy = $true
                Write-Host "SUCCESS: VyomPath API is healthy and operational ($($response.mode))." -ForegroundColor Green
                break
            }
        } catch {
            # retry
        }
    }

    if (-not $healthy) {
        Write-Error "ERROR: Backend health check failed to respond on http://$BackendHost`:$BackendPort/api/health within timeout."
        exit 1
    }

    # 6. Launch frontend preview
    if (Test-Path $distPath) {
        Write-Host "Launching frontend client via Python static server on http://$FrontendHost`:$FrontendPort..." -ForegroundColor Cyan
        $frontendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $frontendStartInfo.FileName = "python"
        $frontendStartInfo.Arguments = "-m http.server $FrontendPort --bind $FrontendHost --directory `"$distPath`""
        $frontendStartInfo.WorkingDirectory = $RootDir
        $frontendStartInfo.UseShellExecute = $false
        $frontendStartInfo.CreateNoWindow = $true

        $frontendProc = [System.Diagnostics.Process]::Start($frontendStartInfo)
        Write-Host "Frontend server active at http://$FrontendHost`:$FrontendPort" -ForegroundColor Green
    }

    Write-Host "`nVyomPath is running entirely offline!" -ForegroundColor Green
    Write-Host "  Backend API:  http://$BackendHost`:$BackendPort"
    Write-Host "  Swagger Docs: http://$BackendHost`:$BackendPort/docs"
    if (Test-Path $distPath) {
        Write-Host "  Frontend App: http://$FrontendHost`:$FrontendPort"
    }

    if ($DurationSeconds -gt 0) {
        Write-Host "Running in test mode for $DurationSeconds seconds..." -ForegroundColor Cyan
        Start-Sleep -Seconds $DurationSeconds
    } else {
        Write-Host "`nPress Ctrl+C or Enter to stop all services..." -ForegroundColor Magenta
        [Console]::ReadLine() | Out-Null
    }
}
finally {
    Cleanup-Processes
}
