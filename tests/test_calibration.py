import numpy as np
import pytest

from src.models.calibration import CalibrationEngine, CalibrationResult


def test_calibration_engine_perfect():
    """Verify metrics for a perfectly calibrated model."""
    engine = CalibrationEngine(n_bins=10)
    confidences = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    # For a perfectly calibrated model, outcomes should match confidence probabilities.
    # In a deterministic test, we can use outcomes that match the bins.
    outcomes = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])  # Rough approximation

    result = engine.analyze(confidences, outcomes)

    assert isinstance(result, CalibrationResult)
    assert result.brier_score >= 0.0
    assert result.ece >= 0.0
    assert len(result.buckets) > 0


def test_calibration_engine_empty():
    """Verify behavior with empty data."""
    engine = CalibrationEngine()
    result = engine.analyze([], [])
    assert result.status == "NO_DATA"
    assert result.brier_score == 0.0
    assert result.ece == 0.0
    assert result.buckets == []


def test_calibration_engine_overconfident():
    """Verify metrics for an overconfident model."""
    engine = CalibrationEngine(n_bins=5)
    # Model says 90% confidence for everything, but only 50% are correct.
    confidences = np.full(100, 0.9)
    outcomes = np.array([1] * 50 + [0] * 50)

    result = engine.analyze(confidences, outcomes)

    # ECE should be high (around 0.4: 0.9 confidence - 0.5 accuracy)
    assert result.ece == pytest.approx(0.4)
    assert result.status == "CRITICAL"


def test_threshold_tuning():
    """Verify optimal threshold finding."""
    engine = CalibrationEngine()
    # Model is better at higher confidence
    confidences = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    outcomes = np.array([0, 0, 1, 1, 1])

    # At 0.7 threshold, we get 3/3 correct (Precision 1.0, Recall 1.0)
    opt_t = engine.tune_thresholds(confidences, outcomes, metric="f1")
    assert opt_t >= 0.7


def test_temperature_scaling():
    """Verify temperature scaling adjustment."""
    engine = CalibrationEngine()
    confidences = np.array([0.8, 0.9])

    # T > 1 should push towards 0.5
    scaled_high = engine.apply_temperature_scaling(confidences, temperature=2.0)
    assert np.all(scaled_high < confidences)
    assert np.all(scaled_high > 0.5)

    # T < 1 should push towards extremes
    scaled_low = engine.apply_temperature_scaling(confidences, temperature=0.5)
    assert np.all(scaled_low > confidences)


def test_overconfidence_mitigation():
    """Verify overconfidence mitigation heuristic."""
    engine = CalibrationEngine()
    confidences = np.array([0.9, 0.95])

    # If ECE is high, it should reduce confidence
    mitigated = engine.mitigate_overconfidence(confidences, ece=0.2)
    assert np.all(mitigated < confidences)

    # If ECE is low, it should do nothing or very little
    stable = engine.mitigate_overconfidence(confidences, ece=0.01)
    assert np.all(stable == confidences)
