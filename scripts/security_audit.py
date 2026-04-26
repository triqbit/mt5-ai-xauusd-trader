"""
Daily Security Audit Script
Checks for dependency vulnerabilities and scans logs for unauthorized access.
"""
import sys
import logging
import subprocess
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))

from src.core.config import get_config
from src.core.monitor import Monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("security_audit")

def run_audit():
    cfg = get_config()
    monitor = Monitor(cfg)

    issues = []

    # 1. Check for vulnerable dependencies
    logger.info("Running pip-audit...")
    try:
        # We use --local to avoid checking global env if not needed, but here we want the project env
        result = subprocess.run(["pip-audit", "--format", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("🔒 *Vulnerability Alert*: pip-audit found issues in dependencies.")
            logger.warning("pip-audit found issues.")
    except FileNotFoundError:
        logger.warning("pip-audit not installed. Skipping dependency check.")

    # 2. Check for suspicious log entries
    logger.info("Scanning logs for anomalies...")
    log_file = root_path / "logs" / "trader.log"
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                content = f.read().lower()
                # Basic checks for typical attack patterns or critical errors
                if "unauthorized" in content or "access denied" in content:
                    issues.append("🕵️ *Security Warning*: 'Unauthorized' or 'Access Denied' found in logs.")
                if "brute force" in content:
                    issues.append("🚨 *Security Alert*: Potential brute force attempt detected in logs.")
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")

    # 3. Report if any issues found
    if issues:
        report = "🛡️ *Security Audit Report*\n" + "\n".join(issues)
        monitor.send_message(report)
        logger.info("Security report sent.")
    else:
        logger.info("No security issues detected.")

if __name__ == "__main__":
    run_audit()
