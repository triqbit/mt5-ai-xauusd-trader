from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TradeSignal(BaseModel):
    """Validated trading signal schema."""
    symbol: str
    direction: int = Field(description="+1 buy / -1 sell / 0 hold")
    entry_price: float = Field(gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    lot_size: Optional[float] = Field(default=None, ge=0.01)
    algorithm: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
