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
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import nest_asyncio
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
from src.core.exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5ExecutionError,
)
from src.core.retry import with_retry
from src.trading.risk_manager import TradeSignal

# Apply nest_asyncio to allow nested loops (MetaAPI SDK uses asyncio)
nest_asyncio.apply()

logger = logging.getLogger(__name__)

# MT5 constants (replicated so the module loads on Mac/Linux)
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_TIME_GTC = 1
ORDER_FILLING_IOC = 1

TIMEFRAME_MAP: dict[str, int] = {
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
        self.metaapi: Any | None = None
        self.metaapi_account: Any | None = None
        self.metaapi_connection: Any | None = None
        self._is_initialized: bool = False

    @with_retry(MT5ConnectionError, max_retries=3)
    def initialize(self) -> bool:
        """
        Establish connection to MT5 terminal or MetaAPI cloud.
        Follows a dual-path strategy: Native SDK first, then MetaAPI fallback.

        Returns:
            True if connection established.

        Raises:
            MT5ConnectionError: If all connection paths fail.
        """
        logger.info("Initializing MT5 connector | mode=%s", self.cfg.mode)

        # 1. Attempt Native MT5 SDK (Primary Path - Windows only)
        if MT5_AVAILABLE:
            try:
                if mt5.initialize(
                    path=self.cfg.mt5_path,
                    login=self.cfg.mt5_login,
                    password=self.cfg.mt5_password.get_secret_value(),
                    server=self.cfg.mt5_server,
                ):
                    logger.info("Native MT5 SDK initialized successfully.")
                    self.use_metaapi = False
                    self._is_initialized = True
                    return True
                error_code, error_desc = mt5.last_error()
                logger.warning("Native mt5.initialize failed: %s (code: %d)", error_desc, error_code)
                if error_code == getattr(mt5, "RES_E_NOT_FOUND", -5):
                    logger.info("TIP: MT5 terminal not found. Check if MT5_PATH is correct.")
            except Exception as e:
                logger.warning("Native MT5 initialization encountered an error: %s", e)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        metaapi_token = self.cfg.metaapi_token.get_secret_value()
        if METAAPI_AVAILABLE and metaapi_token and self.cfg.metaapi_account_id:
            logger.info("Attempting MetaAPI cloud fallback...")
            try:
                self.metaapi = MetaApi(metaapi_token)

                async def _init_metaapi():
                    self.metaapi_account = await self.metaapi.metatrader_account_api.get_account(
                        self.cfg.metaapi_account_id
                    )
                    await self.metaapi_account.wait_connected()
                    self.metaapi_connection = self.metaapi_account.get_rpc_connection()
                    await self.metaapi_connection.connect()
                    await self.metaapi_connection.wait_synchronized()

                asyncio.run(_init_metaapi())
                self.use_metaapi = True
                self._is_initialized = True
                logger.info("MetaAPI fallback configured and connected.")
                return True
            except Exception as e:
                logger.error("MetaAPI initialization failed: %s", e)
                raise MT5ConnectionError(f"MetaAPI initialization failed: {e}") from e

        msg = "All MT5 connection paths failed."
        logger.error(msg)
        raise MT5ConnectionError(msg)

    def connect(self) -> bool:
        """Alias for initialize() to support existing interfaces."""
        return self.initialize()

    def shutdown(self) -> None:
        """Gracefully close all connections."""
        if self._is_initialized:
            if not self.use_metaapi and MT5_AVAILABLE:
                mt5.shutdown()
            elif self.use_metaapi and self.metaapi_connection:
                asyncio.run(self.metaapi_connection.close())
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

    @with_retry(
        MT5DataError, max_retries=3, retry_if=lambda e: getattr(e, "retriable", True)
    )
    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None:
                error_code, error_desc = mt5.last_error()
                # Most data errors in MT5 are transient (connection, busy)
                retriable = error_code in [
                    mt5.TRADE_RETCODE_CONNECTION,
                    mt5.TRADE_RETCODE_TIMEOUT,
                    -5,  # Not found might be transient if terminal is rebooting
                ]
                raise MT5DataError(
                    f"Failed to copy rates: {error_desc} (code: {error_code})",
                    retriable=retriable,
                )
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:

            async def _get_rates():
                try:
                    candles = await self.metaapi_connection.get_historical_candles(
                        symbol, timeframe, None, n_bars
                    )
                    return candles
                except Exception as e:
                    error_msg = str(e).lower()
                    retriable = any(
                        kw in error_msg
                        for kw in ["timeout", "connection", "rate limit", "busy"]
                    )
                    raise MT5DataError(
                        f"MetaAPI rates fetch failed: {e}", retriable=retriable
                    ) from e

            candles = asyncio.run(_get_rates())
            df = pd.DataFrame(candles)
            if not df.empty:
                df["time"] = pd.to_datetime(df["time"])
            return df

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        return self.get_rates(symbol, timeframe, n_bars)

    def get_rates_range(
        self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a specific time range.
        """
        if not self._is_initialized:
            return pd.DataFrame()

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            rates = mt5.copy_rates_range(symbol, tf, date_from, date_to)
            if rates is None:
                logger.error("Failed to copy rates range for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            async def _get_range():
                return await self.metaapi_connection.get_historical_candles(
                    symbol, timeframe, date_from, date_to
                )
            candles = asyncio.run(_get_range())
            df = pd.DataFrame(candles)
            if not df.empty:
                df["time"] = pd.to_datetime(df["time"])
            return df

    @with_retry(
        MT5DataError, max_retries=2, retry_if=lambda e: getattr(e, "retriable", True)
    )
    def get_tick(self, symbol: str) -> dict[str, float]:
        """Retrieve latest symbol tick."""
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        if not self.use_metaapi:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                error_code, error_desc = mt5.last_error()
                retriable = error_code in [
                    mt5.TRADE_RETCODE_CONNECTION,
                    mt5.TRADE_RETCODE_TIMEOUT,
                ]
                raise MT5DataError(
                    f"Failed to get tick: {error_desc} (code: {error_code})",
                    retriable=retriable,
                )
            return {"bid": tick.bid, "ask": tick.ask, "spread": tick.ask - tick.bid}
        else:

            async def _get_tick():
                try:
                    await self.metaapi_connection.get_symbol_specification(symbol)
                    price = await self.metaapi_connection.get_symbol_price(symbol)
                    return {
                        "bid": price["bid"],
                        "ask": price["ask"],
                        "spread": price["ask"] - price["bid"],
                    }
                except Exception as e:
                    error_msg = str(e).lower()
                    retriable = any(
                        kw in error_msg
                        for kw in ["timeout", "connection", "rate limit", "busy"]
                    )
                    raise MT5DataError(
                        f"MetaAPI tick fetch failed: {e}", retriable=retriable
                    ) from e

            return asyncio.run(_get_tick())

    @with_retry(
        MT5ExecutionError,
        max_retries=2,
        retry_if=lambda e: getattr(e, "retriable", False),
    )
    def place_order(self, signal: TradeSignal) -> int | None:
        """
        Execute a market order based on a validated trade signal.
        Retries on transient errors (requotes, price changes).

        Args:
            signal: Validated TradeSignal object.

        Returns:
            Order ticket ID if successful.

        Raises:
            MT5ExecutionError: If order placement fails permanently.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL

        if not self.use_metaapi:
            tick = self.get_tick(signal.symbol)
            price = tick["ask"] if order_type == ORDER_TYPE_BUY else tick["bid"]

            request = {
                "action": TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": signal.lot_size,
                "type": order_type,
                "price": price,
                "magic": 20240419,
                "comment": f"AI:{signal.algorithm}",
                "type_time": ORDER_TIME_GTC,
                "type_filling": ORDER_FILLING_IOC,
            }
            if signal.stop_loss:
                request["sl"] = signal.stop_loss
            if signal.take_profit:
                request["tp"] = signal.take_profit

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                retriable = result.retcode in [
                    mt5.TRADE_RETCODE_REQUOTE,
                    mt5.TRADE_RETCODE_PRICE_CHANGED,
                    mt5.TRADE_RETCODE_CONNECTION,
                    mt5.TRADE_RETCODE_TIMEOUT,
                    mt5.TRADE_RETCODE_PRICE_OFF,
                ]
                raise MT5ExecutionError(
                    f"Order rejected: {result.comment} (code: {result.retcode})",
                    retriable=retriable,
                )
            return int(result.order)
        else:

            async def _place_order():
                try:
                    action = "BUY" if signal.direction > 0 else "SELL"
                    result = await self.metaapi_connection.create_market_order(
                        signal.symbol,
                        action,
                        signal.lot_size,
                        signal.stop_loss,
                        signal.take_profit,
                        {"comment": f"AI:{signal.algorithm}"},
                    )
                    return int(result["orderId"])
                except Exception as e:
                    error_msg = str(e).lower()
                    retriable = any(
                        kw in error_msg
                        for kw in ["timeout", "connection", "rate limit", "busy"]
                    )
                    raise MT5ExecutionError(
                        f"MetaAPI order failed: {e}", retriable=retriable
                    ) from e

            return asyncio.run(_place_order())

    def get_account_info(self) -> dict[str, Any]:
        if not self._is_initialized:
            return {}
        if not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        else:
            async def _get_acc():
                return await self.metaapi_connection.get_account_information()
            return asyncio.run(_get_acc())

    def get_account_balance(self) -> float:
        """Retrieve current account balance."""
        info = self.get_account_info()
        return float(info.get("balance", 0.0))

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        if not self._is_initialized:
            return []
        if not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        else:
            async def _get_pos():
                return await self.metaapi_connection.get_positions()
            return asyncio.run(_get_pos())


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
