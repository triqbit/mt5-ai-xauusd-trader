"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Structured operator-facing decision support system.
Provides institutional-grade decision packets before execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import SignalDirection
from src.core.explainability import SignalExplainer, SignalExplanation
from src.data.event_intelligence import RiskStatus
from src.models.regime_detector import RegimeInfo

logger = logging.getLogger(__name__)


class PerformanceContext(BaseModel):
    """Recent performance metrics for the current strategy/account."""

    sharpe_ratio: float = Field(0.0, description="Recent Sharpe Ratio")
    profit_factor: float = Field(0.0, description="Recent Profit Factor")
    max_drawdown: float = Field(0.0, description="Maximum drawdown observed")
    win_rate: float = Field(0.0, description="Recent win rate percentage")
    total_trades: int = Field(0, description="Total trades in the analysis window")


class DecisionPacket(BaseModel):
    """
    Unified packet for operator review before trade execution.
    Aggregates all critical dimensions of a trading decision.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    symbol: str = Field(..., description="Target trading symbol")
    direction: SignalDirection = Field(..., description="Final signal direction")
    consensus: str = Field(..., description="Qualitative model consensus level")
    is_executable: bool = Field(False, description="Final decision on whether the trade should proceed")
    blocking_reasons: list[str] = Field(default_factory=list, description="List of reasons if the trade is blocked")

    # Components
    explanation: SignalExplanation = Field(..., description="ML signal attribution and explainability")
    regime: RegimeInfo = Field(..., description="Current market regime context")
    macro_risk: RiskStatus = Field(..., description="Macroeconomic event risk status")
    performance: PerformanceContext = Field(..., description="Recent performance context")


class DecisionSupportSystem:
    """
    Orchestrator for generating decision packets.
    Integrates multiple system components to provide a unified 'Go/No-Go' view.
    """

    def __init__(self) -> None:
        self.explainer = SignalExplainer()

    def assemble_packet(
        self,
        symbol: str,
        explanation: SignalExplanation,
        regime_info: RegimeInfo,
        macro_risk: RiskStatus,
        performance_metrics: dict[str, Any],
    ) -> DecisionPacket:
        """
        Assemble a complete decision packet from system components.
        """
        blocking_reasons = []

        # 1. Check Execution Filters
        if not explanation.execution_summary.passed:
            blocking_reasons.append(f"Execution: {explanation.execution_summary.summary}")

        # 2. Check Risk Manager Assessment
        if not explanation.risk_assessment.passed:
            reasons = ", ".join(explanation.risk_assessment.rejection_reasons)
            blocking_reasons.append(f"Risk: {reasons}")

        # 3. Check Macro Event Blocks
        if macro_risk.is_blocked:
            blocking_reasons.append(f"Macro: {macro_risk.reason}")

        # Determine if executable
        is_executable = len(blocking_reasons) == 0

        # Construct Performance Context
        performance = PerformanceContext(
            sharpe_ratio=performance_metrics.get("sharpe_ratio", 0.0),
            profit_factor=performance_metrics.get("profit_factor", 0.0),
            max_drawdown=performance_metrics.get("max_drawdown", 0.0),
            win_rate=performance_metrics.get("win_rate", 0.0),
            total_trades=int(performance_metrics.get("total_trades", 0)),
        )

        # Calculate Consensus
        consensus = self._calculate_consensus(explanation)

        return DecisionPacket(
            symbol=symbol,
            direction=explanation.direction,
            consensus=consensus,
            is_executable=is_executable,
            blocking_reasons=blocking_reasons,
            explanation=explanation,
            regime=regime_info,
            macro_risk=macro_risk,
            performance=performance,
        )

    def _calculate_consensus(self, explanation: SignalExplanation) -> str:
        """
        Determine the level of agreement among ensemble models.
        """
        if not explanation.model_attributions:
            return "No Votes"

        votes = [attr.vote for attr in explanation.model_attributions]
        total_models = len(votes)

        direction = explanation.direction
        matching_votes = sum(1 for v in votes if v == direction)

        agreement_pct = matching_votes / total_models

        if agreement_pct >= 1.0:
            return "Unanimous"
        if agreement_pct >= 0.66:
            return "Strong Majority"
        if agreement_pct >= 0.5:
            return "Mixed Confluence"
        return "Divided/Weak"

    def format_for_operator(self, packet: DecisionPacket, console: Any | None = None) -> str:
        """
        Generate a human-readable, high-fidelity terminal dashboard.
        Aggregates all dimensions of the decision into a single visual summary.
        """
        try:
            from rich import box
            from rich.console import Console, Group
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            # 1. Header with Go/No-Go status
            status_color = "green" if packet.is_executable else "red"
            status_text = "EXECUTE" if packet.is_executable else "BLOCKED"

            dir_color = "green" if packet.direction == SignalDirection.BUY else "red" if packet.direction == SignalDirection.SELL else "yellow"

            header_content = Text()
            header_content.append(f"SYMBOL: {packet.symbol}  ", style="bold")
            header_content.append(f"DIRECTION: {packet.direction.name}\n", style=f"bold {dir_color}")
            header_content.append("STATUS: ", style="bold")
            header_content.append(status_text, style=f"bold {status_color}")
            header_content.append("  |  CONSENSUS: ", style="bold")
            header_content.append(packet.consensus.upper(), style="bold cyan")

            if packet.blocking_reasons:
                header_content.append("\n\nBLOCKING REASONS:\n", style="bold red")
                for reason in packet.blocking_reasons:
                    header_content.append(f" • {reason}\n", style="red")

            header = Panel(
                header_content,
                title="[bold]Institutional Decision Support[/bold]",
                subtitle=packet.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                border_style=status_color,
                box=box.DOUBLE,
            )

            # 2. Market and Performance Overview (Two-column table)
            overview_table = Table.grid(expand=True)
            overview_table.add_column(ratio=1)
            overview_table.add_column(ratio=1)

            # Left Column: Regime
            regime_content = (
                f"Label: [bold cyan]{packet.regime.label.value.upper()}[/bold cyan]\n"
                f"Confidence: [bold]{packet.regime.confidence:.1%}[/bold]\n"
                f"Volatility: [bold]{packet.regime.volatility_index:.2f}[/bold]\n"
                f"Transition: {packet.regime.transition_score:.2f}"
            )
            regime_panel = Panel(regime_content, title="Market Regime", border_style="cyan")

            # Right Column: Performance
            perf_content = (
                f"Sharpe: [bold]{packet.performance.sharpe_ratio:.2f}[/bold]\n"
                f"Profit Factor: [bold]{packet.performance.profit_factor:.2f}[/bold]\n"
                f"Win Rate: [bold]{packet.performance.win_rate:.1%}[/bold]\n"
                f"Total Trades: {packet.performance.total_trades}"
            )
            perf_panel = Panel(perf_content, title="Recent Performance", border_style="magenta")

            overview_table.add_row(regime_panel, perf_panel)

            # 3. Macro Risk
            macro_color = "green" if not packet.macro_risk.active_events else "yellow"
            if packet.macro_risk.is_blocked:
                macro_color = "red"

            macro_content = Text()
            if not packet.macro_risk.active_events:
                macro_content.append("No active macro events identified.", style="green")
            else:
                macro_content.append(f"Active Events: {len(packet.macro_risk.active_events)}\n", style="bold")
                for event in packet.macro_risk.active_events:
                    impact_color = "red" if event.impact >= 3 else "yellow"
                    macro_content.append(f" • {event.name} ", style="white")
                    macro_content.append(f"[{event.impact}]", style=impact_color)
                    macro_content.append(f" at {event.timestamp.strftime('%H:%M')}\n")

            if packet.macro_risk.reason:
                macro_content.append(f"\nInsight: {packet.macro_risk.reason}", style="italic")

            macro_panel = Panel(macro_content, title="Macro Intelligence", border_style=macro_color)

            # 4. Attribution Summary (Text)
            attribution_summary = Panel(
                Text(packet.explanation.human_readable_summary),
                title="Signal Attribution Summary",
                border_style="yellow",
            )

            # Assemble everything into a single group for output
            dashboard = Group(
                header,
                overview_table,
                macro_panel,
                attribution_summary,
                Text("\n[bold]DETAILED ATTRIBUTION BREAKDOWN[/bold]\n"),
                self.explainer.get_renderable(packet.explanation)
            )

            # Print to console if provided
            if console:
                console.print(dashboard)

            # Return string representation
            temp_console = Console(force_terminal=True, width=100)
            with temp_console.capture() as capture:
                temp_console.print(dashboard)
            return capture.get()

        except ImportError:
            # Fallback to plain text
            res = f"=== DECISION PACKET: {packet.symbol} ===\n"
            res += f"STATUS: {'EXECUTE' if packet.is_executable else 'BLOCKED'}\n"
            if packet.blocking_reasons:
                res += "REASONS:\n"
                for r in packet.blocking_reasons:
                    res += f" - {r}\n"

            res += f"\nREGIME: {packet.regime.label.value} (Conf: {packet.regime.confidence:.1%})\n"
            res += f"PERFORMANCE: Sharpe {packet.performance.sharpe_ratio:.2f}, PF {packet.performance.profit_factor:.2f}\n"
            res += f"MACRO: {'Blocked' if packet.macro_risk.is_blocked else 'OK'} ({packet.macro_risk.reason})\n"

            return res
