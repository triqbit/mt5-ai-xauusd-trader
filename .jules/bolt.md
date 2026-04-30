## 2025-05-14 - [Gymnasium Env Observation Optimization]
**Learning:** Pre-calculating rolling mean and standard deviation for Z-score normalization in a trading environment's `_get_observation` method resulted in a ~5.3x performance boost (from ~7k to ~37k steps/sec). Combining this with a pre-allocated observation buffer and avoiding redundant array concatenations significantly reduces the per-step overhead.
**Action:** Always look for O(N) calculations inside the step loop that can be shifted to O(1) lookups via pre-calculation during environment initialization.
