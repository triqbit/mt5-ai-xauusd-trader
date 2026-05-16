"""
Tests for RareEventSimulator.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.rare_event_simulator import (
    RareEventConfig,
    RareEventResult,
    RareEventSimulator,
    RareEventType,
)


@pytest.fixture
def simulator():
    return RareEventSimulator(seed=42)


def test_simulator_basic_structure(simulator):
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=200)
    df, result = simulator.generate_scenario(config)

    assert isinstance(df, pd.DataFrame)
    assert isinstance(result, RareEventResult)
    assert len(df) == 200

    # Verify standard columns
    expected_cols = ["open", "high", "low", "close", "tick_volume", "real_volume", "spread"]
    assert all(col in df.columns for col in expected_cols)
    assert not df.isnull().values.any()

    # Verify strict dtypes for pipeline compatibility
    assert df["open"].dtype == np.float32
    assert df["high"].dtype == np.float32
    assert df["low"].dtype == np.float32
    assert df["close"].dtype == np.float32
    assert df["spread"].dtype == np.float32
    assert df["tick_volume"].dtype == np.int64
    assert df["real_volume"].dtype == np.int64

    # Verify named index
    assert df.index.name == "time"


def test_ohlc_consistency(simulator):
    for event_type in RareEventType:
        config = RareEventConfig(event_type=event_type, n_steps=200)
        df, _ = simulator.generate_scenario(config)

        assert (df["high"] >= df["open"]).all()
        assert (df["high"] >= df["close"]).all()
        assert (df["low"] <= df["open"]).all()
        assert (df["low"] <= df["close"]).all()
        assert (df["high"] >= df["low"]).all()

        # Continuity check (except for gaps)
        if event_type != RareEventType.GOLD_GAP:
            # We check if open is very close to previous close
            # In our implementation it should be exact
            opens = df["open"].values[1:]
            prev_closes = df["close"].values[:-1]
            np.testing.assert_allclose(opens, prev_closes, atol=1e-8)


def test_reproducibility(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=100, seed=123)
    df1, res1 = simulator.generate_scenario(config)

    # Re-run with same seed
    df2, res2 = simulator.generate_scenario(config)

    pd.testing.assert_frame_equal(df1, df2)
    assert res1 == res2


def test_flash_crash_behavior(simulator):
    config = RareEventConfig(
        event_type=RareEventType.FLASH_CRASH, n_steps=300, event_magnitude=2.0, recovery_factor=0.8
    )
    df, result = simulator.generate_scenario(config)

    assert result.peak_impact_pct < -0.05
    assert result.recovery_attained > 0.5

    # Check volume spike
    crash_vol = df["tick_volume"].iloc[result.start_index : result.start_index + 10].mean()
    normal_vol = df["tick_volume"].iloc[: result.start_index].mean()
    assert crash_vol > normal_vol * 2

    # Verify peak impact calculation (it should be negative for a crash)
    assert result.peak_impact_pct < 0


def test_liquidity_vacuum_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.LIQUIDITY_VACUUM, n_steps=300)
    df, result = simulator.generate_scenario(config)

    # Should have some very low volume bars
    vacuum_df = df.iloc[result.start_index : result.end_index]
    assert (vacuum_df["tick_volume"] < 10).all()

    # Spreads should be high
    normal_spread = df["spread"].iloc[: result.start_index].mean()
    vacuum_spread = vacuum_df["spread"].mean()
    assert vacuum_spread > normal_spread * 3

    # Volatility in vacuum should be higher
    returns = df["close"].pct_change().dropna()
    vacuum_returns = returns.iloc[result.start_index : result.end_index]
    normal_returns = returns.iloc[: result.start_index]
    assert vacuum_returns.std() > normal_returns.std() * 5

    # Check high/low expansion in vacuum
    vacuum_range = (df["high"] - df["low"]).iloc[result.start_index : result.end_index].mean()
    normal_range = (df["high"] - df["low"]).iloc[: result.start_index].mean()
    assert vacuum_range > normal_range * 2


def test_gold_gap_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=200, event_magnitude=1.0)
    df, result = simulator.generate_scenario(config)

    # Calculate gap
    gap_idx = result.start_index
    gap = df["open"].iloc[gap_idx] - df["close"].iloc[gap_idx - 1]
    assert abs(gap) > 10  # Assuming start_price 2300 and 2% gap
    assert abs(result.peak_impact_pct) > 0.01


def test_violent_reversal_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VIOLENT_REVERSAL, n_steps=400)
    df, result = simulator.generate_scenario(config)

    # Reversal index
    rev_idx = result.start_index

    # Prices before reversal should be generally increasing (due to trend injection)
    # Price after reversal should crash
    pre_rev_price = df["close"].iloc[rev_idx]
    post_rev_price = df["close"].iloc[result.end_index]

    assert pre_rev_price > config.start_price
    assert post_rev_price < pre_rev_price


def test_dislocation_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.DISLOCATION, n_steps=500, event_magnitude=1.0)
    df, result = simulator.generate_scenario(config)

    returns = df["close"].pct_change().dropna()
    pre_dis_returns = returns.iloc[: result.start_index - 1]
    post_dis_returns = returns.iloc[result.start_index + 1 :]

    pre_dis_vol = pre_dis_returns.std()
    post_dis_vol = post_dis_returns.std()

    assert post_dis_vol > pre_dis_vol * 2


def test_vol_cluster_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VOL_CLUSTER, n_steps=500)
    df, _ = simulator.generate_scenario(config)

    returns = df["close"].pct_change().dropna()
    # Volatility should not be constant
    rolling_std = returns.rolling(20).std().dropna()
    assert rolling_std.max() > rolling_std.min() * 3


def test_multi_session_dislocation(simulator):
    config = RareEventConfig(event_type=RareEventType.MULTI_SESSION_DISLOCATION, n_steps=600)
    df, result = simulator.generate_scenario(config)

    assert len(df) == 600
    assert result.event_type == RareEventType.MULTI_SESSION_DISLOCATION
    assert "sessions" in result.description

    # Since sessions are dynamic, we just check that volatility is not uniform
    returns = df["close"].pct_change().dropna()
    # Chunk returns and check standard deviation variation
    chunks = np.array_split(returns, 6)
    vols = [c.std() for c in chunks]
    assert max(vols) > min(vols) * 1.5


def test_reporting_integration(simulator):
    from src.research.reporting import RareEventSection, RareEventSummary

    suite = simulator.generate_suite(n_steps=200)
    section = simulator.generate_report_section(suite)

    assert isinstance(section, RareEventSection)
    assert len(section.scenarios) == len(RareEventType)
    assert isinstance(section.scenarios[0], RareEventSummary)
    assert section.insights != ""
    assert all(s.description != "" for s in section.scenarios)


def test_news_shock_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.NEWS_SHOCK, n_steps=400)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.NEWS_SHOCK
    assert result.peak_impact_pct > 0.01

    returns = df["close"].pct_change().dropna()
    pre_shock_vol = returns.iloc[: result.start_index - 1].std()
    post_shock_vol = returns.iloc[result.start_index : result.end_index].std()

    assert post_shock_vol > pre_shock_vol * 3

    # Institutional Regime Threshold verification
    from src.models.regime_detector import RegimeDetector

    detector = RegimeDetector()
    regime_info = detector.detect(df.iloc[: result.end_index])
    # Should be NEWS_SHOCK or at least VOLATILE_BREAKOUT due to high ER and ATR
    assert regime_info.label in ["news_shock", "volatile_breakout"]


def test_fat_finger_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.FAT_FINGER, n_steps=200, event_magnitude=2.0)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.FAT_FINGER
    assert abs(result.peak_impact_pct) > 0.02

    # Check for the massive wick
    idx = result.start_index
    bar = df.iloc[idx]
    wick_size = (
        (bar["high"] - max(bar["open"], bar["close"]))
        if result.peak_impact_pct > 0
        else (min(bar["open"], bar["close"]) - bar["low"])
    )
    assert wick_size > config.start_price * 0.02

    # Spread should be widened
    assert df.loc[df.index[idx], "spread"] > 2.0


def test_bull_bear_trap_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.BULL_BEAR_TRAP, n_steps=300)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.BULL_BEAR_TRAP
    # Trap means it reversed, so peak impact (the reversal) should be significant
    assert abs(result.peak_impact_pct) > 0.01

    # Check for reversal: final price of event should be on the opposite side of the breakout
    breakout_price = df["close"].iloc[result.start_index + 4]  # End of breakout phase
    final_price = df["close"].iloc[result.end_index - 1]
    start_price = df["close"].iloc[result.start_index - 1]

    if breakout_price > start_price:  # Bull Trap
        assert final_price < breakout_price
    else:  # Bear Trap
        assert final_price > breakout_price


def test_short_squeeze_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.SHORT_SQUEEZE, n_steps=400)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.SHORT_SQUEEZE
    assert result.peak_impact_pct > 0.03

    # Check for parabolic move (acceleration)
    # Returns should be positive during the squeeze phase
    returns = df["close"].pct_change().dropna()
    squeeze_returns = returns.iloc[result.start_index : result.start_index + 10]
    assert (squeeze_returns > 0).any()

    # Check for blow-off top reversal
    post_squeeze_price = df["close"].iloc[result.end_index - 1]
    peak_price = df["close"].iloc[result.start_index : result.end_index].max()
    assert post_squeeze_price < peak_price


def test_cascade_liquidation_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.CASCADE_LIQUIDATION, n_steps=500)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.CASCADE_LIQUIDATION
    assert result.peak_impact_pct < -0.04

    # Check for multiple waves of selling
    # Since it's a cascade, we expect price to be lower at the end than at the start
    start_price = df["close"].iloc[result.start_index - 1]
    final_price = df["close"].iloc[result.end_index - 1]
    assert final_price < start_price


def test_recovery_bars_calculation(simulator):
    # Flash crash is one of the events that explicitly calculates recovery_bars
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=300)
    _, result = simulator.generate_scenario(config)

    assert result.recovery_bars > 0
    # For flash crash, it's defined as int(30 * magnitude)
    assert result.recovery_bars == 30


def test_spread_widening_realism(simulator):
    # High volatility should trigger significant spread widening
    config = RareEventConfig(event_type=RareEventType.NEWS_SHOCK, n_steps=400, event_magnitude=2.0)
    df, result = simulator.generate_scenario(config)

    # During news shock, vols[idx] *= 20.0, so exp(vols * 500) should be large
    shock_spreads = df["spread"].iloc[result.start_index : result.start_index + 5]
    normal_spreads = df["spread"].iloc[: result.start_index - 10]

    assert shock_spreads.mean() > normal_spreads.mean() * 5


def test_generate_suite(simulator):
    suite = simulator.generate_suite(n_steps=200, magnitude=1.5, seed=100)

    assert len(suite) == len(RareEventType)
    for event_type in RareEventType:
        assert event_type.value in suite
        df, result = suite[event_type.value]
        assert len(df) == 200
        assert result.config.event_magnitude == 1.5


def test_custom_bars_per_day(simulator):
    # Test M1 frequency (1440 bars per day)
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=100, bars_per_day=1440)
    df, _ = simulator.generate_scenario(config)

    # Frequency should be 60 seconds (1 minute)
    freq = (df.index[1] - df.index[0]).total_seconds()
    assert freq == 60

    # Test H1 frequency (24 bars per day)
    config_h1 = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=100, bars_per_day=24)
    df_h1, _ = simulator.generate_scenario(config_h1)

    freq_h1 = (df_h1.index[1] - df_h1.index[0]).total_seconds()
    assert freq_h1 == 3600


def test_start_date_config(simulator):
    start_date = "2023-06-01"
    config = RareEventConfig(
        event_type=RareEventType.VOL_CLUSTER, n_steps=100, start_date=start_date
    )
    df, _ = simulator.generate_scenario(config)

    assert df.index[0].strftime("%Y-%m-%d") == start_date


def test_feature_engineer_compatibility(simulator):
    """Verify that generated rare events are compatible with the FeatureEngineer pipeline."""
    from src.core.feature_engineering import FeatureEngineer

    # Use a large enough number of steps for indicators (e.g. EMA 200)
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=500)
    df, _ = simulator.generate_scenario(config)

    fe = FeatureEngineer(normalize=True)
    features = fe.compute_features(df)

    assert isinstance(features, pd.DataFrame)
    assert not features.empty
    assert len(features) > 0
    # Ensure it produces a significant number of features
    assert features.shape[1] > 20
    assert not features.isnull().values.any()


def test_mean_reversion_failure_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.MEAN_REVERSION_FAILURE, n_steps=400)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.MEAN_REVERSION_FAILURE
    assert abs(result.peak_impact_pct) > 0.02

    # Check for the 'grind': volatility should be low during the grind phase
    grind_vols = df["spread"].iloc[result.start_index + 40 : result.end_index]
    # Spread is a proxy for volatility in our generator
    assert grind_vols.mean() < df["spread"].iloc[: result.start_index].mean() * 1.5


def test_silent_trend_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.SILENT_TREND, n_steps=400)
    df, result = simulator.generate_scenario(config)

    assert result.event_type == RareEventType.SILENT_TREND
    assert abs(result.peak_impact_pct) > 0.02

    # Check for low volatility throughout the trend
    returns = df["close"].pct_change().dropna()
    trend_returns = returns.iloc[result.start_index : result.end_index]
    assert trend_returns.std() < config.base_volatility * 1.5


def test_chain_scenarios(simulator):
    configs = [
        RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=100, start_price=2300.0),
        RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=150),
        RareEventConfig(event_type=RareEventType.NEWS_SHOCK, n_steps=100),
    ]

    combined_df, results = simulator.chain_scenarios(configs)

    assert len(combined_df) == 100 + 150 + 100
    assert len(results) == 3

    # Check price continuity
    for i in range(len(combined_df) - 1):
        # We allow small gaps only for GOLD_GAP event indices
        # results[1] is GOLD_GAP, starts at offset 100
        # In Merton implementation, jump indices are randomized, but let's check basic OHLC link
        if i == 99:  # End of first scenario
            # open of next candle should match close of previous unless it's a gap
            # Since GOLD_GAP only injects gaps within its range, the link at 100 should be continuous
            np.testing.assert_allclose(
                combined_df.iloc[i + 1]["open"], combined_df.iloc[i]["close"], atol=1e-5
            )

    # Check results indices
    assert results[0].start_index == 50  # 100 // 2
    assert results[1].start_index >= 100 + (150 // 4)
    assert results[1].start_index <= 100 + (3 * 150 // 4)
    assert results[2].start_index == 100 + 150 + (100 // 3)

    # Check descriptions
    assert "Flash crash" in results[0].description
    assert "Merton Jump-Diffusion" in results[1].description
    assert "News shock" in results[2].description
