# Tests Module

The `tests/` directory contains the unit and integration tests for the trading bot.

## Structure

- **test_config.py**: Validates configuration loading and risk rules.
- **test_monitor.py**: Tests for the real-time monitoring and alerting system.
- **test_trade_logger.py**: Integration tests for the SQLAlchemy-based trade logger.

## Execution

To run all tests:
```bash
python -m pytest
```
