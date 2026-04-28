#!/usr/bin/env bash
# ==============================================================================
# MT5 AI/ML Trading Bot - Developer Bootstrap Script
# Purpose: Automate environment setup for new developers
# ==============================================================================

set -e

echo "🚀 Starting developer bootstrap..."

# 1. Create necessary directories
echo "📁 Creating local directories..."
mkdir -p models/trained logs data

# 2. Check for .env file
if [ ! -f .env ]; then
    echo "📄 Creating template .env file..."
    cat > .env <<EOF
# MT5 Connection
MT5_LOGIN=0
MT5_PASSWORD=your_password
MT5_SERVER=your_server
MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe

# MetaAPI Fallback
METAAPI_TOKEN=your_token
METAAPI_ACCOUNT_ID=your_account_id

# Runtime Configuration
MODE=demo
ALGORITHM=ensemble
LOG_LEVEL=INFO
EOF
    echo "⚠️  Please update .env with your credentials."
fi

# 3. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# 4. Install dependencies
echo "📦 Installing dependencies (this may take a few minutes)..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel
# Note: TA-Lib may fail if headers are missing, but we proceed
pip install -r requirements.txt || echo "⚠️  Some dependencies failed to install. Check for system headers (e.g., TA-Lib)."

echo "✅ Bootstrap complete!"
echo "👉 Run 'source venv/bin/activate' to start developing."
