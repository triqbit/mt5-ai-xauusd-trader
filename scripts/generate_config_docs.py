import ast
import sys
from pathlib import Path


def extract_config_fields(input_file: str):
    path = Path(input_file)
    if not path.exists():
        print(f"Error: {input_file} not found")
        return []

    with open(path, "r") as f:
        tree = ast.parse(f.read())

    fields = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TradingConfig":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    field_name = stmt.target.id
                    if field_name == "model_config":
                        continue

                    type_hint = ast.unparse(stmt.annotation) if stmt.annotation else "Any"

                    description = ""
                    default = "Required"

                    if stmt.value and isinstance(stmt.value, ast.Call):
                        # Handle Field(...)
                        for keyword in stmt.value.keywords:
                            if keyword.arg == "description":
                                if isinstance(keyword.value, ast.Constant):
                                    description = keyword.value.value
                            elif keyword.arg == "default":
                                default = ast.unparse(keyword.value)

                        # Handle Field(..., description=...)
                        if len(stmt.value.args) > 0:
                            arg0 = stmt.value.args[0]
                            # Robust ellipsis check
                            if ast.unparse(arg0) == "...":
                                default = "Required"
                            else:
                                default = ast.unparse(arg0)

                    fields.append(
                        {
                            "name": field_name,
                            "type": type_hint,
                            "description": description,
                            "default": default,
                        }
                    )
    return fields


def generate_docs(input_file: str, output_file: str, version: str):
    fields = extract_config_fields(input_file)
    if not fields:
        print("No fields found or error parsing.")
        return

    with open(output_file, "w") as f:
        f.write(f"# Configuration Reference (v{version})\n\n")
        f.write(
            "This document lists the available configuration fields, their types, and descriptions.\n\n"
        )
        f.write("| Field | Type | Description | Default |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")

        for field in fields:
            # Clean up default value
            clean_default = field["default"].replace("ROOT / ", "")
            # Clean up quotes in paths or strings
            clean_default = clean_default.replace("'", "").replace('"', "")

            if not clean_default:
                clean_default = "None"

            f.write(
                f"| `{field['name']}` | `{field['type']}` | {field['description']} | `{clean_default}` |\n"
            )


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_config_docs.py <input> <output> <version>")
    else:
        generate_docs(sys.argv[1], sys.argv[2], sys.argv[3])
