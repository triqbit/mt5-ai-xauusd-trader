# ==============================================================================
# MT5 AI/ML Trading Bot - Unified Developer Workflow
# ==============================================================================

.PHONY: help bootstrap doctor test lint audit demo clean

VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff

help:
	@echo "MT5 AI/ML Trading Bot Developer CLI"
	@echo "-----------------------------------"
	@echo "bootstrap - Setup environment and install dependencies"
	@echo "doctor    - Diagnose system and configuration"
	@echo "test      - Run unit and integration tests"
	@echo "lint      - Run code quality checks (ruff)"
	@echo "audit     - Run security audit on dependencies"
	@echo "demo      - Start the bot in demo mode (dry-run)"
	@echo "clean     - Remove temporary files and caches"

bootstrap:
	@bash scripts/bootstrap.sh

doctor:
	@$(PYTHON) scripts/doctor.py

test:
	@$(PYTEST) tests/

lint:
	@$(RUFF) check .
	@$(RUFF) format --check .

audit:
	@$(VENV)/bin/pip-audit || echo "⚠️ pip-audit not found or failed. Ensure it's in requirements.txt"

demo:
	@$(PYTHON) main.py --mode demo --verbose

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf logs/*.log
