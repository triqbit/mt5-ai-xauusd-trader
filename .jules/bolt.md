## 2025-05-15 - [Vectorized Observation Normalization]
**Learning:** Recalculating rolling mean/std for a sliding window at each step in a RL environment is a major bottleneck ((N \cdot F)$). Pre-calculating these via Pandas ((F)$ lookup) and using a pre-allocated buffer for the observation vector can provide a significant speedup (~5.5x in this case).
**Action:** Always check for rolling calculations in the main trading or training loop and move them to initialization or use incremental updates.

## 2024-05-16 - [Vectorized Rolling Linear Regression Slope]
**Learning:** Using `rolling().apply(scipy.stats.linregress)` creates a massive (N \cdot W)$ bottleneck due to Python function call overhead and non-vectorized execution. A vectorized closed-form solution using rolling sums provides a ~1600x-2500x speedup while maintaining mathematical equivalence.
**Action:** Replace all `rolling().apply()` calls involving standard statistical formulas with their vectorized counterparts using Pandas/NumPy.

## 2025-05-22 - [Pre-converting DataFrames to NumPy for Environment Observations]
**Learning:** In Gymnasium environments, calling `df.iloc[...].values.astype(np.float64)` inside the `step()` or `_get_observation()` method is a major bottleneck due to pandas indexing overhead and repeated type conversion. Pre-converting the entire DataFrame to a NumPy array during initialization and using direct NumPy slicing provides a ~50x speedup.
**Action:** Always pre-convert static historical DataFrames to NumPy arrays with the target dtype (usually `float32`) in RL environments.

## 2025-05-23 - [Vectorized Rolling Linear Regression Slope in Backtester]
**Learning:** Manual Python loops for rolling statistics (like linear regression slope) are a major bottleneck in backtesting. Replacing a (N \cdot W)$ loop with a vectorized dot product using `np.convolve` with reversed weights (`weights[::-1]`) provides a ~200x speedup.
**Action:** Ensure vectorized output array length parity with input by using explicit length checks (`if n >= window`) and padding, especially for small $ cases.

## 2026-05-08 - [Incremental Peak Tracking for Drawdown]
**Learning:** Calculating peak equity using `max()` on a growing list inside a loop creates an O(N^2) complexity bottleneck. For 50,000 bars, this results in significant slowdowns. Tracking the peak incrementally in O(1) reduces total complexity to O(N).
**Action:** Always maintain running statistics (max, min, sum) for metrics used inside iterative loops instead of re-scanning historical lists.

## 2026-05-10 - [Eliminating Redundant DataFrame Slicing in Backtest Loops]
**Learning:** Repeatedly slicing a DataFrame using `.iloc[:idx]` inside a high-frequency loop (e.g., a backtester scanning 50,000+ bars) introduces significant overhead because Pandas creates a new (though often shallow) object and performs index alignment checks on every call. If technical indicators are already precomputed, passing `None` to validation methods can eliminate this $O(N^2)$ slicing pattern entirely.
**Action:** When precomputing metrics for a loop, ensure the downstream consumers can accept `None` for the raw market data to avoid expensive and redundant slicing operations.
