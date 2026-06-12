import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

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
        if data is None:
            if page == 1:
                return None  # Signal failure on first page
            break
        if not isinstance(data, list):
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
        if data is None:
            return None  # Signal failure
        if not isinstance(data, list):
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


def get_latest_main_commit_info():
    """Fetches the timestamp and SHA of the latest commit on main to detect history grafts."""
    url = f"https://api.github.com/repos/{REPO}/branches/main"
    data = api_call(url)
    if data and "commit" in data:
        commit_sha = data["commit"]["sha"]
        commit_data = data["commit"]["commit"]
        date_str = commit_data["committer"]["date"]
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
        return dt, commit_sha

    # Fallback to local git if API fails
    try:
        cmd = ["git", "log", "-1", "--format=%cI", "main"]
        date_result = subprocess.check_output(cmd).decode().strip()
        dt = datetime.datetime.fromisoformat(date_result).astimezone(datetime.timezone.utc)
        cmd_sha = ["git", "rev-parse", "main"]
        sha = subprocess.check_output(cmd_sha).decode().strip()
        return dt, sha
    except Exception as e:
        print(f"Local git fallback failed: {e}", file=sys.stderr)

    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1), "unknown"


def load_cache():
    """Loads existing PR data from the daily report to avoid triage regressions or data loss during rate limits."""
    cache = {}
    path = "docs/status/PR_TRIAGE_DAILY.md"
    if not os.path.exists(path):
        return cache

    try:
        with open(path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("| ["):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 8:
                        # Extract PR number from [123](...)
                        num_part = parts[1]
                        pr_num_str = num_part.split("]")[0].replace("[", "")
                        if not pr_num_str.isdigit():
                            continue

                        num = int(pr_num_str)
                        title = parts[2]
                        user = parts[3]
                        branch = parts[4].replace("`", "")
                        labels = parts[5]
                        ci_status = parts[6]
                        risk = parts[7]
                        flag = parts[8]

                        cache[num] = {
                            "number": num,
                            "title": title,
                            "user": user,
                            "branch": branch,
                            "labels": labels,
                            "ci_status": ci_status,
                            "risk": risk,
                            "flag": flag,
                        }
    except Exception as e:
        print(f"Warning: Failed to load triage cache: {e}", file=sys.stderr)

    return cache


def get_domains(files, title=""):
    if not files:
        # Heuristics based on title
        t_lower = title.lower()
        domains = []
        if "docs" in t_lower or "readme" in t_lower:
            domains.append("docs")
        if "test" in t_lower:
            domains.append("tests")
        if "deps" in t_lower or "bump" in t_lower:
            domains.append("dependencies")
        if "dx:" in t_lower:
            domains.append("docs")
            domains.append("infra/scripts")
        if "refactor" in t_lower:
            domains.append("refactor")
        if "chore" in t_lower:
            domains.append("chore")
        if "ci" in t_lower:
            domains.append("infra/CI")

        if not domains:
            return ["Triage Required"]
        return sorted(set(domains))

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
    # Clean up repetitive naming in titles (e.g., "(deps)(deps)")
    title = title.replace("(deps)(deps)", "(deps)")

    # Critical system files that should always trigger High Risk
    high_risk_patterns = [
        "src/trading/",
        "src/models/",
        "src/core/config.py",
        "src/environment/",
        "migrations/",
        "main.py",
        "alembic.ini",
        "Dockerfile",
        ".github/workflows/",  # CI pipeline changes are high risk
    ]

    # Files that are important but not immediately critical to trading execution
    medium_risk_patterns = [
        "src/research/",
        "src/analytics/",
        "src/core/",
        "src/monitoring/",
        "Makefile",
        "scripts/",
        "pyproject.toml",
        "requirements",
    ]

    # High-impact title keywords
    high_risk_keywords = [
        "trading",
        "risk",
        "engine",
        "security",
        "model",
        "connector",
        "allocator",
        "coherence",
        "governance",
    ]
    medium_risk_keywords = [
        "research",
        "analytics",
        "environment",
        "cli",
        "ux",
        "makefile",
        "api",
        "observability",
        "validation",
    ]
    safe_keywords = [
        "docs",
        "readme",
        "lint",
        "typo",
        "cleanup",
        "chore",
        "dx:",
        "dashboard",
        "integrity",
    ]

    # Specific exceptions for safe surfaces within medium/high risk paths
    safe_file_patterns = [
        "docs/",
        "README.md",
        "PR_TRIAGE_DAILY.md",
        "MERGE_READY_CHECKLIST.md",
        ".md",
        "tests/",
        "scripts/generate_triage_report.py",
        "scripts/doctor.py",
        "scripts/bootstrap.sh",
    ]

    t_lower = title.lower()
    is_likely_safe = any(kw in t_lower for kw in safe_keywords)

    if not files:
        if is_likely_safe:
            return "Safe Surface", "Heuristic: Title matches safe keywords."
        if any(kw in t_lower for kw in high_risk_keywords):
            return "High Risk", "Heuristic: Title matches high-risk keywords."
        if any(kw in t_lower for kw in medium_risk_keywords):
            return "Medium Risk", "Heuristic: Title matches medium-risk keywords."
        return "Triage Required", "No files found or unable to fetch files."

    # First check if ALL files are in safe patterns
    all_safe = True
    for f in files:
        if not any(sp in f for sp in safe_file_patterns):
            all_safe = False
            break

    if all_safe:
        return "Safe Surface", "Only documentation or tests."

    # Check for High Risk
    for f in files:
        for p in high_risk_patterns:
            if p in f:
                # Exception: if it's a doc change in a high risk path, don't trigger yet
                if f.endswith(".md"):
                    continue
                return "High Risk", f"Touches high-risk area: {f}"

    # Check for Medium Risk
    for f in files:
        for p in medium_risk_patterns:
            if p in f:
                if f.endswith(".md"):
                    continue
                # General check for minor dependency bumps in non-core packages
                safe_deps = [
                    "click",
                    "rich",
                    "tabulate",
                    "jinja2",
                    "pytz",
                    "colorlog",
                    "tqdm",
                    "gymnasium",
                    "stable-baselines3",
                ]
                if "bump" in t_lower and any(sd in t_lower for sd in safe_deps):
                    return "Safe Surface", f"Minor dependency bump: {t_lower}"
                return "Medium Risk", f"Touches core/research/analytics/risk: {f}"

    return "Safe Surface", "Non-critical surface area."


def get_recommendation(risk, domains, ci_status):
    if risk == "High Risk":
        return "High-risk — needs domain expert review"

    if ci_status != "success":
        return "Needs CI success before merge"

    if "tests" not in domains and risk != "Safe Surface":
        return "Needs tests/docs before merge"

    return "Ready for detailed review"


def generate_report():
    print("Fetching repository state...")
    big_bang_date, big_bang_sha = get_latest_main_commit_info()
    print(f"Latest history graft detected at: {big_bang_date} (SHA: {big_bang_sha})")

    cache = load_cache()
    if cache:
        print(f"Loaded {len(cache)} cached risk classifications.")

    print("Fetching PRs...")
    prs = get_all_prs()

    if prs is None:
        print(
            "WARNING: Rate limited or error fetching PRs. Attempting to rebuild report from cache.",
            file=sys.stderr,
        )
        if not cache:
            print(
                "CRITICAL: No cache available and API failed. Aborting.",
                file=sys.stderr,
            )
            return

        # Convert cache to the format expected by the rest of the script
        prs_from_cache = []
        # Sort by number descending
        for num in sorted(cache.keys(), reverse=True):
            entry = cache[num]
            prs_from_cache.append({
                "number": entry["number"],
                "title": entry["title"],
                "user": {"login": entry["user"]},
                "head": {"ref": entry["branch"], "sha": "unknown"},
                "created_at": "2020-01-01T00:00:00Z", # Placeholder, flag is used
                "labels": [{"name": l.strip()} for l in entry["labels"].split(",") if l.strip() != "none"],
                "from_cache": True,
                "cached_flag": entry["flag"],
                "cached_ci": entry["ci_status"],
                "cached_risk": entry["risk"],
            })
        prs = prs_from_cache

    if not prs:
        print("No open PRs found.")

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
    report += "| PR # | Title | Author | Branch | Labels | CI Status | Risk Class | Status Flag |\n"
    report += "|------|-------|--------|--------|--------|-----------|------------|-------------|\n"

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
        if created_at < big_bang_date:
            status_flag = "⚠️ Stale (Pre-Big-Bang)"

        labels = [label["name"] for label in pr.get("labels", [])]
        labels_str = ", ".join(labels) if labels else "none"

        print(f"[{i + 1}/{len(prs)}] Processing PR #{num}...")

        if pr.get("from_cache"):
            status_flag = pr["cached_flag"]
            ci_status = pr["cached_ci"]
            risk, reason = classify_risk([], title)
            # Prioritize previous risk if current title-only heuristic is weaker
            if (
                pr.get("cached_risk")
                and pr["cached_risk"] != "Triage Required"
                and risk == "Triage Required"
            ):
                risk = pr["cached_risk"]
                reason = "Preserved from previous report."
            domains = get_domains([], title)
        elif i < detailed_limit:
            ci_status = get_ci_status(sha)
            files = get_all_pr_files(num)
            if files is None:
                print(f"Warning: Failed to fetch files for PR #{num}. Using heuristics.")
                if num in cache:
                    risk, reason = classify_risk([], title)
                else:
                    risk, reason = classify_risk([], title)
                domains = get_domains([], title)
            else:
                risk, reason = classify_risk(files, title)
                domains = get_domains(files, title)
        else:
            ci_status = "unknown"
            risk, reason = classify_risk([], title)
            domains = get_domains([], title)
            if risk == "Unknown":
                risk = "Triage Required"

        # Clean up title for the report
        clean_title = title.replace("(deps)(deps)", "(deps)")

        report += f"| [{num}](https://github.com/{REPO}/pull/{num}) | {clean_title} | {user} | `{branch}` | {labels_str} | {ci_status} | {risk} | {status_flag} |\n"

        classified_prs.append(
            {
                "number": num,
                "title": clean_title,
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
    if high_risk:
        for hr in high_risk:
            if len(top_3_items) >= 3:
                break
            top_3_items.append(
                f"**Critical Path:** High Risk PR #{hr['number']} needs expert review."
            )

    # Backfill from Stale PRs if needed
    if len(top_3_items) < 3:
        stale_candidates = [
            pr for pr in classified_prs if "Stale" in pr["flag"] and pr["risk"] != "Triage Required"
        ]
        stale_safe = [pr for pr in stale_candidates if pr["risk"] == "Safe Surface"]
        stale_medium = [pr for pr in stale_candidates if pr["risk"] == "Medium Risk"]

        for s_pr in stale_safe + stale_medium:
            if len(top_3_items) >= 3:
                break
            if f"PR #{s_pr['number']}" not in str(top_3_items):
                top_3_items.append(
                    f"**Re-validate Stale:** Review {s_pr['risk']} PR #{s_pr['number']} ({s_pr['title']})"
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

    def plural(n):
        return "" if n == 1 else "s"

    report += f"- **High Risk (New):** {len(high_risk)} PR{plural(len(high_risk))}\n"
    report += f"- **Medium Risk (New):** {len(medium_risk)} PR{plural(len(medium_risk))}\n"
    report += f"- **Safe Surface (New):** {len(safe_surface)} PR{plural(len(safe_surface))}\n"
    report += f"- **Triage Required (New):** {len(new_triage_required)} PR{plural(len(new_triage_required))}\n"
    stale_count = len([pr for pr in classified_prs if "Stale" in pr["flag"]])
    report += f"- **Stale (Total):** {stale_count} PR{plural(stale_count)}\n"

    report += "\n## ✨ Good Candidates for Review Today\n\n"
    # Exclude High Risk and Triage/Dashboard reports from daily candidates to focus on safe/utility zones
    filtered_safe = [
        pr
        for pr in safe_surface
        if "triage" not in pr["title"].lower() and "dashboard" not in pr["title"].lower()
    ]
    candidates = (filtered_safe + medium_risk)[:4]
    if len(candidates) < 3:
        stale_candidates = [
            pr for pr in classified_prs if "Stale" in pr["flag"] and pr["risk"] != "Triage Required"
        ]
        stale_filtered_safe = [
            pr
            for pr in stale_candidates
            if pr["risk"] == "Safe Surface"
            and "triage" not in pr["title"].lower()
            and "dashboard" not in pr["title"].lower()
        ]
        stale_medium = [pr for pr in stale_candidates if pr["risk"] == "Medium Risk"]
        candidates.extend((stale_filtered_safe + stale_medium)[: 4 - len(candidates)])

    if not candidates:
        report += "No new candidates identified today.\n"
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
    # Generate Merge-Readiness Checklist (Strictly Low/Medium Risk)
    checklist = "# Merge-Readiness Checklist\n\n"
    checklist += "> [!IMPORTANT]\n"
    checklist += f"> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules. **Mandatory rebase against commit `{big_bang_sha}` is required for all PRs.**\n\n"
    checklist += f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    checklist += "This checklist identifies top promising PRs for immediate review.\n\n"

    top_3 = candidates[:3]
    if not top_3:
        checklist += "No new candidates found for merge-readiness checklist today.\n"
    else:
        for i, c in enumerate(top_3):
            checklist += f"## {i + 1}. PR #{c['number']}: {c['title']}\n"
            status_note = ""
            if "Stale" in c["flag"]:
                status_note = " (Candidate for re-validation/review)"

            checklist += f"- **Short scope summary**: {c['risk']} update implementing '{c['title']}'{status_note}\n"
            checklist += f"- **Domains touched**: {', '.join(c['domains'])}\n"
            checklist += f"- **CI status**: {c['ci_status']}\n"

            missing = [f"Mandatory rebase against commit `{big_bang_sha}`"]
            if "tests" not in c["domains"] and c["risk"] != "Safe Surface":
                missing.append("tests")
            if "docs" not in c["domains"] and c["risk"] != "Safe Surface":
                missing.append("docs")

            checklist += f"- **Missing items**: {', '.join(missing)}\n"
            checklist += f"- **Recommendation**: {get_recommendation(c['risk'], c['domains'], c['ci_status'])}\n\n"

    checklist += "---\n*Prepared by Jules06 (qufuwan) for Jules05 and human review.*\n"

    with open("docs/status/MERGE_READY_CHECKLIST.md", "w") as f:
        f.write(checklist)

    print("Reports generated successfully.")


if __name__ == "__main__":
    generate_report()
