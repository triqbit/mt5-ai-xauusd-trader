# Capital Allocation System

The `CapitalAllocator` is an institutional-grade capital management system designed to handle allocation across multiple trading strategies or model families. It ensures that the portfolio maintains a healthy risk profile by tracking portfolio heat and enforcing concentration limits.

## Key Features

- **Portfolio Heat Tracking**: Monitors the total committed capital ratio to prevent overall portfolio overexposure.
- **Per-Strategy Capital Caps**: Limits the maximum capital any single strategy can use, regardless of its performance or requested risk.
- **Adaptive Budget Allocation**: Dynamically adjusts requested risk based on a strategy's `performance_multiplier`, rewarding profitable strategies and scaling down underperforming ones.
- **Diversification-Aware Routing**: Groups strategies by symbol and model family to enforce concentration limits, ensuring the portfolio remains diversified.
- **Portfolio Diversification Scoring**: Provides a quantitative `diversification_score` (0.0 to 1.0) based on the normalized Herfindahl-Hirschman Index (HHI).
- **Safety Limits**: Implements configurable limits for total portfolio heat, symbol-level risk, and model-family-level risk.
- **Flexible Allocation Scaling**: Supports an `allow_scaling` mode that returns the maximum possible allocation within safety limits instead of a binary rejection.
- **Batch Allocation & Routing**: Supports processing multiple simultaneous allocation requests, prioritizing strategies based on their performance multipliers to optimize capital utility.
- **Diversification Guard (Soft Limits)**: Implements a "Diversification Guard" that begins linear scaling of requested risk when exposure approaches hard limits, providing a smoother risk reduction than binary rejections.
- **Cooling-Off Periods**: Automatically enforces a cooling-off period (capping risk multipliers at 0.1) when a strategy hits a configurable consecutive loss threshold, preventing "tilt" and protecting capital during drawdown.
- **Programmatic Rejection Codes**: Returns specific `RejectionCode` values (e.g., `TOTAL_HEAT_LIMIT`, `SYMBOL_CONCENTRATION_LIMIT`) and maintains a `rejection_history` for audit and reporting.
- **Dynamic Risk Adaptation**: Automatically updates strategy multipliers based on PnL outcomes and decays them back to baseline (1.0) over time.

## Configuration

The `CapitalAllocator` is initialized with the following parameters:

- `total_budget`: The total capital available for allocation.
- `max_symbol_risk`: Maximum percentage of total budget that can be allocated to a single symbol (default: 40%).
- `max_family_risk`: Maximum percentage of total budget that can be allocated to a single model family (default: 40%).
- `max_total_heat`: Maximum total percentage of budget that can be committed at once (default: 70%).
- `performance_step`: The increment/decrement applied to the performance multiplier after each trade (default: 0.05).
- `decay_rate`: The rate at which the multiplier returns to 1.0 periodically (default: 0.001).
- `soft_limit_buffer`: Percentage of budget used as a buffer for the Diversification Guard (default: 10%).

### Strategy Configuration

Each strategy is registered using a `StrategyConfig` model:

- `strategy_id`: Unique identifier for the strategy.
- `symbol`: The trading symbol (e.g., XAUUSD).
- `model_family`: The family of the model (e.g., RL, LSTM, Ensemble).
- `capital_cap`: Maximum absolute capital the strategy is allowed to use.
- `performance_multiplier`: A multiplier (0.0 to 2.0) applied to the strategy's requested risk.
- `historical_pnl`: Accumulated PnL for tracking long-term strategy health.
- `win_count` / `loss_count`: Tracks historical trade outcomes.
- `consecutive_losses`: Current streak of losing trades.
- `max_consecutive_losses`: Threshold for triggering a cooling-off period (default: 5).

## Usage Example

```python
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig

# Initialize allocator
allocator = CapitalAllocator(total_budget=100000.0)

# Register a strategy
gold_ppo_config = StrategyConfig(
    strategy_id="gold_ppo_v1",
    symbol="XAUUSD",
    model_family="RL",
    capital_cap=20000.0,
    performance_multiplier=1.2
)
allocator.add_strategy(gold_ppo_config)

# Request allocation (1% risk) with scaling allowed
result = allocator.request_allocation("gold_ppo_v1", 0.01, allow_scaling=True)

if result.is_allowed:
    print(f"Allocated {result.allocated_amount} ({result.allocated_risk_pct * 100}%)")
    if result.was_capped:
        print("Allocation was capped by portfolio limits.")
    # Update current allocation after placing trade
    allocator.update_allocation("gold_ppo_v1", result.allocated_amount)
else:
    print(f"Rejected: {result.rejection_reason} (Code: {result.rejection_code})")

# Get Portfolio Diversification Score
score = allocator.get_diversification_score()
print(f"Portfolio Diversification Score: {score:.2f}")

# After trade closes
allocator.update_strategy_performance("gold_ppo_v1", 500.0) # Profitable trade
allocator.update_allocation("gold_ppo_v1", 0.0) # Reset allocation
```

### Batch Allocation Example

```python
from src.trading.capital_allocator import CapitalAllocator, AllocationRequest

allocator = CapitalAllocator(total_budget=100000.0)
# ... register multiple strategies (e.g., s1, s2, s3) ...

# Create a batch of requests
requests = [
    AllocationRequest(strategy_id="s1", risk_pct=0.02, allow_scaling=True),
    AllocationRequest(strategy_id="s2", risk_pct=0.015, allow_scaling=True),
    AllocationRequest(strategy_id="s3", risk_pct=0.01, allow_scaling=False)
]

# Process the batch (prioritizes by performance_multiplier automatically)
results = allocator.allocate_batch(requests)

for res in results:
    if res.is_allowed:
        print(f"Strategy {res.strategy_id} allocated ${res.allocated_amount:.2f}")
    else:
        print(f"Strategy {res.strategy_id} rejected: {res.rejection_reason}")
```

## Integration with Risk Engine

The `CapitalAllocator` serves as a high-level capital router that works alongside the `RiskManager`. While the `RiskManager` handles per-trade validation (e.g., SL/TP, daily loss limits), the `CapitalAllocator` manages the broader distribution of capital across the entire trading system.
