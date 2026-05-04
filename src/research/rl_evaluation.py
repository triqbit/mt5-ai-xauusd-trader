"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Institutional-grade RL agent evaluation framework.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats

from src.core.constants import SignalDirection
from src.models.regime_detector import MarketRegime, RegimeDetector

logger = logging.getLogger(__name__)


class RLModel(Protocol):
    """Protocol for RL agents to ensure consistent evaluation."""

    def predict(self, observation: np.ndarray) -> Any:
        ...


class StabilityMetrics(BaseModel):
    """Metrics assessing the consistency and risk-adjusted returns."""
    sharpe_ratio: float = Field(..., description="Annualized Sharpe Ratio")
    sortino_ratio: float = Field(..., description="Annualized Sortino Ratio")
    volatility: float = Field(..., description="Annualized volatility")
    calmar_ratio: float = Field(..., description="Return / Max Drawdown")
    expectancy: float = Field(..., description="Expected profit per trade")
    profit_factor: float = Field(..., description="Gross Profit / Gross Loss")
    stability_score: float = Field(..., description="Metric for consistency of returns (R-squared)")
    skewness: float = Field(default=0.0, description="Skewness of return distribution")
    kurtosis: float = Field(default=0.0, description="Kurtosis of return distribution")
    var_95: float = Field(default=0.0, description="Value at Risk (95%)")
    cvar_95: float = Field(default=0.0, description="Conditional Value at Risk (95%)")
    max_consecutive_losses: int = Field(default=0, description="Max sequence of losing trades")


class TurnoverMetrics(BaseModel):
    """Metrics assessing trading activity and execution costs."""
    trade_frequency: float = Field(..., description="Number of trades per 1000 steps")
    avg_hold_time: float = Field(..., description="Average steps per trade")
    max_hold_time: int = Field(default=0, description="Maximum steps held for a single trade")
    min_hold_time: int = Field(default=0, description="Minimum steps held for a single trade")
    total_trades: int
    turnover_ratio: float = Field(..., description="Total traded volume relative to balance")


class DrawdownMetrics(BaseModel):
    """Metrics assessing downside risk and recovery."""
    max_drawdown: float = Field(..., description="Maximum peak-to-trough decline")
    max_drawdown_duration: int = Field(..., description="Maximum steps spent in drawdown")
    avg_drawdown: float = Field(..., description="Average drawdown depth")


class RegimePerformance(BaseModel):
    """Performance metrics segmented by market regime."""
    regime: MarketRegime
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    recovery_factor: float = Field(default=0.0, description="Total PnL / Max Drawdown for this regime")
    max_drawdown: float = Field(default=0.0, description="Max drawdown encountered in this regime")


class RewardDecomposition(BaseModel):
    """Breakdown of returns into gross profit and costs."""
    gross_pnl: float
    net_pnl: float
    total_commissions: float
    commission_drag: float = Field(..., description="Percentage impact of commissions on gross returns")
    avg_win: float = Field(default=0.0, description="Average profit of winning trades")
    avg_loss: float = Field(default=0.0, description="Average loss of losing trades")
    profit_concentration: float = Field(default=0.0, description="Ratio of top 10% of trades to total net profit")


class RLReport(BaseModel):
    """Final aggregate evaluation report for an RL agent."""
    agent_name: str
    total_steps: int
    stability: StabilityMetrics
    turnover: TurnoverMetrics
    drawdown: DrawdownMetrics
    regime_sensitivity: List[RegimePerformance]
    reward_decomposition: RewardDecomposition
    overall_win_rate: float


class RLComparison(BaseModel):
    """Comparative report across multiple agents."""
    baseline_name: str
    agent_reports: List[RLReport]
    performance_gap_pct: float = Field(..., description="Gap between best RL agent and baseline")
    best_agent: str


class MomentumBaseline:
    """Rule-based momentum baseline for RL comparison."""

    def __init__(self, window: int = 14):
        self.window = window

    def predict(self, observation: np.ndarray) -> int:
        """
        Simple momentum: if current price > price N steps ago, buy.
        Note: This expects the observation to contain historical prices.
        In TradingEnv, observations are normalized windows [window_size, n_features].
        Close price is at index 3 in each step's features.
        """
        # Observation format from TradingEnv: [window_normalized_flattened, balance, position]
        # To get the last close, we need to know n_features.
        # However, if we don't know it, we can guess from observation size.
        # Typical window_size=60, n_features=5 -> 300 + 2 = 302 elements.
        # The last step of the window starts at (window_size - 1) * n_features.
        # But we can also look at the relative index from the end.
        # balance is -2, position is -1.
        # The last step's features are from -(n_features+2) to -3.
        # If n_features=5 (OHLCV), close is 4th feature (index 3).
        # So last close is at -(5+2) + 3 = -4.

        # Let's use a more robust way: assume 5 features if not specified.
        n_features = 5
        last_close_idx = -(n_features + 2) + 3

        if len(observation) < abs(last_close_idx):
            return 0

        last_val = observation[last_close_idx]
        if last_val > 0.2:  # Reduced threshold for normalized values
            return 1  # Buy
        elif last_val < -0.2:
            return 2  # Sell
        return 0  # Hold


class MeanReversionBaseline:
    """Rule-based Mean Reversion baseline for RL comparison."""

    def __init__(self, window: int = 14):
        self.window = window

    def predict(self, observation: np.ndarray) -> int:
        # Simplified RSI-like logic on normalized values
        # Normalized values already represent distance from mean.
        # If last close is very high relative to window mean, sell.
        n_features = 5
        last_close_idx = -(n_features + 2) + 3

        if len(observation) < abs(last_close_idx):
            return 0

        last_val = observation[last_close_idx]
        if last_val > 1.5:  # Overbought
            return 2  # Sell
        elif last_val < -1.5:  # Oversold
            return 1  # Buy
        return 0


class RandomBaseline:
    """Random baseline for RL comparison."""

    def predict(self, observation: np.ndarray) -> int:
        return np.random.choice([0, 1, 2])


class SupervisedBaseline:
    """Wrapper for supervised models to compare against RL agents."""

    def __init__(self, model: Any):
        self.model = model

    def predict(self, observation: np.ndarray) -> int:
        # Assuming supervised model returns 0, 1, 2
        # We might need to reshape observation for the model
        obs_reshaped = observation.reshape(1, -1)
        action = self.model.predict(obs_reshaped)
        if isinstance(action, np.ndarray):
            return int(action[0])
        return int(action)


class RLEvaluator:
    """
    Evaluator for RL agents with institutional metrics.
    Analyzes performance beyond simple reward, focusing on stability,
    turnover, and regime sensitivity.
    """

    def __init__(
        self,
        env: Any,
        regime_detector: Optional[RegimeDetector] = None,
        annualization_factor: int = 252,
    ):
        self.env = env
        self.regime_detector = regime_detector or RegimeDetector()
        self.annualization_factor = annualization_factor

    def evaluate(self, agent: RLModel, agent_name: str = "RL_Agent") -> RLReport:
        """
        Run a full evaluation of the agent and generate a typed report.
        Tracks mark-to-market equity for institutional-grade return analysis.
        """
        obs, _ = self.env.reset()
        done = False

        history = {
            "steps": [],
            "actions": [],
            "rewards": [],
            "balances": [],  # This will store Mark-to-Market Equity
            "positions": [],
            "regimes": [],
            "commissions": [],
        }

        step_idx = 0
        while not done:
            action = self._get_prediction(agent, obs)
            next_obs, reward, terminated, truncated, info = self.env.step(action)

            # Detect market regime
            current_regime = MarketRegime.UNKNOWN
            current_price = 0.0
            if hasattr(self.env, "data") and hasattr(self.env, "current_step"):
                data = self.env.data
                current_step = self.env.current_step
                current_price = data[current_step - 1, 3] # Close price

                if current_step >= 100:
                    df_slice = pd.DataFrame(
                        data[current_step - 100 : current_step],
                        columns=["open", "high", "low", "close", "tick_volume"]
                    )
                    current_regime = self.regime_detector.detect(df_slice).label

            # Calculate Mark-to-Market Equity
            # Equity = Realized Balance + Unrealized PnL
            realized_balance = info["balance"]
            position = info["position"]
            unrealized_pnl = 0.0
            if position != 0 and hasattr(self.env, "entry_price"):
                # Simplified: assuming 1.0 lot size and direct price diff (XAUUSD-like)
                # In a real environment, this should use the environment's own equity calculation if available
                unrealized_pnl = (current_price - self.env.entry_price) * position

            mtm_equity = realized_balance + unrealized_pnl

            history["steps"].append(step_idx)
            history["actions"].append(action)
            history["rewards"].append(reward)
            history["balances"].append(mtm_equity)
            history["positions"].append(position)
            history["regimes"].append(current_regime)
            history["commissions"].append(info.get("cumulative_commissions", 0.0))

            obs = next_obs
            done = terminated or truncated
            step_idx += 1

        df_history = pd.DataFrame(history)

        return self._generate_report(agent_name, df_history)

    def compare(
        self, agents: List[Any], agent_names: List[str], baseline_name: str = "Momentum"
    ) -> RLComparison:
        """Compare multiple agents against a baseline."""
        reports = []
        for agent, name in zip(agents, agent_names, strict=True):
            reports.append(self.evaluate(agent, name))

        # Find baseline report
        baseline_report = next((r for r in reports if r.agent_name == baseline_name), None)
        if not baseline_report:
            # If baseline not in list, run it separately
            baseline_agent = MomentumBaseline()
            baseline_report = self.evaluate(baseline_agent, baseline_name)
            reports.append(baseline_report)

        # Calculate performance gap and best agent
        best_report = max(reports, key=lambda r: r.stability.sharpe_ratio)
        baseline_sharpe = baseline_report.stability.sharpe_ratio
        best_sharpe = best_report.stability.sharpe_ratio

        gap = ((best_sharpe - baseline_sharpe) / abs(baseline_sharpe) * 100) if baseline_sharpe != 0 else 0.0

        return RLComparison(
            baseline_name=baseline_name,
            agent_reports=reports,
            performance_gap_pct=float(gap),
            best_agent=best_report.agent_name,
        )

    def to_report_section(self, comparison: RLComparison) -> Any:
        """
        Convert RLComparison into an RLSection for the ResearchReporter.
        """
        from src.research.reporting import RLMetric, RLSection

        metrics = []
        for report in comparison.agent_reports:
            metrics.append(
                RLMetric(
                    agent_name=report.agent_name,
                    sharpe=report.stability.sharpe_ratio,
                    profit_factor=report.stability.profit_factor,
                    max_dd=report.drawdown.max_drawdown,
                    win_rate=report.overall_win_rate,
                    calmar=report.stability.calmar_ratio,
                    stability_score=report.stability.stability_score,
                    var_95=report.stability.var_95,
                )
            )

        summary = (
            f"Evaluated {len(comparison.agent_reports)} agents against {comparison.baseline_name} baseline. "
            f"Best performer: {comparison.best_agent} with a {comparison.performance_gap_pct:.2f}% "
            "improvement in Sharpe ratio over baseline."
        )

        return RLSection(
            comparison_summary=summary,
            best_agent=comparison.best_agent,
            performance_gap=comparison.performance_gap_pct,
            metrics=metrics,
        )

    def _get_prediction(self, agent: Any, obs: np.ndarray) -> int:
        """Translate agent prediction (int or Signal) into environment action."""
        prediction = agent.predict(obs)

        # Handle Signal objects (standardized model output)
        if hasattr(prediction, "direction"):
            if prediction.direction == SignalDirection.BUY:
                return 1
            if prediction.direction == SignalDirection.SELL:
                return 2
            return 0

        # Handle raw integer actions
        return int(prediction)

    def _generate_report(self, agent_name: str, df: pd.DataFrame) -> RLReport:
        """Calculate all metrics and return an RLReport."""
        trades = self._extract_trades(df)
        drawdown = self._calculate_drawdown(df)
        stability = self._calculate_stability(df, trades, drawdown.max_drawdown)
        turnover = self._calculate_turnover(df, trades)
        regime_sensitivity = self._calculate_regime_sensitivity(df)
        reward_decomp = self._calculate_reward_decomposition(df, trades)

        trade_pnls = [t["pnl"] for t in trades]
        win_rate = len([p for p in trade_pnls if p > 0]) / len(trade_pnls) if trade_pnls else 0.0

        return RLReport(
            agent_name=agent_name,
            total_steps=len(df),
            stability=stability,
            turnover=turnover,
            drawdown=drawdown,
            regime_sensitivity=regime_sensitivity,
            reward_decomposition=reward_decomp,
            overall_win_rate=win_rate,
        )

    def _extract_trades(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract detailed trade information from history.
        Each trade contains: pnl, hold_time.
        Uses total PnL from entry to exit.
        """
        trades = []
        balances = df["balances"].values
        positions = df["positions"].values

        entry_idx = 0
        for i in range(1, len(df)):
            # Entry detected
            if positions[i-1] == 0 and positions[i] != 0:
                entry_idx = i
            # Exit detected
            elif positions[i-1] != 0 and positions[i] == 0:
                # PnL is the change in MtM equity from the step BEFORE entry to the exit step
                pnl = balances[i] - balances[entry_idx - 1]
                hold_time = i - entry_idx
                trades.append({"pnl": float(pnl), "hold_time": int(hold_time)})

        return trades

    def _calculate_stability(
        self, df: pd.DataFrame, trades: List[Dict[str, Any]], max_dd: float
    ) -> StabilityMetrics:
        """Assess the consistency and risk-adjusted returns with institutional metrics."""
        returns = df["balances"].pct_change().replace([np.inf, -np.inf], 0).fillna(0)
        # Filter out first zero return from pct_change
        returns = returns.iloc[1:]

        if len(returns) < 2:
            return StabilityMetrics(
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                volatility=0.0,
                calmar_ratio=0.0,
                expectancy=0.0,
                profit_factor=0.0,
                stability_score=0.0,
            )

        mean_ret = returns.mean()
        std_ret = returns.std()

        sharpe = (
            (mean_ret / std_ret * np.sqrt(self.annualization_factor)) if std_ret > 0 else 0.0
        )

        downside_ret = returns[returns < 0]
        downside_std = downside_ret.std() if len(downside_ret) > 1 else std_ret
        sortino = (
            (mean_ret / downside_std * np.sqrt(self.annualization_factor))
            if downside_std > 0
            else 0.0
        )

        vol = std_ret * np.sqrt(self.annualization_factor)

        # Calmar Ratio
        total_return = (
            (df["balances"].iloc[-1] - df["balances"].iloc[0]) / df["balances"].iloc[0]
            if len(df) > 0 and df["balances"].iloc[0] != 0
            else 0.0
        )
        calmar = total_return / max_dd if max_dd > 0 else 0.0

        # Expectancy and Profit Factor
        trade_pnls = [t["pnl"] for t in trades]
        wins = [p for p in trade_pnls if p > 0]
        losses = [abs(p) for p in trade_pnls if p < 0]

        profit_factor = (
            sum(wins) / sum(losses)
            if sum(losses) > 0
            else (float("inf") if sum(wins) > 0 else 1.0)
        )

        win_rate = len(wins) / len(trade_pnls) if trade_pnls else 0.0
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        expectancy = (avg_win * win_rate) - (avg_loss * (1 - win_rate))

        # Stability score: consistency of equity curve (R-squared of linear fit)
        x = np.arange(len(df))
        y = df["balances"].values
        slope, intercept = np.polyfit(x, y, 1)
        line = slope * x + intercept
        y_var = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - (np.sum((y - line) ** 2) / (y_var + 1e-9))

        # Institutional Stats: Skew, Kurtosis, VaR, CVaR
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)
        var_95 = np.percentile(returns, 5) if len(returns) > 20 else 0.0
        cvar_95 = returns[returns <= var_95].mean() if len(returns) > 20 else 0.0

        # Max consecutive losses
        max_consecutive_losses = 0
        current_consecutive_losses = 0
        for p in trade_pnls:
            if p < 0:
                current_consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
            else:
                current_consecutive_losses = 0

        return StabilityMetrics(
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            volatility=float(vol),
            calmar_ratio=float(calmar),
            expectancy=float(expectancy),
            profit_factor=float(profit_factor),
            stability_score=float(r_squared),
            skewness=float(skew),
            kurtosis=float(kurt),
            var_95=float(var_95),
            cvar_95=float(cvar_95),
            max_consecutive_losses=int(max_consecutive_losses),
        )

    def _calculate_turnover(self, df: pd.DataFrame, trades: List[Dict[str, Any]]) -> TurnoverMetrics:
        """Assess trading activity and execution costs."""
        num_trades = len(trades)
        hold_times = [t["hold_time"] for t in trades]

        avg_hold_time = np.mean(hold_times) if hold_times else 0.0
        max_hold_time = np.max(hold_times) if hold_times else 0
        min_hold_time = np.min(hold_times) if hold_times else 0

        trade_freq = (num_trades / len(df)) * 1000 if len(df) > 0 else 0.0

        # Turnover ratio: rough estimate of traded volume relative to initial balance
        # In this env, each trade is 1.0 unit.
        turnover_ratio = (num_trades * 1.0) / (df["balances"].iloc[0]) if len(df) > 0 else 0.0

        return TurnoverMetrics(
            trade_frequency=float(trade_freq),
            avg_hold_time=float(avg_hold_time),
            max_hold_time=int(max_hold_time),
            min_hold_time=int(min_hold_time),
            total_trades=num_trades,
            turnover_ratio=float(turnover_ratio)
        )

    def _calculate_drawdown(self, df: pd.DataFrame) -> DrawdownMetrics:
        """Assess downside risk and recovery."""
        balances = df["balances"].values
        peak = np.maximum.accumulate(balances)
        drawdowns = (peak - balances) / peak

        max_dd = np.max(drawdowns)
        avg_dd = np.mean(drawdowns[drawdowns > 0]) if np.any(drawdowns > 0) else 0.0

        # Max drawdown duration
        is_in_dd = drawdowns > 0
        dd_durations = []
        current_dur = 0
        for in_dd in is_in_dd:
            if in_dd:
                current_dur += 1
            else:
                if current_dur > 0:
                    dd_durations.append(current_dur)
                current_dur = 0
        if current_dur > 0:
            dd_durations.append(current_dur)

        max_dd_dur = max(dd_durations) if dd_durations else 0

        return DrawdownMetrics(
            max_drawdown=float(max_dd),
            max_drawdown_duration=int(max_dd_dur),
            avg_drawdown=float(avg_dd)
        )

    def _calculate_regime_sensitivity(self, df: pd.DataFrame) -> List[RegimePerformance]:
        """Performance metrics segmented by market regime with recovery analysis."""
        regime_stats = []
        unique_regimes = df["regimes"].unique()

        for regime in unique_regimes:
            if regime == MarketRegime.UNKNOWN:
                continue

            regime_df = df[df["regimes"] == regime]
            if len(regime_df) < 10:  # Ignore regimes with too little data
                continue

            returns = regime_df["balances"].pct_change().replace([np.inf, -np.inf], 0).fillna(0)
            sharpe = (returns.mean() / returns.std() * np.sqrt(self.annualization_factor)) if len(returns) > 1 and returns.std() > 0 else 0.0

            # Extract trades within this regime
            regime_pnls = []
            balances = df["balances"].values
            positions = df["positions"].values
            regimes = df["regimes"].values

            entry_idx = 0
            for i in range(1, len(df)):
                if positions[i-1] == 0 and positions[i] != 0:
                    entry_idx = i
                elif positions[i-1] != 0 and positions[i] == 0 and regimes[entry_idx] == regime:
                    pnl = balances[i] - balances[entry_idx - 1]
                    regime_pnls.append(pnl)

            win_rate = len([p for p in regime_pnls if p > 0]) / len(regime_pnls) if regime_pnls else 0.0

            # Profit factor: sum(profits) / abs(sum(losses))
            profits = sum([p for p in regime_pnls if p > 0])
            losses = abs(sum([p for p in regime_pnls if p < 0]))
            profit_factor = profits / losses if losses > 0 else (float('inf') if profits > 0 else 1.0)

            # Max drawdown within this regime
            regime_bals = regime_df["balances"].values
            peak = np.maximum.accumulate(regime_bals)
            drawdowns = (peak - regime_bals) / (peak + 1e-9)
            regime_max_dd = np.max(drawdowns)

            # Recovery factor
            total_regime_pnl = regime_bals[-1] - regime_bals[0]
            recovery_factor = total_regime_pnl / (regime_max_dd * regime_bals[0] + 1e-9) if regime_max_dd > 0 else 1.0

            regime_stats.append(RegimePerformance(
                regime=regime,
                sharpe_ratio=float(sharpe),
                win_rate=float(win_rate),
                total_trades=len(regime_pnls),
                profit_factor=float(profit_factor),
                recovery_factor=float(recovery_factor),
                max_drawdown=float(regime_max_dd),
            ))

        return regime_stats

    def _calculate_reward_decomposition(self, df: pd.DataFrame, trades: List[Dict[str, Any]]) -> RewardDecomposition:
        """Breakdown of returns into gross profit and costs, with concentration analysis."""
        total_commissions = df["commissions"].iloc[-1] if len(df) > 0 else 0.0
        final_pnl = df["balances"].iloc[-1] - df["balances"].iloc[0] if len(df) > 0 else 0.0

        net_pnl = final_pnl
        gross_pnl = net_pnl + total_commissions

        comm_drag = (total_commissions / (gross_pnl + 1e-9) * 100) if gross_pnl > 0 else 0.0

        trade_pnls = [t["pnl"] for t in trades]
        wins = [p for p in trade_pnls if p > 0]
        losses = [abs(p) for p in trade_pnls if p < 0]

        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        # Profit Concentration: Ratio of top 10% of trades to total net profit
        # If net_pnl is negative, concentration is less meaningful but we still calculate.
        profit_concentration = 0.0
        if trade_pnls and net_pnl > 0:
            sorted_pnls = sorted(trade_pnls, reverse=True)
            top_n = max(1, int(len(sorted_pnls) * 0.1))
            top_profit = sum(sorted_pnls[:top_n])
            profit_concentration = top_profit / net_pnl

        return RewardDecomposition(
            gross_pnl=float(gross_pnl),
            net_pnl=float(net_pnl),
            total_commissions=float(total_commissions),
            commission_drag=float(comm_drag),
            avg_win=float(avg_win),
            avg_loss=float(avg_loss),
            profit_concentration=float(profit_concentration),
        )


