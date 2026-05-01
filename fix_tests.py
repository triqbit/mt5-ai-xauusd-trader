import sys
import re

filepath = 'tests/test_e2e_scenarios.py'
with open(filepath, 'r') as f:
    content = f.read()

fixed_test = """def test_ensemble_model_with_gapping_data(mock_cfg):
    \"\"\"Test EnsembleModel behavior when encountering gapping market data.\"\"\"
    import sys
    from unittest.mock import MagicMock

    # Mock dependencies to avoid import errors
    torch_mock = MagicMock()
    # We need to make torch look like a package so torch.nn works
    torch_mock.__path__ = []

    with patch.dict(sys.modules, {
        "torch": torch_mock,
        "torch.nn": MagicMock(),
        "stable_baselines3": MagicMock(),
        "stable_baselines3.common": MagicMock(),
    }):
        from src.models.ensemble import EnsembleModel

        with patch("src.models.ensemble.torch"), \
             patch("src.models.ensemble.LSTMAttentionModel"), \
             patch("stable_baselines3.PPO"):

            model = EnsembleModel(device="cpu")

            gen = ScenarioGenerator(seed=123)
            df = gen.generate(n_steps=10, regime="gapping")

            # Simple test to ensure predict can handle the data structure
            for i in range(len(df)):
                obs = df.iloc[i][["open", "high", "low", "close", "tick_volume"]].values
                # Should not crash
                direction, confidence, per_algo = model.predict(obs)
                assert direction in [-1, 0, 1]
"""

new_content = re.sub(r'def test_ensemble_model_with_gapping_data\(mock_cfg\):.*?assert direction in \[-1, 0, 1\]', fixed_test, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(new_content)
