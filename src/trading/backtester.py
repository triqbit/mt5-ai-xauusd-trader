"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py
Vectorized walk-forward backtesting engine.
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

@dataclass
class TradeResult:
    """Detailed result of a single simulated trade."""
    symbol: str
    direction: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    lot_size: float
    pnl: float
    mae: float  # Maximum Adverse Excursion
    mfe: float  # Maximum Favorable Excursion
    algorithm: str
    confidence: float

@dataclass
class PerformanceReport:
    """Institutional-grade backtest performance summary."""
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    win_rate: float
    total_pnl: float
    start_date: datetime
    end_date: datetime

class BacktestEngine:
    """
    Vectorized backtesting engine supporting walk-forward analysis,
    realistic transaction costs, and per-trade excursion metrics.
    """
    def __init__(
        self,
        symbol: str = "XAUUSD",
        initial_balance: float = 10000.0,
        spread: float = 0.30,  # 30 pips for XAUUSD
        commission: float = 7.0,  # $7 per lot round turn
    ) -> None:
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.spread = spread
        self.commission = commission
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        df: pd.DataFrame,
        model: any,
        feature_engineer: any,
        execution_filter: any,
    ) -> PerformanceReport:
        """Execute a standard backtest over the provided dataframe."""
        self.logger.info("Starting backtest | symbol=%s rows=%d", self.symbol, len(df))

        # 1. Feature Engineering
        df_features = feature_engineer.generate_features(df)

        # 2. Signal Generation
        # Vectorized prediction (if model supports it) or loop
        signals = []
        for i in range(len(df_features)):
            obs = df_features.iloc[i].values
            direction, confidence, _ = model.predict(obs)
            signals.append((direction, confidence))

        df_features["signal_dir"] = [s[0] for s in signals]
        df_features["signal_conf"] = [s[1] for s in signals]

        # 3. Execution Simulation
        results = self._simulate_trades(df, df_features, execution_filter)

        # 4. Metric Calculation
        return self._calculate_performance(results, df.index.min(), df.index.max())

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        model_factory: any,
        feature_engineer: any,
        execution_filter: any,
        train_window_bars: int,
        test_window_bars: int,
    ) -> List[PerformanceReport]:
        """Execute walk-forward analysis."""
        reports = []
        total_bars = len(df)

        start_idx = 0
        while start_idx + train_window_bars + test_window_bars <= total_bars:
            train_df = df.iloc[start_idx : start_idx + train_window_bars]
            test_df = df.iloc[
                start_idx + train_window_bars : start_idx + train_window_bars + test_window_bars
            ]

            # Train model (placeholder for model training logic)
            model = model_factory()
            if hasattr(model, "train"):
                model.train(train_df, feature_engineer)

            # Run backtest on test window
            report = self.run(test_df, model, feature_engineer, execution_filter)
            reports.append(report)

            start_idx += test_window_bars

        return reports

    def _simulate_trades(
        self,
        df: pd.DataFrame,
        df_features: pd.DataFrame,
        execution_filter: any,
    ) -> List[TradeResult]:
        """Simulate trades including SL/TP and costs."""
        results = []
        in_position = False
        current_trade = None

        # contract size for XAUUSD is usually 100
        contract_size = 100

        for i in range(len(df)):
            row = df.iloc[i]
            feat_row = df_features.iloc[i]

            if not in_position:
                # Check for entry
                if feat_row["signal_dir"] != 0:
                    # Apply execution filter
                    from src.trading.risk_manager import TradeSignal
                    # Dummy signal for filter
                    tmp_signal = TradeSignal(
                        symbol=self.symbol,
                        direction=int(feat_row["signal_dir"]),
                        entry_price=row["close"],
                        stop_loss=0, # determined later or by model
                        take_profit=0,
                        lot_size=0.1, # dummy
                        algorithm="backtest",
                        confidence=feat_row["signal_conf"]
                    )

                    decision = execution_filter.filter(tmp_signal, df.iloc[:i+1])
                    if decision.is_approved:
                        in_position = True
                        direction = int(feat_row["signal_dir"])
                        entry_price = row["close"] + (direction * self.spread / 2)

                        # Calculate SL/TP (e.g. 2x ATR for SL)
                        # Assume ATR is in feat_row
                        atr = feat_row.get("atr", 1.0)
                        sl = entry_price - direction * (2 * atr)
                        tp = entry_price + direction * (4 * atr)

                        current_trade = {
                            "symbol": self.symbol,
                            "direction": direction,
                            "entry_time": df.index[i],
                            "entry_price": entry_price,
                            "sl": sl,
                            "tp": tp,
                            "lot_size": 0.1, # Fixed for now or use risk manager
                            "max_favorable": entry_price,
                            "max_adverse": entry_price,
                            "algorithm": "ensemble",
                            "confidence": feat_row["signal_conf"]
                        }
            else:
                # Update MAE / MFE
                if current_trade["direction"] == 1:
                    current_trade["max_favorable"] = max(current_trade["max_favorable"], row["high"])
                    current_trade["max_adverse"] = min(current_trade["max_adverse"], row["low"])
                else:
                    current_trade["max_favorable"] = min(current_trade["max_favorable"], row["low"])
                    current_trade["max_adverse"] = max(current_trade["max_adverse"], row["high"])

                # Check for exit
                exit_price = None
                reason = ""

                if current_trade["direction"] == 1:
                    if row["low"] <= current_trade["sl"]:
                        exit_price = current_trade["sl"]
                        reason = "SL"
                    elif row["high"] >= current_trade["tp"]:
                        exit_price = current_trade["tp"]
                        reason = "TP"
                else:
                    if row["high"] >= current_trade["sl"]:
                        exit_price = current_trade["sl"]
                        reason = "SL"
                    elif row["low"] <= current_trade["tp"]:
                        exit_price = current_trade["tp"]
                        reason = "TP"

                # Time exit or signal reversal exit could be added here

                if exit_price:
                    # Apply costs
                    exit_price_adj = exit_price - (current_trade["direction"] * self.spread / 2)
                    gross_pnl = (exit_price_adj - current_trade["entry_price"]) * current_trade["direction"] * current_trade["lot_size"] * contract_size
                    net_pnl = gross_pnl - (self.commission * current_trade["lot_size"])

                    mae = abs(current_trade["max_adverse"] - current_trade["entry_price"])
                    mfe = abs(current_trade["max_favorable"] - current_trade["entry_price"])

                    results.append(TradeResult(
                        symbol=current_trade["symbol"],
                        direction=current_trade["direction"],
                        entry_time=current_trade["entry_time"],
                        exit_time=df.index[i],
                        entry_price=current_trade["entry_price"],
                        exit_price=exit_price_adj,
                        lot_size=current_trade["lot_size"],
                        pnl=net_pnl,
                        mae=mae,
                        mfe=mfe,
                        algorithm=current_trade["algorithm"],
                        confidence=current_trade["confidence"]
                    ))
                    in_position = False
                    current_trade = None

        return results

    def _calculate_performance(
        self,
        results: List[TradeResult],
        start_date: datetime,
        end_date: datetime,
    ) -> PerformanceReport:
        """Calculate aggregate performance metrics."""
        if not results:
            return PerformanceReport(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, start_date, end_date)

        pnls = np.array([t.pnl for t in results])
        total_pnl = pnls.sum()
        total_trades = len(results)
        win_rate = np.sum(pnls > 0) / total_trades

        # Profit Factor
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Equity Curve
        equity_curve = self.initial_balance + np.cumsum(pnls)
        equity_curve = np.insert(equity_curve, 0, self.initial_balance)

        # Max Drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        max_dd = drawdown.max()

        # Annualized Return
        days = (end_date - start_date).days
        if days > 0:
            total_return = (equity_curve[-1] - self.initial_balance) / self.initial_balance
            annualized_return = (1 + total_return) ** (365 / days) - 1
        else:
            annualized_return = 0.0

        # Sharpe Ratio
        # Using daily-resampled returns would be better, but approximating with trade returns
        if len(pnls) > 1:
            mean_ret = pnls.mean()
            std_ret = pnls.std()
            sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        else:
            sharpe = 0.0

        return PerformanceReport(
            annualized_return=float(annualized_return),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            profit_factor=float(profit_factor),
            total_trades=total_trades,
            win_rate=float(win_rate),
            total_pnl=float(total_pnl),
            start_date=start_date,
            end_date=end_date
        )
