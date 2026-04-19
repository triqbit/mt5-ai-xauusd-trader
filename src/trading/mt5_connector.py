"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/mt5_connector.py
Dual-path MT5 connector:
  Primary : Direct MetaTrader5 Python SDK
  Fallback : MetaAPI cloud (for Mac/Linux or remote deployments)
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Dict, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)

# MT5 constants (replicated so the module loads on Mac/Linux)
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_TIME_GTC = 1
ORDER_FILLING_IOC = 1

TIMEFRAME_MAP: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


class MT5ConnectionError(RuntimeError):
    """Raised when MT5 terminal cannot be reached."""


class MT5Connector:
    """
    Thread-safe wrapper around MetaTrader5 Python SDK.
    Falls back to MetaAPI cloud when direct connection is unavailable.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self._mt5_available = False
        self._connected = False

    # -- Lifecycle ---------------------------------------------------------
    def connect(self) -> bool:
        """Establish connection to MT5. Returns True on success."""
        try:
            import MetaTrader5 as mt5  # Windows-only SDK

            self._mt5_available = True
            if not mt5.initialize(path=self.cfg.mt5_path):
                raise MT5ConnectionError(f"mt5.initialize failed: {mt5.last_error()}")
            if not mt5.login(
                login=self.cfg.mt5_login,
                password=self.cfg.mt5_password,
                server=self.cfg.mt5_server,
            ):
                raise MT5ConnectionError(f"mt5.login failed: {mt5.last_error()}")
            self._connected = True
            info = mt5.account_info()
            logger.info(
                "MT5 connected | account=%d balance=%.2f server=%s",
                info.login,
                info.balance,
                info.server,
            )
            return True
        except ImportError:
            logger.warning("MetaTrader5 SDK not available - using MetaAPI fallback")
            return self._connect_metaapi()
        except MT5ConnectionError as exc:
            logger.error("MT5 connect error: %s", exc)
            return self._connect_metaapi()

    def disconnect(self) -> None:
        """Clean shutdown."""
        if self._mt5_available and self._connected:
            try:
                import MetaTrader5 as mt5

                mt5.shutdown()
            except Exception:
                pass
        self._connected = False
        logger.info("MT5 connector shut down")

    @contextmanager
    def session(self):
        """Context manager that auto-connects and disconnects."""
        self.connect()
        try:
            yield self
        finally:
            self.disconnect()

    # -- Market Data -------------------------------------------------------
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        n_bars: int = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLCV bars from MT5 terminal."""
        import MetaTrader5 as mt5

        tf = TIMEFRAME_MAP.get(timeframe, 5)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
        if rates is None or len(rates) == 0:
            raise ValueError(f"No data for {symbol} {timeframe}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        logger.debug("Fetched %d bars for %s/%s", len(df), symbol, timeframe)
        return df

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """Return latest bid/ask for symbol."""
        import MetaTrader5 as mt5

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f"No tick data for {symbol}")
        return {"bid": tick.bid, "ask": tick.ask, "time": tick.time}

    def get_account_balance(self) -> float:
        import MetaTrader5 as mt5

        info = mt5.account_info()
        return info.balance if info else 0.0

    # -- Order Execution ---------------------------------------------------
    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """
        Submit a market order.
        Returns ticket number on success, None on failure.
        """
        import MetaTrader5 as mt5

        order_type = ORDER_TYPE_BUY if signal.direction == 1 else ORDER_TYPE_SELL
        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": signal.lot_size,
            "type": order_type,
            "price": signal.entry_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "comment": f"MT5Bot/{signal.algorithm}",
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Order failed: %s", result)
            return None
        logger.info(
            "Order placed | ticket=%d symbol=%s dir=%s lots=%.2f",
            result.order,
            signal.symbol,
            signal.direction,
            signal.lot_size,
        )
        return result.order

    def close_position(self, ticket: int, symbol: str, lot_size: float) -> bool:
        """Close an open position by ticket."""
        import MetaTrader5 as mt5

        tick = self.get_tick(symbol)
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            logger.warning("Position %d not found", ticket)
            return False
        direction = ORDER_TYPE_SELL if pos[0].type == ORDER_TYPE_BUY else ORDER_TYPE_BUY
        price = tick["bid"] if direction == ORDER_TYPE_SELL else tick["ask"]
        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": direction,
            "position": ticket,
            "price": price,
            "comment": "MT5Bot/close",
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        success = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
        if success:
            logger.info("Position %d closed", ticket)
        else:
            logger.error("Close failed for %d: %s", ticket, result)
        return success

    # -- MetaAPI fallback (stub) -------------------------------------------
    def _connect_metaapi(self) -> bool:
        if not self.cfg.metaapi_token:
            logger.error("No MetaAPI token configured")
            return False
        logger.info("MetaAPI fallback - implement async client here")
        # TODO: integrate metaapi_cloud_sdk async client
        return False


__all__ = ["MT5Connector", "MT5ConnectionError"]
