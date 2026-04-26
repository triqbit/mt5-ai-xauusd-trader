import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to sys.path
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))

# Setup dummy environment variables for pydantic
os.environ["MT5_PASSWORD"] = "test"
os.environ["MT5_SERVER"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///test_scripts.db"

@pytest.fixture(autouse=True)
def cleanup_db():
    db_path = Path("test_scripts.db")
    if db_path.exists():
        db_path.unlink()
    yield
    if db_path.exists():
        db_path.unlink()

@patch('src.core.monitor.Monitor.send_message')
def test_daily_report_smoke(mock_send_message):
    from scripts.daily_report import generate_report
    generate_report()

@patch('src.core.monitor.Monitor.send_message')
def test_drift_audit_smoke(mock_send_message):
    from scripts.model_drift_audit import audit_drift
    audit_drift()

def test_db_maintenance_smoke():
    from scripts.db_maintenance import run_maintenance
    run_maintenance()

@patch('src.core.monitor.Monitor.send_message')
def test_security_audit_smoke(mock_send_message):
    from scripts.security_audit import run_audit
    run_audit()

def test_sentiment_smoke():
    from src.models.sentiment_analyzer import SentimentAnalyzer
    analyzer = SentimentAnalyzer()
    assert hasattr(analyzer, 'get_symbol_sentiment')
