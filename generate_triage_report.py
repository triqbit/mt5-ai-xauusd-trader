import json
import os
import datetime
import urllib.request
import urllib.error
import sys

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "triqbit/mt5-ai-xauusd-trader"

def api_call(url):
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("User-Agent", "Jules06-Triage-Bot")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error for {url}: {e.code} {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error for {url}: {e}", file=sys.stderr)
        return None

def get_all_prs():
    prs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/pulls?state=open&per_page=100&page={page}"
        data = api_call(url)
        if data is None or not isinstance(data, list):
            break
        prs.extend(data)
        if len(data) < 100:
            break
        page += 1
    return prs

def get_all_pr_files(pr_number):
    files = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/files?per_page=100&page={page}"
        data = api_call(url)
        if data is None or not isinstance(data, list):
            break
        files.extend([f['filename'] for f in data if 'filename' in f])
        if len(data) < 100:
            break
        page += 1
    return files

def get_ci_status(sha):
    url = f"https://api.github.com/repos/{REPO}/commits/{sha}/status"
    status_data = api_call(url)
    if status_data and 'state' in status_data:
        return status_data['state']
    return 'unknown'

def classify_risk(files):
    high_risk_patterns = [
        "src/trading/",
        "src/models/",
        "src/core/config.py",
        "migrations/",
        "main.py",
        "alembic.ini",
        "pyproject.toml"
    ]
    medium_risk_patterns = [
        "src/research/",
        "src/analytics/",
        "src/core/",
        "src/environment/"
    ]

    risk = "Safe Surface"
    reason = "Only documentation, tests, or non-critical configurations."

    if not files:
        return "Unknown", "No files found or unable to fetch files."

    for f in files:
        for p in high_risk_patterns:
            if p in f:
                return "High Risk", f"Touches high-risk area: {f}"
        for p in medium_risk_patterns:
            if p in f:
                risk = "Medium Risk"
                reason = f"Touches core/research/analytics: {f}"

    return risk, reason

def generate_report():
    print("Fetching PRs...")
    prs = get_all_prs()
    if not prs:
        print("No open PRs found or rate limited.")
        # If rate limited and running in CI, this should fail the job
        if os.getenv("GITHUB_ACTIONS") and not GITHUB_TOKEN:
            sys.exit(1)
        # For local testing, we might just have no PRs
        if not prs:
            prs = []

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = "# Daily PR Triage Dashboard\n\n"
    report += f"Generated on: {now}\n\n"

    report += "## Summary Table\n\n"
    report += "| PR # | Title | Author | Branch | Labels | CI Status | Risk Class | Reason |\n"
    report += "|------|-------|--------|--------|--------|-----------|------------|--------|\n"

    classified_prs = []

    for i, pr in enumerate(prs):
        num = pr['number']
        title = pr['title']
        user = pr['user']['login']
        branch = pr['head']['ref']
        labels = ", ".join([l['name'] for l in pr['labels']]) if pr['labels'] else "none"
        sha = pr['head']['sha']

        print(f"[{i+1}/{len(prs)}] Processing PR #{num}...")

        ci_status = get_ci_status(sha)
        files = get_all_pr_files(num)
        risk, reason = classify_risk(files)

        report += f"| [{num}](https://github.com/{REPO}/pull/{num}) | {title} | {user} | `{branch}` | {labels} | {ci_status} | {risk} | {reason} |\n"

        classified_prs.append({
            'number': num,
            'title': title,
            'user': user,
            'risk': risk,
            'ci_status': ci_status,
            'title_full': title,
            'user_login': user
        })

    report += "\n## Good Candidates for Review Today\n\n"

    safe_surface = [pr for pr in classified_prs if pr['risk'] == "Safe Surface"]
    medium_risk = [pr for pr in classified_prs if pr['risk'] == "Medium Risk"]

    safe_surface.sort(key=lambda x: 0 if x['ci_status'] == 'success' else 1)
    medium_risk.sort(key=lambda x: 0 if x['ci_status'] == 'success' else 1)

    candidates = (safe_surface + medium_risk)[:4]

    if not candidates:
        report += "No low/medium risk candidates identified today.\n"
    else:
        for c in candidates:
            status_str = f" [CI: {c['ci_status']}]" if c['ci_status'] != 'unknown' else ""
            report += f"- **PR #{c['number']}**: {c['title_full']} ({c['user_login']}){status_str} - *{c['risk']}*\n"

    report += "\n---\n*Note: This report is generated by Jules06 (qufuwan). Risk classification is based on file paths.*"

    # Write to file
    os.makedirs("docs/status", exist_ok=True)
    with open("docs/status/PR_TRIAGE_DAILY.md", "w") as f:
        f.write(report)

    # Also write to GitHub Step Summary if available
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(report)

    print("Report generated successfully.")

if __name__ == "__main__":
    generate_report()
