"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_cli_ux.py
Unit tests for CLI UX components.
"""

from unittest.mock import MagicMock
from rich.table import Table
from src.core.config_validator import ValidationError

def test_validation_table_structure():
    """Verify that we can create a table with validation errors without crashing."""
    from rich import box

    table = Table(title="Test Validation", box=box.ROUNDED)
    table.add_column("Field")
    table.add_column("Level")
    table.add_column("Message")

    errors = [
        ValidationError(field="TEST_FIELD", message="Test Message", critical=True)
    ]

    for err in errors:
        level_str = "CRITICAL" if err.critical else "WARNING"
        level_color = "red" if err.critical else "yellow"
        table.add_row(err.field, f"[{level_color}]{level_str}[/]", err.message)

    assert len(table.rows) == 1
    assert table.title == "Test Validation"
