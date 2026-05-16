import ast
import sys
from pathlib import Path


def get_required_vars_from_config():
    config_path = Path("src/core/config.py")
    if not config_path.exists():
        print(f"Error: {config_path} not found.")
        return set()

    with open(config_path, "r") as f:
        tree = ast.parse(f.read())

    required_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TradingConfig":
            for item in node.body:
                # Catch both:
                # var: type = Field(...)
                # var: type
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    var_name = item.target.id
                    if var_name != "model_config":
                         required_vars.add(var_name.lower())
    return required_vars

def get_vars_from_example():
    example_path = Path(".env.example")
    if not example_path.exists():
        print(f"Error: {example_path} not found.")
        return set()

    vars = set()
    with open(example_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                var = line.split("=")[0].strip()
                vars.add(var.lower())
    return vars

def validate():
    print("Validating environment configuration template...")

    required = get_required_vars_from_config()
    example = get_vars_from_example()

    if not required:
        print("Error: No configuration fields found in src/core/config.py")
        return False

    missing = []
    for req in required:
        if req not in example:
            missing.append(req)

    if missing:
        print("=" * 60)
        print("  DEPLOYMENT BLOCKED: ENVIRONMENT TEMPLATE INCOMPLETE")
        print("=" * 60)
        print("Error: The following required configuration fields are missing from .env.example:")
        for m in sorted(missing):
            print(f"  [MISSING] -> {m.upper()}")
        print("\nREMEDIATION: Add these fields to .env.example with placeholder values")
        print("to ensure production deployment safety and complete documentation.")
        print("=" * 60)
        return False

    print(f"SUCCESS: Environment validation passed. .env.example contains all {len(required)} fields.")
    return True

if __name__ == "__main__":
    if not validate():
        sys.exit(1)
