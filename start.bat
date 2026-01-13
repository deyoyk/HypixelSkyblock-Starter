@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Server Manager - Installation ^& Startup
echo ==========================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed. Please install Python 3.7+ first.
    exit /b 1
)

echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed. Please install Node.js 18+ first.
    exit /b 1
)

echo Checking npm installation...
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm is not installed. Please install npm first.
    exit /b 1
)

echo.
echo Installing Python dependencies...
if exist requirements.txt (
    python -m pip install -r requirements.txt --quiet
    echo [OK] Python dependencies installed
) else (
    echo [WARN] requirements.txt not found, skipping Python dependencies
)

echo.
echo Installing Node.js dependencies...
if exist package.json (
    call npm install --silent
    echo [OK] Node.js dependencies installed
) else (
    echo [WARN] package.json not found, skipping Node.js dependencies
)

echo.
echo ==========================================
echo Starting servers...
echo ==========================================
echo.

echo Starting Python API server on port 5000...
start "API Server" /min cmd /c "python api_server.py > api_server.log 2>&1"
timeout /t 2 /nobreak >nul

echo Starting Next.js website on port 3000...
start "Next.js Server" /min cmd /c "npm run dev > next_server.log 2>&1"
timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo Servers are running!
echo ==========================================
echo.
echo API Server:    http://localhost:5000
echo Website:       http://localhost:3000
echo.
echo Logs:
echo   API:         api_server.log
echo   Next.js:     next_server.log
echo.
echo Servers are running in background windows.
echo Close those windows or press Ctrl+C in them to stop.
echo.
pause

