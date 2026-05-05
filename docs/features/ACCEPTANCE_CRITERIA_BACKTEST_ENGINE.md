# Acceptance Criteria: Backtest Engine (Walk-Forward Optimization)

## Functional Acceptance Criteria
- **Behavior:**
    - Execute realistic backtests using a walk-forward approach (sliding train/test windows).
    - Simulate institutional trading conditions: spreads, commissions, and leverage.
    - Integrate with `FeatureEngineer` for consistent feature calculation.
    - Integrate with `ExecutionFilter` to vet signals during the simulation.
- **Edge Cases:**
    - Handle insufficient data for the requested train/test windows.
    - Handle model prediction failures gracefully during the loop.
    - Correctly close all open positions at the end of the data stream.
- **Inputs/Outputs:**
    - **Inputs:** OHLCV `pd.DataFrame`, model instance, walk-forward parameters (train_window, test_window, step_size).
    - **Outputs:** `PerformanceReport` containing annualized return, Sharpe ratio, Max Drawdown, Profit Factor, MAE/MFE.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for PnL calculation, SL/TP logic, and MAE/MFE tracking.
    - Integration test with `EnsembleModel` and `ExecutionFilter`.
    - Verification that NumPy-optimized loops match expected pandas-based results.
- **Performance:**
    - Optimized for speed using NumPy arrays; backtesting 10,000 bars should take < 2 seconds (excluding model inference).
- **Error Handling:**
    - Log errors if feature engineering fails or data is misaligned.
- **Observability:**
    - Detailed logging of every backtest trade (entry, exit, PnL, reason).

## Operational Acceptance
- **Documentation:**
    - User guide for walk-forward parameters and performance metric definitions.
- **Configuration:**
    - Simulation parameters (initial balance, spread, commission) must be configurable.
- **Rollback:**
    - N/A (Research component).
- **Monitoring:**
    - Track backtest execution time in development environments.

## Release Readiness
- **Deployment:** Research component; can be deployed independently of the live bot.
- **Backward Compatibility:** Must support existing strategy and model interfaces.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03).
