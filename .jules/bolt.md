## 2025-05-15 - [Optimization of RL Environment Observation Normalization]
**Learning:** In Reinforcement Learning environments, calculating rolling statistics (mean/std) for every observation window using NumPy in each `step()` is a major bottleneck ($O(W \cdot F)$). Using `pandas.rolling()` to pre-calculate these statistics for the entire dataset during initialization reduces per-step complexity to $O(F)$ for normalization, leading to significant speedups (~68% in this case).
**Action:** Always look for opportunities to move statistical calculations out of the simulation loop by pre-calculating them if the dataset is known beforehand (common in training/backtesting). Be careful with window alignment (the statistic at index $i$ corresponds to the window $[i-W+1:i+1]$).
>>>>>>> REPLACE
