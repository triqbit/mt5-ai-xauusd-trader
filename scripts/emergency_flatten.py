#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Emergency Flatten & Fence
scripts/emergency_flatten.py

Immediately closes all open positions and fences the account from further trading.
Part of the "One-command workflow" for Incident Response.
"""

import os
import sys

import structlog

# Add src to sys.path
sys.path.append(os.getcwd())

try:
    from src.core.config import TradingConfig
    from src.trading.mt5_connector import MT5Connector
except ImportError as e:
    print(f"Error: Missing core components. {e}")
    sys.exit(1)

logger = structlog.get_logger(__name__)

def main():
    print("!!! 🛑 EMERGENCY FLATTEN INITIATED 🛑 !!!")

    try:
        cfg = TradingConfig()
        connector = MT5Connector(config=cfg)

        print("Connecting to terminal...")
        if not connector.initialize():
            print("❌ Failed to connect for emergency flattening.")
            sys.exit(1)

        positions = connector.get_positions()
        if not positions:
            print("✅ No open positions found.")
        else:
            print(f"Found {len(positions)} open positions. Closing all...")
            for pos in positions:
                ticket = pos.get("ticket") or pos.get("id")
                print(f"  -> Requesting closure of position {ticket}...")
                try:
                    connector.close_position(ticket)
                    print(f"  ✅ Position {ticket} closed.")
                except Exception as e:
                    print(f"  ❌ Failed to close position {ticket}: {e}")

            print("✅ All position closure requests processed.")

        print("\n--- Fencing Account ---")
        print("Setting lock file: .emergency_lock")
        with open(".emergency_lock", "w") as f:
            f.write("Emergency shutdown triggered at " + os.popen("date").read())

        print("✅ Account fenced. Trading loop will refuse to start while .emergency_lock exists.")

        connector.shutdown()
        print("\n🛑 Emergency flatten complete.")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Error during emergency flatten: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
