"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorised walk-forward backtesting engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.models.base import BaseModel
from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal

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
class BacktestTrade:
    """Details of a single backtested trade."""

    ticket: int
    symbol: str
    direction: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl: float
    lot_size: float
    mae: float  # Maximum Adverse Excursion
    mfe: float  # Maximum Favorable Excursion


class BacktestEngine:
    """
    Simulates trading over historical data with realistic costs and walk-forward support.
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        initial_balance: float = 10000.0,
        spread_pips: float = 2.0,
        commission_per_lot: float = 7.0,
    ) -> None:
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.spread = spread_pips * 0.01  # For XAUUSD, 1 pip = 0.01
        self.commission = commission_per_lot
        self.fe = FeatureEngineer()
        self.filter = ExecutionFilter()

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        model: BaseModel,
        train_window_days: int = 180,
        test_window_days: int = 30,
    ) -> Tuple[PerformanceReport, List[BacktestTrade]]:
        """
        Execute walk-forward backtest.
        """
        if data.empty:
            return PerformanceReport(0, 0, 0, 0, 0, 0), []

        start_date = data.index[0]
        end_date = data.index[-1]

        all_trades: List[BacktestTrade] = []
        current_balance = self.initial_balance

        logger.info("Starting Walk-Forward Backtest | %s to %s", start_date, end_date)

        current_test_start = start_date + timedelta(days=train_window_days)

        while current_test_start < end_date:
            current_test_end = current_test_start + timedelta(days=test_window_days)
            if current_test_end > end_date:
                current_test_end = end_date

            logger.info("WF Window: Testing from %s to %s", current_test_start, current_test_end)

            # Extract test slice
            test_data = data[(data.index >= current_test_start) & (data.index < current_test_end)]
            if not test_data.empty:
                # We need some lookback for features
                lookback_data = data[data.index < current_test_start].tail(250) # Buffer for indicators
                combined_data = pd.concat([lookback_data, test_data])

                # Run backtest on this slice
                # Note: In a real WF, we would train the model on the train_window here
                # but since we assume model is pre-trained or logic-based, we just run.
                _, window_trades = self.run(combined_data, model, start_date=current_test_start, end_date=current_test_end)

                # Update ticket numbers to be unique across windows
                offset = len(all_trades) * 1000
                for t in window_trades:
                    t.ticket += offset

                all_trades.extend(window_trades)

            current_test_start = current_test_end

        # Re-calculate total metrics
        total_pnl = sum(t.pnl for t in all_trades)
        final_balance = self.initial_balance + total_pnl

        # Build equity curve for MDD
        pnls = [t.pnl for t in all_trades]
        equity_curve = [self.initial_balance]
        for p in pnls:
            equity_curve.append(equity_curve[-1] + p)

        return self._calculate_metrics(all_trades, final_balance, equity_curve, data.index[0], data.index[-1]), all_trades

    def run(
        self,
        data: pd.DataFrame,
        model: BaseModel,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[PerformanceReport, List[BacktestTrade]]:
        """
        Execute core backtest loop (semi-vectorized).
        """
        # Generate features (vectorized)
        df_features = self.fe.generate_features(data.copy())

        if df_features.empty:
            return PerformanceReport(0, 0, 0, 0, 0, 0), []

        # Align
        data_aligned = data.loc[df_features.index]
        if start_date:
            data_aligned = data_aligned[data_aligned.index >= start_date]
            df_features = df_features.loc[data_aligned.index]
        if end_date:
            data_aligned = data_aligned[data_aligned.index <= end_date]
            df_features = df_features.loc[data_aligned.index]

        if data_aligned.empty:
            return PerformanceReport(0, 0, 0, 0, 0, 0), []

        # Vectorized signal generation
        # We can't fully vectorize if model is complex, but we can predict in batches
        norm_features = self.fe.normalize(df_features)

        # For simplicity in this implementation, we'll still loop but keep it tight
        # Real vectorization would be: signals = model.predict_batch(norm_features)

        trades: List[BacktestTrade] = []
        balance = self.initial_balance
        peak_balance = balance
        equity_curve = [balance]

        feature_values = norm_features.values
        price_values = data_aligned["close"].values
        high_values = data_aligned["high"].values
        low_values = data_aligned["low"].values
        time_values = data_aligned.index

        current_trade: Optional[Dict] = None
        ticket_counter = 1000

        for i in range(len(data_aligned)):
            current_time = time_values[i]
            current_price = price_values[i]

            # Model prediction
            signal_obj = model.predict(feature_values[i])
            direction = signal_obj.direction
            confidence = signal_obj.confidence

            if current_trade:
                # Update MAE/MFE
                if current_trade["direction"] == 1:
                    current_trade["mae"] = min(current_trade["mae"], low_values[i] - current_trade["entry_price"])
                    current_trade["mfe"] = max(current_trade["mfe"], high_values[i] - current_trade["entry_price"])
                else:
                    current_trade["mae"] = min(current_trade["mae"], current_trade["entry_price"] - high_values[i])
                    current_trade["mfe"] = max(current_trade["mfe"], current_trade["entry_price"] - low_values[i])

                # Check for exit (direction change or neutral)
                if direction != current_trade["direction"] or direction == 0:
                    exit_price = current_price
                    if current_trade["direction"] == 1:
                        pnl = (exit_price - current_trade["entry_price"]) * 100 * current_trade["lot_size"]
                    else:
                        pnl = (current_trade["entry_price"] - exit_price) * 100 * current_trade["lot_size"]

                    pnl -= self.commission * current_trade["lot_size"]

                    trades.append(BacktestTrade(
                        ticket=current_trade["ticket"],
                        symbol=self.symbol,
                        direction=current_trade["direction"],
                        entry_time=current_trade["entry_time"],
                        exit_time=current_time,
                        entry_price=current_trade["entry_price"],
                        exit_price=exit_price,
                        pnl=pnl,
                        lot_size=current_trade["lot_size"],
                        mae=current_trade["mae"],
                        mfe=current_trade["mfe"]
                    ))
                    balance += pnl
                    current_trade = None

            if not current_trade and direction != 0:
                # Apply Execution Filter
                # Note: Execution filter needs some historical context
                # We assume df_features already has necessary indicators
                temp_signal = TradeSignal(
                    symbol=self.symbol,
                    direction=direction,
                    entry_price=current_price,
                    stop_loss=0.0, take_profit=0.0, lot_size=0.1,
                    algorithm="backtest", confidence=confidence,
                    timestamp=current_time
                )

                # Check filter (needs at least some history for rolling calcs)
                # Here we just use the current slice of df_features
                current_drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0

                # We need a small window for the filter checks like rolling ATR
                # Since we are in a loop, we can just pass the dataframe up to current i
                decision = self.filter.validate(temp_signal, df_features.iloc[max(0, i-30):i+1], current_drawdown)

                if decision.is_allowed:
                    entry_price = current_price + (direction * self.spread / 2)
                    current_trade = {
                        "ticket": ticket_counter,
                        "direction": direction,
                        "entry_time": current_time,
                        "entry_price": entry_price,
                        "lot_size": 0.1,
                        "mae": 0.0,
                        "mfe": 0.0
                    }
                    ticket_counter += 1

            if balance > peak_balance:
                peak_balance = balance
            equity_curve.append(balance)

        return self._calculate_metrics(trades, balance, equity_curve, data_aligned.index[0], data_aligned.index[-1]), trades

    def _calculate_metrics(
        self,
        trades: List[BacktestTrade],
        final_balance: float,
        equity_curve: List[float],
        start_time: datetime,
        end_time: datetime
    ) -> PerformanceReport:
        if not trades:
            return PerformanceReport(0, 0, 0, 0, 0, 0)

        pnls = np.array([t.pnl for t in trades])

        # Duration for annualization
        duration = end_time - start_time
        years = duration.total_seconds() / (365.25 * 24 * 3600)
        if years <= 0: years = 1/365.25 # Minimum 1 day

        total_return_pct = (final_balance - self.initial_balance) / self.initial_balance
        # Correct Annualized Return: (1 + total_return)^(1/years) - 1
        ann_return = ((1 + total_return_pct)**(1/years) - 1) * 100

        # Sharpe Ratio (annualized)
        # We calculate it based on periodic returns (e.g. daily) if possible,
        # but for per-trade, we use the standard formula scaled by sqrt(N_trades_per_year)
        if len(pnls) > 1:
            avg_pnl = np.mean(pnls)
            std_pnl = np.std(pnls)
            trades_per_year = len(trades) / years
            sharpe = (avg_pnl / std_pnl * np.sqrt(trades_per_year)) if std_pnl > 0 else 0
        else:
            sharpe = 0

        # Max Drawdown
        eq = np.array(equity_curve)
        peak = np.maximum.accumulate(eq)
        # Avoid division by zero
        drawdowns = np.where(peak > 0, (peak - eq) / peak, 0)
        max_dd = np.max(drawdowns) * 100

        # Profit Factor
        wins = pnls[pnls > 0]
        losses = abs(pnls[pnls < 0])
        pf = np.sum(wins) / np.sum(losses) if np.sum(losses) > 0 else float('inf')

        win_rate = (len(wins) / len(trades)) * 100

        return PerformanceReport(
            annualized_return=ann_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=pf,
            total_trades=len(trades),
            win_rate=win_rate
        )
