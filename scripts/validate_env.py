"""
Environment Validation Utility
Verifies that .env.example contains all required fields from TradingConfig.
"""
import os
import sys
from pathlib import Path

# Add src to path so we can import TradingConfig
sys.path.append(os.getcwd())

try:
    from src.core.config import TradingConfig
    from pydantic import ValidationError
except ImportError as e:
    print(f"Error: Could not import core components: {e}")
    sys.exit(1)

def validate_env_example():
    root = Path(os.getcwd())
    env_example = root / ".env.example"

    if not env_example.exists():
        print("Error: .env.example not found in root directory.")
        return False

    # Extract keys from .env.example
    example_keys = set()
    with open(env_example, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key = line.split("=")[0].strip()
                    example_keys.add(key.lower())

    # Get expected keys from TradingConfig
    # We use model_json_schema to find all fields
    config_schema = TradingConfig.model_json_schema()
    required_fields = config_schema.get("required", [])
    all_fields = config_schema.get("properties", {}).keys()

    missing_fields = []
    for field in all_fields:
        if field.lower() not in example_keys:
            # Check if it's required
            is_required = field in required_fields
            status = "[REQUIRED]" if is_required else "[OPTIONAL]"
            missing_fields.append(f"{status} {field}")

    if missing_fields:
        print("Validation FAILED: .env.example is missing fields found in TradingConfig:")
        for field in missing_fields:
            print(f"  - {field}")
        return False

    print("Validation SUCCESS: .env.example is synchronized with TradingConfig.")
    return True

if __name__ == "__main__":
    if not validate_env_example():
        sys.exit(1)
    sys.exit(0)
