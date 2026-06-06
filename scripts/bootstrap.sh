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

# Install critical diagnostic tools first to ensure 'make doctor' works even if full install fails
echo "Installing core diagnostic tools (rich, pydantic, structlog, ruff)..."
$PIP install rich pydantic pydantic-settings structlog python-dotenv ruff

# Select best requirements file based on platform
OS_TYPE=$(uname -s)
REQ_FILE="requirements.txt"

if [[ "$OS_TYPE" == "Linux" && -f "requirements-linux.txt" ]]; then
    echo "Linux detected, using requirements-linux.txt"
    REQ_FILE="requirements-linux.txt"
elif [[ "$OS_TYPE" == "Darwin" && -f "requirements-linux.txt" ]]; then
    echo "macOS detected, using requirements-linux.txt as baseline"
    REQ_FILE="requirements-linux.txt"
fi

if [ -f "$REQ_FILE" ]; then
    echo "Installing production dependencies from $REQ_FILE..."
    # Attempt standard installation with extra index for torch cpu if needed
    PIP_INSTALL_CMD="$PIP install"
    if grep -q "+cpu" "$REQ_FILE"; then
        PIP_INSTALL_CMD="$PIP install --extra-index-url https://download.pytorch.org/whl/cpu"
    fi

    if ! $PIP_INSTALL_CMD -r "$REQ_FILE"; then
        echo ""
        echo "----------------------------------------------------------"
        echo "WARNING: Standard installation failed."
        echo "Attempting resilient installation (ignoring TA-Lib)..."
        echo "----------------------------------------------------------"

        # Create a temporary requirements file without TA-Lib
        echo "Creating temporary requirements without TA-Lib..."
        grep -iv "TA-Lib" "$REQ_FILE" > requirements-ta-lib-fallback.txt
        if ! $PIP_INSTALL_CMD -r requirements-ta-lib-fallback.txt; then
            echo ""
            echo "----------------------------------------------------------"
            echo "CRITICAL WARNING: Production dependency installation FAILED."
            echo "This is likely due to invalid versions in $REQ_FILE."
            echo "The system will be in a DEGRADED state."
            echo "Run 'make doctor' to diagnose specific missing packages."
            echo "----------------------------------------------------------"
        fi
        rm -f requirements-ta-lib-fallback.txt

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
    echo "$REQ_FILE not found, skipping production dependencies."
fi

# Install test dependencies
if [ -f "requirements-test.txt" ]; then
    echo "Installing test dependencies..."
    $PIP install -r requirements-test.txt
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
