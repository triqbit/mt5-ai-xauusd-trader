"""
MT5 AI/ML Trading Bot - Enterprise Edition
main.py - CLI entrypoint

Usage:
    python main.py --mode demo --algo ensemble
    python main.py --mode live --algo ppo
    python main.py --mode backtest --start 2023-01-01 --end 2023-12-31

Author : triqbit
License: MIT
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import structlog

from src.core.config import get_config
from src.models.ensemble import EnsembleModel
from src.models.feature_engineer import FeatureEngineer
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal

# -- Logging setup ---------------------------------------------------------


def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# -- Trading loop ----------------------------------------------------------


def run_live(
    cfg, connector: MT5Connector, risk: RiskManager, model: EnsembleModel
) -> None:
    log = logging.getLogger("main.live")
    log.info("Starting live trading loop | symbol=%s mode=%s", cfg.symbol, cfg.mode)
    poll_interval = 60  # seconds between signal evaluations
    fe = FeatureEngineer()
    window_size = 60  # Should match TradingEnv window_size

    while True:
        try:
            # 1. Fetch latest market data
            # Need enough bars for indicators (200+) plus window_size (60)
            n_bars = 300 + window_size
            df = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=n_bars)
            if df.empty or len(df) < n_bars:
                log.warning("Insufficient data from MT5 - retrying | count=%d", len(df))
                time.sleep(poll_interval)
                continue

            tick = connector.get_tick(cfg.symbol)
            balance = connector.get_account_balance()
            # Check if we have an open position for this symbol
            # Simplified: 1.0 if in risk.open_positions, else 0.0
            pos_state = 1.0 if cfg.symbol in risk.open_positions else 0.0

            # 2. Build observation vector using FeatureEngineer
            processed_df = fe.generate_features(df)
            # Use same sliding window normalization as TrainingEnv
            features = processed_df[fe.feature_columns].values
            window = features[-window_size:]
            # Z-score normalization of the window
            obs_features = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
            # Concatenate with portfolio state
            portfolio_state = np.array([balance / 10000.0, pos_state], dtype=np.float32)
            obs = np.concatenate([obs_features.flatten(), portfolio_state]).astype(np.float32)

            # 3. Get ensemble prediction
            direction, confidence, _per_algo = model.predict(obs)
            log.debug("Signal | dir=%d conf=%.3f", direction, confidence)
            if direction == 0:
                log.debug("HOLD signal - skipping")
                time.sleep(poll_interval)
                continue
            # 4. Size position
            price = tick["ask"] if direction == 1 else tick["bid"]
            atr = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1])
            stop_loss = price - direction * 2 * atr
            take_profit = price + direction * 4 * atr
            lot_size = risk.size_position(
                cfg.symbol,
                win_rate=0.58,
                avg_win=4 * atr,
                avg_loss=2 * atr,
            )
            signal = TradeSignal(
                symbol=cfg.symbol,
                direction=direction,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot_size=lot_size,
                algorithm=cfg.algorithm,
                confidence=confidence,
            )
            # 5. Risk approval gate
            if risk.approve(signal):
                ticket = connector.place_order(signal)
                if ticket:
                    risk.open_positions[cfg.symbol] = ticket
                    log.info("Order placed | ticket=%d", ticket)
            # 6. Update equity
            balance = connector.get_account_balance()
            risk.update_equity(balance)
        except KeyboardInterrupt:
            log.info("Interrupted by user - shutting down")
            break
        except Exception as exc:
            log.exception("Unhandled error in trading loop: %s", exc)
            time.sleep(poll_interval)


# -- CLI -------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MT5 AI/ML Trading Bot - Enterprise Edition")
    p.add_argument("--mode", choices=["demo", "live", "backtest"], default="demo")
    p.add_argument(
        "--algo",
        choices=["ppo", "dreamer", "lstm", "ensemble"],
        default="ensemble",
    )
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--timeframe", default="M5")
    p.add_argument("--model-dir", type=Path, default=Path("models/trained"))
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)
    log = logging.getLogger("main")
    # Override config from CLI
    os.environ.setdefault("MODE", args.mode)
    os.environ.setdefault("ALGORITHM", args.algo)
    os.environ.setdefault("SYMBOL", args.symbol)
    os.environ.setdefault("TIMEFRAME", args.timeframe)
    cfg = get_config()
    log.info(
        "Configuration loaded | mode=%s algo=%s symbol=%s",
        cfg.mode,
        cfg.algorithm,
        cfg.symbol,
    )
    # Initialise components
    connector = MT5Connector(cfg)
    if not connector.connect():
        log.critical("Cannot connect to MT5 terminal. Aborting.")
        return 1
    balance = connector.get_account_balance()
    risk = RiskManager(cfg, account_balance=balance)
    model = EnsembleModel(device="cpu")
    ppo_path = args.model_dir / "ppo_xauusd.zip"
    lstm_path = args.model_dir / "lstm_xauusd.pt"
    if ppo_path.exists():
        model.load_ppo(ppo_path)
    if lstm_path.exists():
        model.load_lstm(lstm_path)
    try:
        if cfg.mode in ("demo", "live"):
            run_live(cfg, connector, risk, model)
        elif cfg.mode == "backtest":
            log.info("Backtest mode - see scripts/backtest.py")
    finally:
        connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
