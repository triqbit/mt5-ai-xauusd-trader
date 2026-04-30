"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management and portfolio heat tracking.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for a specific model family or strategy."""

    name: str
    capital_cap: float  # Max capital in currency units
    base_weight: float  # Initial weight [0.0, 1.0]
    correlation_group: str = "default"
    max_heat: float = 0.02  # Max risk per strategy as fraction of total capital


@dataclass
class AllocationResult:
    """Typed output for capital allocation requests."""

    strategy_id: str
    allocated_amount: float
    approved: bool
    reason: Optional[str] = None


class CapitalAllocator:
    """
    Manages capital distribution across multiple strategies.
    Implements heat tracking, diversification, and adaptive budgeting.
    """

    def __init__(
        self,
        total_capital: float,
        configs: Dict[str, StrategyConfig],
        max_portfolio_heat: float = 0.10,
        max_group_concentration: float = 0.40,
    ):
        self.total_capital = total_capital
        self.configs = configs
        self.max_portfolio_heat = max_portfolio_heat
        self.max_group_concentration = max_group_concentration

        # Internal state
        self.strategy_heat: Dict[str, float] = {name: 0.0 for name in configs}
        self.strategy_capital_used: Dict[str, float] = {name: 0.0 for name in configs}
        self.performance_multipliers: Dict[str, float] = {name: 1.0 for name in configs}

    def get_allocation(
        self, strategy_id: str, requested_capital: float, risk_amount: float
    ) -> AllocationResult:
        """
        Requests capital for a new trade.

        Args:
            strategy_id: ID of the requesting strategy.
            requested_capital: Amount of capital needed for the position size.
            risk_amount: Amount of capital at risk (entry - stop loss) * size.
        """
        if strategy_id not in self.configs:
            return AllocationResult(
                strategy_id, 0.0, False, f"Unknown strategy: {strategy_id}"
            )

        cfg = self.configs[strategy_id]

        # 1. Adaptive Budgeting (apply performance multiplier before limits)
        multiplier = self.performance_multipliers[strategy_id]
        final_capital = requested_capital * multiplier
        final_risk = risk_amount * multiplier

        # 2. Check Strategy Capital Cap
        current_usage = self.strategy_capital_used[strategy_id]
        if current_usage + final_capital > cfg.capital_cap:
            available_cap = cfg.capital_cap - current_usage
            if available_cap <= 0:
                return AllocationResult(
                    strategy_id,
                    0.0,
                    False,
                    f"Strategy cap reached: {current_usage:.2f}/{cfg.capital_cap:.2f}",
                )
            ratio = available_cap / final_capital
            final_capital = available_cap
            final_risk *= ratio

        # 3. Check Strategy Heat (Risk)
        current_strategy_heat = self.strategy_heat[strategy_id]
        strategy_risk_pct = (current_strategy_heat + final_risk) / self.total_capital
        if strategy_risk_pct > cfg.max_heat:
            allowed_additional_risk = (cfg.max_heat * self.total_capital) - current_strategy_heat
            if allowed_additional_risk <= 0:
                return AllocationResult(
                    strategy_id,
                    0.0,
                    False,
                    f"Strategy heat limit hit: {strategy_risk_pct:.2%} > {cfg.max_heat:.2%}",
                )
            ratio = allowed_additional_risk / final_risk
            final_risk = allowed_additional_risk
            final_capital *= ratio

        # 4. Check Portfolio Heat
        total_heat = sum(self.strategy_heat.values())
        portfolio_heat_pct = (total_heat + final_risk) / self.total_capital
        if portfolio_heat_pct > self.max_portfolio_heat:
            allowed_portfolio_risk = (
                self.max_portfolio_heat * self.total_capital
            ) - total_heat
            if allowed_portfolio_risk <= 0:
                return AllocationResult(
                    strategy_id,
                    0.0,
                    False,
                    f"Portfolio heat limit hit: {portfolio_heat_pct:.2%} > {self.max_portfolio_heat:.2%}",
                )
            ratio = allowed_portfolio_risk / final_risk
            final_risk = allowed_portfolio_risk
            final_capital *= ratio

        # 5. Check Concentration (Safety limit)
        group_heat = self._get_group_heat(cfg.correlation_group)
        current_total_heat = sum(self.strategy_heat.values())
        # The portfolio scaling above MIGHT have reduced final_risk.
        # Check concentration with the scaled final_risk.
        theoretical_total_heat = current_total_heat + final_risk
        if (
            theoretical_total_heat > 0.05 * self.total_capital
        ):
            group_concentration = (group_heat + final_risk) / theoretical_total_heat
            if group_concentration > self.max_group_concentration:
                # x is the allowed_additional_risk for this strategy
                # (group_heat + x) / (current_total_heat + x) = max_conc
                # group_heat + x = max_conc * current_total_heat + max_conc * x
                # x * (1 - max_conc) = max_conc * current_total_heat - group_heat
                # x = (max_conc * current_total_heat - group_heat) / (1 - max_conc)
                allowed_x = (
                    self.max_group_concentration * current_total_heat - group_heat
                ) / (1 - self.max_group_concentration)

                # Ensure we don't increase risk if we are already over concentration but below other limits
                allowed_x = max(0.0, min(allowed_x, final_risk))

                if allowed_x <= 0:
                    return AllocationResult(
                        strategy_id,
                        0.0,
                        False,
                        f"Group concentration limit hit: {group_concentration:.2%} > {self.max_group_concentration:.2%}",
                    )
                ratio = allowed_x / final_risk
                final_risk = allowed_x
                final_capital *= ratio

        return AllocationResult(strategy_id, final_capital, True)

    def allocate(self, strategy_id: str, capital_amount: float, risk_amount: float):
        """Confirm and record an allocation."""
        if strategy_id in self.strategy_capital_used:
            self.strategy_capital_used[strategy_id] += capital_amount
            self.strategy_heat[strategy_id] += risk_amount
            logger.info(
                "Allocated %.2f to %s | Risk: %.2f | Total Heat: %.2f%%",
                capital_amount,
                strategy_id,
                risk_amount,
                (sum(self.strategy_heat.values()) / self.total_capital) * 100,
            )

    def release(self, strategy_id: str, capital_amount: float, risk_amount: float):
        """Release capital and heat after a trade closes."""
        if strategy_id in self.strategy_capital_used:
            self.strategy_capital_used[strategy_id] = max(
                0.0, self.strategy_capital_used[strategy_id] - capital_amount
            )
            self.strategy_heat[strategy_id] = max(
                0.0, self.strategy_heat[strategy_id] - risk_amount
            )

    def update_performance(self, strategy_id: str, pnl: float):
        """Adjust performance multipliers based on realized PnL."""
        if strategy_id in self.performance_multipliers:
            # Simple adjustment: increase on profit, decrease more on loss
            if pnl > 0:
                self.performance_multipliers[strategy_id] = min(
                    2.0, self.performance_multipliers[strategy_id] + 0.05
                )
            elif pnl < 0:
                self.performance_multipliers[strategy_id] = max(
                    0.5, self.performance_multipliers[strategy_id] - 0.10
                )

    def update_total_capital(self, new_total: float):
        """Update total capital (e.g. after deposits or aggregate PnL)."""
        self.total_capital = new_total

    def _get_group_heat(self, group: str) -> float:
        return sum(
            heat
            for name, heat in self.strategy_heat.items()
            if self.configs[name].correlation_group == group
        )
