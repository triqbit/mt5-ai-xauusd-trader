## 2026-04-29 - [Optimizing Gymnasium Environment Observation Generation]
**Learning:** In RL environments, calculating rolling statistics (mean, std) for every observation is a significant bottleneck, especially as the window size or feature count grows. Pre-calculating these values using vectorized libraries like Pandas and using a pre-allocated buffer can lead to >3x speedup.
**Action:** Always profile the `_get_observation` method in custom Gymnasium environments. Prefer pre-computation and buffer reuse over on-the-fly calculation and concatenation.
