## 2025-05-15 - [Pandas vs Numpy rolling std consistency]
**Learning:** Pandas `rolling().std()` defaults to `ddof=1` (unbiased), while `numpy.std()` defaults to `ddof=0`. When optimizing existing Numpy-based normalization logic with Pandas, `ddof=0` must be explicitly set to maintain exact observation consistency for RL agents.
**Action:** Always specify `ddof` explicitly when mixing Pandas and Numpy for statistical calculations to avoid subtle data distribution shifts.

## 2025-05-15 - [Pre-allocation in RL environments]
**Learning:** In Gymnasium environments, `_get_observation` is a hot path. Array concatenation (`np.concatenate`) and repeated slicing/casting are major bottlenecks.
**Action:** Pre-allocate observation buffers and use `ravel()` or `view()` where possible. Pre-calculate rolling statistics for the entire dataset during initialization if the environment uses a fixed dataset (e.g., historical backtesting).
