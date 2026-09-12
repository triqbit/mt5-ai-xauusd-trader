"""
MT5 AI/ML Trading Bot
src/trading/tickerall_backend.py

TickerAll hosted-API backend for MT5Connector - an opt-in third path alongside
the native MetaTrader5 SDK and the MetaAPI cloud fallback. When
`tickerall_api_key` is configured, the bot talks to the hosted TickerAll MT5 API
(https://tickerall.com) instead of a local terminal, so it runs on any OS with
no MetaTrader 5 installed. Every method returns data in the SAME shape as the
native / MetaAPI paths, so MT5Connector stays a drop-in.

License: MIT
"""

from __future__ import annotations

from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

from src.core.exceptions import MT5ConnectionError, MT5DataError, MT5ExecutionError

logger = structlog.get_logger(__name__)

# Timeframes the hosted API serves (superset of the bot's TIMEFRAME_MAP keys).
_TICKERALL_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}
_TF_MINUTES: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
    "MN1": 43200,
}
_MAX_RATES_FETCH = 20000
SYMBOL_TRADE_MODE_DISABLED = 0


class TickerAllBackend:
    """Serves the MT5Connector operations from the hosted TickerAll MT5 API."""

    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self._client: Any = None
        self._account_id: Optional[str] = None
        self._stream: Any = None
        self._subscribed: set[str] = set()

    # ── lifecycle ────────────────────────────────────────────────────────────
    def initialize(self) -> None:
        """Create the client and resolve the account. Raises on failure."""
        try:
            from tickerall import Tickerall
        except ImportError as e:
            raise MT5ConnectionError(
                "The 'tickerall' package is required for the TickerAll backend "
                "(pip install tickerall)."
            ) from e

        api_key = self._secret(self.cfg.tickerall_api_key)
        if not api_key:
            raise MT5ConnectionError("tickerall_api_key is not configured.")

        self._client = Tickerall(api_key=api_key)
        self._account_id = self._resolve_account()

    def _resolve_account(self) -> str:
        configured = self._secret(self.cfg.tickerall_account_id)
        if configured:
            return configured
        accounts = self._client.accounts.list()
        if len(accounts) == 1:
            return accounts[0].id
        if not accounts:
            raise MT5ConnectionError(
                "No accounts are connected to this TickerAll API key. Connect one, "
                "or set tickerall_account_id."
            )
        ids = ", ".join(f"{a.id} ({a.server})" for a in accounts)
        raise MT5ConnectionError(
            f"This TickerAll key has several accounts; set tickerall_account_id to one of: {ids}"
        )

    def shutdown(self) -> None:
        try:
            if self._stream is not None:
                self._stream.close()
                self._stream = None
            if self._client is not None:
                self._client.close()
                self._client = None
        except Exception as e:
            logger.warning("tickerall_shutdown_warning", error=str(e))

    # ── market data ──────────────────────────────────────────────────────────
    def get_rates(self, symbol: str, timeframe: str, n_bars: int) -> pd.DataFrame:
        bars = self._client.candles.get(
            self._account_id, symbol=symbol, count=n_bars, timeframe=self._tf(timeframe)
        )
        return self._candles_df(bars)

    def get_rates_range(
        self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime
    ) -> pd.DataFrame:
        tf = self._tf(timeframe)
        frm, to = self._to_epoch(date_from), self._to_epoch(date_to)
        span = max(1, (to - frm) // (_TF_MINUTES.get(tf, 1) * 60)) + 8
        bars = self._client.candles.get(
            self._account_id, symbol=symbol, count=min(span, _MAX_RATES_FETCH), timeframe=tf
        )
        bars = [b for b in bars if frm <= self._ts(b.timestamp) <= to]
        if not bars:
            raise MT5DataError(
                f"No {timeframe} bars available for {symbol} in the requested range."
            )
        return self._candles_df(bars)

    def get_ticks_range(self, symbol: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
        # Historical raw ticks are not served by the hosted API (yet). Be honest
        # rather than returning fabricated/empty data.
        raise MT5DataError(
            "Historical raw ticks are not available via the TickerAll hosted "
            "provider; use get_rates for OHLC.",
            is_retriable=False,
        )

    def get_tick(self, symbol: str) -> Dict[str, float]:
        bid, ask = self._latest_bid_ask(symbol)
        return {"bid": bid, "ask": ask, "spread": ask - bid}

    def _latest_bid_ask(self, symbol: str) -> tuple[float, float]:
        stream = self._ensure_stream()
        if symbol not in self._subscribed:
            stream.subscribe_ticks(self._account_id, [symbol])
            self._subscribed.add(symbol)
        try:
            ev = stream.wait_for_tick(symbol, account_id=self._account_id, timeout=6.0)
            return float(ev.bid), float(ev.ask)
        except Exception:
            bars = self._client.candles.get(
                self._account_id, symbol=symbol, count=1, timeframe="M1"
            )
            if bars:
                b = bars[-1]
                return float(b.bid or b.close), float(b.close)
            raise MT5DataError(f"No tick available for {symbol}.") from None

    def _ensure_stream(self) -> Any:
        if self._stream is None or not self._stream.is_connected():
            self._stream = self._client.stream.connect(timeout=15.0)
            self._subscribed = set()
        return self._stream

    # ── trading ──────────────────────────────────────────────────────────────
    def place_order(self, signal: Any) -> Optional[int]:
        side = "BUY" if signal.direction > 0 else "SELL"
        try:
            result = self._client.orders.place(
                self._account_id,
                type="market",
                symbol=signal.symbol,
                side=side,
                volume=signal.lot_size,
                stop_loss=float(signal.stop_loss) if signal.stop_loss else None,
                take_profit=float(signal.take_profit) if signal.take_profit else None,
                comment=f"AI:{signal.algorithm}",
            )
            logger.info(
                "tickerall_order_placement_success",
                symbol=signal.symbol,
                ticket=result.ticket,
            )
            return int(result.ticket)
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("unreachable", "timeout", "not hot", "connection", "503")):
                raise MT5ConnectionError(f"TickerAll connection lost during order: {e}") from e
            raise MT5ExecutionError(f"TickerAll order placement failed: {e}") from e

    # ── account / positions ──────────────────────────────────────────────────
    def get_account_info(self) -> Dict[str, Any]:
        detail = self._client.accounts.get(self._account_id)
        acc = detail.account
        if acc is None:
            raise MT5DataError(
                f"TickerAll account snapshot unavailable: {detail.hint or 'offline'}"
            )
        balance = acc.balance
        # equity/margin may be absent (None) - distinct from a real 0.0 value.
        equity = acc.equity if acc.equity is not None else balance
        margin = acc.margin if acc.margin is not None else 0.0
        margin_free = acc.free_margin if acc.free_margin is not None else equity
        digits = "".join(c for c in detail.account_number if c.isdigit())
        return {
            "login": int(digits) if digits else 0,
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "margin_free": margin_free,
            "margin_level": acc.margin_level if acc.margin_level is not None else 0.0,
            "profit": (equity - balance) if acc.equity is not None else 0.0,
            "currency": acc.currency or "",
            "leverage": acc.leverage,
            "name": acc.name,
            "server": detail.server,
            "company": acc.broker_name or detail.broker,
        }

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        detail = self._client.accounts.get(self._account_id)
        out: List[Dict[str, Any]] = []
        for p in detail.positions:
            if symbol and p.symbol != symbol:
                continue
            out.append(self._position_dict(p))
        return out

    def get_terminal_status(self) -> Dict[str, Any]:
        # Hosted API has no local terminal button; a connected session can trade.
        return {"algo_trading": True, "connected": True}

    def get_symbol_properties(self, symbol: str) -> Dict[str, Any]:
        spec = next(
            (s for s in self._client.accounts.symbol_specs(self._account_id) if s.name == symbol),
            None,
        )
        if spec is None:
            raise MT5DataError(f"Symbol {symbol} not found via TickerAll.")
        tradable = (
            True if spec.trade_mode is None else spec.trade_mode != SYMBOL_TRADE_MODE_DISABLED
        )
        return {
            "name": spec.name,
            "tradable": tradable,
            "spread": 0,
            "digits": spec.digits if spec.digits is not None else 0,
            "point": spec.point,
            "trade_contract_size": spec.contract_size,
        }

    def find_symbols(self, pattern: str) -> List[str]:
        names = self._client.accounts.symbols(self._account_id)
        glob = pattern if any(c in pattern for c in "*?[") else f"*{pattern}*"
        return [n for n in names if fnmatch(n.upper(), glob.upper())]

    # ── helpers ──────────────────────────────────────────────────────────────
    def _tf(self, timeframe: str) -> str:
        tf = str(timeframe).upper()
        if tf not in _TICKERALL_TIMEFRAMES:
            raise MT5DataError(
                f"Timeframe {timeframe} is not available via the TickerAll hosted "
                f"provider (supported: {', '.join(sorted(_TICKERALL_TIMEFRAMES))}).",
                is_retriable=False,
            )
        return tf

    @staticmethod
    def _candles_df(bars: Any) -> pd.DataFrame:
        if not bars:
            return pd.DataFrame()
        rows = [
            {
                "time": TickerAllBackend._ts(b.timestamp),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "tick_volume": b.tick_volume,
                "spread": int(b.spread) if b.spread is not None else 0,
                "real_volume": 0,
            }
            for b in sorted(bars, key=lambda x: x.timestamp)
        ]
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    @staticmethod
    def _position_dict(p: Any) -> Dict[str, Any]:
        t = TickerAllBackend._ts(p.open_time)
        return {
            "ticket": int(p.ticket),
            "time": t,
            "type": 0 if str(p.side).upper() == "BUY" else 1,
            "magic": p.magic,
            "identifier": int(p.ticket),
            "volume": p.volume,
            "price_open": p.entry_price if p.entry_price is not None else 0.0,
            "sl": p.stop_loss,
            "tp": p.take_profit,
            "price_current": p.current_price if p.current_price is not None else 0.0,
            "swap": p.swap,
            "profit": p.profit if p.profit is not None else 0.0,
            "symbol": p.symbol,
            "comment": p.comment,
        }

    @staticmethod
    def _secret(value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "get_secret_value"):
            return value.get_secret_value()
        return str(value)

    @staticmethod
    def _ts(value: Any) -> int:
        if value is None or value == "":
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _to_epoch(value: Any) -> int:
        if isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        return TickerAllBackend._ts(value)
