import sys
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from src.core.config import TradingConfig

def validate_env_example():
    repo_root = Path(__file__).resolve().parents[1]
    env_example_path = repo_root / ".env.example"

    if not env_example_path.exists():
        print(f"Error: {env_example_path} does not exist.")
        return False

    with open(env_example_path, "r") as f:
        env_example_content = f.read()

    # Get fields from TradingConfig
    config_fields = TradingConfig.model_fields.keys()

    missing_fields = []
    for field in config_fields:
        if field.upper() not in env_example_content.upper():
            missing_fields.append(field)

    if missing_fields:
        print("Error: The following fields are missing from .env.example:")
        for field in missing_fields:
            print(f"  - {field}")
        return False

    print(".env.example is valid and contains all required fields.")
    return True

if __name__ == "__main__":
    if not validate_env_example():
        sys.exit(1)
    sys.exit(0)
