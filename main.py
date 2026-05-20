"""
MT5 AI/ML Trading Bot - Enterprise Edition
main.py - CLI entrypoint

Usage:
    python main.py --mode demo --algo ensemble
    python main.py --mode live --algo ppo
    python main.py --mode backtest --start 2017-01-01 --end 2026-03-30

Author : triqbit
License: MIT
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from structlog import BoundLogger

    from src.core.audit_log import AuditLogger
    from src.core.decision_support import DecisionSupportSystem
    from src.core.feature_engineering import FeatureEngineer
    from src.core.monitor import Monitor
    from src.core.schemas import TradeSignal
    from src.core.trade_logger import TradeLogger
    from src.data.event_intelligence import EventIntelligence
    from src.models.base_model import BaseModel
    from src.models.regime_detector import RegimeDetector
    from src.trading.capital_allocator import CapitalAllocator
    from src.trading.execution_filter import ExecutionFilter
    from src.trading.mt5_connector import MT5Connector
    from src.trading.risk_manager import RiskManager

HAS_DEPENDENCIES = True
BOOTSTRAP_ERROR = None

try:
    import pandas as pd
    import structlog
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError as e:
    HAS_DEPENDENCIES = False
    BOOTSTRAP_ERROR = e
    # Use fallback if rich is not available
    Console = None
    Panel = None
    Table = None

try:
    import torch
except ImportError:
    torch = None

# -- Logging setup ---------------------------------------------------------


def configure_logging(level: str = "INFO") -> None:
    import logging

    import structlog.contextvars

    from src.core.log_config import get_masking_processor

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            get_masking_processor(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    # Redirect standard library logging to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    # Apply secret masking to standard logging calls
    logging.getLogger().addFilter(get_masking_processor())


# -- Trading loop ----------------------------------------------------------


def _prepare_trade_signal(
    cfg,
    direction: int,
    confidence: float,
    price: float,
    atr: float,
    risk: "RiskManager",
    allocator: "CapitalAllocator",
    audit_logger: Optional["AuditLogger"] = None,
    risk_multiplier: float = 1.0,
) -> "TradeSignal":
    """
    Consolidated helper to calculate stop-loss, take-profit, and lot-size
    based on institutional risk and capital allocation.
    """
    from src.core.schemas import TradeSignal

    log = structlog.get_logger("main.risk")

    # 1. SL/TP Calculation
    stop_loss = price - (direction * 2 * atr)
    take_profit = price + (direction * 4 * atr)

    # 2. Institutional Capital Allocation
    strat_id = f"{cfg.algorithm.upper()}_{cfg.symbol}_{cfg.timeframe}"
    alloc_result = allocator.request_allocation(strat_id, risk_pct=cfg.risk_per_trade)

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

    # 3. Lot Sizing
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

    # 4. Apply Macro Risk Multiplier
    if risk_multiplier < 1.0:
        old_lot = lot_size
        lot_size = round(lot_size * risk_multiplier, 2)
        log.info(
            "Macro risk reduction applied",
            multiplier=risk_multiplier,
            old_lot=old_lot,
            new_lot=lot_size,
        )

    return TradeSignal(
        symbol=cfg.symbol,
        direction=direction,
        entry_price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        lot_size=lot_size,
        algorithm=cfg.algorithm,
        confidence=confidence,
    )


def run_live(
    cfg,
    connector: "MT5Connector",
    risk: "RiskManager",
    model: "BaseModel",
    execution_filter: "ExecutionFilter",
    event_intelligence: "EventIntelligence",
    feature_engineer: "FeatureEngineer",
    regime_detector: "RegimeDetector",
    allocator: "CapitalAllocator",
    dss: "DecisionSupportSystem",
    trade_logger: Optional["TradeLogger"] = None,
    monitor: Optional["Monitor"] = None,
    console: Optional["Console"] = None,
    audit_logger: Optional["AuditLogger"] = None,
) -> None:
    import structlog.contextvars

    from src.core import profile
    from src.core.constants import SignalDirection
    from src.core.exceptions import (
        CircuitBreakerError,
        MT5ConnectionError,
        MT5DataError,
    )
    from src.core.explainability import SignalExplainer

    log = structlog.get_logger("main.live")
    explainer = SignalExplainer()
    log.info("Starting live trading loop", symbol=cfg.symbol, mode=cfg.mode)
    poll_interval = 60  # seconds between signal evaluations
    last_reset_date = datetime.now(timezone.utc).date()
    loop_count = 0
    last_price = None
    while True:
        iteration_start = time.perf_counter()
        # 0. Generate unique trace ID for this iteration
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=str(uuid.uuid4()))

        # Initialize iteration summary state
        iteration_status = "processing"
        final_direction = 0
        final_confidence = 0.0
        confluence_score = 0.0
        market_regime = "unknown"
        market_stability = 0.0

        # 0. Periodic Audit of Configuration State
        if loop_count % 100 == 0 and audit_logger:
            # Dynamic exclusion of all SecretStr/SecretBytes fields
            secret_fields = {
                f
                for f, info in cfg.__class__.model_fields.items()
                if "Secret" in str(info.annotation)
            }
            audit_logger.log_config_snapshot(
                cfg.model_dump(
                    mode="json",
                    exclude=secret_fields,
                ),
                reason=f"periodic_check_loop_{loop_count}",
            )
        loop_count += 1

        # 0. Update account metrics at start of loop
        with profile("account_updates"):
            try:
                balance = connector.get_account_balance()
                risk.update_equity(balance)
                if monitor:
                    monitor.log_equity(balance)
            except Exception as e:
                log.error("Failed to update account metrics", error=str(e))

        # 0.1 Check for day change to trigger daily summary
        current_date = datetime.now(timezone.utc).date()
        if current_date > last_reset_date:
            log.info("Day change detected, resetting daily stats")
            risk.reset_daily()
            last_reset_date = current_date

        with profile("loop_total"):
            try:
                # 1. Fetch latest market data
                with profile("data_fetch"):
                    try:
                        # Fetch more bars to satisfy FeatureEngineer and RegimeDetector windows
                        df_raw = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=500)
                        tick = connector.get_tick(cfg.symbol)
                        if not tick or "bid" not in tick:
                            log.error("Failed to retrieve valid tick for outcome tracking")
                            time.sleep(poll_interval)
                            continue

                        # 1.1 Record market outcome for drift tracking
                        current_price = tick["bid"]  # Use bid as reference for mid-market
                        if last_price is not None and hasattr(model, "observe_outcome"):
                            # Determine actual direction since last prediction
                            actual_dir = SignalDirection.HOLD
                            noise_thresh = getattr(cfg, "outcome_noise_threshold", 0.0001)
                            if current_price > last_price * (1 + noise_thresh):
                                actual_dir = SignalDirection.BUY
                            elif current_price < last_price * (1 - noise_thresh):
                                actual_dir = SignalDirection.SELL

                            model.observe_outcome(actual_dir)

                        last_price = current_price

                        if monitor and not df_raw.empty:
                            # Monitor data freshness using latest bar timestamp
                            latest_bar_time = (
                                df_raw.index[-1]
                                if isinstance(df_raw.index, pd.DatetimeIndex)
                                else df_raw["time"].iloc[-1]
                            )
                            monitor.log_data_freshness(latest_bar_time)

                        # Check for liquidity crisis (extreme spread)
                        raw_spread = abs(tick["ask"] - tick["bid"])

                        # Get symbol properties for precise pip calculation
                        props = connector.get_symbol_properties(cfg.symbol)
                        if props and "point" in props:
                            # Standard pip is 10 points for XAUUSD (0.01 -> 0.10)
                            # We use a robust mapping or derivation
                            point = props["point"]
                            pip_size = point * 10 if "XAUUSD" in cfg.symbol else point
                            spread_pips = raw_spread / pip_size if pip_size > 0 else raw_spread
                        else:
                            # Fallback for XAUUSD
                            spread_pips = (
                                raw_spread * 10.0 if "XAUUSD" in cfg.symbol else raw_spread
                            )

                        if monitor and spread_pips > cfg.spread_halt_pips:
                            monitor.alert_liquidity_crisis(cfg.symbol, spread_pips)

                    except MT5DataError as e:
                        iteration_status = "failed_data"
                        log.error("Transient data retrieval error", error=str(e))
                        if monitor:
                            monitor.record_iteration_heartbeat()
                            monitor.record_iteration_duration(time.perf_counter() - iteration_start)
                        log.info(
                            "iteration_summary",
                            status=iteration_status,
                            error=str(e),
                            duration_ms=round((time.perf_counter() - iteration_start) * 1000, 2),
                        )
                        time.sleep(poll_interval)
                        continue
                    except MT5ConnectionError:
                        iteration_status = "failed_connection"
                        log.warning("Connection lost. Attempting reconnection...")
                        if monitor:
                            monitor.alert_broker_connection_lost()
                            monitor.record_iteration_heartbeat()
                            monitor.record_iteration_duration(time.perf_counter() - iteration_start)

                        log.info(
                            "iteration_summary",
                            status=iteration_status,
                            duration_ms=round((time.perf_counter() - iteration_start) * 1000, 2),
                        )

                        try:
                            connector.connect()
                            log.info("Reconnection successful.")
                            if monitor:
                                monitor.alert_broker_connection_restored()
                            continue
                        except MT5ConnectionError as reconnect_exc:
                            log.critical("Reconnection failed", error=str(reconnect_exc))
                            time.sleep(poll_interval)
                            continue
                    except CircuitBreakerError as e:
                        wait_time = e.details.get("wait_time_remaining", 60)
                        log.error(
                            "MT5 CONNECTOR BLOCKED",
                            error=str(e),
                            remedy=f"Wait {wait_time:.0f}s for circuit breaker to enter HALF_OPEN state.",
                        )
                        if monitor:
                            monitor.log_system_error("MT5Connector", f"Circuit OPEN: {e}")
                        time.sleep(poll_interval)
                        continue

                # 2. Institutional Feature Engineering & Regime Detection
                with profile("institutional_context"):
                    df_features = feature_engineer.compute_features(df_raw)
                    obs = df_features.values[-1]  # Full 140+ features
                    regime_info = regime_detector.detect(df_raw)
                    market_regime = regime_info.label.value
                    market_stability = regime_info.confidence

                    # Optimization: Extract volatility from already-computed features if available
                    # RegimeDetector already calculates z-score (using rolling std), we can reuse it
                    if regime_info.raw_features and "atr_ratio" in regime_info.raw_features:
                        volatility = regime_info.volatility_index
                    else:
                        volatility = float(df_raw["close"].rolling(20).std().iloc[-1])

                # 3. Model Signal Generation
                with profile("inference"):
                    seq = None
                    if torch:
                        seq = torch.from_numpy(df_features.values[-60:]).float()

                    signal_obj = model.predict(
                        obs, seq=seq, regime_info=regime_info, symbol=cfg.symbol
                    )

                    direction = signal_obj.direction
                    confidence = signal_obj.confidence
                    final_direction = direction
                    final_confidence = confidence

                    if hasattr(signal_obj, "metadata") and signal_obj.metadata:
                        market_stability = signal_obj.metadata.get(
                            "market_context_stability", market_stability
                        )

                    if monitor:
                        monitor.check_confidence_degradation(confidence)
                        # Log model performance if available
                        health = getattr(model, "get_health_metrics", lambda: None)()
                        if health:
                            monitor.log_model_performance(
                                accuracy=health.get("accuracy", 0.0),
                                drift_score=health.get("drift", 0.0),
                                calibration_error=health.get("calibration", 0.0),
                            )

                    # Log signal to audit trail
                    if audit_logger:
                        audit_logger.log_prediction(
                            symbol=cfg.symbol,
                            direction=direction,
                            confidence=confidence,
                            model_metadata=signal_obj.metadata
                            if hasattr(signal_obj, "metadata")
                            else None,
                        )

                log.debug("Model signal received", direction=direction, confidence=confidence)

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

                # 4. Signal Preparation & Institutional Risk
                price = tick["ask"] if direction == 1 else tick["bid"]

                # 4.1 Fetch Macro Risk Context
                macro_risk = event_intelligence.get_risk_status(datetime.now(timezone.utc))

                # Optimization: Extract ATR from already-computed features to avoid redundant calculation
                atr_col = f"base_{cfg.timeframe}_atr"
                if atr_col in df_features.columns:
                    atr = float(df_features[atr_col].iloc[-1])
                else:
                    atr = float((df_raw["high"] - df_raw["low"]).rolling(14).mean().iloc[-1])

                with profile("signal_preparation"):
                    signal = _prepare_trade_signal(
                        cfg=cfg,
                        direction=direction,
                        confidence=confidence,
                        price=price,
                        atr=atr,
                        risk=risk,
                        allocator=allocator,
                        audit_logger=audit_logger,
                        risk_multiplier=macro_risk.risk_multiplier,
                    )
                lot_size = signal.lot_size

                # 6. Risk approval gate
                with profile("risk_check"):
                    health = getattr(model, "get_health_metrics", lambda: None)()
                    risk_approved = (
                        risk.approve(signal, signal_id=signal_id, model_health=health)
                        if direction != 0
                        else False
                    )
                    if monitor and direction != 0:
                        monitor.record_signal_funnel(
                            "risk_manager", "passed" if risk_approved else "rejected"
                        )

                # 7. Execution Filter Cascade
                filter_decision = None
                if risk_approved:
                    with profile("execution_filter"):
                        drawdown = (risk.peak_equity - risk.balance) / risk.peak_equity
                        # Model health retrieved in step 6
                        filter_decision = execution_filter.validate(
                            signal,
                            df_features,
                            current_drawdown=drawdown,
                            timestamp=datetime.now(timezone.utc),
                            model_health=health,
                            trade_logger=trade_logger,
                        )
                        if audit_logger:
                            audit_logger.log_execution_decision(
                                symbol=cfg.symbol,
                                direction=signal.direction,
                                trace=filter_decision.trace,
                                is_approved=filter_decision.is_approved,
                            )

                        if monitor:
                            monitor.record_signal_funnel(
                                "execution_filter",
                                "passed"
                                if filter_decision.is_approved
                                else f"blocked_{filter_decision.blocked_by.lower()}",
                            )

                        if not filter_decision.is_approved:
                            log.warning(
                                "Filter BLOCKED | %s | Reason: %s",
                                cfg.symbol,
                                filter_decision.blocked_by,
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
                            "risk_reward": abs(signal.take_profit - price)
                            / abs(price - signal.stop_loss)
                            if abs(price - signal.stop_loss) > 0
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
                        confluence_score = explanation.get_confluence_score()

                        if monitor:
                            monitor.record_confluence(confluence_score)

                        # Log comprehensive decision trace for every non-hold signal
                        if audit_logger:
                            audit_logger.log(
                                actor="system",
                                action="decision_explanation",
                                details=f"Decision trace for {cfg.symbol}: {explanation.human_readable_summary}",
                                metadata={
                                    "symbol": cfg.symbol,
                                    "direction": direction,
                                    "confidence": confidence,
                                    "risk_data": risk_data,
                                    "regime_data": regime_data,
                                    "execution_data": execution_data,
                                    "macro_risk": macro_risk.model_dump(mode="json"),
                                },
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
                        from src.core.exceptions import MT5ExecutionError

                        execution_start = time.perf_counter()
                        try:
                            ticket = connector.place_order(signal)
                        except MT5ExecutionError as e:
                            log.error("Order execution FAILED", error=str(e))
                            if audit_logger:
                                audit_logger.log_blocked_trade(
                                    symbol=cfg.symbol,
                                    reason=f"Order execution failure: {e!s}",
                                    context={"direction": direction, "lot_size": lot_size},
                                )
                            ticket = None

                        execution_latency_ms = (time.perf_counter() - execution_start) * 1000

                        if ticket:
                            risk.open_positions[cfg.symbol] = ticket
                            log.info("Order placed", ticket=ticket, latency_ms=execution_latency_ms)
                            if monitor:
                                # We don't have slippage here yet, so we pass 0.0
                                monitor.log_execution_quality(
                                    latency_ms=execution_latency_ms,
                                    slippage_pips=0.0,
                                    fill_rate=1.0,
                                )
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
                            log.info("Position CLOSED", ticket=ticket)
                            if trade_logger:
                                # Retrieve trade info from DB to get correct direction
                                trade_info = trade_logger.get_trade_by_ticket(ticket)
                                if trade_info:
                                    # For a BUY, exit at BID. For a SELL, exit at ASK.
                                    exit_price = (
                                        tick["bid"] if trade_info.direction == 1 else tick["ask"]
                                    )
                                    # P&L will be calculated automatically by update_trade
                                    # This also logs to audit trail internally now
                                    # Optimization: Pass trade_info (Trade object) to avoid redundant DB query
                                    updated_trade = trade_logger.update_trade(
                                        ticket=ticket,
                                        exit_price=exit_price,
                                        trade_obj=trade_info,
                                    )

                                    # Update allocator performance for feedback loop
                                    if updated_trade and allocator:
                                        strat_id = (
                                            f"{cfg.algorithm.upper()}_{cfg.symbol}_{cfg.timeframe}"
                                        )
                                        allocator.update_strategy_performance(
                                            strat_id, updated_trade.pnl
                                        )
                            closed_tickets.append(symbol)

                    if closed_tickets and trade_logger:
                        # Persist performance metrics only when a trade is closed
                        trade_logger.read_performance_report(persist=True)

                    for sym in closed_tickets:
                        risk.open_positions.pop(sym)

                iteration_status = "success"

                # Emit structured iteration summary and record metrics
                iteration_duration = time.perf_counter() - iteration_start
                if monitor:
                    monitor.record_iteration_heartbeat()
                    monitor.record_iteration_duration(iteration_duration)
                    monitor.record_market_stability(market_stability)

                log.info(
                    "iteration_summary",
                    status=iteration_status,
                    direction=final_direction,
                    confidence=final_confidence,
                    confluence=confluence_score,
                    regime=market_regime,
                    stability=market_stability,
                    duration_ms=round(iteration_duration * 1000, 2),
                )

                # Wait for next interval with operator feedback
                if console:
                    with console.status(
                        "[bold blue]Waiting for next signal evaluation..."
                    ) as status:
                        for i in range(poll_interval, 0, -1):
                            status.update(
                                f"[bold blue]Waiting for next signal evaluation ({i}s remaining)..."
                            )
                            time.sleep(1)
                else:
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                log.info("Interrupted by user - shutting down")
                if audit_logger:
                    audit_logger.log_operator_action(
                        operator="user", action="shutdown", reason="KeyboardInterrupt"
                    )
                break
            except MT5ConnectionError as exc:
                iteration_status = "error_connection"
                log.error("Critical connection failure: %s. Re-initializing...", exc)
                if monitor:
                    monitor.alert_broker_connection_lost()
                    monitor.record_iteration_heartbeat()
                    monitor.record_iteration_duration(time.perf_counter() - iteration_start)

                log.info(
                    "iteration_summary",
                    status=iteration_status,
                    error=str(exc),
                    duration_ms=round((time.perf_counter() - iteration_start) * 1000, 2),
                )
                time.sleep(5)
                try:
                    connector.connect()
                    if monitor:
                        monitor.alert_broker_connection_restored()
                except MT5ConnectionError:
                    log.error("Re-initialization failed during outer loop recovery.")
            except Exception as exc:
                iteration_status = "error_unhandled"
                log.exception("Unhandled error in trading loop: %s", exc)
                if monitor:
                    monitor.record_iteration_heartbeat()
                    monitor.record_iteration_duration(time.perf_counter() - iteration_start)

                log.info(
                    "iteration_summary",
                    status=iteration_status,
                    error=str(exc),
                    duration_ms=round((time.perf_counter() - iteration_start) * 1000, 2),
                )
                time.sleep(poll_interval)


# -- CLI -------------------------------------------------------------------


def get_system_version() -> str:
    """Retrieve application version from src package."""
    # Attempt to read version from src/__init__.py directly to avoid import dependencies
    try:
        init_path = Path(__file__).resolve().parent / "src" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r") as f:
                for line in f:
                    if "__version__" in line and "=" in line:
                        return line.split("=")[1].strip().strip("'\"")
        return "unknown"
    except Exception:
        return "unknown"


def run_setup_wizard() -> int:
    """
    Interactive guided setup wizard for initial configuration.
    Helps users configure .env without manual text editing.
    """
    import getpass

    from pydantic import SecretStr

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import IntPrompt, Prompt
    except ImportError:
        print("Error: 'rich' library is required for the setup wizard.")
        print("Please run 'pip install rich' first.")
        return 1

    console = Console()
    console.print(
        Panel(
            "[bold blue]MT5 AI/ML Trading Bot - Interactive Setup Wizard[/]\n"
            "[dim]This wizard will help you configure your .env file with essential credentials.[/]",
            border_style="blue",
        )
    )

    # 1. Basic Info
    console.print("\n[bold]1. Execution Environment[/]")
    mode = Prompt.ask("Select execution mode", choices=["demo", "live", "backtest"], default="demo")
    symbol = Prompt.ask("Default trading symbol", default="XAUUSD").upper()
    timeframe = Prompt.ask(
        "Default timeframe", choices=["M1", "M5", "M15", "M30", "H1", "H4", "D1"], default="M5"
    )

    # 2. MT5 Credentials
    console.print("\n[bold]2. MetaTrader 5 Credentials[/]")

    if platform.system() != "Windows":
        console.print("[yellow]Notice: You are on a non-Windows platform.[/]")
        console.print(
            "[yellow]Native MT5 SDK requires Windows. You will likely need MetaAPI credentials for Linux/Mac.[/]\n"
        )

    login = IntPrompt.ask("MT5 Account Login (Number)", default=0)

    # Use getpass for password to avoid echoing
    password_val = ""
    while not password_val:
        password_val = getpass.getpass("MT5 Account Password: ")
        if not password_val:
            console.print("[red]Password cannot be empty.[/]")
    password = SecretStr(password_val)
    del password_val

    server = Prompt.ask("MT5 Broker Server (e.g., IC-Markets-Demo)", default="YOUR_SERVER_HERE")

    # 3. MetaAPI (Optional but recommended for Linux/Mac)
    console.print("\n[bold]3. MetaAPI Cloud Fallback (Optional)[/]")
    console.print("[dim]Required for non-Windows environments or cloud failover.[/]")
    use_meta = Prompt.ask("Do you want to configure MetaAPI?", choices=["y", "n"], default="n")
    meta_token = None
    meta_id = ""
    if use_meta == "y":
        token_val = ""
        while not token_val:
            token_val = getpass.getpass("MetaAPI Token: ")
            if not token_val:
                console.print("[red]Token cannot be empty.[/]")
        meta_token = SecretStr(token_val)
        del token_val
        meta_id = Prompt.ask("MetaAPI Account ID")

    # 4. Confirm and Save
    console.print("\n[bold]4. Review & Save[/]")
    if Prompt.ask("Ready to save configuration to .env?", choices=["y", "n"], default="y") != "y":
        console.print("[yellow]Setup aborted. No changes made.[/]")
        return 0

    # Write to .env
    env_path = Path(".env")
    example_path = Path(".env.example")

    lines = []
    if example_path.exists():
        with open(example_path, "r") as f:
            for line in f:
                if line.startswith("MT5_LOGIN="):
                    lines.append(f"MT5_LOGIN={login}\n")
                elif line.startswith("MT5_PASSWORD="):
                    lines.append(f"MT5_PASSWORD={password.get_secret_value()}\n")
                elif line.startswith("MT5_SERVER="):
                    lines.append(f"MT5_SERVER={server}\n")
                elif line.startswith("SYMBOL="):
                    lines.append(f"SYMBOL={symbol}\n")
                elif line.startswith("TIMEFRAME="):
                    lines.append(f"TIMEFRAME={timeframe}\n")
                elif line.startswith("MODE="):
                    lines.append(f"MODE={mode}\n")
                elif line.startswith("METAAPI_TOKEN=") and meta_token:
                    lines.append(f"METAAPI_TOKEN={meta_token.get_secret_value()}\n")
                elif line.startswith("METAAPI_ACCOUNT_ID=") and meta_id:
                    lines.append(f"METAAPI_ACCOUNT_ID={meta_id}\n")
                else:
                    lines.append(line)
    else:
        # Fallback if .env.example is missing
        lines = [
            f"MT5_LOGIN={login}\n",
            f"MT5_PASSWORD={password.get_secret_value()}\n",
            f"MT5_SERVER={server}\n",
            f"SYMBOL={symbol}\n",
            f"TIMEFRAME={timeframe}\n",
            f"MODE={mode}\n",
            f"METAAPI_TOKEN={meta_token.get_secret_value() if meta_token else ''}\n",
            f"METAAPI_ACCOUNT_ID={meta_id}\n",
        ]

    # Enterprise Security: Use os.open with 0o600 to prevent world-readable race condition
    if os.name != "nt":
        fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.writelines(lines)
    else:
        with open(env_path, "w") as f:
            f.writelines(lines)

    # Secure permissions (double-check)
    import contextlib

    with contextlib.suppress(Exception):
        if os.name != "nt":
            os.chmod(env_path, 0o600)

    console.print("[bold green]✅ Configuration saved to .env with secure permissions.[/]")
    console.print(
        "You can now run the bot with [cyan]python main.py --check[/] to verify connectivity.\n"
    )
    return 0


def get_parser() -> argparse.ArgumentParser:
    """Construct the main CLI argument parser with grouped options."""
    p = argparse.ArgumentParser(
        description="MT5 AI/ML Trading Bot - Enterprise Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Interactive guided setup (Recommended for first-time use)
  python main.py --setup

  # Perform a pre-flight health check
  python main.py --check

  # Start trading in DEMO mode with Ensemble algorithm
  python main.py --mode demo --symbol XAUUSD --algo ensemble

  # Start LIVE trading (requires explicit confirmation)
  python main.py --mode live --algo ensemble --confirm-live

  # Run a walk-forward backtest for a specific period
  python main.py --mode backtest --start 2017-01-01 --end 2026-03-30 --algo ppo
        """,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {get_system_version()}")

    # -- Execution Group
    execution = p.add_argument_group("Execution Options")
    execution.add_argument(
        "--mode",
        choices=["demo", "live", "backtest"],
        help="Execution mode: 'demo' (paper), 'live' (real money), or 'backtest' (simulation).",
    )
    execution.add_argument(
        "--algo",
        dest="algorithm",
        choices=["ppo", "dreamer", "lstm", "ensemble", "transformer"],
        help="AI algorithm architecture to use for signal generation.",
    )
    execution.add_argument("--symbol", help="Trading symbol ticker (e.g., XAUUSD, EURUSD).")
    execution.add_argument("--timeframe", help="Chart timeframe for analysis (e.g., M5, H1, D1).")
    execution.add_argument(
        "--confirm-live",
        dest="confirm_live_trading",
        action="store_true",
        help="Explicitly acknowledge and confirm LIVE trading execution.",
    )

    # -- Backtest Group
    backtest = p.add_argument_group("Backtesting & Simulation")
    backtest.add_argument(
        "--start", help="Historical start date (YYYY-MM-DD).", default="2017-01-01"
    )
    backtest.add_argument(
        "--end",
        help="Historical end date (YYYY-MM-DD).",
        default="2026-03-30",
    )
    backtest.add_argument(
        "--train-window",
        type=int,
        default=500,
        help="Number of bars for walk-forward training window.",
    )
    backtest.add_argument(
        "--test-window",
        type=int,
        default=100,
        help="Number of bars for walk-forward testing window.",
    )
    backtest.add_argument(
        "--step-size",
        type=int,
        default=100,
        help="Number of bars to slide the window per iteration.",
    )
    backtest.add_argument(
        "--spread",
        type=float,
        default=0.0001,
        help="Fixed simulated spread (as decimal, e.g. 0.0001).",
    )
    backtest.add_argument(
        "--commission", type=float, default=7.0, help="Commission cost per round-turn lot."
    )

    # -- Setup & Diagnostics Group
    setup = p.add_argument_group("Setup & Diagnostics")
    setup.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive configuration wizard to setup .env and credentials.",
    )
    setup.add_argument(
        "--check",
        action="store_true",
        help="Perform comprehensive pre-flight health checks and exit.",
    )
    setup.add_argument(
        "--doctor",
        action="store_true",
        help="Run the system diagnostic tool to verify environment and dependencies.",
    )
    setup.add_argument(
        "--show-config",
        action="store_true",
        help="Display the current sanitized configuration and exit.",
    )
    setup.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/trained"),
        help="Local directory containing trained model weight files.",
    )

    # -- Logging Group
    logging = p.add_argument_group("Logging & Observability")
    logging.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Granularity of output logging.",
    )

    return p


def run_backtest(
    args,
    cfg,
    feature_engineer: "FeatureEngineer",
    execution_filter: "ExecutionFilter",
    model: "BaseModel",
    console: "Console",
    log: "BoundLogger",
):
    """Bridge for running the walk-forward backtesting engine."""
    try:
        from rich.panel import Panel as RichPanel
        from rich.table import Table as RichTable
    except ImportError:
        RichPanel = None
        RichTable = None

    from src.trading.backtester import BacktestEngine

    def get_color(metric: str, value: float) -> str:
        """Apply institutional color-coding based on EXCELLENCE_BLUEPRINT thresholds."""
        if metric == "sharpe":
            return "green" if value >= 2.0 else "yellow" if value >= 1.0 else "red"
        if metric == "pf":
            return "green" if value >= 2.0 else "yellow" if value >= 1.5 else "red"
        if metric == "wr":
            return "green" if value >= 0.55 else "yellow" if value >= 0.45 else "red"
        if metric == "rf":
            return "green" if value >= 3.0 else "yellow" if value >= 2.0 else "red"
        return "white"

    from src.trading.mt5_connector import MT5Connector

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    log.info("Starting Backtest", symbol=cfg.symbol, start=start_date.date(), end=end_date.date())

    connector = MT5Connector(cfg)
    try:
        with console.status("[bold green]Connecting to MT5 for historical data..."):
            connector.connect()
            df_raw = connector.get_rates_range(cfg.symbol, cfg.timeframe, start_date, end_date)

        if df_raw.empty:
            log.error("No data found for the specified range.")
            return 1

        log.info("Fetched historical data", bars=len(df_raw))
        df_raw.set_index("time", inplace=True)

        engine = BacktestEngine(
            symbol=cfg.symbol,
            initial_balance=10000.0,
            spread=args.spread,
            commission_per_lot=args.commission,
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
        perf_table = RichTable(title="Backtest Performance Report", box=None)
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", justify="right")

        # Color-coded metrics
        s_color = get_color("sharpe", bt_report.sharpe_ratio)
        pf_color = get_color("pf", bt_report.profit_factor)
        wr_color = get_color("wr", bt_report.win_rate)
        rf_color = get_color("rf", bt_report.recovery_factor)

        perf_table.add_row("Annualized Return", f"{bt_report.annualized_return:.2%}")
        perf_table.add_row("Sharpe Ratio", f"[{s_color}]{bt_report.sharpe_ratio:.2f}[/]")
        perf_table.add_row("Max Drawdown", f"{bt_report.max_drawdown:.2%}")
        perf_table.add_row("Profit Factor", f"[{pf_color}]{bt_report.profit_factor:.2f}[/]")
        perf_table.add_row("Recovery Factor", f"[{rf_color}]{bt_report.recovery_factor:.2f}[/]")
        perf_table.add_row("Win Rate", f"[{wr_color}]{bt_report.win_rate:.2%}[/]")
        perf_table.add_row("Total Trades", str(bt_report.total_trades))
        perf_table.add_row("MAE Avg", f"{bt_report.mae_avg:.2f}")
        perf_table.add_row("MFE Avg", f"{bt_report.mfe_avg:.2f}")
        perf_table.add_row("Period", f"{start_date.date()} to {end_date.date()}")

        if RichPanel:
            console.print(
                RichPanel(
                    perf_table,
                    title="[bold]Institutional Performance Summary[/]",
                    border_style="green",
                )
            )
        return 0
    finally:
        connector.disconnect()


def main() -> int:
    # Local imports of Rich for the entire main function to avoid UnboundLocalError
    # when an early exception occurs during bootstrap.
    try:
        from rich.console import Console as RichConsole
        from rich.panel import Panel as RichPanel
        from rich.table import Table as RichTable
    except ImportError:
        RichConsole = None
        RichPanel = None
        RichTable = None

    # 0. Identify diagnostic commands that can proceed without full setup
    diagnostic_flags = ["--help", "-h", "--version", "--doctor", "--setup"]
    is_diagnostic = any(arg in sys.argv for arg in diagnostic_flags)

    # 1. Guided Setup: Detect missing .env and offer to initialize it
    env_file = Path(".env")
    example_file = Path(".env.example")
    if not is_diagnostic and not env_file.exists() and example_file.exists():
        if sys.stdin.isatty():
            try:
                from rich.console import Console
                from rich.panel import Panel

                console = Console()
                console.print(
                    Panel(
                        "[bold yellow]Configuration file (.env) is missing![/]\n\n"
                        "The system requires a .env file to store credentials and settings.\n"
                        "Would you like to run the [cyan]Interactive Setup Wizard[/] now?",
                        title="[bold red]First-Time Setup[/]",
                        border_style="yellow",
                    )
                )
                choice = input("\nRun Setup Wizard? [Y/n]: ").strip().lower()
                if choice in ["", "y", "yes"]:
                    # Create basic directories first with restrictive permissions
                    for d in ["data", "logs", "models/trained"]:
                        # Enterprise Security: Restricted access to data directories (0o700)
                        p = Path(d)
                        if os.name != "nt":
                            p.mkdir(parents=True, exist_ok=True, mode=0o700)
                            if p.exists():
                                os.chmod(p, 0o700)
                        else:
                            p.mkdir(parents=True, exist_ok=True)
                    return run_setup_wizard()
                else:
                    print(
                        "\n[!] Manual setup required. You can run 'python main.py --setup' later."
                    )
            except ImportError:
                print("\n[!] Configuration file (.env) is missing.")
                choice = (
                    input("Would you like to initialize it from .env.example? [Y/n]: ")
                    .strip()
                    .lower()
                )
                if choice in ["", "y", "yes"]:
                    import contextlib
                    import shutil

                    shutil.copy(".env.example", ".env")
                    # Apply restrictive permissions immediately
                    with contextlib.suppress(Exception):
                        os.chmod(env_file, 0o600)

                    # Ensure required directories exist with restrictive permissions
                    for d in ["data", "logs", "models/trained"]:
                        # Enterprise Security: Restricted access to data directories (0o700)
                        p = Path(d)
                        if os.name != "nt":
                            p.mkdir(parents=True, exist_ok=True, mode=0o700)
                            if p.exists():
                                os.chmod(p, 0o700)
                        else:
                            p.mkdir(parents=True, exist_ok=True)

                    print("✅ Created .env with secure permissions and initialized directories.")
                    print("👉 Please edit .env with your credentials before proceeding.\n")
            except (KeyboardInterrupt, EOFError):
                print("\nSetup skipped.")
        else:
            # Non-interactive environment: auto-initialize directories if .env exists
            # (If .env doesn't exist, we can't do much in non-interactive mode anyway)
            pass

    # 2. Handle missing dependencies gracefully for diagnostic flags
    if not HAS_DEPENDENCIES and not is_diagnostic:
        print("=" * 70)
        print("CRITICAL: BOOTSTRAP FAILURE - MISSING CORE DEPENDENCIES")
        print("=" * 70)
        print(f"Details: {BOOTSTRAP_ERROR}")
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python:   {sys.version.split()[0]}")
        print("\nREMEDIATION STEPS:")
        print("1. [Recommended] Run 'python3 scripts/doctor.py' to perform deep diagnostics.")
        print("2. Run 'pip install -r requirements.txt' to install all required libraries.")
        if platform.system() == "Linux":
            print("3. On Linux, if TA-Lib is missing, ensure the C-library is installed:")
            print("   'sudo apt-get install libta-lib0' or equivalent.")
        print("-" * 70)
        return 1

    parser = get_parser()
    args = parser.parse_args()

    # 0. Immediate Diagnostic Handlers
    if args.setup:
        return run_setup_wizard()

    if args.doctor:
        try:
            from scripts import doctor

            doctor.main()
            return 0
        except Exception as e:
            print(f"CRITICAL: Failed to run doctor script: {e}")
            return 1

    # 1. Dynamic CLI Override Mapping
    # Identify explicitly provided arguments to avoid defaults overriding ENV/.env.
    # Also tracked for source attribution in --show-config and summary panel.
    provided_dest = set()
    for action in parser._actions:
        for opt in action.option_strings:
            if opt in sys.argv:
                provided_dest.add(action.dest)
                break

    # Sync CLI overrides to environment variables for Pydantic to pick up
    for dest in provided_dest:
        val = getattr(args, dest, None)
        if val is not None:
            env_var = dest.upper()
            if isinstance(val, bool):
                if val:  # Only set if True for flags
                    os.environ[env_var] = "YES" if dest == "confirm_live_trading" else "TRUE"
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
        if RichConsole and RichPanel:
            console = RichConsole()
            if "validation error" in str(exc).lower():
                console.print(
                    RichPanel(
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
        else:
            # Fallback to plain print if rich is not available
            print("=" * 70)
            print("CRITICAL: BOOTSTRAP FAILURE - CONFIGURATION ERROR")
            print("=" * 70)
            if "validation error" in str(exc).lower():
                print("One or more required environment variables are missing.")
                print("Please ensure you have a .env file in the project root.")
                print("\nQUICK FIX:")
                print("1. Copy .env.example to .env")
                print("2. Fill in your MT5_PASSWORD and MT5_SERVER")
            print(f"\nTechnical details: {exc}")
            print("-" * 70)
        return 1

    from src.core.log_config import get_masking_processor

    configure_logging(cfg.log_level)

    log, console = structlog.get_logger("main"), (RichConsole() if RichConsole else None)
    get_masking_processor().update_secrets(cfg)

    # 3.1 Handle --show-config
    if args.show_config:
        config_table = RichTable(
            title="[bold blue]Current System Configuration (Sanitized)[/]", box=None
        )
        config_table.add_column("Parameter", style="cyan")
        config_table.add_column("Value", style="white")
        config_table.add_column("Source", style="dim")

        # Dynamic discovery of field origins
        # 1. Check CLI overrides (provided_dest)
        # 2. Check ENV (os.environ)
        # 3. Default

        # Dynamic exclusion of all SecretStr/SecretBytes fields
        secret_fields = {
            f for f, info in cfg.__class__.model_fields.items() if "Secret" in str(info.annotation)
        }

        # Get sanitized dump
        sanitized_cfg = cfg.model_dump(
            mode="json",
            exclude=secret_fields,
        )

        for key, value in sorted(sanitized_cfg.items()):
            # Determine source
            source = "[dim]DEFAULT[/]"
            if key in provided_dest:
                source = "[bold cyan]CLI[/]"
            else:
                # Check aliases and env vars
                field_info = cfg.__class__.model_fields.get(key)
                alias = field_info.validation_alias if field_info else None
                if (alias and alias in os.environ) or (key.upper() in os.environ):
                    source = "[bold green]ENV[/]"

            config_table.add_row(key, str(value), source)

            if console:
                console.print(
                    RichPanel(
                        config_table,
                        title="[bold blue]System Config[/]",
                        border_style="blue",
                        expand=False,
                    )
                )
        return 0

    # Re-verify if it was a Pydantic validation error if we somehow got past get_config()
    # (Pydantic 2.0+ usually raises on instantiation)
    # Actually, we already handled it above.

    # Validate configuration
    from src.core.config_validator import ConfigValidator

    validator = ConfigValidator(cfg)
    result = validator.validate()

    if result.errors:
        validation_table = RichTable(
            title="[bold yellow]Startup Configuration Validation[/]", box=None
        )
        validation_table.add_column("Field", style="cyan")
        validation_table.add_column("Status", justify="center")
        validation_table.add_column("Message")
        validation_table.add_column("Suggested Fix", style="green")

        for err in result.errors:
            status = "[bold red]CRITICAL[/]" if err.critical else "[bold yellow]WARNING[/]"
            validation_table.add_row(err.field, status, err.message, err.remedy)

        if console:
            console.print(validation_table)

        if not result.success:
            log.critical(
                "Startup validation FAILED - One or more critical configuration errors found."
            )
            return 1
        else:
            log.warning("Startup validation passed with warnings.")

    # ── Startup Summary ────────────────────────────────────────────────────────
    try:
        from rich.console import Console as RichConsole
        from rich.panel import Panel as RichPanel
        from rich.table import Table as RichTable
    except ImportError:
        RichConsole = None
        RichPanel = None
        RichTable = None

    summary = RichTable.grid(expand=True, padding=(0, 1)) if RichTable else None
    summary.add_column(style="cyan", justify="right")
    summary.add_column(style="white", justify="left")

    # Environment Group
    hw = "CPU"
    if torch and torch.cuda.is_available():
        hw = f"GPU (CUDA: {torch.cuda.get_device_name(0)})"
    elif torch and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        hw = "GPU (MPS)"

    summary.add_row("[bold underline]Environment[/]", "")
    summary.add_row("Version:  ", f"[bold green]{get_system_version()}[/]")
    summary.add_row("OS:  ", f"{platform.system()} {platform.release()}")
    summary.add_row("Python:  ", platform.python_version())
    summary.add_row("Hardware:  ", hw)
    summary.add_row("", "")

    # Configuration Group
    summary.add_row("[bold underline]Configuration[/]", "")

    mode_tag = " [bold cyan](CLI OVERRIDE)[/]" if "mode" in provided_dest else ""
    summary.add_row("Mode:  ", f"[bold]{cfg.mode.upper()}[/]{mode_tag}")

    symbol_tag = " [bold cyan](CLI OVERRIDE)[/]" if "symbol" in provided_dest else ""
    summary.add_row("Symbol:  ", f"[bold]{cfg.symbol}[/]{symbol_tag}")

    tf_tag = " [bold cyan](CLI OVERRIDE)[/]" if "timeframe" in provided_dest else ""
    summary.add_row("Timeframe:  ", f"{cfg.timeframe}{tf_tag}")

    algo_tag = " [bold cyan](CLI OVERRIDE)[/]" if "algorithm" in provided_dest else ""
    summary.add_row("Algorithm:  ", f"{cfg.algorithm}{algo_tag}")

    # Account info for visibility
    masked_login = f"{str(cfg.mt5_login)[:3]}****" if len(str(cfg.mt5_login)) > 3 else "****"
    summary.add_row("Account:  ", f"{masked_login} @ {cfg.mt5_server}")
    summary.add_row(
        "Database:  ",
        "PostgreSQL" if "postgres" in cfg.database_url.get_secret_value() else "SQLite",
    )
    summary.add_row("", "")

    # Risk summary row
    summary.add_row("[bold underline]Risk Controls[/]", "")
    risk_color = (
        "red" if cfg.risk_per_trade > 0.02 else "yellow" if cfg.risk_per_trade > 0.01 else "green"
    )
    summary.add_row("Risk/Trade:  ", f"[{risk_color}]{cfg.risk_per_trade:.1%}[/]")

    daily_loss_color = (
        "red" if cfg.max_daily_loss > 0.06 else "yellow" if cfg.max_daily_loss > 0.05 else "green"
    )
    summary.add_row("Daily Stop:  ", f"[{daily_loss_color}]{cfg.max_daily_loss:.1%}[/]")

    pos_color = "red" if cfg.max_positions > 10 else "yellow" if cfg.max_positions > 5 else "green"
    summary.add_row("Max Positions:  ", f"[{pos_color}]{cfg.max_positions}[/]")

    conf_color = (
        "red" if cfg.min_confidence < 0.50 else "yellow" if cfg.min_confidence < 0.55 else "green"
    )
    summary.add_row("Min Confidence:  ", f"[{conf_color}]{cfg.min_confidence:.1%}[/]")

    if console:
        console.print(
            RichPanel(
                summary,
                title="[bold blue]Trading System Configuration[/]",
                border_style="blue",
                expand=False,
            )
        )

    # Initialise components
    # 1. Audit Logger (Mandatory for enterprise traceability)
    from src.core.audit_log import AuditLogger

    database_url = cfg.database_url.get_secret_value()
    audit_db_url = database_url if "sqlite" in database_url else "sqlite:///audit.db"
    audit_logger = AuditLogger(db_url=audit_db_url)

    # Dynamic exclusion of all SecretStr/SecretBytes fields for audit snapshot
    secret_fields = {
        f for f, info in cfg.__class__.model_fields.items() if "Secret" in str(info.annotation)
    }

    # Log sanitized configuration snapshot
    audit_logger.log_config_snapshot(
        cfg.model_dump(
            mode="json",
            exclude=secret_fields,
        )
    )
    audit_logger.log("system", "startup_initiated", f"Mode: {cfg.mode}, Algo: {cfg.algorithm}")

    from src.core.monitor import Monitor

    monitor = Monitor(cfg)
    # Note: Monitor's start_metrics_server is legacy;
    # Enterprise deployments use the FastAPI health app which includes /metrics.
    # However, we keep it for backward compatibility or individual component runs.
    monitor.start_metrics_server()

    from src.core.exceptions import MT5ConnectionError
    from src.trading.mt5_connector import MT5Connector

    connector = MT5Connector(cfg, monitor=monitor)
    status_ctx = (
        console.status("[bold green]Connecting to MT5 terminal...")
        if console
        else contextlib.nullcontext()
    )

    with status_ctx:
        try:
            connector.connect()
        except MT5ConnectionError as exc:
            # Enhanced connection diagnostics
            diag = RichTable.grid(expand=True)
            diag.add_column(style="cyan", justify="right")
            diag.add_column(style="white", justify="left")
            diag.add_row("Broker Server:  ", cfg.mt5_server)
            diag.add_row("Account Login:  ", str(cfg.mt5_login))
            diag.add_row("Terminal Path:  ", cfg.mt5_path)
            diag.add_row("OS Platform:    ", sys.platform)
            diag.add_row(
                "MetaAPI Config: ",
                "Present" if cfg.metaapi_token and cfg.metaapi_account_id else "Missing",
            )

            if console:
                console.print(
                    RichPanel(
                        diag,
                        title="[bold red]MT5 Connection Diagnostics[/]",
                        subtitle="Please verify these settings in your .env file",
                        border_style="red",
                    )
                )
            log.critical(
                "FAILED TO CONNECT: The system could not establish a session with MetaTrader 5 or MetaAPI.",
                error=str(exc),
            )
            return 1
    from src.core.decision_support import DecisionSupportSystem
    from src.core.feature_engineering import FeatureEngineer
    from src.core.health import HealthStatus, init_health_checker
    from src.core.trade_logger import TradeLogger
    from src.data.event_intelligence import (
        EventIntelligence,
        MetaAPIEventProvider,
        TradingViewEventProvider,
    )
    from src.models.ensemble import EnsembleModel
    from src.models.lstm_model import LSTMModel
    from src.models.ppo_agent import PPOAgent
    from src.models.regime_detector import RegimeDetector
    from src.models.transformer_model import TimeSeriesTransformer
    from src.trading.audited_risk_manager import AuditedRiskManager
    from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
    from src.trading.execution_filter import ExecutionFilter

    balance = connector.get_account_balance()
    trade_logger = TradeLogger(
        db_url=database_url if "sqlite" in database_url else "sqlite:///trades.db"
    )

    risk = AuditedRiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)

    # 5. Initialize Macro Intelligence
    providers = []
    if cfg.metaapi_token:
        providers.append(MetaAPIEventProvider(token=cfg.metaapi_token.get_secret_value()))

    # Always include TradingView mock as a baseline/fallback for deterministic patterns
    providers.append(TradingViewEventProvider())

    event_intelligence = EventIntelligence(providers=providers, fail_safe_blocked=False, config=cfg)

    execution_filter = ExecutionFilter(
        max_drawdown=cfg.max_drawdown if hasattr(cfg, "max_drawdown") else 0.15,
        config=cfg,
        event_intelligence=event_intelligence,
        monitor=monitor,
    )
    feature_engineer = FeatureEngineer(base_timeframe=cfg.timeframe)
    regime_detector = RegimeDetector()
    # Use balance for allocator; if balance is 0, CapitalAllocator will handle it (or fail validation)
    allocator = CapitalAllocator(total_budget=balance, monitor=monitor)
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
        model = EnsembleModel(device="cpu", config=cfg, monitor=monitor)
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        if ppo_path.exists():
            model.load_ppo(ppo_path)
        if lstm_path.exists():
            model.load_lstm(lstm_path)
    elif cfg.algorithm == "ppo":
        ppo_path = args.model_dir / "ppo_xauusd.zip"
        model = PPOAgent(model_path=ppo_path if ppo_path.exists() else None)  # type: ignore
    elif cfg.algorithm == "lstm":
        lstm_path = args.model_dir / "lstm_xauusd.pt"
        model = LSTMModel(model_path=lstm_path if lstm_path.exists() else None)  # type: ignore
    elif cfg.algorithm == "transformer":
        transformer_path = args.model_dir / "transformer_xauusd.pt"
        # Standard input_dim is 140 for the current feature engineer
        model = TimeSeriesTransformer(input_dim=140)
        if torch and transformer_path.exists():
            model.load_state_dict(
                torch.load(transformer_path, map_location="cpu", weights_only=True)
            )
    else:
        # This branch should rarely be hit if Literal choices are enforced by Pydantic
        log.warning(
            f"Algorithm {cfg.algorithm} not fully supported in main.py factory, falling back to Ensemble"
        )
        model = EnsembleModel(device="cpu", monitor=monitor)

    # Enterprise Health Gate
    health_checker = init_health_checker(
        cfg, connector, trade_logger, model, audit_logger=audit_logger
    )
    health_status_ctx = (
        console.status("[bold blue]Running health checks...")
        if console
        else contextlib.nullcontext()
    )

    with health_status_ctx:
        try:
            report = health_checker.startup_gate()
        except RuntimeError as exc:
            log.critical(str(exc))
            # Fetch report directly to show failure state in table
            report = health_checker.get_full_report()

    table = RichTable(title="System Health", box=None)
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Message")
    table.add_column("Suggested Remedy", style="green")
    for name, comp in report.components.items():
        color = (
            "green"
            if comp.status == HealthStatus.HEALTHY
            else "yellow"
            if comp.status == HealthStatus.DEGRADED
            else "red"
        )
        table.add_row(name, f"[{color}]{comp.status.value.upper()}[/]", comp.message, comp.remedy)

    if console:
        console.print(table)

    if report.status == HealthStatus.FAILED:
        log.critical("Startup HEALTH CHECK FAILED - Aborting.")
        return 1

    if args.check:
        log.info("Pre-flight check COMPLETE. System is healthy.")

        next_steps = RichTable.grid(expand=True)
        next_steps.add_column(style="cyan", justify="right")
        next_steps.add_column(style="white", justify="left")

        next_steps.add_row("Demo Trading:  ", f"python main.py --mode demo --algo {cfg.algorithm}")
        next_steps.add_row(
            "Live Trading:  ", f"python main.py --mode live --algo {cfg.algorithm} --confirm-live"
        )
        next_steps.add_row(
            "Backtesting:   ",
            f"python main.py --mode backtest --algo {cfg.algorithm} --start 2017-01-01 --end 2026-03-30",
        )

        if console:
            console.print(
                RichPanel(
                    next_steps,
                    title="[bold green]Ready for Execution[/]",
                    subtitle="Use the commands below to start the bot",
                    border_style="green",
                    expand=False,
                )
            )
        return 0

    # Record successful deployment/startup
    from src import __version__

    audit_logger.log_deployment(version=__version__, environment=cfg.mode)
    audit_logger.log_operator_action(
        operator="system",
        action="trading_engine_started",
        reason=f"System transition to RUNNING state in {cfg.mode} mode",
        metadata={
            "mode": cfg.mode,
            "algo": cfg.algorithm,
            "symbol": cfg.symbol,
            "version": __version__,
        },
    )

    try:
        if cfg.mode in ("demo", "live"):
            run_live(
                cfg,
                connector,
                risk,
                model,
                execution_filter,
                event_intelligence,
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
            connector.disconnect()  # Already connected in run_backtest bridge
            return run_backtest(args, cfg, feature_engineer, execution_filter, model, console, log)
    finally:
        if audit_logger:
            audit_logger.log_operator_action(
                operator="system",
                action="shutdown_initiated",
                reason="Cleaning up resources and disconnecting",
            )
        if connector._is_initialized:
            connector.disconnect()
        if event_intelligence:
            event_intelligence.close()
        if audit_logger:
            audit_logger.log_operator_action(
                operator="system",
                action="shutdown_completed",
                reason="System shutdown sequence finished",
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
