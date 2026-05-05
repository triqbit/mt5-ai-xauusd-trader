import structlog
from src.core.profiler import profile
from src.core.log_config import configure_logging

def test_profiler_captures_trace_id(capsys):
    """Verify that profiler logs include the trace_id from context."""
    # Force JSON output to easily parse and verify
    import sys
    from unittest.mock import patch

    # Mock isatty to False to get JSON output
    with patch.object(sys.stdout, 'isatty', return_value=False):
        configure_logging(level="INFO")

    trace_id = "test-trace-id"
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    with profile("test_block"):
        pass

    captured = capsys.readouterr()
    assert trace_id in captured.out
    assert "performance_metric" in captured.out
    assert "test_block" in captured.out
