"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/drift_analyzer.py
Statistical model drift and feature shift detection.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel


class DriftMetric(BaseModel):
    """Detection results for a single feature or metric."""

    name: str
    baseline_value: float
    current_value: float
    drift_score: float  # 0.0 to 1.0
    is_significant: bool


class DriftAnalysisReport(BaseModel):
    """Aggregate model drift report."""

    metrics: list[DriftMetric]
    feature_importance_shifts: dict[str, float]
    overall_drift_status: str

    def to_report_section(self) -> Any:
        """Convert results to ModelDriftSection for ResearchReporter."""
        from src.research.reporting import DriftMetric as ReportingDriftMetric, ModelDriftSection

        reporting_metrics = []
        for m in self.metrics:
            status = "STABLE"
            if m.drift_score > 0.5:
                status = "CRITICAL"
            elif m.drift_score > 0.2:
                status = "WARNING"

            reporting_metrics.append(
                ReportingDriftMetric(
                    name=m.name,
                    baseline=f"{m.baseline_value:.4f}",
                    current=f"{m.current_value:.4f}",
                    drift_pct=float(m.drift_score * 100),
                    status=status,
                )
            )

        # Summarize feature shifts
        sorted_shifts = sorted(
            self.feature_importance_shifts.items(), key=lambda x: abs(x[1]), reverse=True
        )
        shift_desc = "Significant shifts in: " + ", ".join(
            [f"{k} ({v:+.2f})" for k, v in sorted_shifts[:3]]
        )

        return ModelDriftSection(
            metrics=reporting_metrics,
            feature_shifts=shift_desc
            if sorted_shifts
            else "No significant feature shifts detected.",
        )


class DriftAnalyzer:
    """
    Analyzes model performance and feature distributions for drift.
    """

    def calculate_drift(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        target_col: str = "close",
    ) -> DriftAnalysisReport:
        """
        Compare current data distribution against baseline using KS test or similar.
        """
        from scipy import stats

        metrics = []

        # 1. Target distribution drift
        ks_stat, p_val = stats.ks_2samp(baseline_df[target_col], current_df[target_col])
        metrics.append(
            DriftMetric(
                name=f"Distribution: {target_col}",
                baseline_value=float(baseline_df[target_col].mean()),
                current_value=float(current_df[target_col].mean()),
                drift_score=float(ks_stat),
                is_significant=p_val < 0.05,
            )
        )

        # 2. Return volatility drift
        if "returns" in baseline_df.columns and "returns" in current_df.columns:
            b_vol = baseline_df["returns"].std()
            c_vol = current_df["returns"].std()
            drift = abs(c_vol - b_vol) / (b_vol + 1e-9)
            metrics.append(
                DriftMetric(
                    name="Return Volatility",
                    baseline_value=float(b_vol),
                    current_value=float(c_vol),
                    drift_score=float(min(drift, 1.0)),
                    is_significant=drift > 0.2,
                )
            )

        return DriftAnalysisReport(
            metrics=metrics,
            feature_importance_shifts={},  # Placeholder
            overall_drift_status="WARNING" if any(m.is_significant for m in metrics) else "STABLE",
        )
