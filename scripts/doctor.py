import sys
import platform
from pathlib import Path

def check_python_version():
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"OK ({platform.python_version()})")
        return True
    else:
        print(f"FAILED (Requires 3.10+, found {platform.python_version()})")
        return False

def check_dependencies():
    print("Checking dependencies...", end=" ")
    try:
        # Check a few key dependencies
        import torch
        import pandas
        import numpy
        import pydantic
        import talib
        print("OK")
        return True
    except ImportError as e:
        print(f"FAILED (Missing: {e.name})")
        return False

def check_env_file():
    print("Checking .env file...", end=" ")
    if Path(".env").exists():
        print("OK")
        return True
    else:
        print("MISSING (Create one from .env.example)")
        return False

def check_talib():
    print("Checking TA-Lib installation...", end=" ")
    try:
        import numpy
        import talib
        # Try to call a simple function to ensure the C library is also linked
        talib.SMA(numpy.array([1.0, 2.0, 3.0]), timeperiod=2)
        print("OK")
        return True
    except ImportError as e:
        print(f"FAILED (Missing dependency: {e.name}. Try: pip install TA-Lib numpy)")
        return False
    except Exception as e:
        print(f"FAILED (TA-Lib issue: {e})")
        if "talib" in str(e).lower():
            print("  TIP: You may need to install the TA-Lib C library (e.g., 'brew install ta-lib' or 'apt-get install libta-lib0')")
        return False

def main():
    print("=== MT5 AI/ML Trading Bot Doctor ===")
    results = [
        check_python_version(),
        check_dependencies(),
        check_env_file(),
        check_talib()
    ]

    print("====================================")
    if all(results):
        print("System is READY.")
        sys.exit(0)
    else:
        print("System has ISSUES. Please follow the instructions above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
