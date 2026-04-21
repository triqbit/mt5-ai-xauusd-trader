## 2025-05-14 - [TradingEnv Observation Bottleneck]
**Learning:** Calculating rolling statistics (mean/std) at every environment step for observation normalization creates an O(N*W) bottleneck. Precomputing these during initialization using `pandas.rolling` reduces complexity to O(N) and significantly improves training/backtesting speed.
**Action:** Always check RL environments for redundant calculations inside `step()` or `_get_observation()`. Precompute anything that depends only on the static dataset.
