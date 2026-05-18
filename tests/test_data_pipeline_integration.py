"""
MT5 AI/ML Trading Bot - Data Pipeline Integration Test
tests/test_data_pipeline_integration.py

Verifies the high-value integration path:
Data Ingestion (Synthetic) -> Feature Generation -> Model Input/Inference
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Standardize mocks for use across all tests and imports
mock_torch = MagicMock()
mock_sb3 = MagicMock()
mock_talib = MagicMock()


# Ensure we have some default behaviors to avoid basic crashes
def default_talib_effect(data, *args, **kwargs):
    if hasattr(data, "__len__"):
        return np.random.rand(len(data))
    return 0.0


mock_talib.RSI.side_effect = default_talib_effect
mock_talib.MACD.side_effect = lambda d, *a, **k: (
    np.random.rand(len(d)),
    np.random.rand(len(d)),
    np.random.rand(len(d)),
)
mock_talib.ATR.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
mock_talib.BBANDS.side_effect = lambda c, *a, **k: (
    np.random.rand(len(c)),
    np.random.rand(len(c)),
    np.random.rand(len(c)),
)
mock_talib.EMA.side_effect = default_talib_effect
mock_talib.ADX.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
mock_talib.STOCH.side_effect = lambda h, low, c, *a, **k: (
    np.random.rand(len(c)),
    np.random.rand(len(c)),
)
mock_talib.OBV.side_effect = lambda c, v, *a, **k: np.random.rand(len(c))
mock_talib.MFI.side_effect = lambda h, low, c, v, *a, **k: np.random.rand(len(c))
mock_talib.CCI.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
mock_talib.MOM.side_effect = lambda c, *a, **k: np.random.rand(len(c))
mock_talib.get_function_groups.return_value = {"Pattern Recognition": []}

# Setup the system modules with our mocks BEFORE importing src components
with patch.dict(
    "sys.modules",
    {
        "torch": mock_torch,
        "torch.nn": mock_torch.nn,
        "stable_baselines3": mock_sb3,
        "talib": mock_talib,
    },
):
    # Import components we want to test
    from src.core.constants import SignalDirection
    from src.core.feature_engineering import FeatureEngineer
    from src.models import ensemble  # Use the module to avoid attribute errors on reload
    from src.models.ensemble import EnsembleModel
    from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def data_generator():
    return ScenarioGenerator(seed=42)


@pytest.fixture
def feature_engineer():
    return FeatureEngineer(base_timeframe="M1", timeframes=["M5", "M15"])


@pytest.fixture
def mock_ensemble():
    # Patch torch and LSTMModel within the ensemble module specifically
    with (
        patch.object(ensemble, "torch", mock_torch),
        patch.object(ensemble, "LSTMModel", MagicMock()),
    ):
        model = EnsembleModel(device="cpu")
        model.ppo_agent = MagicMock()
        from src.core.constants import SignalDirection
        from src.models.base_model import Signal

        model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.8)
        return model


def setup_mock_talib(m_talib):
    """Refined helper to ensure mock talib doesn't cause unpacking errors."""
    m_talib.RSI.side_effect = lambda data, *a, **k: np.random.rand(len(data))
    m_talib.MACD.side_effect = lambda data, *a, **k: (
        np.random.rand(len(data)),
        np.random.rand(len(data)),
        np.random.rand(len(data)),
    )
    m_talib.ATR.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
    m_talib.BBANDS.side_effect = lambda c, *a, **k: (
        np.random.rand(len(c)),
        np.random.rand(len(c)),
        np.random.rand(len(c)),
    )
    m_talib.EMA.side_effect = lambda data, *a, **k: np.random.rand(len(data))
    m_talib.ADX.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
    m_talib.STOCH.side_effect = lambda h, low, c, *a, **k: (
        np.random.rand(len(c)),
        np.random.rand(len(c)),
    )
    m_talib.OBV.side_effect = lambda c, v, *a, **k: np.random.rand(len(c))
    m_talib.MFI.side_effect = lambda h, low, c, v, *a, **k: np.random.rand(len(c))
    m_talib.CCI.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
    m_talib.MOM.side_effect = lambda c, *a, **k: np.random.rand(len(c))
    m_talib.WILLR.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
    m_talib.ULTOSC.side_effect = lambda h, low, c, *a, **k: np.random.rand(len(c))
    m_talib.LINEARREG_SLOPE.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.HT_TRENDLINE.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.HT_DCPERIOD.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.HT_PHASOR.side_effect = lambda x, *a, **k: (
        np.random.rand(len(x)),
        np.random.rand(len(x)),
    )
    m_talib.HT_SINE.side_effect = lambda x, *a, **k: (
        np.random.rand(len(x)),
        np.random.rand(len(x)),
    )
    m_talib.HT_TRENDMODE.side_effect = lambda x, *a, **k: np.random.randint(0, 2, len(x)).astype(
        float
    )
    m_talib.SMA.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.SUM.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.MAX.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.MIN.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.ROCP.side_effect = lambda x, *a, **k: np.random.rand(len(x))
    m_talib.get_function_groups.return_value = {"Pattern Recognition": []}


def test_data_to_model_inference_flow(data_generator, feature_engineer, mock_ensemble):
    """Path: Raw OHLCV -> FeatureEngineer -> EnsembleModel.predict"""
    n_steps = 500
    df = data_generator.generate(n_steps=n_steps, regime="trending")
    df.index = pd.date_range(start="2024-01-01", periods=n_steps, freq="1min")

    # The FeatureEngineer uses the 'talib' module imported at the top of src/core/feature_engineering.py
    # We must patch it there.
    import src.core.feature_engineering as fe_mod

    with patch.object(fe_mod, "talib", mock_talib):
        setup_mock_talib(mock_talib)
        features = feature_engineer.compute_features(df)

    assert not features.empty
    assert features.shape[1] > 20

    latest_obs = features.iloc[-1].values
    signal = mock_ensemble.predict(latest_obs)

    assert isinstance(signal.direction, SignalDirection)
    assert 0.0 <= signal.confidence <= 1.0
    assert "ppo" in signal.metadata["per_algo_votes"]
    mock_ensemble.ppo_agent.predict.assert_called_once()

    called_obs = mock_ensemble.ppo_agent.predict.call_args[0][0]
    np.testing.assert_array_equal(called_obs, latest_obs)


def test_pipeline_resilience_to_malformed_data(data_generator, feature_engineer, mock_ensemble):
    """Verifies that the pipeline handles malformed data without crashing."""
    df_malformed = data_generator.generate(n_steps=100, regime="malformed")
    df_malformed.index = pd.date_range(start="2024-01-01", periods=100, freq="1min")

    import src.core.feature_engineering as fe_mod

    with patch.object(fe_mod, "talib", mock_talib):
        setup_mock_talib(mock_talib)
        features = feature_engineer.compute_features(df_malformed)

    if not features.empty:
        obs = features.iloc[-1].values
        direction, _confidence, _ = mock_ensemble.predict(obs)
        assert direction in SignalDirection


def test_pipeline_insufficient_history(data_generator, feature_engineer):
    """Verifies behavior when data is too short for technical indicators."""
    n_short = 10
    df_short = data_generator.generate(n_steps=n_short, regime="ranging")
    df_short.index = pd.date_range(start="2024-01-01", periods=n_short, freq="1min")

    import src.core.feature_engineering as fe_mod

    with patch.object(fe_mod, "talib", mock_talib):
        setup_mock_talib(mock_talib)
        # Force NaNs to simulate indicator warmup
        mock_talib.MACD.side_effect = lambda data, *a, **k: (
            np.full(len(data), np.nan),
            np.full(len(data), np.nan),
            np.full(len(data), np.nan),
        )

        features = feature_engineer.compute_features(df_short)

    assert features.empty


def test_mtf_feature_alignment(data_generator, feature_engineer):
    """Ensures MTF features are present and correctly aligned."""
    n_steps = 1000
    df = data_generator.generate(n_steps=n_steps, regime="ranging")
    df.index = pd.date_range(start="2024-01-01", periods=n_steps, freq="1min")

    import src.core.feature_engineering as fe_mod

    with patch.object(fe_mod, "talib", mock_talib):
        setup_mock_talib(mock_talib)
        features = feature_engineer.compute_features(df)

    mtf_cols = [c for c in features.columns if "mtf_" in c]
    assert len(mtf_cols) > 0
    assert not features[mtf_cols].iloc[-1].isnull().any()
