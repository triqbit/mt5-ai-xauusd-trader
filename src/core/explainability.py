from typing import Dict

from pydantic import BaseModel


class SignalExplanation(BaseModel):
    symbol: str
    direction: int
    features: Dict[str, float]
    contributions: Dict[str, str]  # 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    summary: str

class SignalExplainer:
    def explain(self, symbol: str, direction: int, features: Dict[str, float]) -> SignalExplanation:
        contributions = {}
        for feature, value in features.items():
            if value > 0:
                contributions[feature] = "POSITIVE"
            elif value < 0:
                contributions[feature] = "NEGATIVE"
            else:
                contributions[feature] = "NEUTRAL"

        summary = f"Signal for {symbol} in direction {direction} driven by {len(features)} features."
        return SignalExplanation(
            symbol=symbol,
            direction=direction,
            features=features,
            contributions=contributions,
            summary=summary
        )
