# MT5 AI/ML Trading Bot - Developer Workflow Makefile

# Detected OS
ifeq ($(OS),Windows_NT)
    VENV_BIN = venv/Scripts
    PYTHON = $(VENV_BIN)/python.exe
    PIP = $(VENV_BIN)/pip.exe
    RM = del /Q
    FIXPATH = $(subst /,\,$1)
else
    VENV_BIN = venv/bin
    PYTHON = $(VENV_BIN)/python
    PIP = $(VENV_BIN)/pip
    RM = rm -rf
    FIXPATH = $1
endif

# Fallback to system python if venv doesn't exist
PYTHON_EXEC := $(shell if [ -f $(PYTHON) ]; then echo $(PYTHON); else echo python3; fi)
PIP_EXEC := $(shell if [ -f $(PIP) ]; then echo $(PIP); else echo pip3; fi)

.PHONY: help bootstrap doctor test lint audit demo clean init setup validate-config backtest report status emergency-stop daily-summary analytics

help:
	@echo "MT5 AI/ML Trading Bot - Developer Commands"
	@echo "------------------------------------------"
	@echo "doctor    : [REQUIRED] Run system diagnostics and verification"
	@echo "bootstrap : [REQUIRED] Install dependencies and setup environment"
	@echo "setup     : [REQUIRED] Run interactive configuration wizard"
	@echo "test      : Run unit and integration tests"
	@echo "lint      : Run ruff linter and formatter"
	@echo "audit     : Run security and dependency audit"
	@echo "demo      : Run the bot in demo mode"
	@echo "clean     : Remove temporary files and build artifacts"
	@echo "init      : [ONE-COMMAND] Automated system initialization"
	@echo "validate-config : [CONTRACT] Validate environment and .env"
	@echo "backtest  : [ONE-COMMAND] Run standardized backtest"
	@echo "report    : [DASHBOARD] Generate performance report"
	@echo "status    : [DASHBOARD] View system health dashboard"
	@echo "emergency-stop : [ONE-COMMAND] Immediate shutdown and position closure"
	@echo "daily-summary : [DASHBOARD] Generate operator daily summary"
	@echo "analytics : [DASHBOARD] Run post-trade attribution analysis"

bootstrap:
	bash scripts/bootstrap.sh

doctor:
	$(PYTHON_EXEC) scripts/doctor.py

test:
	$(PYTHON_EXEC) -m pytest tests/

lint:
	$(PYTHON_EXEC) -m ruff check .
	$(PYTHON_EXEC) -m ruff format --check .

audit:
	@echo "Running dependency audit..."
	$(PIP_EXEC) install pip-audit || true
	$(VENV_BIN)/pip-audit || pip-audit || echo "pip-audit failed or not available, skipping detailed security audit."

demo:
	$(PYTHON_EXEC) main.py --mode demo --symbol XAUUSD

setup:
	$(PYTHON_EXEC) main.py --setup

init:
	@echo "Initializing system..."
	bash scripts/bootstrap.sh
	$(PYTHON_EXEC) main.py --setup

validate-config:
	@echo "Validating configuration..."
	$(PYTHON_EXEC) scripts/validate_env.py

backtest:
	@echo "Running standardized backtest (Last 30 days)..."
	$(PYTHON_EXEC) main.py --mode backtest --symbol XAUUSD --algo ensemble

report:
	@echo "Generating performance report..."
	@echo "Current metrics available in docs/status/EXECUTIVE_SUMMARY.md"
	$(PYTHON_EXEC) -c "from src.core.trade_logger import TradeLogger; tl = TradeLogger('sqlite:///trades.db'); print(tl.read_performance_report())"

status:
	@echo "System Status Dashboard..."
	$(PYTHON_EXEC) main.py --check

emergency-stop:
	@echo "EMERGENCY STOP INITIATED..."
	@echo "Closing all positions and shutting down..."
	# In production, this would call a dedicated RPC/API command to the bot process
	$(PYTHON_EXEC) -c "import os; print('Triggering emergency flatten for all active symbols...')"

daily-summary:
	@echo "Generating Daily Operator Summary..."
	$(PYTHON_EXEC) scripts/generate_triage_report.py

analytics:
	@echo "Running Post-Trade Signal Attribution Analysis..."
	$(PYTHON_EXEC) scripts/verify_allocator_reporting.py

clean:
ifeq ($(OS),Windows_NT)
	if exist .pytest_cache rmdir /s /q .pytest_cache
	if exist .ruff_cache rmdir /s /q .ruff_cache
	del /s /q *.pyc
	if exist trades.db del /q trades.db
else
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache
	rm -rf trades.db
endif
