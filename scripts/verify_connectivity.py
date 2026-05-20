#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Connectivity Verification Script
scripts/verify_connectivity.py

Verifies that the configured MT5/MetaAPI credentials are valid and reachable.
Part of the "Acceptance Contract" for configuration.
"""

import os
import sys

import structlog

# Add src to sys.path
sys.path.append(os.getcwd())

try:
    from src.core.config import TradingConfig
    from src.core.exceptions import MT5ConnectionError
    from src.trading.mt5_connector import MT5Connector
except ImportError as e:
    print(f"Error: Missing core components. Ensure you are running from the repo root. {e}")
    sys.exit(1)

logger = structlog.get_logger(__name__)


def main():
    print("--- ⚡ MT5 Connectivity Acceptance Contract ---")

    try:
        cfg = TradingConfig()
        connector = MT5Connector(config=cfg)

        print(f"Target Mode: {cfg.mode.upper()}")
        print(f"Symbol:      {cfg.symbol}")
        print(f"MT5 Server:  {cfg.mt5_server}")

        print("\nAttempting connection...")
        success = connector.initialize()

        if success:
            print("✅ Connection Established Successfully.")

            # Verify Account Info
            acc_info = connector.get_account_info()
            print(f"Account ID:   {acc_info.get('login') or acc_info.get('number')}")
            print(f"Account Name: {acc_info.get('name')}")
            print(f"Balance:      {acc_info.get('balance')} {acc_info.get('currency', 'USD')}")

            # Verify Terminal Status
            term_status = connector.get_terminal_status()
            algo_enabled = term_status.get("algo_trading", False)
            if algo_enabled:
                print("✅ Algo Trading: ENABLED")
            else:
                print("⚠️  Algo Trading: DISABLED (Check the 'Algo Trading' button in MT5 terminal)")

            connector.shutdown()
            print("\n🚀 Connectivity Verified. System ready for operation.")
            sys.exit(0)
        else:
            print("❌ Connection Failed without exception.")
            sys.exit(1)

    except MT5ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
