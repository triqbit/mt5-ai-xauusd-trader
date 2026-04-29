"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorised walk-forward backtesting engine.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.config import TradingConfig
from src.core.feature_engineering import FeatureEngineer
from src.models.ensemble import EnsembleModel
from src.trading.risk_manager import RiskManager, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """
    Standardised performance metrics matching README.md benchmarks.
    """
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    mae_avg: float = 0.0  # Maximum Adverse Excursion
    mfe_avg: float = 0.0  # Maximum Favorable Excursion

    def to_dict(self) -> Dict[str, float]:
        return {
            "Annualized Return (%)": self.annualized_return * 100,
            "Sharpe Ratio": self.sharpe_ratio,
            "Max Drawdown (%)": self.max_drawdown * 100,
            "Profit Factor": self.profit_factor,
            "Total Trades": float(self.total_trades),
            "Win Rate (%)": self.win_rate * 100,
            "MAE Avg ($)": self.mae_avg,
            "MFE Avg ($)": self.mfe_avg,
        }

    def __str__(self) -> str:
        d = self.to_dict()
        lines = [f"{k:25}: {v:>10.2f}" for k, v in d.items()]
        return "\n".join(["Performance Report", "=" * 40] + lines)


class BacktestEngine:
    """
    Institutional-grade backtesting engine.
    """
    def __init__(
        self,
        config: TradingConfig,
        feature_engineer: FeatureEngineer,
        model: EnsembleModel,
        initial_balance: float = 10000.0,
        spread: float = 0.1,  # $0.1 for XAUUSD (10 pips)
        commission: float = 7.0,  # $7 per lot round turn
    ) -> None:
        self.cfg = config
        self.fe = feature_engineer
        self.model = model
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission = commission
        self.contract_size = config.contract_size
        self.trades: List[Dict] = []

    def run(self, data: pd.DataFrame) -> PerformanceReport:
        """
        Run backtest on provided data.
        """
        df = self.fe.extract_features(data)
        obs_array = self.fe.transform(df)

        # 1. Generate Signals (Vectorized if possible)
        # Note: EnsembleModel.predict is often not vectorized by default.
        # We can try to batch if model supports it, but for now we loop.
        signals = []
        confidences = []
        for i in range(len(obs_array)):
            direction, confidence, _ = self.model.predict(obs_array[i])
            signals.append(direction)
            confidences.append(confidence)

        df["signal"] = signals
        df["confidence"] = confidences

        # 2. Simulate Trades (Iterative for logic correctness, using NumPy for speed)
        self.trades = []
        current_position = 0
        entry_price = 0.0
        entry_time = None
        lot_size = 0.1

        prices = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        times = df.index.values
        signal_vals = df["signal"].values
        conf_vals = df["confidence"].values

        for i in range(len(df)):
            sig = signal_vals[i]
            conf = conf_vals[i]
            price = prices[i]

            # Exit logic
            if current_position != 0 and (sig != current_position and sig != 0):
                exit_price = price - current_position * (self.spread / 2)
                pnl = (exit_price - entry_price) * current_position * lot_size * self.contract_size - self.commission * lot_size

                # Calculate MAE/MFE using NumPy
                idx_entry = df.index.get_loc(entry_time)
                trade_slice_high = highs[idx_entry:i+1]
                trade_slice_low = lows[idx_entry:i+1]

                if current_position == 1:
                    mfe = (np.max(trade_slice_high) - entry_price) * lot_size * self.contract_size
                    mae = (np.min(trade_slice_low) - entry_price) * lot_size * self.contract_size
                else:
                    mfe = (entry_price - np.min(trade_slice_low)) * lot_size * self.contract_size
                    mae = (entry_price - np.max(trade_slice_high)) * lot_size * self.contract_size

                self.trades.append({
                    "entry_time": entry_time,
                    "exit_time": times[i],
                    "direction": current_position,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "mae": mae,
                    "mfe": mfe
                })
                current_position = 0

            # Entry logic
            if current_position == 0 and sig != 0:
                if conf >= self.cfg.confidence_threshold:
                    current_position = sig
                    entry_price = price + current_position * (self.spread / 2)
                    entry_time = times[i]

        return self._calculate_metrics(df)

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        train_window: int = 252 * 24 * 12,
        test_window: int = 252 * 24 * 6,
    ) -> List[PerformanceReport]:
        reports = []
        total_len = len(data)

        for start in range(0, total_len - train_window - test_window, test_window):
            test_data = data.iloc[start+train_window:start+train_window+test_window]
            logger.info("Running walk-forward window: %s to %s", test_data.index[0], test_data.index[-1])
            report = self.run(test_data)
            reports.append(report)

        return reports

    def _calculate_metrics(self, df: pd.DataFrame) -> PerformanceReport:
        if not self.trades:
            return PerformanceReport()

        pnls = np.array([t["pnl"] for t in self.trades])
        total_pnl = np.sum(pnls)
        win_rate = np.sum(pnls > 0) / len(pnls)

        gross_profit = np.sum(pnls[pnls > 0])
        gross_loss = abs(np.sum(pnls[pnls < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Correct Sharpe Ratio: Resample equity to daily
        # First build a continuous equity curve
        trade_df = pd.DataFrame(self.trades)
        trade_df.set_index("exit_time", inplace=True)

        daily_equity = trade_df["pnl"].resample("D").sum().cumsum() + self.initial_balance
        # Forward fill days with no trades to maintain current balance
        daily_equity = daily_equity.reindex(pd.date_range(df.index[0], df.index[-1], freq="D")).ffill().fillna(self.initial_balance)

        daily_returns = daily_equity.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown
        peak = daily_equity.cummax()
        drawdown = (peak - daily_equity) / peak
        max_dd = drawdown.max()

        total_return = (daily_equity.iloc[-1] - self.initial_balance) / self.initial_balance
        duration_days = (df.index[-1] - df.index[0]).days
        if duration_days > 0:
            annualized_return = (1 + total_return) ** (365 / duration_days) - 1
        else:
            annualized_return = 0.0

        return PerformanceReport(
            annualized_return=annualized_return,
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            profit_factor=float(profit_factor),
            total_trades=len(self.trades),
            win_rate=float(win_rate),
            mae_avg=float(np.mean([t["mae"] for t in self.trades])),
            mfe_avg=float(np.mean([t["mfe"] for t in self.trades]))
        )
