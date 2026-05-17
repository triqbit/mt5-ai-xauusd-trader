"""
MT5 AI/ML Trading Bot - Jules UX Enhancements Tests
tests/test_jules_ux_new.py
"""
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from main import main
from src.core.config import get_config
from src.trading.backtester import BacktestEngine


def test_doctor_flag_invokes_doctor():
    """Verify that --doctor flag calls scripts.doctor.main()."""
    with patch("sys.argv", ["main.py", "--doctor"]), \
         patch("scripts.doctor.main") as mock_doctor_main:

        # main() should return 0
        assert main() == 0
        mock_doctor_main.assert_called_once()

def test_show_config_flag_displays_config():
    """Verify that --show-config flag displays sanitized config and exits."""
    with patch("sys.argv", ["main.py", "--show-config"]), \
         patch("main.configure_logging"), \
         patch.dict(os.environ, {
             "MT5_LOGIN": "123456",
             "MT5_PASSWORD": "SecretPassword",
             "MT5_SERVER": "TestServer",
             "DATABASE_URL": "postgresql://user:pass@localhost/db"
         }):

        get_config.cache_clear()

        with patch("rich.console.Console.print") as mock_print:
            # main() should return 0
            assert main() == 0
            # Ensure something was printed
            assert mock_print.called

def test_recovery_factor_calculation():
    """Verify recovery factor calculation in BacktestEngine."""
    engine = BacktestEngine(symbol="XAUUSD", initial_balance=10000.0)

    # total_return = (balance - initial) / initial
    engine.balance = 11000.0
    engine.initial_balance = 10000.0

    # Peak = 11000, current = 10500, DD = (11000-10500)/11000 = 500/11000 approx 0.045
    engine.trades = [MagicMock(pnl=1000.0, mae=100.0)]
    now = datetime.now()
    engine.equity_curve = [(now, 10000.0), (now, 11000.0), (now, 10500.0)]

    report = engine._calculate_performance()
    assert hasattr(report, "recovery_factor")

    # If total_return is 0.1 and max_drawdown is > 0, recovery_factor should be > 0
    assert report.total_return == 0.1
    assert report.max_drawdown > 0
    assert report.recovery_factor == report.total_return / report.max_drawdown

def test_cli_argument_handling_refactored():
    """Verify refactored CLI argument handling maps to correct env vars."""
    # We use destination names for env vars now
    with patch("sys.argv", ["main.py", "--mode", "backtest", "--algo", "ppo", "--symbol", "EURUSD"]), \
         patch.dict(os.environ, {}, clear=True), \
         patch("main.configure_logging"):

        get_config.cache_clear()

        # We need to mock things so main doesn't actually run the whole app
        with patch("src.core.config_validator.ConfigValidator.validate") as mock_val:
            mock_val.side_effect = Exception("Stop here") # Use exception to stop main
            try:
                main()
            except Exception as e:
                if str(e) != "Stop here":
                    raise

        assert os.environ.get("MODE") == "backtest"
        assert os.environ.get("ALGORITHM") == "ppo"
        assert os.environ.get("SYMBOL") == "EURUSD"
