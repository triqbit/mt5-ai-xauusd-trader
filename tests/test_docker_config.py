"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_docker_config.py
Tests to verify Docker-related configurations and environmental requirements.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.core.config import get_config

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_exists():
    """Verify that the Dockerfile exists in the root directory."""
    dockerfile_path = ROOT / "Dockerfile"
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"
    assert dockerfile_path.is_file()


def test_docker_compose_exists():
    """Verify that docker-compose.yml exists in the root directory."""
    compose_path = ROOT / "docker-compose.yml"
    assert compose_path.exists(), f"docker-compose.yml not found at {compose_path}"
    assert compose_path.is_file()


def test_docker_compose_structure():
    """Verify the basic structure and volume mounts of docker-compose.yml."""
    compose_path = ROOT / "docker-compose.yml"
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)

    assert "services" in compose_data
    assert "trader" in compose_data["services"]
    trader_service = compose_data["services"]["trader"]

    # Verify build context and dockerfile
    assert trader_service["build"]["context"] == "."
    assert trader_service["build"]["dockerfile"] == "Dockerfile"

    # Verify critical volume mounts
    volumes = trader_service["volumes"]
    expected_mounts = [
        "./.env:/app/.env:ro",
        "./logs:/app/logs",
        "./models:/app/models:ro",
    ]
    for mount in expected_mounts:
        assert mount in volumes


def test_docker_runtime_config_alignment():
    """Verify that TradingConfig ports align with Dockerfile/Compose exposed ports."""
    # Mock required environment variables to prevent validation errors
    with patch.dict(os.environ, {"MT5_PASSWORD": "test", "MT5_SERVER": "test"}):
        # We need to clear lru_cache if it was already called
        from src.core.config import get_config
        get_config.cache_clear()
        config = get_config()

        # Verify Prometheus port alignment (default 8000)
        assert config.prometheus_port == 8000

        # Verify Dash dashboard port alignment (default 8050)
        assert config.dashboard_port == 8050


def test_docker_ignore_exists():
    """Verify that .dockerignore exists in the root directory."""
    ignore_path = ROOT / ".dockerignore"
    assert ignore_path.exists(), f".dockerignore not found at {ignore_path}"
    assert ignore_path.is_file()


def test_docker_ignore_content():
    """Verify that .dockerignore contains critical exclusions."""
    ignore_path = ROOT / ".dockerignore"
    with open(ignore_path, "r") as f:
        content = f.read()

    critical_exclusions = [".git", ".env", "__pycache__/", ".venv", "logs/"]
    for exclusion in critical_exclusions:
        assert exclusion in content
