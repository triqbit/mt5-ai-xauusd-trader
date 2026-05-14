"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/interfaces.py

Core protocols and interfaces to ensure architectural consistency across modules.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Reportable(Protocol):
    """
    Interface for modules that can contribute a section to a consolidated report.
    """

    def to_report_section(self, **kwargs: Any) -> Any:
        """
        Convert internal state or analysis results into a report-ready format.
        """
        ...
