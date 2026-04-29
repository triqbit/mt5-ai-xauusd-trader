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
                    error_code, error_desc = mt5.last_error()
                    logger.error(f"Native MT5 initialization failed | Error: {error_code} ({error_desc})")
                    print("\n ❌ MT5 CONNECTION ERROR")
                    print(f" Error Code: {error_code}")
                    print(f" Description: {error_desc}")
                    print("\n Troubleshooting tips:")
                    print(f" 1. Ensure MT5 terminal path is correct: {self.cfg.mt5_path}")
                    print(f" 2. Check if account {self.cfg.mt5_login} exists on server {self.cfg.mt5_server}")
                    print(" 3. Verify that the MT5 terminal is actually running or can be launched.")
                    print(" 4. On Linux/Mac, ensure you have configured MetaAPI fallback if not using Windows.")
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
                logger.info("MetaAPI fallback configured.")
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

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve current open positions."""
        if self._is_initialized and not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        return []


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
