import sys
import subprocess
import os
from pathlib import Path

def run_command(command, cwd=None):
    process = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    return process.returncode, process.stdout, process.stderr

def validate_migrations():
    repo_root = Path(__file__).resolve().parents[1]

    # Use a temporary SQLite database for validation
    db_file = repo_root / "temp_validation.db"
    if db_file.exists():
        os.remove(db_file)

    db_url = f"sqlite:///{db_file}"

    print(f"Testing migrations against {db_url}")

    # Upgrade to head
    print("Upgrading to head...")
    rc, stdout, stderr = run_command(f"alembic -x db_url={db_url} upgrade head", cwd=repo_root)
    if rc != 0:
        print(f"Error during upgrade: {stderr}")
        return False

    # Downgrade to base
    print("Downgrading to base...")
    rc, stdout, stderr = run_command(f"alembic -x db_url={db_url} downgrade base", cwd=repo_root)
    if rc != 0:
        print(f"Error during downgrade: {stderr}")
        return False

    # Cleanup
    if db_file.exists():
        os.remove(db_file)

    print("Migrations are valid and reversible.")
    return True

if __name__ == "__main__":
    if not validate_migrations():
        sys.exit(1)
    sys.exit(0)
