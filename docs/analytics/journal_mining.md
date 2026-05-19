# Trade Journal Mining & Pattern Recognition

## Overview
The Journal Mining module (`src/analytics/journal_mining.py`) is an institutional-grade analytical tool designed to extract strategic insights from execution logs and rejection events. It identifies recurring motifs, performance clusters, and behavioral risks to improve strategy robustness.

## Key Features

### 1. Motif Analysis
Identifies recurring signal attributes (Algorithm, Volatility, Confidence, Session) and calculates:
- **Expectancy:** The expected profit/loss per trade for a specific motif.
- **Efficiency Ratio:** The ratio of average PnL to average absolute PnL, indicating the cleanliness of the edge.

### 2. Combination Discovery
Detects clusters of multiple signals occurring within short time windows:
- **Toxic Combinations:** Signal patterns that frequently precede drawdown clusters.
- **Golden Combinations:** Signal patterns that frequently precede profit clusters.

### 3. Missed Opportunity Analysis
Detects patterns in signals rejected by risk management:
- **Blocked Golden Motifs:** Highly profitable patterns that are currently being filtered out, suggesting a need for risk limit calibration.
- **Correct Rejections:** Patterns effectively neutralized by risk filters, validating the defensive logic.

### 4. Behavioral Risk Profiling
Detects patterns indicative of psychological or systemic fragility:
- **Overtrading:** Excessive frequency in specific market sessions.
- **Overconfidence (Greed):** Aggressive lot sizing following winning streaks.
- **Revenge Trading (Tilt):** Rapid re-entry following a loss, often with increased risk.
- **Cluster Warnings:** Risk block reasons (e.g., Spread, Drawdown limits) that are highly correlated with "weak strategy states."

### 4. Session & Volatility Analysis
Breaks down performance by Sydney, Tokyo, London, and New York sessions, and segments outcomes by volatility buckets to identify regime-specific weaknesses.

### 5. Session Overlap Analysis
Extracts performance metrics for periods where two major sessions are active simultaneously (e.g., London/New York overlap), which often represent periods of peak liquidity and volatility.

## Institutional Standards
The engine utilizes industry-standard thresholds for anomaly detection:
- **Z-Score Threshold (1.5):** Statistical significance for identifying session-based overtrading.
- **Alpha Decay (30%):** A drop of 30% or more in the rolling Profit Factor triggers a strategy decay alert.
- **Weak State Correlation (70%):** High correlation between risk blocks and drawdown clusters indicates systemic fragility.

## Usage
The analytics are automatically integrated into the institutional research reporting pipeline.

```python
from src.analytics.journal_mining import JournalMiner
miner = JournalMiner(db_url="sqlite:///trades.db")
report = miner.run_mining()
```

## Reporting
Metrics are surfaced in the "Trade Pattern Findings" section of both Terminal and HTML reports, highlighting behavioral risks and profitable concentrations.
