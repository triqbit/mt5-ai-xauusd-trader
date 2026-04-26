import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal
from src.models.ensemble import EnsembleModel

def test_full_pipeline(mock_config, mock_mt5, db_logger, monitor):
    # Setup availability mocks
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", False):

        # 1. Setup components
        connector = MT5Connector(mock_config)
        connector.initialize()

        risk = RiskManager(mock_config, account_balance=10000.0, logger_db=db_logger, monitor=monitor)

        # Mock data ingestion
        # Note: We already set these up in conftest.py's mock_mt5,
        # but we can override here if needed for clarity.

        # 2. Execute pipeline step-by-step as in main.py

        # Data ingestion
        df = connector.get_ohlcv(mock_config.symbol, mock_config.timeframe, n_bars=200)
        tick = connector.get_tick(mock_config.symbol)

        assert not df.empty
        assert tick["bid"] == 2381.0

        # Build observation
        obs = df[["open", "high", "low", "close", "tick_volume"]].values[-1]

        # Mock model prediction
        with patch.object(EnsembleModel, 'predict', return_value=(1, 0.8, {"ppo": 0.8})) as mock_predict:
            model = EnsembleModel(device="cpu")
            direction, confidence, per_algo = model.predict(obs)

            assert direction == 1
            assert confidence == 0.8

            # Log Signal
            signal_id = db_logger.log_signal({
                "symbol": mock_config.symbol,
                "direction": direction,
                "entry_price": tick["ask"] if direction >= 0 else tick["bid"],
                "algorithm": mock_config.algorithm,
                "confidence": confidence,
            })

            assert signal_id > 0

            # Risk Management & Position Sizing
            price = tick["ask"] if direction == 1 else tick["bid"]
            atr = 5.0 # Mocked ATR
            stop_loss = price - direction * 2 * atr
            take_profit = price + direction * 4 * atr

            lot_size = risk.size_position(
                mock_config.symbol,
                win_rate=0.58,
                avg_win=4 * atr,
                avg_loss=2 * atr,
            )

            signal = TradeSignal(
                symbol=mock_config.symbol,
                direction=direction,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot_size=lot_size,
                algorithm=mock_config.algorithm,
                confidence=confidence,
            )

            # Risk approval
            if risk.approve(signal, signal_id=signal_id):
                # Execution
                ticket = connector.place_order(signal)
                assert ticket == 123456

                # Trade Logging
                db_logger.log_trade(
                    ticket=ticket,
                    symbol=mock_config.symbol,
                    direction=direction,
                    entry_price=price,
                    lot_size=lot_size,
                    signal_id=signal_id,
                )

    # 3. Verify side effects
    with db_logger.Session() as session:
        from src.core.trade_logger import Trade, ModelSignal
        assert session.query(ModelSignal).count() == 1
        assert session.query(Trade).count() == 1
        trade = session.query(Trade).first()
        assert trade.ticket == 123456
        assert trade.status == "OPEN"
