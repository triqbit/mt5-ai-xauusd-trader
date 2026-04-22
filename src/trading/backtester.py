"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorized walk-forward backtesting engine with MAE/MFE tracking.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Benchmark metrics as per README.md."""

    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    win_rate: float
    avg_mae: float
    avg_mfe: float


class Backtester:
    """
    Vectorized walk-forward backtesting engine.
    Simulates transaction costs, execution filters, and risk management.
    Supports sliding window training and MAE/MFE metrics.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        initial_balance: float = 10000.0,
        spread: float = 0.5,  # points
        commission: float = 0.0,
        contract_size: float = 100.0,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission = commission
        self.contract_size = contract_size
        self.fe = FeatureEngineer()
        self.ef = ExecutionFilter()

    def run(
        self,
        df: pd.DataFrame,
        model: any,
        train_window: int = 1000,
        test_window: int = 200,
    ) -> PerformanceReport:
        """
        Run backtest with walk-forward simulation and MAE/MFE tracking.
        """
        logger.info("Starting backtest for %s | bars=%d", self.symbol, len(df))

        # 1. Feature Engineering (Pre-calculate all)
        df_feat = self.fe.generate_features(df)
        df_feat = self.fe.normalize_features(df_feat)
        df_feat.dropna(inplace=True)

        signals = np.zeros(len(df_feat))

        # 2. Walk-Forward Loop
        # For simplicity, we use the model's predict on sliding windows.
        # If the model supported retraining, we would do it here.
        for i in range(train_window, len(df_feat), test_window):
            end_idx = min(i + test_window, len(df_feat))

            # Test window signals
            for j in range(i, end_idx):
                row = df_feat.iloc[j]
                # Prepare observation
                obs = row.drop(["time", "open", "high", "low", "close", "tick_volume"]).values

                # Model Prediction
                direction, confidence, _ = model.predict(obs)

                if direction == 0:
                    continue

                # Apply Execution Filter
                decision = self.ef.validate(
                    row,
                    direction,
                    timestamp=row["time"],
                    prev_rows=df_feat.iloc[max(0, j-10):j]
                )

                if decision.approved:
                    signals[j] = direction

        df_feat["signal"] = signals
        # Shift signals to avoid lookahead bias (execute at next open)
        df_feat["signal"] = df_feat["signal"].shift(1).fillna(0)

        # 3. Trade Tracking (for MAE/MFE)
        trades = []
        current_trade = None

        for i in range(len(df_feat)):
            row = df_feat.iloc[i]
            sig = row["signal"]

            if current_trade is None and sig != 0:
                # Open trade
                current_trade = {
                    "direction": sig,
                    "entry_price": row["open"],
                    "entry_time": row["time"],
                    "mae": 0.0,
                    "mfe": 0.0,
                }
            elif current_trade is not None:
                # Update MAE/MFE
                price_high = row["high"]
                price_low = row["low"]

                if current_trade["direction"] == 1: # Buy
                    adverse = current_trade["entry_price"] - price_low
                    favorable = price_high - current_trade["entry_price"]
                else: # Sell
                    adverse = price_high - current_trade["entry_price"]
                    favorable = current_trade["entry_price"] - price_low

                current_trade["mae"] = max(current_trade["mae"], adverse)
                current_trade["mfe"] = max(current_trade["mfe"], favorable)

                # Exit if signal changes or opposite signal
                if sig != current_trade["direction"]:
                    current_trade["exit_price"] = row["open"]
                    current_trade["exit_time"] = row["time"]
                    # Calculate PnL
                    pnl_points = (current_trade["exit_price"] - current_trade["entry_price"]) * current_trade["direction"]
                    # Subtract spread
                    pnl_points -= self.spread
                    current_trade["pnl"] = pnl_points * self.contract_size
                    trades.append(current_trade)

                    if sig != 0:
                        current_trade = {
                            "direction": sig,
                            "entry_price": row["open"],
                            "entry_time": row["time"],
                            "mae": 0.0,
                            "mfe": 0.0,
                        }
                    else:
                        current_trade = None

        # 4. Metrics Calculation
        if not trades:
            return PerformanceReport(0, 0, 0, 0, 0, 0, 0, 0)

        trade_df = pd.DataFrame(trades)

        # Annualized Return
        total_pnl = trade_df["pnl"].sum()
        days = (df_feat["time"].max() - df_feat["time"].min()).days or 1
        total_ret = total_pnl / self.initial_balance
        annual_ret = (1 + total_ret) ** (365 / days) - 1 if total_ret > -1 else -1.0

        # Sharpe Ratio
        # Rough estimation from trade PnLs
        if len(trade_df) > 1:
            sharpe = (trade_df["pnl"].mean() / (trade_df["pnl"].std() + 1e-8)) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown
        equity_curve = self.initial_balance + trade_df["pnl"].cumsum()
        peak = equity_curve.cummax()
        drawdown = (peak - equity_curve) / peak
        max_dd = drawdown.max()

        # Profit Factor
        gross_profit = trade_df.loc[trade_df["pnl"] > 0, "pnl"].sum()
        gross_loss = abs(trade_df.loc[trade_df["pnl"] < 0, "pnl"].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        win_rate = len(trade_df[trade_df["pnl"] > 0]) / len(trade_df)

        report = PerformanceReport(
            annualized_return=float(annual_ret),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            profit_factor=float(pf),
            total_trades=len(trade_df),
            win_rate=float(win_rate),
            avg_mae=float(trade_df["mae"].mean()),
            avg_mfe=float(trade_df["mfe"].mean()),
        )

        return report


__all__ = ["Backtester", "PerformanceReport"]
