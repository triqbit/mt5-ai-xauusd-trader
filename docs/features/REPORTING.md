# Institutional Research Reporting System

## Overview
The institutional research reporting system provides automated, high-fidelity strategy audits and alpha research summaries. It aggregates data from diverse modules (Regime Detection, Stress Testing, RL Evaluation, Trade Logging) into unified, stakeholder-ready reports.

## Features
- **Regime Analysis**: Detailed breakdown of strategy performance across different market environments.
- **Stress Testing**: Resilience scores and fragility indicators derived from adversarial simulations.
- **Hyperparameter Robustness**: Walk-forward optimization results and stability metrics.
- **Trade Pattern Findings**: Behavioral risk identification and signal motif (losing combination) analysis.
- **Model Drift**: Tracking of feature importance shifts and data distribution changes.
- **Capital Allocation**: Multi-strategy portfolio heat tracking and diversification scores.
- **Rare Event Simulations**: Performance analysis during black-swan events (flash crashes, liquidity vacuums).
- **RL Agent Evaluation**: Specialized metrics for reinforcement learning agents including Sortino, CVaR, and Recovery Factor.

## Report Formats
- **HTML**: Interactive, styled dashboard for browser viewing with sticky navigation and status badges.
- **Markdown**: Audit-friendly, version-controllable text format.
- **Terminal**: Scannable, color-coded summaries for quick operator review using `rich`.

## Usage
Reports are generated via the `ResearchReporter` and `ResearchOrchestrator` classes.

```python
from src.research.reporting import ResearchOrchestrator, ResearchReporter

# Create orchestrator
orchestrator = ResearchOrchestrator(title="Strategy Audit", executive_summary="...", conclusion="...")

# Add sections from various modules
orchestrator.add_section(regime_result.to_report_section())
orchestrator.add_section(stress_result.to_report_section())

# Build and save
report = orchestrator.build()
reporter = ResearchReporter()
reporter.save_html(report, "audit_report.html")
```

## Integration
The system integrates with:
- `src/research/rl_evaluation.py` via `RLSection`
- `src/trading/capital_allocator.py` via `AllocationSection`
- `src/research/stress_lab.py` via `StressTestSection`
- `src/models/regime_detector.py` via `RegimeSection`
- `src/analytics/journal_mining.py` via `TradePatternSection`
- `src/analytics/drift_analyzer.py` via `ModelDriftSection`
