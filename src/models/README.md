# Models Module

The `src/models` module houses the AI/ML architectures used for generating trading signals.

## Architectures

- **`ensemble.py`**: A weighted voting ensemble that combines multiple models (PPO, Dreamer, LSTM). It uses dynamic weight rebalancing based on rolling Sharpe ratios.
- **`ppo_agent.py`**: Proximal Policy Optimization agent using Stable-Baselines3.
- **`transformer_model.py`**: (If implemented) Attention-based architectures for sequence modeling.
- **`lstm_attention`**: Bi-directional LSTM with Multi-head attention (defined within `ensemble.py`).

## Ensemble Logic

The `EnsembleModel` blends predictions from multiple sub-models:
- **PPO**: Reinforcement learning agent.
- **LSTM**: Sequential pattern recognition.
- **Dreamer**: World-model based RL.

Weights are adjusted dynamically:
```python
ensemble = EnsembleModel(device="cuda")
ensemble.record_return("ppo", 0.02)  # Track performance for rebalancing
```

## Inference

Predictions return a direction (+1, -1, 0) and a confidence score (0.0 to 1.0).

```python
direction, confidence, votes = ensemble.predict(observation, sequence)
```
