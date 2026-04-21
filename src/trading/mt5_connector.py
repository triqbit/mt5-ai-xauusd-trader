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
        self.metaapi_account: Optional[Any] = None
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

                async def setup_metaapi():
                    account = await self.metaapi.metatrader_account_api.get_account(self.cfg.metaapi_account_id)
                    await account.wait_until_connected()
                    return account, account.get_streaming_connection()

                loop = self._get_or_create_loop()
                self.metaapi_account, self.metaapi_connection = loop.run_until_complete(setup_metaapi())

                self.use_metaapi = True
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
            elif self.use_metaapi and self.metaapi_connection:
                loop = self._get_or_create_loop()
                loop.run_until_complete(self.metaapi_connection.close())
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

        tf_value = TIMEFRAME_MAP.get(timeframe, 5)

        if not self.use_metaapi:
            # Native MT5 uses the mapped integer value
            rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, n_bars)
            if rates is None:
                logger.error("Failed to copy rates for %s: %s", symbol, mt5.last_error())
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            async def fetch_metaapi_rates():
                # MetaAPI timeframe format is usually like '1m', '5m', '1h'
                ma_tf = timeframe.lower()
                if not any(ma_tf.endswith(suffix) for suffix in ['m', 'h', 'd']):
                    ma_tf = f"{tf_value}m" if tf_value < 60 else f"{tf_value//60}h"

                candles = await self.metaapi_account.get_historical_candles(symbol, ma_tf, limit=n_bars)
                return candles

            try:
                loop = self._get_or_create_loop()
                candles = loop.run_until_complete(fetch_metaapi_rates())
                df = pd.DataFrame(candles)
                if not df.empty:
                    # MetaAPI response mapping
                    df.rename(columns={'time': 'time', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'tick_volume'}, inplace=True)
                    df["time"] = pd.to_datetime(df["time"])
                return df
            except Exception as e:
                logger.error("MetaAPI get_rates failed: %s", e)
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
        if not self._is_initialized:
            return {"bid": 0.0, "ask": 0.0}

        if not self.use_metaapi:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error("Failed to get tick for %s: %s", symbol, mt5.last_error())
                return {"bid": 0.0, "ask": 0.0}
            return {"bid": tick.bid, "ask": tick.ask}
        else:
            async def fetch_metaapi_tick():
                price = await self.metaapi_account.get_symbol_price(symbol)
                return price

            try:
                loop = self._get_or_create_loop()
                price = loop.run_until_complete(fetch_metaapi_tick())
                return {"bid": price['bid'], "ask": price['ask']}
            except Exception as e:
                logger.error("MetaAPI get_tick failed: %s", e)
                return {"bid": 0.0, "ask": 0.0}

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
            async def execute_metaapi_order():
                action = 'BUY' if signal.direction > 0 else 'SELL'
                result = await self.metaapi_account.execute_market_order(
                    signal.symbol, action, signal.lot_size, signal.stop_loss, signal.take_profit,
                    {'comment': f"AI:{signal.algorithm}", 'magic': 20240419}
                )
                return result

            try:
                loop = self._get_or_create_loop()
                result = loop.run_until_complete(execute_metaapi_order())
                logger.info("MetaAPI Order PLACED | Ticket #%s | %s", result['orderId'], signal.symbol)
                return int(result['orderId'])
            except Exception as e:
                logger.error("MetaAPI place_order failed: %s", e)
                return None

    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account balance, equity, and margin information."""
        if not self._is_initialized:
            return {}

        if not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        else:
            async def fetch_metaapi_account():
                return await self.metaapi_account.get_account_information()

            try:
                loop = self._get_or_create_loop()
                return loop.run_until_complete(fetch_metaapi_account())
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
            async def fetch_metaapi_positions():
                return await self.metaapi_account.get_positions()

            try:
                loop = self._get_or_create_loop()
                positions = loop.run_until_complete(fetch_metaapi_positions())
                normalized = []
                for p in positions:
                    if symbol and p['symbol'] != symbol:
                        continue
                    normalized.append({
                        'ticket': int(p['id']),
                        'symbol': p['symbol'],
                        'volume': p['volume'],
                        'type': 0 if p['type'] == 'POSITION_TYPE_BUY' else 1,
                        'price_open': p['openPrice'],
                        'sl': p.get('stopLoss', 0),
                        'tp': p.get('takeProfit', 0),
                        'profit': p['profit']
                    })
                return normalized
            except Exception as e:
                logger.error("MetaAPI get_positions failed: %s", e)
                return []

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """Helper to safely get or create an event loop."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
