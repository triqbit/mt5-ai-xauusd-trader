import unittest

from src.core.explainability import (
    SignalDirection,
    SignalExplainer,
    SignalExplanation,
)


class TestSignalExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = SignalExplainer()
        # ModelAction: HOLD=0, BUY=1, SELL=2
        self.sample_votes = {"ModelA": 1, "ModelB": 1, "ModelC": 2}
        self.sample_weights = {"ModelA": 0.5, "ModelB": 0.3, "ModelC": 0.2}
        self.sample_risk = {
            "passed": True,
            "risk_reward": 2.1,
            "kelly_fraction": 0.05,
            "summary": "Risk profile acceptable",
        }
        self.sample_regime = {
            "name": "Trending",
            "confidence": 0.8,
            "volatility": "Normal",
            "is_favorable": True,
            "alignment_score": 0.9,
        }

    def test_basic_explanation_generation(self):
        """Test that a basic explanation object is correctly constructed."""
        explanation = self.explainer.explain(
            symbol="XAUUSD",
            direction=1,
            confidence=0.75,
            model_votes=self.sample_votes,
            model_weights=self.sample_weights,
            risk_data=self.sample_risk,
            regime_info=self.sample_regime,
        )

        self.assertIsInstance(explanation, SignalExplanation)
        self.assertEqual(explanation.symbol, "XAUUSD")
        self.assertEqual(explanation.direction, SignalDirection.BUY)
        self.assertEqual(explanation.total_confidence, 0.75)
        self.assertTrue(explanation.risk_assessment.passed)
        self.assertEqual(explanation.regime_context.regime_name, "Trending")

    def test_model_dominance(self):
        """Test that the dominant model is correctly identified."""
        # ModelA has 0.5 weight and voted Buy (1), so it should be dominant for a Buy signal
        explanation = self.explainer.explain(
            symbol="XAUUSD",
            direction=1,
            confidence=0.75,
            model_votes=self.sample_votes,
            model_weights=self.sample_weights,
            risk_data=self.sample_risk,
            regime_info=self.sample_regime,
        )

        dominant_models = [m.model_name for m in explanation.model_attributions if m.is_dominant]
        self.assertIn("ModelA", dominant_models)
        self.assertEqual(len(dominant_models), 1)

    def test_feature_clustering_and_top_drivers(self):
        """Test that individual features are correctly clustered and top drivers identified."""
        feature_impacts = {
            "rsi_14": 0.8,
            "mfi_14": 0.6,
            "ema_slope": 0.4,
            "atr_ratio": 0.1,
            "efficiency_ratio": 0.9,  # This should be a top driver for Momentum
            "z_score": 0.7,
        }

        explanation = self.explainer.explain(
            symbol="XAUUSD",
            direction=1,
            confidence=0.75,
            model_votes=self.sample_votes,
            model_weights=self.sample_weights,
            risk_data=self.sample_risk,
            regime_info=self.sample_regime,
            feature_impacts=feature_impacts,
        )

        # Momentum cluster should contain rsi, mfi, efficiency_ratio, z_score
        momentum_contrib = next(
            c for c in explanation.feature_contributions if c.cluster_name == "Momentum"
        )
        self.assertEqual(momentum_contrib.impact_level, "High")
        self.assertIn("efficiency_ratio (+0.90)", momentum_contrib.summary)
        self.assertIn("rsi_14 (+0.80)", momentum_contrib.summary)
        self.assertIn("z_score (+0.70)", momentum_contrib.summary)

    def test_strategic_reasoning_regimes(self):
        """Test that different regimes produce appropriate strategic reasoning."""
        regimes = [
            ("Trending", "Trending regimes provide high-velocity environments"),
            ("Ranging", "Mean-reversion setups are prioritized"),
            ("Volatile_Breakout", "Breakout regimes signal high-momentum expansions"),
            ("Mean_Reversion", "Overextended price states indicate corrective snap-back"),
        ]

        for regime_name, expected_text in regimes:
            regime_data = self.sample_regime.copy()
            regime_data["name"] = regime_name

            explanation = self.explainer.explain(
                symbol="XAUUSD",
                direction=1,
                confidence=0.75,
                model_votes=self.sample_votes,
                model_weights=self.sample_weights,
                risk_data=self.sample_risk,
                regime_info=regime_data,
            )

            self.assertIn(expected_text, explanation.human_readable_summary)

    def test_confluence_score_calculation(self):
        """Test the weighted confluence score calculation."""
        explanation = self.explainer.explain(
            symbol="XAUUSD",
            direction=1,
            confidence=0.8,
            model_votes=self.sample_votes,
            model_weights=self.sample_weights,
            risk_data=self.sample_risk,
            regime_info=self.sample_regime,
            session_alignment=0.7,
            volatility_alignment=0.6,
        )

        # 40% * 0.8 (Conf) + 30% * 0.9 (Regime Align) + 15% * 0.7 (Session) + 15% * 0.6 (Vol)
        # 0.32 + 0.27 + 0.105 + 0.09 = 0.785
        expected_score = (0.8 * 0.4) + (0.9 * 0.3) + (0.7 * 0.15) + (0.6 * 0.15)
        self.assertAlmostEqual(explanation.get_confluence_score(), expected_score)

    def test_malformed_input_handling(self):
        """Test that the explainer handles malformed or missing inputs gracefully."""
        # Test with None execution data
        explanation = self.explainer.explain(
            symbol="XAUUSD",
            direction=1,
            confidence=0.5,
            model_votes={},
            model_weights={},
            risk_data={},
            regime_info=None,
        )

        self.assertEqual(explanation.regime_context.regime_name, "Unknown")
        self.assertTrue(explanation.execution_summary.passed)
        self.assertEqual(explanation.human_readable_summary.count("Ensemble generated a"), 1)


if __name__ == "__main__":
    unittest.main()
