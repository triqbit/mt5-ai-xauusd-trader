"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/order_manager.py
Handles trade execution, modification, and closure.
"""

import logging
from typing import Dict, List, Optional


class OrderManager:
    """
    Manages order execution and position tracking.
    Integrates with MT5Connector for dual-path execution (Desktop/MetaAPI).
    """
    def __init__(self, connector, symbol: str = "XAUUSD"):
        self.connector = connector
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)
        self.magic_number = 20240501  # Unique ID for AI trades

    async def execute_trade(self, action: str, volume: float, sl_pips: Optional[float] = None, tp_pips: Optional[float] = None) -> Dict:
        """
        Executes a market order with optional SL/TP.
        action: 'BUY' or 'SELL'
        """
        self.logger.info(f"Executing {action} order for {volume} lots on {self.symbol}")

        try:
            # Get current prices for SL/TP calculation
            tick = await self.connector.get_tick(self.symbol)
            if not tick:
                raise ValueError("Could not retrieve current market price.")

            price = tick['ask'] if action.upper() == "BUY" else tick['bid']
            sl, tp = self._calculate_sl_tp(action, price, sl_pips, tp_pips)

            if self.connector.use_metaapi:
                return await self._execute_metaapi(action, volume, sl, tp)
            else:
                return self._execute_mt5_desktop(action, volume, price, sl, tp)

        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return {"status": "error", "message": str(e)}

    def _calculate_sl_tp(self, action: str, price: float, sl_pips: Optional[float], tp_pips: Optional[float]):
        """Calculates absolute price levels for SL and TP based on pips."""
        # Standard pip for Gold (XAUUSD) is often 0.01 or 0.1 depending on broker
        # We'll use 0.1 as a default step for 'pips' in gold context
        pip_value = 0.1
        sl = None
        tp = None

        if sl_pips:
            sl = price - (sl_pips * pip_value) if action.upper() == "BUY" else price + (sl_pips * pip_value)
        if tp_pips:
            tp = price + (tp_pips * pip_value) if action.upper() == "BUY" else price - (tp_pips * pip_value)

        return sl, tp

    def _execute_mt5_desktop(self, action: str, volume: float, price: float, sl: Optional[float], tp: Optional[float]) -> Dict:
        """Execution via local MetaTrader5 terminal."""
        import MetaTrader5 as mt5

        order_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": "AI Trade - Desktop",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            return {"status": "error", "message": "order_send returned None"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "status": "error",
                "retcode": result.retcode,
                "message": f"MT5 Error: {result.comment}"
            }

        return {"status": "success", "order_id": result.order, "deal": result.deal}

    async def _execute_metaapi(self, action: str, volume: float, sl: Optional[float], tp: Optional[float]) -> Dict:
        """Execution via MetaAPI Cloud."""
        if not self.connector.connection:
            raise ConnectionError("MetaAPI connection not established.")

        try:
            options = {
                "comment": "AI Trade - MetaAPI",
                "magic": self.magic_number
            }
            if sl:
                options["stopLoss"] = sl
            if tp:
                options["takeProfit"] = tp

            result = await self.connector.connection.create_market_order(
                self.symbol,
                action.upper(),
                volume,
                options
            )
            return {"status": "success", "order_id": result['orderId']}
        except Exception as e:
            return {"status": "error", "message": f"MetaAPI Error: {e!s}"}

    async def close_all_positions(self):
        """Emergency close for all open positions for this symbol."""
        # To be implemented with position tracking
        pass

    async def get_active_positions(self) -> List[Dict]:
        """Fetch active positions for the symbol."""
        if self.connector.use_metaapi:
            positions = await self.connector.connection.get_positions()
            return [p for p in positions if p['symbol'] == self.symbol]
        else:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None:
                return []
            return [p._asdict() for p in positions]
