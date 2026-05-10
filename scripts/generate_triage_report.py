import datetime
import json
import os
import sys
import urllib.error
import urllib.request

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "triqbit/mt5-ai-xauusd-trader"
BIG_BANG_DATE = datetime.datetime(2026, 5, 10, tzinfo=datetime.timezone.utc)


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
        url = (
            f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/files?per_page=100&page={page}"
        )
        data = api_call(url)
        if data is None or not isinstance(data, list):
            break
        files.extend([f["filename"] for f in data if "filename" in f])
        if len(data) < 100:
            break
        page += 1
    return files


def get_ci_status(sha):
    url = f"https://api.github.com/repos/{REPO}/commits/{sha}/status"
    status_data = api_call(url)
    if status_data and "state" in status_data:
        return status_data["state"]
    return "unknown"


def get_domains(files):
    if not files:
        return ["Unknown"]

    domains = set()
    mapping = {
        "docs/": "docs",
        "README.md": "docs",
        "tests/": "tests",
        ".github/": "infra/CI",
        "scripts/": "infra/scripts",
        "src/trading/": "core trading",
        "src/risk/": "risk",
        "src/models/": "AI models",
        "src/core/": "core architecture",
        "src/research/": "research",
        "src/analytics/": "analytics",
        "Makefile": "infra",
        "Dockerfile": "infra",
        "requirements": "dependencies",
        "pyproject.toml": "dependencies",
        "migrations/": "database",
        "SECURITY": "security",
    }

    for f in files:
        matched = False
        for pattern, domain in mapping.items():
            if pattern in f:
                # Avoid false positives for dependencies like requirements.md
                if pattern == "requirements" and not (f.endswith(".txt") or f.endswith(".pip")):
                    continue
                domains.add(domain)
                matched = True
        if not matched:
            domains.add("other")

    return sorted(domains)


def classify_risk(files, title=""):
    high_risk_patterns = [
        "src/trading/",
        "src/models/",
        "src/core/config.py",
        "migrations/",
        "main.py",
        "alembic.ini",
        "pyproject.toml",
        "Dockerfile",
        ".github/",
        "Makefile",
        "scripts/",
    ]
    medium_risk_patterns = [
        "src/research/",
        "src/analytics/",
        "src/core/",
        "src/environment/",
    ]

    safe_keywords = ["docs", "readme", "lint", "typo", "cleanup", "chore", "dx:"]

    # Heuristic based on title (useful if no files due to rate limit)
    t_lower = title.lower()
    is_likely_safe = any(kw in t_lower for kw in safe_keywords)

    if not files:
        if is_likely_safe:
            return "Safe Surface", "Heuristic: Title matches safe keywords."
        return "Triage Required", "No files found or unable to fetch files."

    for f in files:
        for p in high_risk_patterns:
            if p in f:
                return "High Risk", f"Touches high-risk area: {f}"
        for p in medium_risk_patterns:
            if p in f:
                return "Medium Risk", f"Touches core/research/analytics/risk: {f}"

    return "Safe Surface", "Only documentation, tests, or non-critical configurations."


def get_recommendation(risk, domains, ci_status):
    if risk == "High Risk":
        return "High-risk — needs domain expert review"

    if ci_status != "success":
        return "Needs CI success before merge"

    if "tests" not in domains and risk != "Safe Surface":
        return "Needs tests/docs before merge"

    return "Ready for detailed review"


def generate_report():
    print("Fetching PRs...")
    prs = get_all_prs()

    if not prs and prs is not None:
        print("No open PRs found.")
    elif prs is None:
        print("Rate limited or error fetching PRs.")
        prs = []

    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    status_tag = "🟢 HEALTHY"
    turbulence_reasons = []

    if len(prs) > 50:
        status_tag = "🟡 MODERATE TURBULENCE"
        turbulence_reasons.append(f"High number of open PRs ({len(prs)})")
    if len(prs) > 200:
        status_tag = "🔴 HIGH TURBULENCE"

    report = "# Daily PR Triage Dashboard\n\n"
    report += f"**Date:** {now_str}\n"
    report += f"**Status:** {status_tag}\n\n"

    if turbulence_reasons:
        report += "### Turbulence Factors:\n"
        for res in turbulence_reasons:
            report += f"- {res}\n"
        report += "\n"

    report += "---\n\n"
    report += "## 🔝 Top 3 Items That Matter Right Now\n\n"
    # We will populate this later

    report += "## 📋 Summary Table\n\n"
    report += "| PR # | Title | Author | Branch | CI Status | Risk Class | Status Flag |\n"
    report += "|------|-------|--------|--------|-----------|------------|-------------|\n"

    classified_prs = []

    # Heuristic: Process latest 20 PRs in detail, then use heuristics for the rest if no token
    detailed_limit = 20 if not GITHUB_TOKEN else 100

    for i, pr in enumerate(prs):
        num = pr["number"]
        title = pr["title"]
        user = pr["user"]["login"]
        branch = pr["head"]["ref"]
        sha = pr["head"]["sha"]
        created_at = datetime.datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )

        status_flag = "New"
        if created_at < BIG_BANG_DATE:
            status_flag = "⚠️ Stale (Pre-Big-Bang)"

        print(f"[{i + 1}/{len(prs)}] Processing PR #{num}...")

        if i < detailed_limit:
            ci_status = get_ci_status(sha)
            files = get_all_pr_files(num)
            risk, reason = classify_risk(files, title)
            domains = get_domains(files)
        else:
            ci_status = "unknown"
            risk, reason = classify_risk([], title)
            domains = ["Triage Required"]
            if risk == "Unknown":
                risk = "Triage Required"

        report += f"| [{num}](https://github.com/{REPO}/pull/{num}) | {title} | {user} | `{branch}` | {ci_status} | {risk} | {status_flag} |\n"

        classified_prs.append(
            {
                "number": num,
                "title": title,
                "user": user,
                "risk": risk,
                "ci_status": ci_status,
                "reason": reason,
                "flag": status_flag,
                "domains": domains,
            }
        )

    # Determine Top 3 (Prioritize "New" PRs over "Stale")
    top_3_items = []
    if turbulence_reasons:
        top_3_items.append(f"**Address Turbulence:** {turbulence_reasons[0]}")

    new_prs = [pr for pr in classified_prs if pr["flag"] == "New"]
    safe_surface = [pr for pr in new_prs if pr["risk"] == "Safe Surface"]
    medium_risk = [pr for pr in new_prs if pr["risk"] == "Medium Risk"]
    high_risk = [pr for pr in new_prs if pr["risk"] == "High Risk"]

    if safe_surface:
        top_3_items.append(
            f"**Quick Win:** Review Safe PR #{safe_surface[0]['number']} ({safe_surface[0]['title']})"
        )
    if medium_risk:
        top_3_items.append(
            f"**Core Progress:** Review Medium Risk PR #{medium_risk[0]['number']} ({medium_risk[0]['title']})"
        )
    elif high_risk:
        top_3_items.append(
            f"**Critical Path:** High Risk PR #{high_risk[0]['number']} needs expert review."
        )

    top_3_section = ""
    for idx, item in enumerate(top_3_items[:3]):
        top_3_section += f"{idx + 1}. {item}\n"

    if not top_3_section:
        top_3_section = "No urgent items identified today.\n"

    report = report.replace(
        "## 🔝 Top 3 Items That Matter Right Now\n\n",
        "## 🔝 Top 3 Items That Matter Right Now\n\n" + top_3_section + "\n",
    )

    new_triage_required = [
        pr for pr in classified_prs if pr["risk"] == "Triage Required" and pr["flag"] == "New"
    ]

    report += "\n## 🛡️ Risk Classification Summary\n\n"
    report += f"- **High Risk (New):** {len(high_risk)} PRs\n"
    report += f"- **Medium Risk (New):** {len(medium_risk)} PRs\n"
    report += f"- **Safe Surface (New):** {len(safe_surface)} PRs\n"
    report += f"- **Triage Required (New):** {len(new_triage_required)} PRs\n"
    report += (
        f"- **Stale (Total):** {len([pr for pr in classified_prs if 'Stale' in pr['flag']])} PRs\n"
    )

    report += "\n## ✨ Good Candidates for Review Today\n\n"
    candidates = (safe_surface + medium_risk)[:4]

    if not candidates:
        report += "No new low/medium risk candidates identified today.\n"
    else:
        for c in candidates:
            status_str = f" [CI: {c['ci_status']}]" if c["ci_status"] != "unknown" else ""
            report += (
                f"- **PR #{c['number']}**: {c['title']} ({c['user']}){status_str} - *{c['risk']}*\n"
            )

    report += "\n---\n*Note: This report is generated by Jules06 (qufuwan). Risk classification is based on file paths and heuristics.*"

    os.makedirs("docs/status", exist_ok=True)
    with open("docs/status/PR_TRIAGE_DAILY.md", "w") as f:
        f.write(report)

    # Generate Merge-Readiness Checklist
    checklist = "# Merge-Readiness Checklist\n\n"
    checklist += "> [!IMPORTANT]\n"
    checklist += "> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules.\n\n"
    checklist += f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    checklist += "This checklist identifies top promising PRs for immediate review.\n\n"

    top_3 = (safe_surface + medium_risk)[:3]
    if not top_3:
        checklist += "No new low-risk candidates found for merge-readiness checklist today.\n"
    else:
        for i, c in enumerate(top_3):
            checklist += f"## {i + 1}. PR #{c['number']}: {c['title']}\n"
            checklist += (
                f"- **Short scope summary**: {c['risk']} update implementing '{c['title']}'\n"
            )
            checklist += f"- **Domains touched**: {', '.join(c['domains'])}\n"
            checklist += f"- **CI status**: {c['ci_status']}\n"

            missing = []
            if "tests" not in c["domains"] and c["risk"] != "Safe Surface":
                missing.append("tests")
            if "docs" not in c["domains"] and c["risk"] != "Safe Surface":
                missing.append("docs")

            checklist += (
                f"- **Missing items**: {', '.join(missing) if missing else 'None identified'}\n"
            )
            checklist += f"- **Recommendation**: {get_recommendation(c['risk'], c['domains'], c['ci_status'])}\n\n"

    checklist += "---\n*Prepared by Jules06 (qufuwan) for Jules05 and human review.*\n"

    with open("docs/status/MERGE_READY_CHECKLIST.md", "w") as f:
        f.write(checklist)

    print("Reports generated successfully.")


if __name__ == "__main__":
    generate_report()
