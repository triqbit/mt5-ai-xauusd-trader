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
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.core.config import TradingConfig
    from src.core.feature_engineering import FeatureEngineer
    from src.models.base_model import BaseModel
    from src.trading.execution_filter import ExecutionFilter

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Institutional-grade backtest performance report."""

    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    win_rate: float
    mae: float  # Mean Maximum Adverse Excursion
    mfe: float  # Mean Maximum Favorable Excursion
    total_pnl: float
    starting_balance: float
    ending_balance: float


class BacktestEngine:
    """
    Vectorized walk-forward backtesting engine for MT5 AI/ML Bot.
    Consumes the same feature engineering and execution filter as live trading.
    """

    def __init__(
        self,
        config: TradingConfig,
        feature_engineer: FeatureEngineer,
        execution_filter: ExecutionFilter,
        starting_balance: float = 10000.0,
        spread: float = 1.0,  # in price units
        commission: float = 0.0,  # per lot
    ) -> None:
        self.cfg = config
        self.fe = feature_engineer
        self.ef = execution_filter
        self.starting_balance = starting_balance
        self.spread = spread
        self.commission = commission

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        model: BaseModel,
        train_window_bars: int = 2000,
        test_window_bars: int = 500,
    ) -> PerformanceReport:
        """
        Executes a walk-forward backtest.
        """
        logger.info(
            "Starting walk-forward backtest | total_bars=%d train_window=%d test_window=%d",
            len(data),
            train_window_bars,
            test_window_bars,
        )

        all_trades_dfs = []
        total_bars = len(data)

        for start_idx in range(
            0, total_bars - train_window_bars - test_window_bars, test_window_bars
        ):
            test_start = start_idx + train_window_bars
            test_end = test_start + test_window_bars

            lookback = 300
            process_start = max(0, test_start - lookback)
            segment_data = data.iloc[process_start:test_end]

            features = self.fe.compute_features(segment_data)
            test_data = data.iloc[test_start:test_end]
            test_features = features.reindex(test_data.index).dropna()

            if test_features.empty:
                continue

            # Optimization: Call predict once and unpack
            preds_conf = test_features.apply(lambda row: model.predict(row.values), axis=1)
            predictions = preds_conf.apply(lambda x: x.direction)
            confidences = preds_conf.apply(lambda x: x.confidence)

            approved_signals = self._vectorized_execution_filter(
                test_data, predictions, confidences
            )

            if approved_signals.any():
                segment_trades = self._vectorized_simulation(test_data, approved_signals)
                all_trades_dfs.append(segment_trades)

        if not all_trades_dfs:
            return self._empty_report()

        combined_trades = pd.concat(all_trades_dfs)
        return self._generate_report(combined_trades)

    def _vectorized_execution_filter(
        self, test_data: pd.DataFrame, predictions: pd.Series, confidences: pd.Series
    ) -> pd.Series:
        """
        Apply execution filter rules using vectorized operations.
        """
        signals = predictions != 0
        signals &= confidences >= self.cfg.confidence_threshold

        times = test_data.index
        weekdays = times.weekday
        hours = times.hour

        # Sun 17:00 - Fri 16:00 GMT
        is_weekend = (
            (weekdays == 5) | ((weekdays == 6) & (hours < 17)) | ((weekdays == 4) & (hours >= 16))
        )
        signals &= ~is_weekend

        return predictions.where(signals, 0)

    def _vectorized_simulation(self, test_data: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
        trades_indices = signals[signals != 0].index
        if trades_indices.empty:
            return pd.DataFrame()

        trade_data = []
        hold_bars = 12

        for entry_time in trades_indices:
            direction = signals[entry_time]
            entry_idx = test_data.index.get_loc(entry_time)
            exit_idx = min(entry_idx + hold_bars, len(test_data) - 1)

            window = test_data.iloc[entry_idx : exit_idx + 1]
            entry_price = window.iloc[0]["close"]
            exit_price = window.iloc[-1]["close"]

            raw_pnl = (exit_price - entry_price) * direction
            cost = self.spread + (self.commission * 0.01)
            net_pnl = raw_pnl - cost

            if direction == 1:
                mfe = window["high"].max() - entry_price
                mae = entry_price - window["low"].min()
            else:
                mfe = entry_price - window["low"].min()
                mae = window["high"].max() - entry_price

            trade_data.append(
                {
                    "entry_time": entry_time,
                    "exit_time": window.index[-1],
                    "direction": direction,
                    "pnl": net_pnl,
                    "mae": mae,
                    "mfe": mfe,
                }
            )

        return pd.DataFrame(trade_data)

    def _generate_report(self, trades_df: pd.DataFrame) -> PerformanceReport:
        trades_df = trades_df.sort_values("entry_time")
        trades_df["cum_pnl"] = trades_df["pnl"].cumsum()
        trades_df["equity"] = self.starting_balance + trades_df["cum_pnl"]

        total_pnl = trades_df["pnl"].sum()
        ending_balance = self.starting_balance + total_pnl

        equity_series = trades_df.set_index("exit_time")["equity"]
        daily_equity = equity_series.resample("D").last().ffill()
        daily_returns = daily_equity.pct_change().dropna()

        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        peak = trades_df["equity"].expanding().max()
        drawdown = (peak - trades_df["equity"]) / peak
        max_dd = drawdown.max()

        gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        win_rate = (trades_df["pnl"] > 0).mean()

        duration_days = (trades_df["exit_time"].max() - trades_df["entry_time"].min()).days
        if duration_days > 30:
            ann_return = (ending_balance / self.starting_balance) ** (365 / duration_days) - 1
        else:
            ann_return = total_pnl / self.starting_balance

        return PerformanceReport(
            annualized_return=float(ann_return),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            profit_factor=float(profit_factor),
            total_trades=len(trades_df),
            win_rate=float(win_rate),
            mae=float(trades_df["mae"].mean()),
            mfe=float(trades_df["mfe"].mean()),
            total_pnl=float(total_pnl),
            starting_balance=self.starting_balance,
            ending_balance=ending_balance,
        )

    def _empty_report(self) -> PerformanceReport:
        return PerformanceReport(
            0, 0, 0, 0, 0, 0, 0, 0, 0, self.starting_balance, self.starting_balance
        )
