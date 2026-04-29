import sys
from pathlib import Path
from src.core.config import TradingConfig

def validate_env_example():
    """
    Validates that .env.example contains all keys defined in TradingConfig.
    """
    root = Path(__file__).resolve().parents[1]
    env_example_path = root / ".env.example"

    if not env_example_path.exists():
        print("Error: .env.example file not found.")
        return False

    # Get keys from TradingConfig (Pydantic model)
    # We use model_fields in Pydantic v2
    config_keys = set(TradingConfig.model_fields.keys())

    # Read keys from .env.example
    env_keys = set()
    with open(env_example_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=")[0].strip().lower()
                env_keys.add(key)

    missing_keys = config_keys - env_keys

    if missing_keys:
        print(f"Error: .env.example is missing the following keys: {', '.join(missing_keys)}")
        return False

    print("Success: .env.example is synchronized with TradingConfig.")
    return True

if __name__ == "__main__":
    if not validate_env_example():
        sys.exit(1)
