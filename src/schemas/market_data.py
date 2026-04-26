from datetime import datetime

from pydantic import BaseModel, Field


class OHLCVData(BaseModel):
    """Schema for validating individual market bar data."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = Field(ge=0)
