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
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core import get_config, profile
from src.core.audit_log import AuditLogger
from src.core.config_validator import ConfigValidator
from src.core.decision_support import DecisionSupportSystem
from src.core.explainability import SignalExplainer
from src.core.feature_engineering import FeatureEngineer
from src.core.health import HealthStatus, init_health_checker
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.data.event_intelligence import RiskStatus
from src.models.base_model import BaseModel
from src.models.ensemble import EnsembleModel
from src.models.lstm_model import LSTMModel
from src.models.ppo_agent import PPOAgent
from src.models.regime_detector import RegimeDetector
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
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
    model: BaseModel,
    execution_filter: ExecutionFilter,
    feature_engineer: FeatureEngineer,
    regime_detector: RegimeDetector,
    allocator: CapitalAllocator,
    dss: DecisionSupportSystem,
    trade_logger: Optional[TradeLogger] = None,
    monitor: Optional[Monitor] = None,
    console: Optional[Console] = None,
    audit_logger: Optional[AuditLogger] = None,
) -> None:
    log = logging.getLogger("main.live")
    explainer = SignalExplainer()
    log.info("Starting live trading loop | symbol=%s mode=%s", cfg.symbol, cfg.mode)
    poll_interval = 60  # seconds between signal evaluations
    while True:
        with profile("loop_total"):
            try:
                # 1. Fetch latest market data
                with profile("data_fetch"):
                    # Fetch more bars to satisfy FeatureEngineer and RegimeDetector windows
                    df_raw = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=500)
                    tick = connector.get_tick(cfg.symbol)

                # 2. Institutional Feature Engineering & Regime Detection
                with profile("institutional_context"):
                    df_features = feature_engineer.compute_features(df_raw)
                    obs = df_features.values[-1]  # Full 140+ features
                    regime_info = regime_detector.detect(df_raw)
                    volatility = float(df_raw["close"].rolling(20).std().iloc[-1])

                # 3. Get model prediction
                with profile("inference"):
                    # Pass regime context to models that support it (e.g. Ensemble)
                    if hasattr(model, "predict"):
                        # Attempt to pass extra context if the model signature allows it
                        try:
                            # EnsembleModel takes seq and regime_info
                            # For simple BaseModel, we just pass obs
                            if isinstance(model, EnsembleModel):
                                import torch
                                seq = torch.from_numpy(df_features.values[-60:]).float()
                                signal_obj = model.predict(obs, seq=seq, regime_info=regime_info)
                            else:
                                signal_obj = model.predict(obs)
                        except TypeError:
                            signal_obj = model.predict(obs)

                    direction = signal_obj.direction
                    confidence = signal_obj.confidence
                    if monitor:
                        monitor.check_confidence_degradation(confidence)

                    # Audit prediction
                    if audit_logger:
                        audit_logger.log_prediction(
                            symbol=cfg.symbol,
                            direction=direction,
                            confidence=confidence,
                            model_name=cfg.algorithm,
                            metadata=signal_obj.metadata if hasattr(signal_obj, "metadata") else None
                        )

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
                            "metadata": {"regime": regime_info.label.value},
                        }
                    )

                # 4. Initial Sizing & Risk Parameters
                price = tick["ask"] if direction == 1 else tick["bid"]
                atr = float((df_raw["high"] - df_raw["low"]).rolling(14).mean().iloc[-1])
                stop_loss = price - (direction * 2 * atr)
                take_profit = price + (direction * 4 * atr)

                # 5. Institutional Capital Allocation
                with profile("capital_allocation"):
                    # Request allocation from the institutional router
                    # Strategy ID: e.g. "PPO_XAUUSD_M5"
                    strat_id = f"{cfg.algorithm.upper()}_{cfg.symbol}_{cfg.timeframe}"
                    alloc_result = allocator.request_allocation(strat_id, risk_pct=cfg.risk_per_trade)

                    if not alloc_result.is_allowed:
                        log.warning("Allocation REJECTED | %s | Reason: %s", strat_id, alloc_result.rejection_reason)
                        approved_risk = 0.0
                    else:
                        approved_risk = alloc_result.allocated_risk_pct

                # Calculate lot size based on approved institutional risk
                lot_size = risk.size_position(
                    cfg.symbol,
                    win_rate=0.58,
                    avg_win=4 * atr,
                    avg_loss=2 * atr,
                ) if approved_risk > 0 else 0.0

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

                # 6. Risk approval gate
                with profile("risk_check"):
                    risk_approved = risk.approve(signal, signal_id=signal_id) if direction != 0 else False

                # 7. Execution Filter Cascade
                filter_decision = None
                if risk_approved:
                    with profile("execution_filter"):
                        drawdown = (risk.peak_equity - risk.balance) / risk.peak_equity
                        filter_decision = execution_filter.validate(
                            signal, df_features, current_drawdown=drawdown, timestamp=datetime.now(timezone.utc)
                        )
                        if not filter_decision.is_approved:
                            log.warning("Filter BLOCKED | %s | Reason: %s", cfg.symbol, filter_decision.blocked_by)
                            if audit_logger:
                                audit_logger.log_blocked_trade(
                                    symbol=cfg.symbol,
                                    reason=filter_decision.blocked_by,
                                    details=f"Confidence Score: {filter_decision.confidence_score:.2f}"
                                )
                            risk_approved = False

                # 8. Decision Support System (Cockpit)
                if direction != 0:
                    with profile("decision_support"):
                        # Prepare data for explainer
                        model_votes = signal_obj.metadata.get("per_algo_votes", {cfg.algorithm: 1 if direction == 1 else 2 if direction == -1 else 0})
                        model_weights = signal_obj.metadata.get("weights", {cfg.algorithm: 1.0})

                        risk_data = {
                            "passed": risk_approved,
                            "rejection_reasons": [],
                            "risk_reward": abs(take_profit - price) / abs(price - stop_loss) if abs(price - stop_loss) > 0 else 0.0,
                            "summary": "Passed all risk gates" if risk_approved else "Risk gate rejected"
                        }

                        regime_data = {
                            "name": regime_info.label.value,
                            "confidence": regime_info.confidence,
                            "volatility": "High" if regime_info.volatility_index > 1.5 else "Normal",
                            "is_favorable": True,
                            "summary": f"Market is {regime_info.label.value}"
                        }

                        execution_data = None
                        if filter_decision:
                            execution_data = {
                                "passed": filter_decision.is_approved,
                                "summary": filter_decision.blocked_by if not filter_decision.is_approved else "All filters passed",
                                "filters": [
                                    {"name": filter_decision.blocked_by, "passed": False, "message": f"Blocked by {filter_decision.blocked_by}"}
                                ] if not filter_decision.is_approved else []
                            }

                        explanation = explainer.explain(
                            symbol=cfg.symbol,
                            direction=direction,
                            confidence=confidence,
                            model_votes=model_votes,
                            model_weights=model_weights,
                            risk_data=risk_data,
                            regime_info=regime_data,
                            execution_data=execution_data
                        )

                        # Use a stub for macro risk since we don't have a live feed in this loop yet
                        macro_risk = RiskStatus(is_blocked=False, active_events=[], reason="No active data")

                        # Mock performance metrics for the cockpit
                        perf_metrics = {
                            "sharpe_ratio": 1.25, "profit_factor": 1.62,
                            "win_rate": 0.58, "total_trades": 142
                        }

                        packet = dss.assemble_packet(
                            cfg.symbol, explanation, regime_info, macro_risk, perf_metrics
                        )
                        # Render the institutional decision cockpit
                        if console:
                            console.print(dss.format_for_operator(packet))
                        else:
                            print(dss.format_for_operator(packet))

                if risk_approved and direction != 0:
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
                with profile("closed_positions_check"):
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
                with profile("account_updates"):
                    balance = connector.get_account_balance()
                    risk.update_equity(balance)
                    monitor.log_equity(balance)

                # Wait for next interval
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                log.info("Interrupted by user - shutting down")
                if audit_logger:
                    audit_logger.log_operator_action(
                        actor="operator",
                        action="manual_shutdown",
                        details="KeyboardInterrupt received"
                    )
                break
            except Exception as exc:
                log.exception("Unhandled error in trading loop: %s", exc)
                time.sleep(poll_interval)


# -- CLI -------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MT5 AI/ML Trading Bot - Enterprise Edition")
    p.add_argument("--mode", choices=["demo", "live", "backtest"], help="Execution mode")
    p.add_argument(
        "--algo",
        choices=["ppo", "dreamer", "lstm", "ensemble"],
        help="Trading algorithm",
    )
    p.add_argument("--symbol", help="Trading symbol (e.g. XAUUSD)")
    p.add_argument("--timeframe", help="Trading timeframe (e.g. M5)")
    p.add_argument("--model-dir", type=Path, default=Path("models/trained"), help="Directory for model weights")
    p.add_argument("--log-level", default="INFO", help="Logging level")
    p.add_argument("--check", action="store_true", help="Perform pre-flight health checks and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)
    log, console = logging.getLogger("main"), Console()

    # Override config from CLI: CLI > ENV > .env defaults
    if args.mode:
        os.environ["MODE"] = args.mode
    if args.algo:
        os.environ["ALGORITHM"] = args.algo
    if args.symbol:
        os.environ["SYMBOL"] = args.symbol
    if args.timeframe:
        os.environ["TIMEFRAME"] = args.timeframe

    try:
        cfg = get_config()
    except Exception as exc:
        log.critical("Failed to load configuration: %s", exc)
        return 1

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

    # ── Startup Summary ────────────────────────────────────────────────────────
    summary = Table.grid(expand=True)
    summary.add_column(style="cyan", justify="right")
    summary.add_column(style="white", justify="left")
    summary.add_row("Mode:  ", f"[bold]{cfg.mode.upper()}[/]")
    summary.add_row("Symbol:  ", f"[bold]{cfg.symbol}[/]")
    summary.add_row("Timeframe:  ", cfg.timeframe)
    summary.add_row("Algorithm:  ", cfg.algorithm)
    summary.add_row("Database:  ", "PostgreSQL" if "postgres" in cfg.database_url.get_secret_value() else "SQLite")

    console.print(Panel(summary, title="[bold blue]Trading System Configuration[/]", border_style="blue", expand=False))

    # Initialise components
    # 1. Audit Logger (Mandatory for enterprise traceability)
    database_url = cfg.database_url.get_secret_value()
    audit_db_url = database_url if "sqlite" in database_url else "sqlite:///audit.db"
    audit_logger = AuditLogger(db_url=audit_db_url)

    # Log deployment and configuration snapshot
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            version = tomllib.load(f)["project"]["version"]
    except Exception:
        version = "1.0.0"  # fallback

    audit_logger.log_deployment(version=version, environment=cfg.mode)
    audit_logger.log_config_snapshot(
        config_dict=cfg.model_dump(exclude={"mt5_password", "metaapi_token", "database_url", "telegram_token"}),
        reason="initial_startup"
    )

    connector = MT5Connector(cfg)
    with console.status("[bold green]Connecting to MT5 terminal..."):
        if not connector.connect():
            log.critical("Cannot connect to MT5 terminal. Aborting.")
            return 1
    balance = connector.get_account_balance()
    trade_logger = TradeLogger(
        db_url=database_url if "sqlite" in database_url else "sqlite:///trades.db"
    )
    monitor = Monitor(cfg)
    # Note: Monitor's start_metrics_server is legacy;
    # Enterprise deployments use the FastAPI health app which includes /metrics.
    # However, we keep it for backward compatibility or individual component runs.
    monitor.start_metrics_server()
    risk = RiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)
    execution_filter = ExecutionFilter(
        max_drawdown=cfg.max_drawdown if hasattr(cfg, "max_drawdown") else 0.15
    )
    feature_engineer = FeatureEngineer(base_timeframe=cfg.timeframe)
    regime_detector = RegimeDetector()
    # Use balance for allocator; if balance is 0, CapitalAllocator will handle it (or fail validation)
    allocator = CapitalAllocator(total_budget=balance)
    dss = DecisionSupportSystem()

    # Register default strategy in allocator
    # Ensure capital_cap is at least 0.01 to pass Pydantic gt=0 validation if balance is 0
    allocator.add_strategy(
        StrategyConfig(
            strategy_id=f"{cfg.algorithm.upper()}_{cfg.symbol}_{cfg.timeframe}",
            symbol=cfg.symbol,
            model_family=cfg.algorithm,
            capital_cap=max(0.01, balance * 0.5),
        )
    )

    # Model Factory based on --algo flag
    if args.algo == "ensemble":
        model = EnsembleModel(device="cpu")
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        if ppo_path.exists():
            model.load_ppo(ppo_path)
        if lstm_path.exists():
            model.load_lstm(lstm_path)
    elif args.algo == "ppo":
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        model = PPOAgent(model_path=ppo_path if ppo_path.exists() else None)
    elif args.algo == "lstm":
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        model = LSTMModel(model_path=lstm_path if lstm_path.exists() else None)
    else:
        log.warning(
            f"Algorithm {args.algo} not fully supported in main.py, falling back to Ensemble"
        )
        model = EnsembleModel(device="cpu")

    # Enterprise Health Gate
    health_checker = init_health_checker(cfg, connector, trade_logger, model, audit_logger=audit_logger)
    with console.status("[bold blue]Running health checks..."):
        try:
            report = health_checker.startup_gate()
        except RuntimeError as exc:
            log.critical(str(exc))
            # Fetch report directly to show failure state in table
            report = health_checker.get_full_report()

    table = Table(title="System Health", box=None)
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Message")
    for name, comp in report.components.items():
        color = (
            "green"
            if comp.status == HealthStatus.HEALTHY
            else "yellow"
            if comp.status == HealthStatus.DEGRADED
            else "red"
        )
        table.add_row(name, f"[{color}]{comp.status.value.upper()}[/]", comp.message)
    console.print(table)

    if report.status == HealthStatus.FAILED:
        log.critical("Startup HEALTH CHECK FAILED - Aborting.")
        return 1

    if args.check:
        log.info("Pre-flight check COMPLETE. System is healthy.")
        return 0

    try:
        if cfg.mode in ("demo", "live"):
            run_live(
                cfg,
                connector,
                risk,
                model,
                execution_filter,
                feature_engineer,
                regime_detector,
                allocator,
                dss,
                trade_logger=trade_logger,
                monitor=monitor,
                console=console,
                audit_logger=audit_logger,
            )
        elif cfg.mode == "backtest":
            log.info("Backtest mode - see scripts/backtest.py")
    finally:
        connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
