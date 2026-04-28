#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - System Doctor
Diagnoses common environment and configuration issues.
"""
import importlib.util
import platform
import sys
from pathlib import Path


def check_python_version():
    print(f"[*] Python Version: {platform.python_version()} - {'OK' if sys.version_info >= (3, 10) else 'FAIL (>= 3.10 required)'}")

def check_dependencies():
    required = ["pydantic", "structlog", "pandas", "torch", "MetaTrader5", "metaapi_cloud_sdk"]
    print("[*] Checking Dependencies:")
    for pkg in required:
        spec = importlib.util.find_spec(pkg.replace("-", "_"))
        status = "OK" if spec else "MISSING"
        print(f"    - {pkg:20}: {status}")

def check_config():
    env_path = Path(".env")
    print(f"[*] Configuration (.env): {'FOUND' if env_path.exists() else 'MISSING'}")
    if env_path.exists():
        with open(env_path, "r") as f:
            content = f.read()
            for key in ["MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER"]:
                if key not in content:
                    print(f"    - WARNING: {key} missing from .env")

def check_directories():
    dirs = ["models/trained", "logs", "data"]
    print("[*] Checking Directories:")
    for d in dirs:
        p = Path(d)
        print(f"    - {d:20}: {'OK' if p.exists() else 'MISSING'}")

def main():
    print("🩺 MT5 AI/ML Bot Doctor - System Health Check\n" + "="*45)
    check_python_version()
    check_dependencies()
    check_config()
    check_directories()
    print("="*45 + "\nDone.")

if __name__ == "__main__":
    main()
