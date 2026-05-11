# Institutional Backtesting Engine

The MT5 AI Trading Bot includes a high-performance, vectorized walk-forward backtesting engine designed to provide institutional-grade performance validation.

## Features

- **Vectorized Execution:** High-speed simulation of trade entries and exits using NumPy and Pandas.
- **Walk-Forward Validation:** Support for rolling window training and testing to prevent curve-fitting and ensure out-of-sample robustness.
- **Realistic Transaction Costs:** Accurate simulation of fixed and variable spreads, along with per-lot commissions.
- **Advanced Metrics:**
  - **MAE (Maximum Adverse Excursion):** Measures the maximum unrealized loss during a trade.
  - **MFE (Maximum Favorable Excursion):** Measures the maximum unrealized profit during a trade.
- **Institutional Reporting:** Detailed PerformanceReport including Annualized Return, Sharpe Ratio, Max Drawdown, and Profit Factor, matching industry benchmarks.
- **Pipeline Parity:** Uses the exact same Feature Engineering and Execution Filter components as live trading, ensuring "backtest-to-live" fidelity.

## Usage

To run a backtest, use the CLI command:

```bash
python main.py --mode backtest --symbol XAUUSD --start 2024-01-01 --end 2024-01-10
```

## Configuration

Parameters such as `train-window`, `test-window`, `step-size`, `spread`, and `commission` can be configured via CLI flags or the `.env` file.
