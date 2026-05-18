"""
Unit tests for the high-resolution profiler.
"""
import time
from unittest.mock import patch

from src.core.profiler import profile


def test_profile_logging():
    """Verify that the profiler logs a performance metric with duration at DEBUG level."""
    with patch("src.core.profiler.logger.debug") as mock_log:
        with profile("test_block"):
            time.sleep(0.01)

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "performance_metric"
        assert kwargs["label"] == "test_block"
        assert isinstance(kwargs["duration_ms"], float)
        assert kwargs["duration_ms"] >= 10.0

def test_profile_exception_handling():
    """Verify that the profiler still logs even if an exception occurs."""
    with patch("src.core.profiler.logger.debug") as mock_log:
        try:
            with profile("error_block"):
                raise ValueError("test error")
        except ValueError:
            pass

        mock_log.assert_called_once()
        assert mock_log.call_args[1]["label"] == "error_block"


def test_profile_slow_threshold():
    """Verify that the profiler logs at INFO level if slow_threshold_ms is exceeded."""
    with patch("src.core.profiler.logger.info") as mock_log_info, \
         patch("src.core.profiler.logger.debug") as mock_log_debug:

        # Test case 1: Below threshold -> DEBUG
        with profile("fast_block", slow_threshold_ms=100.0):
            time.sleep(0.01)

        mock_log_debug.assert_called_once()
        mock_log_info.assert_not_called()
        mock_log_debug.reset_mock()

        # Test case 2: Above threshold -> INFO
        with profile("slow_block", slow_threshold_ms=5.0):
            time.sleep(0.01)

        mock_log_info.assert_called_once()
        mock_log_debug.assert_not_called()
        args, kwargs = mock_log_info.call_args
        assert args[0] == "performance_metric_slow"
        assert kwargs["label"] == "slow_block"
        assert kwargs["threshold_ms"] == 5.0
