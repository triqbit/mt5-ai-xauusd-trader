"""
MT5 AI/ML Trading Bot - Enterprise Diagnostics Tool
scripts/doctor.py
Performs environment, dependency, and connectivity checks to ensure system readiness.
"""

import logging
import os
import platform
import stat
import sys
from pathlib import Path

# Configure minimal logging for the doctor
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("doctor")

# Try to import rich for beautiful output, fallback to plain text if missing
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


def get_system_version() -> str:
    try:
        # Add root to sys.path to allow importing src
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from src import __version__

        return __version__
    except Exception:
        return "1.0.0 (fallback)"


def parse_version(v_str: str) -> tuple[int, ...]:
    """Convert version string to tuple of integers for robust comparison."""
    try:
        # Handle versions like '0.136.1', '2.5.1+cpu', '2.14.1.post0'
        # Strip non-numeric parts from each segment
        parts = []
        for segment in v_str.split("."):
            clean_segment = "".join(filter(str.isdigit, segment))
            if clean_segment:
                parts.append(int(clean_segment))
            else:
                parts.append(0)
        return tuple(parts)
    except Exception:
        return (0,)


class DiagnosticCheck:
    def __init__(self, name, status, message, remedy="N/A"):
        self.name = name
        self.status = status  # "OK", "WARNING", "FAILED"
        self.message = message
        self.remedy = remedy


def check_python_version():
    version = sys.version_info
    msg = f"Found {platform.python_version()}"
    if version.major == 3 and version.minor >= 10:
        return DiagnosticCheck("Python Version", "OK", msg)
    else:
        return DiagnosticCheck("Python Version", "FAILED", msg, "Install Python 3.10 or higher.")


CORE_DEPENDENCIES = {
    "numpy": ("numpy", "1.26.4"),
    "pandas": ("pandas", "2.2.3"),
    "pydantic": ("pydantic", "2.13.4"),
    "pydantic-settings": ("pydantic_settings", "2.14.1"),
    "sqlalchemy": ("sqlalchemy", "2.0.50"),
    "metaapi-cloud-sdk": ("metaapi_cloud_sdk", "29.1.1"),
    "torch": ("torch", "2.5.1"),
    "fastapi": ("fastapi", "0.136.1"),
    "structlog": ("structlog", "25.5.0"),
    "rich": ("rich", "13.9.4"),
    "python-dotenv": ("dotenv", "1.2.2"),
    "requests": ("requests", "2.34.2"),
    "aiohttp": ("aiohttp", "3.14.1"),
    "httpx": ("httpx", "0.28.1"),
    "uvicorn": ("uvicorn", "0.34.0"),
    "gymnasium": ("gymnasium", "1.0.0"),
    "stable-baselines3": ("stable_baselines3", "2.5.0"),
    "jinja2": ("jinja2", "3.1.6"),
    "tqdm": ("tqdm", "4.67.1"),
    "scipy": ("scipy", "1.15.3"),
    "scikit-learn": ("sklearn", "1.6.1"),
    "psutil": ("psutil", "7.2.2"),
    "joblib": ("joblib", "1.5.3"),
    "redis": ("redis", "8.0.0"),
    "alembic": ("alembic", "1.18.4"),
    "prometheus-client": ("prometheus_client", "0.21.1"),
    "python-socketio": ("socketio", "4.6.1"),
    "pytz": ("pytz", "2026.2"),
    "psycopg2-binary": ("psycopg2", "2.9.12"),
    "python-telegram-bot": ("telegram", "22.7"),
    "optuna": ("optuna", "4.9.0"),
}


def check_dependencies(dependencies=None):
    try:
        from importlib.metadata import version as get_version
    except ImportError:
        # Fallback for environments where importlib.metadata is problematic in mocks
        def get_version(name):
            return "unknown"

    deps = (dependencies or CORE_DEPENDENCIES).copy()

    # Platform-specific dependency adjustments
    is_windows = sys.platform == "win32"
    if is_windows:
        deps["MetaTrader5"] = ("MetaTrader5", "5.0.0")

    missing = []
    optional_missing = []
    outdated = []
    versions = []

    for display_name, val in deps.items():
        if isinstance(val, tuple):
            module_name, min_version = val
        else:
            module_name = val
            min_version = "0.0.0"

        try:
            __import__(module_name)
            try:
                # Some modules have different metadata names
                meta_name = module_name.replace("_", "-")
                if module_name == "dotenv":
                    meta_name = "python-dotenv"
                if module_name == "talib":
                    meta_name = "TA-Lib"

                actual_version = get_version(meta_name)

                if actual_version != "unknown" and parse_version(actual_version) < parse_version(
                    min_version
                ):
                    outdated.append(f"{display_name} (found {actual_version}, need {min_version})")

                versions.append(f"{display_name} v{actual_version}")
            except Exception:
                versions.append(f"{display_name} v?")
        except ImportError:
            missing.append(display_name)

    if missing:
        remedy = (
            "Run 'pip install -r requirements-linux.txt'. If versions fail to resolve, check for invalid pins in requirements files."
            if sys.platform != "win32"
            else "Run 'pip install -r requirements.txt'. If versions fail to resolve, check for invalid pins in requirements files."
        )
        return DiagnosticCheck(
            "Dependencies",
            "FAILED",
            f"Missing: {', '.join(missing)}",
            remedy,
        )
    elif optional_missing:
        return DiagnosticCheck(
            "Dependencies",
            "WARNING",
            f"Missing Optional: {', '.join(optional_missing)}",
            "Install optional packages for full functionality.",
        )
    elif outdated:
        return DiagnosticCheck(
            "Dependencies",
            "WARNING",
            f"Outdated: {', '.join(outdated)}",
            "Update dependencies: 'pip install -r requirements.txt'",
        )
    else:
        msg = f"All core libraries present: {', '.join(versions[:3])}..."
        return DiagnosticCheck("Dependencies", "OK", msg)


def check_requirement_harmonization():
    """Verify all requirements*.txt files are in sync."""
    import re

    root = Path(__file__).resolve().parents[1]
    req_files = list(root.glob("requirements*.txt"))

    all_requirements = {}
    mismatches = []

    def parse_requirements(filepath):
        requirements = {}
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("--"):
                    continue
                match = re.match(r"^([^;=<>!~]+)([=<>!~]+.*)$", line)
                if match:
                    package = match.group(1).strip()
                    version = match.group(2).strip()
                    requirements[package] = version
        return requirements

    for req_file in req_files:
        try:
            reqs = parse_requirements(req_file)
            for package, version in reqs.items():
                if package in all_requirements:
                    if all_requirements[package]["version"] != version:
                        mismatches.append(
                            f"{package} ({all_requirements[package]['file']} vs {req_file.name})"
                        )
                else:
                    all_requirements[package] = {"version": version, "file": req_file.name}
        except Exception as e:
            return DiagnosticCheck(
                "Requirement Sync", "FAILED", f"Error parsing {req_file.name}: {e}"
            )

    if mismatches:
        return DiagnosticCheck(
            "Requirement Sync",
            "FAILED",
            f"Mismatches: {', '.join(mismatches[:2])}",
            "Run 'python scripts/verify_dependencies.py' for details.",
        )
    else:
        return DiagnosticCheck("Requirement Sync", "OK", f"All {len(req_files)} files harmonized")


def check_env_file():
    env_path = Path(".env")
    if env_path.exists():
        # Quick check for placeholders
        try:
            with open(env_path, "r") as f:
                content = f.read().upper()
                placeholders = ["YOUR_PASSWORD_HERE", "YOUR_SERVER_HERE", "CHANGE_ME"]
                found = [p for p in placeholders if p in content]
                if found:
                    return DiagnosticCheck(
                        ".env Configuration",
                        "WARNING",
                        f"Found placeholders: {', '.join(found)}",
                        "Update .env with real credentials.",
                    )
            return DiagnosticCheck(".env Configuration", "OK", ".env exists and appears configured")
        except Exception as e:
            return DiagnosticCheck(".env Configuration", "FAILED", f"Error reading .env: {e}")
    else:
        return DiagnosticCheck(
            ".env Configuration",
            "FAILED",
            ".env is missing",
            "Run 'python main.py --setup' or 'make setup' to configure the environment.",
        )


def check_talib():
    try:
        import numpy as np
        import talib

        # Try to call a simple function to ensure the C library is also linked
        talib.SMA(np.array([1.0, 2.0, 3.0]), timeperiod=2)
        return DiagnosticCheck("TA-Lib Library", "OK", "C-Library linked and functional")
    except ImportError:
        return DiagnosticCheck(
            "TA-Lib Library",
            "WARNING",
            "Python wrapper not installed",
            "The bot will use internal fallbacks. Run 'pip install TA-Lib' for full performance.",
        )
    except Exception as e:
        return DiagnosticCheck(
            "TA-Lib Library",
            "WARNING",
            f"Linkage error: {e}",
            "The bot will use internal fallbacks. Ensure TA-Lib C-library is installed for full performance (e.g., brew install ta-lib).",
        )


def check_hardware_acceleration():
    try:
        import torch

        if torch.cuda.is_available():
            msg = f"GPU (CUDA: {torch.cuda.get_device_name(0)})"
            return DiagnosticCheck("Hardware Accel", "OK", msg)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return DiagnosticCheck("Hardware Accel", "OK", "GPU (Apple MPS)")
        else:
            return DiagnosticCheck(
                "Hardware Accel",
                "WARNING",
                "Running on CPU only",
                "Install CUDA drivers if GPU is available.",
            )
    except Exception:
        return DiagnosticCheck(
            "Hardware Accel", "FAILED", "Torch not installed", "Run 'pip install torch'"
        )


def check_database():
    try:
        from sqlalchemy import create_engine, text

        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        db_url = os.getenv("DATABASE_URL", "sqlite:///trades.db")

        # Disable logging for the check
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

        engine = create_engine(
            str(db_url), connect_args={"connect_timeout": 2} if "postgres" in db_url else {}
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return DiagnosticCheck(
            "Database Connectivity",
            "OK",
            f"Connected to {db_url.split('@')[-1] if '@' in db_url else db_url}",
        )
    except Exception as e:
        return DiagnosticCheck(
            "Database Connectivity",
            "FAILED",
            str(e),
            "Verify DATABASE_URL and ensure the database server is running.",
        )


def check_file_permissions():
    if sys.platform == "win32":
        return DiagnosticCheck("File Permissions", "OK", "Skipped on Windows")

    sensitive = [".env", "trades.db", "audit.db"]
    insecure = []
    for f in sensitive:
        p = Path(f)
        if p.exists():
            try:
                mode = os.stat(p).st_mode
                if mode & (stat.S_IRWXG | stat.S_IRWXO):
                    insecure.append(f)
            except Exception:
                pass

    if not insecure:
        return DiagnosticCheck("File Permissions", "OK", "Sensitive files are restricted")
    else:
        return DiagnosticCheck(
            "File Permissions",
            "WARNING",
            f"Insecure: {', '.join(insecure)}",
            "Run 'chmod 600 .env' etc.",
        )


def check_mt5_config():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    login = os.getenv("MT5_LOGIN", "0")
    pwd = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")

    if login != "0" and pwd and server:
        return DiagnosticCheck("MT5 Credentials", "OK", f"Configured for {server}")
    else:
        remedy = (
            "Run 'python main.py --setup'. On Linux, you may need MetaAPI credentials."
            if sys.platform != "win32"
            else "Run 'python main.py --setup' and provide your MT5 credentials."
        )
        return DiagnosticCheck(
            "MT5 Credentials",
            "WARNING",
            "Incomplete MT5 configuration",
            remedy,
        )


def main():
    # Ensure root is in path
    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root))

    checks = [
        check_python_version(),
        check_dependencies(),
        check_requirement_harmonization(),
        check_env_file(),
        check_talib(),
        check_hardware_acceleration(),
        check_database(),
        check_file_permissions(),
        check_mt5_config(),
    ]

    version = get_system_version()

    if HAS_RICH:
        console.print(
            Panel(
                Text.from_markup(
                    f"[bold blue]MT5 AI/ML Trading Bot - System Doctor[/]\n[dim]Version {version} | {platform.system()} {platform.release()}[/]"
                ),
                border_style="blue",
            )
        )

        table = Table(box=None, expand=True)
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Message")
        table.add_column("Suggested Remedy", style="green")

        for c in checks:
            status_color = (
                "green" if c.status == "OK" else "yellow" if c.status == "WARNING" else "red"
            )
            table.add_row(
                c.name,
                f"[{status_color}]{c.status}[/]",
                c.message,
                c.remedy if c.status != "OK" else "",
            )

        console.print(table)

        failed = any(c.status == "FAILED" for c in checks)
        if failed:
            console.print(
                Panel(
                    "[bold red]SYSTEM HAS CRITICAL ISSUES[/]\nPlease resolve the 'FAILED' items above before starting the bot.",
                    border_style="red",
                )
            )
            sys.exit(1)
        else:
            console.print(
                Panel(
                    "[bold green]SYSTEM READY[/]\nYour environment is correctly configured for trading.",
                    border_style="green",
                )
            )
            sys.exit(0)
    else:
        # Plain text fallback
        print(f"=== MT5 AI/ML Trading Bot Doctor (v{version}) ===")
        print(f"Platform: {platform.system()} {platform.release()}")
        print("-" * 50)
        failed = False
        for c in checks:
            print(f"[{c.status:7}] {c.name:20}: {c.message}")
            if c.status != "OK":
                print(f"          REMEDY: {c.remedy}")
            if c.status == "FAILED":
                failed = True

        print("-" * 50)
        if failed:
            print("CRITICAL ISSUES FOUND. Resolve them and try again.")
            sys.exit(1)
        else:
            print("SYSTEM READY.")
            sys.exit(0)


if __name__ == "__main__":
    main()
