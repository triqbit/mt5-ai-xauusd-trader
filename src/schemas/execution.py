from typing import Optional
from pydantic import BaseModel
from .signals import TradeSignal

class ExecutionDecision(BaseModel):
    """Schema for validating the output of risk and execution filters."""
    approved: bool
    reason: str
    signal: Optional[TradeSignal] = None
