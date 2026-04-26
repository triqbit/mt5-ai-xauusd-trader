"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorized walk-forward backtesting engine.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.config import TradingConfig
from src.core.feature_engineering import FeatureEngineer
from src.models.ensemble import EnsembleModel
from src.trading.execution_filter import ExecutionFilter

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Performance metrics matching README.md benchmarks."""
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    win_rate_pct: float
    total_trades: int
    avg_mae_pct: float
    avg_mfe_pct: float


class Backtester:
    """
    Vectorized backtesting engine supporting walk-forward analysis.
    Simulates transaction costs, MAE/MFE, and produces standard reports.
    """

    def __init__(
        self,
        config: TradingConfig,
        model: EnsembleModel,
        feature_engineer: FeatureEngineer,
        spread: float = 0.2,  # Typical Gold spread in USD
        commission: float = 7.0,  # USD per round-turn lot
    ) -> None:
        self.cfg = config
        self.model = model
        self.fe = feature_engineer
        self.spread = spread
        self.commission = commission
        self.filter = ExecutionFilter(timeframe=config.timeframe)

    def run_walk_forward(
        self,
        data: Dict[str, pd.DataFrame],
        train_window_days: int = 180,
        test_window_days: int = 30,
        initial_balance: float = 10000.0,
    ) -> PerformanceReport:
        """
        Execute walk-forward analysis.
        """
        all_trades = []
        equity_curves = []
        current_balance = initial_balance

        # Get total date range from base timeframe
        base_df = data[self.cfg.timeframe]
        start_date = base_df["time"].min()
        end_date = base_df["time"].max()

        current_test_start = start_date + timedelta(days=train_window_days)

        while current_test_start < end_date:
            current_test_end = current_test_start + timedelta(days=test_window_days)

            logger.info("Walk-forward window | Test: %s to %s",
                        current_test_start.date(), current_test_end.date())

            # Slice data for this window
            window_data = {
                tf: df[(df["time"] >= current_test_start - timedelta(days=30)) &
                       (df["time"] < current_test_end)]
                for tf, df in data.items()
            }

            # Run backtest for this slice
            _, window_trades, window_equity = self.run_vectorized(
                window_data,
                initial_balance=current_balance,
                start_ts=current_test_start
            )

            all_trades.extend(window_trades)
            equity_curves.append(window_equity)
            if not window_equity.empty:
                current_balance = window_equity.iloc[-1]

            current_test_start = current_test_end

        # Merge results
        if not equity_curves:
            return self._empty_report()

        full_equity = pd.concat(equity_curves)
        return self._calculate_metrics(full_equity, all_trades, initial_balance)

    def run_vectorized(
        self,
        data: Dict[str, pd.DataFrame],
        initial_balance: float = 10000.0,
        start_ts: Optional[datetime] = None
    ) -> Tuple[PerformanceReport, List[Dict], pd.Series]:
        """
        Run a vectorized backtest on a slice of data.
        """
        # 1. Feature Engineering
        features_df = self.fe.generate_features(data)
        if features_df.empty:
            return self._empty_report(), [], pd.Series()

        if start_ts:
            features_df = features_df[features_df.index >= start_ts]

        if features_df.empty:
             return self._empty_report(), [], pd.Series()

        # 2. Vectorized Signal Generation
        obs_matrix = features_df.values
        directions = []
        for obs in obs_matrix:
            d, _, _ = self.model.predict(obs)
            directions.append(d)

        signals = pd.Series(directions, index=features_df.index)

        # 3. Apply Execution Filter (Vectorized where possible)
        # Layer: Session Filter
        hours = signals.index.hour
        session_mask = (hours >= 8) & (hours < 21)
        signals[~session_mask] = 0

        # 4. P&L Simulation
        base_df = data[self.cfg.timeframe].set_index("time").reindex(features_df.index)
        close = base_df["close"]
        high = base_df["high"]
        low = base_df["low"]

        trades = []
        equity = pd.Series(initial_balance, index=features_df.index)
        balance = initial_balance

        active_trade = None

        for ts, sig in signals.items():
            price = close.loc[ts]

            if active_trade:
                # Update MAE/MFE
                if active_trade["direction"] == 1:
                    mfe = max(active_trade["mfe"], high.loc[ts] - active_trade["entry_price"])
                    mae = min(active_trade["mae"], low.loc[ts] - active_trade["entry_price"])
                else:
                    mfe = max(active_trade["mfe"], active_trade["entry_price"] - low.loc[ts])
                    mae = min(active_trade["mae"], active_trade["entry_price"] - high.loc[ts])

                active_trade["mfe"] = mfe
                active_trade["mae"] = mae

                # Exit logic
                atr = features_df.loc[ts].get(f"{self.cfg.timeframe}_atr_14", 1.0)
                sl = active_trade["entry_price"] - active_trade["direction"] * 2 * atr
                tp = active_trade["entry_price"] + active_trade["direction"] * 4 * atr

                is_exit = False
                exit_price = price

                if active_trade["direction"] == 1:
                    if low.loc[ts] <= sl:
                        exit_price = sl
                        is_exit = True
                    elif high.loc[ts] >= tp:
                        exit_price = tp
                        is_exit = True
                else:
                    if high.loc[ts] >= sl:
                        exit_price = sl
                        is_exit = True
                    elif low.loc[ts] <= tp:
                        exit_price = tp
                        is_exit = True

                if is_exit:
                    pnl = (exit_price - active_trade["entry_price"]) * active_trade["direction"] * active_trade["lots"] * 100
                    pnl -= self.commission * active_trade["lots"]
                    balance += pnl
                    active_trade["exit_time"] = ts
                    active_trade["exit_price"] = exit_price
                    active_trade["pnl"] = pnl
                    trades.append(active_trade)
                    active_trade = None

            if not active_trade and sig != 0:
                # Entry
                entry_price = price + (sig * self.spread / 2)
                active_trade = {
                    "entry_time": ts,
                    "direction": sig,
                    "entry_price": entry_price,
                    "lots": 0.1,
                    "mfe": 0.0,
                    "mae": 0.0
                }

            equity.loc[ts] = balance

        report = self._calculate_metrics(equity, trades, initial_balance)
        return report, trades, equity

    def _calculate_metrics(
        self,
        equity_series: pd.Series,
        trades: List[Dict],
        initial_balance: float
    ) -> PerformanceReport:
        if not trades:
            return self._empty_report()

        pnls = np.array([t["pnl"] for t in trades])
        maes = np.array([abs(t["mae"]) / t["entry_price"] * 100 for t in trades])
        mfes = np.array([t["mfe"] / t["entry_price"] * 100 for t in trades])

        total_return = (equity_series.iloc[-1] - initial_balance) / initial_balance

        # Annualization
        timespan = (equity_series.index[-1] - equity_series.index[0]).total_seconds() / (365 * 24 * 3600)
        ann_return = ((1 + total_return)**(1/timespan) - 1) if timespan > 0 and total_return > -1 else 0.0

        # Sharpe
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 288)) if returns.std() > 0 else 0.0

        # Drawdown
        peak = equity_series.cummax()
        dd = (equity_series - peak) / peak
        max_dd = abs(dd.min())

        # Profit Factor
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 100.0

        win_rate = len(pnls[pnls > 0]) / len(pnls)

        return PerformanceReport(
            total_return_pct=total_return * 100,
            annualized_return_pct=ann_return * 100,
            sharpe_ratio=float(sharpe),
            max_drawdown_pct=max_dd * 100,
            profit_factor=float(profit_factor),
            win_rate_pct=win_rate * 100,
            total_trades=len(trades),
            avg_mae_pct=float(np.mean(maes)),
            avg_mfe_pct=float(np.mean(mfes))
        )

    def _empty_report(self) -> PerformanceReport:
        return PerformanceReport(0, 0, 0, 0, 0, 0, 0, 0, 0)


__all__ = ["Backtester", "PerformanceReport"]
