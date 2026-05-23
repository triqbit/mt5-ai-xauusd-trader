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

# 3. Create required directories
echo "Creating required directories..."
mkdir -p data logs models/trained reports

# 4. Install dependencies
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
    # Attempt standard installation
    if ! $PIP install -r requirements.txt; then
        echo ""
        echo "----------------------------------------------------------"
        echo "WARNING: Standard installation failed (likely TA-Lib)."
        echo "Attempting resilient installation (ignoring TA-Lib)..."
        echo "----------------------------------------------------------"

        # Create a temporary requirements file without TA-Lib
        grep -iv "TA-Lib" requirements.txt > requirements-temp.txt
        $PIP install -r requirements-temp.txt
        rm requirements-temp.txt

        echo ""
        echo "Attempting to install TA-Lib separately..."
        if ! $PIP install TA-Lib; then
            echo ""
            echo "NOTICE: TA-Lib C-library not found on system."
            echo "The bot will use internal fallbacks for technical indicators."
            echo "To enable full TA-Lib support, please install the C-library:"
            echo "  - Linux: sudo apt-get install libta-lib0"
            echo "  - macOS: brew install ta-lib"
            echo "----------------------------------------------------------"
        fi
    fi
else
    echo "requirements.txt not found, skipping installation."
fi

# 4. Setup .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from template..."
        cp .env.example .env
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///data/trades.db|" .env
        chmod 600 .env
    else
        echo ".env.example not found, cannot create .env."
    fi
else
    echo ".env already exists, skipping."
fi

echo "=========================================="
echo "Bootstrap COMPLETE."
echo "CRITICAL: Run 'make doctor' or 'python3 scripts/doctor.py' to verify your installation."
