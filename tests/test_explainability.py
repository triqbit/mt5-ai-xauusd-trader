"""
Unit tests for the explainability module.
"""

from src.core.explainability import (
    SignalDirection,
    SignalExplainer,
    SignalExplanation,
)
from src.core.schemas import TradeSignal
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.trading.execution_filter import ExecutionDecision


def test_signal_explanation_pydantic_validation():
    """Test that SignalExplanation correctly validates its fields."""
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "total_confidence": 0.85,
        "execution_summary": {
            "passed": True,
            "filters": [{"filter_name": "Spread", "passed": True, "value": 0.5}],
            "summary": "Execution OK",
        },
        "model_attributions": [
            {"model_name": "PPO", "vote": 1, "confidence": 0.85, "weight": 0.6, "is_dominant": True}
        ],
        "feature_contributions": [
            {
                "cluster_name": "Trend",
                "contribution_score": 0.8,
                "impact_level": "High",
                "summary": "Strong trend",
            }
        ],
        "risk_assessment": {
            "passed": True,
            "risk_reward_ratio": 2.5,
            "drawdown_impact_pct": 0.05,
            "summary": "Risk acceptable",
        },
        "regime_context": {
            "regime_name": "Trending",
            "confidence": 0.9,
            "volatility_state": "Normal",
            "is_favorable": True,
            "summary": "Favorable trend",
        },
        "human_readable_summary": "Buy signal due to trend.",
        "machine_attribution": {"conf": 0.85},
    }

    explanation = SignalExplanation(**data)
    assert explanation.symbol == "XAUUSD"
    assert explanation.direction == SignalDirection.BUY
    assert explanation.execution_summary.passed is True
    assert len(explanation.model_attributions) == 1
    assert explanation.model_attributions[0].is_dominant is True


def test_signal_explainer_aggregation():
    """Test that SignalExplainer correctly aggregates data from various sources."""
    explainer = SignalExplainer()

    symbol = "XAUUSD"
    direction = 1
    confidence = 0.75
    model_votes = {"ppo": 1, "lstm": 1}  # 1=buy in ModelAction mapping
    model_weights = {"ppo": 0.7, "lstm": 0.3}
    risk_data = {
        "passed": True,
        "risk_reward": 2.1,
        "drawdown_impact": 0.02,
        "kelly_fraction": 0.1,
        "summary": "Risk clear",
    }
    regime_info = {
        "name": "Trending",
        "confidence": 0.88,
        "volatility": "Normal",
        "is_favorable": True,
        "summary": "Strong momentum",
    }
    execution_data = {
        "passed": True,
        "filters": [{"name": "Spread", "passed": True, "value": 0.2, "threshold": 1.0}],
        "summary": "Spread tight",
    }

    explanation = explainer.explain(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        model_votes=model_votes,
        model_weights=model_weights,
        risk_data=risk_data,
        regime_info=regime_info,
        execution_data=execution_data,
    )

    assert explanation.symbol == symbol
    assert explanation.direction == SignalDirection.BUY
    assert explanation.total_confidence == confidence
    assert explanation.execution_summary.passed is True
    assert len(explanation.model_attributions) == 2

    # Check dominant model (ppo has higher weight)
    ppo_attr = next(a for a in explanation.model_attributions if a.model_name == "ppo")
    assert ppo_attr.is_dominant is True

    assert explanation.risk_assessment.passed is True
    assert explanation.regime_context.regime_name == "Trending"
    assert "Ensemble generated a BUY signal" in explanation.human_readable_summary


def test_signal_explainer_execution_blocked():
    """Test explanation generation for a signal blocked by execution filters."""
    explainer = SignalExplainer()

    execution_data = {
        "passed": False,
        "filters": [{"name": "Spread", "passed": False, "value": 3.0, "threshold": 2.0}],
        "summary": "High spread",
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},  # 1=buy
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "risk_reward": 2.0, "summary": "Risk OK"},
        regime_info={"name": "Bullish"},
        execution_data=execution_data,
    )

    assert explanation.execution_summary.passed is False
    assert "EXECUTION BLOCKED: High spread" in explanation.human_readable_summary


def test_signal_explainer_risk_rejection():
    """Test explanation generation for a signal rejected by risk filters."""
    explainer = SignalExplainer()

    risk_data = {
        "passed": False,
        "rejection_reasons": ["Daily loss limit reached"],
        "risk_reward": 1.2,
        "drawdown_impact": 0.0,
        "summary": "Rejected by risk manager",
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.6,
        model_votes={"ppo": 2},  # 2=sell
        model_weights={"ppo": 1.0},
        risk_data=risk_data,
        regime_info={"name": "Volatile"},
    )

    assert explanation.direction == SignalDirection.SELL
    assert explanation.risk_assessment.passed is False
    assert "Daily loss limit reached" in explanation.risk_assessment.rejection_reasons
    assert "Risk REJECTED" in explanation.human_readable_summary


def test_format_for_terminal_fallback():
    """Test terminal formatting (plain text fallback if rich is not used or available)."""
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_votes={"ppo": 1},  # 1=buy
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "risk_reward": 3.0, "summary": "Ok"},
        regime_info={"name": "Bullish"},
        execution_data={
            "passed": True,
            "filters": [{"name": "Spread", "passed": True, "value": 0.5}],
            "summary": "OK",
        },
    )

    formatted = explainer.format_for_terminal(explanation)
    # Check for presence of key info regardless of formatting (rich vs plain)
    assert "XAUUSD" in formatted
    assert "BUY" in formatted
    assert "ppo" in formatted
    assert "Execution" in formatted or "EXECUTION" in formatted.upper()
    assert "Risk Assessment" in formatted or "RISK" in formatted.upper()


def test_signal_explainer_dominant_tie():
    """Test that multiple models are marked as dominant if they have the same weighted confidence."""
    explainer = SignalExplainer()

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1, "lstm": 1},
        model_weights={"ppo": 0.5, "lstm": 0.5},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
    )

    dominant_models = [a.model_name for a in explanation.model_attributions if a.is_dominant]
    assert "ppo" in dominant_models
    assert "lstm" in dominant_models
    assert "Primary driver(s): ppo, lstm" in explanation.human_readable_summary


def test_signal_explainer_no_risk_data():
    """Test that SignalExplainer handles missing risk data with defaults."""
    explainer = SignalExplainer()

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=0,  # HOLD
        confidence=0.5,
        model_votes={"ppo": 0},  # 0=HOLD
        model_weights={"ppo": 1.0},
        risk_data={},  # Empty risk data
        regime_info={},  # Empty regime info
    )

    assert explanation.risk_assessment.passed is False
    assert explanation.risk_assessment.summary == "No risk data provided"
    assert explanation.regime_context.regime_name == "Unknown"
    assert explanation.regime_context.volatility_state == "Normal"


def test_signal_explainer_feature_contributions():
    """Test that feature contributions are correctly processed."""
    explainer = SignalExplainer()
    feature_impacts = [
        {"cluster": "Trend", "score": 0.8, "impact": "High", "summary": "Strong bullish trend"},
        {"cluster": "Volatility", "score": -0.2, "impact": "Low", "summary": "Slightly elevated"},
    ]

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.7,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        feature_impacts=feature_impacts,
    )

    assert len(explanation.feature_contributions) == 2
    trend = next(c for c in explanation.feature_contributions if c.cluster_name == "Trend")
    assert trend.contribution_score == 0.8
    assert trend.impact_level == "High"

    # Check that high impact feature is in summary (now via Strategic Confluence)
    assert (
        "Strategic Confluence: High alignment from Trend (+0.80)"
        in explanation.human_readable_summary
    )

    # Check machine attribution for features
    assert "feature_impacts" in explanation.machine_attribution
    assert explanation.machine_attribution["feature_impacts"]["Trend"] == 0.8


def test_signal_explainer_feature_clustering():
    """Test that individual feature impacts are automatically clustered."""
    explainer = SignalExplainer()
    feature_impacts = {
        "base_M5_rsi": 0.8,
        "base_M5_macd": 0.6,
        "base_M5_slope": 0.7,
        "base_M5_atr": 0.1,
        "unknown_feature": 0.5,
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        feature_impacts=feature_impacts,
    )

    clusters = [c.cluster_name for c in explanation.feature_contributions]
    assert "Momentum" in clusters  # rsi, macd
    assert "Trend" in clusters  # slope
    assert "Volatility" in clusters  # atr
    assert "Other" in clusters  # unknown_feature

    momentum = next(c for c in explanation.feature_contributions if c.cluster_name == "Momentum")
    assert momentum.contribution_score == 0.7  # (0.8 + 0.6) / 2
    assert momentum.impact_level == "High"


def test_signal_explainer_new_keywords_categorization():
    """Test that newly added institutional feature keywords are correctly categorized."""
    explainer = SignalExplainer()
    feature_impacts = {
        "base_M5_ht_trendline": 0.5,
        "base_M5_log_returns": 0.6,
        "base_M5_dist_ema_21": 0.4,
        "base_M5_body_size": 0.3,
        "base_M5_rvol": 0.7,
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        feature_impacts=feature_impacts,
    )

    clusters = {c.cluster_name: c for c in explanation.feature_contributions}

    assert "Trend" in clusters
    assert "Momentum" in clusters
    assert "Volatility" in clusters
    assert "Volume" in clusters

    # Verification of specific mappings
    # log_returns and dist_ema are Momentum
    momentum_score = (0.6 + 0.4) / 2
    assert clusters["Momentum"].contribution_score == momentum_score

    # ht_ is Trend
    assert clusters["Trend"].contribution_score == 0.5

    # body_size is Volatility
    assert clusters["Volatility"].contribution_score == 0.3

    # rvol is Volume
    assert clusters["Volume"].contribution_score == 0.7


def test_signal_explainer_structured_inputs():
    """Test explain with RegimeInfo and ExecutionDecision objects."""
    explainer = SignalExplainer()

    regime = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.95,
        transition_score=0.1,
        volatility_index=1.1,
    )

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.9,
    )

    execution = ExecutionDecision(
        signal=signal,
        confidence_score=0.9,
        blocked_by="ATR_VOLATILITY",
        trace={
            "atr_volatility": {"passed": False, "ratio": 3.5, "threshold": 3.0},
            "momentum": {"passed": True, "rsi": 65},
        },
    )

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info=regime,
        execution_data=execution,
    )

    assert explanation.regime_context.regime_name == "Trending"
    assert explanation.regime_context.confidence == 0.95
    assert explanation.execution_summary.passed is False
    assert "Blocked by ATR_VOLATILITY" in explanation.execution_summary.summary

    # Check filter trace mapping
    atr_filter = next(
        f for f in explanation.execution_summary.filters if f.filter_name == "atr_volatility"
    )
    assert atr_filter.passed is False
    assert atr_filter.value == 3.5
    assert atr_filter.threshold == 3.0


def test_signal_explainer_with_individual_confidences():
    """Test that SignalExplainer respects individual model confidences."""
    explainer = SignalExplainer()
    model_confidences = {"ppo": 0.95, "lstm": 0.4}

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.7,
        model_votes={"ppo": 1, "lstm": 1},
        model_weights={"ppo": 0.5, "lstm": 0.5},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        model_confidences=model_confidences,
    )

    ppo_attr = next(a for a in explanation.model_attributions if a.model_name == "ppo")
    lstm_attr = next(a for a in explanation.model_attributions if a.model_name == "lstm")

    assert ppo_attr.confidence == 0.95
    assert lstm_attr.confidence == 0.4
    assert ppo_attr.is_dominant is True
    assert lstm_attr.is_dominant is False


def test_signal_explainer_expanded_machine_attribution():
    """Test that expanded machine attribution fields are present."""
    explainer = SignalExplainer()
    risk_data = {
        "passed": False,
        "rejection_reasons": ["Risk limit exceeded"],
        "risk_reward": 1.5,
    }
    execution_data = {
        "passed": False,
        "filters": [{"name": "Spread", "passed": False, "value": 5.0, "threshold": 1.0}],
        "summary": "High spread",
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data=risk_data,
        regime_info={"name": "Trending"},
        execution_data=execution_data,
    )

    attr = explanation.machine_attribution
    assert attr["risk_passed"] is False
    assert attr["risk_reward_ratio"] == 1.5
    assert "Risk limit exceeded" in attr["risk_rejection_reasons"]
    assert attr["execution_passed"] is False
    assert "Spread" in attr["failed_execution_filters"]


def test_format_for_terminal_with_features():
    """Test that terminal formatting includes feature contributions."""
    explainer = SignalExplainer()
    feature_impacts = [
        {"cluster": "Trend", "score": 0.8, "impact": "High", "summary": "Strong bullish trend"},
    ]

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.7,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        feature_impacts=feature_impacts,
    )

    formatted = explainer.format_for_terminal(explanation)
    assert "Feature Cluster Contributions" in formatted or "Feature Contributions" in formatted
    assert "Trend" in formatted
    assert "Strong bullish trend" in formatted


def test_signal_explainer_mixed_votes():
    """Test behavior when models have conflicting votes."""
    explainer = SignalExplainer()

    # PPO votes BUY (1), LSTM votes SELL (2)
    # Ensemble confidence 0.6, final direction BUY (1)
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.6,
        model_votes={"ppo": 1, "lstm": 2},
        model_weights={"ppo": 0.6, "lstm": 0.4},
        risk_data={"passed": True},
        regime_info={"name": "Volatile"},
    )

    ppo_attr = next(a for a in explanation.model_attributions if a.model_name == "ppo")
    lstm_attr = next(a for a in explanation.model_attributions if a.model_name == "lstm")

    assert ppo_attr.vote == SignalDirection.BUY
    assert lstm_attr.vote == SignalDirection.SELL
    # ppo aligned with final direction, so it should have the confidence
    assert ppo_attr.confidence == 0.6
    # lstm not aligned, should have neutral 0.5
    assert lstm_attr.confidence == 0.5
    assert ppo_attr.is_dominant is True
    assert lstm_attr.is_dominant is False


def test_signal_explainer_with_signal_id():
    """Test that SignalExplainer correctly handles and passes through signal_id."""
    explainer = SignalExplainer()
    signal_id = 12345

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        signal_id=signal_id,
    )

    assert explanation.signal_id == signal_id


def test_signal_explainer_summary_regime_favorability():
    """Test that the summary explicitly mentions market favorability."""
    explainer = SignalExplainer()

    # Case 1: Favorable Regime
    exp_favorable = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending", "is_favorable": True},
    )
    assert (
        "Market state is considered favorable for this strategy"
        in exp_favorable.human_readable_summary
    )

    # Case 2: Unfavorable Regime
    exp_unfavorable = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.6,
        model_votes={"ppo": 2},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Volatile", "is_favorable": False},
    )
    assert (
        "Market state is UNFAVORABLE/CAUTIONARY for this strategy"
        in exp_unfavorable.human_readable_summary
    )


def test_human_readable_summary_confluence():
    """Test that the summary correctly identifies supporting and opposing factors."""
    explainer = SignalExplainer()
    feature_impacts = {
        "rsi": 0.8,  # Supporting BUY
        "atr": -0.3,  # Opposing BUY
        "volume": 0.5,  # Supporting BUY
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,  # BUY
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        feature_impacts=feature_impacts,
    )

    summary = explanation.human_readable_summary
    assert "Strategic Confluence: High alignment from" in summary
    assert "Momentum (+0.80)" in summary
    assert "Volume (+0.50)" in summary
    assert "Opposed by:" in summary
    assert "Volatility (-0.30)" in summary


def test_explain_malformed_inputs():
    """Ensure the system doesn't crash when receiving unexpected or partial data structures."""
    explainer = SignalExplainer()

    # Test with None or empty values where dicts/lists are expected
    explanation = explainer.explain(
        symbol="",  # Should fallback to XAUUSD
        direction=1,
        confidence=0.5,
        model_votes=None,
        model_weights={},
        risk_data=None,
        regime_info=None,
        execution_data="not a dict",
        feature_impacts="not a list",
    )

    assert explanation.symbol == "XAUUSD"
    assert explanation.execution_summary.passed is False
    assert "Malformed execution data detected" in explanation.execution_summary.summary
    assert explanation.regime_context.regime_name == "Unknown"
    assert explanation.risk_assessment.passed is False
    assert len(explanation.model_attributions) == 0


def test_explain_invalid_model_votes():
    """Test robustness against invalid model vote indices."""
    explainer = SignalExplainer()

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": "invalid", "lstm": 999},
        model_weights={"ppo": 0.5, "lstm": 0.5},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
    )

    # Invalid votes should fallback to HOLD (0)
    for attr in explanation.model_attributions:
        assert attr.vote == SignalDirection.HOLD


def test_terminal_formatting_icons_and_markers():
    """Test that terminal formatting includes new directional icons and density markers."""
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        model_votes={"ppo": 1, "lstm": 2},  # PPO: BUY, LSTM: SELL
        model_weights={"ppo": 0.6, "lstm": 0.4},
        risk_data={"passed": True, "risk_reward": 2.5},
        regime_info={"name": "Trending"},
        feature_impacts=[
            {"cluster": "Trend", "score": 0.8, "impact": "High", "summary": "Strong trend"},
            {"cluster": "Volatility", "score": -0.4, "impact": "Medium", "summary": "Elevated"},
        ],
    )

    formatted = explainer.format_for_terminal(explanation)

    # Check for directional icons in model votes and features
    # Use separate checks to be robust against ANSI escape codes
    assert "📈" in formatted
    assert "📉" in formatted
    assert "BUY" in formatted
    assert "SELL" in formatted
    assert "+0.80" in formatted
    assert "-0.40" in formatted

    # Check for impact density markers
    assert "●●●" in formatted
    assert "●●○" in formatted
    assert "High" in formatted
    assert "Medium" in formatted


def test_strategic_confluence_summary():
    """Verify the accuracy and depth of the generated natural language summaries."""
    explainer = SignalExplainer()

    # Case 1: Trending Regime
    exp_trending = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending", "is_favorable": True},
        feature_impacts={"rsi": 0.8},
    )
    summary = exp_trending.human_readable_summary
    assert "Trending regimes provide high-velocity environments" in summary
    assert "Strategic Confluence: High alignment from Momentum (+0.80)" in summary

    # Case 2: Ranging Regime
    exp_ranging = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.75,
        model_votes={"ppo": 2},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Ranging", "is_favorable": True},
        feature_impacts={"slope": -0.6},
    )
    assert (
        "Mean-reversion setups are prioritized in ranging regimes"
        in exp_ranging.human_readable_summary
    )
    assert (
        "Strategic Confluence: High alignment from Trend (-0.60)"
        in exp_ranging.human_readable_summary
    )


def test_advanced_metrics_calculation():
    """Ensure dominance_ratio and regime_alignment_score are correctly derived."""
    explainer = SignalExplainer()

    # Setup ensemble with different confidences
    model_votes = {"ppo": 1, "lstm": 1}
    model_weights = {"ppo": 0.7, "lstm": 0.3}
    model_confidences = {"ppo": 0.9, "lstm": 0.7}

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes=model_votes,
        model_weights=model_weights,
        risk_data={"passed": True},
        regime_info={"name": "Trending", "confidence": 0.95, "alignment_score": 0.9},
        model_confidences=model_confidences,
    )

    ppo_attr = next(a for a in explanation.model_attributions if a.model_name == "ppo")
    lstm_attr = next(a for a in explanation.model_attributions if a.model_name == "lstm")

    # Weighted confidences:
    # ppo: 0.7 * 0.9 = 0.63
    # lstm: 0.3 * 0.7 = 0.21
    # total: 0.84
    # ppo ratio: 0.63 / 0.84 = 0.75
    # lstm ratio: 0.21 / 0.84 = 0.25

    assert abs(ppo_attr.dominance_ratio - 0.75) < 1e-6
    assert abs(lstm_attr.dominance_ratio - 0.25) < 1e-6
    assert explanation.regime_context.regime_alignment_score == 0.9

    # Check machine attribution
    attr = explanation.machine_attribution
    assert attr["model_dominance_ratios"]["ppo"] == ppo_attr.dominance_ratio
    assert attr["regime_alignment_score"] == 0.9


def test_to_report_section_integration():
    """Test the to_report_section method for ResearchReport integration."""
    explainer = SignalExplainer()

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={
            "name": "Trending",
            "alignment_score": 0.8,
            "session_alignment": 0.7,
            "volatility_alignment": 0.6,
        },
    )

    from src.research.reporting import StrategicConfluenceSection
    section = StrategicConfluenceSection.from_explanation(explanation)

    # Verify section type
    assert isinstance(section, StrategicConfluenceSection)

    # Verify scores
    assert section.regime_alignment == 0.8
    assert section.session_alignment == 0.7
    assert section.volatility_alignment == 0.6

    # Weighted score logic:
    # 40% Model Confidence (0.8 * 0.4 = 0.32)
    # 30% Regime Alignment (0.8 * 0.3 = 0.24)
    # 15% Session Alignment (0.7 * 0.15 = 0.105)
    # 15% Volatility Alignment (0.6 * 0.15 = 0.09)
    # Total: 0.32 + 0.24 + 0.105 + 0.09 = 0.755
    assert abs(section.confluence_score - 0.755) < 1e-6
    assert section.insights == explanation.human_readable_summary


def test_explain_with_alignment_overrides():
    """Test that SignalExplainer respects session and volatility alignment overrides."""
    explainer = SignalExplainer()

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True},
        regime_info={"name": "Trending"},
        session_alignment=0.9,
        volatility_alignment=0.1,
    )

    assert explanation.regime_context.session_alignment == 0.9
    assert explanation.regime_context.volatility_alignment == 0.1
