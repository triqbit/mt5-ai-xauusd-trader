"""
Integration module to bridge ATLAS with the existing MT5-AI Ensemble & Risk Engine.
"""

import structlog

from src.core.constants import SignalDirection
from src.core.schemas import TradeSignal
from src.models.atlas.agents.layer1_macro import FedAgent, GeopoliticsAgent
from src.models.atlas.agents.layer4_decision import ChiefInvestmentOfficer, ChiefRiskOfficer
from src.models.atlas.core.darwinian_engine import DarwinianEngine
from src.models.atlas.core.vertex_client import VertexClient
from src.models.atlas.data.fetchers import AtlasDataPipeline

logger = structlog.get_logger(__name__)

class AtlasHybridSystem:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.darwin = DarwinianEngine()
        self.cio = ChiefInvestmentOfficer(self.darwin)
        self.cro = ChiefRiskOfficer()

        self.agents = {}
        if self.use_llm:
            try:
                self.llm = VertexClient()
                self.agents["Federal_Reserve_Agent"] = FedAgent(self.llm)
                self.agents["Geopolitics_Agent"] = GeopoliticsAgent(self.llm)

                for name in self.agents:
                    self.darwin.register_agent(name)
            except Exception as e:
                logger.error("Failed to initialize ATLAS LLM Agents. Falling back to technical-only.", error=str(e))
                self.use_llm = False

    def get_atlas_overlay(self, technical_signal: TradeSignal) -> TradeSignal:
        """
        Takes the base technical signal (e.g., from PPO/Ensemble) and applies the ATLAS macro overlay.
        """
        logger.info("ATLAS Overlay activated.")

        # 1. Fetch Data
        context = AtlasDataPipeline.aggregate_context()

        # 2. CRO Veto Check
        is_safe = self.cro.evaluate_risk(context)
        if not is_safe:
            logger.warning("ATLAS CRO has vetoed the trade due to macro risk.")
            technical_signal.direction = SignalDirection.FLAT
            technical_signal.confidence = 0.0
            technical_signal.metadata["atlas_veto"] = True
            return technical_signal

        # 3. LLM Agent Processing (if enabled and configured)
        atlas_direction = 0 # 0=Flat
        if self.use_llm:
            # Note: In a real system, you'd parse the LLM text to extract the 0.0-1.0 score.
            # This is a placeholder for the parsed outputs.
            # outputs = { name: parse_score(agent.analyze(context)) for name, agent in self.agents.items() }

            # Mocking parsed output for MVP integration
            outputs = {
                "Federal_Reserve_Agent": {"score": 0.6},
                "Geopolitics_Agent": {"score": 0.7}
            }

            cio_decision = self.cio.synthesize(outputs)
            atlas_direction = cio_decision["direction"]
            technical_signal.metadata["atlas_cio_conviction"] = cio_decision["conviction"]
        else:
            # Fallback logic if no API key: Simple heuristic based on VIX
            vix = context.get("macro_data", {}).get("VIX")
            if vix and vix < 20:
                atlas_direction = 1 # Risk on implies slightly bullish for markets
            elif vix and vix > 25:
                atlas_direction = -1

        # 4. Hybrid Synthesis (Technical + ATLAS)
        # If ATLAS disagrees heavily with technicals, reduce confidence or flatten.
        tech_dir = technical_signal.direction.value

        if tech_dir != 0 and atlas_direction != 0 and tech_dir != atlas_direction:
            logger.info("Conflict detected between Technical Ensemble and ATLAS Macro. Flattening position for safety.")
            technical_signal.direction = SignalDirection.FLAT
            technical_signal.confidence = 0.0
            technical_signal.metadata["atlas_conflict"] = True

        technical_signal.metadata["atlas_processed"] = True
        return technical_signal
