# Walk-Forward Backtesting Engine

The MT5 AI/ML Trading Bot includes a high-performance, efficient walk-forward backtesting engine designed to simulate institutional trading conditions for the XAUUSD market.

## Features

- **Walk-Forward Analysis:** Supports rolling train/test windows to validate model robustness over time.
- **Efficient Simulation:** Features and technical indicators are pre-calculated for the entire dataset to maximize performance.
- **Realistic Transaction Costs:** Incorporates spread and commission costs into P&L calculations.
- **Institutional Metrics:** Calculates key performance indicators including:
  - Annualized Return
  - Sharpe Ratio
  - Max Drawdown
  - Profit Factor
  - Win Rate
  - Maximum Adverse Excursion (MAE)
  - Maximum Favorable Excursion (MFE)
- **Position Management:** Respects `max_positions` constraints to match live trading behavior.
- **Unified Pipeline:** Consumes the same `FeatureEngineer` and `ExecutionFilter` as the live trading loop.

## Usage

To run a backtest, use the `--mode backtest` flag with `main.py`:

```bash
python main.py --mode backtest --start 2024-01-01 --end 2024-03-30 --algo ensemble
```

### Configurable Parameters

- `--start`: Start date for the backtest (YYYY-MM-DD).
- `--end`: End date for the backtest (YYYY-MM-DD).
- `--train-window`: Size of the training window (default: 500 bars).
- `--test-window`: Size of the testing window (default: 100 bars).
- `--step-size`: Step size for the sliding windows (default: 100 bars).

## Implementation Details

The engine is implemented in `src/trading/backtester.py`. It uses a highly optimized $O(N)$ simulation loop where all technical indicators and execution filter metrics are pre-calculated using vectorized NumPy operations before entering the walk-forward cycle.

- `BacktestEngine`: The core engine class.
- `PerformanceReport`: Dataclass containing the final backtest results.
- `BacktestTrade`: Records individual trade details during the simulation.
