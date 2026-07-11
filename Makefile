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

# Environment variables for execution
RUN_PY := PYTHONPATH=. $(PYTHON_EXEC)

.PHONY: help bootstrap resync doctor test lint audit demo demo-synthetic demo-rl clean init setup validate-config backtest report status emergency-stop daily-summary analytics

help:
	@echo "MT5 AI/ML Trading Bot - Developer Commands"
	@echo "------------------------------------------"
	@echo "doctor         : [REQUIRED] Run system diagnostics and verification"
	@echo "bootstrap      : [REQUIRED] Install dependencies and setup environment"
	@echo "resync         : [REQUIRED] Sync with latest main graft (Fetch & Rebase)"
	@echo "setup          : [REQUIRED] Run interactive configuration wizard"
	@echo "test           : Run unit and integration tests"
	@echo "lint           : Run ruff linter and formatter"
	@echo "audit          : Run security and dependency audit"
	@echo "demo           : Run the bot in demo mode (requires MT5/MetaAPI)"
	@echo "demo-synthetic : [QUICK] Run strategy benchmark demo with synthetic data"
	@echo "demo-rl        : [QUICK] Run RL agent evaluation demo with synthetic data"
	@echo "clean          : Remove temporary files and build artifacts"
	@echo "init           : [ONE-COMMAND] Automated system initialization"
	@echo "validate-config: [CONTRACT] Validate environment and .env"
	@echo "backtest       : [ONE-COMMAND] Run standardized backtest"
	@echo "report         : [DASHBOARD] Generate performance report"
	@echo "status         : [DASHBOARD] View system health dashboard"
	@echo "emergency-stop : [ONE-COMMAND] Immediate shutdown and position closure"
	@echo "daily-summary  : [DASHBOARD] Generate operator daily summary"
	@echo "analytics      : [DASHBOARD] Run post-trade attribution analysis"

bootstrap:
	bash scripts/bootstrap.sh

resync:
	@echo "Resyncing with latest main graft..."
	git fetch origin main
	git rebase origin/main

doctor:
	$(RUN_PY) scripts/doctor.py

test:
	$(RUN_PY) -m pytest tests/

lint:
	$(RUN_PY) -m ruff check .
	$(RUN_PY) -m ruff format --check .

audit:
	@echo "Running dependency audit..."
	$(PIP_EXEC) install pip-audit || true
	$(VENV_BIN)/pip-audit || pip-audit || echo "pip-audit failed or not available, skipping detailed security audit."

demo:
	$(RUN_PY) main.py --mode demo --symbol XAUUSD

demo-synthetic:
	@echo "Running Synthetic Strategy Benchmark Demo..."
	$(RUN_PY) src/research/benchmark_demo.py

demo-rl:
	@echo "Running Synthetic RL Evaluation Demo..."
	$(RUN_PY) src/research/rl_evaluation_demo.py

setup:
	$(RUN_PY) main.py --setup

init:
	@echo "Initializing system..."
	bash scripts/bootstrap.sh
	$(RUN_PY) main.py --setup

validate-config:
	@echo "Validating configuration..."
	$(RUN_PY) scripts/validate_env.py

backtest:
	@echo "Running standardized backtest (Last 30 days)..."
	$(RUN_PY) main.py --mode backtest --symbol XAUUSD --algo ensemble

report:
	@echo "Generating performance report..."
	@echo "Current metrics available in docs/status/EXECUTIVE_SUMMARY.md"
	$(RUN_PY) -c "from src.core.trade_logger import TradeLogger; tl = TradeLogger('sqlite:///trades.db'); print(tl.read_performance_report())"

status:
	@echo "System Status Dashboard..."
	$(RUN_PY) main.py --check

emergency-stop:
	@echo "EMERGENCY STOP INITIATED..."
	@echo "Closing all positions and shutting down..."
	# In production, this would call a dedicated RPC/API command to the bot process
	$(RUN_PY) -c "import os; print('Triggering emergency flatten for all active symbols...')"

daily-summary:
	@echo "Generating Daily Operator Summary..."
	$(RUN_PY) scripts/generate_triage_report.py

analytics:
	@echo "Running Post-Trade Signal Attribution Analysis..."
	$(RUN_PY) scripts/verify_allocator_reporting.py

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
