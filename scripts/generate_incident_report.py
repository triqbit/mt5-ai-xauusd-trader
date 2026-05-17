"""
MT5 AI/ML Trading Bot - Operational Incident Triage Tool
scripts/generate_incident_report.py
Analyzes the trade and audit databases to provide a summary of recent operational incidents.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Use timezone.utc for compatibility with Python 3.10
UTC = timezone.utc


def get_db_path(env_var, default_filename):
    load_dotenv()
    url = os.getenv(env_var, f"sqlite:///{default_filename}")
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    # If it's a full URL (like postgres), sqlite3 won't work, but for this bot
    # we predominantly use SQLite for operational data.
    return default_filename


def get_db_connection(path):
    if not os.path.exists(path):
        return None
    try:
        return sqlite3.connect(path)
    except Exception:
        return None


def table_exists(conn, table_name):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def analyze_risk_events(conn):
    if not conn or not table_exists(conn, "risk_events"):
        return []
    cursor = conn.cursor()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "SELECT event_type, description, symbol, created_at FROM risk_events "
        "WHERE created_at > ? ORDER BY created_at DESC",
        (yesterday,),
    )
    return cursor.fetchall()


def analyze_audit_logs(conn):
    if not conn or not table_exists(conn, "audit_log"):
        return []
    cursor = conn.cursor()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    actions = (
        "risk_decision",
        "trade_blocked",
        "operator_action",
        "deployment",
        "mt5_connection_status",
        "circuit_breaker_triggered",
        "daily_loss_limit_triggered",
        "system_restored",
        "config_change",
        "operator_circuit_breaker_triggered",
        "operator_db_repair_attempt",
        "operator_db_restoration",
        "operator_db_incident_resolved",
        "operator_rollback_initiated",
        "operator_db_migration_downgrade",
        "operator_rollback_verified",
        "operator_secret_rotation_initiated",
        "operator_secret_rotation_completed",
    )
    placeholders = ", ".join(["?"] * len(actions))
    cursor.execute(
        f"SELECT action, details, created_at FROM audit_log "
        f"WHERE action IN ({placeholders}) AND created_at > ? ORDER BY created_at DESC",
        (*actions, yesterday),
    )
    return cursor.fetchall()


def analyze_recent_trades(conn):
    if not conn or not table_exists(conn, "trades"):
        return []
    cursor = conn.cursor()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "SELECT ticket, symbol, direction, pnl, status, created_at FROM trades "
        "WHERE created_at > ? ORDER BY created_at DESC",
        (yesterday,),
    )
    return cursor.fetchall()


def generate_report():
    print("=== MT5 Operational Incident Report (Last 24h) ===")

    trades_path = get_db_path("DATABASE_URL", "trades.db")
    audit_path = get_db_path("AUDIT_DATABASE_URL", "audit.db")

    trades_conn = get_db_connection(trades_path)
    audit_conn = get_db_connection(audit_path)

    risk_events = analyze_risk_events(trades_conn)
    audit_logs = analyze_audit_logs(audit_conn)
    recent_trades = analyze_recent_trades(trades_conn)

    print(f"\n[Risk Events: {len(risk_events)}]")
    for event in risk_events[:10]:
        print(f"  - {event[3]} | {event[0]} | {event[2] or 'N/A'} | {event[1]}")

    print(f"\n[Audit Logs: {len(audit_logs)}]")
    for log in audit_logs[:10]:
        print(f"  - {log[2]} | {log[0]} | {log[1]}")

    print(f"\n[Recent Trades: {len(recent_trades)}]")
    for trade in recent_trades[:10]:
        print(f"  - {trade[5]} | {trade[0]} | {trade[1]} | {trade[4]} | PnL: {trade[3]:.2f}")

    if not risk_events and not audit_logs and not recent_trades:
        print("\nNo significant operational events detected in the last 24 hours.")

    if trades_conn:
        trades_conn.close()
    if audit_conn:
        audit_conn.close()


if __name__ == "__main__":
    generate_report()
