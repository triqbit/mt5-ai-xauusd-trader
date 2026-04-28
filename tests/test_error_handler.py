"""
Tests for Resilience utilities.
"""
import unittest
import time
from unittest.mock import MagicMock
from src.core.error_handler import CircuitBreaker, CircuitBreakerError, CircuitState, retry_with_backoff

class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")
        mock_func = MagicMock(return_value="ok")

        result = cb.call(mock_func)

        self.assertEqual(result, "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failures, 0)

    def test_circuit_breaker_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")
        mock_func = MagicMock(side_effect=Exception("fail"))

        # First failure
        with self.assertRaises(Exception):
            cb.call(mock_func)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failures, 1)

        # Second failure -> Open
        with self.assertRaises(Exception):
            cb.call(mock_func)
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertEqual(cb.failures, 2)

        # Subsequent calls fail immediately with CircuitBreakerError
        with self.assertRaises(CircuitBreakerError):
            cb.call(mock_func)

    def test_circuit_breaker_recovery(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name="test")
        mock_func = MagicMock(side_effect=Exception("fail"))

        # Trip the breaker
        with self.assertRaises(Exception):
            cb.call(mock_func)
        self.assertEqual(cb.state, CircuitState.OPEN)

        time.sleep(0.15)

        # Should transition to HALF_OPEN
        mock_func.side_effect = None
        mock_func.return_value = "recovered"

        result = cb.call(mock_func)

        self.assertEqual(result, "recovered")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failures, 0)

class TestRetryWithBackoff(unittest.TestCase):
    def test_retry_success_after_failure(self):
        mock_func = MagicMock(side_effect=[Exception("fail"), "ok"])

        # We need to use a smaller initial_delay for tests
        @retry_with_backoff(retries=2, initial_delay=0.01, jitter=False)
        def decorated_func():
            return mock_func()

        result = decorated_func()
        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 2)

    def test_retry_exhausted(self):
        mock_func = MagicMock(side_effect=Exception("permanent fail"))

        @retry_with_backoff(retries=2, initial_delay=0.01, jitter=False)
        def decorated_func():
            return mock_func()

        with self.assertRaises(Exception):
            decorated_func()

        self.assertEqual(mock_func.call_count, 3) # 1 original + 2 retries

if __name__ == '__main__':
    unittest.main()
