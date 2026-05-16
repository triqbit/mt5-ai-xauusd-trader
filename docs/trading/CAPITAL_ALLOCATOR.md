# Institutional Capital Management

The `CapitalAllocator` system (src/trading/capital_allocator.py) provides institutional-grade capital management for multi-strategy and multi-symbol trading environments.

## Key Features

- **Portfolio Heat Tracking:** Monitors the total committed capital ratio across the entire portfolio.
- **Diversification Guard:** Implements normalized Herfindahl-Hirschman Index (HHI) for diversification scoring and applies linear scaling as risk limits are approached.
- **Adaptive Sizing:** Utilizes performance multipliers to reward winning strategies and apply cooling-off floors to losing ones.
- **Concentration Limits:** Enforces hard safety limits on a per-symbol and per-model-family basis.
- **Dynamic Budgeting:** Supports real-time updates to the total trading budget via `update_budget`.
- **Granular Rejection Tracking:** Provides detailed feedback through typed `AllocationResult` and programmatic `RejectionCode` (e.g., `SCALED_TO_ZERO`, `TOTAL_HEAT_LIMIT`, `NO_BUDGET`).

## Technical Components

### Strategy Configuration
Each strategy or model family is registered with a `StrategyConfig` that defines:
- `capital_cap`: Maximum absolute capital allowed.
- `max_allocation_pct`: Maximum fraction of total budget this strategy can use (default: 0.2).
- `performance_multiplier`: Dynamic scaling factor based on historical performance.
- `max_consecutive_losses`: Threshold for the automated cooling-off mechanism.

### Allocation Workflow
1. **Performance Scaling:** Requested risk is first scaled by the strategy's current performance multiplier.
2. **Cap Enforcement:** The scaled amount is capped at the strategy's `capital_cap`.
3. **Strategy-Level Limit:** The allocation is checked against the strategy-specific `max_allocation_pct` and the global `allocator_max_strategy_risk`.
4. **Diversification Guard:** If approaching total heat, symbol, family, or strategy limits, the allocation is linearly scaled down within a configurable `soft_limit_buffer`.
5. **Hard Limit Verification:** A final check ensures no absolute safety limits (total heat, symbol, family, or strategy concentration) are violated.

### Diversification Scoring
The system calculates a diversification score (0.0 to 1.0) based on strategy concentration:
- `1.0`: Perfectly balanced across all registered strategies.
- `0.0`: Fully concentrated in a single strategy.

## Usage

### Adding a Strategy
```python
from src.trading import CapitalAllocator, StrategyConfig

allocator = CapitalAllocator(total_budget=100000.0)
config = StrategyConfig(
    strategy_id="gold_rl_v1",
    symbol="XAUUSD",
    model_family="RL",
    capital_cap=50000.0
)
allocator.add_strategy(config)
```

### Requesting Allocation
```python
# Standard request
result = allocator.request_allocation("gold_rl_v1", risk_pct=0.01)

# Request with scaling (returns max possible if limit hit)
result = allocator.request_allocation("gold_rl_v1", risk_pct=0.05, allow_scaling=True)

if result.is_allowed:
    # Proceed with order execution using result.allocated_amount
    allocator.update_allocation("gold_rl_v1", result.allocated_amount)
```

### Optimal Routing
The `route_allocation` method selects the best strategy for a given symbol by evaluating the diversification impact (HHI) of each candidate. If multiple strategies result in the same diversification score, it uses the `performance_multiplier` as a tie-breaker.

```python
result = allocator.route_allocation("XAUUSD", risk_pct=0.01)
```

### Monitoring Allocations
Use `get_active_allocations()` to retrieve a map of currently utilized capital.

```python
active = allocator.get_active_allocations()
# {'gold_rl_v1': 1250.0, 'eur_lstm_v2': 800.0}
```

### Updating Performance
```python
# After a trade closes
allocator.update_strategy_performance("gold_rl_v1", pnl=500.0)
allocator.release_allocation("gold_rl_v1")
```

## Institutional Feedback Loop

The system implements an automated feedback loop between trade execution and capital allocation. When a position is closed in `main.py`, the realized PnL is retrieved from the `TradeLogger` and fed back into the `CapitalAllocator`.

This loop ensures:
- **Winning strategies** gain increased risk allocation (capped at 2.0x baseline).
- **Losing strategies** face reduced risk exposure.
- **Systemic failures** trigger a "Cooling-off" floor (risk reduced to 0.1x) after a streak of consecutive losses.

This behavior is verified by the end-to-end integration test `tests/test_institutional_feedback_loop.py`.
