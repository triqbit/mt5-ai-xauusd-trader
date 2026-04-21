"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorised walk-forward backtesting engine.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

import numpy as np
import pandas as pd

from src.models.base_model import BaseModel
from src.trading.execution_filter import ExecutionFilter
from src.trading.feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Matches benchmark table in README.md."""

    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    win_rate: float


@dataclass
class TradeRecord:
    entry_time: datetime
    exit_time: datetime
    direction: int
    entry_price: float
    exit_price: float
    pnl: float
    mae: float  # Maximum Adverse Excursion
    mfe: float  # Maximum Favorable Excursion


class Backtester:
    """
    Vectorised walk-forward backtesting engine with transaction cost simulation.
    """

    def __init__(
        self,
        model: BaseModel,
        symbol: str = "XAUUSD",
        initial_balance: float = 10000.0,
        spread: float = 0.2,  # in points/pips
        commission: float = 0.0,
        lot_size: float = 0.1,
    ) -> None:
        self.model = model
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission = commission
        self.lot_size = lot_size
        self.fe = FeatureEngineer()
        self.ef = ExecutionFilter()

    def run(
        self,
        df_raw: pd.DataFrame,
        train_window: int = 1000,
        test_window: int = 200,
        use_walk_forward: bool = True,
    ) -> PerformanceReport:
        """
        Run vectorized walk-forward backtest.
        """
        logger.info("Starting backtest | symbol=%s total_bars=%d", self.symbol, len(df_raw))

        # 1. Feature Engineering
        df = self.fe.generate_features(df_raw)

        if not use_walk_forward:
            return self._run_window(df)

        # 2. Walk-forward Execution
        all_trades: List[TradeRecord] = []

        # Windows logic:
        # [Train Window (for normalization mu/sigma)] -> [Test Window (Actual Trading)]
        # Shift both by test_window

        start_idx = train_window
        while start_idx + test_window <= len(df):
            train_df = df.iloc[start_idx - train_window : start_idx]
            test_df = df.iloc[start_idx : start_idx + test_window]

            # Use training stats for test window normalization (avoid look-ahead)
            mu = train_df.mean()
            sigma = train_df.std() + 1e-8

            test_df_norm = (test_df - mu) / sigma

            # Run simulation on this window
            window_trades = self._simulate_trading(df.iloc[: start_idx + test_window], test_df_norm)
            all_trades.extend(window_trades)

            start_idx += test_window

        return self._calculate_metrics(all_trades)

    def _simulate_trading(
        self, df_full: pd.DataFrame, df_test_norm: pd.DataFrame
    ) -> List[TradeRecord]:
        """
        Simulate trading over a normalized test window.
        Uses a fast loop but signals can be vectorized if model supports it.
        """
        trades: List[TradeRecord] = []
        current_pos = 0
        entry_price = 0.0
        entry_idx = -1
        peak_pnl = 0.0
        trough_pnl = 0.0

        # Vectorized signal generation for the whole test window
        # features = df_test_norm.values
        # This assumes the model.predict is fast or can take batches (not yet in BaseModel)

        for i in range(len(df_test_norm)):
            idx_in_full = df_full.index.get_loc(df_test_norm.index[i])
            row = df_full.iloc[idx_in_full]
            norm_row = df_test_norm.iloc[i]

            if current_pos != 0:
                price = row["close"]
                unrealized_pnl = (price - entry_price) * current_pos * self.lot_size * 100
                peak_pnl = max(peak_pnl, unrealized_pnl)
                trough_pnl = min(trough_pnl, unrealized_pnl)

                signal = self.model.predict(norm_row.values)
                if signal.direction != current_pos:
                    # Close
                    exit_price = row["close"] - (
                        self.spread / 2.0 if current_pos == 1 else -self.spread / 2.0
                    )
                    realized_pnl = (
                        exit_price - entry_price
                    ) * current_pos * self.lot_size * 100 - self.commission
                    trades.append(
                        TradeRecord(
                            entry_time=df_full.index[entry_idx],
                            exit_time=df_test_norm.index[i],
                            direction=current_pos,
                            entry_price=entry_price,
                            exit_price=exit_price,
                            pnl=realized_pnl,
                            mae=trough_pnl,
                            mfe=peak_pnl,
                        )
                    )
                    current_pos = 0

            if current_pos == 0:
                signal = self.model.predict(norm_row.values)
                if signal.direction != 0:
                    # Use bar time for session filter
                    decision = self.ef.validate(
                        self.symbol,
                        signal.direction,
                        df_full.iloc[: idx_in_full + 1],
                        timestamp=df_test_norm.index[i],
                    )
                    if decision.approved:
                        current_pos = signal.direction
                        entry_price = row["close"] + (
                            self.spread / 2.0 if current_pos == 1 else -self.spread / 2.0
                        )
                        entry_idx = idx_in_full
                        peak_pnl = 0.0
                        trough_pnl = 0.0

        return trades

    def _calculate_metrics(self, trades: List[TradeRecord]) -> PerformanceReport:
        if not trades:
            return PerformanceReport(0, 0, 0, 0, 0, 0)

        pnls = np.array([t.pnl for t in trades])
        total_pnl = pnls.sum()

        # Annualized Return
        duration = trades[-1].exit_time - trades[0].entry_time
        years = duration.days / 365.25 or 1 / 365.25
        annualized_return = (total_pnl / self.initial_balance) / years

        # Sharpe Ratio
        if len(pnls) > 1:
            sharpe = (pnls.mean() / (pnls.std() + 1e-9)) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown
        equity_curve = self.initial_balance + np.cumsum(pnls)
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        max_dd = drawdown.max()

        # Profit Factor
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        win_rate = len(pnls[pnls > 0]) / len(pnls)

        return PerformanceReport(
            annualized_return=annualized_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            total_trades=len(trades),
            win_rate=win_rate,
        )
