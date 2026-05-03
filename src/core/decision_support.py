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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.explainability import SignalExplanation
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

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = Field(..., description="Target trading symbol")
    is_executable: bool = Field(False, description="Final decision on whether the trade should proceed")
    blocking_reasons: List[str] = Field(default_factory=list, description="List of reasons if the trade is blocked")

    # Components
    explanation: SignalExplanation = Field(..., description="ML signal attribution and explainability")
    regime: RegimeInfo = Field(..., description="Current market regime context")
    macro_risk: RiskStatus = Field(..., description="Macroeconomic event risk status")
    performance: PerformanceContext = Field(..., description="Recent performance context")

    class Config:
        arbitrary_types_allowed = True


class DecisionSupportSystem:
    """
    Orchestrator for generating decision packets.
    Integrates multiple system components to provide a unified 'Go/No-Go' view.
    """

    def __init__(self) -> None:
        pass

    def assemble_packet(
        self,
        symbol: str,
        explanation: SignalExplanation,
        regime_info: RegimeInfo,
        macro_risk: RiskStatus,
        performance_metrics: Dict[str, Any],
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

        return DecisionPacket(
            symbol=symbol,
            is_executable=is_executable,
            blocking_reasons=blocking_reasons,
            explanation=explanation,
            regime=regime_info,
            macro_risk=macro_risk,
            performance=performance,
        )

    def format_for_operator(self, packet: DecisionPacket) -> str:
        """
        Generate a human-readable, high-fidelity terminal dashboard.
        """
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console(force_terminal=True)

            # 1. Header with Go/No-Go status
            status_color = "green" if packet.is_executable else "red"
            status_text = "EXECUTE" if packet.is_executable else "BLOCKED"

            header_content = Text()
            header_content.append(f"SYMBOL: {packet.symbol}\n", style="bold")
            header_content.append(f"STATUS: ", style="bold")
            header_content.append(status_text, style=f"bold {status_color}")

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

            # Capture output
            with console.capture() as capture:
                console.print(header)
                console.print(overview_table)
                console.print(macro_panel)

                # Integration with existing SignalExplainer output for the details
                from src.core.explainability import SignalExplainer
                explainer = SignalExplainer()
                console.print("\n[bold]SIGNAL ATTRIBUTION DETAILS[/bold]")
                console.print(explainer.format_for_terminal(packet.explanation))

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
