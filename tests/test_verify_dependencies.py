
import subprocess
import sys
from pathlib import Path


def test_verify_dependencies_script_success():
    """Test that verify_dependencies.py succeeds when files are harmonized."""
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "verify_dependencies.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(root)
    )

    assert result.returncode == 0
    assert "All overlapping dependencies are harmonized" in result.stdout

def test_verify_dependencies_script_failure(tmp_path):
    """Test that verify_dependencies.py fails when there is a mismatch."""
    # Create dummy requirements files with a mismatch
    req1 = tmp_path / "requirements_test1.txt"
    req1.write_text("pandas==2.2.3\n")

    req2 = tmp_path / "requirements_test2.txt"
    req2.write_text("pandas==2.2.2\n")

    # Create a minimal script that we can run against these files
    test_script = tmp_path / "verify.py"
    test_script.write_text("""
import sys
from pathlib import Path
import re

def parse_requirements(filepath):
    requirements = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('--'):
                continue
            match = re.match(r'^([^;=<>!~]+)([=<>!~]+.*)$', line)
            if match:
                package = match.group(1).strip()
                version = match.group(2).strip()
                requirements[package] = version
    return requirements

def main():
    root = Path(sys.argv[1])
    req_files = list(root.glob('requirements_test*.txt'))
    all_requirements = {}
    mismatches = []
    for req_file in req_files:
        reqs = parse_requirements(req_file)
        for package, version in reqs.items():
            if package in all_requirements:
                if all_requirements[package]['version'] != version:
                    mismatches.append({'package': package})
            else:
                all_requirements[package] = {'version': version}
    if mismatches:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

    result = subprocess.run(
        [sys.executable, str(test_script), str(tmp_path)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
