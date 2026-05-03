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
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import nest_asyncio
import pandas as pd

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

nest_asyncio.apply()

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

METAAPI_TIMEFRAME_MAP: Dict[str, str] = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
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
        self.metaapi_account: Optional[Any] = None
        self.metaapi_connection: Optional[Any] = None
        self._is_initialized: bool = False
        self._loop = asyncio.get_event_loop()

    def _run_async(self, coro):
        """Helper to run coroutines synchronously."""
        return self._loop.run_until_complete(coro)

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
                    password=self.cfg.mt5_password.get_secret_value(),
                    server=self.cfg.mt5_server,
                ):
                    logger.info("Native MT5 SDK initialized successfully.")
                    self.use_metaapi = False
                    self._is_initialized = True
                    return True
                else:
                    error_code, error_desc = mt5.last_error()
                    logger.warning(
                        "Native mt5.initialize failed: %s (code: %d)", error_desc, error_code
                    )

                    # Troubleshooting guidance
                    if error_code == mt5.RES_E_NOT_FOUND:
                        logger.info(
                            "TIP: MT5 terminal not found. Check if MT5_PATH is correct: %s",
                            self.cfg.mt5_path,
                        )
                    elif error_code == mt5.RES_E_INVALID_PARAMS:
                        logger.info(
                            "TIP: Invalid credentials or server name. Check MT5_LOGIN and MT5_SERVER."
                        )
                    elif error_code == mt5.RES_E_CONNECTION_FAILED:
                        logger.info(
                            "TIP: Connection failed. Check your internet or if the broker server is reachable."
                        )
                    else:
                        logger.info(
                            "TIP: Ensure the MT5 terminal is open and 'Allow Algo Trading' is enabled in options."
                        )
            except Exception as e:
                logger.error("Native MT5 initialization error: %s", e)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")
            if sys.platform == "win32":
                logger.warning(
                    "Running on Windows but 'MetaTrader5' package is missing. Install with 'pip install MetaTrader5'."
                )
            else:
                logger.info("On Linux/Mac, use MetaAPI fallback by setting METAAPI_TOKEN.")

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
                    # Use streaming connection for real-time data and faster execution
                    self.metaapi_connection = self.metaapi_account.get_streaming_connection()
                    await self.metaapi_connection.connect()
                    await self.metaapi_connection.wait_synchronized()

                self._run_async(_init_metaapi())
                self.use_metaapi = True
                self._is_initialized = True
                logger.info("MetaAPI fallback configured and synchronized.")
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
            elif self.use_metaapi and self.metaapi_connection:
                try:
                    self._run_async(self.metaapi_connection.close())
                except Exception as e:
                    logger.warning("Error closing MetaAPI connection: %s", e)
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
            return pd.DataFrame()

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None:
                logger.error("Failed to copy rates for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            try:
                ma_tf = METAAPI_TIMEFRAME_MAP.get(timeframe, "5m")

                async def _get_ma_rates():
                    # get_historical_candles returns bars in descending order of time usually?
                    # Actually MetaAPI returns them.
                    return await self.metaapi_connection.get_historical_candles(
                        symbol, ma_tf, None, n_bars
                    )

                candles = self._run_async(_get_ma_rates())
                if not candles:
                    return pd.DataFrame()
                df = pd.DataFrame(candles)
                df["time"] = pd.to_datetime(df["time"])
                # Standardize column names to match MT5 SDK output
                df = df.rename(columns={"tickVolume": "tick_volume", "realVolume": "real_volume"})
                return df
            except Exception as e:
                logger.error("MetaAPI get_rates error: %s", e)
                return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match main.py expectations."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_rates_range(
        self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a specific time range.

        Args:
            symbol: Trading symbol.
            timeframe: Chart timeframe string.
            date_from: Start of the range.
            date_to: End of the range.

        Returns:
            DataFrame containing OHLCV data.
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
            try:
                ma_tf = METAAPI_TIMEFRAME_MAP.get(timeframe, "5m")

                async def _get_ma_rates_range():
                    return await self.metaapi_connection.get_historical_candles(
                        symbol, ma_tf, date_from, n_bars=None, end_time=date_to
                    )

                candles = self._run_async(_get_ma_rates_range())
                if not candles:
                    return pd.DataFrame()
                df = pd.DataFrame(candles)
                df["time"] = pd.to_datetime(df["time"])
                df = df.rename(columns={"tickVolume": "tick_volume", "realVolume": "real_volume"})
                return df
            except Exception as e:
                logger.error("MetaAPI get_rates_range error: %s", e)
                return pd.DataFrame()

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask).

        Args:
            symbol: Trading symbol.

        Returns:
            Dictionary with 'bid' and 'ask' prices.
        """
        if not self._is_initialized:
            return {"bid": 0.0, "ask": 0.0, "spread": 0.0}

        if not self.use_metaapi:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error("Failed to get tick for %s: %s", symbol, mt5.last_error())
                return {"bid": 0.0, "ask": 0.0, "spread": 0.0}
            return {"bid": tick.bid, "ask": tick.ask, "spread": tick.ask - tick.bid}
        else:
            try:

                async def _get_ma_tick():
                    return await self.metaapi_connection.get_symbol_price(symbol)

                price = self._run_async(_get_ma_tick())
                return {
                    "bid": price["bid"],
                    "ask": price["ask"],
                    "spread": price["ask"] - price["bid"],
                }
            except Exception as e:
                logger.error("MetaAPI get_tick error: %s", e)
                return {"bid": 0.0, "ask": 0.0, "spread": 0.0}

    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """
        Execute a market order based on a validated trade signal.

        Args:
            signal: Validated TradeSignal object.

        Returns:
            Order ticket ID if successful, None otherwise.
        """
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
            try:
                side = "BUY" if signal.direction > 0 else "SELL"

                async def _place_ma_order():
                    return (
                        await self.metaapi_connection.create_market_buy_order(
                            signal.symbol,
                            signal.lot_size,
                            signal.stop_loss,
                            signal.take_profit,
                            {"comment": f"AI:{signal.algorithm}"},
                        )
                        if side == "BUY"
                        else await self.metaapi_connection.create_market_sell_order(
                            signal.symbol,
                            signal.lot_size,
                            signal.stop_loss,
                            signal.take_profit,
                            {"comment": f"AI:{signal.algorithm}"},
                        )
                    )

                result = self._run_async(_place_ma_order())
                logger.info("MetaAPI Order PLACED | ID: %s", result["orderId"])
                return int(result["orderId"])
            except Exception as e:
                logger.error("MetaAPI place_order error: %s", e)
                return None

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account balance, equity, and margin information."""
        if not self._is_initialized:
            return {}

        if not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        else:
            try:

                async def _get_ma_acc():
                    return await self.metaapi_connection.get_account_information()

                return self._run_async(_get_ma_acc())
            except Exception as e:
                logger.error("MetaAPI get_account_info error: %s", e)
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
            try:

                async def _get_ma_pos():
                    return await self.metaapi_connection.get_positions()

                positions = self._run_async(_get_ma_pos())
                if symbol:
                    positions = [p for p in positions if p["symbol"] == symbol]
                return positions
            except Exception as e:
                logger.error("MetaAPI get_positions error: %s", e)
                return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
