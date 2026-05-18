"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/capital_allocator.py
Institutional-grade capital management system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import contextlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Generator

import structlog
from pydantic import BaseModel, Field

from src.core.audit_log import get_audit_logger
from src.core.config import TradingConfig

logger = structlog.get_logger(__name__)


class RejectionCode(str, Enum):
    """Programmatic rejection codes for allocation failures."""

    STRATEGY_NOT_FOUND = "STRATEGY_NOT_FOUND"
    TOTAL_HEAT_LIMIT = "TOTAL_HEAT_LIMIT"
    SYMBOL_CONCENTRATION_LIMIT = "SYMBOL_CONCENTRATION_LIMIT"
    FAMILY_CONCENTRATION_LIMIT = "FAMILY_CONCENTRATION_LIMIT"
    CAPITAL_CAP_REACHED = "CAPITAL_CAP_REACHED"
    SCALED_TO_ZERO = "SCALED_TO_ZERO"
    NO_BUDGET = "NO_BUDGET"


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
    consecutive_losses: int = Field(
        default=0, description="Current streak of consecutive losing trades."
    )
    max_consecutive_losses: int = Field(
        default=5, description="Threshold for cooling-off mechanism."
    )


class AllocationRequest(BaseModel):
    """Request for capital allocation."""

    strategy_id: str
    risk_pct: float
    allow_scaling: bool = False


class AllocationResult(BaseModel):
    """Typed result of a capital allocation request."""

    strategy_id: str
    allocated_amount: float
    allocated_risk_pct: float
    requested_risk_pct: float
    is_allowed: bool
    rejection_reason: str | None = None
    rejection_code: RejectionCode | None = None
    was_capped: bool = False
    was_scaled: bool = False


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
        soft_limit_buffer: float = 0.1,  # Buffer for diversification guard
        monitor: Any | None = None,
    ):
        self.total_budget = total_budget
        self.max_symbol_risk = max_symbol_risk
        self.max_family_risk = max_family_risk
        self.max_total_heat = max_total_heat
        self.performance_step = performance_step
        self.decay_rate = decay_rate
        self.soft_limit_buffer = soft_limit_buffer
        self.monitor = monitor

        self.strategies: dict[str, StrategyConfig] = {}
        self.current_allocations: dict[str, float] = {}  # strategy_id -> current allocated amount
        self.rejection_history: dict[str, int] = {code.value: 0 for code in RejectionCode}

    @staticmethod
    def from_config(config: TradingConfig, total_budget: float, monitor: Any | None = None) -> CapitalAllocator:
        """
        Factory method to initialize CapitalAllocator from TradingConfig.
        """
        return CapitalAllocator(
            total_budget=total_budget,
            max_symbol_risk=config.allocator_max_symbol_risk,
            max_family_risk=config.allocator_max_family_risk,
            max_total_heat=config.allocator_max_total_heat,
            performance_step=config.allocator_performance_step,
            decay_rate=config.allocator_decay_rate,
            soft_limit_buffer=config.allocator_soft_limit_buffer,
            monitor=monitor,
        )

    def add_strategy(self, config: StrategyConfig) -> None:
        """Register a new strategy for capital allocation."""
        self.strategies[config.strategy_id] = config
        if config.strategy_id not in self.current_allocations:
            self.current_allocations[config.strategy_id] = 0.0
        logger.info("strategy_registered", strategy_id=config.strategy_id, symbol=config.symbol)

    def update_budget(self, new_budget: float) -> None:
        """Dynamically update the total budget."""
        old_budget = self.total_budget
        self.total_budget = max(0.0, new_budget)
        logger.info("budget_updated", old_budget=old_budget, new_budget=self.total_budget)

    def update_allocation(self, strategy_id: str, amount: float) -> None:
        """Update the currently used capital for a strategy."""
        if strategy_id in self.strategies:
            self.current_allocations[strategy_id] = max(0.0, amount)

    def release_allocation(self, strategy_id: str) -> None:
        """Explicitly release all allocated capital for a strategy."""
        if strategy_id in self.current_allocations:
            self.current_allocations[strategy_id] = 0.0
            logger.debug("allocation_released", strategy_id=strategy_id)

    @contextlib.contextmanager
    def _temporary_allocation(self, strategy_id: str, amount: float) -> Generator[None, None, None]:
        """Temporarily set an allocation for scoring purposes, then restore."""
        old_amt = self.current_allocations.get(strategy_id, 0.0)
        self.current_allocations[strategy_id] = amount
        try:
            yield
        finally:
            self.current_allocations[strategy_id] = old_amt

    def route_allocation(
        self, symbol: str, risk_pct: float, allow_scaling: bool = False
    ) -> AllocationResult | None:
        """
        Diversification-aware routing.
        Selects the optimal strategy for a symbol by calculating which one
        would result in the best portfolio diversification score.
        """
        eligible_strategies = [
            sid for sid, config in self.strategies.items() if config.symbol == symbol
        ]
        if not eligible_strategies:
            logger.warning("no_strategies_for_symbol", symbol=symbol)
            return None

        best_score = -1.0
        best_result = None

        for sid in eligible_strategies:
            # Simulate allocation silently to avoid audit pollution
            res = self.request_allocation(sid, risk_pct, allow_scaling=allow_scaling, silent=True)
            if not res.is_allowed:
                continue

            with self._temporary_allocation(sid, res.allocated_amount):
                score = self.get_diversification_score()

            if score > best_score:
                best_score = score
                best_result = res

        if best_result:
            logger.info(
                "allocation_routed",
                symbol=symbol,
                strategy_id=best_result.strategy_id,
                diversification_score=best_score,
            )
        else:
            logger.warning("no_eligible_strategy", symbol=symbol)

        return best_result

    def save_state(self, filepath: str | Path) -> None:
        """
        Persist strategy performance multipliers and historical PnL to a JSON file.
        Useful for maintaining state across system restarts.
        """
        state = {
            sid: {
                "performance_multiplier": config.performance_multiplier,
                "historical_pnl": config.historical_pnl,
                "consecutive_losses": config.consecutive_losses,
            }
            for sid, config in self.strategies.items()
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=4)
        logger.info("state_saved", filepath=str(filepath))

    def load_state(self, filepath: str | Path) -> None:
        """
        Load strategy performance multipliers and historical PnL from a JSON file.
        Only updates strategies that are already registered.
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning("state_file_not_found", filepath=str(filepath))
            return

        with open(path) as f:
            state = json.load(f)

        for sid, data in state.items():
            if sid in self.strategies:
                config = self.strategies[sid]
                config.performance_multiplier = data.get(
                    "performance_multiplier", config.performance_multiplier
                )
                config.historical_pnl = data.get("historical_pnl", config.historical_pnl)
                config.consecutive_losses = data.get(
                    "consecutive_losses", config.consecutive_losses
                )
                logger.debug("state_restored", strategy_id=sid)

        logger.info("state_loaded", filepath=str(filepath))

    def update_strategy_performance(self, strategy_id: str, pnl: float) -> None:
        """
        Adjust performance multiplier based on trade outcome.
        Positive PnL increases multiplier, negative PnL decreases it.
        Implements cooling-off mechanism based on consecutive losses.
        """
        if strategy_id not in self.strategies:
            return

        config = self.strategies[strategy_id]
        old_multiplier = config.performance_multiplier
        config.historical_pnl += pnl

        if pnl > 0:
            config.consecutive_losses = 0
            config.performance_multiplier = min(
                2.0, config.performance_multiplier + self.performance_step
            )
        elif pnl < 0:
            config.consecutive_losses += 1
            config.performance_multiplier = max(
                0.0, config.performance_multiplier - self.performance_step
            )

            # Cooling-off mechanism: Floor multiplier if too many losses
            if config.consecutive_losses >= config.max_consecutive_losses:
                logger.warning(
                    "cooling_off_triggered",
                    strategy_id=strategy_id,
                    consecutive_losses=config.consecutive_losses,
                )
                config.performance_multiplier = min(config.performance_multiplier, 0.1)

        if old_multiplier != config.performance_multiplier:
            with contextlib.suppress(RuntimeError, ImportError):
                get_audit_logger().log_config_change(
                    old_config={"strategy_id": strategy_id, "multiplier": old_multiplier},
                    new_config={
                        "strategy_id": strategy_id,
                        "multiplier": config.performance_multiplier,
                    },
                    reason=f"Performance adjustment for {strategy_id} after trade outcome: {pnl:.2f}",
                )

        logger.debug(
            "performance_updated",
            strategy_id=strategy_id,
            multiplier=config.performance_multiplier,
            pnl=pnl,
            consecutive_losses=config.consecutive_losses,
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

    def get_diversification_score(self) -> float:
        """
        Calculate portfolio diversification score using multi-factor normalized HHI.
        Ranges from 0.0 (maximum concentration) to 1.0 (perfectly diversified).

        Factors:
        - Strategy-level HHI (40%): Diversification across specific models.
        - Symbol-level HHI (30%): Diversification across assets.
        - Family-level HHI (30%): Diversification across model architectures.

        Normalization uses the number of registered strategies as the baseline
        degrees of freedom.
        """
        total_allocated = sum(self.current_allocations.values())
        n_strategies = len(self.strategies)

        if total_allocated <= 0 or n_strategies <= 1:
            return 1.0

        def _calculate_score(shares: list[float]) -> float:
            """Calculate 1.0 - normalized HHI using n_strategies as the baseline."""
            hhi = sum(s**2 for s in shares)
            # normalized_hhi ranges from 0 (perfectly diversified) to 1 (concentrated)
            # We use n_strategies as the baseline because it represents the total
            # units of risk/decisions the system can make.
            normalized_hhi = (hhi - 1 / n_strategies) / (1 - 1 / n_strategies)
            return max(0.0, min(1.0, 1.0 - normalized_hhi))

        # 1. Strategy-level HHI
        strategy_shares = [amt / total_allocated for amt in self.current_allocations.values() if amt > 0]
        strategy_score = _calculate_score(strategy_shares)

        # 2. Symbol-level HHI
        symbol_totals: dict[str, float] = {}
        for sid, amt in self.current_allocations.items():
            if amt > 0:
                sym = self.strategies[sid].symbol
                symbol_totals[sym] = symbol_totals.get(sym, 0.0) + amt
        symbol_shares = [amt / total_allocated for amt in symbol_totals.values()]
        symbol_score = _calculate_score(symbol_shares)

        # 3. Family-level HHI
        family_totals: dict[str, float] = {}
        for sid, amt in self.current_allocations.items():
            if amt > 0:
                fam = self.strategies[sid].model_family
                family_totals[fam] = family_totals.get(fam, 0.0) + amt
        family_shares = [amt / total_allocated for amt in family_totals.values()]
        family_score = _calculate_score(family_shares)

        # Weighted Ensemble of Scores
        return (strategy_score * 0.4) + (symbol_score * 0.3) + (family_score * 0.3)

    def to_report_section(self, rejection_history: dict[str, int] | None = None) -> Any:
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
            rejection_summary=rejection_history or self.rejection_history,
            diversification_score=self.get_diversification_score(),
        )

    def _record_rejection(self, code: RejectionCode) -> None:
        """Increment the counter for a specific rejection reason."""
        self.rejection_history[code.value] += 1

    def allocate_batch(self, requests: list[AllocationRequest]) -> list[AllocationResult]:
        """
        Process a batch of allocation requests with prioritization.
        Prioritizes strategies based on their performance multipliers.
        Useful for multi-strategy portfolios or model ensembles.
        """
        # Sort requests by strategy performance multiplier (descending)
        sorted_requests = sorted(
            requests,
            key=lambda r: self.strategies.get(r.strategy_id).performance_multiplier
            if r.strategy_id in self.strategies
            else 0.0,
            reverse=True,
        )

        results = []
        for req in sorted_requests:
            res = self.request_allocation(
                req.strategy_id, req.risk_pct, allow_scaling=req.allow_scaling
            )
            results.append(res)
            # If allowed, we update the current allocation so subsequent requests
            # in the same batch see the updated heat.
            if res.is_allowed:
                self.update_allocation(res.strategy_id, res.allocated_amount)

        return results

    def request_allocation(
        self, strategy_id: str, risk_pct: float, allow_scaling: bool = False, silent: bool = False
    ) -> AllocationResult:
        """
        Evaluate if a strategy can be allocated the requested risk.
        Applies adaptive budget allocation, caps, and concentration limits.

        If allow_scaling is True, instead of rejecting due to heat limits,
        it will return the maximum possible allocation that fits within limits.

        Args:
            strategy_id: ID of the strategy requesting capital.
            risk_pct: Requested risk as a percentage of total budget.
            allow_scaling: If True, partial allocations are allowed.
            silent: If True, audit logging and metric recording are skipped (useful for simulations).
        """
        if self.total_budget <= 0:
            if not silent:
                self._record_rejection(RejectionCode.NO_BUDGET)
            res = AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason="Total budget is zero or negative",
                rejection_code=RejectionCode.NO_BUDGET,
            )
            self._log_and_audit(res, silent=silent)
            return res

        if strategy_id not in self.strategies:
            if not silent:
                self._record_rejection(RejectionCode.STRATEGY_NOT_FOUND)
            res = AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason="Strategy not registered",
                rejection_code=RejectionCode.STRATEGY_NOT_FOUND,
            )
            self._log_and_audit(res, silent=silent)
            return res

        config = self.strategies[strategy_id]
        was_capped = False
        was_scaled = False

        # 1. Apply Performance Multiplier (Adaptive Allocation)
        # This scales the requested risk based on historical performance.
        target_risk_pct = risk_pct * config.performance_multiplier
        if config.performance_multiplier != 1.0:
            was_scaled = True
        target_amount = self.total_budget * target_risk_pct

        # 2. Check Strategy-Level Capital Cap
        # Ensure we don't exceed the absolute capital limit for this strategy.
        if target_amount > config.capital_cap:
            logger.debug(
                "strategy_cap_exceeded",
                strategy_id=strategy_id,
                target_amount=target_amount,
                cap=config.capital_cap,
            )
            target_amount = config.capital_cap
            target_risk_pct = target_amount / self.total_budget
            was_capped = True

            if target_amount <= 0:
                if not silent:
                    self._record_rejection(RejectionCode.CAPITAL_CAP_REACHED)
                res = AllocationResult(
                    strategy_id=strategy_id,
                    allocated_amount=0.0,
                    allocated_risk_pct=0.0,
                    requested_risk_pct=risk_pct,
                    is_allowed=False,
                    rejection_reason="Strategy capital cap reached or zero",
                    rejection_code=RejectionCode.CAPITAL_CAP_REACHED,
                )
                self._log_and_audit(res, silent=silent)
                return res

        # 3. Diversification Guard: Linear scaling as limits are approached
        # This scales down the requested risk before hard limits are hit.
        current_total_heat = self.get_total_heat()
        symbol_heat = self.get_symbol_heat(config.symbol)
        family_heat = self.get_family_heat(config.model_family)

        def _calculate_soft_scale(current: float, limit: float, buffer: float) -> float:
            """Linearly scale down if within the buffer zone of a limit."""
            if buffer <= 0:
                return 1.0 if current <= limit else 0.0

            soft_limit = limit - buffer
            if current <= soft_limit:
                return 1.0
            if current >= limit:
                return 0.0
            # Linear decay from 1.0 to 0.0 across the buffer
            return (limit - current) / buffer

        heat_scale = _calculate_soft_scale(
            current_total_heat, self.max_total_heat, self.soft_limit_buffer
        )
        symbol_scale = _calculate_soft_scale(
            symbol_heat, self.max_symbol_risk, self.soft_limit_buffer
        )
        family_scale = _calculate_soft_scale(
            family_heat, self.max_family_risk, self.soft_limit_buffer
        )

        overall_soft_scale = min(heat_scale, symbol_scale, family_scale)
        if overall_soft_scale < 1.0:
            target_risk_pct *= overall_soft_scale
            was_scaled = True
            logger.debug(
                "diversification_guard_active",
                strategy_id=strategy_id,
                scale=overall_soft_scale,
                heat_scale=heat_scale,
                symbol_scale=symbol_scale,
                family_scale=family_scale,
            )

        # 4. Hard Safety Limits: Final check of scaled amount against absolute limits
        # Use the final target_risk_pct for safety checks.

        if current_total_heat + target_risk_pct > self.max_total_heat:
            if allow_scaling:
                target_risk_pct = max(0.0, self.max_total_heat - current_total_heat)
                was_capped = True
            else:
                if not silent:
                    self._record_rejection(RejectionCode.TOTAL_HEAT_LIMIT)
                res = AllocationResult(
                    strategy_id=strategy_id,
                    allocated_amount=0.0,
                    allocated_risk_pct=0.0,
                    requested_risk_pct=risk_pct,
                    is_allowed=False,
                    rejection_reason=f"Total heat limit reached: {current_total_heat:.2f}",
                    rejection_code=RejectionCode.TOTAL_HEAT_LIMIT,
                )
                self._log_and_audit(res, silent=silent)
                return res

        if symbol_heat + target_risk_pct > self.max_symbol_risk:
            if allow_scaling:
                target_risk_pct = max(0.0, self.max_symbol_risk - symbol_heat)
                was_capped = True
            else:
                if not silent:
                    self._record_rejection(RejectionCode.SYMBOL_CONCENTRATION_LIMIT)
                res = AllocationResult(
                    strategy_id=strategy_id,
                    allocated_amount=0.0,
                    allocated_risk_pct=0.0,
                    requested_risk_pct=risk_pct,
                    is_allowed=False,
                    rejection_reason=f"Symbol concentration limit reached for {config.symbol}",
                    rejection_code=RejectionCode.SYMBOL_CONCENTRATION_LIMIT,
                )
                self._log_and_audit(res, silent=silent)
                return res

        if family_heat + target_risk_pct > self.max_family_risk:
            if allow_scaling:
                target_risk_pct = max(0.0, self.max_family_risk - family_heat)
                was_capped = True
            else:
                if not silent:
                    self._record_rejection(RejectionCode.FAMILY_CONCENTRATION_LIMIT)
                res = AllocationResult(
                    strategy_id=strategy_id,
                    allocated_amount=0.0,
                    allocated_risk_pct=0.0,
                    requested_risk_pct=risk_pct,
                    is_allowed=False,
                    rejection_reason=f"Family concentration limit reached for {config.model_family}",
                    rejection_code=RejectionCode.FAMILY_CONCENTRATION_LIMIT,
                )
                self._log_and_audit(res, silent=silent)
                return res

        # Final check if scaling reduced it to zero
        if target_risk_pct <= 0:
            # We already checked RejectionCode.CAPITAL_CAP_REACHED in step 2.
            # If scaling brought it to 0, it means we're at some heat limit or scaling was zero.
            if not silent:
                self._record_rejection(RejectionCode.SCALED_TO_ZERO)
            res = AllocationResult(
                strategy_id=strategy_id,
                allocated_amount=0.0,
                allocated_risk_pct=0.0,
                requested_risk_pct=risk_pct,
                is_allowed=False,
                rejection_reason="Scaling or safety limits reduced allocation to zero",
                rejection_code=RejectionCode.SCALED_TO_ZERO,
            )
            self._log_and_audit(res, silent=silent)
            return res

        target_amount = self.total_budget * target_risk_pct

        res = AllocationResult(
            strategy_id=strategy_id,
            allocated_amount=target_amount,
            allocated_risk_pct=target_risk_pct,
            requested_risk_pct=risk_pct,
            is_allowed=True,
            was_capped=was_capped,
            was_scaled=was_scaled,
        )
        self._log_and_audit(res, silent=silent)
        return res

    def _log_and_audit(self, result: AllocationResult, silent: bool = False) -> None:
        """Helper to log and audit an allocation result."""
        if silent:
            return

        if result.is_allowed:
            logger.info(
                "allocation_allowed",
                strategy_id=result.strategy_id,
                amount=result.allocated_amount,
                risk=result.allocated_risk_pct,
            )
        else:
            logger.warning(
                "allocation_rejected",
                strategy_id=result.strategy_id,
                reason=result.rejection_reason,
                code=result.rejection_code,
            )
            if self.monitor and result.rejection_code:
                self.monitor.record_internal_rejection("capital_allocator", result.rejection_code.value)

        with contextlib.suppress(RuntimeError, ImportError):
            get_audit_logger().log_allocation_decision(
                strategy_id=result.strategy_id,
                requested_risk=result.requested_risk_pct,
                allocated_amount=result.allocated_amount,
                is_allowed=result.is_allowed,
                rejection_code=result.rejection_code.value if result.rejection_code else None,
                metadata={
                    "was_capped": result.was_capped,
                    "was_scaled": result.was_scaled,
                    "rejection_reason": result.rejection_reason,
                },
            )


__all__ = [
    "AllocationRequest",
    "AllocationResult",
    "CapitalAllocator",
    "RejectionCode",
    "StrategyConfig",
]
