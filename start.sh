#!/bin/bash

set -e

echo "=========================================="
echo "Server Manager - Installation & Startup"
echo "=========================================="
echo ""

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "ERROR: Python is not installed. Please install Python 3.7+ first."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm is not installed. Please install npm first."
    exit 1
fi

echo ""
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    echo "Checking for venv module..."
    if ! $PYTHON_CMD -m venv --help > /dev/null 2>&1; then
        echo "✗ ERROR: venv module not available"
        echo ""
        echo "On Ubuntu/Debian, install python3-venv:"
        echo "  sudo apt update && sudo apt install -y python3-venv"
        echo ""
        exit 1
    fi
    
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "✗ ERROR: Failed to create virtual environment"
        echo ""
        echo "On Ubuntu/Debian, you may need:"
        echo "  sudo apt update && sudo apt install -y python3-venv python3-full"
        exit 1
    fi
    echo "✓ Virtual environment created"
fi

if [ ! -f "venv/bin/activate" ]; then
    echo "✗ ERROR: Virtual environment activation script not found"
    echo "Try removing venv directory and running again: rm -rf venv"
    exit 1
fi

source venv/bin/activate || {
    echo "✗ ERROR: Failed to activate virtual environment"
    exit 1
}
echo "✓ Virtual environment activated"

echo ""
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "✗ ERROR: Failed to install Python dependencies"
        exit 1
    fi
    echo "✓ Python dependencies installed"
else
    echo "⚠ Warning: requirements.txt not found, skipping Python dependencies"
fi

echo ""
echo "Installing Node.js dependencies..."
if [ -f "package.json" ]; then
    npm install --silent
    echo "✓ Node.js dependencies installed"
else
    echo "⚠ Warning: package.json not found, skipping Node.js dependencies"
fi

echo ""
echo "=========================================="
echo "Starting servers..."
echo "=========================================="
echo ""

API_PID_FILE="api_server.pid"
NEXT_PID_FILE="next_server.pid"

cleanup() {
    echo ""
    echo "Shutting down servers..."
    if [ -f "$API_PID_FILE" ]; then
        API_PID=$(cat "$API_PID_FILE")
        if ps -p "$API_PID" > /dev/null 2>&1; then
            kill "$API_PID" 2>/dev/null || true
        fi
        rm -f "$API_PID_FILE"
    fi
    if [ -f "$NEXT_PID_FILE" ]; then
        NEXT_PID=$(cat "$NEXT_PID_FILE")
        if ps -p "$NEXT_PID" > /dev/null 2>&1; then
            kill "$NEXT_PID" 2>/dev/null || true
        fi
        rm -f "$NEXT_PID_FILE"
    fi
    pkill -f "python.*api_server.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    deactivate 2>/dev/null || true
    echo "Servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Python API server on port 5000..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    venv/bin/python api_server.py > api_server.log 2>&1 &
else
    $PYTHON_CMD api_server.py > api_server.log 2>&1 &
fi
API_PID=$!
echo "$API_PID" > "$API_PID_FILE"
echo "✓ API server started (PID: $API_PID)"

sleep 2

if ! ps -p "$API_PID" > /dev/null 2>&1; then
    echo "✗ ERROR: API server failed to start. Check api_server.log for details."
    rm -f "$API_PID_FILE"
    exit 1
fi

echo ""
echo "Starting Next.js website on port 3000..."
cd "$BASE_DIR"
npm run dev > next_server.log 2>&1 &
NEXT_PID=$!
echo "$NEXT_PID" > "$NEXT_PID_FILE"
echo "✓ Next.js server started (PID: $NEXT_PID)"

sleep 3

if ! ps -p "$NEXT_PID" > /dev/null 2>&1; then
    echo "✗ ERROR: Next.js server failed to start. Check next_server.log for details."
    rm -f "$NEXT_PID_FILE"
    cleanup
    exit 1
fi

echo ""
echo "=========================================="
echo "Servers are running!"
echo "=========================================="
echo ""
echo "API Server:    http://localhost:5000"
echo "Website:       http://localhost:3000"
echo ""
echo "Logs:"
echo "  API:         api_server.log"
echo "  Next.js:     next_server.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

wait

