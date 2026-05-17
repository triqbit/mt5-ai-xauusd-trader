# Trade Signal Explainability System

The explainability system in `src/core/explainability.py` provides institutional-grade attribution for trade signals.

## Components

- **Execution Filters**: Detailed trace of all technical and operational gates.
- **Model Attribution**: Individual model contributions and dominance tracking within the ensemble, powered by the [Dynamic Ensemble Weighting Engine](./DYNAMIC_ENSEMBLE.md).
- **Feature Cluster Contributions**: Automated grouping of features into categories like Momentum, Volatility, Trend, and Volume.
- **Regime Context**: Alignment with detected market regimes, trading sessions, and volatility states.
- **Risk Assessment**: Breakdown of risk-reward ratios, drawdown impact, and Kelly-based sizing.

## Implementation Details

- **Typed Models**: Utilizes Pydantic for strict runtime validation and type safety.
- **Immutability**: Attribution models are frozen to ensure a reliable audit trail.
- **Strategic Confluence**: Calculates a weighted score based on model confidence, regime alignment, session, and volatility.

## Usage

```python
explainer = SignalExplainer()
explanation = explainer.explain(
    symbol=\"XAUUSD\",
    direction=1,
    confidence=0.85,
    ...
)
print(explainer.format_for_terminal(explanation))
```
