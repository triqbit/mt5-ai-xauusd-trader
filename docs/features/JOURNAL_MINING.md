# Trade Journal Mining

The Trade Journal Mining system provides automated behavioral and pattern analysis for XAUUSD trading operations. It transforms raw database records (executed trades, AI signals, and risk events) into actionable strategic insights.

## Core Analytical Motifs

### 1. Session-Based Performance
Detects overtrading and profitability decay across major global sessions:
- **Sydney**: 22:00 - 07:00 UTC
- **Tokyo**: 00:00 - 09:00 UTC
- **London**: 08:00 - 17:00 UTC
- **New York**: 13:00 - 22:00 UTC

Flags a session as "overtrading" if trade frequency exceeds 150% of the session average.

### 2. Volatility-Aware False Positives
Analyzes AI signal reliability under different market conditions by binning historical volatility into four regimes:
- **Low**
- **Normal**
- **High**
- **Extreme**

This helps identify if specific algorithms become prone to false breakouts during high-volatility spikes or news shocks.

### 3. Drawdown Cluster Detection
Automatically identifies sequences of 3 or more consecutive losing trades. This is used to diagnose "streakiness" and identify if the system is failing to adapt to rapid regime transitions.

### 4. Profitable Pattern Concentrations
Aggregates performance by:
- **Algorithm**: Which AI model family is currently dominant.
- **Hour of Day**: Identifying specific intraday windows of high edge.

### 5. Risk Block Analysis
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
