# Capital Allocation System

The Capital Allocator provides institutional-grade capital management across multiple strategies and model families. It ensures that portfolio risk is well-distributed and that individual strategies are scaled based on their performance.

## Overview

In a multi-strategy environment, the Capital Allocator acts as a central authority for budget distribution. It prevents over-concentration in any single symbol or model family and dynamically adjusts capital based on real-world performance metrics.

## Key Features

### 1. Portfolio Heat Tracking
Monitors the total committed capital (portfolio "heat") across all active strategies. It ensures the total exposure remains within safe limits (default 70% of total budget).

### 2. Concentration Limits
Enforces safety caps to prevent "putting all eggs in one basket":
- **Symbol Concentration:** Limits risk per individual symbol (e.g., max 40% of budget in XAUUSD).
- **Family Concentration:** Limits risk per model family (e.g., max 40% in Reinforcement Learning models).

### 3. Adaptive Budgeting
Uses a **Performance Multiplier** to scale requested risk:
- **Win Streaks:** Increases the multiplier (up to 2.0x) allowing profitable strategies to trade larger sizes.
- **Loss Streaks:** Decreases the multiplier.
- **Cooling-off:** If a strategy hits a maximum consecutive loss threshold (default 5), its multiplier is immediately floored (default 0.1) to protect capital.

### 4. Multi-Factor Diversification
The system utilizes a weighted multi-factor diversification score based on the Herfindahl-Hirschman Index (HHI). It tracks concentration across three dimensions:
- **Strategy-level (40%):** Ensures risk is spread across specific model instances.
- **Symbol-level (30%):** Prevents over-exposure to a single asset (e.g. XAUUSD).
- **Family-level (30%):** Prevents architectural concentration (e.g. relying solely on RL agents).

### 5. Silent Simulation Mode
The `request_allocation` method supports a `silent` flag, which allows the `route_allocation` logic to simulate potential risk distributions without polluting the production audit log or triggering metrics. This is critical for finding the most optimal strategy to route a signal to while maintaining a clean audit trail.

### 6. Linear Soft-Scaling
Instead of hard rejections when approaching limits, the allocator can linearly scale down requests as they enter a "buffer zone" near the hard limits.

### 7. State Persistence
Performance multipliers and PnL metrics are persisted to JSON, ensuring that the system's "memory" of strategy performance survives restarts.

### 8. Institutional Audit Trail
Every allocation decision (Allowed, Capped, or Rejected) is recorded in the system audit log with specific rejection codes for compliance and debugging.

## Usage

```python
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
from src.core.config import get_config

cfg = get_config()
allocator = CapitalAllocator.from_config(cfg, total_budget=100000.0)

# Register a strategy
allocator.add_strategy(StrategyConfig(
    strategy_id="gold_ppo_v1",
    symbol="XAUUSD",
    model_family="RL",
    capital_cap=50000.0
))

# Request 1% risk
result = allocator.request_allocation("gold_ppo_v1", 0.01)
if result.is_allowed:
    print(f"Allocated: ${result.allocated_amount}")
```
