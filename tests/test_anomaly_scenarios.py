"""
Tests for new anomaly and adversarial synthetic scenarios.
"""
import numpy as np
import pytest
import pandas as pd
from src.utils.synthetic_data import AdversarialScenarioBuilder, AnomalyScenarioBuilder

def test_ema_crossover_flicker():
    builder = AdversarialScenarioBuilder(seed=42)
    df = builder.ema_crossover_flicker(n_steps=100, start_price=2300.0)

    assert len(df) == 100
    # Price should oscillate around 2300
    assert df["close"].max() > 2300
    assert df["close"].min() < 2300
    # Check for frequent crossings (diff between price and 2300 changes sign)
    crossings = np.diff(np.sign(df["close"] - 2300))
    assert np.count_nonzero(crossings) > 10

def test_rsi_boundary_oscillation():
    builder = AdversarialScenarioBuilder(seed=42)
    # Target high RSI (e.g., 75)
    df = builder.rsi_boundary_oscillation(n_steps=100, target_rsi=75.0)

    # Simple check: price should generally be increasing
    assert df["close"].iloc[-1] > df["close"].iloc[0]

    # Target low RSI (e.g., 25)
    df_low = builder.rsi_boundary_oscillation(n_steps=100, target_rsi=25.0)
    assert df_low["close"].iloc[-1] < df_low["close"].iloc[0]

def test_ghost_spikes():
    builder = AnomalyScenarioBuilder(seed=42)
    df = builder.ghost_spikes(n_steps=100)

    # Check that spikes exist but close is stable
    # Spikes injected every 10 bars
    spike_idx = df.index[10]
    assert df.loc[spike_idx, "high"] > df.loc[spike_idx, "close"] + 40
    assert df.loc[spike_idx, "low"] < df.loc[spike_idx, "close"] - 40

    # Background volatility is low (0.0001)
    # Check that close price at 10 is near close price at 9
    assert abs(df.loc[spike_idx, "close"] - df.iloc[9]["close"]) < 1.0

def test_stale_data_with_noise():
    builder = AnomalyScenarioBuilder(seed=42)
    df = builder.stale_data_with_noise(n_steps=50)

    # Close prices should be almost identical
    diffs = df["close"].diff().dropna()
    assert (diffs.abs() < 1e-6).all()
    # But they should NOT be exactly zero due to jitter
    assert not (diffs == 0).all()
