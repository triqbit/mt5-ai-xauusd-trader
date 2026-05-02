#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/backtest.py - Backtesting entry point

This script provides a unified interface for historical strategy evaluation.
"""

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Institutional Backtesting Suite")
    parser.add_argument("--symbol", default="XAUUSD", help="Symbol to backtest")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--algo", default="ensemble", help="Algorithm to evaluate")
    args = parser.parse_args()

    print("=" * 60)
    print("🏛️  Institutional Backtesting Suite")
    print("=" * 60)
    print(f"Target Symbol: {args.symbol}")
    print(f"Algorithm    : {args.algo}")
    print(f"Period       : {args.start or 'Earliest'} to {args.end or 'Latest'}")
    print("-" * 60)

    print("\n[INFO] Backtesting module is currently in 'Experimental' status.")
    print("[INFO] Please use 'python main.py --mode backtest' for vectorized validation.")
    print("[INFO] For walk-forward optimization, see: scripts/hyperopt_walkforward.py")

    print("\nStatus: DEFERRED TO V1.1.0-RC2")
    print("Reference: docs/product/FEATURE_ROADMAP.md")

    return 0

if __name__ == "__main__":
    sys.exit(main())
