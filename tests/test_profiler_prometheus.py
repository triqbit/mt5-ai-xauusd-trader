"""
Unit tests for the profiler with Prometheus integration.
"""
import time
from unittest.mock import MagicMock, patch

from src.core.profiler import profile


def test_profile_prometheus_interaction():
    """Verify that the profiler calls Prometheus observe."""
    # We need to mock TRADING_BLOCK_DURATION in src.core.profiler
    mock_histogram = MagicMock()

    with patch("src.core.profiler.TRADING_BLOCK_DURATION", mock_histogram):
        with profile("test_prometheus"):
            time.sleep(0.01)

        # Check if labels was called with correct block_label
        mock_histogram.labels.assert_called_with(block_label="test_prometheus")
        # Check if observe was called on the returned label object
        mock_histogram.labels.return_value.observe.assert_called_once()
        # The observed value should be approximately 0.01
        args, _ = mock_histogram.labels.return_value.observe.call_args
        assert 0.01 <= args[0] <= 0.05
