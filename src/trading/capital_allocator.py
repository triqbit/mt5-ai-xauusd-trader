"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management and adaptive budgeting.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class StrategyAllocation(BaseModel):
    """Current allocation state for a specific strategy/model family."""
    model_config = ConfigDict(frozen=False)

    strategy_id: str
    capital_cap_pct: float = Field(default=0.5, description="Maximum allocation as percentage of equity")
    capital_cap: float = Field(..., description="Maximum USD capital allowed for this strategy")
    current_used: float = 0.0
    performance_multiplier: float = 1.0
    rolling_win_rate: float = 0.5
    trades_count: int = 0


class AllocationRequest(BaseModel):
    """Input for requesting capital for a new trade signal."""
    strategy_id: str
    symbol: str
    requested_risk: float = Field(..., description="Amount in USD to risk on this trade")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class AllocationResult(BaseModel):
    """Result of the capital allocation request."""
    approved: bool
    allocated_risk: float
    multiplier: float
    reason: Optional[str] = None


class CapitalAllocator:
    """
    Manages institutional-grade capital budgeting across multiple strategies.
    Enforces global portfolio heat limits and per-strategy capital caps.
    """

    def __init__(
        self,
        total_equity: float,
        global_max_heat: float = 0.20,  # 20% of equity at risk
        symbol_concentration_limit: float = 0.50,  # Max 50% of allowed total heat per symbol
    ) -> None:
        self.equity = total_equity
        self.max_heat_pct = global_max_heat
        self.symbol_limit_pct = symbol_concentration_limit
        self.strategies: Dict[str, StrategyAllocation] = {}
        self.symbol_heat: Dict[str, float] = {}  # symbol -> USD risk
        logger.info(
            "CapitalAllocator initialised | equity=%.2f heat_limit=%.1f%% symbol_limit=%.1f%%",
            total_equity, global_max_heat * 100, symbol_concentration_limit * 100
        )

    def register_strategy(
        self, strategy_id: str, capital_cap_pct: float = 0.5
    ) -> None:
        """Register a new strategy with a specific capital cap as percentage of equity."""
        cap = self.equity * capital_cap_pct
        self.strategies[strategy_id] = StrategyAllocation(
            strategy_id=strategy_id,
            capital_cap_pct=capital_cap_pct,
            capital_cap=cap
        )
        logger.info("Strategy %s registered | cap=%.2f", strategy_id, cap)

    def update_equity(self, current_equity: float) -> None:
        """Update internal equity reference and scale absolute caps."""
        self.equity = current_equity
        for strat in self.strategies.values():
            strat.capital_cap = self.equity * strat.capital_cap_pct
        logger.debug("Updated equity and strategy caps | equity=%.2f", current_equity)

    def update_performance(self, strategy_id: str, win_rate: float) -> None:
        """
        Update strategy performance multiplier based on rolling win rate.
        Implements adaptive budgeting logic.
        """
        if strategy_id in self.strategies:
            strat = self.strategies[strategy_id]
            strat.rolling_win_rate = win_rate
            # Institutional logic: scale by performance relative to 50% baseline
            # Clipped between 0.5x and 1.5x to prevent extreme swings
            multiplier = max(0.5, min(1.5, win_rate / 0.5))
            strat.performance_multiplier = multiplier
            logger.info(
                "Strategy %s performance updated | WR=%.2f multiplier=%.2f",
                strategy_id, win_rate, multiplier
            )

    def request_allocation(self, request: AllocationRequest) -> AllocationResult:
        """
        Evaluates an allocation request against portfolio heat and concentration limits.
        """
        if request.strategy_id not in self.strategies:
            return AllocationResult(
                approved=False,
                allocated_risk=0.0,
                multiplier=0.0,
                reason=f"Strategy {request.strategy_id} not registered"
            )

        strat = self.strategies[request.strategy_id]

        # 0. Calculate final allocated risk based on performance and confidence first
        # Multiplier = Performance-based * Confidence-based
        final_multiplier = strat.performance_multiplier * request.confidence
        final_risk = request.requested_risk * final_multiplier

        # 1. Global Portfolio Heat Check
        total_current_heat = sum(self.symbol_heat.values())
        max_allowed_heat = self.equity * self.max_heat_pct

        if total_current_heat + final_risk > max_allowed_heat:
            return AllocationResult(
                approved=False,
                allocated_risk=0.0,
                multiplier=0.0,
                reason=f"Global portfolio heat limit exceeded (max: {max_allowed_heat:.2f})"
            )

        # 2. Symbol Concentration Check (50% of total allowed heat)
        symbol_current_heat = self.symbol_heat.get(request.symbol, 0.0)
        max_symbol_heat = max_allowed_heat * self.symbol_limit_pct

        if symbol_current_heat + final_risk > max_symbol_heat:
            return AllocationResult(
                approved=False,
                allocated_risk=0.0,
                multiplier=0.0,
                reason=f"Symbol {request.symbol} concentration limit exceeded"
            )

        # 3. Strategy Cap Check
        if strat.current_used + final_risk > strat.capital_cap:
            return AllocationResult(
                approved=False,
                allocated_risk=0.0,
                multiplier=0.0,
                reason=f"Strategy {request.strategy_id} capital cap reached"
            )

        return AllocationResult(
            approved=True,
            allocated_risk=final_risk,
            multiplier=final_multiplier
        )

    def commit_allocation(self, strategy_id: str, symbol: str, risk_usd: float) -> None:
        """Record the actual risk committed to a trade."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].current_used += risk_usd
            self.strategies[strategy_id].trades_count += 1

        self.symbol_heat[symbol] = self.symbol_heat.get(symbol, 0.0) + risk_usd
        logger.debug("Committed allocation | strategy=%s symbol=%s risk=%.2f", strategy_id, symbol, risk_usd)

    def release_allocation(self, strategy_id: str, symbol: str, risk_usd: float) -> None:
        """Release risk from tracking once a trade is closed."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].current_used = max(0.0, self.strategies[strategy_id].current_used - risk_usd)

        self.symbol_heat[symbol] = max(0.0, self.symbol_heat.get(symbol, 0.0) - risk_usd)
        logger.debug("Released allocation | strategy=%s symbol=%s risk=%.2f", strategy_id, symbol, risk_usd)

    def get_portfolio_state(self) -> Dict:
        """Return summary of current capital distribution."""
        return {
            "total_equity": self.equity,
            "total_heat_usd": sum(self.symbol_heat.values()),
            "total_heat_pct": (sum(self.symbol_heat.values()) / self.equity) if self.equity > 0 else 0,
            "strategy_states": {k: v.model_dump() for k, v in self.strategies.items()},
            "symbol_concentration": self.symbol_heat.copy()
        }
