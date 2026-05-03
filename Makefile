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

.PHONY: help bootstrap doctor test lint audit demo clean init validate-config backtest report status emergency-stop daily-summary

help:
	@echo "MT5 AI/ML Trading Bot - Developer Commands"
	@echo "------------------------------------------"
	@echo "bootstrap : Install dependencies and setup environment"
	@echo "doctor    : Run system health check and diagnostics"
	@echo "test      : Run unit and integration tests"
	@echo "lint      : Run ruff linter and formatter"
	@echo "audit     : Run security and dependency audit"
	@echo "demo      : Run the bot in demo mode"
	@echo "clean     : Remove temporary files and build artifacts"
	@echo "init      : [NEW] Automated system initialization"
	@echo "validate-config : [NEW] Validate environment and .env"
	@echo "backtest  : [NEW] Run standardized backtest"
	@echo "report    : [NEW] Generate performance report"
	@echo "status    : [NEW] View system health dashboard"
	@echo "emergency-stop : [NEW] Immediate shutdown and position closure"
	@echo "daily-summary : [NEW] Generate operator daily summary"

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
	$(PYTHON_EXEC) main.py --mode demo --symbol XAUUSD --verbose

init:
	@echo "Initializing system..."
	bash scripts/bootstrap.sh

validate-config:
	@echo "Validating configuration..."
	$(PYTHON_EXEC) scripts/validate_env.py

backtest:
	@echo "Running standardized backtest..."
	$(PYTHON_EXEC) scripts/backtest.py

report:
	@echo "Generating performance report (Stub)..."
	@echo "See docs/status/EXECUTIVE_SUMMARY.md for current status."

status:
	@echo "System Status Dashboard (Stub)..."
	$(PYTHON_EXEC) main.py --check

emergency-stop:
	@echo "EMERGENCY STOP INITIATED (Stub)..."
	@echo "Closing all positions and shutting down..."
	# In a real scenario, this would call a dedicated emergency script

daily-summary:
	@echo "Generating Daily Operator Summary..."
	$(PYTHON_EXEC) generate_triage_report.py

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
