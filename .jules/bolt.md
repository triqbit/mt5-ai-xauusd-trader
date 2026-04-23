## 2025-05-15 - [Optimize TradingEnv observation generation]
**Learning:** Calculating rolling window statistics (mean/std) at every step in an RL environment is a significant bottleneck. Precomputing these using pandas (C-optimized) in __init__ and using O(1) lookups during the step reduces latency by ~80%.
**Action:** Always look for sliding window calculations in environment 'step' or 'get_observation' methods and precompute them if the dataset is known beforehand.
