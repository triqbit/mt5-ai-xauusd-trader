import os
import sys

# Ensure the root directory is in the path
sys.path.append(os.getcwd())

from src.core.constants import SignalDirection
from src.core.decision_support import (
    DecisionSupportSystem,
)
from src.core.explainability import (
    ExecutionSummary,
    FeatureContribution,
    FilterResult,
    ModelAttribution,
    RegimeContext,
    RiskAssessment,
    SignalExplanation,
)
from src.data.event_intelligence import RiskStatus
from src.models.regime_detector import MarketRegime, RegimeInfo


def create_mock_explanation(direction=SignalDirection.BUY):
    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=direction,
        total_confidence=0.85,
        execution_summary=ExecutionSummary(
            passed=True,
            summary="All filters passed",
            filters=[
                FilterResult(filter_name="Spread", passed=True, value=1.5, threshold=3.0),
                FilterResult(filter_name="Volatility", passed=True, value=0.5, threshold=1.0),
            ],
        ),
        model_attributions=[
            ModelAttribution(
                model_name="PPO", vote=direction, confidence=0.9, weight=0.6, is_dominant=True
            ),
            ModelAttribution(
                model_name="LSTM", vote=direction, confidence=0.8, weight=0.4, is_dominant=False
            ),
        ],
        feature_contributions=[
            FeatureContribution(
                cluster_name="Momentum",
                contribution_score=0.7 if direction == SignalDirection.BUY else -0.7,
                impact_level="High",
                summary="Strong momentum alignment",
            ),
            FeatureContribution(
                cluster_name="Volatility",
                contribution_score=0.2,
                impact_level="Low",
                summary="Low volatility environment",
            ),
            FeatureContribution(
                cluster_name="Trend",
                contribution_score=-0.3 if direction == SignalDirection.BUY else 0.3,
                impact_level="Medium",
                summary="Counter-trend pressure",
            ),
        ],
        risk_assessment=RiskAssessment(
            passed=True, risk_reward_ratio=2.5, kelly_fraction=0.03, summary="Risk approved"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Market trending upward",
        ),
        human_readable_summary="Ensemble generated a BUY signal with high confidence. Momentum is strong.",
        machine_attribution={},
    )
    return explanation


def verify_ux():
    dss = DecisionSupportSystem()

    regime = RegimeInfo(
        label=MarketRegime.TRENDING, confidence=0.92, transition_score=0.05, volatility_index=1.1
    )

    macro_risk = RiskStatus(
        is_blocked=False, risk_multiplier=1.0, active_events=[], reason="Market conditions stable"
    )

    perf_metrics = {
        "sharpe_ratio": 2.1,
        "profit_factor": 2.3,
        "recovery_factor": 3.5,
        "win_rate": 0.58,
        "win_loss_ratio": 1.9,
        "total_trades": 150,
    }

    print("\n" + "=" * 80)
    print("SCENARIO 1: HIGH CONVICTION BUY")
    print("=" * 80)
    explanation = create_mock_explanation(SignalDirection.BUY)
    packet = dss.assemble_packet("XAUUSD", explanation, regime, macro_risk, perf_metrics)
    print(dss.format_for_operator(packet))

    print("\n" + "=" * 80)
    print("SCENARIO 2: BLOCKED TRADE (MACRO)")
    print("=" * 80)
    macro_risk_blocked = RiskStatus(
        is_blocked=True, risk_multiplier=0.0, active_events=[], reason="Blocked by FOMC"
    )
    perf_metrics_low = {
        "sharpe_ratio": 0.8,
        "profit_factor": 1.1,
        "recovery_factor": 1.5,
        "win_rate": 0.42,
        "win_loss_ratio": 1.1,
        "total_trades": 50,
    }
    packet_blocked = dss.assemble_packet(
        "XAUUSD", explanation, regime, macro_risk_blocked, perf_metrics_low
    )
    print(dss.format_for_operator(packet_blocked))

    print("\n" + "=" * 80)
    print("SCENARIO 3: SELL SIGNAL (CONTRA-CONFLUENCE)")
    print("=" * 80)
    explanation_sell = create_mock_explanation(SignalDirection.SELL)
    packet_sell = dss.assemble_packet("XAUUSD", explanation_sell, regime, macro_risk, perf_metrics)
    print(dss.format_for_operator(packet_sell))


if __name__ == "__main__":
    verify_ux()
