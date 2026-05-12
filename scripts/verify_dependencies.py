
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
            # Simple regex to match package==version
            match = re.match(r'^([^;=<>!~]+)([=<>!~]+.*)$', line)
            if match:
                package = match.group(1).strip()
                version = match.group(2).strip()
                requirements[package] = version
    return requirements

def main():
    root = Path(__file__).resolve().parents[1]
    req_files = list(root.glob('requirements*.txt'))

    all_requirements = {}
    mismatches = []

    for req_file in req_files:
        reqs = parse_requirements(req_file)
        for package, version in reqs.items():
            if package in all_requirements:
                if all_requirements[package]['version'] != version:
                    mismatches.append({
                        'package': package,
                        'file1': all_requirements[package]['file'],
                        'version1': all_requirements[package]['version'],
                        'file2': req_file.name,
                        'version2': version
                    })
            else:
                all_requirements[package] = {'version': version, 'file': req_file.name}

    if mismatches:
        print("Dependency mismatches found:")
        for m in mismatches:
            print(f"Package: {m['package']}")
            print(f"  {m['file1']}: {m['version1']}")
            print(f"  {m['file2']}: {m['version2']}")
        sys.exit(1)
    else:
        print("All overlapping dependencies are harmonized across requirements files.")
        sys.exit(0)

if __name__ == "__main__":
    main()
