"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/backtester.py

Efficient walk-forward backtesting engine with institutional metrics.
Uses a hybrid vectorized approach:
- Vectorized feature engineering and indicator calculations.
- Vectorized SL/TP exit simulation for high performance.
- Iterative loop for signal evaluation and execution filter validation.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import structlog

from src.core.audit_log import get_audit_logger
from src.core.feature_engineering import FeatureEngineer
from src.core.profiler import profile
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceReport:
    """Institutional-grade backtest performance report matching benchmark standards."""

    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    recovery_factor: float = 0.0
    mae_avg: float = 0.0  # Maximum Adverse Excursion
    mfe_avg: float = 0.0  # Maximum Favorable Excursion
    total_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    start_date: datetime | None = None
    end_date: datetime | None = None


@dataclass
class BacktestTrade:
    """Detailed record of a trade executed during backtest for audit and analysis."""

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
        # Disable internal normalization to handle it per-window in walk-forward
        self.fe = feature_engineer or FeatureEngineer(normalize=False)
        self.ef = execution_filter or ExecutionFilter()
        self.max_positions = max_positions

        self.balance = initial_balance
        self.max_equity = initial_balance
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[tuple[datetime, float]] = []
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
        Optimized via vectorized pre-calculations and future-scanning exit simulation.
        """
        start_wall_time = time.perf_counter()
        logger.info(
            "Starting walk-forward backtest",
            train=train_window,
            test=test_window,
            step=step_size,
        )

        try:
            audit = get_audit_logger()
            audit.log(
                actor="system",
                action="backtest_started",
                details=f"Symbol: {self.symbol}, Data points: {len(data)}",
                metadata={
                    "symbol": self.symbol,
                    "train_window": train_window,
                    "test_window": test_window,
                    "step_size": step_size,
                    "data_length": len(data),
                },
            )
        except Exception:
            # AuditLogger might not be initialized in all environments (e.g. simple unit tests)
            logger.debug("AuditLogger not available - skipping backtest_started log")

        # 1. Pre-calculate all possible features for the entire dataset
        logger.info("Pre-calculating features for the entire dataset...")
        # Ensure we get raw features for proper walk-forward normalization
        original_norm = self.fe.normalize
        self.fe.normalize = False

        with profile("bt_feature_engineering_total"):
            df_features = self.fe.compute_features(data, drop_ohlcv=False)
        self.fe.normalize = original_norm

        if df_features.empty:
            logger.error("Feature engineering returned empty DataFrame. Insufficient data?")
            return PerformanceReport()

        # Align raw data with engineered features (FeatureEngineer might drop rows)
        data = data.loc[df_features.index].copy()
        n = len(data)

        if n < train_window + test_window:
            logger.error("Insufficient data for walk-forward: %d bars available", n)
            return PerformanceReport()

        # 2. Pre-calculate metrics for the ExecutionFilter to avoid O(N) in loop
        logger.info("Pre-calculating execution filter metrics...")

        with profile("bt_ef_precomputation_total"):
            # Calculate ATR for SL/TP and Volatility filter
            high_low = data["high"] - data["low"]
            high_close = (data["high"] - data["close"].shift(1)).abs()
            low_close = (data["low"] - data["close"].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            data["atr"] = tr.rolling(14).mean()

            prefix = f"base_{self.fe.base_timeframe}"
            atr_series = data["atr"]
            avg_atr_series = atr_series.rolling(window=100).mean()
            atr_current_vals = atr_series.values
            atr_avg_vals = avg_atr_series.values

            # Trend Angle (EMA21 Slope) via vectorized convolution
            ema21_col = f"{prefix}_ema_21"
            if ema21_col in df_features.columns:
                ema21_series = df_features[ema21_col]
            else:
                ema21_series = data["close"].ewm(span=21, adjust=False).mean()

            ema21_vals = ema21_series.values
            window = 20
            x = np.arange(window)
            weights = (x - np.mean(x)) / (np.var(x) * window + 1e-8)
            # Vectorized rolling slope (O(N) vs O(N*W))
            if n >= window:
                conv = np.convolve(ema21_vals, weights[::-1], mode="valid")
                slopes = np.concatenate([np.zeros(window - 1), conv])
            else:
                slopes = np.zeros(n)

            # Pre-extract EMAs for Layer 3 check
            ema_vals = {}
            for p in [8, 21, 50, 200]:
                col = f"{prefix}_ema_{p}"
                if col in df_features.columns:
                    ema_vals[p] = df_features[col].values
                else:
                    ema_vals[p] = data["close"].ewm(span=p, adjust=False).mean().values

            # Pre-calculate RSI for Layer 4 check
            rsi_col = f"{prefix}_rsi"
            if rsi_col in df_features.columns:
                rsi_vals = df_features[rsi_col].values
            else:
                delta = data["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rsi_vals = (100 - (100 / (1 + (gain / (loss + 1e-8))))).values

        # 3. Main Walk-Forward Loop
        start = 0
        active_trades: list[dict[str, Any]] = []
        last_processed_idx = -1

        # Optimization: Pre-extract data into NumPy arrays for fast access
        high_vals = data["high"].values
        low_vals = data["low"].values
        close_vals = data["close"].values
        atr_vals = data["atr"].values
        time_vals = data.index

        # Feature matrix for model prediction
        cols_to_exclude = ["open", "high", "low", "close", "tick_volume", "atr", "real_volume"]
        feature_cols = [c for c in df_features.columns if c not in cols_to_exclude]
        feature_vals = df_features[feature_cols].values

        # Lightweight timing accumulators for institutional performance analysis
        stats_timers = {
            "normalization": 0.0,
            "inference": 0.0,
            "execution_filter": 0.0,
            "trade_simulation": 0.0,
            "equity_tracking": 0.0,
            "update_active": 0.0,
        }

        with profile("bt_walk_forward_loop_total"):
            while start + train_window + test_window <= n:
                test_start_idx = start + train_window

                # Institutional Walk-Forward: Compute normalization stats from train window ONLY
                # to strictly prevent look-ahead bias in the test window.
                train_slice = feature_vals[start:test_start_idx]
                train_mean = np.nanmean(train_slice, axis=0)
                train_std = np.nanstd(train_slice, axis=0)
                train_std[train_std == 0] = 1.0  # Avoid division by zero

                for i in range(test_window):
                    abs_idx = test_start_idx + i

                    # Prevent double-processing bars due to step overlap
                    if abs_idx <= last_processed_idx or abs_idx >= n:
                        continue

                    bar_time = time_vals[abs_idx]
                    current_price = close_vals[abs_idx]

                    # 1. Update active trades: Check if any simulated exit is reached
                    t0 = time.perf_counter()
                    self._update_active_trades(active_trades, abs_idx)
                    stats_timers["update_active"] += time.perf_counter() - t0

                    # 2. Evaluation Logic: If slot available, check for new signals
                    if len(active_trades) < self.max_positions:
                        # Apply train-window normalization to the current observation
                        t0 = time.perf_counter()
                        obs_raw = feature_vals[abs_idx]
                        obs = (obs_raw - train_mean) / (train_std + 1e-8)
                        stats_timers["normalization"] += time.perf_counter() - t0

                        try:
                            # Standard Signal object or fallback to raw int
                            t0 = time.perf_counter()
                            signal_obj = model.predict(obs)
                            direction = int(signal_obj.direction)
                            confidence = float(signal_obj.confidence)
                            stats_timers["inference"] += time.perf_counter() - t0
                        except Exception:
                            direction, confidence = 0, 0.0

                        if direction != 0:
                            atr = atr_vals[abs_idx]
                            if not np.isnan(atr) and atr > 0:
                                # 3. Prepare Signal and Validate with Filter Cascade
                                signal = TradeSignal(
                                    symbol=self.symbol,
                                    direction=direction,
                                    entry_price=current_price,
                                    stop_loss=current_price - (direction * 2 * atr),
                                    take_profit=current_price + (direction * 4 * atr),
                                    lot_size=0.1,  # Base lot for backtest
                                    algorithm="backtest",
                                    confidence=confidence,
                                    timestamp=bar_time,
                                )

                                # Dynamic Drawdown for Layer 6 (O(1) lookup)
                                current_drawdown = 0.0
                                if self.equity_curve:
                                    peak = self.max_equity
                                    current_equity = self.equity_curve[-1][1]
                                    current_drawdown = (peak - current_equity) / (peak + 1e-8)

                                # Pack precomputed metrics for speed
                                precomputed = {
                                    "atr_volatility": {
                                        "current_atr": atr_current_vals[abs_idx],
                                        "avg_atr": atr_avg_vals[abs_idx],
                                    },
                                    "trend_angle": {"slope": slopes[abs_idx]},
                                    "ema_sequence": {
                                        "emas": {p: ema_vals[p][abs_idx] for p in [8, 21, 50, 200]}
                                    },
                                    "momentum": {"rsi": rsi_vals[abs_idx]},
                                }

                                # Validate signal through 10-layer filter
                                # Optimization: market_data=None because we use precomputed_metrics
                                t0 = time.perf_counter()
                                decision = self.ef.validate(
                                    signal,
                                    market_data=None,
                                    current_drawdown=current_drawdown,
                                    timestamp=bar_time,
                                    precomputed_metrics=precomputed,
                                )
                                stats_timers["execution_filter"] += time.perf_counter() - t0

                                if decision.is_approved:
                                    # Vectorized Exit Simulation: Scan future bars for SL/TP hit
                                    t0 = time.perf_counter()
                                    self._open_and_simulate_trade(
                                        active_trades,
                                        signal,
                                        abs_idx,
                                        high_vals,
                                        low_vals,
                                        time_vals,
                                    )
                                    stats_timers["trade_simulation"] += time.perf_counter() - t0

                    # 4. Record equity at the end of each bar
                    t0 = time.perf_counter()
                    self._record_equity(bar_time, current_price, active_trades)
                    stats_timers["equity_tracking"] += time.perf_counter() - t0
                    last_processed_idx = abs_idx

                start += step_size

        # Log lightweight performance summary
        total_loop_time = sum(stats_timers.values())
        logger.info(
            "backtest_loop_performance_breakdown",
            total_loop_ms=round(total_loop_time * 1000, 2),
            normalization_ms=round(stats_timers["normalization"] * 1000, 2),
            inference_ms=round(stats_timers["inference"] * 1000, 2),
            execution_filter_ms=round(stats_timers["execution_filter"] * 1000, 2),
            trade_simulation_ms=round(stats_timers["trade_simulation"] * 1000, 2),
            equity_tracking_ms=round(stats_timers["equity_tracking"] * 1000, 2),
            update_active_ms=round(stats_timers["update_active"] * 1000, 2),
        )

        # 4. Finalization: Close any trailing trades
        self._close_all_trades(active_trades, close_vals[-1], time_vals[-1])
        report = self._calculate_performance()

        duration = time.perf_counter() - start_wall_time
        try:
            audit = get_audit_logger()
            audit.log(
                actor="system",
                action="backtest_completed",
                details=f"Backtest completed in {duration:.2f}s | Trades: {report.total_trades}",
                metadata={
                    "symbol": self.symbol,
                    "duration_seconds": duration,
                    "total_trades": report.total_trades,
                    "annualized_return": report.annualized_return,
                    "sharpe_ratio": report.sharpe_ratio,
                    "max_drawdown": report.max_drawdown,
                    "period_start": str(report.start_date),
                    "period_end": str(report.end_date),
                },
            )
        except Exception:
            logger.debug("AuditLogger not available - skipping backtest_completed log")

        return report

    def _record_equity(
        self, timestamp: datetime, current_price: float, active_trades: list[dict[str, Any]]
    ) -> None:
        """Records current portfolio equity (Balance + Unrealized PnL)."""
        unrealized_pnl = 0.0
        contract_multiplier = 100 if "XAU" in self.symbol else 1

        for t in active_trades:
            dir = int(t["signal"].direction)
            unrealized_pnl += (
                (current_price - t["entry_price"])
                * dir
                * t["signal"].lot_size
                * contract_multiplier
            )

        current_equity = self.balance + unrealized_pnl
        self.equity_curve.append((timestamp, current_equity))
        self.max_equity = max(self.max_equity, current_equity)

    def _open_and_simulate_trade(
        self,
        active_trades: list[dict[str, Any]],
        signal: TradeSignal,
        entry_idx: int,
        high_vals: np.ndarray,
        low_vals: np.ndarray,
        time_vals: pd.Index,
    ) -> None:
        """
        Calculates trade exit and metrics using vectorized future scanning.
        """
        direction = int(signal.direction)
        # Entry price adjusted for half-spread
        entry_price = signal.entry_price + (direction * self.spread / 2)
        sl, tp = signal.stop_loss, signal.take_profit

        # Subset future market data
        future_high = high_vals[entry_idx + 1 :]
        future_low = low_vals[entry_idx + 1 :]
        future_times = time_vals[entry_idx + 1 :]

        # If no future bars, trade remains open until engine closes it
        if len(future_high) == 0:
            active_trades.append(
                {
                    "signal": signal,
                    "entry_price": entry_price,
                    "mae": 0.0,
                    "mfe": 0.0,
                    "exit_abs_idx": np.inf,
                }
            )
            return

        # Vectorized hit detection
        if direction == 1:  # BUY
            sl_hit = future_low <= sl
            tp_hit = future_high >= tp
        else:  # SELL
            sl_hit = future_high >= sl
            tp_hit = future_low <= tp

        hits = sl_hit | tp_hit

        if not hits.any():
            # Trade survives until end of dataset
            active_trades.append(
                {
                    "signal": signal,
                    "entry_price": entry_price,
                    "mae": 0.0,
                    "mfe": 0.0,
                    "exit_abs_idx": np.inf,
                }
            )
            return

        # Find first exit index and price
        exit_rel_idx = np.where(hits)[0][0]
        exit_abs_idx = entry_idx + 1 + exit_rel_idx
        exit_time = future_times[exit_rel_idx]
        # Conservative assumption: hit SL first if both hit in same bar
        exit_price = sl if sl_hit[exit_rel_idx] else tp

        # Vectorized MAE/MFE calculation
        trade_highs = future_high[: exit_rel_idx + 1]
        trade_lows = future_low[: exit_rel_idx + 1]

        if direction == 1:
            mae = float(entry_price - np.min(trade_lows))
            mfe = float(np.max(trade_highs) - entry_price)
        else:
            mae = float(np.max(trade_highs) - entry_price)
            mfe = float(entry_price - np.min(trade_lows))

        # Queue trade for closing at exit_abs_idx
        active_trades.append(
            {
                "signal": signal,
                "entry_price": entry_price,
                "mae": max(0.0, mae),
                "mfe": max(0.0, mfe),
                "exit_abs_idx": exit_abs_idx,
                "exit_price": exit_price,
                "exit_time": exit_time,
            }
        )

    def _update_active_trades(self, active_trades: list[dict[str, Any]], abs_idx: int) -> None:
        """Finalizes trades whose simulated exit time has arrived."""
        closed_indices = []
        for i, t in enumerate(active_trades):
            if abs_idx >= t.get("exit_abs_idx", np.inf):
                closed_indices.append(i)

        for i in sorted(closed_indices, reverse=True):
            trade_data = active_trades.pop(i)
            self._record_trade(trade_data, trade_data["exit_price"], trade_data["exit_time"])

    def _record_trade(self, trade: dict[str, Any], exit_price: float, exit_time: datetime) -> None:
        """Calculates realized PnL and adds to permanent trade history."""
        signal = trade["signal"]
        direction = int(signal.direction)

        # Adjust exit price for spread (buy exits at bid, sell exits at ask)
        exit_price_adj = exit_price - (direction * self.spread / 2)

        contract_multiplier = 100 if "XAU" in self.symbol else 1
        raw_pnl = (
            (exit_price_adj - trade["entry_price"])
            * direction
            * signal.lot_size
            * contract_multiplier
        )

        # Transaction costs: commission
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

    def _close_all_trades(
        self, active_trades: list[dict[str, Any]], last_close: float, last_time: datetime
    ) -> None:
        """Force-close remaining positions at end of backtest."""
        for trade in active_trades:
            self._record_trade(trade, last_close, last_time)
        active_trades.clear()

    def _calculate_performance(self) -> PerformanceReport:
        """Aggregates trade history into a PerformanceReport dataclass."""
        if not self.trades or not self.equity_curve:
            return PerformanceReport()

        pnls = np.array([t.pnl for t in self.trades])
        total_return = (self.balance - self.initial_balance) / self.initial_balance
        win_rate = np.sum(pnls > 0) / len(pnls)

        gross_profit = np.sum(pnls[pnls > 0])
        gross_loss = abs(np.sum(pnls[pnls < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Max Drawdown
        equity_vals = np.array([e[1] for e in self.equity_curve])
        peak = np.maximum.accumulate(equity_vals)
        max_drawdown = np.max((peak - equity_vals) / (peak + 1e-8))

        # Sharpe Ratio
        df_equity = pd.DataFrame(self.equity_curve, columns=["time", "equity"]).set_index("time")
        daily_equity = df_equity["equity"].resample("D").last().dropna()
        if len(daily_equity) > 1:
            daily_returns = daily_equity.pct_change().dropna()
            sharpe = (daily_returns.mean() / (daily_returns.std() + 1e-8)) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Annualized Return (CAGR)
        start_time, end_time = self.equity_curve[0][0], self.equity_curve[-1][0]
        years = (end_time - start_time).total_seconds() / (365.25 * 24 * 3600)
        if years > 0:
            try:
                ann_return = float(np.power(1 + total_return, 1 / years) - 1)
            except (OverflowError, RuntimeWarning):
                ann_return = total_return
        else:
            ann_return = total_return

        # Recovery Factor (Net Profit / Max Drawdown)
        recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0.0

        report = PerformanceReport(
            annualized_return=ann_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            recovery_factor=recovery_factor,
            mae_avg=np.mean([t.mae for t in self.trades]),
            mfe_avg=np.mean([t.mfe for t in self.trades]),
            total_trades=len(self.trades),
            win_rate=win_rate,
            total_return=total_return,
            start_date=start_time,
            end_date=end_time,
        )
        self.results = report
        return report
