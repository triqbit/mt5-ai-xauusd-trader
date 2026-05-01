# Decision Support System

The Decision Support system provides institutional-grade oversight for trade decisions by generating structured "Decision Packets" before execution. It aggregates signal intelligence, risk evaluation, market context, and performance history into a human-readable dashboard.

## Key Components

### 1. Decision Packet (`src/core/decision_support.py`)
A typed Pydantic model that captures:
- **Signal Intelligence**: Direction, confidence, and model-by-model consensus.
- **Risk State**: Real-time evaluation of risk filters (Circuit Breaker, Daily Loss, etc.).
- **Market Regime**: Detected regime (Trending, Ranging, etc.) and volatility context.
- **Performance Context**: Recent strategy health (Sharpe Ratio, Win Rate, PnL).
- **Explainability**: Deep attribution summaries from the explainability engine.

### 2. Side-Effect-Free Risk Evaluation
The `RiskManager` implements `_get_rejection_reason`, allowing the system to perform "dry-run" risk checks. This ensures that operators can see why a trade *would* be blocked without triggering risk events or circuit breaker alerts prematurely.

### 3. Institutional Terminal Dashboard
A high-fidelity terminal output powered by `rich`, providing a scannable overview of the decision-making process.

## Usage Example

```python
from src.core.decision_support import DecisionSupport

# Initialize support system
support = DecisionSupport(trade_logger, risk_manager, regime_detector, signal_explainer)

# Generate a decision packet for a proposed signal
packet = support.generate_packet(signal, regime_info, explanation)

# Format for operator review
print(support.format_for_terminal(packet))
```

## Benefits
- **Operator Confidence**: Transparency into why the AI is proposing a specific action.
- **Enhanced Oversight**: Ability to review blocked signals and understand the "opportunity cost" of risk rejections.
- **Auditability**: Structured packets can be logged for post-trade research and compliance reviews.
