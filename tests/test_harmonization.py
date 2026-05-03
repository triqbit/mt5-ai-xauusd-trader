"""
Tests for system harmonization and cross-agent conflict resolution.
"""
from unittest.mock import MagicMock, patch


def test_risk_manager_consolidated_initialization():
    """Verify RiskManager can be initialized with both logger and monitor."""
    from src.core.config import TradingConfig
    from src.core.monitor import Monitor
    from src.core.trade_logger import TradeLogger
    from src.trading.risk_manager import RiskManager

    config = MagicMock(spec=TradingConfig)
    logger = MagicMock(spec=TradeLogger)
    monitor = MagicMock(spec=Monitor)

    risk = RiskManager(
        config=config,
        account_balance=10000.0,
        logger_db=logger,
        monitor=monitor
    )

    assert risk.trade_logger == logger
    assert risk.monitor == monitor
    assert risk.balance == 10000.0

def test_config_singleton_loading():
    """Verify get_config returns a TradingConfig singleton."""
    # Ensure environment variables required for validation are present and valid
    with patch.dict("os.environ", {
        "MT5_PASSWORD": "dummy",
        "MT5_SERVER": "dummy",
        "RISK_PER_TRADE": "0.01"
    }):
        from src.core.config import TradingConfig, get_config
        # We need to clear the lru_cache for testing purpose if it was already populated
        get_config.cache_clear()
        cfg1 = get_config()
        cfg2 = get_config()
        assert isinstance(cfg1, TradingConfig)
        assert cfg1 is cfg2


def test_model_action_to_direction_mapping():
    """Verify that ModelAction maps correctly to SignalDirection."""
    from src.core.constants import ModelAction, SignalDirection
    assert ModelAction.HOLD.to_direction() == SignalDirection.HOLD
    assert ModelAction.BUY.to_direction() == SignalDirection.BUY
    assert ModelAction.SELL.to_direction() == SignalDirection.SELL

    assert SignalDirection.HOLD == 0
    assert SignalDirection.BUY == 1
    assert SignalDirection.SELL == -1


def test_signal_explainer_mapping_alignment():
    """Verify that SignalExplainer uses unified ModelAction mapping."""
    from src.core.constants import SignalDirection
    from src.core.explainability import SignalExplainer
    explainer = SignalExplainer()

    # Votes: ppo=1 (BUY), lstm=2 (SELL)
    model_votes = {"ppo": 1, "lstm": 2}
    model_weights = {"ppo": 0.5, "lstm": 0.5}

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.7,
        model_votes=model_votes,
        model_weights=model_weights,
        risk_data={"passed": True},
        regime_info={"name": "Trending"}
    )

    # Verify attribution mapping
    for attr in explanation.model_attributions:
        if attr.model_name == "ppo":
            assert attr.vote == SignalDirection.BUY
        elif attr.model_name == "lstm":
            assert attr.vote == SignalDirection.SELL
