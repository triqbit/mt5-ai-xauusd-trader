# Acceptance Criteria: RL Evaluation Framework

## Functional Acceptance Criteria
- **Behavior:** Evaluate RL agents using stability, turnover, drawdown, and regime-aware metrics against institutional baselines.
- **Edge Cases:**
    - Handle agents with non-standard action spaces (via adapters).
    - Accurate calculation of Sharpe and Sortino ratios for short history.
    - Segmentation of performance by `MarketRegime`.
- **Inputs/Outputs:**
    - **Inputs:** `RLModel`, `TradingEnv`, and evaluation period.
    - **Outputs:** `EvaluationReport` with typed metrics and baseline comparisons.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for all financial metrics (Sharpe, Sortino, R-squared).
    - Tests for regime-based segmentation logic.
    - Verification of turnover and hold-time calculations.
- **Performance:**
    - Evaluation run (1000 steps) < 10 seconds.
- **Error Handling:**
    - Handle division by zero in Sharpe ratio if volatility is zero.
- **Observability:**
    - Log evaluation progress and metric summaries.

## Operational Acceptance
- **Documentation:**
    - Reference: [RL Evaluation Framework](RL_EVALUATION.md) (Technical Specs & Usage).
    - Mathematical definitions for each institutional metric.
    - Instructions for adding new baseline strategies.
- **Configuration:**
    - Evaluation window and risk-free rate configurable via `research_config.yaml`.
- **Rollback:**
    - Research-only tool; no impact on production stability.
- **Monitoring:**
    - Use evaluation reports to trigger model retraining or promotion.

## Release Readiness
- **Deployment:** Requires `gymnasium` and `stable-baselines3` (optional).
- **Backward Compatibility:** Default metrics must align with previous model audits.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the AI Research Lead.
