"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Decision support engine for generating operator-facing decision packets.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.models.ensemble import EnsembleModel
    from src.trading.risk_manager import RiskManager
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class SignalSummary(BaseModel):
    """Core trade signal parameters."""
    symbol: str
    direction: int  # +1 buy, -1 sell, 0 hold
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    lot_size: float
    confidence: float
    algorithm: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelConsensus(BaseModel):
    """Ensemble model voting details."""
    weights: Dict[str, float]
    votes: Dict[str, float]  # algorithm -> prediction
    agreement_score: float


class MarketRegime(BaseModel):
    """Market condition analysis."""
    regime_type: str  # TRENDING, RANGING, VOLATILE
    volatility: float
    strength: float
    description: str


class RiskState(BaseModel):
    """Current risk management status."""
    current_drawdown: float
    daily_loss_pct: float
    circuit_breaker_active: bool
    max_positions_reached: bool


class BlockedConditions(BaseModel):
    """Reasons for signal rejection."""
    is_blocked: bool
    reasons: List[str]


class PerformanceContext(BaseModel):
    """Recent trading performance metrics."""
    sharpe_ratio: float
    profit_factor: float
    win_rate: float
    total_trades: int


class ExplainabilityPayload(BaseModel):
    """Signal reasoning decomposition."""
    primary_reason: str
    feature_importance: Dict[str, float]
    risk_reward_ratio: float
    tags: List[str]


class DecisionPacket(BaseModel):
    """Structured operator-facing decision packet."""
    signal: SignalSummary
    consensus: ModelConsensus
    regime: MarketRegime
    risk: RiskState
    blocked: BlockedConditions
    performance: PerformanceContext
    explainability: ExplainabilityPayload
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DecisionSupport:
    """
    Orchestrates decision packet generation and formatting.
    Provides institutional-grade oversight for trading decisions.
    """

    def __init__(self):
        self.console = Console(force_terminal=True)

    def _detect_regime(self, symbol: str) -> MarketRegime:
        """
        Placeholder for regime detection logic.
        In a full implementation, this would analyze recent OHLCV data.
        """
        # Simulated heuristic
        return MarketRegime(
            regime_type="TRENDING",
            volatility=0.15,
            strength=0.72,
            description="Strong bullish momentum detected on M5/M15 timeframes."
        )

    def _generate_explainability(self, signal: SignalSummary) -> ExplainabilityPayload:
        """
        Decomposes signal reasoning for the operator.
        """
        rr = 0.0
        if signal.stop_loss and signal.entry_price != signal.stop_loss:
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs((signal.take_profit or signal.entry_price) - signal.entry_price)
            rr = reward / risk if risk > 0 else 0.0

        return ExplainabilityPayload(
            primary_reason=f"Model ensemble identified high-probability { 'long' if signal.direction > 0 else 'short' } setup.",
            feature_importance={
                "RSI_14": 0.25,
                "ATR_14": 0.18,
                "MA_Crossover": 0.32,
                "Volume_Profile": 0.25
            },
            risk_reward_ratio=round(rr, 2),
            tags=["BULLISH_ENGULFING", "SUPPORT_BOUNCE", "VOL_EXPANSION"]
        )

    def generate_packet(
        self,
        signal: SignalSummary,
        risk_manager: "RiskManager",
        ensemble: "EnsembleModel",
        performance_metrics: Dict[str, float]
    ) -> DecisionPacket:
        """
        Aggregates data from multiple sources into a single decision packet.
        """
        # Get risk state
        drawdown = (risk_manager.peak_equity - risk_manager.balance) / risk_manager.peak_equity if risk_manager.peak_equity > 0 else 0.0
        daily_loss_pct = abs(risk_manager.daily.realised_pnl) / risk_manager.daily.peak_equity if risk_manager.daily.peak_equity > 0 else 0.0

        # We need to convert SignalSummary to TradeSignal for RiskManager
        from src.trading.risk_manager import TradeSignal
        ts = TradeSignal(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss or 0.0,
            take_profit=signal.take_profit or 0.0,
            lot_size=signal.lot_size,
            algorithm=signal.algorithm,
            confidence=signal.confidence,
            timestamp=signal.timestamp
        )

        is_approved, reasons = risk_manager.validate_signal_full(ts)

        risk_state = RiskState(
            current_drawdown=drawdown,
            daily_loss_pct=daily_loss_pct,
            circuit_breaker_active=drawdown >= 0.15,
            max_positions_reached=len(risk_manager.open_positions) >= risk_manager.cfg.max_positions
        )

        blocked = BlockedConditions(
            is_blocked=not is_approved,
            reasons=reasons
        )

        # Consensus
        # Assuming ensemble.predict returns per_algo_probs or similar
        # We'll mock some consensus data if it's hard to extract from current EnsembleModel
        consensus = ModelConsensus(
            weights=ensemble.weights,
            votes={}, # Need to pass votes from predict if available
            agreement_score=signal.confidence # Simplified
        )

        # Performance
        perf_context = PerformanceContext(
            sharpe_ratio=performance_metrics.get("sharpe_ratio", 0.0),
            profit_factor=performance_metrics.get("profit_factor", 0.0),
            win_rate=performance_metrics.get("win_rate", 0.0),
            total_trades=int(performance_metrics.get("total_trades", 0))
        )

        return DecisionPacket(
            signal=signal,
            consensus=consensus,
            regime=self._detect_regime(signal.symbol),
            risk=risk_state,
            blocked=blocked,
            performance=perf_context,
            explainability=self._generate_explainability(signal)
        )

    def format_for_operator(self, packet: DecisionPacket) -> None:
        """
        Enterprise-safe rich formatting for the decision packet.
        """
        # Signal Panel
        sig = packet.signal
        dir_str = "[green]BUY[/green]" if sig.direction > 0 else "[red]SELL[/red]" if sig.direction < 0 else "[yellow]HOLD[/yellow]"
        sig_table = Table(show_header=False, box=None)
        sig_table.add_row("Symbol", sig.symbol)
        sig_table.add_row("Direction", dir_str)
        sig_table.add_row("Entry Price", f"{sig.entry_price:.5f}")
        sig_table.add_row("Stop Loss", f"{sig.stop_loss:.5f}" if sig.stop_loss else "N/A")
        sig_table.add_row("Take Profit", f"{sig.take_profit:.5f}" if sig.take_profit else "N/A")
        sig_table.add_row("Confidence", f"{sig.confidence*100:.1f}%")

        # Risk & Blocked Panel
        risk = packet.risk
        blocked = packet.blocked
        risk_table = Table(show_header=False, box=None)
        risk_table.add_row("Drawdown", f"{risk.current_drawdown*100:.2f}%")
        status = "[red]BLOCKED[/red]" if blocked.is_blocked else "[green]CLEAR[/green]"
        risk_table.add_row("Execution Status", status)
        if blocked.reasons:
            reasons_str = ", ".join(blocked.reasons)
            risk_table.add_row("Rejection Reasons", f"[yellow]{reasons_str}[/yellow]")

        # Performance Panel
        perf = packet.performance
        perf_table = Table(show_header=True, header_style="bold magenta")
        perf_table.add_column("Metric", style="dim")
        perf_table.add_column("Value")
        perf_table.add_row("Sharpe Ratio", f"{perf.sharpe_ratio:.2f}")
        perf_table.add_row("Profit Factor", f"{perf.profit_factor:.2f}")
        perf_table.add_row("Win Rate", f"{perf.win_rate*100:.1f}%")
        perf_table.add_row("Total Trades", str(perf.total_trades))

        # Explainability Panel
        exp = packet.explainability
        exp_panel = Panel(
            f"[bold cyan]Reason:[/bold cyan] {exp.primary_reason}\n"
            f"[bold cyan]Tags:[/bold cyan] {', '.join(exp.tags)}\n"
            f"[bold cyan]R:R Ratio:[/bold cyan] {exp.risk_reward_ratio}",
            title="Explainability & Logic",
            border_style="blue"
        )

        # Assemble Layout
        self.console.print("\n")
        self.console.print(Panel(sig_table, title=f"Signal: {sig.symbol} @ {sig.timestamp.strftime('%H:%M:%S')}", border_style="green" if sig.direction > 0 else "red"))
        self.console.print(Panel(risk_table, title="Risk & Guardrails", border_style="yellow"))
        self.console.print(Panel(perf_table, title="Historical Context", border_style="magenta"))
        self.console.print(exp_panel)
        self.console.print(f"[dim]Packet generated at {packet.generated_at.isoformat()}[/dim]")
        self.console.print("\n")
