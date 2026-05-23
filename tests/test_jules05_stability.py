from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.trading.capital_allocator import StrategyConfig


def test_monitor_logging_fix():
    """Verify the structured logging fix in Monitor.send_message."""
    config = MagicMock(spec=TradingConfig)
    config.telegram_token = SecretStr("fake_token")
    config.telegram_chat_id = "12345"

    monitor = Monitor(config)
    monitor.bot = MagicMock()
    # Mock send_message to raise an exception to trigger the catch block
    monitor.bot.send_message.side_effect = Exception("Telegram Error")

    # This should not raise TypeError anymore due to proxy_to_logger positional args
    monitor.send_message("test message")


def test_strategy_config_validation():
    """Verify StrategyConfig enforces gt=0 for capital_cap."""
    # This should pass
    StrategyConfig(strategy_id="TEST", symbol="XAUUSD", model_family="ensemble", capital_cap=100.0)

    # This should fail validation
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        StrategyConfig(
            strategy_id="TEST", symbol="XAUUSD", model_family="ensemble", capital_cap=0.0
        )
