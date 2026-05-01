## 2025-05-15 - [Vectorized Observation Normalization]
**Learning:** Recalculating rolling mean/std for a sliding window at each step in a RL environment is a major bottleneck ($O(N \cdot F)$). Pre-calculating these via Pandas ($O(F)$ lookup) and using a pre-allocated buffer for the observation vector can provide a significant speedup (~5.5x in this case).
**Action:** Always check for rolling calculations in the main trading or training loop and move them to initialization or use incremental updates.
