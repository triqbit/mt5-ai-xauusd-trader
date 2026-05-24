"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/executor.py

Institutional trading executor responsible for the live trading loop,
signal preparation, and automated order execution.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import pandas as pd
import structlog

from src.core.constants import SignalDirection
from src.core.exceptions import (
    CircuitBreakerError,
    MT5ConnectionError,
    MT5DataError,
    MT5ExecutionError,
)
from src.core.explainability import SignalExplainer
from src.core.schemas import TradeSignal

if TYPE_CHECKING:
    from rich.console import Console
    from structlog import BoundLogger

    from src.core.audit_log import AuditLogger
    from src.core.config import TradingConfig
    from src.core.decision_support import DecisionSupportSystem
    from src.core.feature_engineering import FeatureEngineer
    from src.core.monitor import Monitor
    from src.core.trade_logger import TradeLogger
    from src.data.event_intelligence import EventIntelligence
    from src.models.base_model import BaseModel
    from src.models.regime_detector import RegimeDetector
    from src.trading.capital_allocator import CapitalAllocator
    from src.trading.execution_filter import ExecutionFilter
    from src.trading.mt5_connector import MT5Connector
    from src.trading.risk_manager import RiskManager


class TradingExecutor:
    """
    Enterprise-grade trading executor.
    Orchestrates the lifecycle of signal generation, risk validation, and execution.
    """

    def __init__(
        self,
        config: "TradingConfig",
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
        audit_logger: Optional["AuditLogger"] = None,
        console: Optional["Console"] = None,
    ):
        self.cfg = config
        self.connector = connector
        self.risk = risk
        self.model = model
        self.filter = execution_filter
        self.events = event_intelligence
        self.fe = feature_engineer
        self.regime = regime_detector
        self.allocator = allocator
        self.dss = dss
        self.trade_logger = trade_logger
        self.monitor = monitor
        self.audit = audit_logger
        self.console = console
        self.log = structlog.get_logger("executor")
        self.explainer = SignalExplainer()

    def run_live(self) -> None:
        """Main institutional trading loop."""
        import structlog.contextvars
        from src.core import profile

        self.log.info("Starting live trading loop", symbol=self.cfg.symbol, mode=self.cfg.mode)
        poll_interval = 60
        last_reset_date = datetime.now(timezone.utc).date()
        loop_count = 0
        last_price = None

        while True:
            iteration_start = time.perf_counter()
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(trace_id=str(uuid.uuid4()))

            iteration_status = "processing"
            final_direction = 0
            final_confidence = 0.0
            confluence_score = 0.0

            # 0. Periodic Audit
            if loop_count % 100 == 0 and self.audit:
                secret_fields = {
                    f
                    for f, info in self.cfg.__class__.model_fields.items()
                    if "Secret" in str(info.annotation)
                }
                self.audit.log_config_snapshot(
                    self.cfg.model_dump(mode="json", exclude=secret_fields),
                    reason=f"periodic_check_loop_{loop_count}",
                )
            loop_count += 1

            # 0.1 Account metrics
            try:
                balance = self.connector.get_account_balance()
                self.risk.update_equity(balance)
                if self.monitor:
                    self.monitor.log_equity(balance)
            except Exception as e:
                self.log.error("Failed to update account metrics", error=str(e))

            # 0.2 Day reset
            current_date = datetime.now(timezone.utc).date()
            if current_date > last_reset_date:
                self.log.info("Day change detected, resetting daily stats")
                self.risk.reset_daily()
                last_reset_date = current_date

            with profile("loop_total"):
                try:
                    # 1. Fetch data
                    with profile("data_fetch"):
                        df_raw = self.connector.get_ohlcv(self.cfg.symbol, self.cfg.timeframe, n_bars=500)
                        tick = self.connector.get_tick(self.cfg.symbol)
                        if not tick or "bid" not in tick:
                            time.sleep(poll_interval)
                            continue

                        current_price = tick["bid"]
                        if last_price is not None and hasattr(self.model, "observe_outcome"):
                            actual_dir = SignalDirection.HOLD
                            if current_price > last_price * (1 + self.cfg.outcome_noise_threshold):
                                actual_dir = SignalDirection.BUY
                            elif current_price < last_price * (1 - self.cfg.outcome_noise_threshold):
                                actual_dir = SignalDirection.SELL
                            self.model.observe_outcome(actual_dir)
                        last_price = current_price

                    # 2. Context detection
                    with profile("institutional_context"):
                        df_features = self.fe.compute_features(df_raw)
                        obs = df_features.values[-1]
                        regime_info = self.regime.detect(df_raw)

                    # 3. Inference
                    with profile("inference"):
                        signal_obj = self.model.predict(
                            obs, regime_info=regime_info, symbol=self.cfg.symbol
                        )
                        direction = signal_obj.direction
                        confidence = signal_obj.confidence
                        final_direction = direction
                        final_confidence = confidence

                        if self.audit:
                            self.audit.log_prediction(
                                symbol=self.cfg.symbol,
                                direction=direction,
                                confidence=confidence,
                                model_metadata=getattr(signal_obj, "metadata", None),
                            )

                    # 4. Preparation & Risk
                    price = tick["ask"] if direction == 1 else tick["bid"]
                    macro_risk = self.events.get_risk_status(datetime.now(timezone.utc))

                    atr_col = f"base_{self.cfg.timeframe}_atr"
                    atr = float(df_features[atr_col].iloc[-1]) if atr_col in df_features.columns else 0.0

                    signal = self._prepare_trade_signal(
                        direction, confidence, price, atr, macro_risk.risk_multiplier
                    )

                    # 5. Risk Gate (8-layer cascade)
                    open_pos = self.connector.get_positions(self.cfg.symbol)
                    health = getattr(self.model, "get_health_metrics", lambda: None)()

                    risk_decision = self.risk.validate_signal(
                        signal, df_features, open_pos, model_health=health
                    )

                    if not risk_decision.is_approved and direction != 0:
                        self.log.warning("risk_rejected", reason=risk_decision.reason)

                    # 6. Execution Filter
                    filter_decision = None
                    approved = risk_decision.is_approved
                    if approved:
                        drawdown = (self.risk.peak_equity - self.risk.balance) / self.risk.peak_equity
                        filter_decision = self.filter.validate(
                            signal, df_features, current_drawdown=drawdown,
                            timestamp=datetime.now(timezone.utc), model_health=health
                        )
                        approved = filter_decision.is_approved
                        if not approved:
                            self.log.warning("filter_blocked", reason=filter_decision.blocked_by)

                    # 8. Decision Support System (Cockpit)
                    if direction != 0:
                        with profile("decision_support"):
                            model_votes = getattr(signal_obj, "metadata", {}).get("per_algo_votes", {self.cfg.algorithm: direction})
                            model_weights = getattr(signal_obj, "metadata", {}).get("weights", {self.cfg.algorithm: 1.0})

                            explanation = self.explainer.explain(
                                symbol=self.cfg.symbol,
                                direction=direction,
                                confidence=confidence,
                                model_votes=model_votes,
                                model_weights=model_weights,
                                risk_data={"passed": risk_decision.is_approved, "summary": risk_decision.reason},
                                regime_info={"name": regime_info.label.value, "confidence": regime_info.confidence},
                                execution_data={"passed": filter_decision.is_approved, "summary": filter_decision.blocked_by} if filter_decision else None
                            )
                            confluence_score = explanation.get_confluence_score()

                            packet = self.dss.assemble_packet(
                                self.cfg.symbol, explanation, regime_info, macro_risk, {}
                            )
                            if self.console:
                                self.dss.format_for_operator(packet, console=self.console)
                            else:
                                self.log.info("decision_cockpit", summary=explanation.human_readable_summary)

                    # 7. Execute
                    if approved and direction != 0:
                        try:
                            # Use adjusted lot size from risk manager
                            signal = signal.model_copy(update={"lot_size": risk_decision.adjusted_lot_size})
                            ticket = self.connector.place_order(signal)
                            if ticket:
                                self.log.info("order_placed", ticket=ticket)
                                if self.trade_logger:
                                    self.trade_logger.log_trade(
                                        ticket=ticket, symbol=self.cfg.symbol,
                                        direction=direction, entry_price=price,
                                        lot_size=signal.lot_size
                                    )
                        except MT5ExecutionError as e:
                            self.log.error("execution_failed", error=str(e))

                    # 8. Check for closed positions
                    current_positions = self.connector.get_positions(self.cfg.symbol)
                    current_tickets = {p["ticket"] for p in current_positions}

                    # Logic to detect closed positions and update logger...
                    # (Simplified for now to match the scope of refactoring)

                    iteration_status = "success"

                except (MT5DataError, MT5ConnectionError) as e:
                    self.log.error("connection_or_data_error", error=str(e))
                    time.sleep(poll_interval)
                    continue
                except Exception as e:
                    self.log.exception("unexpected_loop_error", error=str(e))
                    time.sleep(poll_interval)
                    continue

            self.log.info("iteration_summary", status=iteration_status, direction=final_direction, duration_ms=round((time.perf_counter() - iteration_start)*1000, 2))
            time.sleep(poll_interval)

    def _prepare_trade_signal(
        self,
        direction: int,
        confidence: float,
        price: float,
        atr: float,
        risk_multiplier: float = 1.0,
    ) -> "TradeSignal":
        from src.core.schemas import TradeSignal

        # Standard SL/TP logic (2x ATR / 4x ATR)
        sl = price - (direction * 2 * atr) if atr > 0 else price * (1 - direction * 0.01)
        tp = price + (direction * 4 * atr) if atr > 0 else price * (1 + direction * 0.02)

        # Initial lot size (to be refined by risk manager)
        lot_size = self.cfg.min_lot_size

        return TradeSignal(
            symbol=self.cfg.symbol,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            lot_size=lot_size,
            algorithm=self.cfg.algorithm,
            confidence=confidence,
        )
