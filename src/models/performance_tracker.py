"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/performance_tracker.py
Performance tracking and drift detection system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any, Dict, Optional

import numpy as np

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Monitors model performance and detects concept drift using rolling windows.
    """

    def __init__(
        self,
        config: TradingConfig,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        self.cfg = config
        self.db = logger_db
        self.monitor = monitor

        # Rolling windows for metrics
        self.window_short = config.drift_window_short
        self.window_long = config.drift_window_long

        # history: List of (prediction_probs, outcome_binary, confidence, algorithm_weights)
        # outcome_binary: 1 for win, 0 for loss
        self.history: deque = deque(maxlen=self.window_long)

        # Track per-algorithm win rates
        self.algo_history: Dict[str, deque] = {}

        # Map signal_id or ticket to pending predictions
        self.pending_predictions: Dict[Any, Dict[str, Any]] = {}

    def record_prediction(
        self,
        prediction_id: Any,
        prediction_probs: np.ndarray,
        confidence: float,
        direction: int,
        algorithm_weights: Dict[str, float],
        algo_decisions: Dict[str, int],
    ) -> None:
        """
        Record a prediction before the outcome is known.
        Outcome will be updated later via record_outcome.
        """
        self.pending_predictions[prediction_id] = {
            "probs": prediction_probs,
            "confidence": confidence,
            "direction": direction,
            "weights": algorithm_weights,
            "algo_decisions": algo_decisions,
        }

    def record_outcome(self, prediction_id: Any, win: bool) -> None:
        """Record the outcome of a prediction."""
        if prediction_id not in self.pending_predictions:
            logger.debug(
                "record_outcome called for unknown prediction_id: %s", prediction_id
            )
            return

        prediction = self.pending_predictions.pop(prediction_id)
        outcome = 1.0 if win else 0.0

        entry = {
            "probs": prediction["probs"],
            "confidence": prediction["confidence"],
            "weights": prediction["weights"],
            "algo_decisions": prediction["algo_decisions"],
            "win": outcome,
        }
        self.history.append(entry)

        # Per-algorithm history
        # If the overall trade won, algorithms that voted in the same direction also won
        for algo, algo_dir_idx in prediction["algo_decisions"].items():
            if algo not in self.algo_history:
                self.algo_history[algo] = deque(maxlen=self.window_long)

            # direction_map = {0: 1, 1: -1, 2: 0} from EnsembleModel
            # But wait, EnsembleModel says: action_idx = int(np.argmax(blended)) # 0=buy,1=sell,2=hold
            # per_algo = {k: float(np.argmax(votes[k])) for k in votes}
            # So 0=buy(+1), 1=sell(-1), 2=hold(0)
            algo_dir = 1 if algo_dir_idx == 0 else (-1 if algo_dir_idx == 1 else 0)

            if algo_dir == 0:
                continue  # Hold doesn't count towards win rate degradation in this context

            # If ensemble direction matches algo direction, then algo win = ensemble win
            if algo_dir == prediction["direction"]:
                self.algo_history[algo].append(outcome)
            else:
                # If they differed, and ensemble won, algo lost (and vice-versa)
                self.algo_history[algo].append(1.0 - outcome)

        # Check for drift every time we have enough data
        if len(self.history) >= self.window_short:
            self.check_drift()

    def check_drift(self) -> Dict[str, Any]:
        """
        Evaluate all drift metrics and trigger alerts if thresholds exceeded.
        """
        drifts = {}

        # 1. Accuracy Degradation
        acc_drift = self._check_accuracy_drift()
        if acc_drift:
            drifts["accuracy_degradation"] = acc_drift

        # 2. Confidence Calibration Drift
        conf_drift = self._check_confidence_drift()
        if conf_drift:
            drifts["confidence_drift"] = conf_drift

        # 3. Prediction Distribution Shift (PSI)
        dist_drift = self._check_distribution_shift()
        if dist_drift:
            drifts["distribution_shift"] = dist_drift

        # 4. Ensemble Weight Imbalance
        weight_drift = self._check_weight_imbalance()
        if weight_drift:
            drifts["weight_imbalance"] = weight_drift

        # 5. Per-model Win Rate Degradation
        algo_drifts = self._check_algo_win_rates()
        if algo_drifts:
            drifts["algo_performance_drift"] = algo_drifts

        return drifts

    def _check_accuracy_drift(self) -> Optional[Dict[str, Any]]:
        """Detect drop in win rate."""
        if len(self.history) < self.window_short:
            return None

        recent = list(self.history)[-self.window_short :]
        historical = (
            list(self.history)[: -self.window_short]
            if len(self.history) > self.window_short
            else []
        )

        recent_acc = np.mean([x["win"] for x in recent])

        # Compare to baseline (either historical or fixed threshold)
        baseline_acc = (
            np.mean([x["win"] for x in historical]) if historical else 0.55
        )  # Assume 55% as healthy baseline

        diff = baseline_acc - recent_acc
        if diff > self.cfg.drift_accuracy_threshold:
            self._trigger_alert("Accuracy Degradation", recent_acc, baseline_acc)
            return {"recent": recent_acc, "baseline": baseline_acc, "diff": diff}
        return None

    def _check_confidence_drift(self) -> Optional[Dict[str, Any]]:
        """Detect if model is becoming overconfident or underconfident."""
        recent = list(self.history)[-self.window_short :]
        avg_conf = np.mean([x["confidence"] for x in recent])
        avg_win = np.mean([x["win"] for x in recent])

        # In a well-calibrated model, confidence ~ win_rate (approx)
        calibration_error = abs(avg_conf - avg_win)
        if calibration_error > self.cfg.drift_confidence_threshold:
            self._trigger_alert("Confidence Calibration Drift", avg_conf, avg_win)
            return {
                "avg_confidence": avg_conf,
                "win_rate": avg_win,
                "error": calibration_error,
            }
        return None

    def _calculate_psi(
        self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10
    ) -> float:
        """Calculate Population Stability Index."""

        def scale_range(data, min_val, max_val):
            return (data - min_val) / (max_val - min_val + 1e-9)

        # Quantize into buckets
        expected_percents = np.histogram(expected, bins=buckets, range=(0, 1))[0] / len(
            expected
        )
        actual_percents = np.histogram(actual, bins=buckets, range=(0, 1))[0] / len(
            actual
        )

        # Avoid division by zero
        expected_percents = np.clip(expected_percents, 0.0001, 1)
        actual_percents = np.clip(actual_percents, 0.0001, 1)

        psi = np.sum(
            (actual_percents - expected_percents)
            * np.log(actual_percents / expected_percents)
        )
        return float(psi)

    def _check_distribution_shift(self) -> Optional[Dict[str, Any]]:
        """Detect shift in prediction probabilities using PSI."""
        if len(self.history) < self.window_long:
            return None

        recent_probs = np.array(
            [x["probs"] for x in list(self.history)[-self.window_short :]]
        ).flatten()
        historical_probs = np.array(
            [x["probs"] for x in list(self.history)[: -self.window_short]]
        ).flatten()

        psi = self._calculate_psi(historical_probs, recent_probs)
        if psi > self.cfg.drift_psi_threshold:
            self._trigger_alert(
                "Prediction Distribution Shift", psi, self.cfg.drift_psi_threshold
            )
            return {"psi": psi, "threshold": self.cfg.drift_psi_threshold}
        return None

    def _check_weight_imbalance(self) -> Optional[Dict[str, Any]]:
        """Detect if ensemble weights have become too skewed."""
        if not self.history:
            return None

        current_weights = self.history[-1]["weights"]
        # If any model has < 5% weight, it might be dead
        min_weight = min(current_weights.values())
        if min_weight < 0.05:
            self._trigger_alert("Ensemble Weight Imbalance", min_weight, 0.05)
            return {"min_weight": min_weight, "weights": current_weights}
        return None

    def _check_algo_win_rates(self) -> Optional[Dict[str, Any]]:
        """Detect win rate degradation for individual models."""
        drifts = {}
        for algo, history in self.algo_history.items():
            if len(history) < self.window_short:
                continue

            recent_acc = np.mean(list(history)[-self.window_short :])
            historical_acc = (
                np.mean(list(history)[: -self.window_short])
                if len(history) > self.window_short
                else 0.55
            )

            if (historical_acc - recent_acc) > self.cfg.drift_accuracy_threshold:
                self._trigger_alert(f"Algo Drift: {algo}", recent_acc, historical_acc)
                drifts[algo] = {"recent": recent_acc, "historical": historical_acc}

        return drifts if drifts else None

    def _trigger_alert(
        self, metric_name: str, current_value: float, threshold_or_baseline: float
    ) -> None:
        """Log drift event to DB and send monitor alert."""
        logger.warning(
            "DRIFT DETECTED | %s: %.4f (baseline/threshold: %.4f)",
            metric_name,
            current_value,
            threshold_or_baseline,
        )

        if self.db:
            self.db.log_drift_event(
                {
                    "metric_name": metric_name,
                    "metric_value": float(current_value),
                    "threshold": float(threshold_or_baseline),
                    "algorithm": self.cfg.algorithm,
                    "metadata_json": json.dumps(
                        {
                            "window_short": self.window_short,
                            "window_long": self.window_long,
                        }
                    ),
                }
            )

        if self.monitor:
            msg = (
                f"🚨 MODEL DRIFT DETECTED\n"
                f"Metric: {metric_name}\n"
                f"Current: {current_value:.4f}\n"
                f"Baseline/Threshold: {threshold_or_baseline:.4f}\n"
                f"Action: Retraining Recommended"
            )
            self.monitor.send_message(msg)


__all__ = ["PerformanceTracker"]
