"""
Darwinian Self-Research and Weighting Engine
Adjusts agent weights based on historical performance.
"""

import math
from typing import Dict

import structlog

logger = structlog.get_logger(__name__)

class DarwinianEngine:
    def __init__(self, min_weight: float = 0.3, max_weight: float = 2.5):
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.agent_scores: Dict[str, float] = {} # Agent name -> cumulative score
        self.agent_weights: Dict[str, float] = {} # Agent name -> current weight

    def register_agent(self, agent_name: str, initial_weight: float = 1.0):
        if agent_name not in self.agent_weights:
            self.agent_weights[agent_name] = initial_weight
            self.agent_scores[agent_name] = 0.0

    def update_scores(self, performance_data: Dict[str, float]):
        """
        performance_data: {agent_name: rolling_sharpe_or_profit_contrib}
        """
        if not performance_data:
            return

        # Sort agents by performance
        sorted_agents = sorted(performance_data.items(), key=lambda x: x[1], reverse=True)
        total_agents = len(sorted_agents)

        if total_agents == 0:
            return

        # Determine quartiles
        top_quartile_count = math.ceil(total_agents * 0.25)
        bottom_quartile_count = math.floor(total_agents * 0.25)

        top_agents = [a[0] for a in sorted_agents[:top_quartile_count]]
        bottom_agents = [a[0] for a in sorted_agents[-bottom_quartile_count:]] if bottom_quartile_count > 0 else []

        # Apply Darwinian Weighting: Top gets * 1.05, Bottom gets * 0.95
        for agent_name in self.agent_weights:
            current = self.agent_weights[agent_name]
            if agent_name in top_agents:
                new_w = min(current * 1.05, self.max_weight)
                self.agent_weights[agent_name] = new_w
                logger.info(f"Darwinian Up-Weight: {agent_name} -> {new_w:.2f}")
            elif agent_name in bottom_agents:
                new_w = max(current * 0.95, self.min_weight)
                self.agent_weights[agent_name] = new_w
                logger.info(f"Darwinian Down-Weight: {agent_name} -> {new_w:.2f}")

    def get_weights(self) -> Dict[str, float]:
        return self.agent_weights

