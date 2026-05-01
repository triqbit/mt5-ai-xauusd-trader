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
from typing import Any, Dict, List, Optional, Callable, Awaitable, TypeVar

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

T = TypeVar("T")

# MetaAPI timeframe mapping
META_TIMEFRAME_MAP: Dict[str, str] = {
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
        """Initialize the connector with configuration."""
        self.cfg = config
        self.use_metaapi: bool = False
        self.metaapi: Optional[Any] = None
        self.metaapi_account: Optional[Any] = None
        self.metaapi_connection: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self) -> bool:
        """Establish connection to MT5 or MetaAPI."""
        logger.info("Initializing MT5 connector | mode=%s", self.cfg.mode)

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

        if METAAPI_AVAILABLE and self.cfg.metaapi_token and self.cfg.metaapi_account_id:
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
        return self.initialize()

    def shutdown(self) -> None:
        if self._is_initialized:
            if not self.use_metaapi and MT5_AVAILABLE:
                mt5.shutdown()
            logger.info("MT5 connector shutdown complete.")
            self._is_initialized = False

    def disconnect(self) -> None:
        self.shutdown()

    @contextmanager
    def session(self):
        try:
            if not self._is_initialized:
                self.initialize()
            yield self
        finally:
            self.shutdown()

    def _run_async(self, coro: Awaitable[T]) -> T:
        """Helper to run async code in a synchronous context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    async def _get_metaapi_connection(self):
        if not self.metaapi: return None
        if not self.metaapi_account:
            self.metaapi_account = await self.metaapi.metatrader_account_api.get_account(
                self.cfg.metaapi_account_id
            )
        if not self.metaapi_connection:
            self.metaapi_connection = self.metaapi_account.get_rpc_connection()
            await self.metaapi_connection.connect()
            await self.metaapi_connection.wait_synchronized()
        return self.metaapi_connection

    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        if not self._is_initialized: return pd.DataFrame()

        if not self.use_metaapi:
            # We map strings to MT5 constants. Default to M5 if not found.
            # Using int values directly for robustness if mt5 module is mocked.
            tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
            tf = tf_map.get(timeframe, 5)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None: return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        else:
            async def _fetch():
                conn = await self._get_metaapi_connection()
                meta_tf = META_TIMEFRAME_MAP.get(timeframe, "5m")
                return await conn.get_historical_candles(symbol, meta_tf, None, n_bars)

            candles = self._run_async(_fetch())
            if not candles: return pd.DataFrame()
            df = pd.DataFrame(candles)
            df.rename(columns={"tickVolume": "tick_volume"}, inplace=True)
            df["time"] = pd.to_datetime(df["time"])
            return df

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        return self.get_rates(symbol, timeframe, n_bars)

    def get_tick(self, symbol: str) -> Dict[str, float]:
        if not self._is_initialized: return {"bid": 0.0, "ask": 0.0}

        if not self.use_metaapi:
            tick = mt5.symbol_info_tick(symbol)
            return {"bid": tick.bid, "ask": tick.ask} if tick else {"bid": 0.0, "ask": 0.0}
        else:
            async def _fetch():
                conn = await self._get_metaapi_connection()
                return await conn.get_symbol_price(symbol)
            p = self._run_async(_fetch())
            return {"bid": p["bid"], "ask": p["ask"]}

    def place_order(self, signal: TradeSignal) -> Optional[int]:
        if not self._is_initialized or signal.direction == 0: return None

        if not self.use_metaapi:
            order_type = mt5.ORDER_TYPE_BUY if signal.direction > 0 else mt5.ORDER_TYPE_SELL
            tick = self.get_tick(signal.symbol)
            price = tick["ask"] if signal.direction > 0 else tick["bid"]

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": signal.lot_size,
                "type": order_type,
                "price": price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "magic": 20240419,
                "comment": f"AI:{signal.algorithm}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return int(result.order)
            return None
        else:
            async def _execute():
                conn = await self._get_metaapi_connection()
                # MetaAPI uses a generic create_market_order or specific helpers
                # We'll use the documented generic method for safety
                order_type = "ORDER_TYPE_BUY" if signal.direction > 0 else "ORDER_TYPE_SELL"
                return await conn.create_market_order(
                    symbol=signal.symbol,
                    side="BUY" if signal.direction > 0 else "SELL",
                    volume=signal.lot_size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    comment=f"AI:{signal.algorithm}"
                )
            res = self._run_async(_execute())
            return int(res["orderId"]) if res and "orderId" in res else None

    def get_account_info(self) -> Dict[str, Any]:
        if not self._is_initialized: return {}
        if not self.use_metaapi:
            acc = mt5.account_info()
            return acc._asdict() if acc else {}
        else:
            async def _fetch():
                conn = await self._get_metaapi_connection()
                return await conn.get_account_information()
            return self._run_async(_fetch())

    def get_account_balance(self) -> float:
        return float(self.get_account_info().get("balance", 0.0))

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._is_initialized: return []
        if not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            return [p._asdict() for p in positions] if positions else []
        else:
            async def _fetch():
                conn = await self._get_metaapi_connection()
                return await conn.get_positions()
            p = self._run_async(_fetch())
            return [x for x in p if x["symbol"] == symbol] if symbol else p


__all__ = ["MT5Connector"]
