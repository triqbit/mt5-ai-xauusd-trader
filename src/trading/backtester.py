"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Institutional-grade vectorized walk-forward backtesting engine.
Supports transaction costs, MAE/MFE, and time-aware execution filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Institutional-grade performance summary matching README.md benchmarks."""
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    win_rate: float
    total_net_pnl: float
    avg_mae: float  # Maximum Adverse Excursion
    avg_mfe: float  # Maximum Favorable Excursion
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class BacktestEngine:
    """
    Vectorized and event-driven hybrid backtester for XAUUSD.
    Features:
    - Walk-forward window support
    - Realistic transaction costs (spread + commission + slippage)
    - Path-dependent metrics (MAE/MFE)
    - Integration with live FeatureEngineer and ExecutionFilter
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        spread_points: float = 20,  # 20 points = 0.20 USD for XAUUSD
        commission_per_lot: float = 7.0,
        slippage_points: float = 5,
    ) -> None:
        self.initial_balance = initial_balance
        self.spread = spread_points * 0.01
        self.commission = commission_per_lot
        self.slippage = slippage_points * 0.01

        self.fe = FeatureEngineer()
        self.filter = ExecutionFilter()

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        model: Any,
        train_bars: int = 2000,
        test_bars: int = 500,
    ) -> PerformanceReport:
        """
        Execute a walk-forward backtest by sliding train/test windows.
        """
        if len(df) < train_bars + test_bars:
            logger.warning("Data length %d shorter than WF window %d. Running single pass.", len(df), train_bars + test_bars)
            return self.run(df, model)

        all_trades: List[Dict] = []
        full_equity_curve: List[float] = [self.initial_balance]
        current_balance = self.initial_balance

        # Walk-forward loop
        for start_idx in range(0, len(df) - train_bars, test_bars):
            test_start = start_idx + train_bars
            test_end = min(test_start + test_bars, len(df))

            # In a full implementation, the model would be retrained on df.iloc[start_idx:test_start]
            test_df = df.iloc[test_start : test_end]
            if test_df.empty:
                break

            logger.debug("WF Window | Test: %s to %s", test_df.index[0], test_df.index[-1])

            _, trades, equity = self._simulate(test_df, model, current_balance)

            if trades:
                all_trades.extend(trades)
                # Stitch equity curve (skip first element as it's the previous balance)
                full_equity_curve.extend(equity[1:])
                current_balance = equity[-1]
            else:
                # If no trades, equity remains flat for the period
                full_equity_curve.extend([current_balance] * len(test_df))

        return self._calculate_metrics(all_trades, full_equity_curve, df.index[0], df.index[-1])

    def run(self, df: pd.DataFrame, model: Any) -> PerformanceReport:
        """Standard single-pass backtest."""
        report, _, _ = self._simulate(df, model, self.initial_balance)
        return report

    def _simulate(
        self,
        df: pd.DataFrame,
        model: Any,
        initial_balance: float
    ) -> Tuple[PerformanceReport, List[Dict], List[float]]:
        """Core simulation engine."""
        if df.empty:
            return self._empty_report(), [], [initial_balance]

        # 1. Generate Features
        df_features = self.fe.generate_features(df)
        feature_names = self.fe.get_feature_names()
        obs_matrix = df_features[feature_names].values

        # 2. Simulation State
        balance = initial_balance
        trades = []
        equity_curve = [balance]
        timestamps = df_features.index

        current_pos: Optional[dict] = None

        # 3. Main Loop (Event-driven for path-dependent metrics)
        for i in range(len(df_features)):
            row = df_features.iloc[i]
            ts = timestamps[i]

            # Get Signal
            direction, confidence, _ = model.predict(obs_matrix[i])

            if direction != 0:
                signal = TradeSignal(
                    symbol="XAUUSD",
                    direction=direction,
                    entry_price=row["close"],
                    stop_loss=0.0,
                    take_profit=0.0,
                    lot_size=0.1,
                    algorithm="ensemble",
                    confidence=confidence,
                    timestamp=ts
                )

                # Execution Filter Gate
                hist_slice = df_features.iloc[max(0, i-200):i+1]
                decision = self.filter.validate(signal, hist_slice, timestamp=ts)

                if decision.is_approved:
                    # Transaction Cost: (Spread + Slippage) in points * multiplier + Commission
                    # For XAUUSD, 0.1 lot, multiplier 10 (1 point = 0.01 USD, 0.1 lot = 1 USD per USD move)
                    # So 1 point move (0.01) on 0.1 lot = 0.01 * 100 * 0.1 = 0.10 USD?
                    # MT5 XAUUSD: 1 lot = 100oz. 0.01 price move = 1 USD profit.
                    # So 0.1 lot = 0.10 USD profit per 0.01 move.
                    cost = (self.spread + self.slippage) * 10 + (self.commission * 0.1)

                    # Exit and Flip Logic
                    if current_pos and current_pos["dir"] != direction:
                        exit_price = row["open"]
                        pnl = (exit_price - current_pos["entry"]) * current_pos["dir"] * 100 * 0.1 - cost
                        balance += pnl
                        trades.append({
                            "entry": current_pos["entry"],
                            "exit": exit_price,
                            "pnl": pnl,
                            "mae": current_pos["mae"],
                            "mfe": current_pos["mfe"],
                            "dir": current_pos["dir"]
                        })
                        current_pos = None

                    # Open New Position
                    if not current_pos:
                        current_pos = {
                            "entry": row["close"],
                            "dir": direction,
                            "mae": 0.0,
                            "mfe": 0.0,
                            "ts": ts
                        }

            # Track MAE/MFE while position is open
            if current_pos:
                price_diff = (row["close"] - current_pos["entry"]) * current_pos["dir"]
                current_pos["mfe"] = max(current_pos["mfe"], price_diff)
                current_pos["mae"] = min(current_pos["mae"], price_diff)

            equity_curve.append(balance)

        # Close final position
        if current_pos:
            exit_price = df_features.iloc[-1]["close"]
            cost = (self.spread + self.slippage) * 10 + (self.commission * 0.1)
            pnl = (exit_price - current_pos["entry"]) * current_pos["dir"] * 100 * 0.1 - cost
            balance += pnl
            trades.append({
                "entry": current_pos["entry"], "exit": exit_price, "pnl": pnl,
                "mae": current_pos["mae"], "mfe": current_pos["mfe"], "dir": current_pos["dir"]
            })
            equity_curve[-1] = balance

        report = self._calculate_metrics(trades, equity_curve, timestamps[0], timestamps[-1])
        return report, trades, equity_curve

    def _calculate_metrics(
        self,
        trades: List[dict],
        equity: List[float],
        start_time: datetime,
        end_time: datetime
    ) -> PerformanceReport:
        """Compute institutional metrics."""
        if not trades:
            return self._empty_report(start_time, end_time)

        pnl_series = pd.Series([t["pnl"] for t in trades])
        equity_series = pd.Series(equity)

        # Annualization Factor
        duration_days = max(1, (end_time - start_time).days)
        total_return = (equity[-1] - equity[0]) / (equity[0] + 1e-9)
        ann_return = (1 + total_return) ** (365 / duration_days) - 1

        # Sharpe Ratio (daily scaled)
        returns = equity_series.pct_change().dropna()
        if returns.std() == 0:
            sharpe = 0.0
        else:
            # Assuming 5-minute bars, ~288 per day
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 288)

        # Max Drawdown
        roll_max = equity_series.cummax()
        drawdown = (equity_series - roll_max) / (roll_max + 1e-9)
        max_dd = abs(drawdown.min())

        # Profit Factor
        gross_profit = pnl_series[pnl_series > 0].sum()
        gross_loss = abs(pnl_series[pnl_series < 0].sum())
        pf = gross_profit / (gross_loss + 1e-9)

        # Win Rate
        win_rate = len(pnl_series[pnl_series > 0]) / len(pnl_series)

        return PerformanceReport(
            annualized_return=ann_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=pf,
            total_trades=len(trades),
            win_rate=win_rate,
            total_net_pnl=pnl_series.sum(),
            avg_mae=np.mean([t["mae"] for t in trades]),
            avg_mfe=np.mean([t["mfe"] for t in trades]),
            period_start=start_time,
            period_end=end_time
        )

    def _empty_report(self, start=None, end=None) -> PerformanceReport:
        return PerformanceReport(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.0, start, end)
