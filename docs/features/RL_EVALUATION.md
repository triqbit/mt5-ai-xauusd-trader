# Reinforcement Learning Evaluation Framework

The RL Evaluation Framework provides institutional-grade metrics to assess reinforcement learning agents beyond simple reward accumulation. It is designed to separate apparent profitability from reliable, stable, and regime-aware performance.

## Key Metrics

### 1. Stability Analysis
- **Annualized Sharpe Ratio**: Risk-adjusted return consistency.
- **Annualized Sortino Ratio**: Focuses on downside risk.
- **Calmar Ratio**: Total return relative to maximum drawdown.
- **Expectancy**: Expected profit per trade based on historical performance.
- **Profit Factor**: Ratio of gross profit to gross loss.
- **Recovery Factor**: Total PnL relative to dollar drawdown.
- **Ulcer Index**: Measures the depth and duration of drawdowns (stress metric).
- **System Quality Number (SQN)**: Van Tharp's metric for strategy reliability.
- **Stability Score (R-squared)**: Measures the linearity of the equity curve, indicating consistency of returns.
- **Value at Risk (VaR 95%)**: Estimate of the maximum potential loss at a 95% confidence level.
- **Conditional VaR (CVaR 95%)**: Average loss beyond the VaR threshold.
- **Skewness & Kurtosis**: Higher-order moments of the return distribution to detect tail risk and asymmetry.

### 2. Turnover Analysis
- **Trade Frequency**: Number of trades per 1000 steps.
- **Average Hold Time**: Duration of positions in steps.
- **Max/Min Hold Time**: Extreme durations of held positions.
- **Turnover Ratio**: Total traded volume relative to initial balance.

### 3. Drawdown Behavior
- **Max Drawdown**: Maximum peak-to-trough decline.
- **Max Drawdown Duration**: Longest period spent in a drawdown state.
- **Average Drawdown**: Mean depth of all drawdowns.

### 4. Regime Sensitivity
- SEGMENTS performance metrics (Win Rate, Profit Factor, Sharpe) by detected market regime (Trending, Ranging, News Shock, etc.).
- Helps identify if an agent is only profitable in specific market conditions.

### 5. Reward Decomposition
- **Gross PnL**: Total profit before costs.
- **Net PnL**: Profit after commissions.
- **Commission Drag**: Percentage impact of execution costs on gross returns.
- **Profit Concentration**: Ratio of the top 10% of trades to total net profit, identifying over-reliance on outlier trades.

## Usage

### Basic Evaluation
```python
from src.research.rl_evaluation import RLEvaluator
from src.models.ppo_agent import PPOAgent

evaluator = RLEvaluator(env=trading_env)
report = evaluator.evaluate(ppo_agent, agent_name="PPO_Institutional")

print(report.model_dump_json(indent=2))
```

### Benchmarking
The framework includes wrappers to compare RL agents against institutional baselines:
- **MomentumBaseline**: A rule-based strategy following recent price trends.
- **SupervisedBaseline**: Wraps standard supervised learning models.

## Integration
The evaluator uses the `RLModel` protocol, ensuring compatibility with any agent that implements a `predict(observation: np.ndarray) -> Any` method. It natively supports both raw integer actions (0=Hold, 1=Buy, 2=Sell) and the bot's standardized `Signal` objects.
