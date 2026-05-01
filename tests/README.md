# Tests Suite

This directory contains the comprehensive testing suite for the MT5 AI/ML Trading Bot.

## Structure

- **Unit Tests**: Test individual components in isolation (e.g., `test_config.py`, `test_monitor.py`).
- **Integration Tests**: (Planned) Test interactions between modules and external services like MT5.
- **Fixtures**: Shared test data and mocks defined in `conftest.py`.

## Running Tests

Ensure all dependencies are installed, including `pytest`:

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=src
```

## Mocking External Services

We use `pytest` and `monkeypatch` to mock MT5 connectivity in CI environments where the MT5 terminal is not available.

## CI/CD Integration

Tests are automatically executed on every push and pull request via GitHub Actions (`.github/workflows/ci.yml`).
