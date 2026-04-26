"""Tests for src.core.config_manager module."""

import os
import json
import pytest
from pathlib import Path
from src.core.config_manager import ConfigManager, MockSecretProvider, ConfigSchema

@pytest.fixture
def temp_env_file(tmp_path):
    def _create(name, content):
        f = tmp_path / name
        f.write_text(content)
        return f
    return _create

def test_config_manager_default_loading(monkeypatch):
    """Test ConfigManager loads default values when no .env is present."""
    monkeypatch.setenv("APP_ENV", "dev")
    # Ensure no relevant env vars or .env files interfere
    monkeypatch.delenv("MT5_LOGIN", raising=False)

    cm = ConfigManager(env_override="dev")
    assert cm.config.app_env == "dev"
    assert cm.config.mt5_login == 0

def test_config_manager_env_override(monkeypatch, tmp_path):
    """Test ConfigManager respects environment variable overrides."""
    monkeypatch.setenv("MT5_LOGIN", "99999")
    cm = ConfigManager(env_override="dev")
    assert cm.config.mt5_login == 99999

def test_config_manager_specific_env_file(monkeypatch, tmp_path):
    """Test ConfigManager loads from .env.{env} file."""
    env_file = tmp_path / ".env.staging"
    env_file.write_text("MT5_SERVER=StagingServer\nAPP_ENV=staging")

    # We need to mock ROOT in config_manager or change directory
    monkeypatch.setattr("src.core.config_manager.ROOT", tmp_path)

    cm = ConfigManager(env_override="staging")
    assert cm.config.mt5_server == "StagingServer"
    assert cm.config.app_env == "staging"

def test_secret_provider_integration(monkeypatch, tmp_path):
    """Test SecretProvider integration in ConfigManager."""
    monkeypatch.setattr("src.core.config_manager.ROOT", tmp_path)
    secrets = {"MT5_PASSWORD": "provider_secret"}
    sp = MockSecretProvider(secrets)

    # Create a .env file that also has a password
    env_file = tmp_path / ".env.dev"
    env_file.write_text("MT5_PASSWORD=env_password")

    cm = ConfigManager(env_override="dev", secret_provider=sp)

    # Provider should override .env
    assert cm.config.mt5_password == "provider_secret"

def test_config_reload(monkeypatch, tmp_path):
    """Test dynamic config reloading and audit trail."""
    env_file = tmp_path / ".env.dev"
    env_file.write_text("SYMBOL=XAUUSD")
    monkeypatch.setattr("src.core.config_manager.ROOT", tmp_path)
    audit_file = tmp_path / "audit.jsonl"

    cm = ConfigManager(env_override="dev", audit_file=audit_file)
    assert cm.config.symbol == "XAUUSD"
    # Initial load should be recorded
    assert len(cm.audit_trail) == 1
    assert cm.audit_trail[0]["event"] == "initial_load"

    # Modify .env file and reload
    env_file.write_text("SYMBOL=BTCUSD")
    cm.reload()

    assert cm.config.symbol == "BTCUSD"
    # Initial load + 1 update
    assert len(cm.audit_trail) == 2
    assert cm.audit_trail[1]["event"] == "config_update"
    assert cm.audit_trail[1]["changes"]["symbol"]["old"] == "XAUUSD"
    assert cm.audit_trail[1]["changes"]["symbol"]["new"] == "BTCUSD"

    # Verify persistence
    assert audit_file.exists()
    with open(audit_file) as f:
        lines = f.readlines()
        assert len(lines) == 2
        initial_load = json.loads(lines[0])
        assert initial_load["event"] == "initial_load"
        audit_entry = json.loads(lines[1])
        assert audit_entry["event"] == "config_update"
        assert audit_entry["changes"]["symbol"]["new"] == "BTCUSD"

def test_validation_rules():
    """Test that validation rules are enforced."""
    # Test invalid mode
    with pytest.raises(Exception):
        ConfigSchema(mode="invalid")

    # Test ge/le constraints
    with pytest.raises(Exception):
        ConfigSchema(max_positions=11)
