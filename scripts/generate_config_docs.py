import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

def clean_value(val_str: str) -> str:
    """Clean up AST unparsed values for Markdown display."""
    # Remove ROOT / prefix
    val_str = val_str.replace("ROOT / ", "")

    # Handle the weird case for model_path where it might have a trailing quote
    if val_str.startswith("'") and not val_str.endswith("'") and " / " in val_str:
         val_str = val_str[1:]
    if val_str.endswith("'") and not val_str.startswith("'") and " / " in val_str:
         val_str = val_str[:-1]

    # Remove excessive quotes if fully quoted
    if (val_str.startswith("'") and val_str.endswith("'")) or \
       (val_str.startswith('"') and val_str.endswith('"')):
        val_str = val_str[1:-1]

    if not val_str or val_str == "''" or val_str == '""':
        return "None"
    return val_str

def get_field_info(node: ast.AnnAssign) -> Dict[str, Any]:
    """Extract information from a Pydantic-style field assignment."""
    field_name = node.target.id if isinstance(node.target, ast.Name) else "unknown"

    # Extract type hint as string
    type_hint = ast.unparse(node.annotation)

    description = ""
    default = "Required"

    # Check for = Field(...)
    if node.value and isinstance(node.value, ast.Call):
        if isinstance(node.value.func, ast.Name) and node.value.func.id == "Field":
            # Process arguments of Field()
            # Positional arguments (often just default)
            if node.value.args:
                arg0 = node.value.args[0]
                if isinstance(arg0, ast.Constant) and arg0.value is Ellipsis:
                    default = "Required"
                else:
                    default = ast.unparse(arg0)

            # Keyword arguments (description, default, etc.)
            for kw in node.value.keywords:
                if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                    description = kw.value.value
                elif kw.arg == "default":
                    if isinstance(kw.value, ast.Constant) and kw.value.value is Ellipsis:
                        default = "Required"
                    else:
                        default = ast.unparse(kw.value)
    # Check for simple assignment: field: type = value
    elif node.value:
        default = ast.unparse(node.value)

    return {
        "name": field_name,
        "type": type_hint,
        "description": description,
        "default": clean_value(default)
    }

def generate_config_docs(input_file: str, output_file: str, version: str):
    path = Path(input_file)
    if not path.exists():
        print(f"Error: {input_file} not found")
        return

    with open(path, "r") as f:
        tree = ast.parse(f.read())

    fields = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TradingConfig":
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    # Skip model_config
                    if isinstance(item.target, ast.Name) and item.target.id == "model_config":
                        continue
                    fields.append(get_field_info(item))

    with open(output_file, "w") as f:
        f.write(f"# Configuration Reference (v{version})\n\n")
        f.write("This document lists the available configuration fields, their types, and descriptions.\n\n")
        f.write("| Field | Type | Description | Default |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")

        for field in fields:
            desc = field["description"] if field["description"] else "No description provided."
            f.write(f"| `{field['name']}` | `{field['type']}` | {desc} | `{field['default']}` |\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python generate_config_docs.py <input> <output> <version>")
    else:
        generate_config_docs(sys.argv[1], sys.argv[2], sys.argv[3])
