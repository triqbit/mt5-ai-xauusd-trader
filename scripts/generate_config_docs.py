import re
from pathlib import Path

def generate_config_docs(input_file: str, output_file: str, version: str):
    path = Path(input_file)
    if not path.exists():
        print(f"Error: {input_file} not found")
        return

    with open(path, "r") as f:
        content = f.read()

    # Find TradingConfig class
    class_match = re.search(r"class TradingConfig\(BaseSettings\):(.*?)(?=\nclass|\Z)", content, re.DOTALL)
    if not class_match:
        print("Error: TradingConfig class not found")
        return

    class_content = class_match.group(1)

    # Match fields like: mt5_login: int = Field(default=0, description="MT5 account number")
    field_pattern = r"([a-z0-9_]+):\s+([a-zA-Z\[\],\s]+)\s+=\s+Field\((.*?)\)"
    matches = re.findall(field_pattern, class_content)

    with open(output_file, "w") as f:
        f.write(f"# Configuration Reference (v{version})\n\n")
        f.write("This document lists the available configuration fields, their types, and descriptions.\n\n")
        f.write("| Field | Type | Description | Default |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")

        for name, type_hint, field_args in matches:
            description = ""
            default = "Required"

            desc_match = re.search(r"description=[\"'](.*?)[\"']", field_args)
            if desc_match:
                description = desc_match.group(1)

            def_match = re.search(r"default=(.*?)(?:,|$)", field_args)
            if def_match:
                default = def_match.group(1).strip().strip("\"'")
                if not default:
                    default = "None"

            f.write(f"| `{name}` | `{type_hint.strip()}` | {description} | `{default}` |\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python generate_config_docs.py <input> <output> <version>")
    else:
        generate_config_docs(sys.argv[1], sys.argv[2], sys.argv[3])
