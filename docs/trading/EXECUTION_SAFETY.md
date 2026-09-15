# Execution Safety & Regime-Adaptive Hardening

The `ExecutionFilter` (src/trading/execution_filter.py) implements a multi-layer validation cascade to vet signals before they reach the market. To ensure stability in volatile conditions, it uses **Regime-Adaptive Hardening**.

## Regime-Adaptive Logic

When the `RegimeDetector` identifies high-risk market states, the `ExecutionFilter` automatically tightens its requirements:

### 1. News Shock (`NEWS_SHOCK`)
During news-driven spikes or extreme volatility:
- **Confidence Floor**: Raised from the default (0.55) to **0.70**.
- **Model Drift Threshold**: Reduced by **0.1** (e.g., from 0.3 to 0.2), increasing sensitivity to model deterioration.
- **Accuracy Floor**: Raised by **0.05** (e.g., from 0.45 to 0.50).

### 2. Volatile Breakout (`VOLATILE_BREAKOUT`)
During confirmed high-volatility breakouts:
- **Confidence Floor**: Raised from the default (0.55) to **0.65**.
- **Model Drift Threshold**: Reduced by **0.1**.
- **Accuracy Floor**: Raised by **0.05**.

## Regime Stability Guard (Layer 12)

In addition to threshold hardening, the system includes a **Regime Stability Guard**. This guard monitors the statistical confidence and transition score of the regime detection.

- **Block Condition**: If the `transition_score` exceeds **0.8**, all signal execution is blocked.
- **Rationale**: A high transition score indicates that the market is in a state of flux where historical regime patterns are breaking down, making model predictions statistically unreliable.

## Configuration

These safety features are integrated into the core `ExecutionFilter.validate()` pipeline and do not require manual activation. They are driven by the `regime_info` object propagated from `main.py`.

For manual limit adjustments, see `RISK_LIMITS.md`.
