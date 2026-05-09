# Trade Journal Mining

The Trade Journal Mining system provides automated behavioral and pattern analysis for XAUUSD trading operations. It transforms raw database records (executed trades, AI signals, and risk events) into actionable strategic insights.

## Core Analytical Motifs

### 1. Session-Based Performance
Detects overtrading and profitability decay across major global sessions:
- **Sydney**: 22:00 - 07:00 UTC
- **Tokyo**: 00:00 - 09:00 UTC
- **London**: 08:00 - 17:00 UTC
- **New York**: 13:00 - 22:00 UTC

Flags a session as "overtrading" if trade frequency exceeds 150% of the session average. Performance metrics and motifs are now session-aware, allowing the identification of regime-specific algorithm failures.

### 2. Multi-Dimensional Signal Motifs
Analyzes AI signal reliability under different market conditions by binning historical volatility, confidence, and **trading session** into regimes:
- **Volatility Buckets**: Low, Normal, High, Extreme.
- **Confidence Buckets**: Low (<0.4), Medium (<0.7), High (<0.9), Extreme.

This helps identify "Toxic Motifs"—recurring attribute combinations (e.g., "PPO + Long + High Volatility + Low Confidence") that show significantly lower win rates.

### 3. Drawdown Cluster Detection
Automatically identifies sequences of 3 or more consecutive losing trades. This is used to diagnose "streakiness" and identify if the system is failing to adapt to rapid regime transitions.

### 4. Profitable Pattern Concentrations
Aggregates performance by:
- **Symbol**: Asset-level performance (e.g., XAUUSD vs others).
- **Algorithm**: Which AI model family is currently dominant.
- **Hour of Day**: Identifying specific intraday windows of high edge.
- **Day of Week**: Detecting cyclical edges or "Friday volatility" effects.

### 5. Trade Duration Analysis
Calculates average win vs loss holding times in minutes. This reveals behavioral biases such as "cutting winners short and letting losers run," which is critical for XAUUSD risk management where volatility can quickly turn a small loss into a major drawdown.

### 6. Early Warning & Toxic Motif Tracking
Detects advanced behavioral risks:
- **Toxic Motifs**: Recurring attribute combinations that show significantly lower win rates or high frequency within drawdown clusters. Motifs are ranked using a toxic score: `(1.0 - win_rate) * log1p(frequency)`, prioritizing high-confidence failures.
- **Pre-Drawdown Motifs**: Identification of signal combinations that frequently occur shortly before (default 6 hours) a drawdown cluster begins.
- **Combination Motifs**: Recurring sets of multiple signals (e.g., Ensemble BUY + PPO SELL) within a short window (60m) that frequently precede drawdown clusters.
- **Strategy Fragility**: High correlation between risk blocks and "weak states" (defined as the 24-hour window *preceding* a drawdown cluster).

### 7. Risk Block Analysis
Summarizes recurring reasons why the `RiskManager` rejected AI signals (e.g., `MAX_DRAWDOWN`, `SPREAD_TOO_WIDE`). This reveals the "opportunity cost" of the current risk parameters.


## Technical Implementation

- **Location**: `src/analytics/journal_mining.py`
- **Output**: Typed `JournalReport` (Pydantic model)
- **Engine**: SQLAlchemy for data retrieval and Pandas for statistical analysis.

## Usage

```python
from src.analytics.journal_mining import JournalMiner

miner = JournalMiner("sqlite:///trades.db")
report = miner.run_mining()

print(f"Total drawdown clusters: {len(report.drawdown_clusters)}")
for session in report.session_analysis:
    if session.is_overtrading:
        print(f"Overtrading detected in {session.session_name}")
```

## Analytical Motifs
The JournalMiner detects early-warning motifs that frequently precede drawdowns, allowing for proactive strategy damping.
