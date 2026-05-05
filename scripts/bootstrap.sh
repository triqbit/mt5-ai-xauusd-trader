#!/bin/bash
set -e

echo "=== MT5 AI/ML Trading Bot Bootstrapper ==="

# 1. Check Python
python3 --version || { echo "Python 3 not found"; exit 1; }

# 2. Setup virtual environment if not present
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Install dependencies
echo "Installing dependencies..."
# Use venv pip if it exists
if [ -f "venv/bin/pip" ]; then
    PIP="venv/bin/pip"
elif [ -f "venv/Scripts/pip" ]; then
    PIP="venv/Scripts/pip"
else
    PIP="pip"
fi

$PIP install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt..."
    # On Linux/macOS, MetaTrader5 and other win32-marked packages will be skipped automatically by pip
    $PIP install -r requirements.txt
else
    echo "requirements.txt not found, skipping installation."
fi

# 4. Setup .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from template..."
        cp .env.example .env
    else
        echo ".env.example not found, cannot create .env."
    fi
else
    echo ".env already exists, skipping."
fi

echo "=========================================="
echo "Bootstrap COMPLETE. Run 'make doctor' to verify."
