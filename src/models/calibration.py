"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/calibration.py
Measuring and improving confidence reliability across model outputs.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from typing import List

import numpy as np
from pydantic import BaseModel, Field


class ConfidenceBucket(BaseModel):
    """Statistically representative bin for confidence analysis."""

    bin_min: float
    bin_max: float
    avg_confidence: float
    accuracy: float
    sample_count: int


class CalibrationMetrics(BaseModel):
    """Standardised metrics for model reliability."""

    brier_score: float = Field(..., description="Mean squared error of probabilistic forecasts")
    ece: float = Field(..., description="Expected Calibration Error (weighted avg diff)")
    mce: float = Field(..., description="Max Calibration Error (worst bin diff)")
    reliability_curve: List[ConfidenceBucket]


class CalibrationReport(BaseModel):
    """Institutional-grade calibration summary."""

    algorithm: str
    metrics: CalibrationMetrics
    optimal_threshold: float
    status: str  # e.g., "Well Calibrated", "Overconfident", "Underconfident"


class ModelCalibrator:
    """
    Measures and analyses model confidence reliability.
    Supports Brier scoring, ECE, MCE, and threshold optimization.
    """

    def __init__(self, n_bins: int = 10) -> None:
        self.n_bins = n_bins

    def calculate_metrics(
        self,
        confidences: np.ndarray,
        outcomes: np.ndarray,
    ) -> CalibrationMetrics:
        """
        Calculate calibration metrics and reliability curve.

        Args:
            confidences: Array of model confidence scores [0, 1]
            outcomes: Array of binary outcomes (1 for correct/profitable, 0 otherwise)

        Returns:
            CalibrationMetrics object
        """
        if len(confidences) == 0:
            return CalibrationMetrics(
                brier_score=0.0,
                ece=0.0,
                mce=0.0,
                reliability_curve=[],
            )

        # Brier Score: Mean Squared Error
        brier_score = float(np.mean((confidences - outcomes) ** 2))

        # Reliability Curve / ECE / MCE
        bins = np.linspace(0.0, 1.0, self.n_bins + 1)
        reliability_curve: List[ConfidenceBucket] = []

        ece = 0.0
        mce = 0.0
        total_samples = len(confidences)

        for i in range(self.n_bins):
            bin_min, bin_max = bins[i], bins[i+1]
            indices = np.where((confidences >= bin_min) & (confidences < bin_max))[0]

            # Handle the last bin edge case
            if i == self.n_bins - 1:
                indices = np.where((confidences >= bin_min) & (confidences <= bin_max))[0]

            if len(indices) > 0:
                bin_conf = confidences[indices]
                bin_out = outcomes[indices]

                avg_conf = float(np.mean(bin_conf))
                accuracy = float(np.mean(bin_out))
                count = len(indices)

                bucket = ConfidenceBucket(
                    bin_min=float(bin_min),
                    bin_max=float(bin_max),
                    avg_confidence=avg_conf,
                    accuracy=accuracy,
                    sample_count=count
                )
                reliability_curve.append(bucket)

                diff = abs(avg_conf - accuracy)
                ece += (count / total_samples) * diff
                mce = max(mce, diff)

        return CalibrationMetrics(
            brier_score=brier_score,
            ece=ece,
            mce=mce,
            reliability_curve=reliability_curve
        )

    def find_optimal_threshold(
        self,
        confidences: np.ndarray,
        outcomes: np.ndarray,
        min_accuracy: float = 0.6
    ) -> float:
        """
        Find the minimum confidence threshold that meets an accuracy target.
        """
        thresholds = np.linspace(0.0, 0.95, 20)

        for t in thresholds:
            mask = confidences >= t
            if np.any(mask):
                acc = np.mean(outcomes[mask])
                if acc >= min_accuracy:
                    return float(t)

        return 0.0

    def generate_report(
        self,
        algorithm: str,
        confidences: np.ndarray,
        outcomes: np.ndarray
    ) -> CalibrationReport:
        """Generate a full calibration report with automated status detection."""
        metrics = self.calculate_metrics(confidences, outcomes)
        optimal_threshold = self.find_optimal_threshold(confidences, outcomes)

        # Simple status logic
        if metrics.ece < 0.05:
            status = "Well Calibrated"
        elif metrics.ece < 0.15:
            status = "Adequate"
        else:
            # Check if overconfident or underconfident
            avg_conf = np.mean(confidences) if len(confidences) > 0 else 0
            avg_acc = np.mean(outcomes) if len(outcomes) > 0 else 0
            if avg_conf > avg_acc + 0.05:
                status = "Overconfident"
            elif avg_conf < avg_acc - 0.05:
                status = "Underconfident"
            else:
                status = "Unreliable"

        return CalibrationReport(
            algorithm=algorithm,
            metrics=metrics,
            optimal_threshold=optimal_threshold,
            status=status
        )

    def apply_temperature_scaling(
        self,
        logits: np.ndarray,
        temperature: float
    ) -> np.ndarray:
        """
        Simple temperature scaling to soften/harden probabilities.
        p_i = exp(z_i / T) / sum(exp(z_j / T))
        """
        if temperature <= 0:
            temperature = 1.0

        scaled_logits = logits / temperature
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits, axis=-1, keepdims=True))
        return exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
