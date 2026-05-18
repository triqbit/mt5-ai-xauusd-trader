# Reinforcement Learning Evaluation Framework

The RL Evaluation Framework provides institutional-grade metrics for assessing the performance, stability, and reliability of reinforcement learning agents (such as PPO) beyond simple rewards.

## Core Components

### RLEvaluator
The `RLEvaluator` is the primary orchestration class that runs agents through a Gymnasium-compatible environment and collects high-fidelity history data.

Key capabilities:
- **Mark-to-Market Tracking**: Calculates equity curves using realized balance and unrealized PnL.
- **Comparative Analysis**: Compares multiple agents against rule-based and random baselines.
- **Reporting Integration**: Seamlessly integrates with the `ResearchReporter` to generate Terminal, Markdown, and HTML reports.

## Institutional Metrics

### Stability Analysis
- **Sharpe/Sortino/Calmar Ratios**: Standard risk-adjusted return metrics.
- **System Quality Number (SQN)**: Van Tharp's metric for system reliability.
- **Lake Ratio**: Area-based drawdown assessment.
- **Stability Score**: R-squared of the equity curve to measure consistency.

### Turnover Analysis
- **Trade Frequency**: Number of trades per 1000 steps.
- **Average Hold Time**: Duration of positions in steps.
- **Action Entropy**: Detects policy collapse or over-concentration in specific actions.

### Reward Decomposition
- **Commission Drag**: Percentage impact of transaction costs on gross returns.
- **Profit Concentration**: Ratio of the top 10% of trades to total net profit.
- **Risk-Adjusted PnL**: PnL penalized by return volatility.

### Regime Sensitivity
- **Regime-Specific Performance**: Partitioned PnL analysis across trending, ranging, and shock regimes.
- **Regime Stability Score**: Consistency of performance (inverse CoV of Sharpe) across different market environments.

## Usage Example

```python
from src.research.rl_evaluation import RLEvaluator, MomentumBaseline
from src.environment.gym_env import TradingEnv

# Initialize environment and evaluator
env = TradingEnv(data=market_data)
evaluator = RLEvaluator(env=env)

# Compare your agent against baseline
comparison = evaluator.compare(
    agents=[my_ppo_agent],
    agent_names=["PPO_V1"],
    baseline_name="Momentum"
)

# Convert to report section
rl_section = evaluator.to_report_section(comparison)
```

## Demo
Run the comprehensive demo to see the framework in action:
```bash
python3 -m src.research.rl_evaluation_demo
```
