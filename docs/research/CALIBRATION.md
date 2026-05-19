# Confidence Calibration & Reliability Analysis

## Overview
Confidence calibration measures how well a model's predicted confidence scores correspond to its actual likelihood of being correct. In institutional trading, a well-calibrated model is critical because overconfident weak signals can lead to excessive risk exposure and poor capital allocation.

The `CalibrationEngine` in `src/models/calibration.py` provides the tools to audit model reliability and improve it through systematic tuning.

## Key Metrics

### 1. Brier Score & Decomposition
The Brier score measures the mean squared difference between predicted probabilities and actual binary outcomes.
- **Reliability:** Measures how close the predicted probabilities are to the true frequencies (lower is better).
- **Resolution:** Measures how much the predicted probabilities differ from the base rate (higher is better).
- **Uncertainty:** Measures the inherent variability of the outcomes.

### 2. Expected Calibration Error (ECE)
The weighted average of the absolute difference between confidence and accuracy across different confidence buckets. It provides a single number summarizing the overall calibration quality.

### 3. Maximum Calibration Error (MCE)
The largest deviation between confidence and accuracy across all buckets, highlighting the worst-case miscalibration.

## Operational Features

### Confidence Buckets
Predictions are grouped into bins (e.g., 10% increments) to visualize the reliability curve. A perfectly calibrated model would have an accuracy of X% in the X% confidence bucket.

### Threshold Tuning
The engine can find the optimal confidence threshold to maximize a specific metric:
- **F1-Score:** Balances precision and recall.
- **Precision:** Prioritizes signal accuracy over volume.
- **Accuracy:** Maximizes overall correct predictions.

### Calibration Methods
The engine supports multiple calibration techniques via the `fit()` and `calibrate()` methods:
- **Temperature Scaling:** Optimizes a single parameter (T) to minimize Brier score. It preserves the ranking of predictions but shifts the distribution.
- **Platt Scaling:** Fits a logistic regression model on the logits of the predictions. Effective for sigmoid-based outputs.
- **Isotonic Regression:** A non-parametric method that fits a monotonic function to the predictions. Most flexible but requires more data to avoid overfitting.

### Mitigation Strategies
- **Heuristic Damping:** Automatically reduces confidence scores when high ECE is detected to prevent overconfident execution.

## Research Integration
Calibration audits are automatically included in institutional research reports, providing researchers with:
- **Reliability Tables:** Detailed breakdown of performance by confidence range.
- **Status Indicators:** VERIFIED, WARNING, or CRITICAL based on ECE thresholds.
- **Operational Insights:** Actionable recommendations for threshold adjustments.
