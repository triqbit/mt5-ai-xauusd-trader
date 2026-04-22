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

import asyncio
import logging
import threading
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
        self._metaapi_rpc_conn: Optional[Any] = None
        self._metaapi_streaming_conn: Optional[Any] = None

        self._is_initialized: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def _start_loop(self) -> None:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._loop_thread.start()

    def _run_coro(self, coro: Any) -> Any:
        if self._loop is None:
            self._start_loop()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

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
                if mt5.initialize(
                    path=self.cfg.mt5_path,
                    login=self.cfg.mt5_login,
                    password=self.cfg.mt5_password,
                    server=self.cfg.mt5_server,
                ):
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

                async def _setup_metaapi() -> None:
                    self._metaapi_account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    await self._metaapi_account.wait_connected()
                    self._metaapi_rpc_conn = self._metaapi_account.get_rpc_connection()
                    await self._metaapi_rpc_conn.connect()
                    self._metaapi_streaming_conn = self._metaapi_account.get_streaming_connection()
                    await self._metaapi_streaming_conn.connect()
                    await self._metaapi_streaming_conn.wait_synchronized()

                self._run_coro(_setup_metaapi())
                self._is_initialized = True
                logger.info("MetaAPI fallback configured and connected.")
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

                async def _close() -> None:
                    if self._metaapi_rpc_conn:
                        await self._metaapi_rpc_conn.close()
                    if self._metaapi_streaming_conn:
                        await self._metaapi_streaming_conn.close()

                self._run_coro(_close())

            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)
                if self._loop_thread:
                    self._loop_thread.join()
                self._loop = None

            logger.info("MT5 connector shutdown complete.")
            self._is_initialized = False

    def disconnect(self) -> None:
        """Alias for shutdown() to support existing interfaces."""
        self.shutdown()

    @contextmanager
    def session(self) -> Any:
        """Context manager for safe connection handling."""
        try:
            if not self._is_initialized:
                self.initialize()
            yield self
        finally:
            self.shutdown()

    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        if not self._is_initialized:
            return pd.DataFrame()

        if not self.use_metaapi:
            tf = TIMEFRAME_MAP.get(timeframe, 5)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None:
                logger.error("Failed to copy rates for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:

            async def _get_rates() -> Any:
                return await self._metaapi_streaming_conn.terminal_state.get_candles(
                    symbol, timeframe, n_bars
                )

            try:
                candles = self._run_coro(_get_rates())
                return pd.DataFrame(candles)
            except Exception as e:
                logger.error("MetaAPI get_rates failed: %s", e)
                return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match main.py expectations."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """Retrieve latest symbol tick (bid/ask)."""
        if not self._is_initialized:
            return {"bid": 0.0, "ask": 0.0}

        if not self.use_metaapi:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error("Failed to get tick for %s: %s", symbol, mt5.last_error())
                return {"bid": 0.0, "ask": 0.0}
            return {"bid": tick.bid, "ask": tick.ask}
        else:

            async def _get_tick() -> Any:
                return await self._metaapi_streaming_conn.terminal_state.get_symbol_price(symbol)

            try:
                price = self._run_coro(_get_tick())
                return {"bid": price["bid"], "ask": price["ask"]}
            except Exception as e:
                logger.error("MetaAPI get_tick failed: %s", e)
                return {"bid": 0.0, "ask": 0.0}

    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """Execute a market order."""
        if not self._is_initialized:
            return None

        if not self.use_metaapi:
            order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL
            tick = self.get_tick(signal.symbol)
            price = tick["ask"] if order_type == ORDER_TYPE_BUY else tick["bid"]

            if price == 0:
                logger.error("Invalid price for order execution.")
                return None

            request = {
                "action": TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": signal.lot_size,
                "type": order_type,
                "price": price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "magic": 20240419,
                "comment": f"AI:{signal.algorithm}",
                "type_time": ORDER_TIME_GTC,
                "type_filling": ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Order rejected: %s (code: %d)", result.comment, result.retcode)
                return None

            logger.info("Order PLACED | Ticket #%d | %s", result.order, signal.symbol)
            return int(result.order)
        else:

            async def _place_order() -> Any:
                if signal.direction > 0:
                    return await self._metaapi_rpc_conn.create_market_buy_order(
                        signal.symbol, signal.lot_size, signal.stop_loss, signal.take_profit
                    )
                else:
                    return await self._metaapi_rpc_conn.create_market_sell_order(
                        signal.symbol, signal.lot_size, signal.stop_loss, signal.take_profit
                    )

            try:
                result = self._run_coro(_place_order())
                return int(result["orderId"])
            except Exception as e:
                logger.error("MetaAPI place_order failed: %s", e)
                return None

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account information."""
        if not self._is_initialized:
            return {}
        if not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        else:

            async def _get_acc() -> Any:
                return await self._metaapi_rpc_conn.get_account_information()

            try:
                return self._run_coro(_get_acc())
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
        if not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        else:

            async def _get_pos() -> Any:
                return await self._metaapi_rpc_conn.get_positions()

            try:
                return self._run_coro(_get_pos())
            except Exception as e:
                logger.error("MetaAPI get_positions failed: %s", e)
                return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
