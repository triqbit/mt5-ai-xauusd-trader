"""
Unit tests for the high-resolution profiler.
"""

import time
import pytest
from unittest.mock import patch
from src.core.profiler import profile


def test_profile_logging():
    """Verify that the profiler logs a performance metric with duration."""
    with patch("src.core.profiler.logger.info") as mock_log:
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
    with patch("src.core.profiler.logger.info") as mock_log:
        try:
            with profile("error_block"):
                raise ValueError("test error")
        except ValueError:
            pass

        mock_log.assert_called_once()
        assert mock_log.call_args[1]["label"] == "error_block"
