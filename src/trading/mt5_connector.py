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
import time
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
        self.metaapi_connection: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self, retries: int = 3, delay: int = 2) -> bool:
        """
        Establish connection to MT5 terminal or MetaAPI cloud.
        Follows a dual-path strategy: Native SDK first, then MetaAPI fallback.

        Args:
            retries: Number of retries for connection attempts.
            delay: Delay in seconds between retries.

        Returns:
            True if connection established, False otherwise.
        """
        logger.info("Initializing MT5 connector | mode=%s", self.cfg.mode)

        # 1. Attempt Native MT5 SDK (Primary Path - Windows only)
        if MT5_AVAILABLE:
            for attempt in range(1, retries + 1):
                try:
                    if mt5.initialize(
                        path=self.cfg.mt5_path,
                        login=self.cfg.mt5_login,
                        password=self.cfg.mt5_password,
                        server=self.cfg.mt5_server,
                    ):
                        logger.info("Native MT5 SDK initialized successfully (Attempt %d).", attempt)
                        self.use_metaapi = False
                        self._is_initialized = True
                        return True
                    else:
                        logger.warning("Native mt5.initialize failed (Attempt %d): %s", attempt, mt5.last_error())
                except Exception as e:
                    logger.error("Native MT5 initialization error (Attempt %d): %s", attempt, e)

                if attempt < retries:
                    time.sleep(delay)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        if METAAPI_AVAILABLE and self.cfg.metaapi_token:
            logger.info("Attempting MetaAPI cloud fallback...")
            for attempt in range(1, retries + 1):
                try:
                    self.metaapi = MetaApi(self.cfg.metaapi_token)
                    self.use_metaapi = True
                    self._is_initialized = True
                    logger.info("MetaAPI fallback configured (Attempt %d).", attempt)
                    return True
                except Exception as e:
                    logger.error("MetaAPI initialization failed (Attempt %d): %s", attempt, e)

                if attempt < retries:
                    time.sleep(delay)

        logger.error("All MT5 connection paths failed.")
        return False

    def health_check(self) -> bool:
        """
        Check the status of the connection.

        Returns:
            True if connection is healthy, False otherwise.
        """
        if not self._is_initialized:
            return False

        if not self.use_metaapi:
            # Native SDK health check
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.error("Health check failed: terminal_info is None")
                return False
            if not terminal_info.connected:
                logger.warning("Health check: terminal is not connected to broker")
                return False
            return True
        else:
            # MetaAPI health check placeholder
            # In a real implementation, we would check the MetaAPI connection status
            return self.metaapi is not None

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

        tf_code = TIMEFRAME_MAP.get(timeframe)
        if tf_code is None:
            logger.error("Invalid timeframe: %s", timeframe)
            return pd.DataFrame()

        if not self.use_metaapi:
            rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, n_bars)
            if rates is None:
                logger.error("Failed to copy rates for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            # Placeholder for MetaAPI async rates fetching
            logger.warning("MetaAPI get_rates not implemented in sync wrapper.")
            return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match main.py expectations."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask).

        Args:
            symbol: Trading symbol.

        Returns:
            Dictionary with 'bid' and 'ask' prices.
        """
        if not self._is_initialized or self.use_metaapi:
            return {"bid": 0.0, "ask": 0.0}

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error("Failed to get tick for %s: %s", symbol, mt5.last_error())
            return {"bid": 0.0, "ask": 0.0}

        return {"bid": tick.bid, "ask": tick.ask}

    def place_order(self, request: Dict[str, Any]) -> Optional[int]:
        """
        Execute an order.

        Args:
            request: Order request dictionary.

        Returns:
            Order ticket ID if successful, None otherwise.
        """
        if not self._is_initialized:
            return None

        if not self.use_metaapi:
            result = mt5.order_send(request)
            if result is None:
                logger.error("order_send returned None")
                return None
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Order rejected: %s (code: %d)", result.comment, result.retcode)
                return None

            logger.info("Order PLACED | Ticket #%d", result.order)
            return int(result.order)

        return None

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

    def get_account_equity(self) -> float:
        """Retrieve current account equity."""
        info = self.get_account_info()
        return float(info.get("equity", 0.0))

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve current open positions."""
        if self._is_initialized and not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
