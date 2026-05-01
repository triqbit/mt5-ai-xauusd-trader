# Acceptance Criteria: Risk Management Engine

## Feature Overview
The Risk Management Engine (`RiskManager`) is the central authority for trade validation and position sizing. It implements a multi-layer filter cascade and the Kelly Criterion to ensure institutional-grade capital protection.

## Functional Acceptance Criteria
- **Behavior**: Every trade signal must pass through a 6-layer validation pipeline.
- **Edge Cases**:
    - **Circuit Breaker**: Trading must be halted if total equity drawdown exceeds 15%.
    - **Daily Loss**: Trading must be halted if realized daily loss exceeds the configured limit (default 5%).
    - **Max Positions**: New trades must be rejected if the count of open positions reaches the limit (default 3).
    - **Symbol Allocation**: Only symbols defined in the Ray Dalio All-Weather portfolio (XAUUSD, EURUSD, etc.) are permitted.
    - **Minimum Confidence**: Signals with a model confidence score below the threshold (default 0.55) must be rejected.
    - **Risk-Reward (R:R)**: Signals must have a minimum R:R ratio (default 1.5).
- **Inputs/Outputs**:
    - **Inputs**: `TradeSignal` object.
    - **Outputs**: Boolean (Approved/Rejected) and a specific rejection reason.

## Technical Acceptance
- **Test Coverage**:
    - **Unit**: 90%+ coverage for `src/trading/risk_manager.py`, including filter layers and Kelly calculation.
    - **Integration**: Verify interaction with `TradeLogger` and `Monitor`.
    - **End-to-End**: Validated through backtesting cycles.
- **Performance**:
    - **Latency**: `approve()` method must execute in < 1ms.
    - **Resource Usage**: Negligible CPU/RAM footprint.
- **Error Handling**: Every rejected signal must log the specific filter that failed.
- **Logging/Observability**: Critical events (circuit breaker) logged at `CRITICAL`. Rejections tracked via `TradeLogger`.

## Operational Acceptance
- **Documentation**: Updated README and technical docs explaining the 6-layer filter logic.
- **Configuration**: `MAX_DAILY_LOSS`, `RISK_PER_TRADE`, and `MAX_POSITIONS` must be configurable via `.env`. `risk_per_trade` validated to be < 2%.
- **Rollback Considerations**: Configuration changes can be reverted by updating the `.env` file and restarting the bot.
- **Monitoring/Alerting**: Telegram alerts for circuit breaker triggers and daily summaries.

## Release Readiness
- **Deployment**: Can be deployed independently of ML models.
- **Backward Compatibility**: `TradeSignal` schema must remain compatible.
- **Migration Requirements**: None (in-memory state).
- **Stakeholder Sign-off**: Lead Trader approval required for hard risk limits (15% drawdown).
