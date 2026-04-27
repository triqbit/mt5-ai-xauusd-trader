import pytest
from unittest.mock import MagicMock
import numpy as np
from src.utils.synthetic_data import generate_synthetic_ohlcv
from src.trading.risk_manager import RiskManager, TradeSignal
from src.models.ensemble import EnsembleModel

def test_full_pipeline(test_config, db_logger, connector, monitor, mock_mt5):
    # 1. Setup
    symbol = "XAUUSD"
    df = generate_synthetic_ohlcv(symbol=symbol, n_bars=200)

    # Mock connector methods
    connector.initialize()
    connector.get_ohlcv = MagicMock(return_value=df)

    tick_data = {"bid": 2000.0, "ask": 2000.5}
    connector.get_tick = MagicMock(return_value=tick_data)

    # Mock MT5 order execution
    mock_order_result = MagicMock()
    mock_order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    mock_order_result.order = 1234567
    mock_mt5.order_send.return_value = mock_order_result

    # 2. Pipeline Execution (simulating main.py logic)

    # Data ingestion
    fetched_df = connector.get_ohlcv(symbol, "M5", n_bars=200)
    tick = connector.get_tick(symbol)

    # Feature engineering (simplified as in main.py)
    obs = fetched_df[["open", "high", "low", "close", "tick_volume"]].values[-1]

    # Model prediction
    model = EnsembleModel(device="cpu")
    # Mock predict to return a strong BUY signal
    model.predict = MagicMock(return_value=(1, 0.85, {"ppo": 1.0}))

    direction, confidence, per_algo = model.predict(obs)

    # Trade Logging (Signal)
    signal_id = db_logger.log_signal({
        "symbol": symbol,
        "direction": direction,
        "entry_price": tick["ask"] if direction > 0 else tick["bid"],
        "algorithm": "ensemble",
        "confidence": confidence
    })

    # Risk Management
    risk = RiskManager(test_config, account_balance=10000.0, logger_db=db_logger, monitor=monitor)

    price = tick["ask"] if direction == 1 else tick["bid"]
    # Simple SL/TP calculation
    atr = float((fetched_df["high"] - fetched_df["low"]).rolling(14).mean().iloc[-1])
    stop_loss = price - direction * 2 * atr
    take_profit = price + direction * 4 * atr

    lot_size = risk.size_position(symbol, win_rate=0.6, avg_win=4*atr, avg_loss=2*atr)

    signal = TradeSignal(
        symbol=symbol,
        direction=direction,
        entry_price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        lot_size=lot_size,
        algorithm="ensemble",
        confidence=confidence
    )

    # 3. Validation
    if risk.approve(signal, signal_id=signal_id):
        ticket = connector.place_order(signal)
        assert ticket == 1234567

        # Trade Logging (Execution)
        db_logger.log_trade(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            entry_price=price,
            lot_size=lot_size,
            signal_id=signal_id
        )

    # Verify database state
    with db_logger.Session() as session:
        from src.core.trade_logger import Trade, ModelSignal
        saved_signal = session.query(ModelSignal).filter_by(id=signal_id).first()
        assert saved_signal is not None
        assert saved_signal.direction == 1

        saved_trade = session.query(Trade).filter_by(ticket=1234567).first()
        assert saved_trade is not None
        assert saved_trade.signal_id == signal_id
