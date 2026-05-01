import re
import sys
from pathlib import Path


def get_required_vars_from_config():
    config_path = Path("src/core/config.py")
    if not config_path.exists():
        return set()

    with open(config_path, "r") as f:
        content = f.read()

    # Simple regex to find Field(...) definitions in TradingConfig
    # This is a bit brittle but avoids importing the code which might have side effects
    matches = re.findall(r"([a-z0-9_]+):\s+[a-zA-Z\[\],\s]+=\s+Field\(", content)
    return set(matches)


def get_vars_from_example():
    example_path = Path(".env.example")
    if not example_path.exists():
        return set()

    vars = set()
    with open(example_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    var = line.split("=")[0].strip()
                    vars.add(var.lower())
    return vars


def validate():
    print("Validating environment configuration template...")

    required = get_required_vars_from_config()
    example = get_vars_from_example()

    missing = []
    for req in required:
        if req.lower() not in example:
            missing.append(req)

    if missing:
        print("Error: The following required configuration fields are missing from .env.example:")
        for m in missing:
            print(f"  - {m}")
        return False

    print("Environment validation passed: .env.example is up to date.")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
