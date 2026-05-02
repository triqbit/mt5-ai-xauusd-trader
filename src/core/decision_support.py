"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Operator-facing decision support system for institutional oversight.
Generates structured decision packets before execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from src.analytics.journal_mining import SessionAnalysis
from src.core.constants import SignalDirection
from src.core.explainability import SignalExplanation
from src.trading.capital_allocator import AllocationResult

logger = logging.getLogger(__name__)


class DecisionPacket(BaseModel):
    """
    Structured packet for institutional operator review.
    Aggregates explainability, risk, allocation, and historical context.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    direction: SignalDirection
    confidence: float

    # Core Components
    explanation: SignalExplanation
    allocation: Optional[AllocationResult] = None
    recent_performance: List[SessionAnalysis] = Field(default_factory=list)

    # State flags
    is_blocked: bool
    block_reasons: List[str] = Field(default_factory=list)

    # Summaries
    operator_summary: str = Field(..., description="High-level human-readable decision summary")

    model_config = {"use_enum_values": False}


class DecisionSupport:
    """
    Orchestrator for generating operator-facing decision packets.
    """

    def generate_packet(
        self,
        explanation: SignalExplanation,
        allocation: Optional[AllocationResult] = None,
        recent_performance: Optional[List[SessionAnalysis]] = None,
    ) -> DecisionPacket:
        """
        Builds a comprehensive decision packet from system components.
        """
        block_reasons = []
        if not explanation.execution_summary.passed:
            block_reasons.append(f"Execution: {explanation.execution_summary.summary}")

        if not explanation.risk_assessment.passed:
            block_reasons.extend(explanation.risk_assessment.rejection_reasons)

        if allocation and not allocation.is_allowed:
            block_reasons.append(f"Allocation: {allocation.rejection_reason}")

        is_blocked = len(block_reasons) > 0

        # Build operator summary
        status_str = "BLOCKED" if is_blocked else "APPROVED"
        dir_str = explanation.direction.name
        summary = f"Decision: {status_str} | {dir_str} {explanation.symbol} | Conf: {explanation.total_confidence:.1%}\n"
        summary += f"Regime: {explanation.regime_context.regime_name} ({explanation.regime_context.volatility_state})\n"

        if is_blocked:
            summary += f"REASONS: {'; '.join(block_reasons)}"
        else:
            if allocation:
                summary += f"Allocated: {allocation.allocated_risk_pct:.2%} risk (${allocation.allocated_amount:,.2f})"
            else:
                summary += "Risk: PASS (No allocation data)"

        return DecisionPacket(
            symbol=explanation.symbol,
            direction=explanation.direction,
            confidence=explanation.total_confidence,
            explanation=explanation,
            allocation=allocation,
            recent_performance=recent_performance or [],
            is_blocked=is_blocked,
            block_reasons=block_reasons,
            operator_summary=summary
        )

    def format_for_operator(self, packet: DecisionPacket) -> str:
        """
        Formats the decision packet for high-impact terminal display.
        """
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console(force_terminal=True)

            # Status styling
            color = "red" if packet.is_blocked else ("green" if packet.direction == SignalDirection.BUY else "blue")
            status_title = "🛑 TRADE BLOCKED" if packet.is_blocked else "✅ TRADE APPROVED"

            header_panel = Panel(
                f"[bold {color}]{packet.direction.name}[/bold {color}] {packet.symbol}\n"
                f"Confidence: [bold]{packet.confidence:.1%}[/bold]\n"
                f"Market Regime: [cyan]{packet.explanation.regime_context.regime_name}[/cyan]\n\n"
                f"{packet.operator_summary}",
                title=f"[bold]{status_title}[/bold]",
                box=box.DOUBLE_EDGE,
                border_style=color
            )

            # Performance Table
            perf_table = Table(title="Recent Session Performance", box=box.SIMPLE)
            perf_table.add_column("Session")
            perf_table.add_column("Win Rate", justify="right")
            perf_table.add_column("PF", justify="right")
            perf_table.add_column("Status", justify="center")

            for sess in packet.recent_performance:
                status = "[red]OVERTRADING[/red]" if sess.is_overtrading else "[green]NORMAL[/green]"
                perf_table.add_row(
                    sess.session_name,
                    f"{sess.win_rate:.1%}",
                    f"{sess.profit_factor:.2f}",
                    status
                )

            # Capture all output
            with console.capture() as capture:
                console.print(header_panel)
                if packet.recent_performance:
                    console.print(perf_table)

            return capture.get()

        except ImportError:
            # Plain text fallback
            status = "BLOCKED" if packet.is_blocked else "APPROVED"
            output = f"=== DECISION PACKET [{status}] ===\n"
            output += f"{packet.operator_summary}\n"
            if packet.recent_performance:
                output += "\nRecent Performance:\n"
                for sess in packet.recent_performance:
                    ot = " [OVERTRADING]" if sess.is_overtrading else ""
                    output += f"  - {sess.session_name}: WR={sess.win_rate:.1%}, PF={sess.profit_factor:.2f}{ot}\n"
            return output
