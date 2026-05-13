"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/calibration.py
Confidence calibration and reliability analysis engine.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)

__all__ = ["CalibrationEngine", "CalibrationResult", "ConfidenceBucket"]


class ConfidenceBucket(BaseModel):
    """Statistically significant grouping of model predictions by confidence."""

    range_start: float
    range_end: float
    avg_confidence: float
    accuracy: float
    sample_count: int
    deviation: float  # |avg_confidence - accuracy|


class CalibrationResult(BaseModel):
    """Enterprise-grade calibration audit result."""

    brier_score: float
    reliability: float  # Brier decomposition: Reliability (lower is better)
    resolution: float  # Brier decomposition: Resolution (higher is better)
    uncertainty: float  # Brier decomposition: Uncertainty
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    buckets: list[ConfidenceBucket]
    optimal_threshold: float = 0.5
    status: str = "PROVISIONAL"

    def to_report_section(self) -> Any:
        """Convert result to CalibrationSection for ResearchReporter."""
        from src.research.reporting import CalibrationBucket as ReportingBucket, CalibrationSection

        reporting_buckets = []
        for b in self.buckets:
            reporting_buckets.append(
                ReportingBucket(
                    range=f"{b.range_start:.1f}-{b.range_end:.1f}",
                    accuracy=b.accuracy,
                    confidence=b.avg_confidence,
                    samples=b.sample_count,
                )
            )

        reliability_msg = "Model shows good alignment between confidence and accuracy."
        if self.ece > 0.25:
            reliability_msg = "Critical calibration error; confidence scores unreliable."
        elif self.ece > 0.15:
            reliability_msg = "Model is overconfident; calibration suggested."

        return CalibrationSection(
            brier_score=self.brier_score,
            ece=self.ece,
            mce=self.mce,
            status=self.status,
            optimal_threshold=self.optimal_threshold,
            buckets=reporting_buckets,
            reliability_insight=reliability_msg,
        )


class CalibrationEngine:
    """
    Measures and improves the reliability of model confidence scores.

    A well-calibrated model has confidence scores that reflect its actual
    probability of being correct. This engine provides tools to audit
    calibration and tune thresholds for operational use.
    """

    def __init__(self, n_bins: int = 10) -> None:
        """
        Initialize the calibration engine.

        Args:
            n_bins: Number of buckets for reliability analysis.
        """
        self.n_bins = n_bins

    def analyze(
        self,
        confidences: np.ndarray | list[float],
        outcomes: np.ndarray | list[int],
    ) -> CalibrationResult:
        """
        Perform a full calibration audit.

        Args:
            confidences: Array of confidence scores (0.0 to 1.0).
            outcomes: Binary outcomes (1 for correct, 0 for incorrect).

        Returns:
            CalibrationResult: Comprehensive audit metrics.
        """
        conf = np.array(confidences)
        y = np.array(outcomes)

        if len(conf) == 0:
            return CalibrationResult(
                brier_score=0.0,
                reliability=0.0,
                resolution=0.0,
                uncertainty=0.0,
                ece=0.0,
                mce=0.0,
                buckets=[],
                status="NO_DATA",
            )

        # 1. Brier Score & Decomposition
        brier, rel, res, unc = self.calculate_brier_score(conf, y)

        # 2. Buckets & ECE/MCE
        buckets, ece, mce = self.analyze_buckets(conf, y)

        # 3. Optimal Threshold
        opt_threshold = self.tune_thresholds(conf, y)

        status = "VERIFIED" if ece < 0.15 else "WARNING"
        if ece > 0.25:
            status = "CRITICAL"

        return CalibrationResult(
            brier_score=float(brier),
            reliability=float(rel),
            resolution=float(res),
            uncertainty=float(unc),
            ece=float(ece),
            mce=float(mce),
            buckets=buckets,
            optimal_threshold=float(opt_threshold),
            status=status,
        )

    def calculate_brier_score(
        self, confidences: np.ndarray, outcomes: np.ndarray
    ) -> tuple[float, float, float, float]:
        """
        Calculate Brier score and its 3-component decomposition.
        BS = Reliability - Resolution + Uncertainty
        """
        bs = np.mean((confidences - outcomes) ** 2)

        # Base rate (uncertainty)
        p_bar = np.mean(outcomes)
        uncertainty = p_bar * (1 - p_bar)

        # Grouping for decomposition
        bins = np.linspace(0, 1, self.n_bins + 1)
        indices = np.digitize(confidences, bins) - 1
        indices = np.clip(indices, 0, self.n_bins - 1)

        reliability = 0.0
        resolution = 0.0

        for i in range(self.n_bins):
            mask = indices == i
            if not np.any(mask):
                continue

            n_k = np.sum(mask)
            f_k = np.mean(confidences[mask])
            o_k = np.mean(outcomes[mask])

            reliability += n_k * (f_k - o_k) ** 2
            resolution += n_k * (o_k - p_bar) ** 2

        reliability /= len(confidences)
        resolution /= len(confidences)

        return float(bs), float(reliability), float(resolution), float(uncertainty)

    def analyze_buckets(
        self, confidences: np.ndarray, outcomes: np.ndarray
    ) -> tuple[list[ConfidenceBucket], float, float]:
        """
        Group predictions into bins to calculate ECE and MCE.
        """
        bins = np.linspace(0, 1, self.n_bins + 1)
        indices = np.digitize(confidences, bins) - 1
        indices = np.clip(indices, 0, self.n_bins - 1)

        buckets = []
        ece = 0.0
        mce = 0.0

        for i in range(self.n_bins):
            mask = indices == i
            n_k = np.sum(mask)
            if n_k == 0:
                continue

            avg_conf = np.mean(confidences[mask])
            accuracy = np.mean(outcomes[mask])
            deviation = abs(avg_conf - accuracy)

            buckets.append(
                ConfidenceBucket(
                    range_start=float(bins[i]),
                    range_end=float(bins[i + 1]),
                    avg_confidence=float(avg_conf),
                    accuracy=float(accuracy),
                    sample_count=int(n_k),
                    deviation=float(deviation),
                )
            )

            ece += n_k * deviation
            mce = max(mce, deviation)

        ece /= len(confidences)

        return buckets, float(ece), float(mce)

    def tune_thresholds(
        self, confidences: np.ndarray, outcomes: np.ndarray, metric: str = "f1"
    ) -> float:
        """
        Find the confidence threshold that optimizes for a specific metric.
        Default is F1-score to balance precision and recall.
        """
        thresholds = np.linspace(0.5, 0.95, 46)
        best_score = -1.0
        best_threshold = 0.5

        for t in thresholds:
            preds = (confidences >= t).astype(int)
            tp = np.sum((preds == 1) & (outcomes == 1))
            fp = np.sum((preds == 1) & (outcomes == 0))
            fn = np.sum((preds == 0) & (outcomes == 1))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0

            if metric == "f1":
                score = (
                    2 * (precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0
                )
            elif metric == "precision":
                score = precision
            else:
                score = (tp + np.sum((preds == 0) & (outcomes == 0))) / len(outcomes)

            if score >= best_score:
                best_score = score
                best_threshold = t

        return float(best_threshold)

    def apply_temperature_scaling(self, confidences: np.ndarray, temperature: float) -> np.ndarray:
        """
        Adjust confidence scores using temperature scaling.
        Confidence = sigmoid(logit / T)
        Note: This is a simplified version assuming confidences were derived via sigmoid.
        """
        if temperature <= 0:
            return confidences

        # Inverse sigmoid to get logits (clamped to avoid infinity)
        eps = 1e-7
        clamped_conf = np.clip(confidences, eps, 1.0 - eps)
        logits = np.log(clamped_conf / (1.0 - clamped_conf))

        # Scale and re-sigmoid
        scaled_logits = logits / temperature
        return 1.0 / (1.0 + np.exp(-scaled_logits))

    def mitigate_overconfidence(self, confidences: np.ndarray, ece: float) -> np.ndarray:
        """
        Heuristic-based reduction of overconfident signals based on ECE.
        If ECE is high, it pushes scores slightly towards 0.5.
        """
        if ece < 0.05:
            return confidences

        # Adjustment factor based on ECE magnitude
        adjustment = np.clip(ece, 0.0, 0.2)
        # Push towards 0.5 (uncertainty)
        return confidences * (1.0 - adjustment) + (0.5 * adjustment)
