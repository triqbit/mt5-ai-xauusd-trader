"""Broker-state reconciliation and fail-closed live trading gate."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol


logger = logging.getLogger(__name__)


class BrokerStateProvider(Protocol):
    """Minimum connector interface required by the safety supervisor."""

    def get_account_info(self) -> dict[str, Any]: ...

    def get_positions(self) -> list[dict[str, Any]]: ...

    def get_terminal_status(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of one broker-versus-strategy state check."""

    is_safe: bool
    reasons: tuple[str, ...] = ()
    broker_position_count: int = 0
    internal_position_count: int = 0
    account_balance: float | None = None
    account_equity: float | None = None


@dataclass
class SafetySupervisor:
    """Maintain a fail-closed gate for live order submission.

    A failed or mismatched reconciliation latches the supervisor in a halted
    state. An operator must acknowledge a subsequent healthy reconciliation
    before trading can resume.
    """

    volume_tolerance: float = 1e-6
    halted: bool = False
    halt_reasons: tuple[str, ...] = field(default_factory=tuple)
    last_result: ReconciliationResult | None = None

    @property
    def trading_allowed(self) -> bool:
        """Return whether new orders may be submitted."""

        return not self.halted

    def reconcile(
        self,
        provider: BrokerStateProvider,
        internal_positions: list[dict[str, Any]],
    ) -> ReconciliationResult:
        """Compare broker state with the strategy's current position view."""

        try:
            account = provider.get_account_info()
            broker_positions = provider.get_positions()
            terminal = provider.get_terminal_status()
        except Exception as exc:
            return self._halt((f"broker_state_unavailable:{type(exc).__name__}",))

        reasons: list[str] = []
        if terminal.get("algo_trading") is False:
            reasons.append("terminal_algo_trading_disabled")

        broker_by_ticket = self._index_positions(broker_positions)
        internal_by_ticket = self._index_positions(internal_positions)
        if len(broker_by_ticket) != len(broker_positions):
            reasons.append("broker_position_missing_ticket")
        if len(internal_by_ticket) != len(internal_positions):
            reasons.append("internal_position_missing_ticket")

        missing_tickets = sorted(set(internal_by_ticket) - set(broker_by_ticket))
        orphan_tickets = sorted(set(broker_by_ticket) - set(internal_by_ticket))
        if missing_tickets:
            reasons.append(f"missing_broker_positions:{','.join(missing_tickets)}")
        if orphan_tickets:
            reasons.append(f"orphan_broker_positions:{','.join(orphan_tickets)}")

        for ticket in sorted(set(internal_by_ticket) & set(broker_by_ticket)):
            internal = internal_by_ticket[ticket]
            broker = broker_by_ticket[ticket]
            if not self._same_position(internal, broker):
                reasons.append(f"position_mismatch:{ticket}")

        result = ReconciliationResult(
            is_safe=not reasons,
            reasons=tuple(reasons),
            broker_position_count=len(broker_positions),
            internal_position_count=len(internal_positions),
            account_balance=self._number(account.get("balance")),
            account_equity=self._number(account.get("equity")),
        )
        self.last_result = result
        if reasons:
            self.halted = True
            self.halt_reasons = result.reasons
            logger.critical("Live trading halted: %s", "; ".join(result.reasons))
        return result

    def acknowledge_resume(self) -> bool:
        """Resume trading only after a healthy reconciliation is recorded."""

        if self.last_result is None or not self.last_result.is_safe:
            return False
        self.halted = False
        self.halt_reasons = ()
        logger.warning("Live trading resume acknowledged")
        return True

    def _halt(self, reasons: tuple[str, ...]) -> ReconciliationResult:
        result = ReconciliationResult(is_safe=False, reasons=reasons)
        self.last_result = result
        self.halted = True
        self.halt_reasons = reasons
        logger.critical("Live trading halted: %s", "; ".join(reasons))
        return result

    def _index_positions(self, positions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for position in positions:
            ticket = position.get("ticket", position.get("id"))
            if ticket is not None:
                indexed[str(ticket)] = position
        return indexed

    def _same_position(self, left: dict[str, Any], right: dict[str, Any]) -> bool:
        if left.get("symbol") != right.get("symbol"):
            return False

        left_direction = left.get("type", left.get("direction"))
        right_direction = right.get("type", right.get("direction"))
        if left_direction != right_direction:
            return False

        left_volume = self._number(left.get("volume", left.get("lot_size")))
        right_volume = self._number(right.get("volume", right.get("lot_size")))
        return (
            left_volume is not None
            and right_volume is not None
            and abs(left_volume - right_volume) <= self.volume_tolerance
        )

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["BrokerStateProvider", "ReconciliationResult", "SafetySupervisor"]