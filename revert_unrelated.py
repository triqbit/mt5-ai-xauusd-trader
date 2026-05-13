import os
import subprocess

touched = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-linux.txt",
    "requirements-docker.txt",
    "requirements-ci.txt",
    "requirements-ci-no-talib.txt",
    "scripts/doctor.py",
    "scripts/verify_ux_terminal.py"
}

with open("modified_files.txt", "r") as f:
    for line in f:
        filepath = line.strip()
        if filepath not in touched and os.path.exists(filepath):
            print(f"Reverting {filepath}")
            subprocess.run(["git", "checkout", "--", filepath])
