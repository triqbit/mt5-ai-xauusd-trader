"""
Layer 4: Decision Agents (CIO & CRO)
Synthesizes Layer 1-3 outputs and applies Darwinian weights.
"""

from typing import Any, Dict

import structlog

from src.models.atlas.core.darwinian_engine import DarwinianEngine

logger = structlog.get_logger(__name__)

class ChiefInvestmentOfficer:
    def __init__(self, darwin_engine: DarwinianEngine):
        self.darwin = darwin_engine

    def synthesize(self, agent_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        agent_outputs: { 'Federal_Reserve_Agent': {'score': 0.8, 'thesis': '...'}, ... }
        """
        weights = self.darwin.get_weights()
        total_weight = 0.0
        weighted_score = 0.0

        for agent_name, output in agent_outputs.items():
            if 'score' not in output:
                continue

            weight = weights.get(agent_name, 1.0)
            score = output['score'] # Assume 0.0 (bearish) to 1.0 (bullish)

            weighted_score += score * weight
            total_weight += weight

        final_conviction = weighted_score / total_weight if total_weight > 0 else 0.5

        # Decision logic mapping conviction to Signal Direction
        direction = 0 # Flat
        if final_conviction > 0.65:
            direction = 1 # Long
        elif final_conviction < 0.35:
            direction = -1 # Short

        logger.info("CIO Synthesis Complete", conviction=final_conviction, direction=direction)

        return {
            "conviction": final_conviction,
            "direction": direction,
            "weighted_scores": weights
        }

class ChiefRiskOfficer:
    def evaluate_risk(self, macro_context: Dict[str, Any]) -> bool:
        """
        Acts as an antagonist. If it finds severe correlated risks (e.g. VIX > 35),
        it vetos the trade. Returns True if Trade is ALLOWED, False if VETOED.
        """
        try:
            vix = macro_context.get("macro_data", {}).get("VIX", 0.0)
            if vix is not None and vix > 35.0:
                logger.warning("CRO VETO: VIX exceeds extreme threshold.", vix=vix)
                return False
        except Exception as e:
            logger.error("CRO Evaluation Error", error=str(e))

        return True
