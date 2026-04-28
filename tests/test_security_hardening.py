
import pytest
from pydantic import SecretStr
from src.core.config import TradingConfig
import torch
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.models.ensemble import EnsembleModel

def test_config_secrets_masking(monkeypatch):
    """Verify that sensitive fields are masked in TradingConfig."""
    # Ensure environment variables don't interfere
    monkeypatch.delenv("RISK_PER_TRADE", raising=False)

    config = TradingConfig(
        mt5_password="secret_password",
        mt5_server="TestServer",
        metaapi_token="secret_token",
        telegram_token="secret_telegram",
        database_url="postgresql://user:pass@localhost/db",
        redis_url="redis://localhost:6379/0"
    )

    config_str = str(config)
    assert "secret_password" not in config_str
    assert "secret_token" not in config_str
    assert "secret_telegram" not in config_str
    assert "postgresql://user:pass@localhost/db" not in config_str
    assert "redis://localhost:6379/0" not in config_str

    assert isinstance(config.mt5_password, SecretStr)
    assert config.mt5_password.get_secret_value() == "secret_password"

@patch("torch.load")
def test_ensemble_load_lstm_weights_only(mock_load):
    """Verify that load_lstm uses weights_only=True."""
    mock_load.return_value = {}
    model = EnsembleModel(device="cpu")

    # We need a dummy path
    dummy_path = Path("dummy.pt")

    with patch("src.models.ensemble.LSTMAttentionModel") as mock_lstm_class:
        mock_lstm = MagicMock()
        mock_lstm_class.return_value = mock_lstm

        model.load_lstm(dummy_path)

        mock_load.assert_called_once()
        args, kwargs = mock_load.call_args
        assert kwargs.get("weights_only") is True
