from dataclasses import dataclass

from src.trading.safety_supervisor import SafetySupervisor


@dataclass
class Provider:
    positions: list[dict]
    terminal: dict | None = None
    error: Exception | None = None

    def get_account_info(self):
        if self.error:
            raise self.error
        return {"balance": 10000.0, "equity": 9950.0}

    def get_positions(self):
        return self.positions

    def get_terminal_status(self):
        return self.terminal or {"algo_trading": True}


def position(volume=0.2):
    return {"ticket": 7, "symbol": "XAUUSD", "type": 0, "volume": volume}


def test_healthy_reconciliation_allows_trading():
    supervisor = SafetySupervisor()

    result = supervisor.reconcile(Provider([position()]), [position()])

    assert result.is_safe
    assert supervisor.trading_allowed
    assert result.account_equity == 9950.0


def test_orphan_position_latches_halt_until_acknowledged():
    supervisor = SafetySupervisor()

    result = supervisor.reconcile(Provider([position()]), [])

    assert not result.is_safe
    assert "orphan_broker_positions:7" in result.reasons
    assert not supervisor.trading_allowed
    assert not supervisor.acknowledge_resume()

    supervisor.reconcile(Provider([]), [])
    assert supervisor.acknowledge_resume()
    assert supervisor.trading_allowed


def test_volume_mismatch_and_disabled_terminal_are_unsafe():
    supervisor = SafetySupervisor()

    result = supervisor.reconcile(
        Provider([position(0.3)], terminal={"algo_trading": False}),
        [position(0.2)],
    )

    assert not result.is_safe
    assert "terminal_algo_trading_disabled" in result.reasons
    assert "position_mismatch:7" in result.reasons


def test_provider_failure_fails_closed():
    supervisor = SafetySupervisor()

    result = supervisor.reconcile(Provider([], error=TimeoutError()), [])

    assert not result.is_safe
    assert result.reasons == ("broker_state_unavailable:TimeoutError",)
    assert not supervisor.trading_allowed


def test_position_without_ticket_is_unsafe():
    supervisor = SafetySupervisor()

    result = supervisor.reconcile(
        Provider([{"symbol": "XAUUSD", "type": 0, "volume": 0.2}]),
        [],
    )

    assert not result.is_safe
    assert "broker_position_missing_ticket" in result.reasons
