"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RejectionCode(str, Enum):
    """Programmatic rejection codes for allocation failures."""

    STRATEGY_NOT_FOUND = "STRATEGY_NOT_FOUND"
    TOTAL_HEAT_LIMIT = "TOTAL_HEAT_LIMIT"
    SYMBOL_CONCENTRATION_LIMIT = "SYMBOL_CONCENTRATION_LIMIT"
    FAMILY_CONCENTRATION_LIMIT = "FAMILY_CONCENTRATION_LIMIT"
    CAPITAL_CAP_REACHED = "CAPITAL_CAP_REACHED"


class StrategyConfig(BaseModel):
    """Configuration for a single trading strategy or model family."""

    strategy_id: str
    symbol: str
    model_family: str
    capital_cap: float = Field(..., gt=0, description="Maximum capital this strategy can use.")
    performance_multiplier: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Multiplier based on recent performance."
    )
    historical_pnl: float = Field(default=0.0, description="Accumulated PnL for this strategy.")


class AllocationResult(BaseModel):
    """Typed result of a capital allocation request."""

    strategy_id: str
    allocated_amount: float
    allocated_risk_pct: float
    requested_risk_pct: float
    is_allowed: bool
    rejection_reason: Optional[str] = None
    rejection_code: Optional[RejectionCode] = None


class CapitalAllocator:
    """
    Institutional-grade capital management system.
    Handles allocation across multiple strategies with risk concentration limits
    and portfolio heat tracking.
    """

    def __init__(
        self,
        total_budget: float,
        max_symbol_risk: float = 0.4,  # Max 40% of budget per symbol
        max_family_risk: float = 0.4,  # Max 40% of budget per model family
        max_total_heat: float = 0.7,  # Max 70% of budget committed at once
        performance_step: float = 0.05,  # Adjustment step for performance multiplier
        decay_rate: float = 0.001,  # Rate at which multiplier returns to 1.0
    ):
        self.total_budget = total_budget
        self.max_symbol_risk = max_symbol_risk
        self.max_family_risk = max_family_risk
        self.max_total_heat = max_total_heat
        self.performance_step = performance_step
        self.decay_rate = decay_rate

        self.strategies: Dict[str, StrategyConfig] = {}
        self.current_allocations: Dict[str, float] = {}  # strategy_id -> current allocated amount

    def add_strategy(self, config: StrategyConfig) -> None:
        """Register a new strategy for capital allocation."""
        self.strategies[config.strategy_id] = config
        if config.strategy_id not in self.current_allocations:
            self.current_allocations[config.strategy_id] = 0.0
        logger.info("Strategy %s registered for symbol %s", config.strategy_id, config.symbol)

    def update_allocation(self, strategy_id: str, amount: float) -> None:
        """Update the currently used capital for a strategy."""
        if strategy_id in self.strategies:
            self.current_allocations[strategy_id] = max(0.0, amount)

    def update_strategy_performance(self, strategy_id: str, pnl: float) -> None:
        """
        Adjust performance multiplier based on trade outcome.
        Positive PnL increases multiplier, negative PnL decreases it.
        """
        if strategy_id not in self.strategies:
            return

        config = self.strategies[strategy_id]
        config.historical_pnl += pnl

        if pnl > 0:
            config.performance_multiplier = min(
                2.0, config.performance_multiplier + self.performance_step
            )
        elif pnl < 0:
            config.performance_multiplier = max(
                0.0, config.performance_multiplier - self.performance_step
            )

        logger.debug(
            "Strategy %s multiplier updated to %.2f | PnL: %.2f",
            strategy_id,
            config.performance_multiplier,
            pnl,
        )

    def decay_performance_multipliers(self) -> None:
        """
        Slowly return performance multipliers toward the baseline of 1.0.
        Called periodically (e.g., daily) to normalize risk.
        """
        for config in self.strategies.values():
            if config.performance_multiplier > 1.0:
                config.performance_multiplier = max(
                    1.0, config.performance_multiplier - self.decay_rate
                )
            elif config.performance_multiplier < 1.0:
                config.performance_multiplier = min(
                    1.0, config.performance_multiplier + self.decay_rate
                )

    def get_total_heat(self) -> float:
        """Calculate current portfolio heat (total committed capital ratio)."""
        total_allocated = sum(self.current_allocations.values())
        return total_allocated / self.total_budget if self.total_budget > 0 else 1.0

    def get_symbol_heat(self, symbol: str) -> float:
        """Calculate total heat for a specific symbol."""
        symbol_total = sum(
            amount
            for sid, amount in self.current_allocations.items()
            if self.strategies[sid].symbol == symbol
        )
        return symbol_total / self.total_budget if self.total_budget > 0 else 1.0

    def get_family_heat(self, family: str) -> float:
        """Calculate total heat for a specific model family."""
        family_total = sum(
            amount
            for sid, amount in self.current_allocations.items()
            if self.strategies[sid].model_family == family
        )
        return family_total / self.total_budget if self.total_budget > 0 else 1.0

    def get_strategy_utilization(self, strategy_id: str) -> float:
        """Calculate how much of the strategy's capital cap is currently used."""
        if strategy_id not in self.strategies:
            return 0.0
        allocated = self.current_allocations.get(strategy_id, 0.0)
        cap = self.strategies[strategy_id].capital_cap
        return allocated / cap if cap > 0 else 1.0

    def to_report_section(self, rejection_history: Optional[Dict[str, int]] = None) -> Any:
        """Convert current state to AllocationSection for ResearchReporter."""
        from src.research.reporting import AllocationEntry, AllocationSection

        allocations = []
        for sid, config in self.strategies.items():
            current_amt = self.current_allocations.get(sid, 0.0)
            allocations.append(
                AllocationEntry(
                    name=sid,
                    amount=f"${current_amt:,.2f}",
                    heat_pct=float((current_amt / self.total_budget) * 100)
                    if self.total_budget > 0
                    else 0.0,
                    multiplier=config.performance_multiplier,
                )
            )

        return AllocationSection(
            total_heat_pct=float(self.get_total_heat() * 100),
            allocations=allocations,
            rejection_summary=rejection_history or {},
        )

    def request_allocation(self, strategy_id: str, risk_pct: float) -> AllocationResult:
        """
        Evaluate if a strategy can be allocated the requested risk.
        Applies adaptive budget allocation, caps, and concentration limits.
        """
        if strategy_id not in self.strategies:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason="Strategy not registered",
                rejection_code=RejectionCode.STRATEGY_NOT_FOUND,
            )

        config = self.strategies[strategy_id]

        # 1. Apply Performance Multiplier (Adaptive Allocation)
        # This scales the requested risk based on historical performance.
        target_risk_pct = risk_pct * config.performance_multiplier
        target_amount = self.total_budget * target_risk_pct

        # 2. Check Strategy-Level Capital Cap
        # Ensure we don't exceed the absolute capital limit for this strategy.
        if target_amount > config.capital_cap:
            logger.debug(
                "Strategy %s target amount %.2f exceeds cap %.2f",
                strategy_id,
                target_amount,
                config.capital_cap,
            )
            target_amount = config.capital_cap
            target_risk_pct = target_amount / self.total_budget

            if target_amount <= 0:
                return AllocationResult(
                    strategy_id=strategy_id,
                    allocated_amount=0.0,
                    allocated_risk_pct=0.0,
                    requested_risk_pct=risk_pct,
                    is_allowed=False,
                    rejection_reason="Strategy capital cap reached or zero",
                    rejection_code=RejectionCode.CAPITAL_CAP_REACHED,
                )

        # 3. Check Total Portfolio Heat
        # Use the final adjusted_risk_pct (scaled and capped) for safety checks.
        current_total_heat = self.get_total_heat()
        if current_total_heat + target_risk_pct > self.max_total_heat:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason=f"Total heat limit reached: {current_total_heat:.2f}",
                rejection_code=RejectionCode.TOTAL_HEAT_LIMIT,
            )

        # 4. Check Symbol Concentration
        symbol_heat = self.get_symbol_heat(config.symbol)
        if symbol_heat + target_risk_pct > self.max_symbol_risk:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason=f"Symbol concentration limit reached for {config.symbol}",
                rejection_code=RejectionCode.SYMBOL_CONCENTRATION_LIMIT,
            )

        # 5. Check Model Family Concentration
        family_heat = self.get_family_heat(config.model_family)
        if family_heat + target_risk_pct > self.max_family_risk:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason=f"Family concentration limit reached for {config.model_family}",
                rejection_code=RejectionCode.FAMILY_CONCENTRATION_LIMIT,
            )

        return AllocationResult(
            strategy_id=strategy_id,
            allocated_amount=target_amount,
            allocated_risk_pct=target_risk_pct,
            requested_risk_pct=risk_pct,
            is_allowed=True,
        )


__all__ = ["AllocationResult", "CapitalAllocator", "RejectionCode", "StrategyConfig"]
