"""
Tests for Anomaly and Enhanced Adversarial Scenario Builders.
"""

import pytest

from src.utils.synthetic_data import AdversarialScenarioBuilder, AnomalyScenarioBuilder


@pytest.fixture
def adversarial_builder():
    return AdversarialScenarioBuilder(seed=42)


@pytest.fixture
def anomaly_builder():
    return AnomalyScenarioBuilder(seed=42)


def test_ema_crossover_flicker(adversarial_builder):
    df = adversarial_builder.ema_crossover_flicker(n_steps=50)
    # Check that we have enough data (base 100 + flicker 50)
    assert len(df) == 150

    # Calculate EMA21
    ema21 = df["close"].ewm(span=21, adjust=False).mean()

    # Check that last 50 steps are flickering around EMA21
    flicker_part = df.iloc[-50:]
    crossovers = 0
    for i in range(len(flicker_part) - 1):
        idx = flicker_part.index[i]
        next_idx = flicker_part.index[i + 1]
        if (df.loc[idx, "close"] > ema21.loc[idx]) != (
            df.loc[next_idx, "close"] > ema21.loc[next_idx]
        ):
            crossovers += 1

    # We expect high frequency crossovers
    assert crossovers > 10


def test_rsi_boundary_oscillation(adversarial_builder):
    df = adversarial_builder.rsi_boundary_oscillation(n_steps=100)
    assert len(df) == 200

    # Calculate RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    rsi = 100 - (100 / (1 + rs))

    # In the second half, RSI should be near the boundary (usually > 60 after a trend)
    osc_rsi = rsi.iloc[-50:]
    assert osc_rsi.mean() > 60
    assert osc_rsi.std() < 5.0  # Stable around the target


def test_ghost_spikes(anomaly_builder):
    df = anomaly_builder.ghost_spikes(n_steps=100)
    # Check for extreme wicks at specific indices
    for i in [20, 40, 60, 80]:
        idx = df.index[i]
        if i % 40 == 20:
            assert df.loc[idx, "high"] > df.loc[idx, "open"] + 45.0
        else:
            assert df.loc[idx, "low"] < df.loc[idx, "open"] - 45.0

    # Check that close is stable (close matches open closely in ranging)
    for i in [20, 40, 60, 80]:
        idx = df.index[i]
        assert abs(df.loc[idx, "close"] - df.loc[idx, "open"]) < 1.0


def test_stale_data_with_noise(anomaly_builder):
    df = anomaly_builder.stale_data_with_noise(n_steps=100)
    # Price should be extremely flat
    assert df["close"].std() < 0.001

    # Verify minimal jitter
    diffs = df["close"].diff().dropna()
    assert (diffs.abs() < 1e-5).all()
    # Ensure it's not EXACTLY zero (noise exists)
    assert (diffs.abs() > 0).any()
