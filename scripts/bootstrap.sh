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

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux detected. Installing CI/Linux compatible dependencies..."
    # Attempt to install requirements.txt but skip MetaTrader5 which is Windows-only
    if [ -f "requirements.txt" ]; then
        grep -v "MetaTrader5" requirements.txt > requirements-linux.txt
        $PIP install -r requirements-linux.txt
        rm requirements-linux.txt
    else
        echo "requirements.txt not found, skipping installation."
    fi
else
    if [ -f "requirements.txt" ]; then
        $PIP install -r requirements.txt
    else
        echo "requirements.txt not found, skipping installation."
    fi
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
