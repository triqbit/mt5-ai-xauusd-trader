# Trade Journal Pattern Mining

The Trade Journal Pattern Mining system (`src/analytics/journal_mining.py`) provides institutional-grade analytical capabilities to detect hidden behavioral and strategic patterns in executed and rejected trades.

## Key Features

### 1. Statistical Overtrading Detection
Replaces simple frequency heuristics with Z-score statistics to identify sessions where trade volume significantly deviates from the mean.
- **Metric**: `z_score` in `SessionAnalysis`.
- **Threshold**: Z-score > 1.5 indicates significant overtrading.

### 2. Equity-Aware Drawdown Clusters
Analyzes clusters of consecutive losing trades (3+) with a focus on their actual equity impact.
- **Metric**: `max_equity_drop` in `DrawdownCluster`.
- **Value**: Captures the maximum realized drawdown within a specific loss cluster.

### 3. Rolling Alpha Decay Detection
Monitors strategy degradation by comparing recent performance against a historical baseline.
- **Method**: Calculates the trend in Profit Factor over a rolling window.
- **Indicator**: `is_decaying` flag triggered when the Profit Factor trend drops significantly (e.g., >30% decline).

### 4. Behavioral Motif Recognition
Identifies recurring signal attributes (algorithm, volatility, confidence, session) that correlate with either exceptional profit (Golden Motifs) or consistent failure (Toxic Motifs).

### 5. Rejection Quality Analysis
Evaluates the efficiency of risk management by analyzing the opportunity cost of blocked signals.
- **Metric**: `accuracy` (avoided losses) and `profit_opportunity_cost` (missed winners).

## Integration with Institutional Reporting

All analytical findings are automatically mapped to the `TradePatternSection` of the institutional research reports. This ensures that strategy developers and risk managers have immediate visibility into behavioral risks and alpha degradation.

## Technical Implementation

- **Database**: Integrated with the centralized SQLAlchemy engine and session factory.
- **Observability**: Utilizes `structlog` for high-fidelity analytical logging.
- **Validation**: Typed outputs ensured via Pydantic models.
