"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Adaptive capital allocation system for multi-strategy portfolios.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Configuration for a specific strategy's allocation limits."""
    name: str
    capital_cap: float
    max_heat: float  # max percentage of capital at risk
    family: str      # e.g., 'trend', 'mean_reversion'

@dataclass
class AllocationResult:
    """Result of an allocation request."""
    strategy_name: str
    allocated_amount: float
    is_approved: bool
    reason: str = ""

class CapitalAllocator:
    """
    Orchestrates capital distribution across multiple strategies.
    Implements institutional constraints on concentration and portfolio heat.
    """

    def __init__(self, total_capital: float, max_portfolio_heat: float = 0.20) -> None:
        self.total_capital = total_capital
        self.max_portfolio_heat = max_portfolio_heat
        self.strategies: Dict[str, StrategyConfig] = {}
        self.performance_multipliers: Dict[str, float] = {}
        self.active_allocations: Dict[str, float] = {}

    def add_strategy(self, config: StrategyConfig) -> None:
        """Register a new strategy for capital allocation."""
        self.strategies[config.name] = config
        self.performance_multipliers[config.name] = 1.0
        self.active_allocations[config.name] = 0.0
        logger.info("Strategy registered: %s (family: %s)", config.name, config.family)

    def request_allocation(self, strategy_name: str, requested_amount: float) -> AllocationResult:
        """Request capital allocation for a specific strategy."""
        if strategy_name not in self.strategies:
            return AllocationResult(strategy_name, 0.0, False, "Strategy not registered")

        config = self.strategies[strategy_name]
        multiplier = self.performance_multipliers[strategy_name]

        # 1. Strategy Cap
        limit = config.capital_cap * multiplier
        approved_amount = min(requested_amount, limit)

        # 2. Total Portfolio Heat
        current_total_heat = sum(self.active_allocations.values()) / self.total_capital
        if current_total_heat >= self.max_portfolio_heat:
            return AllocationResult(strategy_name, 0.0, False, "Max portfolio heat reached")

        # 3. Symbol/Family Concentration (Simplified)
        family_heat = sum(self.active_allocations[s] for s in self.active_allocations
                         if self.strategies[s].family == config.family) / self.total_capital
        if family_heat >= 0.10: # 10% family limit
            return AllocationResult(strategy_name, 0.0, False, "Family concentration limit reached")

        self.active_allocations[strategy_name] += approved_amount
        return AllocationResult(strategy_name, approved_amount, True)

    def record_pnl(self, strategy_name: str, pnl: float) -> None:
        """Adjust multipliers based on realized performance."""
        if strategy_name in self.performance_multipliers:
            # Reward winning strategies, scale down losers
            if pnl > 0:
                self.performance_multipliers[strategy_name] *= 1.05
            else:
                self.performance_multipliers[strategy_name] *= 0.95

            # Keep multipliers within sane bounds
            self.performance_multipliers[strategy_name] = max(0.5, min(2.0, self.performance_multipliers[strategy_name]))
