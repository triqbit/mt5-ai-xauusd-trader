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

def test_config_reload_and_audit(monkeypatch, tmp_path):
    """Test dynamic config reloading and audit trail with masking."""
    env_file = tmp_path / ".env.dev"
    env_file.write_text("SYMBOL=XAUUSD\nMT5_PASSWORD=old_pass")
    monkeypatch.setattr("src.core.config_manager.ROOT", tmp_path)
    audit_file = tmp_path / "audit.jsonl"

    cm = ConfigManager(env_override="dev", audit_file=audit_file)
    assert cm.config.symbol == "XAUUSD"

    # Modify .env file and reload
    env_file.write_text("SYMBOL=BTCUSD\nMT5_PASSWORD=new_pass")
    cm.reload()

    assert cm.config.symbol == "BTCUSD"
    assert cm.config.mt5_password == "new_pass"

    # Verify audit trail
    update_entry = [e for e in cm.audit_trail if e.get("event") == "config_update"][0]

    # Non-sensitive field should be clear
    assert update_entry["changes"]["symbol"]["old"] == "XAUUSD"
    assert update_entry["changes"]["symbol"]["new"] == "BTCUSD"

    # Sensitive field should be masked
    assert update_entry["changes"]["mt5_password"]["old"] == "********"
    assert update_entry["changes"]["mt5_password"]["new"] == "********"

def test_env_consistency(monkeypatch, tmp_path):
    """Test that app_env field matches ConfigManager's app_env."""
    monkeypatch.setattr("src.core.config_manager.ROOT", tmp_path)
    # Even if environment variable APP_ENV is set to something else
    monkeypatch.setenv("APP_ENV", "prod")

    cm = ConfigManager(env_override="staging")
    assert cm.config.app_env == "staging"

def test_validation_rules():
    """Test that validation rules are enforced."""
    # Test invalid mode
    with pytest.raises(Exception):
        ConfigSchema(mode="invalid")

    # Test ge/le constraints
    with pytest.raises(Exception):
        ConfigSchema(max_positions=11)
