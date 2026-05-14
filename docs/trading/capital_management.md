# Institutional Capital Management

The MT5 AI/ML Trading Bot utilizes an institutional-grade capital management system implemented in `src/trading/capital_allocator.py`. This system ensures disciplined risk distribution, portfolio diversification, and automatic safety intervention.

## Core Features

### 1. Adaptive Budget Allocation
Risk is dynamically adjusted for each strategy or model family using two primary multipliers:
- **Performance Multiplier**: Automatically scales risk (0.0x to 2.0x) based on historical strategy PnL. Profitable strategies receive more capital, while losing streaks trigger a "cooling-off" period.
- **Regime Multiplier**: Adjusts risk based on current market conditions detected by the `RegimeDetector`. For example, risk is significantly reduced during `NEWS_SHOCK` events and slightly increased during `LOW_VOLATILITY_DRIFT`.

### 2. Strategy-Level Circuit Breakers
Each strategy tracks its own drawdown relative to its capital cap and peak PnL.
- **Max Drawdown Limit**: If a strategy's drawdown exceeds the configured limit (default 15%), it is automatically halted (`performance_multiplier` set to 0) until manual intervention or recovery.

### 3. Portfolio Heat Tracking
The allocator maintains a real-time view of committed capital ("heat"):
- **Total Heat**: Maximum 70% of total budget committed across all strategies.
- **Symbol Concentration**: Maximum 40% of budget per symbol (e.g., XAUUSD).
- **Family Concentration**: Maximum 40% of budget per model family (e.g., RL, LSTM).

### 4. Diversification Awareness
The system calculates a **Diversification Score** using a multi-factor normalized Herfindahl-Hirschman Index (HHI). This score considers:
- Strategy-level concentration (40% weight)
- Symbol-level concentration (30% weight)
- Family-level concentration (30% weight)

When routing allocations for a symbol, the system selects the strategy that results in the highest portfolio diversification score.

## Configuration

Settings are managed via `TradingConfig` (environment variables):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ALLOCATOR_MAX_TOTAL_HEAT` | 0.70 | Max % of budget committed at once |
| `ALLOCATOR_MAX_SYMBOL_RISK` | 0.40 | Max % of budget per symbol |
| `ALLOCATOR_MAX_FAMILY_RISK` | 0.40 | Max % of budget per model family |
| `ALLOCATOR_PERFORMANCE_STEP`| 0.05 | Multiplier adjustment per trade |
| `ALLOCATOR_DECAY_RATE` | 0.001 | Daily normalization rate toward 1.0 |

## Integration with Trading Loop

The `CapitalAllocator` is tightly integrated with the `RiskManager` and `main.py`:
1. `main.py` requests allocation for a strategy.
2. `CapitalAllocator` returns an `AllocationResult` with the scaled risk percentage.
3. `RiskManager` uses this scaled percentage to calculate the final lot size using the Kelly Criterion.
4. On trade entry, notional heat is updated in the allocator.
5. On trade exit, PnL is reported back to update performance multipliers and drawdown metrics.
