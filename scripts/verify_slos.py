"""
MT5 AI/ML Trading Bot - Enterprise Reliability Verification Tool
scripts/verify_slos.py
Version: 1.1.0
Calculates current SLO compliance metrics from audit and trade databases.
Synchronized with docs/SLO_TARGETS.md.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

# Use timezone.utc for compatibility
UTC = timezone.utc

# --- Targets from docs/SLO_TARGETS.md ---
TARGETS = {
    "UPTIME": 0.995,
    "CI_SUCCESS": 0.95,
    "RTO_SECONDS": 900,  # 15 mins
    "BACKTEST_P50": 300,  # 5 mins
    "BACKTEST_P95": 480,  # 8 mins
    "BACKTEST_P99": 720,  # 12 mins
    "INFERENCE_P50": 0.010,  # 10ms
    "INFERENCE_P95": 0.050,  # 50ms
    "INFERENCE_P99": 0.100,  # 100ms
}


def get_db_connection(path):
    if not os.path.exists(path):
        return None
    try:
        return sqlite3.connect(path)
    except Exception:
        return None


def calculate_backtest_slos(conn):
    """Analyze backtest durations against targets (<5m P50, <8m P95, <12m P99)."""
    if not conn:
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
    if not cursor.fetchone():
        return None

    cursor.execute("SELECT metadata_json FROM audit_log WHERE action='backtest_completed'")
    rows = cursor.fetchall()

    durations = []
    for row in rows:
        try:
            meta = json.loads(row[0])
            if "duration_seconds" in meta:
                durations.append(meta["duration_seconds"])
        except Exception:
            continue

    if not durations:
        return "No backtest data found."

    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    p99 = durations[int(len(durations) * 0.99)]

    is_compliant = (
        p50 < TARGETS["BACKTEST_P50"]
        and p95 < TARGETS["BACKTEST_P95"]
        and p99 < TARGETS["BACKTEST_P99"]
    )
    status = "✅" if is_compliant else "⚠️"

    return {
        "P50": f"{p50 / 60:.2f} min",
        "P95": f"{p95 / 60:.2f} min",
        "P99": f"{p99 / 60:.2f} min",
        "Status": status,
    }


def calculate_rto_slos(conn):
    """Analyze Recovery Time Objective (Target: 15 mins)."""
    if not conn:
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
    if not cursor.fetchone():
        return None

    cursor.execute(
        "SELECT created_at, metadata_json FROM audit_log WHERE action='system_restored' ORDER BY created_at DESC"
    )
    restorations = cursor.fetchall()

    rto_durations = []
    for rest_time_str, meta_str in restorations:
        try:
            meta = json.loads(meta_str)
            incident_id = meta.get("incident_id")
            if not incident_id:
                continue

            cursor.execute(
                "SELECT created_at FROM audit_log WHERE (action='startup_gate_failure' OR action LIKE 'operator_emergency%') "
                "AND created_at < ? ORDER BY created_at DESC LIMIT 1",
                (rest_time_str,),
            )
            failure = cursor.fetchone()
            if failure:
                fail_time = datetime.fromisoformat(failure[0].replace("Z", "+00:00"))
                rest_time = datetime.fromisoformat(rest_time_str.replace("Z", "+00:00"))
                duration = (rest_time - fail_time).total_seconds()
                rto_durations.append(duration)
        except Exception:
            continue

    if not rto_durations:
        return "No incident recovery data found."

    avg_rto = sum(rto_durations) / len(rto_durations)
    max_rto = max(rto_durations)
    status = "✅" if max_rto < TARGETS["RTO_SECONDS"] else "⚠️"

    return {
        "Avg RTO": f"{avg_rto / 60:.2f} min",
        "Max RTO": f"{max_rto / 60:.2f} min",
        "Status": status,
    }


def calculate_error_budget(conn):
    """Calculate consumed error budget for Availability (30-day window)."""
    if not conn:
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
    if not cursor.fetchone():
        return None

    # Simple heuristic: startup failures represent unreliability
    # Target 99.5% uptime = 0.5% error budget = 144 mins per month
    # We'll assign a weight to each failure (e.g. 30 mins downtime per failure if not specified)
    cursor.execute(
        "SELECT count(*) FROM audit_log WHERE action='startup_gate_failure' "
        "AND created_at > datetime('now', '-30 days')"
    )
    failure_count = cursor.fetchone()[0]

    estimated_downtime_mins = failure_count * 30
    budget_mins = 216  # 0.5% of 30 days (market hours approx)
    remaining_pct = max(0, (budget_mins - estimated_downtime_mins) / budget_mins * 100)

    return {
        "Failure Count (30d)": failure_count,
        "Est. Downtime": f"{estimated_downtime_mins} min",
        "Budget Remaining": f"{remaining_pct:.1f}%",
        "Status": "✅" if remaining_pct > 0 else "🛑 STABILITY FREEZE",
    }


def main():
    print("=== MT5 AI/ML Trading Bot - SLO Compliance Audit ===")

    audit_path = os.getenv("AUDIT_DATABASE_URL", "audit.db").replace("sqlite:///", "")
    conn = get_db_connection(audit_path)

    if not conn:
        print(f"Error: Could not connect to audit database at {audit_path}")
        return

    print("\n[Availability & Error Budget (Target: 99.5%)]")
    eb_slos = calculate_error_budget(conn)
    if eb_slos:
        for k, v in eb_slos.items():
            print(f"  {k}: {v}")

    print("\n[Backtest Generation (Target: P50 < 5m, P95 < 8m)]")
    bt_slos = calculate_backtest_slos(conn)
    if isinstance(bt_slos, dict):
        for k, v in bt_slos.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {bt_slos}")

    print("\n[Incident Recovery (RTO) (Target: 15 min)]")
    rto_slos = calculate_rto_slos(conn)
    if isinstance(rto_slos, dict):
        for k, v in rto_slos.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {rto_slos}")

    print("\n[Prometheus/CI Metrics (External)]")
    print(f"  CI Success Rate Target: {TARGETS['CI_SUCCESS']:.1%}")
    print("  Model Inference P99 Target: < 100ms")
    print("  (Note: Real-time latency and CI rates require Prometheus/GitHub API integration)")

    conn.close()


if __name__ == "__main__":
    main()
