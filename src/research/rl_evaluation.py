"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Institutional-grade RL agent evaluation framework.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats

from src.core.constants import SignalDirection
from src.models.regime_detector import MarketRegime, RegimeDetector

logger = logging.getLogger(__name__)


class RLModel(Protocol):
    """Protocol for RL agents to ensure consistent evaluation."""

    def predict(self, observation: np.ndarray) -> Any: ...


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
    ulcer_index: float = Field(default=0.0, description="Ulcer Index (Drawdown stress metric)")
    sqn: float = Field(default=0.0, description="System Quality Number")
    tail_ratio: float = Field(default=0.0, description="Ratio of 95th percentile to 5th percentile")
    common_sense_ratio: float = Field(
        default=0.0, description="Tail Ratio * Profit Factor (institutional robustness)"
    )
    gain_to_pain_ratio: float = Field(
        default=0.0, description="Sum of gains / Abs(Sum of losses) per month/period"
    )
    regime_stability_score: float = Field(
        default=0.0, description="Consistency of performance across different market regimes"
    )
    lake_ratio: float = Field(
        default=0.0, description="Ratio of drawdown area to total duration (Lake Ratio)"
    )


class ExposureMetrics(BaseModel):
    """Metrics assessing portfolio exposure and time-at-risk."""

    avg_portfolio_heat: float = Field(
        ..., description="Average time-weighted position size (lots/units)"
    )
    max_portfolio_heat: float = Field(..., description="Maximum position size held")
    time_at_risk_pct: float = Field(
        ..., description="Percentage of time spent with an open position"
    )


class TurnoverMetrics(BaseModel):
    """Metrics assessing trading activity and execution costs."""

    trade_frequency: float = Field(..., description="Number of trades per 1000 steps")
    avg_hold_time: float = Field(..., description="Average steps per trade")
    max_hold_time: int = Field(default=0, description="Maximum steps held for a single trade")
    min_hold_time: int = Field(default=0, description="Minimum steps held for a single trade")
    total_trades: int
    turnover_ratio: float = Field(..., description="Total traded volume relative to balance")
    action_entropy: float = Field(
        default=0.0, description="Entropy of action distribution (detects policy collapse)"
    )


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
    recovery_factor: float = Field(
        default=0.0, description="Total PnL / Max Drawdown for this regime"
    )
    max_drawdown: float = Field(default=0.0, description="Max drawdown encountered in this regime")


class RewardDecomposition(BaseModel):
    """Breakdown of returns into gross profit and costs."""

    gross_pnl: float
    net_pnl: float
    total_commissions: float
    commission_drag: float = Field(
        ..., description="Percentage impact of commissions on gross returns"
    )
    avg_win: float = Field(default=0.0, description="Average profit of winning trades")
    avg_loss: float = Field(default=0.0, description="Average loss of losing trades")
    profit_concentration: float = Field(
        default=0.0, description="Ratio of top 10% of trades to total net profit"
    )
    risk_adjusted_pnl: float = Field(
        default=0.0, description="PnL penalized by variance of returns"
    )


class RLReport(BaseModel):
    """Final aggregate evaluation report for an RL agent."""

    agent_name: str
    total_steps: int
    initial_balance: float
    stability: StabilityMetrics
    turnover: TurnoverMetrics
    drawdown: DrawdownMetrics
    exposure: ExposureMetrics
    regime_sensitivity: list[RegimePerformance]
    reward_decomposition: RewardDecomposition
    overall_win_rate: float


class RLComparison(BaseModel):
    """Comparative report across multiple agents."""

    baseline_name: str
    agent_reports: list[RLReport]
    performance_gap_pct: float = Field(..., description="Gap between best RL agent and baseline")
    best_agent: str


class MomentumBaseline:
    """
    Rule-based momentum baseline for RL comparison.
    Uses configurable thresholds on normalized price distance from mean.
    """

    def __init__(
        self,
        threshold: float = 0.2,
        close_idx: int = 3,
        n_features: int = 5,
    ):
        self.threshold = threshold
        self.close_idx = close_idx
        self.n_features = n_features

    def predict(self, observation: np.ndarray) -> int:
        """
        Momentum logic: Buy if normalized price is significantly positive (trending up),
        Sell if significantly negative (trending down).
        """
        # Observation format from TradingEnv: [window_normalized_flattened, balance, position]
        last_close_idx = -(self.n_features + 2) + self.close_idx

        if len(observation) < abs(last_close_idx):
            return 0

        last_val = observation[last_close_idx]
        if last_val > self.threshold:
            return 1  # Buy
        if last_val < -self.threshold:
            return 2  # Sell
        return 0  # Hold


class MeanReversionBaseline:
    """
    Rule-based Mean Reversion baseline for RL comparison.
    Uses configurable overbought/oversold thresholds on normalized price.
    """

    def __init__(
        self,
        ob_threshold: float = 1.5,
        os_threshold: float = -1.5,
        close_idx: int = 3,
        n_features: int = 5,
    ):
        self.ob_threshold = ob_threshold
        self.os_threshold = os_threshold
        self.close_idx = close_idx
        self.n_features = n_features

    def predict(self, observation: np.ndarray) -> int:
        """
        Mean reversion logic: Sell if significantly above mean, Buy if significantly below.
        """
        last_close_idx = -(self.n_features + 2) + self.close_idx

        if len(observation) < abs(last_close_idx):
            return 0

        last_val = observation[last_close_idx]
        if last_val > self.ob_threshold:
            return 2  # Sell (Overbought)
        if last_val < self.os_threshold:
            return 1  # Buy (Oversold)
        return 0


class RandomBaseline:
    """Random baseline for RL comparison."""

    def predict(self, observation: np.ndarray) -> int:
        return np.random.choice([0, 1, 2])


class SupervisedBaseline:
    """
    Wrapper for supervised models (scikit-learn, etc.) to compare against RL agents.
    Handles reshaping and ensures output matches environment action space.
    """

    def __init__(self, model: Any):
        self.model = model

    def predict(self, observation: np.ndarray) -> int:
        """
        Generate prediction from supervised model.
        Args:
            observation: Environment observation.
        Returns:
            int: Action (0, 1, 2).
        """
        # Reshape for single sample inference if it's a flat array
        obs_reshaped = observation.reshape(1, -1)
        try:
            prediction = self.model.predict(obs_reshaped)

            # Extract scalar from numpy array or list
            if isinstance(prediction, (np.ndarray, list)):
                if isinstance(prediction, np.ndarray) and prediction.size == 1:
                    prediction = prediction.item()
                else:
                    prediction = prediction[0]

            return int(prediction)
        except Exception as e:
            logger.error("SupervisedBaseline prediction error: %s", e)
            return 0


class RLEvaluator:
    """
    Evaluator for RL agents with institutional metrics.
    Analyzes performance beyond simple reward, focusing on stability,
    turnover, and regime sensitivity.
    """

    def __init__(
        self,
        env: Any,
        regime_detector: RegimeDetector | None = None,
        annualization_factor: int = 252,
        close_idx: int = 3,
        n_features: int = 5,
    ):
        self.env = env
        self.regime_detector = regime_detector or RegimeDetector()
        self.annualization_factor = annualization_factor
        self.close_idx = close_idx
        self.n_features = n_features

    def evaluate(self, agent: RLModel, agent_name: str = "RL_Agent") -> RLReport:
        """
        Run a full evaluation of the agent and generate a typed report.
        Tracks mark-to-market equity for institutional-grade return analysis.
        """
        obs, _ = self.env.reset()
        done = False

        # Pre-calculate market regimes for the entire dataset for performance
        regime_labels = []
        if hasattr(self.env, "data"):
            data_df = pd.DataFrame(
                self.env.data[:, :5],
                columns=["open", "high", "low", "close", "tick_volume"],
            )
            labeled_df = self.regime_detector.label_history(data_df)
            regime_labels = labeled_df["regime"].values

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

            # Detect market regime from pre-calculated labels
            current_regime = MarketRegime.UNKNOWN
            current_price = 0.0
            if hasattr(self.env, "data") and hasattr(self.env, "current_step"):
                current_step = self.env.current_step
                current_price = self.env.data[current_step - 1, self.close_idx]

                if current_step - 1 < len(regime_labels):
                    regime_val = regime_labels[current_step - 1]
                    try:
                        current_regime = MarketRegime(regime_val)
                    except ValueError:
                        current_regime = MarketRegime.UNKNOWN

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
        self, agents: list[Any], agent_names: list[str], baseline_name: str = "Momentum"
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

        gap = (
            ((best_sharpe - baseline_sharpe) / abs(baseline_sharpe) * 100)
            if baseline_sharpe != 0
            else 0.0
        )

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
            # Recovery Factor: Net PnL / Max Drawdown (in currency)
            max_dd_currency = report.drawdown.max_drawdown * report.initial_balance
            recovery_factor = report.reward_decomposition.net_pnl / (max_dd_currency + 1e-9)

            metrics.append(
                RLMetric(
                    agent_name=report.agent_name,
                    sharpe=report.stability.sharpe_ratio,
                    sortino=report.stability.sortino_ratio,
                    profit_factor=report.stability.profit_factor,
                    max_dd=report.drawdown.max_drawdown,
                    win_rate=report.overall_win_rate,
                    calmar=report.stability.calmar_ratio,
                    stability_score=report.stability.stability_score,
                    var_95=report.stability.var_95,
                    cvar_95=report.stability.cvar_95,
                    recovery_factor=float(recovery_factor),
                    ulcer_index=report.stability.ulcer_index,
                    sqn=report.stability.sqn,
                    tail_ratio=report.stability.tail_ratio,
                    common_sense_ratio=report.stability.common_sense_ratio,
                    gain_to_pain_ratio=report.stability.gain_to_pain_ratio,
                    lake_ratio=report.stability.lake_ratio,
                    portfolio_heat=report.exposure.avg_portfolio_heat,
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
        """
        Translate agent prediction (int or Signal) into environment action.
        Robustly handles SB3 tuples, numpy scalars/arrays, and Signal objects.
        Maps SignalDirection.SELL (-1) to ModelAction.SELL (2).
        """
        try:
            prediction = agent.predict(obs)

            # Handle Signal objects FIRST (they are tuples, but we want the object)
            if hasattr(prediction, "direction"):
                direction = prediction.direction
                if direction == SignalDirection.BUY:
                    return 1
                if direction == SignalDirection.SELL:
                    return 2
                return 0

            # Handle StableBaselines3 models (returns tuple (action, states))
            if (
                isinstance(prediction, tuple)
                and len(prediction) >= 2
                and not hasattr(prediction, "_fields")
            ):
                prediction = prediction[0]

            # If prediction is a numpy array or list, get the first element
            if isinstance(prediction, (np.ndarray, list)):
                if isinstance(prediction, np.ndarray) and prediction.size == 1:
                    prediction = prediction.item()
                else:
                    prediction = prediction[0]

            # Handle Pydantic-like or Enum-like objects that might have 'value'
            if hasattr(prediction, "value") and not isinstance(prediction, (int, float)):
                prediction = prediction.value

            # Final cast to int and SignalDirection mapping
            res = int(prediction)
            if res == -1:  # Map SignalDirection.SELL to ModelAction.SELL
                return 2
            return res
        except Exception as e:
            logger.error("Error extracting prediction from agent %s: %s", type(agent), e)
            return 0  # Default to Hold on error

    def _generate_report(self, agent_name: str, df: pd.DataFrame) -> RLReport:
        """Calculate all metrics and return an RLReport."""
        trades = self._extract_trades(df)
        drawdown = self._calculate_drawdown(df)
        regime_sensitivity = self._calculate_regime_sensitivity(df)
        stability = self._calculate_stability(df, trades, drawdown.max_drawdown, regime_sensitivity)
        turnover = self._calculate_turnover(df, trades)
        exposure = self._calculate_exposure(df)
        reward_decomp = self._calculate_reward_decomposition(df, trades, stability.volatility)

        trade_pnls = [t["pnl"] for t in trades]
        win_rate = len([p for p in trade_pnls if p > 0]) / len(trade_pnls) if trade_pnls else 0.0

        initial_balance = float(df["balances"].iloc[0]) if len(df) > 0 else 0.0

        return RLReport(
            agent_name=agent_name,
            total_steps=len(df),
            initial_balance=initial_balance,
            stability=stability,
            turnover=turnover,
            drawdown=drawdown,
            exposure=exposure,
            regime_sensitivity=regime_sensitivity,
            reward_decomposition=reward_decomp,
            overall_win_rate=win_rate,
        )

    def _extract_trades(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Extract detailed trade information from history.
        Each trade contains: pnl, hold_time.
        Uses total PnL from entry to exit.
        """
        trades = []
        balances = df["balances"].values
        positions = df["positions"].values

        entry_idx = 0
        in_position = False

        # Special case: position already open at step 0
        if positions[0] != 0:
            entry_idx = 0
            in_position = True

        for i in range(1, len(df)):
            # Entry detected
            if positions[i - 1] == 0 and positions[i] != 0:
                entry_idx = i
                in_position = True
            # Exit detected
            elif positions[i - 1] != 0 and positions[i] == 0:
                # PnL is the change in MtM equity from the step BEFORE entry to the exit step
                # If entry was at 0, we use 0 as the reference point for balance change
                prev_idx = max(0, entry_idx - 1)
                pnl = balances[i] - balances[prev_idx]
                hold_time = i - entry_idx
                trades.append({"pnl": float(pnl), "hold_time": int(hold_time)})
                in_position = False

        # Handle final open position
        if in_position:
            i = len(df) - 1
            prev_idx = max(0, entry_idx - 1)
            pnl = balances[i] - balances[prev_idx]
            hold_time = i - entry_idx
            trades.append({"pnl": float(pnl), "hold_time": int(hold_time)})

        return trades

    def _calculate_stability(
        self,
        df: pd.DataFrame,
        trades: list[dict[str, Any]],
        max_dd: float,
        regime_perf: list[RegimePerformance] | None = None,
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
                lake_ratio=0.0,
            )

        mean_ret = returns.mean()
        std_ret = returns.std()

        sharpe = (mean_ret / std_ret * np.sqrt(self.annualization_factor)) if std_ret > 0 else 0.0

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
            sum(wins) / sum(losses) if sum(losses) > 0 else (float("inf") if sum(wins) > 0 else 1.0)
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

        # Ulcer Index: square root of the mean of squared drawdowns
        balances = df["balances"].values
        peak = np.maximum.accumulate(balances)
        drawdowns = (peak - balances) / (peak + 1e-9)
        ulcer_index = np.sqrt(np.mean(np.square(drawdowns)))

        # SQN: sqrt(N) * mean_pnl / std_pnl
        sqn = 0.0
        if len(trade_pnls) > 0:
            avg_pnl = np.mean(trade_pnls)
            std_pnl = np.std(trade_pnls)
            if std_pnl > 0:
                sqn = np.sqrt(len(trade_pnls)) * avg_pnl / std_pnl

        # Tail Ratio: 95th percentile / abs(5th percentile)
        p95 = np.percentile(returns, 95) if len(returns) > 20 else 0.0
        p5 = np.percentile(returns, 5) if len(returns) > 20 else 0.0
        tail_ratio = abs(p95 / p5) if abs(p5) > 1e-9 else 0.0

        # Common Sense Ratio: Tail Ratio * Profit Factor
        common_sense_ratio = tail_ratio * (profit_factor if profit_factor != float("inf") else 1.0)

        # Gain-to-Pain Ratio: Sum(Gains) / Abs(Sum(Losses))
        # Note: Often calculated on monthly basis, here we use step returns for granularity
        gains = returns[returns > 0].sum()
        pains = abs(returns[returns < 0].sum())
        gain_to_pain_ratio = gains / pains if pains > 1e-9 else 0.0

        # Lake Ratio: area of drawdown relative to duration
        lake_ratio = np.mean(drawdowns)

        # Regime stability: inverse of CoV of Sharpe across regimes
        regime_stability = 0.0
        if regime_perf:
            sharpes = [rp.sharpe_ratio for rp in regime_perf]
            if len(sharpes) > 1:
                mean_sharpe = np.mean(sharpes)
                std_sharpe = np.std(sharpes)
                if abs(mean_sharpe) > 1e-9:
                    cov = std_sharpe / abs(mean_sharpe)
                    regime_stability = 1.0 / (1.0 + cov)

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
            ulcer_index=float(ulcer_index),
            sqn=float(sqn),
            tail_ratio=float(tail_ratio),
            common_sense_ratio=float(common_sense_ratio),
            gain_to_pain_ratio=float(gain_to_pain_ratio),
            regime_stability_score=float(regime_stability),
            lake_ratio=float(lake_ratio),
        )

    def _calculate_turnover(
        self, df: pd.DataFrame, trades: list[dict[str, Any]]
    ) -> TurnoverMetrics:
        """Assess trading activity and execution costs, including policy entropy."""
        num_trades = len(trades)
        hold_times = [t["hold_time"] for t in trades]

        avg_hold_time = np.mean(hold_times) if hold_times else 0.0
        max_hold_time = np.max(hold_times) if hold_times else 0
        min_hold_time = np.min(hold_times) if hold_times else 0

        trade_freq = (num_trades / len(df)) * 1000 if len(df) > 0 else 0.0

        # Turnover ratio: rough estimate of traded volume relative to initial balance
        # In this env, each trade is 1.0 unit.
        turnover_ratio = (num_trades * 1.0) / (df["balances"].iloc[0]) if len(df) > 0 else 0.0

        # Action entropy: H(X) = -sum(p(x) * log(p(x)))
        action_entropy = 0.0
        if "actions" in df.columns and len(df) > 0:
            counts = df["actions"].value_counts(normalize=True).values
            action_entropy = -np.sum(counts * np.log(counts + 1e-9))

        initial_balance = df["balances"].iloc[0] if len(df) > 0 else 1.0
        turnover_ratio = (num_trades * 1.0) / (initial_balance)

        return TurnoverMetrics(
            trade_frequency=float(trade_freq),
            avg_hold_time=float(avg_hold_time),
            max_hold_time=int(max_hold_time),
            min_hold_time=int(min_hold_time),
            total_trades=num_trades,
            turnover_ratio=float(turnover_ratio),
            action_entropy=float(action_entropy),
        )

    def _calculate_exposure(self, df: pd.DataFrame) -> ExposureMetrics:
        """Assess portfolio exposure and time-at-risk."""
        if len(df) == 0:
            return ExposureMetrics(
                avg_portfolio_heat=0.0, max_portfolio_heat=0.0, time_at_risk_pct=0.0
            )

        positions = df["positions"].abs().values
        avg_heat = np.mean(positions)
        max_heat = np.max(positions)
        time_at_risk = np.mean(positions > 0) * 100

        return ExposureMetrics(
            avg_portfolio_heat=float(avg_heat),
            max_portfolio_heat=float(max_heat),
            time_at_risk_pct=float(time_at_risk),
        )

    def _calculate_drawdown(self, df: pd.DataFrame) -> DrawdownMetrics:
        """Assess downside risk and recovery."""
        if len(df) == 0:
            return DrawdownMetrics(max_drawdown=0.0, max_drawdown_duration=0, avg_drawdown=0.0)

        balances = df["balances"].values
        peak = np.maximum.accumulate(balances)
        drawdowns = (peak - balances) / (peak + 1e-9)

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
            avg_drawdown=float(avg_dd),
        )

    def _calculate_regime_sensitivity(self, df: pd.DataFrame) -> list[RegimePerformance]:
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
            sharpe = (
                (returns.mean() / returns.std() * np.sqrt(self.annualization_factor))
                if len(returns) > 1 and returns.std() > 0
                else 0.0
            )

            # Extract trades within this regime
            regime_pnls = []
            balances = df["balances"].values
            positions = df["positions"].values
            regimes = df["regimes"].values

            entry_idx = 0
            for i in range(1, len(df)):
                if positions[i - 1] == 0 and positions[i] != 0:
                    entry_idx = i
                elif positions[i - 1] != 0 and positions[i] == 0 and regimes[entry_idx] == regime:
                    pnl = balances[i] - balances[entry_idx - 1]
                    regime_pnls.append(pnl)

            win_rate = (
                len([p for p in regime_pnls if p > 0]) / len(regime_pnls) if regime_pnls else 0.0
            )

            # Profit factor: sum(profits) / abs(sum(losses))
            profits = sum([p for p in regime_pnls if p > 0])
            losses = abs(sum([p for p in regime_pnls if p < 0]))
            profit_factor = (
                profits / losses if losses > 0 else (float("inf") if profits > 0 else 1.0)
            )

            # Max drawdown within this regime
            regime_bals = regime_df["balances"].values
            peak = np.maximum.accumulate(regime_bals)
            drawdowns = (peak - regime_bals) / (peak + 1e-9)
            regime_max_dd = np.max(drawdowns)

            # Recovery factor
            total_regime_pnl = regime_bals[-1] - regime_bals[0]
            recovery_factor = (
                total_regime_pnl / (regime_max_dd * regime_bals[0] + 1e-9)
                if regime_max_dd > 0
                else 1.0
            )

            regime_stats.append(
                RegimePerformance(
                    regime=regime,
                    sharpe_ratio=float(sharpe),
                    win_rate=float(win_rate),
                    total_trades=len(regime_pnls),
                    profit_factor=float(profit_factor),
                    recovery_factor=float(recovery_factor),
                    max_drawdown=float(regime_max_dd),
                )
            )

        return regime_stats

    def _calculate_reward_decomposition(
        self,
        df: pd.DataFrame,
        trades: list[dict[str, Any]],
        volatility: float = 0.0,
    ) -> RewardDecomposition:
        """Breakdown of returns into gross profit and costs, with concentration analysis."""
        total_commissions = df["commissions"].iloc[-1] if len(df) > 0 else 0.0
        final_pnl = df["balances"].iloc[-1] - df["balances"].iloc[0] if len(df) > 0 else 0.0

        net_pnl = final_pnl
        gross_pnl = net_pnl + total_commissions

        comm_drag = (total_commissions / (gross_pnl + 1e-9) * 100) if gross_pnl > 0 else 0.0

        # Risk-adjusted PnL: simple version (net_pnl - penalty * volatility)
        # Using a penalty proportional to the initial balance and volatility
        initial_balance = df["balances"].iloc[0] if len(df) > 0 else 0.0
        risk_penalty = 0.1 * volatility * initial_balance
        risk_adjusted_pnl = net_pnl - risk_penalty

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
            risk_adjusted_pnl=float(risk_adjusted_pnl),
        )
