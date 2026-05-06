"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Efficient walk-forward backtesting engine with institutional metrics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Institutional-grade backtest performance report."""

    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    mae_avg: float = 0.0  # Maximum Adverse Excursion
    mfe_avg: float = 0.0  # Maximum Favorable Excursion
    total_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    start_date: datetime | None = None
    end_date: datetime | None = None


@dataclass
class BacktestTrade:
    """Record of a trade executed during backtest."""

    ticket: int
    symbol: str
    direction: int
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    lot_size: float
    pnl: float
    mae: float = 0.0
    mfe: float = 0.0


class BacktestEngine:
    """
    Efficient walk-forward backtesting engine.
    Simulates institutional trading conditions including spreads and commissions.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10000.0,
        spread: float = 0.0001,
        commission_per_lot: float = 7.0,
        leverage: int = 100,
        feature_engineer: FeatureEngineer | None = None,
        execution_filter: ExecutionFilter | None = None,
        max_positions: int = 1,
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission_per_lot = commission_per_lot
        self.leverage = leverage
        self.fe = feature_engineer or FeatureEngineer()
        self.ef = execution_filter or ExecutionFilter()
        self.max_positions = max_positions

        self.balance = initial_balance
        self.trades: list[BacktestTrade] = []
        self.results: PerformanceReport | None = None

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        model: Any,
        train_window: int = 500,
        test_window: int = 100,
        step_size: int = 100,
    ) -> PerformanceReport:
        """
        Executes a walk-forward backtest.
        Pre-calculates features to optimize performance.
        """
        logger.info(
            "Starting walk-forward backtest | train=%d test=%d step=%d",
            train_window,
            test_window,
            step_size,
        )

        # Pre-calculate all possible features and technical indicators for efficiency
        logger.info("Pre-calculating features for the entire dataset...")
        df_features = self.fe.compute_features(data, drop_ohlcv=False)

        if df_features.empty:
            logger.error("Feature engineering returned empty DataFrame. Insufficient data?")
            return PerformanceReport()

        # Align data with features (FeatureEngineer drops rows with NaNs)
        data = data.loc[df_features.index].copy()
        n = len(data)

        if n < train_window + test_window:
            logger.error(
                "Insufficient data for walk-forward after feature engineering: %d bars available", n
            )
            return PerformanceReport()

        # Calculate ATR once for the whole dataset
        high_low = data["high"] - data["low"]
        high_close = (data["high"] - data["close"].shift(1)).abs()
        low_close = (data["low"] - data["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data = data.copy()
        data["atr"] = tr.rolling(14).mean()

        # Pre-calculate ExecutionFilter metrics to avoid O(N) calculations in loop
        logger.info("Pre-calculating execution filter metrics...")
        prefix = f"base_{self.fe.base_timeframe}"

        # 1. ATR Ratio (current / avg)
        atr_series = data["atr"]
        avg_atr_series = atr_series.rolling(window=100).mean()
        atr_current_vals = atr_series.values
        atr_avg_vals = avg_atr_series.values

        # 2. Trend Angle (EMA21 Slope)
        ema21_col = f"{prefix}_ema_21"
        if ema21_col not in df_features.columns:
            # Fallback if FeatureEngineer didn't provide it
            ema21_series = data["close"].ewm(span=21, adjust=False).mean()
        else:
            ema21_series = df_features[ema21_col]

        # Use a vectorized rolling slope if possible, or pre-calculate
        # For simplicity and correctness with ExecutionFilter logic:
        ema21_vals = ema21_series.values
        slopes = np.zeros(n)
        window = 20
        x = np.arange(window)
        x_mean = np.mean(x)
        x_var = np.var(x) * window

        # Optimized rolling slope calculation
        for j in range(window, n + 1):
            y = ema21_vals[j - window : j]
            slope = np.sum((x - x_mean) * y) / x_var
            slopes[j - 1] = slope

        # 3. EMA Sequence
        ema_vals = {}
        for p in [8, 21, 50, 200]:
            col = f"{prefix}_ema_{p}"
            if col in df_features.columns:
                ema_vals[p] = df_features[col].values
            else:
                ema_vals[p] = data["close"].ewm(span=p, adjust=False).mean().values

        # 4. RSI
        rsi_col = f"{prefix}_rsi"
        if rsi_col in df_features.columns:
            rsi_vals = df_features[rsi_col].values
        else:
            # Simple RSI fallback
            delta = data["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-8)
            rsi_vals = (100 - (100 / (1 + rs))).values

        start = 0
        active_trades: list[dict[str, Any]] = []

        # Optimization: Pre-extract data into NumPy arrays to avoid expensive pandas indexing in the loop
        # Slicing .iloc[i] on a DataFrame creates a new Series object, which is slow.
        high_vals = data["high"].values
        low_vals = data["low"].values
        close_vals = data["close"].values
        atr_vals = data["atr"].values
        time_vals = data.index
        feature_vals = df_features.values

        while start + train_window + test_window <= n:
            test_start_idx = start + train_window

            for i in range(test_window):
                abs_idx = test_start_idx + i
                bar_time = time_vals[abs_idx]

                # 1. Update active trades (SL/TP checks)
                # Optimization: Pass raw values instead of a pd.Series
                self._update_active_trades(
                    active_trades,
                    high=high_vals[abs_idx],
                    low=low_vals[abs_idx],
                    timestamp=bar_time,
                )

                # 2. Skip if max positions reached
                if len(active_trades) >= self.max_positions:
                    continue

                # 3. Get Model Signal
                # Optimization: Direct NumPy row access
                obs = feature_vals[abs_idx]
                try:
                    signal_obj = model.predict(obs)
                    direction = signal_obj.direction
                    confidence = signal_obj.confidence
                except Exception:
                    pred = model.predict(obs)
                    direction = (
                        int(pred[0]) if isinstance(pred, (tuple, list, np.ndarray)) else int(pred)
                    )
                    confidence = 1.0

                if direction == 0:
                    continue

                # 4. Prepare Signal and Validate with Execution Filter
                price = close_vals[abs_idx]
                atr = atr_vals[abs_idx]
                if np.isnan(atr):
                    continue

                stop_loss = price - (direction * 2 * atr)
                take_profit = price + (direction * 4 * atr)

                signal = TradeSignal(
                    symbol=self.symbol,
                    direction=direction,
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    lot_size=0.1,  # Base lot
                    algorithm="backtest",
                    confidence=confidence,
                    timestamp=bar_time,
                )

                # Prepare filter metrics
                drawdown = (self.initial_balance - self.balance) / self.initial_balance
                precomputed = {
                    "atr_volatility": {
                        "current_atr": atr_current_vals[abs_idx],
                        "avg_atr": atr_avg_vals[abs_idx],
                    },
                    "trend_angle": {"slope": slopes[abs_idx]},
                    "ema_sequence": {"emas": {p: ema_vals[p][abs_idx] for p in [8, 21, 50, 200]}},
                    "momentum": {"rsi": rsi_vals[abs_idx]},
                }

                decision = self.ef.validate(
                    signal,
                    df_features,  # Still pass df for layers that might need it (though we precomputed most)
                    current_drawdown=drawdown,
                    timestamp=bar_time,
                    precomputed_metrics=precomputed,
                )

                if decision.is_approved:
                    self._open_trade(active_trades, signal)

            start += step_size

        # Close any remaining trades at the end of data
        self._close_all_trades(active_trades, last_close=close_vals[-1], last_time=time_vals[-1])

        return self._calculate_performance()

    def _open_trade(self, active_trades: list[dict[str, Any]], signal: TradeSignal) -> None:
        """Opens a new trade and adds it to the active list."""
        execution_price = signal.entry_price + (signal.direction * self.spread / 2)
        active_trades.append(
            {"signal": signal, "entry_price": execution_price, "mae": 0.0, "mfe": 0.0}
        )

    def _update_active_trades(
        self,
        active_trades: list[dict[str, Any]],
        high: float,
        low: float,
        timestamp: datetime,
    ) -> None:
        """Checks SL/TP for all active trades and closes them if hit."""
        closed_indices = []
        for i, trade in enumerate(active_trades):
            signal = trade["signal"]
            direction = signal.direction
            entry_price = trade["entry_price"]

            # Update MAE/MFE
            if direction == 1:
                trade["mae"] = max(trade["mae"], entry_price - low)
                trade["mfe"] = max(trade["mfe"], high - entry_price)
            else:
                trade["mae"] = max(trade["mae"], high - entry_price)
                trade["mfe"] = max(trade["mfe"], entry_price - low)

            # SL/TP Check
            exit_price = None
            if direction == 1:
                if low <= signal.stop_loss:
                    exit_price = signal.stop_loss
                elif high >= signal.take_profit:
                    exit_price = signal.take_profit
            else:
                if high >= signal.stop_loss:
                    exit_price = signal.stop_loss
                elif low <= signal.take_profit:
                    exit_price = signal.take_profit

            if exit_price:
                self._record_trade(trade, exit_price, timestamp)
                closed_indices.append(i)

        for i in sorted(closed_indices, reverse=True):
            active_trades.pop(i)

    def _close_all_trades(
        self, active_trades: list[dict[str, Any]], last_close: float, last_time: datetime
    ) -> None:
        """Force close all remaining trades."""
        for trade in active_trades:
            self._record_trade(trade, last_close, last_time)
        active_trades.clear()

    def _record_trade(self, trade: dict[str, Any], exit_price: float, exit_time: datetime) -> None:
        """Finalizes a trade, calculates PnL, and records it."""
        signal = trade["signal"]
        direction = signal.direction

        # Adjust exit price for spread
        exit_price_adj = exit_price - (direction * self.spread / 2)

        contract_multiplier = 100 if "XAU" in self.symbol else 1
        raw_pnl = (
            (exit_price_adj - trade["entry_price"])
            * direction
            * signal.lot_size
            * contract_multiplier
        )
        commission = signal.lot_size * self.commission_per_lot
        final_pnl = raw_pnl - commission

        self.trades.append(
            BacktestTrade(
                ticket=len(self.trades) + 1,
                symbol=self.symbol,
                direction=direction,
                entry_time=signal.timestamp,
                entry_price=trade["entry_price"],
                exit_time=exit_time,
                exit_price=exit_price_adj,
                lot_size=signal.lot_size,
                pnl=final_pnl,
                mae=trade["mae"],
                mfe=trade["mfe"],
            )
        )
        self.balance += final_pnl

    def _calculate_performance(self) -> PerformanceReport:
        """Aggregates all trades and calculates final metrics."""
        if not self.trades:
            return PerformanceReport()

        pnls = np.array([t.pnl for t in self.trades])
        maes = np.array([t.mae for t in self.trades])
        mfes = np.array([t.mfe for t in self.trades])

        total_return = (self.balance - self.initial_balance) / self.initial_balance
        win_rate = np.sum(pnls > 0) / len(pnls)

        gross_profit = np.sum(pnls[pnls > 0])
        gross_loss = abs(np.sum(pnls[pnls < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Equity curve for drawdown calculation
        equity_curve = self.initial_balance + np.cumsum(pnls)
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        max_drawdown = np.max(drawdown)

        # Sharpe Ratio (daily approximation)
        if len(pnls) > 1:
            avg_pnl = np.mean(pnls)
            std_pnl = np.std(pnls)
            sharpe = (avg_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        # Annualized Return
        start_time = self.trades[0].entry_time
        end_time = self.trades[-1].exit_time
        days = (end_time - start_time).days
        if days > 0:
            annualized_return = (1 + total_return) ** (365 / days) - 1
        else:
            annualized_return = total_return

        report = PerformanceReport(
            annualized_return=annualized_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            mae_avg=np.mean(maes),
            mfe_avg=np.mean(mfes),
            total_trades=len(self.trades),
            win_rate=win_rate,
            total_return=total_return,
            start_date=start_time,
            end_date=end_time,
        )
        self.results = report
        return report
