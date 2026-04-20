"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/portfolio_manager.py
Handles account monitoring, balance tracking, and aggregate exposure.
"""

import logging
from typing import Dict


class PortfolioManager:
    """
    Tracks account health and portfolio-wide metrics.
    Integrates with MT5Connector for real-time data.
    """

    def __init__(self, connector):
        self.connector = connector
        self.logger = logging.getLogger(__name__)

    async def get_account_summary(self) -> Dict:
        """Retrieves key account metrics (balance, equity, profit)."""
        try:
            # Assuming connector has a unified method for account info
            balance_info = await self.connector.get_account_balance()
            summary = {
                "balance": balance_info.get('balance', 0.0),
                "equity": balance_info.get('equity', 0.0),
                "margin": balance_info.get('margin', 0.0),
                "margin_free": balance_info.get('margin_free', 0.0),
                "margin_level": balance_info.get('margin_level', 0.0),
                "profit": balance_info.get('profit', 0.0)
            }
            return summary
        except Exception as e:
            self.logger.error(f"Failed to fetch account summary: {e}")
            return {}

    async def get_symbol_exposure(self, symbol: str) -> float:
        """Calculates total net lot exposure for a specific symbol."""
        try:
            if self.connector.use_metaapi:
                positions = await self.connector.connection.get_positions()
                symbol_positions = [p for p in positions if p['symbol'] == symbol]
                total_lots = sum(
                    [p['volume'] if p['type'] == 'BUY' else -p['volume']
                     for p in symbol_positions]
                )
                return total_lots
            else:
                import MetaTrader5 as mt5

                positions = mt5.positions_get(symbol=symbol)
                if positions is None:
                    return 0.0
                total_lots = sum(
                    [p.volume if p.type == mt5.POSITION_TYPE_BUY else -p.volume
                     for p in positions]
                )
                return total_lots
        except Exception as e:
            self.logger.error(f"Exposure calculation error for {symbol}: {e}")
            return 0.0

    async def check_drawdown(self, initial_balance: float) -> float:
        """Calculates current drawdown percentage."""
        summary = await self.get_account_summary()
        equity = summary.get('equity', initial_balance)
        if initial_balance <= 0:
            return 0.0
        drawdown = (initial_balance - equity) / initial_balance * 100
        return max(0.0, drawdown)
