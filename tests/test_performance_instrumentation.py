
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.models.ensemble import EnsembleModel


def test_feature_engineer_profiling_blocks():
    """Verify that FeatureEngineer uses the granular profiling blocks."""
    fe = FeatureEngineer(base_timeframe="M5")
    df = pd.DataFrame({
        'open': np.random.randn(100),
        'high': np.random.randn(100),
        'low': np.random.randn(100),
        'close': np.random.randn(100),
        'tick_volume': np.random.randn(100)
    })
    df.index = pd.date_range(start='2023-01-01', periods=100, freq='5min')

    with patch('src.core.feature_engineering.profile') as mock_profile:
        fe.compute_features(df)

        # Check for expected labels
        expected_labels = {
            "compute_features_total",
            "fe_base_technical",
            "fe_candle_patterns",
            "fe_price_action",
            "fe_volume",
            "fe_mtf_all"
        }
        actual_labels = {call.args[0] for call in mock_profile.call_args_list}
        for label in expected_labels:
            assert label in actual_labels

def test_ensemble_model_profiling_blocks():
    """Verify that EnsembleModel uses profiling blocks for sub-models."""
    model = EnsembleModel()
    model.ppo_agent = MagicMock()
    # Mock the return value of ppo.predict which returns a Signal
    from src.core.constants import SignalDirection
    from src.models.base_model import Signal
    model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.8)

    features = np.random.randn(140)

    with patch('src.models.ensemble.profile') as mock_profile:
        # PPO path
        model.predict(features)

        actual_labels = {call.args[0] for call in mock_profile.call_args_list}
        assert "inference_ppo" in actual_labels

def test_feature_engineer_fallback_logic():
    """Verify that compute_features doesn't return empty DF if MTF data is short."""
    # Provide only 5 bars
    df = pd.DataFrame({
        'open': np.random.randn(5),
        'high': np.random.randn(5),
        'low': np.random.randn(5),
        'close': np.random.randn(5),
        'tick_volume': np.random.randn(5)
    })
    df.index = pd.date_range(start='2023-01-01', periods=5, freq='5min')

    # It should not crash and should ideally return base features if we allow it,
    # but currently our implementation drops rows where base indicators (like EMA 200) are NaN.
    # With 5 bars, even base technicals will be NaN.
    # Let's try with 300 bars but insufficient for H4/D1.

    fe_full = FeatureEngineer(base_timeframe="M5", timeframes=["D1"])
    df_long = pd.DataFrame({
        'open': np.random.randn(300),
        'high': np.random.randn(300),
        'low': np.random.randn(300),
        'close': np.random.randn(300),
        'tick_volume': np.random.randn(300)
    })
    df_long.index = pd.date_range(start='2023-01-01', periods=300, freq='5min')

    # 300 bars of M5 is ~25 hours, enough for base indicators but NOT for D1 indicators (window 14-200)
    result = fe_full.compute_features(df_long)
    # If fallback works, it should contain base features
    assert not result.empty
    assert any(c.startswith("base_") for c in result.columns)
