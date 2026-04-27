"""
src/schemas/market_data.py
Pydantic schemas for market data validation.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict


class OHLCVData(BaseModel):
    """Schema for a single OHLCV bar."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    time: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    tick_volume: float = Field(..., ge=0)

    @property
    def is_valid_ohlc(self) -> bool:
        """Check if high is the highest and low is the lowest."""
        return self.high >= self.open and self.high >= self.close and \
               self.low <= self.open and self.low <= self.close


class OHLCVSeries(BaseModel):
    """Schema for a sequence of OHLCV bars."""
    bars: List[OHLCVData]

    def to_pandas(self):
        import pandas as pd
        return pd.DataFrame([bar.model_dump() for bar in self.bars])
