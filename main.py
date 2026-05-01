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
import pandas as pd
from pathlib import Path
from typing import Optional

import structlog

from src.core import FeatureEngineer, get_config, profile
from src.core.config_validator import ConfigValidator
from src.core.health import HealthStatus, init_health_checker
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
from src.trading.backtester import BacktestEngine
from src.trading.execution_filter import ExecutionFilter
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
    execution_filter: ExecutionFilter,
    feature_engineer: FeatureEngineer,
    trade_logger: Optional[TradeLogger] = None,
    monitor: Optional[Monitor] = None,
) -> None:
    log = logging.getLogger("main.live")
    log.info("Starting live trading loop | symbol=%s mode=%s", cfg.symbol, cfg.mode)
    poll_interval = 60  # seconds between signal evaluations
    while True:
        try:
            # 1. Fetch latest market data
            with profile("data_fetch"):
                df = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=1000)
                tick = connector.get_tick(cfg.symbol)

            # 2. Build observation vector
            with profile("feature_engineering"):
                df_features = feature_engineer.generate_features(df)

            row = df_features.iloc[-1]
            obs = row[feature_engineer.get_feature_names()].values
            volatility = float(row.get("atr_14", 0.0))

            # 3. Get ensemble prediction
            with profile("inference"):
                direction, confidence, _per_algo = model.predict(obs)
            log.debug("Signal | dir=%d conf=%.3f", direction, confidence)

            signal_id = None
            if trade_logger:
                signal_id = trade_logger.log_signal(
                    {
                        "symbol": cfg.symbol,
                        "direction": direction,
                        "entry_price": tick["ask"] if direction >= 0 else tick["bid"],
                        "algorithm": cfg.algorithm,
                        "confidence": confidence,
                        "volatility": volatility,
                    }
                )

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
            # 5. Execution Filter & Risk approval gate
            with profile("risk_check"):
                # Layer A: Technical Execution Filter
                decision = execution_filter.validate(signal, df_features)

                # Layer B: Portfolio Risk Manager
                if decision.is_approved:
                    approved = risk.approve(signal, signal_id=signal_id)
                else:
                    log.warning("Signal blocked by execution filter | reason=%s", decision.blocked_by)
                    approved = False

            if approved:
                with profile("execution"):
                    ticket = connector.place_order(signal)
                    if ticket:
                        risk.open_positions[cfg.symbol] = ticket
                        log.info("Order placed | ticket=%d", ticket)
                        if trade_logger:
                            trade_logger.log_trade(
                                ticket=ticket,
                                symbol=cfg.symbol,
                                direction=direction,
                                entry_price=price,
                                lot_size=lot_size,
                                signal_id=signal_id,
                            )
            # 6. Check for closed positions to update logger
            current_positions = connector.get_positions(cfg.symbol)
            current_tickets = {p["ticket"] for p in current_positions}

            closed_tickets = []
            for symbol, ticket in list(risk.open_positions.items()):
                if symbol == cfg.symbol and ticket not in current_tickets:
                    # Position closed - in a real scenario we'd fetch deal history
                    log.info("Position CLOSED | ticket=%d", ticket)
                    if trade_logger:
                        # Retrieve trade info from DB to get correct direction
                        trade_info = trade_logger.get_trade_by_ticket(ticket)
                        if trade_info:
                            # For a BUY, exit at BID. For a SELL, exit at ASK.
                            exit_price = tick["bid"] if trade_info.direction == 1 else tick["ask"]
                            # P&L will be calculated automatically by update_trade
                            trade_logger.update_trade(
                                ticket=ticket,
                                exit_price=exit_price,
                            )
                    closed_tickets.append(symbol)

            for sym in closed_tickets:
                risk.open_positions.pop(sym)

            # 7. Update equity
            balance = connector.get_account_balance()
            risk.update_equity(balance)
            monitor.log_equity(balance)
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
    p.add_argument("--start", help="Backtest start date YYYY-MM-DD")
    p.add_argument("--end", help="Backtest end date YYYY-MM-DD")
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

    # Validate configuration
    validator = ConfigValidator(cfg)
    result = validator.validate()

    if not result.success:
        log.critical("Startup validation FAILED")
        for err in result.errors:
            level = "CRITICAL" if err.critical else "WARNING"
            log.error(f"  [{level}] {err.field}: {err.message}")
        return 1

    if result.errors:
        for err in result.errors:
            log.warning(f"  [WARNING] {err.field}: {err.message}")

    log.info(
        "Configuration loaded and validated | mode=%s algo=%s symbol=%s",
        cfg.mode,
        cfg.algorithm,
        cfg.symbol,
    )
    # Initialise components
    connector = MT5Connector(cfg)
    if cfg.mode != "backtest":
        if not connector.connect():
            log.critical("Cannot connect to MT5 terminal. Aborting.")
            return 1
    balance = connector.get_account_balance()
    trade_logger = TradeLogger(
        db_url=cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
    )
    monitor = Monitor(cfg)
    risk = RiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)
    execution_filter = ExecutionFilter()
    feature_engineer = FeatureEngineer()
    model = EnsembleModel(device="cpu")
    ppo_path = args.model_dir / "ppo_xauusd.zip"
    lstm_path = args.model_dir / "lstm_xauusd.pt"
    if ppo_path.exists():
        model.load_ppo(ppo_path)
    if lstm_path.exists():
        model.load_lstm(lstm_path)

    # Enterprise Health Gate
    if cfg.mode != "backtest":
        health_checker = init_health_checker(cfg, connector, trade_logger, model)
        health_report = health_checker.get_full_report()

        if health_report.status == HealthStatus.FAILED:
            log.critical("Startup HEALTH CHECK FAILED")
            for name, comp in health_report.components.items():
                if comp.status == HealthStatus.FAILED:
                    log.error(f"  [FAILED] {name}: {comp.message}")
            return 1

        log.info("System HEALTH CHECK PASSED | status=%s", health_report.status)

    try:
        if cfg.mode in ("demo", "live"):
            run_live(
                cfg,
                connector,
                risk,
                model,
                execution_filter,
                feature_engineer,
                trade_logger=trade_logger,
                monitor=monitor,
            )
        elif cfg.mode == "backtest":
            log.info("Starting Backtest Engine...")
            start_date = args.start or "2023-01-01"
            end_date = args.end or "2023-12-31"

            # Fetch historical data for backtest
            df = connector.get_ohlcv(
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                n_bars=10000 # Fetch enough for the range
            )

            if df.empty:
                log.warning("No data from connector, generating synthetic data for backtest demonstration")
                from src.utils.synthetic_data import ScenarioGenerator
                gen = ScenarioGenerator()
                df = gen.generate(n_steps=10000, regime="trending")
                df.index = pd.date_range(start=start_date, periods=len(df), freq="5min")

            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            log.info("Backtest range: %s to %s | bars=%d", start_date, end_date, len(df))

            engine = BacktestEngine()
            report = engine.run_walk_forward(df, model)

            print("\n" + "="*50)
            print(" BACKTEST PERFORMANCE REPORT")
            print("="*50)
            print(f"Annualized Return: {report.annualized_return*100:.2f}%")
            print(f"Sharpe Ratio:      {report.sharpe_ratio:.2f}")
            print(f"Max Drawdown:      {report.max_drawdown*100:.2f}%")
            print(f"Profit Factor:     {report.profit_factor:.2f}")
            print(f"Total Trades:      {report.total_trades}")
            print(f"Win Rate:          {report.win_rate*100:.2f}%")
            print(f"Total Net PnL:     ${report.total_net_pnl:.2f}")
            print("="*50 + "\n")

    finally:
        connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
