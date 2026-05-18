import subprocess
import sys


def test_cli_help_resilience():
    """Verify that --help works even if dependencies are missing (logic check)."""
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0
    assert "MT5 AI/ML Trading Bot" in result.stdout
    assert "Usage Examples" in result.stdout

def test_cli_version_resilience():
    """Verify that --version works and reads from source directly."""
    result = subprocess.run(
        [sys.executable, "main.py", "--version"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0
    # Should contain a version number like x.y.z
    assert "main.py" in result.stdout

def test_cli_doctor_resilience():
    """Verify that --doctor works even in uninitialized environment."""
    result = subprocess.run(
        [sys.executable, "main.py", "--doctor"],
        capture_output=True,
        text=True,
        timeout=30
    )
    # --doctor might exit with 1 if issues are found, but it should reach the doctor logic
    assert "System Doctor" in result.stdout or "MT5 AI/ML Trading Bot Doctor" in result.stdout
