"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/preflight.py
Pre-deployment safety checks to ensure system readiness.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from typing import Dict, List

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


class PreflightCheck:
    """
    The Guardian's Gate: Verifies system readiness before live execution.
    Checks connectivity, credentials, and model artifacts.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []

    def run_all(self) -> bool:
        """Run the full suite of pre-flight checks."""
        logger.info("🗺️ Atlas: Starting system pre-flight checks...")

        self.results["Config Validation"] = self._check_config()
        self.results["Model Artifacts"] = self._check_models()
        self.results["Database Connection"] = self._check_database()

        passed = all(self.results.values())

        if passed:
            logger.info("✅ Pre-flight checks passed. System ready for deployment.")
        else:
            logger.error("❌ Pre-flight checks FAILED. Review errors below:")
            for err in self.errors:
                logger.error("  - %s", err)

        return passed

    def _check_config(self) -> bool:
        """Verify basic configuration requirements."""
        if self.cfg.is_live and self.cfg.risk_per_trade > 0.02:
            self.errors.append("CRITICAL: Risk per trade > 2% in LIVE mode is prohibited.")
            return False
        return True

    def _check_models(self) -> bool:
        """Verify model files exist and are accessible."""
        models_to_check = [
            self.cfg.model_path,
            self.cfg.model_path.parent / "ppo_xauusd.zip",
            self.cfg.model_path.parent / "lstm_xauusd.pt",
        ]

        missing = [str(m) for m in models_to_check if not m.exists()]
        if missing:
            for m in missing:
                logger.warning("Optional model artifact missing: %s", m)

        if not self.cfg.model_path.exists():
            self.errors.append(f"Model file not found: {self.cfg.model_path}")
            return False
        return True

    def _check_database(self) -> bool:
        """Verify database connectivity (SQLite or Postgres)."""
        try:
            from sqlalchemy import create_engine, text  # type: ignore

            engine = create_engine(self.cfg.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.errors.append(f"Database connection failed: {e}")
            return False


__all__ = ["PreflightCheck"]
