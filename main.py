"""
MT5 AI/ML Trading Bot - Enterprise Edition
main.py - CLI entrypoint

Usage:
    python main.py --mode demo --algo ensemble
    python main.py --mode live --algo ppo
    python main.py --mode backtest --start 2017-01-01 --end 2026-03-30

Author : triqbit
License: MIT
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import contextlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from structlog import BoundLogger
    from rich.console import Console

HAS_DEPENDENCIES = True
BOOTSTRAP_ERROR = None

try:
    import pandas as pd
    import structlog
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError as e:
    HAS_DEPENDENCIES = False
    BOOTSTRAP_ERROR = e
    Console = None
    Panel = None
    Table = None

try:
    import torch
except ImportError:
    torch = None

# -- Logging setup ---------------------------------------------------------


def configure_logging(level: str = "INFO") -> None:
    import logging
    import structlog.contextvars
    from src.core.log_config import get_masking_processor

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            get_masking_processor(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    logging.getLogger().addFilter(get_masking_processor())


# -- CLI Helpers -----------------------------------------------------------


def get_system_version() -> str:
    """Retrieve application version from src package."""
    try:
        init_path = Path(__file__).resolve().parent / "src" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r") as f:
                for line in f:
                    if "__version__" in line and "=" in line:
                        return line.split("=")[1].strip().strip("'\"")
        return "unknown"
    except Exception:
        return "unknown"


def run_setup_wizard() -> int:
    """Run the interactive configuration wizard."""
    import getpass
    from pydantic import SecretStr

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import IntPrompt, Prompt
    except ImportError:
        print("Error: 'rich' library is required for the setup wizard.")
        return 1

    console = Console()
    console.print(
        Panel(
            "[bold blue]MT5 AI/ML Trading Bot - Interactive Setup Wizard[/]\n"
            "[dim]This wizard will help you configure your .env file with essential credentials.[/]",
            border_style="blue",
        )
    )

    mode = Prompt.ask("Select execution mode", choices=["demo", "live", "backtest"], default="demo")
    symbol = Prompt.ask("Default trading symbol", default="XAUUSD").upper()
    timeframe = Prompt.ask("Default timeframe", choices=["M1", "M5", "M15", "M30", "H1", "H4", "D1"], default="M5")

    console.print("\n[bold]2. MetaTrader 5 Credentials[/]")
    login = IntPrompt.ask("MT5 Account Login (Number)", default=0)
    password_val = getpass.getpass("MT5 Account Password: ")
    password = SecretStr(password_val)
    server = Prompt.ask("MT5 Broker Server", default="YOUR_SERVER_HERE")

    if Prompt.ask("\nReady to save configuration to .env?", choices=["y", "n"], default="y") == "y":
        env_path = Path(".env")
        lines = [
            f"MT5_LOGIN={login}\n",
            f"MT5_PASSWORD={password.get_secret_value()}\n",
            f"MT5_SERVER={server}\n",
            f"SYMBOL={symbol}\n",
            f"TIMEFRAME={timeframe}\n",
            f"MODE={mode}\n",
        ]
        with open(env_path, "w") as f:
            f.writelines(lines)
        if os.name != "nt":
            os.chmod(env_path, 0o600)
        console.print("[bold green]✅ Configuration saved to .env.[/]")
    return 0


def get_parser() -> argparse.ArgumentParser:
    """Construct the main CLI argument parser."""
    p = argparse.ArgumentParser(
        description="MT5 AI/ML Trading Bot - Enterprise Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  python main.py --setup
  python main.py --check
  python main.py --mode demo --symbol XAUUSD --algo ensemble
  python main.py --mode backtest --start 2024-01-01 --end 2024-05-01 --algo ppo
        """,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {get_system_version()}")

    execution = p.add_argument_group("Execution Options")
    execution.add_argument("--mode", choices=["demo", "live", "backtest"], help="Start the bot in a specific mode (demo, live, backtest).")
    execution.add_argument("--algo", dest="algorithm", choices=["ppo", "ensemble", "lstm", "transformer"], help="Select the AI algorithm architecture to use.")
    execution.add_argument("--symbol", help="Specify the trading symbol ticker (e.g., XAUUSD).")
    execution.add_argument("--timeframe", help="Specify the chart timeframe for analysis (e.g., M5, H1).")
    execution.add_argument("--confirm-live", dest="confirm_live_trading", action="store_true", help="Confirm live trading execution.")

    # -- Backtest Group
    backtest = p.add_argument_group("Backtesting & Simulation")
    backtest.add_argument("--start", help="Historical start date for backtesting (YYYY-MM-DD).", default="2017-01-01")
    backtest.add_argument("--end", help="Historical end date for backtesting (YYYY-MM-DD).", default="2026-03-30")
    backtest.add_argument("--spread", type=float, default=0.0001, help="Specify a fixed simulated spread (as decimal).")
    backtest.add_argument("--commission", type=float, default=7.0, help="Specify commission cost per round-turn lot.")

    setup = p.add_argument_group("Setup & Diagnostics")
    setup.add_argument("--setup", action="store_true", help="Run the interactive configuration wizard to setup .env.")
    setup.add_argument("--check", action="store_true", help="Perform comprehensive pre-flight health checks and exit.")
    setup.add_argument("--doctor", action="store_true", help="Run the system diagnostic tool to verify environment.")
    setup.add_argument("--show-config", action="store_true", help="Display the current sanitized configuration and exit.")

    return p


def main() -> int:
    try:
        from rich.console import Console as RichConsole
        from rich.panel import Panel as RichPanel
        from rich.table import Table as RichTable
    except ImportError:
        RichConsole = None
        RichPanel = None
        RichTable = None

    diagnostic_flags = ["--help", "-h", "--version", "--doctor", "--setup"]
    is_diagnostic = any(arg in sys.argv for arg in diagnostic_flags)

    # 1. Secure directory initialization
    for d in ["data", "logs", "models/trained"]:
        p = Path(d)
        if os.name != "nt":
            p.mkdir(parents=True, exist_ok=True, mode=0o700)
            if p.exists():
                os.chmod(p, 0o700)
        else:
            p.mkdir(parents=True, exist_ok=True)

    if not HAS_DEPENDENCIES and not is_diagnostic:
        print("=" * 70)
        print("CRITICAL: BOOTSTRAP FAILURE - MISSING CORE DEPENDENCIES")
        print("=" * 70)
        print(f"Details: {BOOTSTRAP_ERROR}")
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python:   {sys.version.split()[0]}")
        print("\nREMEDIATION STEPS:")
        print("1. [Recommended] Run 'python3 scripts/doctor.py' to perform deep diagnostics.")
        print("2. Run 'pip install -r requirements.txt' to install all required libraries.")
        if platform.system() == "Linux":
            print("3. On Linux, if TA-Lib is missing, ensure the C-library is installed:")
            print("   'sudo apt-get install libta-lib0' or equivalent.")
        print("-" * 70)
        return 1

    parser = get_parser()
    args = parser.parse_args()

    if args.setup:
        return run_setup_wizard()

    if args.doctor:
        from scripts import doctor
        doctor.main()
        return 0

    from src.core.config import get_config
    try:
        cfg = get_config()
    except Exception as exc:
        if RichConsole:
            console = RichConsole()
            console.print(f"[bold red]CRITICAL: Configuration load failed:[/] {exc}")
        else:
            print(f"CRITICAL: Config load failed: {exc}")
        return 1

    configure_logging(cfg.log_level)
    log = structlog.get_logger("main")
    console = RichConsole() if RichConsole else None

    # Sync CLI overrides to ENV for Pydantic
    provided_dest = {action.dest for action in parser._actions if any(opt in sys.argv for opt in action.option_strings)}
    for dest in provided_dest:
        val = getattr(args, dest, None)
        if val is not None:
            os.environ[dest.upper()] = str(val)
    get_config.cache_clear()
    cfg = get_config()

    from src.core.audit_log import AuditLogger
    from src.core.monitor import Monitor
    from src.trading.mt5_connector import MT5Connector
    from src.trading.executor import TradingExecutor
    from src.trading.audited_risk_manager import AuditedRiskManager
    from src.core.trade_logger import TradeLogger
    from src.core.decision_support import DecisionSupportSystem
    from src.data.feature_engineering import FeatureEngineer
    from src.models.regime_detector import RegimeDetector
    from src.trading.execution_filter import ExecutionFilter
    from src.data.event_intelligence import EventIntelligence, TradingViewEventProvider
    from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
    from src.models.ensemble import EnsembleModel

    # Audit Trail initialization
    audit_logger = AuditLogger()
    monitor = Monitor(cfg)
    connector = MT5Connector(cfg, monitor=monitor)

    try:
        connector.connect()
    except Exception as e:
        log.critical("Failed to connect to MT5", error=str(e))
        return 1

    balance = connector.get_account_balance()
    trade_logger = TradeLogger()
    risk = AuditedRiskManager(cfg, account_balance=balance, logger_db=trade_logger, monitor=monitor)

    events = EventIntelligence(providers=[TradingViewEventProvider()], config=cfg)
    ex_filter = ExecutionFilter(config=cfg, event_intelligence=events, monitor=monitor)
    fe = FeatureEngineer(base_timeframe=cfg.timeframe)
    regime = RegimeDetector()
    allocator = CapitalAllocator(total_budget=balance, monitor=monitor)
    dss = DecisionSupportSystem()

    # Strategy registration
    allocator.add_strategy(StrategyConfig(
        strategy_id=f"{cfg.algorithm.upper()}_{cfg.symbol}",
        symbol=cfg.symbol,
        model_family=cfg.algorithm,
        capital_cap=max(0.1, balance * 0.5)
    ))

    # Model Factory
    if cfg.algorithm == "ensemble":
        model = EnsembleModel(config=cfg, monitor=monitor)
    else:
        from src.models.ppo_agent import PPOAgent
        model = PPOAgent()

    if args.check:
        log.info("Health check passed.")
        return 0

    try:
        if cfg.mode in ("demo", "live"):
            if cfg.mode == "live" and cfg.confirm_live_trading != "YES":
                log.critical("LIVE trading attempted without --confirm-live or MT5_CONFIRM_LIVE_TRADING=YES")
                return 1

            executor = TradingExecutor(
                config=cfg, connector=connector, risk=risk, model=model,
                execution_filter=ex_filter, event_intelligence=events,
                feature_engineer=fe, regime_detector=regime,
                allocator=allocator, dss=dss, trade_logger=trade_logger,
                monitor=monitor, audit_logger=audit_logger, console=console
            )
            executor.run_live()
        elif cfg.mode == "backtest":
            from src.trading.backtester import BacktestEngine
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")

            with console.status("[bold green]Fetching historical data for backtest...") if console else contextlib.nullcontext():
                df_raw = connector.get_rates_range(cfg.symbol, cfg.timeframe, start_date, end_date)

            if df_raw.empty:
                log.error("No historical data found for backtest range.")
                return 1

            engine = BacktestEngine(
                symbol=cfg.symbol, initial_balance=10000.0,
                spread=args.spread, commission_per_lot=args.commission,
                feature_engineer=fe, execution_filter=ex_filter
            )
            report = engine.run_walk_forward(df_raw, model)

            if RichTable:
                table = RichTable(title="Backtest Results", box=None)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", justify="right")
                table.add_row("Annualized Return", f"{report.annualized_return:.2%}")
                table.add_row("Sharpe Ratio", f"{report.sharpe_ratio:.2f}")
                table.add_row("Max Drawdown", f"{report.max_drawdown:.2%}")
                table.add_row("Win Rate", f"{report.win_rate:.2%}")
                table.add_row("Total Trades", str(report.total_trades))
                console.print(Panel(table, title="[bold green]Institutional Report[/]", border_style="green"))
            else:
                log.info("backtest_completed", report=report)
    finally:
        connector.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
