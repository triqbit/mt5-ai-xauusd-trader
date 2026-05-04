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
import sys
from contextlib import contextmanager
from datetime import datetime
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
from src.core.exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5ExecutionError,
)
from src.core.retry import with_retry
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
        self.metaapi_connection: Optional[Any] = None
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
                logger.warning(
                    "Native MT5 initialization encountered an error: %s. Attempting fallback if available.",
                    e,
                )
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
        if METAAPI_AVAILABLE and metaapi_token:
            logger.info("Attempting MetaAPI cloud fallback...")
            try:
                self.metaapi = MetaApi(metaapi_token)
                self.use_metaapi = True
                self._is_initialized = True
                logger.info("MetaAPI fallback configured.")
                return True
            except Exception as e:
                logger.error("MetaAPI initialization failed: %s", e)
                # We raise MT5ConnectionError here to trigger the retry decorator
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

    @with_retry(MT5DataError, max_retries=3)
    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD').
            timeframe: Chart timeframe string (e.g., 'M5').
            n_bars: Number of bars to retrieve.

        Returns:
            DataFrame containing OHLCV data.

        Raises:
            MT5DataError: If data retrieval fails.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None:
                error_msg = f"Failed to copy rates for {symbol}: {mt5.last_error()}"
                logger.error(error_msg)
                raise MT5DataError(error_msg)
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            # Placeholder for MetaAPI async rates fetching
            logger.warning("MetaAPI get_rates not implemented in sync wrapper.")
            raise MT5DataError("MetaAPI get_rates not implemented.")

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
            logger.warning("MetaAPI get_rates_range not implemented.")
            return pd.DataFrame()

    @with_retry(MT5DataError, max_retries=2)
    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask).

        Args:
            symbol: Trading symbol.

        Returns:
            Dictionary with 'bid' and 'ask' prices.

        Raises:
            MT5DataError: If tick retrieval fails.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        if self.use_metaapi:
            raise MT5DataError("MetaAPI get_tick not implemented.")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            error_msg = f"Failed to get tick for {symbol}: {mt5.last_error()}"
            logger.error(error_msg)
            raise MT5DataError(error_msg)

        # Calculate spread in price units
        spread = tick.ask - tick.bid

        return {"bid": tick.bid, "ask": tick.ask, "spread": spread}

    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """
        Execute a market order based on a validated trade signal.

        Args:
            signal: Validated TradeSignal object.

        Returns:
            Order ticket ID if successful.

        Raises:
            MT5ExecutionError: If order placement fails.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("MT5 connector not initialized.")

        if not self.use_metaapi:
            order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL
            try:
                tick = self.get_tick(signal.symbol)
            except MT5DataError as e:
                raise MT5ExecutionError(
                    f"Cannot place order due to tick retrieval failure: {e}"
                ) from e

            price = tick["ask"] if order_type == ORDER_TYPE_BUY else tick["bid"]

            if price == 0:
                raise MT5ExecutionError("Invalid price (0.0) for order execution.")

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
                error_msg = f"Order rejected: {result.comment} (code: {result.retcode})"
                logger.error(error_msg)
                raise MT5ExecutionError(error_msg)

            logger.info("Order PLACED | Ticket #%d | %s", result.order, signal.symbol)
            return int(result.order)

        raise MT5ExecutionError("MetaAPI place_order not implemented.")

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account balance, equity, and margin information."""
        if self._is_initialized and not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        return {}

    def get_account_balance(self) -> float:
        """Retrieve current account balance."""
        info = self.get_account_info()
        return float(info.get("balance", 0.0))

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve current open positions."""
        if self._is_initialized and not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
