"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Operator-facing decision support system for trade review and oversight.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.core.explainability import SignalDirection, SignalExplanation
from src.models.regime_detector import RegimeInfo
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


class PerformanceContext(BaseModel):
    """Recent performance metrics for context."""

    sharpe_ratio: float = Field(..., description="Strategy Sharpe Ratio")
    profit_factor: float = Field(..., description="Gross Profit / Gross Loss")
    max_drawdown: float = Field(..., description="Maximum Peak-to-Valley Drawdown")
    win_rate: float = Field(..., description="Percentage of profitable trades")
    total_trades: int = Field(..., description="Total closed trades recorded")
    recent_pnl: float = Field(0.0, description="Realised PnL in the current session")


class DecisionPacket(BaseModel):
    """
    Comprehensive decision packet for operator review.
    Aggregates signal, risk, regime, and performance context.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the decision was evaluated",
    )
    symbol: str = Field(..., description="Trading symbol (e.g., XAUUSD)")
    direction: SignalDirection = Field(..., description="Proposed trade direction")
    confidence: float = Field(..., description="Ensemble confidence level")

    # Model Consensus
    model_consensus: Dict[str, str] = Field(
        ..., description="Directional vote per model in the ensemble"
    )

    # Market Regime
    regime: RegimeInfo = Field(..., description="Current detected market regime")

    # Risk State
    risk_approved: bool = Field(..., description="Whether the signal passed risk filters")
    blocked_reasons: List[str] = Field(
        default_factory=list, description="Reasons for risk rejection if any"
    )
    risk_reward_ratio: float = Field(..., description="Risk-to-Reward ratio for this trade")
    lot_size: float = Field(..., description="Calculated position size in lots")

    # Performance Context
    performance: PerformanceContext = Field(..., description="Historical performance context")

    # Explainability Payload
    explanation: SignalExplanation = Field(..., description="Deep attribution and explanation")

    human_summary: str = Field(..., description="Concise natural language summary for the operator")


class DecisionSupport:
    """
    Orchestrator for generating and formatting decision packets.
    Provides institutional-grade oversight for trade decisions.
    """

    def __init__(
        self,
        trade_logger: Any,
        risk_manager: Any,
        regime_detector: Any,
        signal_explainer: Any,
    ) -> None:
        self.trade_logger = trade_logger
        self.risk_manager = risk_manager
        self.regime_detector = regime_detector
        self.signal_explainer = signal_explainer

    def generate_packet(
        self,
        signal: TradeSignal,
        regime_info: RegimeInfo,
        explanation: SignalExplanation,
    ) -> DecisionPacket:
        """
        Synthesize all available context into a structured DecisionPacket.
        """
        # 1. Fetch performance context
        perf_data = self.trade_logger.read_performance_report()
        # Ensure we handle missing fields from legacy or simplified report
        performance = PerformanceContext(
            sharpe_ratio=perf_data.get("sharpe_ratio", 0.0),
            profit_factor=perf_data.get("profit_factor", 0.0),
            max_drawdown=perf_data.get("max_drawdown", 0.0),
            win_rate=perf_data.get("win_rate", 0.0),
            total_trades=perf_data.get("total_trades", 0),
            recent_pnl=getattr(self.risk_manager.daily, "realised_pnl", 0.0),
        )

        # 2. Risk Evaluation (Side-effect free)
        # If the risk_manager supports _get_rejection_reason, use it for dry-run
        if hasattr(self.risk_manager, "_get_rejection_reason"):
            blocked_reasons = self.risk_manager._get_rejection_reason(signal)
        else:
            # Fallback for now - logic will be added to risk_manager in next steps
            blocked_reasons = [] if explanation.risk_assessment.passed else explanation.risk_assessment.rejection_reasons

        risk_approved = len(blocked_reasons) == 0

        # 3. Model Consensus
        consensus = {
            attr.model_name: attr.vote.name for attr in explanation.model_attributions
        }

        # 4. Human Summary
        summary = (
            f"{'✅ APPROVED' if risk_approved else '❌ BLOCKED'} "
            f"{explanation.direction.name} {signal.symbol} @ {signal.entry_price:.2f} "
            f"| Conf: {signal.confidence:.1%} | R:R: {explanation.risk_assessment.risk_reward_ratio:.2f}"
        )

        return DecisionPacket(
            symbol=signal.symbol,
            direction=explanation.direction,
            confidence=signal.confidence,
            model_consensus=consensus,
            regime=regime_info,
            risk_approved=risk_approved,
            blocked_reasons=blocked_reasons,
            risk_reward_ratio=explanation.risk_assessment.risk_reward_ratio,
            lot_size=signal.lot_size,
            performance=performance,
            explanation=explanation,
            human_summary=summary,
        )

    def format_for_terminal(self, packet: DecisionPacket) -> str:
        """
        Render the decision packet as a high-fidelity terminal dashboard.
        """
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console(force_terminal=True, width=100)

            # Header
            status_color = "green" if packet.risk_approved else "red"
            header = Panel(
                f"[bold {status_color}]{packet.human_summary}[/bold {status_color}]",
                title=f"Institutional Decision Support | {packet.symbol}",
                subtitle=f"{packet.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                box=box.DOUBLE,
                border_style=status_color
            )

            # Performance & Regime Table
            context_table = Table(box=box.SIMPLE, expand=True)
            context_table.add_column("Market Context", style="cyan")
            context_table.add_column("Strategy Performance", style="magenta")

            regime_str = (
                f"Regime: [bold]{packet.regime.label.value.upper()}[/bold]\n"
                f"Confidence: {packet.regime.confidence:.1%}\n"
                f"Volatility: {packet.regime.volatility_index:.2f}x"
            )
            perf_str = (
                f"Win Rate: {packet.performance.win_rate:.1%}\n"
                f"Sharpe: {packet.performance.sharpe_ratio:.2f}\n"
                f"Daily PnL: {packet.performance.recent_pnl:+.2f}"
            )
            context_table.add_row(regime_str, perf_str)

            # Consensus & Risk Table
            detail_table = Table(box=box.SIMPLE, expand=True)
            detail_table.add_column("Model Consensus", style="yellow")
            detail_table.add_column("Risk Assessment", style="white")

            consensus_str = "\n".join([f"• {m}: {v}" for m, v in packet.model_consensus.items()])

            risk_status = "[bold green]PASS[/bold green]" if packet.risk_approved else "[bold red]FAIL[/bold red]"
            risk_str = (
                f"Gate: {risk_status}\n"
                f"Size: {packet.lot_size:.2f} lots\n"
                f"R:R: {packet.risk_reward_ratio:.2f}"
            )
            if packet.blocked_reasons:
                risk_str += f"\n[dim]Blocked by: {', '.join(packet.blocked_reasons)}[/dim]"

            detail_table.add_row(consensus_str, risk_str)

            # Execution
            with console.capture() as capture:
                console.print(header)
                console.print(context_table)
                console.print(detail_table)
                console.print(Panel(packet.explanation.human_readable_summary, title="Explainability Attribution", box=box.ROUNDED))

            return capture.get()

        except ImportError:
            # Fallback to plain text
            output = f"=== DECISION PACKET: {packet.symbol} ===\n"
            output += f"Summary: {packet.human_summary}\n"
            output += f"Regime: {packet.regime.label.value} (Conf: {packet.regime.confidence:.1%})\n"
            output += f"Performance: Sharpe {packet.performance.sharpe_ratio:.2f}, WinRate {packet.performance.win_rate:.1%}\n"
            output += "Model Consensus:\n"
            for m, v in packet.model_consensus.items():
                output += f"  - {m}: {v}\n"
            if packet.blocked_reasons:
                output += f"Blocked Reasons: {', '.join(packet.blocked_reasons)}\n"
            output += f"Explainability: {packet.explanation.human_readable_summary}\n"
            return output
