"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management engine.
Handles portfolio heat, diversification, and adaptive budget allocation.
"""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StrategyConfig(BaseModel):
    """Configuration for a specific strategy or model family."""

    name: str
    max_capital_share: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Max share of total equity this strategy can use"
    )
    max_risk_per_trade: float = Field(
        default=0.02, ge=0.0, le=0.05, description="Max risk % per single trade"
    )
    is_active: bool = True


class AllocationRequest(BaseModel):
    """Typed request for capital allocation."""

    strategy_id: str
    symbol: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_risk: float = Field(ge=0.0, le=0.05)
    current_stop_loss_dist: float = Field(gt=0.0, description="Distance to SL in price units")
    pip_value: float = Field(default=1.0)


class AllocationResult(BaseModel):
    """Typed result from the capital allocator."""

    approved: bool
    allocated_risk: float = 0.0
    lot_size: float = 0.0
    rejection_reason: Optional[str] = None
    portfolio_heat_after: float


class CapitalAllocator:
    """
    Manages capital distribution across multiple strategies.
    Ensures portfolio-wide risk limits and diversification.
    """

    # Institutional defaults
    MAX_PORTFOLIO_HEAT = 0.20  # 20% max equity at risk
    MAX_SYMBOL_CONCENTRATION = 0.10  # 10% max risk per symbol

    def __init__(self, total_equity: float, strategies: List[StrategyConfig]):
        self.total_equity = total_equity
        self.strategies = {s.name: s for s in strategies}

        # Tracking live risk (in currency units)
        self.strategy_risk: Dict[str, float] = {s.name: 0.0 for s in strategies}
        self.symbol_risk: Dict[str, float] = {}
        self.total_risk: float = 0.0

    def update_equity(self, new_equity: float):
        """Update the base equity for calculations."""
        self.total_equity = new_equity
        logger.info(f"CapitalAllocator equity updated to {self.total_equity}")

    def calculate_allocation(self, request: AllocationRequest) -> AllocationResult:
        """
        Main entry point for capital routing.
        Implements adaptive allocation and multi-layer safety checks.
        """
        if request.strategy_id not in self.strategies:
            return self._reject("Unknown strategy ID", 0.0)

        strat_cfg = self.strategies[request.strategy_id]
        if not strat_cfg.is_active:
            return self._reject("Strategy is inactive", 0.0)

        # 1. Portfolio Heat Check
        current_heat = self.total_risk / self.total_equity
        if current_heat >= self.MAX_PORTFOLIO_HEAT:
            return self._reject(f"Max portfolio heat reached: {current_heat:.2%}", current_heat)

        # 2. Strategy Cap Check
        strat_current_risk = self.strategy_risk.get(request.strategy_id, 0.0)
        strat_max_risk = self.total_equity * strat_cfg.max_capital_share
        if strat_current_risk >= strat_max_risk:
            return self._reject(f"Strategy {request.strategy_id} cap reached", current_heat)

        # 3. Symbol Concentration Check
        symbol_current_risk = self.symbol_risk.get(request.symbol, 0.0)
        if symbol_current_risk >= (self.total_equity * self.MAX_SYMBOL_CONCENTRATION):
            return self._reject(f"Max concentration for {request.symbol} reached", current_heat)

        # 4. Adaptive Risk Calculation
        # Scale suggested risk by confidence and available room
        target_risk_pct = min(request.suggested_risk, strat_cfg.max_risk_per_trade)

        # Confidence weighting (adaptive budget)
        # If confidence is 0.6 (threshold), we take 60% of target risk, etc.
        # Below 0.5 we don't trade (usually handled by signal layer, but safety here)
        if request.confidence < 0.5:
            return self._reject("Confidence too low for allocation", current_heat)

        final_risk_pct = target_risk_pct * request.confidence

        # Ensure we don't exceed remaining portfolio heat
        remaining_heat_pct = self.MAX_PORTFOLIO_HEAT - current_heat
        final_risk_pct = min(final_risk_pct, remaining_heat_pct)

        # Ensure we don't exceed remaining strategy cap
        remaining_strat_pct = (strat_max_risk - strat_current_risk) / self.total_equity
        final_risk_pct = min(final_risk_pct, remaining_strat_pct)

        # Calculate absolute risk and lot size
        risk_amount = self.total_equity * final_risk_pct

        # Position sizing: risk_amount = lot_size * SL_dist * pip_value
        # lot_size = risk_amount / (SL_dist * pip_value)
        if request.current_stop_loss_dist <= 0:
            return self._reject("Invalid stop loss distance", current_heat)

        lot_size = risk_amount / (request.current_stop_loss_dist * request.pip_value)
        lot_size = round(max(0.0, lot_size), 2)

        if lot_size < 0.01:
            return self._reject("Calculated lot size too small", current_heat)

        return AllocationResult(
            approved=True,
            allocated_risk=final_risk_pct,
            lot_size=lot_size,
            portfolio_heat_after=(self.total_risk + risk_amount) / self.total_equity,
        )

    def register_trade(self, strategy_id: str, symbol: str, risk_amount: float):
        """Register a live trade to track current risk exposure."""
        self.strategy_risk[strategy_id] = self.strategy_risk.get(strategy_id, 0.0) + risk_amount
        self.symbol_risk[symbol] = self.symbol_risk.get(symbol, 0.0) + risk_amount
        self.total_risk += risk_amount
        logger.debug(
            f"Registered trade: {strategy_id} {symbol} risk={risk_amount}. Total risk={self.total_risk}"
        )

    def unregister_trade(self, strategy_id: str, symbol: str, risk_amount: float):
        """Remove a closed trade from risk tracking."""
        self.strategy_risk[strategy_id] = max(
            0.0, self.strategy_risk.get(strategy_id, 0.0) - risk_amount
        )
        self.symbol_risk[symbol] = max(0.0, self.symbol_risk.get(symbol, 0.0) - risk_amount)
        self.total_risk = max(0.0, self.total_risk - risk_amount)
        logger.debug(
            f"Unregistered trade: {strategy_id} {symbol} risk={risk_amount}. Total risk={self.total_risk}"
        )

    def _reject(self, reason: str, current_heat: float) -> AllocationResult:
        logger.info(f"Allocation rejected: {reason}")
        return AllocationResult(
            approved=False, rejection_reason=reason, portfolio_heat_after=current_heat
        )
