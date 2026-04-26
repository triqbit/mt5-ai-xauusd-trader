# Models Module

The `src/models/` package contains the AI/ML architectures used for market prediction.

## Components

- **ensemble.py**: A weighted voting system that combines PPO, Dreamer V3, and LSTM-Attention models.
- **ppo_agent.py**: Wrapper for Stable-Baselines3 PPO implementation.
- **transformer_model.py**: Transformer-based architecture for sequential market data analysis.

## Usage

```python
from src.models.ensemble import EnsembleModel

model = EnsembleModel(device="cuda")
model.load_ppo("ppo_weights.zip")
direction, confidence, votes = model.predict(observation)
```
