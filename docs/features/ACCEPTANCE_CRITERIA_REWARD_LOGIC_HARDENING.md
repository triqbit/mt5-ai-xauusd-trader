# Acceptance Criteria: Reward Logic Hardening (RL Training)

## Functional Acceptance Criteria
- **Behavior:**
    - Replace placeholder constant rewards with a multi-factor reward function for RL agent training (PPO, Dreamer).
    - Incorporate Risk-Adjusted Returns: Reward = (PnL / Max Drawdown) * Volatility Scaling.
    - Implement a "Safety Penalty" for trades that violate risk thresholds or experience excessive slippage.
    - Include a "Time Penalty" to discourage over-trading or holding positions through high-impact news without conviction.
    - Ensure reward normalization to prevent gradient instability during training.
- **Edge Cases:**
    - Correctly handle zero-trade episodes (neutral reward or small penalty for inactivity if appropriate).
    - Handle massive PnL outliers by clipping rewards to a specific standard deviation.
- **Inputs/Outputs:**
    - **Inputs:** Realized PnL, Trade Duration, Max Adverse Excursion (MAE), Volatility (ATR), Slippage.
    - **Outputs:** Normalized scalar `Reward` value.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the `RewardCalculator` ensuring correct output for various PnL and risk scenarios.
    - Property-based testing to ensure rewards stay within normalized bounds (e.g., [-1, 1]).
- **Performance:**
    - Reward calculation must be negligible (< 1ms) to avoid slowing down the training loop.
- **Error Handling:**
    - Validation of input metrics to prevent `NaN` or `Inf` rewards.
- **Observability:**
    - Detailed logging of reward components (Base PnL, Risk Penalty, News Penalty) for training analysis.

## Operational Acceptance
- **Documentation:**
    - Update the RL Research documentation with the new reward shaping formulas.
- **Configuration:**
    - `REWARD_PNL_WEIGHT`: Weight for raw profitability.
    - `REWARD_RISK_PENALTY_WEIGHT`: Weight for drawdown/risk violations.
    - `REWARD_SLIPPAGE_PENALTY`: Multiplier for slippage-induced losses.
- **Rollback:**
    - Ability to revert to simpler reward functions for baseline comparisons.
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Integral for transitioning RL agents from "Stubs" to "Functional".
- **Backward Compatibility:** N/A (Training logic only).
- **Migration:** N/A.
- **Sign-off:** Requires approval from the ML Research Lead (Jules01) and Quant Lead (Jules04).
