"""
MT5 AI/ML Trading Bot - CLI Commands
src/cli/commands.py
Enhanced CLI using Click and Rich.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.core.config import get_config
from src.core.trade_logger import Trade, TradeLogger
from src.trading.mt5_connector import MT5Connector

console = Console()

@click.group()
def cli():
    """MT5 AI/ML Trading Bot CLI"""
    pass

@cli.command()
def status():
    """Show system health and current positions."""
    cfg = get_config()
    connector = MT5Connector(cfg)

    with console.status("[bold green]Checking system status..."):
        connected = connector.connect()
        balance = 0.0
        positions = []
        if connected:
            balance = connector.get_account_balance()
            positions = connector.get_positions()
            connector.disconnect()

    # System Health Panel
    health_table = Table(show_header=False, box=None)
    health_table.add_row("MT5 Connection", "[green]CONNECTED[/]" if connected else "[red]DISCONNECTED[/]")
    health_table.add_row("Account Balance", f"${balance:,.2f}")
    health_table.add_row("Mode", cfg.mode.upper())
    health_table.add_row("Symbol", cfg.symbol)

    console.print(Panel(health_table, title="[bold]System Health[/]", expand=False))

    # Positions Table
    pos_table = Table(title="Open Positions")
    pos_table.add_column("Ticket", justify="right", style="cyan")
    pos_table.add_column("Symbol", style="magenta")
    pos_table.add_column("Type", justify="center")
    pos_table.add_column("Volume", justify="right")
    pos_table.add_column("Price", justify="right")
    pos_table.add_column("Profit", justify="right", style="green")

    if not positions:
        pos_table.add_row("No open positions", "", "", "", "", "")
    else:
        for p in positions:
            p_type = "BUY" if p.get("type") == 0 else "SELL" # Simple mapping
            profit = p.get("profit", 0.0)
            profit_style = "green" if profit >= 0 else "red"
            pos_table.add_row(
                str(p.get("ticket")),
                p.get("symbol"),
                p_type,
                f"{p.get('volume'):.2f}",
                f"{p.get('price_open'):.2f}",
                f"[{profit_style}]${profit:.2f}[/]"
            )

    console.print(pos_table)

@cli.command()
@click.option("--period", default="7d", help="Period for report (e.g., 24h, 7d, 30d)")
def report(period: str):
    """Generate performance report for the given period."""
    cfg = get_config()
    db_url = cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
    logger_db = TradeLogger(db_url=db_url)

    # Parse period
    unit = period[-1]
    try:
        amount = int(period[:-1])
    except ValueError:
        console.print(f"[red]Invalid period format: {period}. Use 'h' or 'd' (e.g. 7d).[/]")
        return

    if unit == 'h':
        delta = timedelta(hours=amount)
    elif unit == 'd':
        delta = timedelta(days=amount)
    else:
        console.print(f"[red]Invalid period unit: {unit}. Use 'h' or 'd'.[/]")
        return

    start_date = datetime.now(timezone.utc) - delta

    with logger_db.Session() as session:
        trades = session.query(Trade).filter(
            Trade.created_at >= start_date,
            Trade.status == "CLOSED"
        ).all()

    if not trades:
        console.print(f"[yellow]No closed trades found for the period {period}.[/]")
        return

    # Basic stats
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.pnl > 0]
    win_rate = (len(winning_trades) / total_trades) * 100
    total_pnl = sum(t.pnl for t in trades)

    report_table = Table(title=f"Performance Report ({period})")
    report_table.add_column("Metric", style="bold")
    report_table.add_column("Value", justify="right")

    report_table.add_row("Total Trades", str(total_trades))
    report_table.add_row("Win Rate", f"{win_rate:.2f}%")
    report_table.add_row("Net P&L", f"${total_pnl:,.2f}")

    console.print(Panel(report_table, title="[bold]Performance Summary[/]", expand=False))

@cli.command()
def validate():
    """Run all validations and health checks."""
    cfg = get_config()

    console.print("[bold]Running System Validations...[/]")

    # 1. MT5 Connection
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Checking MT5 connection...", total=None)
        connector = MT5Connector(cfg)
        if connector.connect():
            progress.update(task, description="[green]MT5 Connection: OK")
            connector.disconnect()
        else:
            progress.update(task, description="[red]MT5 Connection: FAILED")

        # 2. Database Connection
        task = progress.add_task("Checking database connection...", total=None)
        try:
            db_url = cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
            logger_db = TradeLogger(db_url=db_url)
            with logger_db.engine.connect():
                progress.update(task, description="[green]Database Connection: OK")
        except Exception as e:
            progress.update(task, description=f"[red]Database Connection: FAILED ({e})")

        # 3. Model Files
        task = progress.add_task("Checking model files...", total=None)
        ppo_path = Path("models/trained/ppo_xauusd.zip")
        lstm_path = Path("models/trained/lstm_xauusd.pt")
        models_ok = ppo_path.exists() or lstm_path.exists()
        if models_ok:
            progress.update(task, description="[green]Model Files: OK")
        else:
            progress.update(task, description="[yellow]Model Files: MISSING (using default ensemble)")

@cli.group()
def models():
    """Model management commands."""
    pass

@models.command(name="list")
def list_models():
    """List all available models and their status."""
    model_dir = Path("models/trained")
    table = Table(title="Available Models")
    table.add_column("Model Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", justify="center")
    table.add_column("Last Modified")

    if not model_dir.exists():
        console.print(f"[yellow]Model directory {model_dir} does not exist.[/]")
        # We still print an empty table or message
        table.add_row("No models found", "", "", "")
    else:
        for file in model_dir.glob("*"):
            if file.is_file():
                mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                status = "[green]READY[/]"
                m_type = "Unknown"
                if file.suffix == ".zip":
                    m_type = "PPO / SB3"
                elif file.suffix == ".pt":
                    m_type = "PyTorch / LSTM"

                table.add_row(file.name, m_type, status, mtime)

        if table.row_count == 0:
            table.add_row("No models found", "", "", "")

    console.print(table)

@cli.group()
def config():
    """Configuration management commands."""
    pass

@config.command(name="show")
def show_config():
    """Display current configuration with masked secrets."""
    cfg = get_config()
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for field, value in cfg.model_dump().items():
        # Mask secrets
        if any(secret in field.lower() for secret in ["password", "token", "chat_id"]):
            value = "********"
        table.add_row(field, str(value))

    console.print(table)

@cli.group()
def logs():
    """Log management commands."""
    pass

@logs.command(name="tail")
@click.option("--lines", default=20, help="Number of lines to show initially.")
def tail_logs(lines: int):
    """Stream logs in real time."""
    cfg = get_config()
    log_file = cfg.logs_dir / "main.log"

    if not log_file.exists():
        log_file = Path("main.log")
        if not log_file.exists():
            console.print(f"[red]Log file not found at {cfg.logs_dir / 'main.log'} or ./main.log[/]")
            return

    console.print(f"[bold]Tailing {log_file}...[/] (Ctrl+C to stop)")

    try:
        with open(log_file, "r") as f:
            # Read last N lines
            content = f.readlines()
            for line in content[-lines:]:
                console.print(line.strip())

            # Now tail
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                console.print(line.strip())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped tailing logs.[/]")

if __name__ == "__main__":
    cli()
