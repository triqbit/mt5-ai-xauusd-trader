# Acceptance Criteria: Institutional What-If Execution Simulator

## Functional Acceptance Criteria
- **Behavior:**
    - Immediately following a `TradeSignal` generation, the system must simulate the trade's outcome under at least three discrete scenarios:
        1. **Base Case:** Current market conditions (spread, volatility).
        2. **Execution Stress:** Dynamically calibrated based on realized slippage (30-day rolling mean) + 3x spread widening.
        3. **Market Shock:** A sudden 50-pip move against the position (Flash Crash scenario).
    - **Slippage Feedback Loop:** The system must automatically ingest the last 30 days of realized slippage from `TradeLogger` to set the baseline for the "Execution Stress" scenario.
    - For each scenario, the system must calculate:
        - **Projected PnL:** Realized outcome if the scenario occurs.
        - **Drawdown Impact:** Percentage impact on the current daily and total equity peak.
        - **Stop-Out Probability:** Heuristic probability that the trade hits SL under the given volatility.
    - A "Safety Interlock" must be able to prevent trade execution if the "Market Shock" scenario results in a loss exceeding 50% of the remaining daily loss limit.
- **Edge Cases:**
    - Handle signals where SL/TP are not yet defined (e.g., pending orders) by using ATR-based projections.
    - Handle cases where current market liquidity is too low to provide a reliable "Base Case."
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal`, `MarketRegime`, `AccountState`, `RareEventConfig`.
    - **Outputs:** `WhatIfBriefing` Pydantic model containing scenario results.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the impact calculation logic.
    - Integration tests with `RareEventSimulator` to ensure scenario data is correctly ingested.
    - Integration tests with `TradeLogger` verifying that the simulator correctly calculates the 30-day rolling mean slippage.
    - Performance benchmark: Total simulation time must be < 300ms.
- **Performance:**
    - Must use vectorized calculations where possible to maintain low latency.
- **Error Handling:**
    - If the simulator fails, the system must default to the `RiskManager`'s standard filters and log a `SIMULATOR_ERROR` event.
- **Observability:**
    - Every simulation result must be logged to the `trade_simulations` table for post-trade analysis.
    - The "Stress Rehearsal" panel in the Decision Cockpit must update in real-time when a signal is pending.

## Operational Acceptance
- **Documentation:**
    - Technical guide on how to configure "Market Shock" parameters in `config.py`.
    - User guide for interpreting the "Risk-of-Ruin" heatmap in the TUI.
- **Configuration:**
    - `WHAT_IF_SIMULATOR_ENABLED` (bool)
    - `SIMULATOR_SHOCK_PIPS` (int): Default 50.
    - `SIMULATOR_SLIPPAGE_MAX` (int): Default 5.
- **Rollback:**
    - Disabling the feature must not impact the core signal-to-execution flow.
- **Monitoring:**
    - Alert if the simulator consistently rejects trades that the `RiskManager` would have otherwise approved.

## Release Readiness
- **Deployment:** Integrated with the Institutional Intelligence module.
- **Backward Compatibility:** No breaking changes to `TradeSignal` or `RiskManager` interfaces.
- **Migration:** Database migration required for the `trade_simulations` table.
- **Sign-off:** Requires approval from Jules04 (Quant Lead) and Jules02 (Observability Lead).
