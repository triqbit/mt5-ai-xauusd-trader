## 2025-05-15 - [Vectorized Observation Normalization]
**Learning:** Recalculating rolling mean/std for a sliding window at each step in a RL environment is a major bottleneck ($O(N \cdot F)$). Pre-calculating these via Pandas ($O(F)$ lookup) and using a pre-allocated buffer for the observation vector can provide a significant speedup (~5.5x in this case).
**Action:** Always check for rolling calculations in the main trading or training loop and move them to initialization or use incremental updates.

## 2024-05-16 - [Vectorized Rolling Linear Regression Slope]
**Learning:** Using `rolling().apply(scipy.stats.linregress)` creates a massive (N \cdot W)$ bottleneck due to Python function call overhead and non-vectorized execution. A vectorized closed-form solution using rolling sums provides a ~1600x-2500x speedup while maintaining mathematical equivalence.
**Action:** Replace all `rolling().apply()` calls involving standard statistical formulas with their vectorized counterparts using Pandas/NumPy.

## 2025-05-22 - [Pre-converting DataFrames to NumPy for Environment Observations]
**Learning:** In Gymnasium environments, calling `df.iloc[...].values.astype(np.float32)` inside the `step()` or `_get_observation()` method is a major bottleneck due to pandas indexing overhead and repeated type conversion. Pre-converting the entire DataFrame to a NumPy array during initialization and using direct NumPy slicing provides a ~50x speedup.
**Action:** Always pre-convert static historical DataFrames to NumPy arrays with the target dtype (usually `float32`) in RL environments.
