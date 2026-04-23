"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorised walk-forward backtesting engine with institutional metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter

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
    """Detailed record of a single backtested trade."""

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
    Institutional-grade backtesting engine supporting vectorized execution
    with walk-forward validation and realistic cost simulation.
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        initial_balance: float = 10000.0,
        spread_pips: float = 2.0,
        commission_per_lot: float = 7.0,
        contract_size: float = 100.0,
    ) -> None:
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.spread = spread_pips * 0.01  # Assuming Gold (XAUUSD) 1 pip = 0.01
        self.commission = commission_per_lot
        self.contract_size = contract_size
        self.fe = FeatureEngineer()
        self.ef = ExecutionFilter()

    def run(
        self,
        df: pd.DataFrame,
        model: Any,
        train_window: int = 2000,
        test_window: int = 500,
    ) -> Tuple[PerformanceReport, List[TradeRecord]]:
        """
        Run walk-forward backtest.
        df: Raw OHLCV data.
        model: Model with a .predict() method compatible with EnsembleModel.
        """
        logger.info("Starting walk-forward backtest | total_bars=%d", len(df))

        # 1. Feature Engineering
        df_features = self.fe.generate_features(df)

        # 2. Walk-forward loops
        all_trades: List[TradeRecord] = []

        # We start after the first train_window
        for i in range(train_window, len(df_features) - test_window, test_window):
            # In a real walk-forward, we might re-train the model here.
            # For this implementation, we assume the model is pre-trained or
            # handles internal state.

            test_slice = df_features.iloc[i : i + test_window]
            trades = self._simulate_trading(test_slice, model, df.loc[test_slice.index])
            all_trades.extend(trades)

        # 3. Aggregate Performance
        report = self._calculate_metrics(all_trades)
        return report, all_trades

    def _simulate_trading(
        self,
        df_features: pd.DataFrame,
        model: Any,
        df_raw: pd.DataFrame,
    ) -> List[TradeRecord]:
        """
        Vectorized signal generation followed by trade simulation.
        """
        trades: List[TradeRecord] = []

        # 1. Vectorized Prediction
        # If the model has a batch predict method, use it. Otherwise, loop.
        if hasattr(model, "predict_batch"):
            directions, _ = model.predict_batch(df_features.values)
        else:
            # Fallback for models without batch support
            results = [model.predict(obs) for obs in df_features.values]
            directions = np.array([r[0] for r in results])

        active_trade: Optional[Dict[str, Any]] = None
        current_equity = self.initial_balance
        peak_equity = self.initial_balance

        # 2. Simulation Loop (necessary for sequential path-dependent logic)
        for idx in range(len(df_features)):
            timestamp = df_features.index[idx]
            direction = directions[idx]
            # confidence = confidences[idx]

            # Update Peak Equity for Drawdown Calculation (O(1))
            if current_equity > peak_equity:
                peak_equity = current_equity

            drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0

            if active_trade is None and direction != 0:
                # Layer 1-5 validation
                # Note: ef.validate is O(1) as it checks the provided df_indicators slice's last bar
                if self.ef.validate(direction, df_features.iloc[: idx + 1], drawdown, timestamp):
                    # Open trade
                    entry_price = df_raw.iloc[idx]["close"]
                    # Adjust for spread
                    if direction == 1:
                        entry_price += self.spread / 2
                    else:
                        entry_price -= self.spread / 2

                    active_trade = {
                        "entry_time": timestamp,
                        "direction": direction,
                        "entry_price": entry_price,
                        "mae": 0.0,
                        "mfe": 0.0,
                    }
            else:
                # Update MAE/MFE
                current_price = df_raw.iloc[idx]["close"]
                pnl_points = (current_price - active_trade["entry_price"]) * active_trade[
                    "direction"
                ]
                active_trade["mfe"] = max(active_trade["mfe"], pnl_points)
                active_trade["mae"] = max(active_trade["mae"], -pnl_points)

                # Check for exit signal
                if direction == -active_trade["direction"] or direction == 0:
                    exit_price = current_price
                    # Adjust for spread
                    if active_trade["direction"] == 1:
                        exit_price -= self.spread / 2
                    else:
                        exit_price += self.spread / 2

                    # Calculate PnL (including commission)
                    # Assuming 0.1 lot for backtest sizing consistency
                    lot_size = 0.1
                    raw_pnl = (
                        (exit_price - active_trade["entry_price"])
                        * active_trade["direction"]
                        * lot_size
                        * self.contract_size
                    )
                    final_pnl = raw_pnl - (self.commission * lot_size)

                    trades.append(
                        TradeRecord(
                            entry_time=active_trade["entry_time"],
                            exit_time=timestamp,
                            direction=active_trade["direction"],
                            entry_price=active_trade["entry_price"],
                            exit_price=exit_price,
                            pnl=final_pnl,
                            mae=active_trade["mae"],
                            mfe=active_trade["mfe"],
                        )
                    )
                    current_equity += final_pnl
                    active_trade = None

        return trades

    def _calculate_metrics(self, trades: List[TradeRecord]) -> PerformanceReport:
        if not trades:
            return PerformanceReport(0.0, 0.0, 0.0, 0.0, 0, 0.0)

        pnls = np.array([t.pnl for t in trades])
        total_pnl = pnls.sum()

        # Annualized Return
        duration_days = (trades[-1].exit_time - trades[0].entry_time).days or 1
        annualized_return = (total_pnl / self.initial_balance) * (365 / duration_days)

        # Sharpe Ratio (Daily Return-based approximation)
        # For a truly accurate Sharpe, we'd need a daily equity curve.
        # This is a trade-based approximation.
        if len(pnls) > 1:
            mean_pnl = np.mean(pnls)
            std_pnl = np.std(pnls) + 1e-9
            sharpe = (mean_pnl / std_pnl) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown
        equity_curve = self.initial_balance + np.cumsum(pnls)
        peak = np.maximum.accumulate(equity_curve)
        # Avoid division by zero
        safe_peak = np.where(peak == 0, 1e-9, peak)
        drawdown = (peak - equity_curve) / safe_peak
        max_dd = np.max(drawdown)

        # Profit Factor
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        win_rate = len(pnls[pnls > 0]) / len(pnls)

        return PerformanceReport(
            annualized_return=float(annualized_return),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            profit_factor=float(profit_factor),
            total_trades=len(trades),
            win_rate=float(win_rate),
        )


__all__ = ["Backtester", "PerformanceReport", "TradeRecord"]
