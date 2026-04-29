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
from src.core.error_handler import CircuitBreaker
from src.core.exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5ExecutionError,
)
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

        # Circuit Breakers for different paths
        self.cb_native = CircuitBreaker("MT5-Native", failure_threshold=3, recovery_timeout=60)
        self.cb_metaapi = CircuitBreaker("MetaAPI-Cloud", failure_threshold=3, recovery_timeout=60)

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
                return self.cb_native.call(self._initialize_native)
            except Exception as e:
                logger.error("Native MT5 initialization failed through Circuit Breaker: %s", e)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        if METAAPI_AVAILABLE and self.cfg.metaapi_token:
            try:
                return self.cb_metaapi.call(self._initialize_metaapi)
            except Exception as e:
                logger.error("MetaAPI initialization failed through Circuit Breaker: %s", e)

        logger.error("All MT5 connection paths failed.")
        return False

    def _initialize_native(self) -> bool:
        """Internal method for native MT5 initialization with retries."""
        for attempt in range(3):
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
                    err_code, err_msg = mt5.last_error()
                    logger.warning("Native mt5.initialize attempt %d failed: %s (%d)", attempt + 1, err_msg, err_code)
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception as e:
                logger.error("Native MT5 initialization error on attempt %d: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise MT5ConnectionError("Failed to initialize native MT5 after retries")

    def _initialize_metaapi(self) -> bool:
        """Internal method for MetaAPI initialization."""
        logger.info("Attempting MetaAPI cloud fallback...")
        try:
            self.metaapi = MetaApi(self.cfg.metaapi_token)
            self.use_metaapi = True
            self._is_initialized = True
            logger.info("MetaAPI fallback configured.")
            return True
        except Exception as e:
            raise MT5ConnectionError(f"MetaAPI initialization failed: {e}")

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
        Fetch historical OHLCV data with error handling.
        """
        if not self._is_initialized:
            logger.warning("Attempted get_rates while not initialized.")
            return pd.DataFrame()

        try:
            if not self.use_metaapi:
                return self.cb_native.call(self._get_rates_native, symbol, timeframe, n_bars)
            else:
                return self.cb_metaapi.call(self._get_rates_metaapi, symbol, timeframe, n_bars)
        except Exception as e:
            logger.error("Failed to fetch rates for %s: %s", symbol, e)
            return pd.DataFrame()

    def _get_rates_native(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        tf = TIMEFRAME_MAP.get(timeframe, 5)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
        if rates is None:
            err_code, err_msg = mt5.last_error()
            raise MT5DataError(f"Failed to copy rates for {symbol}: {err_msg} ({err_code})")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def _get_rates_metaapi(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        # Placeholder for MetaAPI async rates fetching
        logger.warning("MetaAPI get_rates not implemented in sync wrapper.")
        return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match main.py expectations."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask).
        """
        if not self._is_initialized:
            return {"bid": 0.0, "ask": 0.0}

        try:
            if not self.use_metaapi:
                return self.cb_native.call(self._get_tick_native, symbol)
            else:
                return {"bid": 0.0, "ask": 0.0} # Placeholder
        except Exception as e:
            logger.error("Failed to get tick for %s: %s", symbol, e)
            return {"bid": 0.0, "ask": 0.0}

    def _get_tick_native(self, symbol: str) -> Dict[str, float]:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            err_code, err_msg = mt5.last_error()
            raise MT5DataError(f"Failed to get tick for {symbol}: {err_msg} ({err_code})")
        return {"bid": tick.bid, "ask": tick.ask}

    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """
        Execute a market order based on a validated trade signal.
        """
        if not self._is_initialized:
            return None

        try:
            if not self.use_metaapi:
                return self.cb_native.call(self._place_order_native, signal)
            else:
                return None # Placeholder
        except Exception as e:
            logger.error("Order execution failed: %s", e)
            return None

    def _place_order_native(self, signal: TradeSignal) -> Optional[int]:
        order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL
        tick = self._get_tick_native(signal.symbol)
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
            raise MT5ExecutionError(f"Order rejected: {result.comment} (code: {result.retcode})")

        logger.info("Order PLACED | Ticket #%d | %s", result.order, signal.symbol)
        return int(result.order)

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account balance, equity, and margin information."""
        if self._is_initialized and not self.use_metaapi:
            try:
                acc = mt5.account_info()
                return acc._asdict() if acc else {}
            except Exception:
                return {}
        return {}

    def get_account_balance(self) -> float:
        """Retrieve current account balance."""
        info = self.get_account_info()
        return float(info.get("balance", 0.0))

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve current open positions."""
        if self._is_initialized and not self.use_metaapi:
            try:
                positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
                return [p._asdict() for p in positions] if positions else []
            except Exception:
                return []
        return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
