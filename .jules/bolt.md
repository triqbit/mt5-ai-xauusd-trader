## 2024-05-22 - [RL Environment Observation Bottleneck]
**Learning:** Recalculating window statistics (mean/std) in a tight RL loop is a major bottleneck ((W \times F)$ per step). Using `pandas.rolling()` to precompute these for the entire dataset reduces per-step overhead to (1)$ lookup plus normalization broadcasting.
**Action:** Precompute rolling statistics in environment initialization when possible to avoid redundant calculations during training/inference.
