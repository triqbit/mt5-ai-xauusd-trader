#!/usr/bin/env python
"""
Institutional Backtesting Stub
Redirects to main.py --mode backtest with standard parameters.
"""
import sys
import subprocess

def main():
    print("🚀 Initiating Institutional Backtest...")
    cmd = [
        sys.executable, "main.py",
        "--mode", "backtest",
        "--symbol", "XAUUSD",
        "--algo", "ensemble"
    ]
    # Pass through any additional arguments
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Backtest failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Backtest interrupted by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
