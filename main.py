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
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from src.core.config import get_config
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
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
    cfg,
    connector: MT5Connector,
    risk: RiskManager,
    model: EnsembleModel,
    trade_logger: Optional[TradeLogger] = None,
    monitor: Optional[Monitor] = None,
) -> None:
    log = logging.getLogger("main.live")
    log.info("Starting live trading loop | symbol=%s mode=%s", cfg.symbol, cfg.mode)
    poll_interval = 60  # seconds between signal evaluations
    last_date = datetime.now(timezone.utc).date()

    while True:
        try:
            # 0. Check for daily reset
            current_date = datetime.now(timezone.utc).date()
            if current_date > last_date:
                log.info("New day detected: %s", current_date)
                risk.reset_daily()
                last_date = current_date

            # 1. Fetch latest market data
            df = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=200)
            tick = connector.get_tick(cfg.symbol)

            # 2. Update equity and monitor
            balance = connector.get_account_balance()
            risk.update_equity(balance)
            if monitor:
                monitor.log_equity(balance)

            # 3. Circuit breaker check
            if not risk._check_circuit_breaker():
                log.critical("Circuit breaker active - sleeping")
                time.sleep(poll_interval)
                continue

            # 4. Build observation vector
            # NOTE: In production, this would use FeatureEngineer for 140+ features
            obs = df[["open", "high", "low", "close", "tick_volume"]].values[-1]

            # 5. Get ensemble prediction
            direction, confidence, _per_algo = model.predict(obs)
            log.debug("Signal | dir=%d conf=%.3f", direction, confidence)

            if monitor:
                monitor.check_confidence_degradation(confidence)

            signal_id = None
            if trade_logger:
                signal_id = trade_logger.log_signal(
                    {
                        "symbol": cfg.symbol,
                        "direction": direction,
                        "entry_price": tick["ask"] if direction >= 0 else tick["bid"],
                        "algorithm": cfg.algorithm,
                        "confidence": confidence,
                    }
                )

            if direction == 0:
                log.debug("HOLD signal - skipping")
                time.sleep(poll_interval)
                continue

            # 6. Size position
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

            # 7. Risk approval gate
            if risk.approve(signal, signal_id=signal_id):
                ticket = connector.place_order(signal)
                if ticket:
                    risk.open_positions[cfg.symbol] = ticket
                    log.info("Order placed | ticket=%d", ticket)
                    if monitor:
                        monitor.log_trade(side="buy" if direction == 1 else "sell", lot_size=lot_size)
                    if trade_logger:
                        trade_logger.log_trade(
                            ticket=ticket,
                            symbol=cfg.symbol,
                            direction=direction,
                            entry_price=price,
                            lot_size=lot_size,
                            signal_id=signal_id,
                        )

            # 8. Check for closed positions to update logger
            current_positions = connector.get_positions(cfg.symbol)
            current_tickets = {p["ticket"] for p in current_positions}

            closed_tickets = []
            for symbol, ticket in list(risk.open_positions.items()):
                if symbol == cfg.symbol and ticket not in current_tickets:
                    log.info("Position CLOSED | ticket=%d", ticket)
                    if trade_logger:
                        trade_info = trade_logger.get_trade_by_ticket(ticket)
                        if trade_info:
                            exit_price = tick["bid"] if trade_info.direction == 1 else tick["ask"]
                            updated_trade = trade_logger.update_trade(
                                ticket=ticket,
                                exit_price=exit_price,
                            )
                            if updated_trade and updated_trade.pnl is not None:
                                risk.record_pnl(updated_trade.pnl)
                    closed_tickets.append(symbol)

            for sym in closed_tickets:
                risk.open_positions.pop(sym)

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            log.info("Interrupted by user - shutting down")
            break
        except Exception as exc:
            log.exception("Unhandled error in trading loop: %s", exc)
            if monitor:
                monitor.log_error(error_type=type(exc).__name__)
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
    trade_logger = TradeLogger(
        db_url=cfg.database_url if "sqlite" in cfg.database_url or "postgres" in cfg.database_url else "sqlite:///trades.db"
    )
    monitor = Monitor(cfg)
    risk = RiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)

    model = EnsembleModel(device="cpu")
    ppo_path = args.model_dir / "ppo_xauusd.zip"
    lstm_path = args.model_dir / "lstm_xauusd.pt"
    if ppo_path.exists():
        model.load_ppo(ppo_path)
    if lstm_path.exists():
        model.load_lstm(lstm_path)

    try:
        if cfg.mode in ("demo", "live"):
            run_live(cfg, connector, risk, model, trade_logger=trade_logger, monitor=monitor)
        elif cfg.mode == "backtest":
            log.info("Backtest mode - see scripts/backtest.py")
    finally:
        connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
