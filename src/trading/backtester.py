"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorized walk-forward backtesting engine with institutional metrics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.config import TradingConfig
from src.core.feature_engineering import FeatureEngineer
from src.models.base_model import BaseModel
from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Institutional-grade backtest performance summary."""

    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    mae_avg: float
    mfe_avg: float
    total_trades: int = 0
    win_rate: float = 0.0


@dataclass
class TradeRecord:
    """Detailed record of a single simulated trade."""

    entry_time: datetime
    exit_time: datetime
    direction: int
    entry_price: float
    exit_price: float
    pnl: float
    mae: float  # Maximum Adverse Excursion
    mfe: float  # Maximum Favorable Excursion
    duration_bars: int


class BacktestEngine:
    """
    Vectorized walk-forward backtesting engine.
    Supports transaction costs, institutional metrics, and 6-layer execution filtering.
    """

    def __init__(
        self,
        model: BaseModel,
        feature_engineer: FeatureEngineer,
        execution_filter: ExecutionFilter,
        config: TradingConfig,
        initial_balance: float = 10000.0,
        spread: float = 0.20,  # XAUUSD typical spread in USD
        commission_per_lot: float = 7.0,  # Round turn commission per standard lot
    ):
        self.model = model
        self.fe = feature_engineer
        self.filter = execution_filter
        self.cfg = config
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission_per_lot = commission_per_lot
        self.trades: List[TradeRecord] = []

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        train_size: int = 2000,
        test_size: int = 500,
        step_size: int = 500,
    ) -> PerformanceReport:
        """
        Execute walk-forward backtest across the provided dataset.
        """
        all_oos_trades = []
        n = len(df)

        start_idx = 0
        while start_idx + train_size + test_size <= n:
            train_df = df.iloc[start_idx : start_idx + train_size]
            test_df = df.iloc[start_idx + train_size : start_idx + train_size + test_size]

            logger.info(
                "Walk-forward window | Train: %s to %s | Test: %s to %s",
                train_df.index[0], train_df.index[-1],
                test_df.index[0], test_df.index[-1]
            )

            # In a real walk-forward, we might re-train the model here.
            # For this implementation, we assume the model is pre-trained or updated externally.

            # Run backtest on OOS window
            window_trades = self._backtest_window(test_df, full_df_for_context=df)
            all_oos_trades.extend(window_trades)

            start_idx += step_size

        self.trades = all_oos_trades
        return self._generate_report()

    def _backtest_window(self, test_df: pd.DataFrame, full_df_for_context: pd.DataFrame) -> List[TradeRecord]:
        """
        Run backtest on a single out-of-sample window.
        Uses vectorized signal generation but candle-by-candle execution for filtering and MAE/MFE.
        """
        # 1. Compute features for the window (with enough lookback)
        # We need context before test_df for indicators to be valid
        window_start_idx = full_df_for_context.index.get_loc(test_df.index[0])
        lookback = 300 # Sufficient for most EMAs/Indicators
        context_start = max(0, window_start_idx - lookback)
        context_df = full_df_for_context.iloc[context_start : window_start_idx + len(test_df)]

        features_df = self.fe.compute_features(context_df)
        # Re-align features with test_df
        features_test = features_df.reindex(test_df.index).dropna()

        if features_test.empty:
            return []

        # 2. Vectorized Signal Generation
        # model.predict usually takes a single observation, so we might need to loop or use a batch method if available.
        # Given BaseModel.predict(obs), we loop.

        window_trades = []
        current_equity = self.initial_balance # Simple approximation for drawdown filter
        peak_equity = current_equity

        # We simulate one trade at a time to keep it simple and match RiskManager logic
        active_trade: Optional[Dict[str, Any]] = None

        for i in range(len(test_df)):
            timestamp = test_df.index[i]
            row = test_df.iloc[i]

            if active_trade:
                # Update MAE / MFE
                high = row['high']
                low = row['low']

                if active_trade['direction'] == 1: # BUY
                    active_trade['mfe'] = max(active_trade['mfe'], high - active_trade['entry_price'])
                    active_trade['mae'] = max(active_trade['mae'], active_trade['entry_price'] - low)
                else: # SELL
                    active_trade['mfe'] = max(active_trade['mfe'], active_trade['entry_price'] - low)
                    active_trade['mae'] = max(active_trade['mae'], high - active_trade['entry_price'])

                # Check Exit (Simple fixed SL/TP for backtest or signal reversal)
                # In this backtester, we close when we get an opposite signal or reach end of window
                # For now, let's implement signal-based exit to keep it "vectorized-like"

            # If no active trade, look for entry
            if not active_trade:
                if timestamp not in features_test.index:
                    continue

                obs = features_test.loc[timestamp].values
                signal_obj = self.model.predict(obs)

                if signal_obj.direction != 0:
                    # Risk/Filter Check
                    drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0

                    # Create a dummy TradeSignal for the filter
                    # In backtest we don't have all RiskManager info, so we use simplified version
                    temp_signal = TradeSignal(
                        symbol=self.cfg.symbol,
                        direction=signal_obj.direction,
                        entry_price=row['close'],
                        stop_loss=0, take_profit=0, lot_size=0.1, # Placeholders
                        algorithm=self.cfg.algorithm,
                        confidence=signal_obj.confidence,
                        timestamp=timestamp
                    )

                    # Pass context DF up to current timestamp for filter
                    filter_context = context_df.loc[:timestamp].tail(500)
                    decision = self.filter.validate(temp_signal, filter_context, drawdown, timestamp=timestamp)

                    if decision.is_approved:
                        entry_price = row['close'] + (signal_obj.direction * self.spread / 2)
                        active_trade = {
                            'entry_time': timestamp,
                            'direction': signal_obj.direction,
                            'entry_price': entry_price,
                            'mae': 0.0,
                            'mfe': 0.0,
                            'start_idx': i
                        }
            else:
                # Check for exit signal
                if timestamp in features_test.index:
                    obs = features_test.loc[timestamp].values
                    signal_obj = self.model.predict(obs)

                    # Exit if opposite signal or end of test window
                    is_opposite = (signal_obj.direction != 0 and signal_obj.direction != active_trade['direction'])
                    is_end = (i == len(test_df) - 1)

                    if is_opposite or is_end:
                        exit_price = row['close'] - (active_trade['direction'] * self.spread / 2)
                        raw_pnl = (exit_price - active_trade['entry_price']) * active_trade['direction']

                        # Apply commission (assuming 0.1 lot for simplicity or using cfg.risk_per_trade)
                        # Let's say we trade 1.0 lot for metric consistency if not specified
                        lot_size = 1.0
                        commission = self.commission_per_lot * lot_size
                        pnl = (raw_pnl * 100) * lot_size - commission # XAUUSD 1 lot = 100 oz

                        current_equity += pnl
                        peak_equity = max(peak_equity, current_equity)

                        window_trades.append(TradeRecord(
                            entry_time=active_trade['entry_time'],
                            exit_time=timestamp,
                            direction=active_trade['direction'],
                            entry_price=active_trade['entry_price'],
                            exit_price=exit_price,
                            pnl=pnl,
                            mae=active_trade['mae'],
                            mfe=active_trade['mfe'],
                            duration_bars=i - active_trade['start_idx']
                        ))
                        active_trade = None

        return window_trades

    def _generate_report(self) -> PerformanceReport:
        """Calculate aggregate metrics from all trades."""
        if not self.trades:
            return PerformanceReport(0, 0, 0, 0, 0, 0)

        pnls = np.array([t.pnl for t in self.trades])
        total_pnl = np.sum(pnls)

        # Returns based on initial balance
        total_return = total_pnl / self.initial_balance

        # Annualization (Roughly assuming M5 timeframe and 252 days)
        # If we have timestamps, we can be more accurate
        duration_days = (self.trades[-1].exit_time - self.trades[0].entry_time).days
        if duration_days > 0:
            annualized_return = (1 + total_return) ** (365.25 / duration_days) - 1
        else:
            annualized_return = total_return

        # Sharpe (Daily approximation)
        # Group pnls by day
        df_trades = pd.DataFrame([{
            'date': t.exit_time.date(),
            'pnl': t.pnl
        } for t in self.trades])
        daily_pnl = df_trades.groupby('date')['pnl'].sum()

        if len(daily_pnl) > 1:
            sharpe = (daily_pnl.mean() / (daily_pnl.std() + 1e-8)) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown
        equity_curve = self.initial_balance + np.cumsum(pnls)
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0

        # Profit Factor
        wins = pnls[pnls > 0]
        losses = np.abs(pnls[pnls < 0])
        profit_factor = np.sum(wins) / np.sum(losses) if np.sum(losses) > 0 else float('inf')

        # MAE / MFE
        mae_avg = np.mean([t.mae for t in self.trades])
        mfe_avg = np.mean([t.mfe for t in self.trades])

        # Win Rate
        win_rate = len(wins) / len(pnls)

        return PerformanceReport(
            annualized_return=annualized_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            mae_avg=mae_avg,
            mfe_avg=mfe_avg,
            total_trades=len(self.trades),
            win_rate=win_rate
        )
