## 2025-05-14 - [TradingEnv Observation Optimization]
**Learning:** Per-step rolling window normalization in Gymnasium environments is a massive bottleneck. Original $O(N \times F)$ calculation at every step can be reduced to $O(F)$ by pre-calculating stats.
**Action:** Use Pandas `rolling().mean()` and `rolling().std(ddof=0)` at initialization to pre-calculate the entire dataset's stats. Use a pre-allocated NumPy buffer for observations to minimize GC and allocation overhead.
