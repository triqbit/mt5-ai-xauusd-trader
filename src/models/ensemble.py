"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining signals from multiple AI models:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Weighted confidence voting with model dissent checks and dynamic weight adaptation.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np

try:
    import torch
except ImportError:
    torch = None  # type: ignore

from src.core.constants import SignalDirection
from src.core.profiler import profile
from src.models.base_model import BaseModel, Signal

if TYPE_CHECKING:
    from src.core.config import TradingConfig
    from src.core.monitor import Monitor
from src.models.dreamer_agent import DreamerAgent
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.lstm_model import LSTMModel
from src.models.ppo_agent import PPOAgent
from src.models.regime_detector import MarketRegime, RegimeInfo

logger = logging.getLogger(__name__)


class EnsembleModel(BaseModel):
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.

    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    Implements institutional consensus (60%) and dissent checks (veto).
    Uses standardized model wrappers for all sub-algorithms.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(
        self,
        device: str = "cpu",
        consensus_threshold: float = 0.60,
        model_weights: Optional[Dict[str, float]] = None,
        config: Optional[TradingConfig] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        """
        Initialize the EnsembleModel.

        Args:
            device: Computing device ('cpu', 'cuda', etc.).
            consensus_threshold: Required weighted agreement (default 60%).
            model_weights: Initial weights for each algorithm.
            config: Optional trading configuration for risk thresholds.
            monitor: Optional monitor instance for telemetry.
        """
        super().__init__()
        self.device = device
        self.cfg = config
        self.monitor = monitor
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS, smoothing_factor=0.1, max_swing=0.05, min_weight=0.05
        )
        if model_weights:
            total = sum(model_weights.values())
            self.dynamic_ensemble.weights = {k: v / total for k, v in model_weights.items()}

        # Standardized model wrappers
        self.ppo_agent: Optional[PPOAgent] = None
        self.dreamer_agent: Optional[DreamerAgent] = None
        self.lstm_model: Optional[LSTMModel] = None

        self.consensus_threshold = consensus_threshold

        self._performance: Dict[str, deque[float]] = {k: deque(maxlen=200) for k in self.ALGORITHMS}
        self._last_confidences: Dict[str, deque[float]] = {
            k: deque(maxlen=200) for k in self.ALGORITHMS
        }
        self._latest_health_metrics: Dict[str, float] = {
            "accuracy": 1.0,
            "drift": 0.0,
            "calibration": 0.0,
        }

    def load_ppo(self, path: str | Path) -> None:
        """Load PPO model from path."""
        self.ppo_agent = PPOAgent(model_path=path, device=self.device)

    def load_lstm(self, path: str | Path) -> None:
        """Load LSTM model from path."""
        self.lstm_model = LSTMModel(model_path=path, device=self.device)

    def load_dreamer(self, path: str | Path) -> None:
        """Load Dreamer model from path."""
        self.dreamer_agent = DreamerAgent(model_path=path, device=self.device)

    @property
    def weights(self) -> Dict[str, float]:
        """Expose weights from dynamic_ensemble."""
        return self.dynamic_ensemble.get_weights()

    def get_health_metrics(self) -> Dict[str, float]:
        """
        Aggregate health metrics across the ensemble.
        Calculates weighted averages of accuracy, drift, and calibration.
        """
        weights = self.weights
        total_acc = 0.0
        total_drift = 0.0
        total_cal = 0.0

        for name in self.ALGORITHMS:
            m = self.dynamic_ensemble.calculate_metrics(name)
            w = weights.get(name, 0.0)
            total_acc += m.get("accuracy", 0.5) * w
            total_drift += m.get("drift_score", 0.0) * w
            total_cal += m.get("calibration_error", 0.0) * w

        return {
            "accuracy": total_acc,
            "drift": total_drift,
            "calibration": total_cal,
        }

    def observe_outcome(
        self,
        actual_direction: SignalDirection,
        regime_info: Optional[RegimeInfo] = None,
        volatility_context: Optional[float] = None,
    ) -> None:
        """
        Record market outcome and update dynamic weights.
        This enables autonomous drift monitoring and adaptive rebalancing.
        """
        for name in self.ALGORITHMS:
            self.dynamic_ensemble.record_outcome(name, actual_direction)

        # Update weights based on the new history
        self.dynamic_ensemble.update_weights(
            regime_info=regime_info, volatility_context=volatility_context
        )
        logger.info(
            "Ensemble outcome observed | actual=%s | new_weights=%s",
            actual_direction.name,
            self.weights,
        )

    def aggregate_signals(
        self,
        signals: Dict[str, Signal],
        symbol: str = "unknown",
        regime_info: Optional[RegimeInfo] = None,
    ) -> Signal:
        """
        Aggregates pre-calculated signals from sub-models using weighted consensus.

        Args:
            signals: Dictionary of algorithm names and their predicted Signal.
            symbol: Trading symbol identifier.
            regime_info: Optional market regime information for adaptive safety.

        Returns:
            Signal: The aggregated consensus signal.
        """
        if not signals:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        # 1. Dissent Check: Block if there are conflicting BUY and SELL signals
        has_buy = any(s.direction == SignalDirection.BUY for s in signals.values())
        has_sell = any(s.direction == SignalDirection.SELL for s in signals.values())

        if has_buy and has_sell:
            logger.warning("Dissent detected: BUY and SELL conflict. Returning HOLD.")
            if self.monitor:
                self.monitor.record_signal_funnel("ensemble", "dissent")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={
                    "reason": "Dissent conflict",
                    "per_algo_votes": {k: s.direction for k, s in signals.items()},
                },
            )

        # 2. Weighted Aggregation
        weighted_buy_conf = 0.0
        weighted_sell_conf = 0.0
        weighted_hold_conf = 0.0

        total_active_weight = sum(self.weights.get(k, 0.0) for k in signals)
        if total_active_weight <= 0:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        for name, sig in signals.items():
            norm_weight = self.weights.get(name, 0.0) / total_active_weight
            if sig.direction == SignalDirection.BUY:
                weighted_buy_conf += sig.confidence * norm_weight
            elif sig.direction == SignalDirection.SELL:
                weighted_sell_conf += sig.confidence * norm_weight
            else:
                weighted_hold_conf += sig.confidence * norm_weight

        metadata: Dict[str, Any] = {
            "symbol": symbol,
            "weighted_probs": {
                "BUY": weighted_buy_conf,
                "SELL": weighted_sell_conf,
                "HOLD": weighted_hold_conf,
            },
            "weights": self.weights,
            "per_algo_votes": {k: s.direction for k, s in signals.items()},
            "per_algo_signals": {k: s._asdict() for k, s in signals.items()},
        }

        # 3. Adaptive Consensus Threshold Determination
        # We increase the consensus requirement during unstable market regimes
        # to ensure stronger agreement before committing capital.
        dynamic_threshold = self.consensus_threshold

        if regime_info:
            # 3.1 Regime-Based Hardening
            if regime_info.label in (MarketRegime.NEWS_SHOCK, MarketRegime.VOLATILE_BREAKOUT):
                # Increase required consensus to 80% during news or breakouts
                dynamic_threshold = max(dynamic_threshold, 0.80)
                logger.info(
                    "Regime-adaptive safety active | symbol=%s | regime=%s | consensus_threshold raised to %.2f",
                    symbol,
                    regime_info.label.value,
                    dynamic_threshold,
                )

            # 3.2 Transition-Aware Hardening
            # If a regime shift is likely (high transition_score), we require 10% more agreement
            if regime_info.transition_score > 0.70:
                dynamic_threshold = min(0.95, dynamic_threshold + 0.10)
                logger.info(
                    "Transition-aware safety active | symbol=%s | score=%.2f | consensus_threshold raised to %.2f",
                    symbol,
                    regime_info.transition_score,
                    dynamic_threshold,
                )

        metadata["dynamic_threshold"] = dynamic_threshold

        # 4. Consensus Determination
        direction = SignalDirection.HOLD
        confidence = weighted_hold_conf

        if weighted_buy_conf >= dynamic_threshold:
            direction = SignalDirection.BUY
            confidence = weighted_buy_conf
        elif weighted_sell_conf >= dynamic_threshold:
            direction = SignalDirection.SELL
            confidence = weighted_sell_conf

        # 5. Veto Power Safety Logic
        # If any sub-model contributing to the winning direction has dangerously low confidence
        # (< 0.40), we force HOLD regardless of weighted consensus.
        # We only consider models that have a non-zero weight in the current ensemble.
        if direction != SignalDirection.HOLD:
            for name, sig in signals.items():
                if (
                    sig.direction == direction
                    and self.weights.get(name, 0.0) > 0
                    and sig.confidence < 0.40
                ):
                    logger.warning(
                        "Veto power active | symbol=%s | model=%s | confidence=%.2f | forcing HOLD",
                        symbol,
                        name,
                        sig.confidence,
                    )
                    metadata["veto_active"] = True
                    metadata["veto_model"] = name
                    if self.monitor:
                        self.monitor.record_signal_funnel("ensemble", "veto")
                    return Signal(
                        direction=SignalDirection.HOLD,
                        confidence=0.0,
                        metadata=metadata,
                    )

        if direction == SignalDirection.HOLD:
            if self.monitor:
                self.monitor.record_signal_funnel("ensemble", "hold")
            return Signal(direction=direction, confidence=confidence, metadata=metadata)

        # 6. Defensive Safeguards (Risk Control & Drift Monitoring)

        # 6.1 Drift-Aware Confidence Penalty
        # If aggregate drift is rising, we proactively reduce confidence to trigger safer sizing
        # or block trades before hard limits are hit.
        health = self.get_health_metrics()
        drift = health.get("drift", 0.0)
        # Using 50% of the threshold as the trigger for the defensive penalty
        drift_threshold = self.cfg.model_drift_threshold if self.cfg else 0.3
        penalty_trigger = drift_threshold * 0.5

        if drift > penalty_trigger:
            # Scale penalty from 0 to 20% reduction in confidence
            drift_excess = (drift - penalty_trigger) / penalty_trigger
            drift_penalty = min(0.20, 0.20 * drift_excess)
            old_conf = confidence
            confidence *= 1.0 - drift_penalty
            logger.warning(
                "Drift safeguard active | symbol=%s | drift=%.2f | confidence reduced: %.2f -> %.2f",
                metadata.get("symbol", "unknown"),
                drift,
                old_conf,
                confidence,
            )
            metadata["drift_penalty"] = drift_penalty

        # 6.2 Market Context Alignment Guard (Regime Stability Check)
        # Evaluates the quality of the market state before approving signals.
        if regime_info:
            # Calculate a unified context stability factor (0.0 to 1.0)
            # Factors: regime confidence, session alignment, volatility alignment, and transition stability.
            context_stability = float(
                np.mean(
                    [
                        regime_info.confidence,
                        regime_info.session_alignment,
                        regime_info.volatility_alignment,
                        (1.0 - regime_info.transition_score),
                    ]
                )
            )
            metadata["market_context_stability"] = context_stability

            # 6.2.1 Critical Instability Check (Hard Block)
            if context_stability < 0.40:
                logger.warning(
                    "Market context instability active | symbol=%s | stability=%.2f | forcing HOLD",
                    symbol,
                    context_stability,
                )
                metadata["reason"] = "Critical market context instability"
                if self.monitor:
                    self.monitor.record_signal_funnel("ensemble", "hold")
                return Signal(
                    direction=SignalDirection.HOLD,
                    confidence=0.0,
                    metadata=metadata,
                )

            # 6.2.2 Graduated Alignment Penalty
            # If stability is below institutional baseline (70%), apply a linear penalty.
            if context_stability < 0.70:
                # Penalty scales from 0% at 0.7 stability up to 15% at 0.4 stability.
                # Formula: (0.7 - stability) * 0.5
                alignment_penalty = (0.70 - context_stability) * 0.5
                old_conf = confidence
                confidence *= 1.0 - alignment_penalty
                logger.warning(
                    "Market alignment safeguard active | symbol=%s | stability=%.2f | confidence reduced: %.2f -> %.2f",
                    symbol,
                    context_stability,
                    old_conf,
                    confidence,
                )
                metadata["market_context_penalty"] = alignment_penalty

        # 6.3 Entropy Guard (Consistency Check)
        # If sub-models are highly divergent in their confidence, it indicates uncertainty.
        winning_signals = [s for s in signals.values() if s.direction == direction]
        if len(winning_signals) > 1:
            conf_std = float(np.std([s.confidence for s in winning_signals]))
            if conf_std > 0.25:
                # 10% safety penalty for high entropy / internal disagreement
                old_conf = confidence
                confidence *= 0.90
                logger.warning(
                    "Entropy guard active | symbol=%s | conf_std=%.2f | confidence reduced: %.2f -> %.2f",
                    metadata.get("symbol", "unknown"),
                    conf_std,
                    old_conf,
                    confidence,
                )
                metadata["entropy_penalty"] = 0.10

        if self.monitor:
            self.monitor.record_signal_funnel("ensemble", "passed")
        return Signal(direction=direction, confidence=confidence, metadata=metadata)

    def predict(
        self,
        features: np.ndarray,
        **kwargs: Any,
    ) -> Signal:
        """
        Generate a trading signal from input features using internal models.

        Args:
            features: Primary feature array for RL agents (PPO, Dreamer).
            **kwargs: Additional context:
                seq (np.ndarray): Sequence data for the LSTM model.
                regime_info (RegimeInfo): Market regime information.

        Returns:
            Signal: Consolidated ensemble signal.
        """
        seq = kwargs.get("seq")
        regime_info = kwargs.get("regime_info")
        votes: Dict[str, Signal] = {}

        # PPO prediction
        if self.ppo_agent is not None:
            with profile("inference_ppo"):
                votes["ppo"] = self.ppo_agent.predict(features, regime_info=regime_info)
                self.dynamic_ensemble.record_prediction(
                    "ppo", votes["ppo"].direction, votes["ppo"].confidence
                )

        # Dreamer prediction
        if self.dreamer_agent is not None:
            with profile("inference_dreamer"):
                votes["dreamer"] = self.dreamer_agent.predict(features, regime_info=regime_info)
                self.dynamic_ensemble.record_prediction(
                    "dreamer", votes["dreamer"].direction, votes["dreamer"].confidence
                )

        # LSTM prediction
        if self.lstm_model is not None:
            with profile("inference_lstm"):
                # Use seq if provided, otherwise fallback to features
                lstm_input = seq if seq is not None else features
                votes["lstm"] = self.lstm_model.predict(lstm_input, regime_info=regime_info)
                self.dynamic_ensemble.record_prediction(
                    "lstm", votes["lstm"].direction, votes["lstm"].confidence
                )

        return self.aggregate_signals(
            votes, symbol=kwargs.get("symbol", "unknown"), regime_info=regime_info
        )


__all__ = ["EnsembleModel"]
