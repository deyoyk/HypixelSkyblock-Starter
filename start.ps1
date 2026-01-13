Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Server Manager - Installation & Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed. Please install Python 3.7+ first." -ForegroundColor Red
    exit 1
}

Write-Host "Checking Node.js installation..."
try {
    $nodeVersion = node --version 2>&1
    Write-Host "Found: Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Node.js is not installed. Please install Node.js 18+ first." -ForegroundColor Red
    exit 1
}

Write-Host "Checking npm installation..."
try {
    $npmVersion = npm --version 2>&1
    Write-Host "Found: npm $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: npm is not installed. Please install npm first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installing Python dependencies..."
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt --quiet
    Write-Host "[OK] Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[WARN] requirements.txt not found, skipping Python dependencies" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Installing Node.js dependencies..."
if (Test-Path "package.json") {
    npm install --silent
    Write-Host "[OK] Node.js dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[WARN] package.json not found, skipping Node.js dependencies" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting servers..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$apiJob = $null
$nextJob = $null

try {
    Write-Host "Starting Python API server on port 5000..." -ForegroundColor Yellow
    $apiJob = Start-Process -FilePath "python" -ArgumentList "api_server.py" -RedirectStandardOutput "api_server.log" -RedirectStandardError "api_server.log" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    
    if (-not $apiJob.HasExited) {
        Write-Host "[OK] API server started (PID: $($apiJob.Id))" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] API server failed to start. Check api_server.log for details." -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Starting Next.js website on port 3000..." -ForegroundColor Yellow
    $nextJob = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -RedirectStandardOutput "next_server.log" -RedirectStandardError "next_server.log" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 3
    
    if (-not $nextJob.HasExited) {
        Write-Host "[OK] Next.js server started (PID: $($nextJob.Id))" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Next.js server failed to start. Check next_server.log for details." -ForegroundColor Red
        if ($apiJob -and -not $apiJob.HasExited) {
            Stop-Process -Id $apiJob.Id -Force -ErrorAction SilentlyContinue
        }
        exit 1
    }
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Servers are running!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "API Server:    http://localhost:5000" -ForegroundColor Cyan
    Write-Host "Website:       http://localhost:3000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Yellow
    Write-Host "  API:         api_server.log"
    Write-Host "  Next.js:     next_server.log"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Servers are running in the background." -ForegroundColor Green
    Write-Host "To stop them, run: Stop-Process -Id $($apiJob.Id),$($nextJob.Id) -Force" -ForegroundColor Yellow
    Write-Host ""
    
    while ($true) {
        Start-Sleep -Seconds 1
        if ($apiJob.HasExited -or $nextJob.HasExited) {
            Write-Host "One of the servers has stopped." -ForegroundColor Red
            break
        }
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($apiJob -and -not $apiJob.HasExited) {
        Stop-Process -Id $apiJob.Id -Force -ErrorAction SilentlyContinue
    }
    if ($nextJob -and -not $nextJob.HasExited) {
        Stop-Process -Id $nextJob.Id -Force -ErrorAction SilentlyContinue
    }
    exit 1
}

