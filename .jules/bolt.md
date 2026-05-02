## 2025-05-15 - [Vectorized Observation Normalization]
**Learning:** Recalculating rolling mean/std for a sliding window at each step in a RL environment is a major bottleneck ($O(N \cdot F)$). Pre-calculating these via Pandas ($O(F)$ lookup) and using a pre-allocated buffer for the observation vector can provide a significant speedup (~5.5x in this case).
**Action:** Always check for rolling calculations in the main trading or training loop and move them to initialization or use incremental updates.

## 2024-05-16 - [Vectorized Rolling Linear Regression Slope]
**Learning:** Using `rolling().apply(scipy.stats.linregress)` creates a massive (N \cdot W)$ bottleneck due to Python function call overhead and non-vectorized execution. A vectorized closed-form solution using rolling sums provides a ~1600x-2500x speedup while maintaining mathematical equivalence.
**Action:** Replace all `rolling().apply()` calls involving standard statistical formulas with their vectorized counterparts using Pandas/NumPy.
