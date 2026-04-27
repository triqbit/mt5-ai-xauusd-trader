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
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

try:
    from metaapi_cloud_sdk import MetaApi

    METAAPI_AVAILABLE = True
except ImportError:
    METAAPI_AVAILABLE = False
    MetaApi = None

from src.core.config import TradingConfig

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


class MT5Connector:
    """
    Enterprise-grade connector for MetaTrader 5.
    Supports both native Windows SDK and MetaAPI cloud fallback for cross-platform support.
    """

    def __init__(self, config: TradingConfig) -> None:
        """
        Initialize the connector with configuration.

        Args:
            config: TradingConfig object containing credentials and settings.
        """
        self.cfg = config
        self.use_metaapi: bool = False
        self.metaapi: Optional[Any] = None
        self._metaapi_account: Optional[Any] = None
        self._metaapi_connection: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self) -> bool:
        """
        Establish connection to MT5 terminal or MetaAPI cloud.
        Follows a dual-path strategy: Native SDK first, then MetaAPI fallback.

        Returns:
            True if connection established, False otherwise.
        """
        logger.info("Initializing MT5 connector | mode=%s", self.cfg.mode)

        # 1. Attempt Native MT5 SDK (Primary Path - Windows only)
        if MT5_AVAILABLE:
            try:
                # mt5.initialize returns True on success
                init_params = {
                    "login": self.cfg.mt5_login,
                    "password": self.cfg.mt5_password,
                    "server": self.cfg.mt5_server,
                }
                if self.cfg.mt5_path:
                    init_params["path"] = self.cfg.mt5_path

                if mt5.initialize(**init_params):
                    logger.info("Native MT5 SDK initialized successfully.")
                    self.use_metaapi = False
                    self._is_initialized = True
                    return True
                else:
                    logger.warning("Native mt5.initialize failed: %s", mt5.last_error())
            except Exception as e:
                logger.error("Native MT5 initialization error: %s", e)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        if METAAPI_AVAILABLE and self.cfg.metaapi_token:
            logger.info("Attempting MetaAPI cloud fallback...")
            try:
                self.metaapi = MetaApi(self.cfg.metaapi_token)
                self.use_metaapi = True
                self._is_initialized = True
                logger.info(
                    "MetaAPI fallback configured (Note: Async features limited in sync wrapper)."
                )
                return True
            except Exception as e:
                logger.error("MetaAPI initialization failed: %s", e)

        logger.error("All MT5 connection paths failed.")
        return False

    def connect(self) -> bool:
        """Alias for initialize() to support existing interfaces."""
        return self.initialize()

    def shutdown(self) -> None:
        """Gracefully close all connections."""
        if self._is_initialized:
            if not self.use_metaapi and MT5_AVAILABLE:
                mt5.shutdown()
            elif self.use_metaapi:
                import asyncio

                try:
                    if self._metaapi_connection:
                        asyncio.run(self._metaapi_connection.close())
                except Exception as e:
                    logger.error("Error closing MetaAPI connection: %s", e)

            logger.info("MT5 connector shutdown complete.")
            self._is_initialized = False

    def disconnect(self) -> None:
        """Alias for shutdown() to support existing interfaces."""
        self.shutdown()

    @contextmanager
    def session(self):
        """Context manager for safe connection handling."""
        try:
            if not self._is_initialized:
                self.initialize()
            yield self
        finally:
            self.shutdown()

    async def _get_metaapi_connection(self) -> Any:
        """Get or create MetaAPI streaming connection."""
        if self._metaapi_connection and self._metaapi_connection.connected:
            return self._metaapi_connection

        if not self._metaapi_account:
            self._metaapi_account = await self.metaapi.metatrader_account_api.get_account(
                self.cfg.metaapi_account_id
            )

        self._metaapi_connection = self._metaapi_account.get_streaming_connection()
        await self._metaapi_connection.connect()
        await self._metaapi_connection.wait_synchronized()
        return self._metaapi_connection

    def _run_async(self, coro):
        """Helper to run async code in a temporary event loop, ensuring cleanup."""
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD').
            timeframe: Chart timeframe string (e.g., 'M5').
            n_bars: Number of bars to retrieve.

        Returns:
            DataFrame containing OHLCV data or empty DataFrame on failure.
        """
        if not self._is_initialized:
            logger.error("Connector not initialized.")
            return pd.DataFrame()

        tf = TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            logger.error("Invalid timeframe: %s", timeframe)
            return pd.DataFrame()

        if not self.use_metaapi:
            # Native MT5 SDK
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None:
                logger.error("Failed to copy rates for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            # MetaAPI Cloud Fallback
            try:

                async def fetch_metaapi_rates():
                    # Note: We must re-initialize/connect within this loop
                    # because asyncio.run/new_event_loop creates a fresh context.
                    # In a production app, we'd run the whole bot in one async loop.
                    account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await connection.wait_synchronized()
                    candles = await connection.terminal_state.get_candles(symbol, timeframe, n_bars)
                    await connection.close()
                    return pd.DataFrame(candles)

                return self._run_async(fetch_metaapi_rates())
            except Exception as e:
                logger.error("MetaAPI get_rates failed: %s", e)
                return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match expected interface."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask).

        Args:
            symbol: Trading symbol.

        Returns:
            Dictionary with 'bid' and 'ask' prices.
        """
        if not self._is_initialized:
            return {"bid": 0.0, "ask": 0.0}

        if not self.use_metaapi and MT5_AVAILABLE:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error("Failed to get tick for %s: %s", symbol, mt5.last_error())
                return {"bid": 0.0, "ask": 0.0}
            return {"bid": float(tick.bid), "ask": float(tick.ask)}
        elif self.use_metaapi:
            try:

                async def fetch_metaapi_tick():
                    account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await connection.wait_synchronized()
                    price = connection.terminal_state.price(symbol)
                    res = {"bid": 0.0, "ask": 0.0}
                    if price:
                        res = {"bid": float(price["bid"]), "ask": float(price["ask"])}
                    await connection.close()
                    return res

                return self._run_async(fetch_metaapi_tick())
            except Exception as e:
                logger.error("MetaAPI get_tick failed: %s", e)

        return {"bid": 0.0, "ask": 0.0}

    def place_order(
        self,
        symbol: str,
        order_type: int,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
    ) -> Optional[int]:
        """
        Execute a market order.

        Args:
            symbol: Trading symbol.
            order_type: 0 for BUY, 1 for SELL.
            volume: Lot size.
            sl: Stop loss price.
            tp: Take profit price.
            comment: Order comment.

        Returns:
            Order ticket ID if successful, None otherwise.
        """
        if not self._is_initialized:
            logger.error("Connector not initialized.")
            return None

        if not self.use_metaapi and MT5_AVAILABLE:
            tick = self.get_tick(symbol)
            price = tick["ask"] if order_type == ORDER_TYPE_BUY else tick["bid"]

            if price == 0:
                logger.error("Invalid price for order execution.")
                return None

            request = {
                "action": TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": float(price),
                "magic": 20240419,
                "comment": comment,
                "type_time": ORDER_TIME_GTC,
                "type_filling": ORDER_FILLING_IOC,
            }
            if sl:
                request["sl"] = float(sl)
            if tp:
                request["tp"] = float(tp)

            result = mt5.order_send(request)
            if result is None:
                logger.error("order_send returned None. MT5 error: %s", mt5.last_error())
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Order rejected: %s (code: %d)", result.comment, result.retcode)
                return None

            logger.info("Order PLACED | Ticket #%d | %s", result.order, symbol)
            return int(result.order)

        elif self.use_metaapi:
            try:

                async def place_metaapi_order():
                    account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await connection.wait_synchronized()
                    side = "BUY" if order_type == ORDER_TYPE_BUY else "SELL"
                    result = await connection.create_market_order(
                        symbol, side, volume, sl, tp, {"comment": comment}
                    )
                    await connection.close()
                    return int(result["orderId"])

                return self._run_async(place_metaapi_order())
            except Exception as e:
                logger.error("MetaAPI place_order failed: %s", e)
                return None

        logger.warning("place_order failed: No connection path available.")
        return None

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account balance, equity, and margin information."""
        if not self._is_initialized:
            return {}

        if not self.use_metaapi and MT5_AVAILABLE:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        elif self.use_metaapi:
            try:

                async def fetch_metaapi_account():
                    account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await connection.wait_synchronized()
                    info = connection.terminal_state.account_information
                    await connection.close()
                    return info

                return self._run_async(fetch_metaapi_account())
            except Exception as e:
                logger.error("MetaAPI get_account_info failed: %s", e)

        return {}

    def get_account_balance(self) -> float:
        """Retrieve current account balance."""
        info = self.get_account_info()
        return float(info.get("balance", 0.0))

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve current open positions."""
        if not self._is_initialized:
            return []

        if not self.use_metaapi and MT5_AVAILABLE:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        elif self.use_metaapi:
            try:

                async def fetch_metaapi_positions():
                    account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await connection.wait_synchronized()
                    positions = connection.terminal_state.positions
                    if symbol:
                        positions = [p for p in positions if p["symbol"] == symbol]
                    await connection.close()
                    return positions

                return self._run_async(fetch_metaapi_positions())
            except Exception as e:
                logger.error("MetaAPI get_positions failed: %s", e)

        return []


__all__ = ["ORDER_TYPE_BUY", "ORDER_TYPE_SELL", "TIMEFRAME_MAP", "MT5Connector"]
