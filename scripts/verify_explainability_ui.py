import os
import sys

from rich.console import Console

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.explainability import SignalExplainer
from src.core.schemas import ExecutionDecision, TradeSignal
from src.models.regime_detector import MarketRegime, RegimeInfo


def verify_ui():
    console = Console(force_terminal=True, width=100)
    explainer = SignalExplainer()

    print("\n" + "=" * 80)
    print("SCENARIO 1: HIGH-CONFIDENCE APPROVED BUY SIGNAL")
    print("=" * 80)

    regime = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.92,
        transition_score=0.05,
        volatility_index=1.1,
    )

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.88,
    )

    feature_impacts = {
        "base_M5_rsi": 0.85,
        "base_M5_slope_20": 0.75,
        "base_M5_atr": 0.2,
        "base_M5_rvol": 0.6,
        "pattern_hammer": 0.9,
    }

    risk_data = {
        "passed": True,
        "risk_reward": 2.8,
        "drawdown_impact": 0.02,
        "kelly_fraction": 0.15,
        "summary": "Risk profile aligned with institutional standards.",
    }

    execution_data = ExecutionDecision(
        signal=signal,
        is_approved=True,
        confidence_score=0.88,
        trace={
            "spread": {"passed": True, "value": 0.3, "threshold": 1.0},
            "momentum": {"passed": True, "rsi": 62},
            "trend": {"passed": True, "slope": 0.4},
        },
    )

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.88,
        model_votes={"PPO": 1, "LSTM": 1, "Transformer": 1},
        model_weights={"PPO": 0.4, "LSTM": 0.3, "Transformer": 0.3},
        risk_data=risk_data,
        regime_info=regime,
        execution_data=execution_data,
        feature_impacts=feature_impacts,
        signal_id=888,
    )

    explainer.format_for_terminal(explanation, console=console)

    print("\n" + "=" * 80)
    print("SCENARIO 2: BLOCKED SIGNAL (EXECUTION FILTER)")
    print("=" * 80)

    execution_data_blocked = ExecutionDecision(
        signal=signal,
        is_approved=False,
        confidence_score=0.75,
        blocked_by="ATR_VOLATILITY",
        trace={
            "atr_volatility": {"passed": False, "ratio": 3.5, "threshold": 3.0},
            "spread": {"passed": True, "value": 0.5},
        },
    )

    explanation_blocked = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.75,
        model_votes={"PPO": 2, "LSTM": 0},
        model_weights={"PPO": 0.7, "LSTM": 0.3},
        risk_data={"passed": True, "summary": "Risk OK"},
        regime_info={"name": "News Shock", "volatility": "Extreme", "is_favorable": False},
        execution_data=execution_data_blocked,
    )

    explainer.format_for_terminal(explanation_blocked, console=console)


if __name__ == "__main__":
    verify_ui()
