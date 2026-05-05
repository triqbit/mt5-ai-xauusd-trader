"""
Security hardening tests for MT5 AI Trading Bot.
tests/test_security_hardening.py
"""

import json
from io import StringIO

import structlog
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.log_config import SecretMaskingProcessor


def test_secret_masking_processor(monkeypatch):
    # Ensure environment variables don't override our test values
    monkeypatch.setenv("MT5_PASSWORD", "supersecretpassword123")
    monkeypatch.setenv("MT5_SERVER", "DemoServer")
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:dbpassword456@localhost:5432/db")

    # 1. Setup config with secrets
    config = TradingConfig(
        mt5_login=12345,
        mt5_password=SecretStr("supersecretpassword123"),
        mt5_server="DemoServer",
        database_url=SecretStr("postgresql://trader:dbpassword456@localhost:5432/db"),
    )

    # 2. Initialize processor
    processor = SecretMaskingProcessor(config=config)

    # 3. Test cases for masking
    test_event = {
        "message": "Connecting with supersecretpassword123",
        "db": "Using password dbpassword456 for connection",
        "safe": "This is a safe message",
    }

    processed = processor(None, "info", test_event)

    assert processed["message"] == "Connecting with [MASKED]"
    assert processed["db"] == "Using password [MASKED] for connection"
    assert processed["safe"] == "This is a safe message"
    assert "supersecretpassword123" not in processed["message"]
    assert "dbpassword456" not in processed["db"]


def test_structlog_integration(monkeypatch):
    # Ensure environment variables don't override our test values
    monkeypatch.setenv("MT5_PASSWORD", "loggingsecret789")
    monkeypatch.setenv("MT5_SERVER", "DemoServer")

    # 1. Setup a custom logger to capture output
    output = StringIO()

    # Custom config for testing
    config = TradingConfig(
        mt5_login=12345, mt5_password=SecretStr("loggingsecret789"), mt5_server="DemoServer"
    )

    masker = SecretMaskingProcessor(config=config)

    structlog.configure(
        processors=[masker, structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(output),
    )

    logger = structlog.get_logger()
    logger.info("attempting_login", password="loggingsecret789")

    # 2. Verify output
    log_content = json.loads(output.getvalue())
    assert log_content["password"] == "[MASKED]"
    assert "loggingsecret789" not in output.getvalue()


def test_dockerfile_permissions():
    """Verify Dockerfile hardening via file content check."""
    with open("Dockerfile", "r") as f:
        content = f.read()

    assert "chmod 755 /app/logs" in content
    assert "chmod 777 /app/logs" not in content
