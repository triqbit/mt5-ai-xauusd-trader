import unittest
from unittest.mock import MagicMock

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime, RegimeInfo


class TestJulesEnsembleSafetyV2(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.model_drift_threshold = 0.3
        self.config.consensus_threshold = 0.60

        self.ensemble = EnsembleModel(config=self.config, consensus_threshold=0.60)
        # Mock sub-agents
        self.ensemble.ppo_agent = MagicMock()
        self.ensemble.dreamer_agent = MagicMock()
        self.ensemble.lstm_model = MagicMock()

    def test_veto_power_active(self):
        """Verify that a weak contributing model triggers a Veto HOLD."""
        # Weighted consensus would be high, but one model is weak
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 0.5, "dreamer": 0.5, "lstm": 0.0
        })

        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.35), # Weak!
        }

        result = self.ensemble.aggregate_signals(signals)

        # Weighted BUY conf = 0.9*0.5 + 0.35*0.5 = 0.45 + 0.175 = 0.625
        # 0.625 > 0.60 threshold, but Dreamer has 0.35 confidence < 0.40 veto floor.
        self.assertEqual(result.direction, SignalDirection.HOLD)
        self.assertTrue(result.metadata.get("veto_active"))
        self.assertEqual(result.metadata.get("veto_model"), "dreamer")

    def test_regime_adaptive_consensus_high(self):
        """Verify that NEWS_SHOCK raises the consensus threshold to 80%."""
        # Weighted consensus = 0.70 (usually enough, but not for NEWS_SHOCK)
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 1.0, "dreamer": 0.0, "lstm": 0.0
        })

        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.70),
        }

        # 1. Normal regime (threshold 0.60)
        normal_regime = RegimeInfo(
            label=MarketRegime.RANGING, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )
        result_normal = self.ensemble.aggregate_signals(signals, regime_info=normal_regime)
        self.assertEqual(result_normal.direction, SignalDirection.BUY)

        # 2. News Shock regime (threshold 0.80)
        news_regime = RegimeInfo(
            label=MarketRegime.NEWS_SHOCK, confidence=1.0, transition_score=0.0, volatility_index=5.0
        )
        result_news = self.ensemble.aggregate_signals(signals, regime_info=news_regime)
        self.assertEqual(result_news.direction, SignalDirection.HOLD)
        self.assertEqual(result_news.metadata.get("dynamic_threshold"), 0.80)

    def test_transition_aware_threshold_increase(self):
        """Verify that high transition score increases threshold by 10%."""
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 1.0, "dreamer": 0.0, "lstm": 0.0
        })

        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.65),
        }

        # Transition score 0.8 (> 0.7 trigger)
        # Threshold 0.60 -> 0.70
        transition_regime = RegimeInfo(
            label=MarketRegime.RANGING, confidence=1.0, transition_score=0.8, volatility_index=1.0
        )
        result = self.ensemble.aggregate_signals(signals, regime_info=transition_regime)

        self.assertEqual(result.direction, SignalDirection.HOLD)
        self.assertEqual(result.metadata.get("dynamic_threshold"), 0.70)

    def test_cumulative_threshold_hardening(self):
        """Verify that regime and transition hardening are cumulative."""
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 1.0, "dreamer": 0.0, "lstm": 0.0
        })

        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.85),
        }

        # News Shock (0.80) + Transition (0.10) = 0.90
        danger_regime = RegimeInfo(
            label=MarketRegime.NEWS_SHOCK, confidence=1.0, transition_score=0.9, volatility_index=5.0
        )
        result = self.ensemble.aggregate_signals(signals, regime_info=danger_regime)

        self.assertEqual(result.direction, SignalDirection.HOLD)
        self.assertEqual(result.metadata.get("dynamic_threshold"), 0.90)

    def test_dissent_check_preserved(self):
        """Ensure core BUY/SELL dissent check still works."""
        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "dreamer": Signal(direction=SignalDirection.SELL, confidence=0.9),
        }

        result = self.ensemble.aggregate_signals(signals)
        self.assertEqual(result.direction, SignalDirection.HOLD)
        self.assertEqual(result.metadata.get("reason"), "Dissent conflict")

if __name__ == "__main__":
    unittest.main()
