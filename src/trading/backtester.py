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
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.core.types import TradeSignal
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
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


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
        feature_engineer: Optional[FeatureEngineer] = None,
        execution_filter: Optional[ExecutionFilter] = None,
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
        self.trades: List[BacktestTrade] = []
        self.results: Optional[PerformanceReport] = None

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
            logger.error("Insufficient data for walk-forward after feature engineering: %d bars available", n)
            return PerformanceReport()

        # Calculate ATR once for the whole dataset
        high_low = data["high"] - data["low"]
        high_close = (data["high"] - data["close"].shift(1)).abs()
        low_close = (data["low"] - data["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data = data.copy()
        data["atr"] = tr.rolling(14).mean()

        start = 0
        active_trades: List[Dict[str, Any]] = []

        while start + train_window + test_window <= n:
            test_start_idx = start + train_window
            test_end_idx = test_start_idx + test_window

            test_data = data.iloc[test_start_idx : test_end_idx]
            test_features = df_features.iloc[test_start_idx : test_end_idx]

            for i in range(len(test_data)):
                bar_idx = test_data.index[i]
                current_bar = test_data.iloc[i]

                # 1. Update active trades (SL/TP checks)
                self._update_active_trades(active_trades, current_bar, bar_idx)

                # 2. Skip if max positions reached
                if len(active_trades) >= self.max_positions:
                    continue

                # 3. Get Model Signal
                obs = test_features.iloc[i]
                try:
                    signal_obj = model.predict(obs.values)
                    direction = signal_obj.direction
                    confidence = signal_obj.confidence
                except Exception:
                    pred = model.predict(obs.values)
                    direction = int(pred[0]) if isinstance(pred, (tuple, list, np.ndarray)) else int(pred)
                    confidence = 1.0

                if direction == 0:
                    continue

                # 4. Prepare Signal and Validate with Execution Filter
                price = current_bar["close"]
                atr = current_bar["atr"]
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
                    timestamp=bar_idx,
                )

                # Prepare filter context
                filter_context = df_features.loc[:bar_idx]
                drawdown = (self.initial_balance - self.balance) / self.initial_balance

                decision = self.ef.validate(
                    signal,
                    filter_context,
                    current_drawdown=drawdown,
                    timestamp=bar_idx,
                )

                if decision.is_approved:
                    self._open_trade(active_trades, signal)

            start += step_size

        # Close any remaining trades at the end of data
        self._close_all_trades(active_trades, data.iloc[-1])

        return self._calculate_performance()

    def _open_trade(self, active_trades: List[Dict[str, Any]], signal: TradeSignal) -> None:
        """Opens a new trade and adds it to the active list."""
        execution_price = signal.entry_price + (signal.direction * self.spread / 2)
        active_trades.append({
            "signal": signal,
            "entry_price": execution_price,
            "mae": 0.0,
            "mfe": 0.0
        })

    def _update_active_trades(self, active_trades: List[Dict[str, Any]], current_bar: pd.Series, timestamp: datetime) -> None:
        """Checks SL/TP for all active trades and closes them if hit."""
        closed_indices = []
        for i, trade in enumerate(active_trades):
            signal = trade["signal"]
            direction = signal.direction
            high, low = current_bar["high"], current_bar["low"]
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

    def _close_all_trades(self, active_trades: List[Dict[str, Any]], last_bar: pd.Series) -> None:
        """Force close all remaining trades."""
        for trade in active_trades:
            self._record_trade(trade, last_bar["close"], last_bar.name)
        active_trades.clear()

    def _record_trade(self, trade: Dict[str, Any], exit_price: float, exit_time: datetime) -> None:
        """Finalizes a trade, calculates PnL, and records it."""
        signal = trade["signal"]
        direction = signal.direction

        # Adjust exit price for spread
        exit_price_adj = exit_price - (direction * self.spread / 2)

        contract_multiplier = 100 if "XAU" in self.symbol else 1
        raw_pnl = (exit_price_adj - trade["entry_price"]) * direction * signal.lot_size * contract_multiplier
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
