from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Schema for validating performance reporting data."""
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    total_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
