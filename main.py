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
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

try:
    import torch
except ImportError:
    torch = None

import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core import profile
from src.core.audit_log import AuditLogger
from src.core.config_validator import ConfigValidator
from src.core.decision_support import DecisionSupportSystem
from src.core.exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5ExecutionError,
)
from src.core.explainability import SignalExplainer
from src.core.feature_engineering import FeatureEngineer
from src.core.health import HealthStatus, init_health_checker
from src.core.log_config import get_masking_processor
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.data.event_intelligence import RiskStatus
from src.models.base_model import BaseModel
from src.models.ensemble import EnsembleModel
from src.models.lstm_model import LSTMModel
from src.models.ppo_agent import PPOAgent
from src.models.regime_detector import RegimeDetector
from src.trading.audited_risk_manager import AuditedRiskManager
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
            get_masking_processor(),
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
                    try:
                        # Fetch more bars to satisfy FeatureEngineer and RegimeDetector windows
                        df_raw = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=500)
                        tick = connector.get_tick(cfg.symbol)
                    except MT5DataError as e:
                        log.error("Transient data retrieval error: %s. Skipping this iteration.", e)
                        time.sleep(poll_interval)
                        continue
                    except MT5ConnectionError:
                        log.warning("Connection lost. Attempting reconnection...")
                        try:
                            connector.connect()
                            log.info("Reconnection successful.")
                            continue
                        except MT5ConnectionError as reconnect_exc:
                            log.critical(
                                "Reconnection failed: %s. Waiting for next cycle.", reconnect_exc
                            )
                            time.sleep(poll_interval)
                            continue

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
                            if isinstance(model, EnsembleModel) and torch:
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

                    # Log prediction to audit trail
                    if audit_logger:
                        audit_logger.log_prediction(
                            symbol=cfg.symbol,
                            direction=direction,
                            confidence=confidence,
                            model_metadata=signal_obj.metadata
                            if hasattr(signal_obj, "metadata")
                            else None,
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
                    alloc_result = allocator.request_allocation(
                        strat_id, risk_pct=cfg.risk_per_trade
                    )

                    if not alloc_result.is_allowed:
                        log.warning(
                            "Allocation REJECTED | %s | Reason: %s",
                            strat_id,
                            alloc_result.rejection_reason,
                        )
                        if audit_logger:
                            audit_logger.log_blocked_trade(
                                symbol=cfg.symbol,
                                reason=f"Capital allocation rejected: {alloc_result.rejection_reason}",
                                context={"strategy_id": strat_id},
                            )
                        approved_risk = 0.0
                    else:
                        approved_risk = alloc_result.allocated_risk_pct

                # Calculate lot size based on approved institutional risk
                lot_size = (
                    risk.size_position(
                        cfg.symbol,
                        win_rate=0.58,
                        avg_win=4 * atr,
                        avg_loss=2 * atr,
                    )
                    if approved_risk > 0
                    else 0.0
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

                # 6. Risk approval gate
                with profile("risk_check"):
                    risk_approved = (
                        risk.approve(signal, signal_id=signal_id)
                        if direction != 0
                        else False
                    )

                # 7. Execution Filter Cascade
                filter_decision = None
                if risk_approved:
                    with profile("execution_filter"):
                        drawdown = (risk.peak_equity - risk.balance) / risk.peak_equity
                        filter_decision = execution_filter.validate(
                            signal,
                            df_features,
                            current_drawdown=drawdown,
                            timestamp=datetime.now(UTC),
                        )
                        if not filter_decision.is_approved:
                            log.warning(
                                "Filter BLOCKED | %s | Reason: %s",
                                cfg.symbol,
                                filter_decision.blocked_by,
                            )
                            audit_logger.log_blocked_trade(
                                symbol=cfg.symbol,
                                reason=f"Execution filter blocked: {filter_decision.blocked_by}",
                                context={
                                    "filter": filter_decision.blocked_by,
                                    "confidence": filter_decision.confidence_score,
                                },
                            )
                            risk_approved = False

                # 8. Decision Support System (Cockpit)
                if direction != 0:
                    with profile("decision_support"):
                        # Prepare data for explainer
                        model_votes = signal_obj.metadata.get(
                            "per_algo_votes",
                            {cfg.algorithm: 1 if direction == 1 else 2 if direction == -1 else 0},
                        )
                        model_weights = signal_obj.metadata.get("weights", {cfg.algorithm: 1.0})

                        risk_data = {
                            "passed": risk_approved,
                            "rejection_reasons": [],
                            "risk_reward": abs(take_profit - price) / abs(price - stop_loss)
                            if abs(price - stop_loss) > 0
                            else 0.0,
                            "summary": "Passed all risk gates"
                            if risk_approved
                            else "Risk gate rejected",
                        }

                        regime_data = {
                            "name": regime_info.label.value,
                            "confidence": regime_info.confidence,
                            "volatility": "High"
                            if regime_info.volatility_index > 1.5
                            else "Normal",
                            "is_favorable": True,
                            "summary": f"Market is {regime_info.label.value}",
                        }

                        execution_data = None
                        if filter_decision:
                            execution_data = {
                                "passed": filter_decision.is_approved,
                                "summary": filter_decision.blocked_by
                                if not filter_decision.is_approved
                                else "All filters passed",
                                "filters": [
                                    {
                                        "name": filter_decision.blocked_by,
                                        "passed": False,
                                        "message": f"Blocked by {filter_decision.blocked_by}",
                                    }
                                ]
                                if not filter_decision.is_approved
                                else [],
                            }

                        explanation = explainer.explain(
                            symbol=cfg.symbol,
                            direction=direction,
                            confidence=confidence,
                            model_votes=model_votes,
                            model_weights=model_weights,
                            risk_data=risk_data,
                            regime_info=regime_data,
                            execution_data=execution_data,
                        )

                        # Use a stub for macro risk since we don't have a live feed in this loop yet
                        macro_risk = RiskStatus(
                            is_blocked=False, active_events=[], reason="No active data"
                        )

                        # Optimization: Use real performance metrics from TradeLogger
                        if trade_logger:
                            perf_metrics = trade_logger.read_performance_report()
                        else:
                            perf_metrics = {
                                "sharpe_ratio": 0.0,
                                "profit_factor": 0.0,
                                "win_rate": 0.0,
                                "total_trades": 0,
                            }

                        packet = dss.assemble_packet(
                            cfg.symbol, explanation, regime_info, macro_risk, perf_metrics
                        )
                        # Render the institutional decision cockpit
                        if console:
                            # Optimization: Pass console to avoid redundant creation and captures
                            dss.format_for_operator(packet, console=console)
                        else:
                            log.info(dss.format_for_operator(packet))

                if risk_approved and direction != 0:
                    with profile("execution"):
                        try:
                            ticket = connector.place_order(signal)
                        except MT5ExecutionError as e:
                            log.error("Order execution FAILED: %s", e)
                            if audit_logger:
                                audit_logger.log_blocked_trade(
                                    symbol=cfg.symbol,
                                    reason=f"Order execution failure: {e!s}",
                                    context={"direction": direction, "lot_size": lot_size},
                                )
                            ticket = None

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
                                    exit_price = (
                                        tick["bid"] if trade_info.direction == 1 else tick["ask"]
                                    )
                                    # P&L will be calculated automatically by update_trade
                                    trade_logger.update_trade(
                                        ticket=ticket,
                                        exit_price=exit_price,
                                    )
                            closed_tickets.append(symbol)

                    if closed_tickets and trade_logger:
                        # Persist performance metrics only when a trade is closed
                        trade_logger.read_performance_report(persist=True)

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
                        operator="user", action="shutdown", reason="KeyboardInterrupt"
                    )
                break
            except MT5ConnectionError as exc:
                log.error("Critical connection failure: %s. Re-initializing...", exc)
                time.sleep(5)
                try:
                    connector.connect()
                except MT5ConnectionError:
                    log.error("Re-initialization failed during outer loop recovery.")
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
    p.add_argument("--start", help="Start date for backtest (YYYY-MM-DD)")
    p.add_argument("--end", help="End date for backtest (YYYY-MM-DD)")
    p.add_argument("--train-window", type=int, default=500, help="Train window size for backtest")
    p.add_argument("--test-window", type=int, default=100, help="Test window size for backtest")
    p.add_argument("--step-size", type=int, default=100, help="Step size for backtest")
    p.add_argument("--symbol", help="Trading symbol (e.g. XAUUSD)")
    p.add_argument("--timeframe", help="Trading timeframe (e.g. M5)")
    p.add_argument(
        "--model-dir", type=Path, default=Path("models/trained"), help="Directory for model weights"
    )
    p.add_argument("--log-level", default="INFO", help="Logging level")
    p.add_argument("--check", action="store_true", help="Perform pre-flight health checks and exit")
    p.add_argument("--confirm-live", action="store_true", help="Explicitly confirm live trading")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # 1. Dynamic CLI Override Mapping: CLI Arg -> Environment Variable
    # This ensures CLI > ENV > .env precedence.
    cli_overrides = {
        "mode": "MODE",
        "algo": "ALGORITHM",
        "symbol": "SYMBOL",
        "timeframe": "TIMEFRAME",
        "confirm_live": "CONFIRM_LIVE_TRADING",
        "log_level": "LOG_LEVEL",
    }

    # Identify explicitly provided arguments to avoid defaults overriding ENV/.env.
    provided_dest = set()
    temp_p = argparse.ArgumentParser(add_help=False)
    temp_p.add_argument("--mode")
    temp_p.add_argument("--algo")
    temp_p.add_argument("--symbol")
    temp_p.add_argument("--timeframe")
    temp_p.add_argument("--confirm-live", action="store_true")
    temp_p.add_argument("--log-level", dest="log_level")

    for action in temp_p._actions:
        for opt in action.option_strings:
            if opt in sys.argv:
                provided_dest.add(action.dest)

    for arg_name, env_var in cli_overrides.items():
        if arg_name in provided_dest:
            val = getattr(args, arg_name, None)
            if val is not None:
                if isinstance(val, bool):
                    if val:  # Only set if True for flags
                        os.environ[env_var] = "YES" if arg_name == "confirm_live" else str(val)
                else:
                    os.environ[env_var] = str(val)

    # 2. Reset config cache before ANY component uses get_config()
    from src.core.config import get_config

    get_config.cache_clear()

    # 3. Load configuration and initialize logging
    try:
        cfg = get_config()
    except Exception as exc:
        # Preliminary check for missing required variables before logging is even ready
        console = Console()
        if "validation error" in str(exc).lower():
            console.print(
                Panel(
                    "[bold red]Configuration Error:[/]\n\n"
                    "One or more required environment variables are missing.\n"
                    "Please ensure you have a [bold].env[/] file in the project root.\n\n"
                    "Quick Fix:\n"
                    "1. Copy [cyan].env.example[/] to [cyan].env[/]\n"
                    "2. Fill in your [bold]MT5_PASSWORD[/] and [bold]MT5_SERVER[/]\n\n"
                    f"[dim]Technical details: {exc}[/]",
                    title="[bold red]Bootstrap Failure[/]",
                    border_style="red",
                )
            )
        else:
            print(f"CRITICAL: Failed to load configuration: {exc}")
        return 1

    configure_logging(cfg.log_level)
    log, console = logging.getLogger("main"), Console()
    get_masking_processor().update_secrets(cfg)

    # Re-verify if it was a Pydantic validation error if we somehow got past get_config()
    # (Pydantic 2.0+ usually raises on instantiation)
    # Actually, we already handled it above.

    # Validate configuration
    validator = ConfigValidator(cfg)
    result = validator.validate()

    if result.errors:
        validation_table = Table(title="[bold yellow]Startup Configuration Validation[/]", box=None)
        validation_table.add_column("Field", style="cyan")
        validation_table.add_column("Status", justify="center")
        validation_table.add_column("Message")
        validation_table.add_column("Suggested Fix", style="green")

        for err in result.errors:
            status = "[bold red]CRITICAL[/]" if err.critical else "[bold yellow]WARNING[/]"
            validation_table.add_row(err.field, status, err.message, err.remedy)

        console.print(validation_table)

        if not result.success:
            log.critical(
                "Startup validation FAILED - One or more critical configuration errors found."
            )
            return 1
        else:
            log.warning("Startup validation passed with warnings.")

    # ── Startup Summary ────────────────────────────────────────────────────────
    summary = Table.grid(expand=True)
    summary.add_column(style="cyan", justify="right")
    summary.add_column(style="white", justify="left")
    summary.add_row("Mode:  ", f"[bold]{cfg.mode.upper()}[/]")
    summary.add_row("Symbol:  ", f"[bold]{cfg.symbol}[/]")
    summary.add_row("Timeframe:  ", cfg.timeframe)
    summary.add_row("Algorithm:  ", cfg.algorithm)
    summary.add_row(
        "Database:  ",
        "PostgreSQL" if "postgres" in cfg.database_url.get_secret_value() else "SQLite",
    )

    # Risk summary row
    risk_color = (
        "red"
        if cfg.risk_per_trade > 0.02
        else "yellow"
        if cfg.risk_per_trade > 0.01
        else "green"
    )
    summary.add_row("Risk/Trade:  ", f"[{risk_color}]{cfg.risk_per_trade:.1%}[/]")

    daily_loss_color = "red" if cfg.max_daily_loss > 0.06 else "yellow" if cfg.max_daily_loss > 0.05 else "green"
    summary.add_row("Daily Stop:  ", f"[{daily_loss_color}]{cfg.max_daily_loss:.1%}[/]")

    pos_color = "red" if cfg.max_positions > 10 else "yellow" if cfg.max_positions > 5 else "green"
    summary.add_row("Max Positions:  ", f"[{pos_color}]{cfg.max_positions}[/]")

    conf_color = "red" if cfg.min_confidence < 0.50 else "yellow" if cfg.min_confidence < 0.55 else "green"
    summary.add_row("Min Confidence:  ", f"[{conf_color}]{cfg.min_confidence:.1%}[/]")

    console.print(
        Panel(
            summary,
            title="[bold blue]Trading System Configuration[/]",
            border_style="blue",
            expand=False,
        )
    )

    # Initialise components
    # 1. Audit Logger (Mandatory for enterprise traceability)
    database_url = cfg.database_url.get_secret_value()
    audit_db_url = database_url if "sqlite" in database_url else "sqlite:///audit.db"
    audit_logger = AuditLogger(db_url=audit_db_url)

    # Log sanitized configuration snapshot
    audit_logger.log_config_snapshot(
        cfg.model_dump(
            mode="json",
            exclude={
                "mt5_password",
                "metaapi_token",
                "metaapi_account_id",
                "database_url",
                "telegram_token",
            },
        )
    )
    audit_logger.log("system", "startup_initiated", f"Mode: {cfg.mode}, Algo: {cfg.algorithm}")

    connector = MT5Connector(cfg)
    with console.status("[bold green]Connecting to MT5 terminal..."):
        try:
            connector.connect()
        except MT5ConnectionError as exc:
            # Enhanced connection diagnostics
            diag = Table.grid(expand=True)
            diag.add_column(style="cyan", justify="right")
            diag.add_column(style="white", justify="left")
            diag.add_row("Server:  ", cfg.mt5_server)
            diag.add_row("Login:  ", str(cfg.mt5_login))
            diag.add_row("Path:  ", cfg.mt5_path)
            diag.add_row("Platform:  ", sys.platform)

            console.print(
                Panel(
                    diag,
                    title="[bold red]Connection Diagnostics[/]",
                    subtitle="Sanitized connection settings",
                    border_style="red",
                )
            )
            log.critical("Cannot connect to MT5 terminal: %s. Aborting.", exc)
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
    risk = AuditedRiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)
    execution_filter = ExecutionFilter(
        max_drawdown=cfg.max_drawdown if hasattr(cfg, "max_drawdown") else 0.15,
        config=cfg,
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

    # Model Factory based on configured algorithm
    if cfg.algorithm == "ensemble":
        model = EnsembleModel(device="cpu")
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        if ppo_path.exists():
            model.load_ppo(ppo_path)
        if lstm_path.exists():
            model.load_lstm(lstm_path)
    elif cfg.algorithm == "ppo":
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        model = PPOAgent(model_path=ppo_path if ppo_path.exists() else None)
    elif cfg.algorithm == "lstm":
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        model = LSTMModel(model_path=lstm_path if lstm_path.exists() else None)
    else:
        # This branch should rarely be hit if Literal choices are enforced by Pydantic
        log.warning(
            f"Algorithm {cfg.algorithm} not fully supported in main.py factory, falling back to Ensemble"
        )
        model = EnsembleModel(device="cpu")

    # Enterprise Health Gate
    health_checker = init_health_checker(
        cfg, connector, trade_logger, model, audit_logger=audit_logger
    )
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

    # Record successful deployment/startup
    audit_logger.log_deployment(version="1.1.0", environment=cfg.mode)

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
            from src.trading.backtester import BacktestEngine

            start_date = (
                datetime.strptime(args.start, "%Y-%m-%d") if args.start else datetime(2023, 1, 1)
            )
            end_date = datetime.strptime(args.end, "%Y-%m-%d") if args.end else datetime.now()

            log.info(
                "Starting Backtest | symbol=%s range=%s to %s",
                cfg.symbol,
                start_date.date(),
                end_date.date(),
            )

            with console.status("[bold green]Fetching historical data..."):
                df_raw = connector.get_rates_range(cfg.symbol, cfg.timeframe, start_date, end_date)

            if df_raw.empty:
                log.error("No data found for the specified range.")
                return 1

            log.info("Fetched %d bars of data", len(df_raw))
            df_raw.set_index("time", inplace=True)

            engine = BacktestEngine(
                symbol=cfg.symbol,
                initial_balance=10000.0,
                feature_engineer=feature_engineer,
                execution_filter=execution_filter,
                max_positions=cfg.max_positions,
            )

            bt_report = engine.run_walk_forward(
                df_raw,
                model,
                train_window=args.train_window,
                test_window=args.test_window,
                step_size=args.step_size,
            )

            # Display Report
            perf_table = Table(title="Backtest Performance Report", box=None)
            perf_table.add_column("Metric", style="cyan")
            perf_table.add_column("Value", justify="right")

            perf_table.add_row("Annualized Return", f"{bt_report.annualized_return:.2%}")
            perf_table.add_row("Sharpe Ratio", f"{bt_report.sharpe_ratio:.2f}")
            perf_table.add_row("Max Drawdown", f"{bt_report.max_drawdown:.2%}")
            perf_table.add_row("Profit Factor", f"{bt_report.profit_factor:.2f}")
            perf_table.add_row("Win Rate", f"{bt_report.win_rate:.2%}")
            perf_table.add_row("Total Trades", str(bt_report.total_trades))
            perf_table.add_row("MAE Avg", f"{bt_report.mae_avg:.2f}")
            perf_table.add_row("MFE Avg", f"{bt_report.mfe_avg:.2f}")

            console.print(Panel(perf_table, border_style="green"))
    finally:
        connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
