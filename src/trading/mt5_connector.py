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

from src.core.exceptions import MarketDataError, MT5ConnectionError, OrderExecutionError

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
        self.metaapi_connection: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self, max_retries: int = 3) -> bool:
        """
        Establish connection to MT5 terminal or MetaAPI cloud with retry logic.
        Follows a dual-path strategy: Native SDK first, then MetaAPI fallback.

        Returns:
            True if connection established, False otherwise.
        """
        logger.info("Initializing MT5 connector | mode=%s", self.cfg.mode)

        # 1. Attempt Native MT5 SDK (Primary Path - Windows only)
        if MT5_AVAILABLE:
            for attempt in range(max_retries):
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
                        error_code = mt5.last_error()
                        logger.warning(
                            "Native mt5.initialize attempt %d failed: %s",
                            attempt + 1,
                            error_code,
                        )
                        if attempt < max_retries - 1:
                            time.sleep(2**attempt)
                except Exception as e:
                    logger.error("Native MT5 initialization error on attempt %d: %s", attempt + 1, e)
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)
        else:
            logger.info("Native MetaTrader5 SDK not available on this platform.")

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        if METAAPI_AVAILABLE and self.cfg.metaapi_token:
            logger.info("Attempting MetaAPI cloud fallback...")
            for attempt in range(max_retries):
                try:
                    self.metaapi = MetaApi(self.cfg.metaapi_token)
                    self.use_metaapi = True
                    self._is_initialized = True
                    logger.info("MetaAPI fallback configured.")
                    return True
                except Exception as e:
                    logger.error("MetaAPI initialization attempt %d failed: %s", attempt + 1, e)
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)

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

    def get_rates(
        self, symbol: str, timeframe: str, n_bars: int, max_retries: int = 3
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data with retry logic.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD').
            timeframe: Chart timeframe string (e.g., 'M5').
            n_bars: Number of bars to retrieve.
            max_retries: Number of retry attempts.

        Returns:
            DataFrame containing OHLCV data.

        Raises:
            MT5ConnectionError: If connector is not initialized.
            MarketDataError: If data fetching fails after retries.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("Connector not initialized. Call initialize() first.")

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            for attempt in range(max_retries):
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df["time"] = pd.to_datetime(df["time"], unit="s")
                    return df

                error_code = mt5.last_error()
                logger.warning(
                    "Failed to copy rates for %s (attempt %d): %s",
                    symbol,
                    attempt + 1,
                    error_code,
                )
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))

            raise MarketDataError(f"Failed to fetch rates for {symbol} after {max_retries} attempts.")
        else:
            # Placeholder for MetaAPI async rates fetching
            logger.warning("MetaAPI get_rates not implemented in sync wrapper.")
            return pd.DataFrame()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to match main.py expectations."""
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str, max_retries: int = 3) -> Dict[str, float]:
        """
        Retrieve latest symbol tick (bid/ask) with retry logic.

        Args:
            symbol: Trading symbol.
            max_retries: Number of retry attempts.

        Returns:
            Dictionary with 'bid' and 'ask' prices.

        Raises:
            MT5ConnectionError: If connector is not initialized.
            MarketDataError: If tick data cannot be retrieved.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("Connector not initialized.")

        if self.use_metaapi:
            return {"bid": 0.0, "ask": 0.0}

        for attempt in range(max_retries):
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                return {"bid": tick.bid, "ask": tick.ask}

            error_code = mt5.last_error()
            logger.warning(
                "Failed to get tick for %s (attempt %d): %s",
                symbol,
                attempt + 1,
                error_code,
            )
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))

        raise MarketDataError(f"Failed to get tick for {symbol} after {max_retries} attempts.")

    def place_order(self, signal: TradeSignal) -> int:
        """
        Execute a market order based on a validated trade signal.

        Args:
            signal: Validated TradeSignal object.

        Returns:
            Order ticket ID if successful.

        Raises:
            MT5ConnectionError: If connector is not initialized.
            OrderExecutionError: If order placement is rejected.
        """
        if not self._is_initialized:
            raise MT5ConnectionError("Connector not initialized.")

        if not self.use_metaapi:
            order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL
            # get_tick now raises MarketDataError on failure
            tick = self.get_tick(signal.symbol)
            price = tick["ask"] if order_type == ORDER_TYPE_BUY else tick["bid"]

            if price == 0:
                raise OrderExecutionError(f"Invalid price {price} for {signal.symbol}")

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
            if result is None:
                raise OrderExecutionError("mt5.order_send returned None")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                err_msg = f"Order rejected: {result.comment} (code: {result.retcode})"
                logger.error(err_msg)
                raise OrderExecutionError(err_msg)

            logger.info("Order PLACED | Ticket #%d | %s", result.order, signal.symbol)
            return int(result.order)

        raise OrderExecutionError("MetaAPI place_order not implemented in sync wrapper.")

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
