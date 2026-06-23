from scripts.generate_triage_report import classify_risk

prs = [
    (1528, "docs: improve developer onboarding and contribution experience"),
    (1525, "docs: update process integrity log [2026-06-15]"),
    (1510, "chore(deps): bump torch from 2.5.1+cpu to 2.12.0+cpu"),
    (1470, "docs: update daily merge-readiness checklist [2026-06-03]"),
    (1409, "docs: Daily PR triage and risk dashboard [2026-05-23]"),
]

for num, title in prs:
    risk, reason = classify_risk([], title)
    print(f"PR #{num}: {risk} - {reason}")
