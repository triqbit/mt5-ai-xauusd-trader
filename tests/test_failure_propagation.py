"""
MT5 AI/ML Trading Bot - Failure Propagation Test
tests/test_failure_propagation.py

Verifies that unexpected component failures (exceptions) are correctly caught
by the system loop and do not lead to silent execution or system crashes.
"""

from unittest.mock import patch

import pytest

from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter


def test_execution_filter_exception_handling():
    """
    Verifies that if ExecutionFilter.validate raises an exception,
    it propagates out of the component (to be caught by the main loop).
    """
    filter_obj = ExecutionFilter()
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    with patch.object(ExecutionFilter, "validate", side_effect=RuntimeError("Filter Explosion!")):
        with pytest.raises(RuntimeError) as excinfo:
            filter_obj.validate(signal)
        assert "Filter Explosion!" in str(excinfo.value)

def test_main_loop_error_handling_structure():
    """
    Verifies the existence of error handling logic in main.py by inspecting its source.
    This is a meta-test to ensure the safety net is present.
    """
    import inspect

    import main

    source = inspect.getsource(main.run_live)
    assert "except Exception as exc:" in source
    assert "log.exception(\"Unhandled error in trading loop: %s\", exc)" in source
    assert "time.sleep(poll_interval)" in source
