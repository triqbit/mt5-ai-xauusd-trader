# Execution Quality Analytics

The Execution Quality Analytics module provides institutional-grade metrics to evaluate the efficiency of trade execution and distinguish alpha quality from execution drag.

## Overview

High-quality signals (alpha) can be eroded by poor execution mechanics. This module isolates broker-induced slippage from market-driven alpha decay, providing a clear picture of whether performance issues stem from the strategy or the execution environment.

## Key Metrics

### 1. Alpha Decay
Measures the price movement between the time a signal is generated and the time the trade is actually executed. This represents the portion of slippage caused by the market moving against the position before the broker could fill it.

### 2. Broker Slippage
Calculated as `Total Slippage - Alpha Decay`. This isolates the execution drag attributable to the broker's liquidity and mechanics, such as wide spreads or slow fills.

### 3. Fill Quality Score
A sigmoid-based score (0.0 to 1.0) that penalizes large slippage relative to the prevailing spread. It also factors in execution latency.

### 4. Edge Capture
Measures the percentage of the theoretical signal edge (distance from entry to take-profit) that was actually captured, adjusted for the cost of the half-spread.

### 5. Markouts (Post-Entry Drift)
Tracks price movement at fixed horizons (1m, 5m, 15m, 30m, 60m) after trade entry. This helps identify if entries are being "picked off" (negative drift) or if they are timed well.

### 6. Blocked Signal Quality (Opportunity Cost)
Analyzes signals rejected by risk management to determine if they would have hit their Take-Profit or Stop-Loss first. This measures the opportunity cost of being too risk-averse. It also tracks **Max Adverse Excursion (MAE)** and **Max Favorable Excursion (MFE)** for these signals to quantify the price movement they experienced.

### 7. Institutional Symbol Robustness
The system features a centralized property detection engine for institutional assets:
- **XAUUSD/Gold:** Standardized to 0.1 pip size and 100 contract size.
- **JPY Pairs:** Standardized to 0.01 pip size.
- **Crypto (BTC/ETH):** Standardized to 1.0 pip size.
- **Dynamic Detection:** Automatically pulls digits and contract specifications from MT5/MetaAPI properties when available.

## Usage

Metrics are automatically calculated and persisted to the `execution_qualities` database table. Aggregate summaries can be generated via the `ExecutionAnalyzer.generate_summary_report()` method, which integrates with the research reporting system.

```python
from src.analytics.execution_quality import ExecutionAnalyzer

analyzer = ExecutionAnalyzer()
summary = analyzer.generate_summary_report(days=7)
print(f"Execution Efficiency: {summary.execution_efficiency_score:.2%}")
```
