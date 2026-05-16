"""
Tests for system-wide product coherence and architectural standards.
Ensures that core types and enums are centralized and consistently used.
"""

from src.core.constants import DecisionStatus, EventCategory, EventImpact, SignalDirection


def test_enum_centralization():
    """Verify that core enums are correctly exported from constants."""
    assert SignalDirection.BUY == 1
    assert SignalDirection.SELL == -1
    assert SignalDirection.HOLD == 0

    assert DecisionStatus.EXECUTE == "execute"
    assert DecisionStatus.BLOCKED == "blocked"

    assert EventImpact.CRITICAL == 4
    assert EventCategory.FOMC.value == "FOMC"


def test_schema_import_coherence():
    """Verify that schemas.py uses the centralized SignalDirection."""
    from src.core.schemas import TradeSignal

    # If this imports without error and TradeSignal uses the enum, we are coherent
    assert TradeSignal.model_fields["direction"].annotation == SignalDirection


def test_explainability_import_coherence():
    """Verify that explainability.py uses the centralized SignalDirection."""
    from src.core.explainability import ModelAttribution

    assert ModelAttribution.model_fields["vote"].annotation == SignalDirection


def test_decision_support_import_coherence():
    """Verify that decision_support.py uses the centralized types."""
    from src.core.decision_support import DecisionPacket

    assert DecisionPacket.model_fields["direction"].annotation == SignalDirection
    assert DecisionPacket.model_fields["status_level"].annotation == DecisionStatus


def test_event_intelligence_import_coherence():
    """Verify that event_intelligence.py uses the centralized enums."""
    from src.data.event_intelligence import MacroEvent

    assert MacroEvent.model_fields["impact"].annotation == EventImpact
    assert MacroEvent.model_fields["category"].annotation == EventCategory


def test_model_interface_polymorphism():
    """Verify that all core models follow the polymorphic predict signature."""
    import inspect

    from src.models.dreamer_agent import DreamerAgent
    from src.models.ensemble import EnsembleModel
    from src.models.lstm_model import LSTMModel
    from src.models.ppo_agent import PPOAgent
    from src.models.transformer_model import TimeSeriesTransformer

    models = [PPOAgent, LSTMModel, TimeSeriesTransformer, DreamerAgent, EnsembleModel]

    for model_cls in models:
        sig = inspect.signature(model_cls.predict)
        assert "kwargs" in sig.parameters, f"{model_cls.__name__}.predict missing **kwargs"
