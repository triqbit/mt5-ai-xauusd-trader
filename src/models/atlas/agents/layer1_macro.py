"""
Layer 1: Macro Agents
Analyzes Central Banks, Geopolitics, and Yield Curves.
"""

from src.models.atlas.agents.base_agent import AgentConfig, BaseAgent
from src.models.atlas.core.vertex_client import VertexClient


class FedAgent(BaseAgent):
    def __init__(self, llm_client: VertexClient):
        config = AgentConfig(
            name="Federal_Reserve_Agent",
            layer=1,
            prompt_template="""
            You are the Federal Reserve Macro Agent.
            Analyze the following macroeconomic data and recent news:
            {macro_data}

            Determine the current regime: Risk-On or Risk-Off?
            Provide a conviction score (0.0 to 1.0) and a brief thesis.
            """
        )
        super().__init__(config, llm_client)

class GeopoliticsAgent(BaseAgent):
    def __init__(self, llm_client: VertexClient):
        config = AgentConfig(
            name="Geopolitics_Agent",
            layer=1,
            prompt_template="""
            You are the Geopolitical Risk Agent.
            Analyze the following global news events:
            {news_data}

            Assess the flight-to-safety risk (especially relevant for Gold/XAUUSD).
            Provide a conviction score (0.0 to 1.0) and a brief thesis.
            """
        )
        super().__init__(config, llm_client)
