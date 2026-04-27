import numpy as np
import pytest
from src.models.calibration import ModelCalibrator, CalibrationMetrics, CalibrationReport

def test_calculate_metrics_perfect_calibration():
    calibrator = ModelCalibrator(n_bins=5)
    # Perfect calibration: confidence equals outcome probability
    confidences = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
    outcomes = np.array([0, 0, 1, 1, 1])  # Not exactly matching, but let's use more samples

    confidences = np.repeat([0.2, 0.8], 50)
    outcomes = np.concatenate([np.zeros(40), np.ones(10), np.zeros(10), np.ones(40)])
    # 0.2 bin: 10/50 = 0.2 accuracy
    # 0.8 bin: 40/50 = 0.8 accuracy

    metrics = calibrator.calculate_metrics(confidences, outcomes)

    assert metrics.ece == pytest.approx(0.0, abs=1e-5)
    assert metrics.mce == pytest.approx(0.0, abs=1e-5)
    assert len(metrics.reliability_curve) == 2

def test_calculate_metrics_overconfident():
    calibrator = ModelCalibrator(n_bins=10)
    confidences = np.array([0.9, 0.9, 0.9])
    outcomes = np.array([0, 0, 1])  # 33% accuracy for 90% confidence

    metrics = calibrator.calculate_metrics(confidences, outcomes)

    assert metrics.ece > 0.5
    assert metrics.mce > 0.5

def test_find_optimal_threshold():
    calibrator = ModelCalibrator()
    confidences = np.array([0.1, 0.2, 0.5, 0.7, 0.8, 0.9])
    outcomes = np.array([0, 0, 0, 1, 1, 1])

    # Target 100% accuracy (possible at 0.7+)
    # np.linspace(0.0, 0.95, 20) -> [0.  , 0.05, 0.1 , 0.15, 0.2 , 0.25, 0.3 , 0.35, 0.4 , 0.45, 0.5 , 0.55, 0.6 , 0.65, 0.7 , 0.75, 0.8 , 0.85, 0.9 , 0.95]
    # at t=0.55, mask is [0.7, 0.8, 0.9], acc = 1.0. This is the first t >= 0.55 that yields 100% accuracy.
    # Wait, if t=0.55, then conf >= 0.55 are [0.7, 0.8, 0.9]. All are 1. So acc = 1.0.
    threshold = calibrator.find_optimal_threshold(confidences, outcomes, min_accuracy=1.0)
    assert threshold == pytest.approx(0.55, abs=0.01)

def test_generate_report():
    calibrator = ModelCalibrator()
    confidences = np.array([0.8, 0.85, 0.9])
    outcomes = np.array([1, 1, 1])

    report = calibrator.generate_report("test_algo", confidences, outcomes)

    assert report.algorithm == "test_algo"
    # avg_conf = 0.85, accuracy = 1.0. ECE = 0.15.
    # Status logic: ECE < 0.05 -> Well, < 0.15 -> Adequate, else Under/Over
    assert report.status == "Underconfident"

def test_temperature_scaling():
    calibrator = ModelCalibrator()
    logits = np.array([[1.0, 2.0, 0.0]])

    # High temperature -> more uniform
    probs_high_t = calibrator.apply_temperature_scaling(logits, temperature=10.0)
    assert np.allclose(probs_high_t, [1/3, 1/3, 1/3], atol=0.1)

    # Low temperature -> more sharp
    probs_low_t = calibrator.apply_temperature_scaling(logits, temperature=0.1)
    assert probs_low_t[0, 1] > 0.99

def test_empty_input():
    calibrator = ModelCalibrator()
    metrics = calibrator.calculate_metrics(np.array([]), np.array([]))
    assert metrics.ece == 0.0
    assert metrics.reliability_curve == []
