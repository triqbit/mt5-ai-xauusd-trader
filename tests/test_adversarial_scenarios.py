"""
Tests for Adversarial and Transition Scenario Builders.
"""

import pytest

from src.models.regime_detector import MarketRegime, RegimeDetector
from src.utils.synthetic_data import AdversarialScenarioBuilder, RegimeTransitionScenarioBuilder


@pytest.fixture
def transition_builder():
    return RegimeTransitionScenarioBuilder(seed=42)


@pytest.fixture
def adversarial_builder():
    return AdversarialScenarioBuilder(seed=42)


@pytest.fixture
def detector():
    return RegimeDetector(window=20, long_window=100)


def test_ranging_to_news_shock(transition_builder, detector):
    df = transition_builder.ranging_to_news_shock(n_steps=200)

    # Analyze the transition
    # First half should be ranging
    info_start = detector.detect(df.iloc[:100])
    assert info_start.label == MarketRegime.RANGING

    # At the peak of the shock
    info_shock = detector.detect(df.iloc[:110])
    # News shock detection is sensitive to the window.
    # Let's verify it triggers a high volatility/transition state.
    assert info_shock.label in [MarketRegime.NEWS_SHOCK, MarketRegime.VOLATILE_BREAKOUT]
    assert info_shock.transition_score > 0.5


def test_trending_to_reversal(transition_builder, detector):
    df = transition_builder.trending_to_reversal(n_steps=200)

    # First half: Trending
    info_trend = detector.detect(df.iloc[:100])
    assert info_trend.label == MarketRegime.TRENDING

    # After reversal
    info_reversal = detector.detect(df)
    # Reversal might be classified as Volatile Breakout or Trending (bearish) or News Shock
    # depending on sharpness.
    assert info_reversal.label != MarketRegime.TRENDING or info_reversal.raw_features["slope"] < 0


def test_volatile_to_ranging(transition_builder, detector):
    df = transition_builder.volatile_to_ranging(n_steps=200)

    # End state should be ranging
    info_end = detector.detect(df)
    assert info_end.label == MarketRegime.RANGING


def test_wick_trap_cascade(adversarial_builder):
    df = adversarial_builder.wick_trap_cascade(n_steps=50)

    # Check for massive wicks in the target range
    for i in range(10, 20):
        if i % 2 == 0:
            assert df.iloc[i]["high"] > df.iloc[i]["close"] + 15.0
        else:
            assert df.iloc[i]["low"] < df.iloc[i]["close"] - 15.0


def test_liquidity_void(adversarial_builder):
    df = adversarial_builder.liquidity_void(n_steps=50)

    # Check for continuity breaks (Open[i] != Close[i-1])
    opens = df["open"].values[1:]
    closes = df["close"].values[:-1]

    has_break = False
    for o, c in zip(opens, closes, strict=False):
        if abs(o - c) > 10.0:
            has_break = True
            break
    assert has_break


def test_vov_explosion(adversarial_builder, detector):
    df = adversarial_builder.vov_explosion(n_steps=150)

    # Label history and check vol_of_vol feature
    df_labeled = detector.label_history(df)
    vov_values = df_labeled["regime_transition_score"].values  # Transition score incorporates VOV

    # In vov_explosion, we expect some very high transition scores due to unstable variance
    assert vov_values.max() > 0.4
