"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Decision support system for institutional operator oversight.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.trading.risk_manager import RiskManager, TradeSignal

logger = logging.getLogger(__name__)


class MarketRegime(BaseModel):
    """Current market regime assessment."""

    name: str = "Unknown"
    volatility: str = "Normal"  # Low, Normal, High, Extreme
    trend: str = "Neutral"  # Bullish, Bearish, Neutral
    description: Optional[str] = None


class SignalSummary(BaseModel):
    """Summary of the generated AI signal."""

    direction: int
    confidence: float
    consensus: Dict[str, float] = Field(default_factory=dict)
    algorithm: str
    explainability: Dict[str, Any] = Field(default_factory=dict)


class RiskSummary(BaseModel):
    """Summary of the risk management state."""

    is_approved: bool
    rejection_reason: Optional[str] = None
    current_drawdown: float
    daily_pnl: float
    blocked_conditions: List[str] = Field(default_factory=list)


class PerformanceContext(BaseModel):
    """Contextual performance metrics."""

    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    recent_trades_count: int = 0


class DecisionPacket(BaseModel):
    """Structured decision support packet for institutional oversight."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    regime: MarketRegime
    signal: SignalSummary
    risk: RiskSummary
    performance: PerformanceContext
    meta: Dict[str, Any] = Field(default_factory=dict)


class DecisionSupport:
    """
    Generates structured decision packets to provide operator confidence.
    Aggregates data from models, risk management, and market analysis.
    """

    def __init__(self, risk_manager: RiskManager, console: Optional[Console] = None) -> None:
        self.risk_manager = risk_manager
        self.console = console or Console()

    def detect_regime(self, ohlcv_data: Any) -> MarketRegime:
        """
        Detects market regime based on OHLCV data.
        Placeholder implementation using basic heuristics.
        """
        # In a real implementation, this would use ATR, ADX, or a trained Regime Classifier.
        return MarketRegime(
            name="Ranging",
            volatility="Normal",
            trend="Neutral",
            description="Market showing no clear trend on current timeframe.",
        )

    def generate_packet(
        self,
        signal: TradeSignal,
        consensus: Dict[str, float],
        ohlcv_data: Any,
        performance_metrics: Optional[Dict[str, float]] = None,
    ) -> DecisionPacket:
        """Generates a complete decision packet for the given signal."""
        # Check risk approval without logging a risk event (dry run)
        rejection_reason = self._get_rejection_reason(signal)
        is_approved = rejection_reason == ""

        regime = self.detect_regime(ohlcv_data)

        # Build risk summary
        risk_summary = RiskSummary(
            is_approved=is_approved,
            rejection_reason=rejection_reason if not is_approved else None,
            current_drawdown=(self.risk_manager.peak_equity - self.risk_manager.balance)
            / self.risk_manager.peak_equity
            if self.risk_manager.peak_equity > 0
            else 0.0,
            daily_pnl=self.risk_manager.daily.realised_pnl,
            blocked_conditions=[rejection_reason] if not is_approved else [],
        )

        # Build signal summary
        signal_summary = SignalSummary(
            direction=signal.direction,
            confidence=signal.confidence,
            consensus=consensus,
            algorithm=signal.algorithm,
            explainability={"per_model_votes": consensus},
        )

        # Build performance context
        metrics = performance_metrics or {}
        perf_context = PerformanceContext(
            win_rate=metrics.get("win_rate", 0.0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            recent_trades_count=int(metrics.get("total_trades", 0)),
        )

        return DecisionPacket(
            symbol=signal.symbol,
            regime=regime,
            signal=signal_summary,
            risk=risk_summary,
            performance=perf_context,
        )

    def format_for_terminal(self, packet: DecisionPacket) -> Panel:
        """Creates a rich-formatted Panel for terminal output."""
        table = Table.grid(expand=True)
        table.add_column(style="cyan", justify="right")
        table.add_column(style="white", justify="left")

        # Symbol and Direction
        dir_str = "BUY 🟢" if packet.signal.direction == 1 else "SELL 🔴" if packet.signal.direction == -1 else "HOLD ⚪"
        table.add_row("Action:", f"[bold]{dir_str}[/bold] @ {packet.symbol}")
        table.add_row("Confidence:", f"{packet.signal.confidence:.2%}")

        # Regime
        table.add_row("Regime:", f"{packet.regime.name} ({packet.regime.volatility} Vol)")

        # Risk
        status_str = "[green]APPROVED[/green]" if packet.risk.is_approved else f"[red]REJECTED[/red] ({packet.risk.rejection_reason})"
        table.add_row("Risk Status:", status_str)
        table.add_row("Drawdown:", f"{packet.risk.current_drawdown:.2%}")

        # Consensus
        consensus_str = ", ".join([f"{k}: {v}" for k, v in packet.signal.consensus.items()])
        table.add_row("Consensus:", consensus_str)

        return Panel(
            table,
            title=f"Decision Support Packet | {packet.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle="Institutional Grade Execution Gate",
            border_style="blue" if packet.risk.is_approved else "red",
        )

    def _get_rejection_reason(self, signal: TradeSignal) -> str:
        """Simulate risk approval to find rejection reason without side effects."""
        # Copy of logic from RiskManager.approve to avoid state changes or logging
        # In a real system, RiskManager should have a 'check' method that returns the reason.
        if (
            self.risk_manager.peak_equity > 0
            and (self.risk_manager.peak_equity - self.risk_manager.balance) / self.risk_manager.peak_equity >= 0.15
        ):
            return "Circuit breaker active"

        if self.risk_manager.daily.peak_equity > 0:
            loss_pct = abs(self.risk_manager.daily.realised_pnl) / self.risk_manager.daily.peak_equity
            if self.risk_manager.daily.realised_pnl < 0 and loss_pct >= self.risk_manager.cfg.max_daily_loss:
                return "Daily loss limit reached"

        if len(self.risk_manager.open_positions) >= self.risk_manager.cfg.max_positions:
            return "Max positions reached"

        from src.trading.risk_manager import ALLOCATION_WEIGHTS
        if signal.symbol not in ALLOCATION_WEIGHTS:
            return f"Symbol {signal.symbol} not in portfolio"

        if signal.confidence < 0.55:
            return f"Confidence {signal.confidence:.2f} too low"

        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0 or (reward / risk) < 1.5:
            return "Risk-Reward ratio too low"

        return ""
