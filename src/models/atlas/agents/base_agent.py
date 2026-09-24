"""
Base Agent Architecture for the ATLAS Hybrid System
"""

from dataclasses import dataclass
from typing import Any, Dict

from src.models.atlas.core.vertex_client import VertexClient


@dataclass
class AgentConfig:
    name: str
    layer: int
    prompt_template: str
    weight: float = 1.0

class BaseAgent:
    def __init__(self, config: AgentConfig, llm_client: VertexClient):
        self.config = config
        self.llm = llm_client
        self.current_weight = config.weight

    def generate_prompt(self, context: Dict[str, Any]) -> str:
        """Hydrates the prompt template with real-time data."""
        return self.config.prompt_template.format(**context)

    def analyze(self, context: Dict[str, Any]) -> str:
        """Core method to be overridden or used by subclasses to get LLM insights."""
        prompt = self.generate_prompt(context)
        return self.llm.query(prompt)
