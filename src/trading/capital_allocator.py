"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital allocation engine.
Handles multi-strategy budgeting, portfolio heat, and diversification.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StrategyConfig(BaseModel):
    """Configuration for a specific strategy or model family."""
    strategy_id: str
    capital_cap: float = Field(default=0.2, description="Max fraction of total balance for this strategy")
    base_allocation: float = Field(default=0.1, description="Base allocation fraction for a single trade")
    min_allocation: float = Field(default=0.01)
    max_allocation: float = Field(default=0.4)
    priority: int = Field(default=1, ge=1, le=5)


class AllocationRequest(BaseModel):
    """Request for capital allocation for a new trade signal."""
    strategy_id: str
    symbol: str
    current_balance: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    volatility_scale: float = Field(default=1.0, description="1.0 is normal, >1.0 reduces allocation")


class AllocationResult(BaseModel):
    """Result of the allocation request."""
    strategy_id: str
    allocated_amount: float
    allocation_fraction: float
    approved: bool
    reason: Optional[str] = None
    portfolio_heat: float


class CapitalAllocator:
    """
    Manages capital distribution across multiple strategies and symbols.
    Ensures the portfolio remains within risk heat limits and avoids over-concentration.
    """

    def __init__(self, strategies: List[StrategyConfig], max_portfolio_heat: float = 0.5):
        self.strategies = {s.strategy_id: s for s in strategies}
        self.max_portfolio_heat = max_portfolio_heat

        # Track active allocation fractions (0.0 to 1.0)
        self.active_allocations: Dict[str, List[float]] = {s.strategy_id: [] for s in strategies}
        self.symbol_allocations: Dict[str, float] = {}

        # Performance tracking for adaptive budgeting
        self.performance_history: Dict[str, List[float]] = {s.strategy_id: [] for s in strategies}

        logger.info("CapitalAllocator initialized with %d strategies | max_heat=%.2f",
                    len(strategies), max_portfolio_heat)

    def get_allocation(self, request: AllocationRequest) -> AllocationResult:
        """
        Calculate the optimal capital allocation for a signal.
        """
        if request.strategy_id not in self.strategies:
            return self._reject(request, f"Strategy {request.strategy_id} not registered")

        strategy_cfg = self.strategies[request.strategy_id]

        # 1. Check Portfolio Heat
        current_heat = self._calculate_portfolio_heat()
        if current_heat >= self.max_portfolio_heat:
            return self._reject(request, f"Max portfolio heat reached: {current_heat:.2f}", current_heat)

        # 2. Adaptive Budgeting (Performance-based)
        perf_multiplier = self._get_performance_multiplier(request.strategy_id)

        # 3. Calculate Base Allocation
        # Adjust by performance, confidence, and volatility
        target_fraction = (strategy_cfg.base_allocation *
                           perf_multiplier *
                           request.confidence /
                           max(request.volatility_scale, 0.5))

        # Apply min/max bounds for the strategy
        target_fraction = max(strategy_cfg.min_allocation, min(target_fraction, strategy_cfg.max_allocation))

        # 4. Enforce Strategy Capital Cap
        current_strategy_exposure = sum(self.active_allocations[request.strategy_id])
        remaining_strategy_cap = max(0.0, strategy_cfg.capital_cap - current_strategy_exposure)

        target_fraction = min(target_fraction, remaining_strategy_cap)

        # 5. Enforce Portfolio Heat Cap
        remaining_heat = max(0.0, self.max_portfolio_heat - current_heat)
        target_fraction = min(target_fraction, remaining_heat)

        # 6. Diversification Check (Concentration limit per symbol)
        # Limit any single symbol to 50% of max portfolio heat
        symbol_cap = self.max_portfolio_heat * 0.5
        current_symbol_exposure = self.symbol_allocations.get(request.symbol, 0.0)
        remaining_symbol_cap = max(0.0, symbol_cap - current_symbol_exposure)

        target_fraction = min(target_fraction, remaining_symbol_cap)

        if target_fraction < strategy_cfg.min_allocation:
             return self._reject(request, "Allocation below minimum threshold after constraints", current_heat)

        # Final Approval
        allocated_amount = request.current_balance * target_fraction

        # Record the allocation
        self.active_allocations[request.strategy_id].append(target_fraction)
        self.symbol_allocations[request.symbol] = self.symbol_allocations.get(request.symbol, 0.0) + target_fraction

        new_heat = self._calculate_portfolio_heat()

        logger.info("Allocation APPROVED | strategy=%s symbol=%s amount=%.2f (%.1f%%) | heat=%.2f",
                    request.strategy_id, request.symbol, allocated_amount, target_fraction * 100, new_heat)

        return AllocationResult(
            strategy_id=request.strategy_id,
            allocated_amount=allocated_amount,
            allocation_fraction=target_fraction,
            approved=True,
            portfolio_heat=new_heat
        )

    def release_allocation(self, strategy_id: str, symbol: str, fraction: float):
        """Release capital when a trade is closed."""
        if strategy_id in self.active_allocations:
            if fraction in self.active_allocations[strategy_id]:
                self.active_allocations[strategy_id].remove(fraction)
            elif self.active_allocations[strategy_id]:
                # Fallback if exact fraction not found (e.g. rounding)
                self.active_allocations[strategy_id].pop()

        if symbol in self.symbol_allocations:
            self.symbol_allocations[symbol] = max(0.0, self.symbol_allocations[symbol] - fraction)
            if self.symbol_allocations[symbol] == 0:
                del self.symbol_allocations[symbol]

    def update_performance(self, strategy_id: str, pnl: float):
        """Update strategy performance history to influence future budgeting."""
        if strategy_id in self.performance_history:
            self.performance_history[strategy_id].append(pnl)
            # Keep last 50 trades
            if len(self.performance_history[strategy_id]) > 50:
                self.performance_history[strategy_id].pop(0)

    def _calculate_portfolio_heat(self) -> float:
        """Sum of all active allocation fractions."""
        return sum(sum(allocs) for allocs in self.active_allocations.values())

    def _get_performance_multiplier(self, strategy_id: str) -> float:
        """
        Calculate a multiplier based on recent win rate and Sharpe-like metric.
        Returns a value between 0.5 and 1.5.
        """
        history = self.performance_history.get(strategy_id, [])
        if len(history) < 5:
            return 1.0  # Default for new strategies

        history_arr = np.array(history)
        win_rate = np.sum(history_arr > 0) / len(history_arr)

        # Simple performance factor
        if win_rate > 0.6:
            return 1.2
        elif win_rate < 0.4:
            return 0.8

        return 1.0

    def _reject(self, request: AllocationRequest, reason: str, heat: float = 0.0) -> AllocationResult:
        logger.warning("Allocation REJECTED | strategy=%s reason=%s", request.strategy_id, reason)
        return AllocationResult(
            strategy_id=request.strategy_id,
            allocated_amount=0.0,
            allocation_fraction=0.0,
            approved=False,
            reason=reason,
            portfolio_heat=heat or self._calculate_portfolio_heat()
        )
