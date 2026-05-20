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
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import nest_asyncio

if TYPE_CHECKING:
    from src.core.monitor import Monitor
import pandas as pd
import structlog

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
from src.core.resilience import CircuitBreaker
from src.core.retry import with_retry
from src.core.schemas import TradeSignal

# Apply nest_asyncio to allow nested loops (MetaAPI SDK uses asyncio)
nest_asyncio.apply()

logger = structlog.get_logger(__name__)

# MT5 constants (replicated so the module loads on Mac/Linux)
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_TIME_GTC = 1
ORDER_FILLING_IOC = 1

# MT5 Retcodes that indicate permanent failure (no retry)
NON_RETRIABLE_RETCODES = {
    10014,  # TRADE_RETCODE_INVALID_VOLUME
    10015,  # TRADE_RETCODE_INVALID_PRICE
    10016,  # TRADE_RETCODE_INVALID_STOPS
    10017,  # TRADE_RETCODE_INVALID_FILL
    10018,  # TRADE_RETCODE_MARKET_CLOSED
    10019,  # TRADE_RETCODE_NO_MONEY
    10022,  # TRADE_RETCODE_TOO_MANY_OPEN_ORDERS
    10023,  # TRADE_RETCODE_INVALID_EXPIRATION
    10024,  # TRADE_RETCODE_ORDER_CHANGED
    10027,  # TRADE_RETCODE_NO_HISTORY
    10028,  # TRADE_RETCODE_ON_ONLY_STOPS
}

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

    def __init__(
        self, config: TradingConfig, monitor: Optional["Monitor"] = None
    ) -> None:
        """
        Initialize the connector with configuration.

        Args:
            config: TradingConfig object containing credentials and settings.
            monitor: Optional Monitor instance for observability.
        """
        self.cfg = config
        self.monitor = monitor
        self.use_metaapi: bool = False
        self.metaapi: Any | None = None
        self.metaapi_account: Any | None = None
        self.metaapi_connection: Any | None = None
        self._is_initialized: bool = False
        self._background_tasks: set[asyncio.Task] = set()

        # Circuit Breaker for connection, data retrieval and execution
        self.breaker = CircuitBreaker(
            name="MT5Connector",
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exceptions=(MT5ConnectionError, MT5DataError),
            monitor=self.monitor,
        )

    @property
    def circuit_state(self) -> str:
        """Return the current state of the circuit breaker."""
        return self.breaker.state.value

    def connect(self) -> bool:
        """Alias for initialize() to support legacy calls."""
        return self.initialize()

    def disconnect(self) -> None:
        """Alias for shutdown() to support legacy calls."""
        self.shutdown()

    @with_retry(MT5ConnectionError, max_retries=3)
    def initialize(self) -> bool:
        """
        Establish connection to MT5 terminal or MetaAPI cloud.

        Follows a dual-path strategy:
        1. Native SDK: Attempt direct connection (Windows only).
        2. MetaAPI Cloud: Fallback for Linux/Mac or remote deployments.

        Returns:
            bool: True if connection established successfully.

        Raises:
            MT5ConnectionError: If all connection paths fail after retries.
            CircuitBreakerError: If the circuit is OPEN.
        """
        # Circuit Breaker check
        return self.breaker(self._initialize_logic)()

    def _initialize_logic(self) -> bool:
        """Internal initialization logic wrapped by circuit breaker."""
        logger.info(
            "mt5_connector_initialization_started",
            mode=self.cfg.mode,
            symbol=self.cfg.symbol,
            mt5_server=self.cfg.mt5_server,
        )
        self.use_metaapi = False  # Reset state

        # 1. Attempt Native MT5 SDK (Primary Path - Windows only)
        if MT5_AVAILABLE:
            try:
                logger.debug("native_mt5_sdk_initialization_attempt")
                init_result = mt5.initialize(
                    path=self.cfg.mt5_path,
                    login=self.cfg.mt5_login,
                    password=self.cfg.mt5_password.get_secret_value(),
                    server=self.cfg.mt5_server,
                )
                if init_result:
                    logger.info(
                        "native_mt5_sdk_initialization_success",
                        server=self.cfg.mt5_server,
                        login=self.cfg.mt5_login,
                    )
                    self.use_metaapi = False
                    self._is_initialized = True
                    return True

                error_code, error_desc = mt5.last_error()
                logger.warning(
                    "native_mt5_sdk_initialization_failed",
                    error=error_desc,
                    code=error_code,
                    server=self.cfg.mt5_server,
                )
            except Exception as e:
                logger.error(
                    "native_mt5_sdk_initialization_exception",
                    error=str(e),
                    exc_info=True,
                )
        else:
            logger.info(
                "native_mt5_sdk_unavailable",
                platform=sys.platform,
                reason="SDK not imported or platform incompatible",
            )

        # 2. Attempt MetaAPI Cloud (Fallback Path - Linux/Mac/Cloud)
        metaapi_token = self.cfg.metaapi_token.get_secret_value() if self.cfg.metaapi_token else ""
        if METAAPI_AVAILABLE and metaapi_token and self.cfg.metaapi_account_id:
            logger.info("metaapi_fallback_initialization_attempt")
            try:
                self.metaapi = MetaApi(metaapi_token)

                async def _init_metaapi():
                    account_id = self.cfg.metaapi_account_id
                    if hasattr(account_id, "get_secret_value"):
                        account_id = account_id.get_secret_value()

                    logger.debug("metaapi_fetching_account", account_id=account_id)
                    self.metaapi_account = await self.metaapi.metatrader_account_api.get_account(
                        account_id
                    )

                    logger.debug("metaapi_waiting_for_connection")
                    await self.metaapi_account.wait_connected()

                    self.metaapi_connection = self.metaapi_account.get_rpc_connection()

                    logger.debug("metaapi_connecting_rpc_sync")
                    await self.metaapi_connection.connect()
                    await self.metaapi_connection.wait_synchronized()

                # Robust async execution ensuring we wait for completion
                self._run_async(_init_metaapi())

                self.use_metaapi = True
                self._is_initialized = True
                logger.info("metaapi_fallback_initialization_success")
                return True
            except Exception as e:
                logger.error("metaapi_fallback_initialization_failed", error=str(e))
                raise MT5ConnectionError(
                    f"MetaAPI initialization failed: {e}", details={"error_type": type(e).__name__}
                ) from e

        msg = "All MT5 connection paths failed. Check credentials, network, and platform availability."
        logger.error(msg)
        raise MT5ConnectionError(
            msg,
            details={
                "native_available": MT5_AVAILABLE,
                "metaapi_available": METAAPI_AVAILABLE,
                "platform": sys.platform,
            },
        )

    def shutdown(self) -> None:
        """Gracefully close all connections."""
        if self._is_initialized:
            if not self.use_metaapi and MT5_AVAILABLE:
                mt5.shutdown()
            elif self.use_metaapi and self.metaapi_connection:
                asyncio.run(self.metaapi_connection.close())
            logger.info("MT5 connector shutdown complete.")
            self._is_initialized = False

    @contextmanager
    def session(self):
        """Context manager for safe connection handling."""
        try:
            if not self._is_initialized:
                self.initialize()
            yield self
        finally:
            self.shutdown()

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Alias for get_rates() to support legacy calls."""
        return self.get_rates(symbol, timeframe, n_bars)

    def _run_async(self, coro):
        """Helper to run a coroutine in the appropriate event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # This is tricky because we want the result synchronously in this sync method.
                # nest_asyncio.apply() was called at the top, so we should be able to use asyncio.run
                # or a loop.run_until_complete if we are in a thread.
                return loop.run_until_complete(coro)
            else:
                return asyncio.run(coro)
        except RuntimeError:
            return asyncio.run(coro)

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.

        Args:
            symbol: Trading symbol (e.g., XAUUSD).
            timeframe: Chart timeframe (e.g., M5, H1).
            n_bars: Number of bars to retrieve.

        Returns:
            pd.DataFrame: OHLCV data.
        """
        return self.breaker(self._get_rates_logic)(symbol, timeframe, n_bars)

    def _get_rates_logic(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        """Internal data retrieval logic wrapped by circuit breaker."""
        if not self._is_initialized:
            logger.info("mt5_connector_auto_initialization")
            self.initialize()

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        try:
            if not self.use_metaapi:
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
                if rates is None:
                    err_code, err_desc = mt5.last_error()
                    # If it's a connection-related error, trigger re-init for next retry
                    if err_code in [-1, 10001, 10002, 10003, 10004]:
                        logger.warning(
                            "mt5_data_connection_failure",
                            error=err_desc,
                            code=err_code,
                            action="resetting_initialized_state",
                        )
                        self._is_initialized = False

                    is_retriable = err_code not in [-2, -5, 10018]  # 10018: Market closed
                    raise MT5DataError(
                        f"Failed to copy rates: {err_desc} (code: {err_code})",
                        is_retriable=is_retriable,
                    )
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                return df
            else:

                candles = self._run_async(
                    self.metaapi_connection.get_historical_candles(symbol, timeframe, None, n_bars)
                )
                df = pd.DataFrame(candles)
                if not df.empty:
                    df["time"] = pd.to_datetime(df["time"])
                return df
        except Exception as e:
            if isinstance(e, (MT5DataError, MT5ConnectionError)):
                raise
            # For unexpected exceptions that might be connection-related
            logger.exception("Unexpected error in get_rates: %s", e)
            self._is_initialized = False
            raise MT5DataError(f"Unexpected data retrieval error: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_ticks_range(
        self, symbol: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical tick data for a specific date range.

        Args:
            symbol: Trading symbol.
            date_from: Start date.
            date_to: End date.

        Returns:
            pd.DataFrame: Tick data (time, bid, ask, last, volume, etc.)
        """
        return self.breaker(self._get_ticks_range_logic)(symbol, date_from, date_to)

    def _get_ticks_range_logic(
        self, symbol: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        if not self._is_initialized:
            self.initialize()

        try:
            if not self.use_metaapi:
                # Native MT5
                ticks = mt5.copy_ticks_range(symbol, date_from, date_to, mt5.COPY_TICKS_ALL)
                if ticks is None:
                    err_code, err_desc = mt5.last_error()
                    if err_code in [-1, 10001, 10002, 10003, 10004]:
                        self._is_initialized = False
                    raise MT5DataError(f"Failed to copy ticks range: {err_desc} (code: {err_code})")
                df = pd.DataFrame(ticks)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                return df
            else:
                ticks = self._run_async(
                    self.metaapi_connection.get_historical_ticks(symbol, date_from, date_to)
                )
                df = pd.DataFrame(ticks)
                if not df.empty:
                    df["time"] = pd.to_datetime(df["time"])
                return df
        except Exception as e:
            if isinstance(e, (MT5DataError, MT5ConnectionError)):
                raise
            logger.exception("Unexpected error in get_ticks_range: %s", e)
            self._is_initialized = False
            raise MT5DataError(f"Unexpected tick range retrieval error: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_rates_range(
        self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a specific date range.

        Args:
            symbol: Trading symbol.
            timeframe: Chart timeframe.
            date_from: Start date.
            date_to: End date.

        Returns:
            pd.DataFrame: OHLCV data.
        """
        return self.breaker(self._get_rates_range_logic)(symbol, timeframe, date_from, date_to)

    def _get_rates_range_logic(
        self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        if not self._is_initialized:
            self.initialize()

        tf = TIMEFRAME_MAP.get(timeframe, 5)

        try:
            if not self.use_metaapi:
                # Native MT5 uses UTC timestamps
                rates = mt5.copy_rates_range(symbol, tf, date_from, date_to)
                if rates is None:
                    err_code, err_desc = mt5.last_error()
                    if err_code in [-1, 10001, 10002, 10003, 10004]:
                        logger.warning(
                            "mt5_connection_failure_detected",
                            code=err_code,
                            action="resetting_initialized_state",
                        )
                        self._is_initialized = False
                    raise MT5DataError(f"Failed to copy rates range: {err_desc} (code: {err_code})")
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                return df
            else:
                # MetaAPI uses ISO strings or dates
                candles = self._run_async(
                    self.metaapi_connection.get_historical_candles(
                        symbol, timeframe, date_from, date_to
                    )
                )
                df = pd.DataFrame(candles)
                if not df.empty:
                    df["time"] = pd.to_datetime(df["time"])
                return df
        except Exception as e:
            if isinstance(e, (MT5DataError, MT5ConnectionError)):
                raise
            logger.exception("unexpected_error_in_get_rates_range", error=str(e))
            self._is_initialized = False
            raise MT5DataError(f"Unexpected data range retrieval error: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_tick(self, symbol: str) -> Dict[str, float]:
        """
        Retrieve latest symbol tick.

        Args:
            symbol: Trading symbol.

        Returns:
            Dict[str, float]: Bid, Ask, and Spread.
        """
        return self.breaker(self._get_tick_logic)(symbol)

    def _get_tick_logic(self, symbol: str) -> Dict[str, float]:
        if not self._is_initialized:
            self.initialize()

        try:
            if not self.use_metaapi:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    err_code, err_desc = mt5.last_error()
                    if err_code in [-1, 10001, 10002, 10003, 10004]:
                        logger.warning(
                            "MT5 connection failure detected (code %d). Resetting...", err_code
                        )
                        self._is_initialized = False
                    is_retriable = err_code not in [-2, -5]
                    raise MT5DataError(
                        f"Failed to get_tick: {err_desc} (code: {err_code})",
                        is_retriable=is_retriable,
                    )
                return {"bid": tick.bid, "ask": tick.ask, "spread": tick.ask - tick.bid}
            else:
                price = self._run_async(self.metaapi_connection.get_symbol_price(symbol))
                return {
                    "bid": price["bid"],
                    "ask": price["ask"],
                    "spread": price["ask"] - price["bid"],
                }
        except Exception as e:
            if isinstance(e, (MT5DataError, MT5ConnectionError)):
                raise
            logger.exception("Unexpected error in get_tick: %s", e)
            self._is_initialized = False
            raise MT5DataError(f"Unexpected tick retrieval error: {e}") from e

    @with_retry((MT5ExecutionError, MT5ConnectionError), max_retries=2)
    def place_order(self, signal: TradeSignal) -> Optional[int]:
        """
        Execute a market order based on a validated trade signal.

        Args:
            signal: Validated TradeSignal object.

        Returns:
            Optional[int]: Order ticket ID if successful.

        Raises:
            MT5ConnectionError: If not initialized or blocked by breaker.
            MT5ExecutionError: If order is rejected.
            CircuitBreakerError: If the circuit is OPEN.
        """
        return self.breaker(self._place_order_logic)(signal)

    def _place_order_logic(self, signal: TradeSignal) -> Optional[int]:
        """Internal order placement logic wrapped by circuit breaker."""
        if not self._is_initialized:
            self.initialize()

        logger.info(
            "order_placement_attempt",
            symbol=signal.symbol,
            direction=signal.direction,
            lots=signal.lot_size,
            algo=signal.algorithm,
        )

        order_type = ORDER_TYPE_BUY if signal.direction > 0 else ORDER_TYPE_SELL

        if not self.use_metaapi:
            # Note: get_tick is also wrapped by the breaker
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
                request["sl"] = float(signal.stop_loss)
            if signal.take_profit:
                request["tp"] = float(signal.take_profit)

            result = mt5.order_send(request)
            if result is None:
                err_code, err_desc = mt5.last_error()
                logger.error(
                    "order_placement_failed_none",
                    error=err_desc,
                    code=err_code,
                    symbol=signal.symbol,
                )
                # We don't necessarily want execution errors to trip the connection breaker
                # unless they are connection related retcodes.
                raise MT5ExecutionError(
                    f"Order send failed (None result): {err_desc} (code: {err_code})"
                )

            if result.retcode not in [
                getattr(mt5, "TRADE_RETCODE_DONE", 10009),
                getattr(mt5, "TRADE_RETCODE_PLACED", 10008),
            ]:
                error_msg = f"Order rejected: {result.comment} (code: {result.retcode})"
                logger.error(
                    "order_placement_rejected",
                    symbol=signal.symbol,
                    comment=result.comment,
                    retcode=result.retcode,
                    deal=result.deal,
                )
                is_retriable = result.retcode not in NON_RETRIABLE_RETCODES
                raise MT5ExecutionError(error_msg, is_retriable=is_retriable)

            logger.info(
                "order_placement_success",
                symbol=signal.symbol,
                ticket=result.order,
                deal=result.deal,
                price=result.price,
            )
            return int(result.order)
        else:
            action = "BUY" if signal.direction > 0 else "SELL"
            try:
                result = self._run_async(
                    self.metaapi_connection.create_market_order(
                        signal.symbol,
                        action,
                        signal.lot_size,
                        signal.stop_loss,
                        signal.take_profit,
                        {"comment": f"AI:{signal.algorithm}"},
                    )
                )
                ticket = int(result["orderId"])
                logger.info(
                    "metaapi_order_placement_success",
                    symbol=signal.symbol,
                    ticket=ticket,
                )
                return ticket
            except Exception as e:
                logger.error(
                    "metaapi_order_placement_failed",
                    symbol=signal.symbol,
                    error=str(e),
                )
                # Check if it is a connection error for MetaAPI
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    self._is_initialized = False
                    raise MT5ConnectionError(f"MetaAPI connection lost during order: {e}") from e

                raise MT5ExecutionError(f"MetaAPI order placement failed: {e}") from e

    def get_account_balance(self) -> float:
        """Retrieve current account balance."""
        info = self.get_account_info()
        # MT5 standard field is 'balance', MetaAPI is 'balance'
        # Hardened to use direct key access so exceptions in get_account_info propagate
        # and we don't accidentally return 0.0 on hidden failure.
        return float(info["balance"])

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account information."""
        return self.breaker(self._get_account_info_logic)()

    def _get_account_info_logic(self) -> Dict[str, Any]:
        """Internal account information retrieval logic."""
        if not self._is_initialized:
            self.initialize()

        if not self.use_metaapi:
            acc = mt5.account_info()
            if acc is None:
                err_code, err_desc = mt5.last_error()
                if err_code in [-1, 10001, 10002, 10003, 10004]:
                    self._is_initialized = False
                raise MT5DataError(f"Failed to get account info: {err_desc} (code: {err_code})")
            return acc._asdict()
        else:
            try:
                return self._run_async(self.metaapi_connection.get_account_information())
            except Exception as e:
                self._is_initialized = False
                raise MT5DataError(f"MetaAPI get_account_information failed: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve open positions."""
        return self.breaker(self._get_positions_logic)(symbol)

    def _get_positions_logic(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Internal positions retrieval logic."""
        if not self._is_initialized:
            self.initialize()

        if not self.use_metaapi:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if positions is None:
                err_code, err_desc = mt5.last_error()
                if err_code in [-1, 10001, 10002, 10003, 10004]:
                    self._is_initialized = False
                raise MT5DataError(f"Failed to get positions: {err_desc} (code: {err_code})")
            return [p._asdict() for p in positions]
        else:
            try:
                return self._run_async(self.metaapi_connection.get_positions())
            except Exception as e:
                self._is_initialized = False
                raise MT5DataError(f"MetaAPI get_positions failed: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_terminal_status(self) -> Dict[str, Any]:
        """
        Retrieve terminal status (e.g., algo trading enabled).
        Ensures a consistent 'algo_trading' key is present.
        """
        return self.breaker(self._get_terminal_status_logic)()

    def _get_terminal_status_logic(self) -> Dict[str, Any]:
        """Internal terminal status retrieval logic."""
        if not self._is_initialized:
            self.initialize()

        if not self.use_metaapi:
            info = mt5.terminal_info()
            if not info:
                err_code, err_desc = mt5.last_error()
                if err_code in [-1, 10001, 10002, 10003, 10004]:
                    self._is_initialized = False
                raise MT5DataError(f"Failed to get terminal status: {err_desc} (code: {err_code})")
            data = info._asdict()
            # Map 'trade_allowed' (terminal-wide algo trading button) to 'algo_trading' for clarity
            if "trade_allowed" in data:
                data["algo_trading"] = data["trade_allowed"]
            return data
        else:
            # MetaAPI doesn't have a direct equivalent for terminal 'algo_trading' button
            # but we assume it's true if we can connect and synchronize.
            return {"algo_trading": True}

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def get_symbol_properties(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve symbol properties."""
        return self.breaker(self._get_symbol_properties_logic)(symbol)

    def _get_symbol_properties_logic(self, symbol: str) -> Dict[str, Any]:
        """Internal symbol properties retrieval logic."""
        if not self._is_initialized:
            self.initialize()

        if not self.use_metaapi:
            info = mt5.symbol_info(symbol)
            if not info:
                err_code, err_desc = mt5.last_error()
                if err_code in [-1, 10001, 10002, 10003, 10004]:
                    self._is_initialized = False
                raise MT5DataError(f"Failed to get symbol info for {symbol}: {err_desc} (code: {err_code})")
            return {
                "name": info.name,
                "tradable": info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED,
                "spread": info.spread,
                "digits": info.digits,
                "point": info.point,
                "trade_contract_size": info.trade_contract_size,
            }
        else:
            try:
                spec = self._run_async(self.metaapi_connection.get_symbol_specification(symbol))
                return {
                    "name": spec["symbol"],
                    "tradable": True,
                    "spread": 0,
                    "digits": spec["digits"],
                    "point": spec.get("point"),
                    "pip_size": spec.get("pipSize"),
                    "trade_contract_size": spec.get("contractSize"),
                }
            except Exception as e:
                self._is_initialized = False
                raise MT5DataError(f"MetaAPI get_symbol_specification failed for {symbol}: {e}") from e

    @with_retry((MT5DataError, MT5ConnectionError), max_retries=3)
    def find_symbols(self, pattern: str) -> List[str]:
        """Find symbols matching a pattern."""
        return self.breaker(self._find_symbols_logic)(pattern)

    def _find_symbols_logic(self, pattern: str) -> List[str]:
        """Internal symbols discovery logic."""
        if not self._is_initialized:
            self.initialize()

        if not self.use_metaapi:
            symbols = mt5.symbols_get(pattern)
            if symbols is None:
                err_code, err_desc = mt5.last_error()
                if err_code in [-1, 10001, 10002, 10003, 10004]:
                    self._is_initialized = False
                raise MT5DataError(f"Failed to find symbols with pattern {pattern}: {err_desc} (code: {err_code})")
            return [s.name for s in symbols]
        else:
            # For MetaAPI, we'd need to fetch all and filter, which is slow.
            # Return empty or a simple guess.
            return [pattern.upper()]


__all__ = ["TIMEFRAME_MAP", "MT5Connector"]
