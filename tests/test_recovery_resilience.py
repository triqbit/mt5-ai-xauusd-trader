
import pytest
from unittest.mock import MagicMock, patch
from src.core.trade_logger import TradeLogger, Trade
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from main import main
import sys
from pathlib import Path

@pytest.fixture
def mock_db(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test_recovery.db"
    logger = TradeLogger(db_url)
    return logger

def test_position_reconciliation_logic(mock_db):
    """
    Test that the reconciliation logic correctly populates RiskManager state.
    """
    # 1. Setup an "OPEN" trade in the database
    mock_db.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        lot_size=0.1,
        status="OPEN"
    )

    # 2. Mock configuration and dependencies
    cfg = MagicMock()
    cfg.database_url.get_secret_value.return_value = mock_db.engine.url.render_as_string()

    risk = MagicMock()
    risk.open_positions = {}

    # 3. Simulate the reconciliation logic from main.py
    recovered_trades = mock_db.get_open_trades()
    assert len(recovered_trades) == 1

    for t in recovered_trades:
        risk.open_positions[t.symbol] = t.ticket

    # 4. Verify state was recovered
    assert risk.open_positions["XAUUSD"] == 12345

@patch("main.Console")
def test_main_startup_reconciliation(
    mock_console_class
):
    """
    Verify that main() calls get_open_trades and updates risk manager.
    """
    # Patch components that are imported inside main()
    with patch("src.core.config.get_config") as mock_get_config, \
         patch("src.core.health.init_health_checker") as mock_health_init, \
         patch("src.core.audit_log.AuditLogger") as mock_audit_logger_class, \
         patch("src.core.trade_logger.TradeLogger") as mock_trade_logger_class, \
         patch("src.trading.audited_risk_manager.AuditedRiskManager") as mock_risk_class, \
         patch("src.trading.mt5_connector.MT5Connector") as mock_connector_class, \
         patch("src.models.ensemble.EnsembleModel"), \
         patch("src.models.ppo_agent.PPOAgent"), \
         patch("src.models.lstm_model.LSTMModel"), \
         patch("src.models.transformer_model.TimeSeriesTransformer"), \
         patch("src.core.config_validator.ConfigValidator") as mock_validator_class, \
         patch("src.core.monitor.Monitor") as mock_monitor_class:

        # Setup Mocks
        class MockConfig:
            model_fields = TradingConfig.model_fields
            mode = "demo"
            algorithm = "ensemble"
            symbol = "XAUUSD"
            log_level = "INFO"
            timeframe = "M5"
            risk_per_trade = 0.01
            max_daily_loss = 0.05
            max_positions = 5
            min_confidence = 0.55
            max_drawdown = 0.15
            logs_dir = Path("/tmp/logs")
            database_url = MagicMock()
            def model_dump(self, **kwargs): return {}

        mock_cfg = MockConfig()
        mock_cfg.database_url.get_secret_value.return_value = "sqlite:///test.db"
        mock_get_config.return_value = mock_cfg

        # Mock validator to pass
        mock_validator = mock_validator_class.return_value
        mock_validator.validate.return_value = MagicMock(errors=[], success=True)

        mock_trade_logger = mock_trade_logger_class.return_value
        mock_trade1 = MagicMock(spec=Trade)
        mock_trade1.symbol = "XAUUSD"
        mock_trade1.ticket = 999
        mock_trade1.lot_size = 0.1
        mock_trade_logger.get_open_trades.return_value = [mock_trade1]

        mock_risk = mock_risk_class.return_value
        mock_risk.open_positions = {}

        # Mock connector to return a balance
        mock_connector = mock_connector_class.return_value
        mock_connector.get_account_balance.return_value = 10000.0

        # Mock health check to pass
        mock_health_checker = mock_health_init.return_value
        mock_health_checker.startup_gate.return_value = MagicMock(status="healthy")

        # Mock sys.argv to avoid reading real args and trigger --check to exit early after setup
        with patch.object(sys, 'argv', ['main.py', '--check']):
            # Execute main (should exit 0 because of --check)
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

    # Verify reconciliation was attempted
    mock_trade_logger.get_open_trades.assert_called_once()
    assert mock_risk.open_positions["XAUUSD"] == 999
