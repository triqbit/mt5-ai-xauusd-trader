#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Production Smoke Test Suite
scripts/smoke_test.py

Verifies the operational readiness of a deployed instance by auditing:
1. API Liveness/Readiness
2. Component Health (Database, MT5, Models)
3. Prometheus Metrics availability
4. Audit Log traceability

Usage:
    python scripts/smoke_test.py --url http://localhost:8000 --audit-db audit.db
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict

try:
    import httpx
except ImportError:
    print("Error: 'httpx' library is required. Run 'pip install httpx'.")
    sys.exit(1)


def check_api_health(base_url: str, retries: int = 1, delay: int = 5) -> Dict[str, Any]:
    """Check liveness and readiness endpoints with optional retries."""
    results = {"liveness": False, "readiness": False, "components": {}}

    for attempt in range(1, retries + 1):
        try:
            # 1. Liveness
            resp = httpx.get(f"{base_url}/health/liveness", timeout=5.0)
            results["liveness"] = resp.status_code == 200

            # 2. Readiness (Detailed)
            resp = httpx.get(f"{base_url}/health/readiness", timeout=10.0)
            results["readiness"] = resp.status_code == 200
            if resp.status_code in (200, 503):
                data = resp.json()
                results["version"] = data.get("version", "unknown")
                results["components"] = data.get("components", {})

            # If both are healthy, we're done
            if results["liveness"] and results["readiness"]:
                if attempt > 1:
                    print(f"✅ Connection established on attempt {attempt}.")
                break

        except Exception as e:
            if attempt < retries:
                print(f"⚠️ Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"❌ API Connection Failed after {retries} attempts: {e}")

        # If not successful but still have attempts, wait
        if not (results["liveness"] and results["readiness"]) and attempt < retries:
            print(f"⚠️ Service not ready on attempt {attempt}/{retries}. Retrying in {delay}s...")
            time.sleep(delay)

    return results


def check_metrics(base_url: str) -> bool:
    """Verify Prometheus metrics endpoint."""
    try:
        resp = httpx.get(f"{base_url}/metrics", timeout=5.0)
        if resp.status_code == 200 and "system_component_health" in resp.text:
            return True
    except Exception:
        pass
    return False


def check_audit_trail(db_path: str) -> bool:
    """Verify that a startup event exists in the audit trail."""
    path = Path(db_path)
    if not path.exists():
        print(f"⚠️ Audit DB not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check for 'startup_initiated' or 'trading_engine_started' in the last hour
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log
            WHERE action IN ('startup_initiated', 'trading_engine_started')
            AND timestamp > datetime('now', '-1 hour')
        """)
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"⚠️ Audit Trace Check Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="MT5 Bot Smoke Tests")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Base URL of the running bot"
    )
    parser.add_argument("--audit-db", default="audit.db", help="Path to audit.db")
    parser.add_argument(
        "--wait", type=int, default=0, help="Wait N seconds before starting (for startup)"
    )
    parser.add_argument(
        "--retries", type=int, default=1, help="Number of times to retry API checks"
    )
    parser.add_argument("--delay", type=int, default=5, help="Delay between retries in seconds")
    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait}s for service to stabilize...")
        time.sleep(args.wait)

    print(f"--- MT5 Bot Smoke Test: {args.url} ---")

    api_results = check_api_health(args.url, retries=args.retries, delay=args.delay)
    metrics_ok = check_metrics(args.url)
    audit_ok = check_audit_trail(args.audit_db)

    # 1. API Status
    liveness_status = "✅ OK" if api_results["liveness"] else "❌ FAILED"
    readiness_status = "✅ OK" if api_results["readiness"] else "❌ FAILED"
    print(f"Liveness Check:  {liveness_status}")
    print(f"Readiness Check: {readiness_status}")

    if api_results.get("version"):
        print(f"Detected Version: {api_results['version']}")

    # 2. Component Breakdown
    if api_results["components"]:
        print("\nComponent Status:")
        for name, info in api_results["components"].items():
            status_icon = (
                "✅"
                if info["status"] == "healthy"
                else "⚠️"
                if info["status"] == "degraded"
                else "❌"
            )
            print(f"  {status_icon} {name:12}: {info['status'].upper()} - {info['message']}")

    # 3. Infrastructure
    print("\nInfrastructure:")
    print(f"  {'✅' if metrics_ok else '❌'} Prometheus Metrics (/metrics)")
    print(f"  {'✅' if audit_ok else '❌'} Audit Trail Trace (audit.db)")

    # Final Verdict
    print("\n--- Verdict ---")
    critical_failures = not api_results["readiness"]

    if critical_failures:
        print("🛑 SMOKE TEST FAILED: Service is not ready for production.")
        sys.exit(1)
    else:
        print("🚀 SMOKE TEST PASSED: Deployment is operational.")
        sys.exit(0)


if __name__ == "__main__":
    main()
