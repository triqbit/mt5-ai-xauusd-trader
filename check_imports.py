import os
import pkgutil
import sys

# Add current directory to sys.path
sys.path.insert(0, os.path.abspath("."))


def check_imports():
    import src

    errors = []
    for _loader, name, _is_pkg in pkgutil.walk_packages(src.__path__, src.__name__ + "."):
        try:
            # Skip modules that might fail due to missing environment (like MT5 on Linux)
            # but we want to see if there are actual syntax/import errors.
            # Some might fail if they require talib and it's not installed,
            # but I installed it.
            __import__(name)
        except Exception as e:
            print(f"Failed to import {name}: {e}")
            errors.append((name, e))

    if not errors:
        print("All modules in src imported successfully!")


if __name__ == "__main__":
    check_imports()
