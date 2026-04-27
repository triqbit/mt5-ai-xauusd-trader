import sys
import os
from pydantic import ValidationError

# Add src to sys.path to allow importing TradingConfig
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.core.config import TradingConfig

    def validate():
        try:
            # We instantiate TradingConfig directly to bypass get_config's cache
            # and ensure we are validating current environment.
            TradingConfig()
            print("✅ Environment variables validation passed.")
            return 0
        except ValidationError as e:
            print("❌ Environment variables validation failed!")
            # We want clear error messages as per requirements
            for error in e.errors():
                loc = ".".join(str(l) for l in error["loc"])
                print(f"  - {loc}: {error['msg']}")
            return 1
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
            return 1

    if __name__ == "__main__":
        sys.exit(validate())

except ImportError as e:
    print(f"❌ Failed to import TradingConfig: {e}")
    sys.exit(1)
