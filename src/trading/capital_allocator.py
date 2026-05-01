"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StrategyConfig(BaseModel):
    """Configuration for a single trading strategy or model family."""

    strategy_id: str
    symbol: str
    model_family: str
    capital_cap: float = Field(..., gt=0, description="Maximum capital this strategy can use.")
    performance_multiplier: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Multiplier based on recent performance."
    )


class AllocationResult(BaseModel):
    """Typed result of a capital allocation request."""

    strategy_id: str
    allocated_amount: float
    risk_pct: float
    is_allowed: bool
    rejection_reason: Optional[str] = None


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
    ):
        self.total_budget = total_budget
        self.max_symbol_risk = max_symbol_risk
        self.max_family_risk = max_family_risk
        self.max_total_heat = max_total_heat

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

    def request_allocation(self, strategy_id: str, risk_pct: float) -> AllocationResult:
        """
        Evaluate if a strategy can be allocated the requested risk.
        Applies adaptive budget allocation, caps, and concentration limits.
        """
        if strategy_id not in self.strategies:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                risk_pct=0.0,
                is_allowed=False,
                rejection_reason="Strategy not registered",
            )

        config = self.strategies[strategy_id]

        # 1. Apply Performance Multiplier (Adaptive Allocation)
        adjusted_risk_pct = risk_pct * config.performance_multiplier
        requested_amount = self.total_budget * adjusted_risk_pct

        # 2. Check Strategy-Level Capital Cap
        if requested_amount > config.capital_cap:
            logger.debug("Strategy %s requested amount above cap", strategy_id)
            requested_amount = config.capital_cap
            adjusted_risk_pct = requested_amount / self.total_budget

        # 3. Check Total Portfolio Heat
        current_total_heat = self.get_total_heat()
        if current_total_heat + adjusted_risk_pct > self.max_total_heat:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                risk_pct=0.0,
                is_allowed=False,
                rejection_reason=f"Total heat limit reached: {current_total_heat:.2f}",
            )

        # 4. Check Symbol Concentration
        symbol_heat = self.get_symbol_heat(config.symbol)
        if symbol_heat + adjusted_risk_pct > self.max_symbol_risk:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                risk_pct=0.0,
                is_allowed=False,
                rejection_reason=f"Symbol concentration limit reached for {config.symbol}",
            )

        # 5. Check Model Family Concentration
        family_heat = self.get_family_heat(config.model_family)
        if family_heat + adjusted_risk_pct > self.max_family_risk:
            return AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                risk_pct=0.0,
                is_allowed=False,
                rejection_reason=f"Family concentration limit reached for {config.model_family}",
            )

        return AllocationResult(
            strategy_id=strategy_id,
            allocated_amount=requested_amount,
            risk_pct=adjusted_risk_pct,
            is_allowed=True,
        )


__all__ = ["StrategyConfig", "AllocationResult", "CapitalAllocator"]
