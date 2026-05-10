# Security Policy

> **CRITICAL NOTICE**
> This repository contains autonomous trading software that interfaces
> with live financial markets, broker credentials, and real capital.
> Security vulnerabilities in this codebase carry direct financial risk.
> All security reports MUST use the private channels defined below.
> **Never disclose vulnerabilities publicly before a fix is released.**

---

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [What to Include in Your Report](#what-to-include-in-your-report)
- [What NOT to Do](#what-not-to-do)
- [Coordinated Disclosure Process](#coordinated-disclosure-process)
- [Vulnerability Scope](#vulnerability-scope)
- [Severity Classification](#severity-classification)
- [Response SLOs](#response-slos)
- [Safe Harbor](#safe-harbor)
- [Security Contacts](#security-contacts)
- [Acknowledgements](#acknowledgements)

---

## Supported Versions

Only the versions listed below receive active security maintenance.
Running an unsupported version in a live trading environment is done
entirely at your own risk.

| Version  | Support Status       | Security Patches | End of Support |
|----------|----------------------|------------------|----------------|
| v1.2.x   | ✅ Actively maintained | ✅ All severities | TBD            |
| v1.1.x   | ⚠️ Critical fixes only | Critical only    | 2026-08-01     |
| ≤ v1.0.x | ❌ End of life         | None             | Ended          |

**Recommendation:** Always deploy the latest patch release.
Enable [Security Advisory notifications](../../security/advisories)
to receive alerts when new advisories are published.

---

## Reporting a Vulnerability

### Method 1 — GitHub Private Vulnerability Reporting (Preferred)

This is the fastest and most secure channel. Reports are fully
encrypted and visible only to repository maintainers.

1. Go to the **[Security](../../security)** tab of this repository
2. Click **"Report a vulnerability"**
3. Fill in the structured form with as much detail as possible
4. Submit — you will receive a confirmation and tracking reference

Your report will never be publicly visible until a coordinated
fix has been released and both parties agree on the timeline.

### Method 2 — Encrypted Email

If GitHub private reporting is unavailable, email:

**security@triqbit.com**

Use the subject line format:
[SECURITY] <Severity> — <One-line description>

Example: [SECURITY] High — MT5 credentials exposed in structlog output


PGP encryption is strongly encouraged for Critical and High severity
reports. Request our public key before sending sensitive content.

---

## What to Include in Your Report

A complete report enables faster triage and remediation. Please
provide as many of the following fields as possible:
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1 — REPORT │
│ Reporter submits via GitHub private advisory or email │
└────────────────────────────┬────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2 — ACKNOWLEDGEMENT [≤48h] │
│ Maintainer confirms receipt and assigns tracking ID │
└────────────────────────────┬────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3 — ASSESSMENT [≤7d] │
│ Severity scored via CVSS 3.1, internal ticket created, │
│ reporter notified of classification and patch timeline │
└────────────────────────────┬────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4 — REMEDIATION [varies] │
│ Patch developed on private branch, peer-reviewed, │
│ validated against original reproduction steps │
└────────────────────────────┬────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5 — RELEASE [varies] │
│ Patch shipped, reporter notified, patch release tagged │
└────────────────────────────┬────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 6 — PUBLIC DISCLOSURE [≤90d] │
│ GitHub Security Advisory published, CVE requested if │
│ warranted, reporter credited unless anonymity requested │
└─────────────────────────────────────────────────────────────┘

If we require more time than the SLO for any stage, we will
proactively notify the reporter with a revised timeline and
written justification before the deadline passes.

---

## Vulnerability Scope

### In Scope

| Category | Specific Examples |
|---|---|
| **Credential Exposure** | MT5 password/token in logs, `.env` leakage, SecretStr bypass, dynamic discovery gaps, URL credential leaks |
| **Trade Execution** | RiskManager approval bypass, signal injection, order tampering |
| **Database Layer** | SQL injection in TradeLogger, Alembic migration tampering, constraint bypass |
| **Model Integrity** | Unsafe deserialization of PPO/LSTM/Dreamer weights, model poisoning |
| **CI/CD Pipeline** | GitHub Actions workflow injection, secrets in step outputs or artifacts |
| **Dependency Chain** | Exploitable CVEs in `requirements.txt`, `requirements-ci.txt`, `Dockerfile` |
| **File Permissions** | Privilege escalation via DB file (`0o600`) or config file permissions |
| **API Endpoints** | Unauthenticated FastAPI health endpoint abuse, information disclosure |
| **Audit Trail** | AuditLogger tampering, log deletion, decision chain bypass |
| **Macro Intelligence** | EventIntelligence manipulation to force trades during blocked windows |

### Out of Scope

- MetaTrader 5 terminal application and broker server infrastructure
- Third-party model weight files not distributed in this repository
- Vulnerabilities requiring physical access to the deployment host
- Automated scanner output with no demonstrated exploitability
- Denial-of-service via resource exhaustion (network/CPU flooding)
- Social engineering attacks targeting project maintainers
- Dependencies with no viable upgrade path and no realistic
  exploitation vector in the context of this application

---

## Severity Classification

All vulnerabilities are scored using **CVSS v3.1**.
Scores are assigned by maintainers during Stage 3 triage.

| Severity | CVSS v3.1 Score | Project-Specific Examples |
|---|---|---|
| 🔴 **Critical** | 9.0 – 10.0 | Full credential exfiltration, live trade manipulation, complete RiskManager bypass |
| 🟠 **High** | 7.0 – 8.9 | Secrets leaked to logs, DB SQL injection, auth token exposure, position size manipulation |
| 🟡 **Medium** | 4.0 – 6.9 | Partial information disclosure, insecure defaults with limited blast radius |
| 🔵 **Low** | 0.1 – 3.9 | Minor hardening gaps, non-sensitive data exposure, defence-in-depth weaknesses |
| ⚪ **Informational** | N/A | Best practice recommendations, configuration hardening suggestions |

---

## Response SLOs

| Severity | Acknowledgement | Classification | Patch Target | Disclosure |
|---|---|---|---|---|
| 🔴 Critical | 24 hours | 48 hours | 7 days | 30 days post-patch |
| 🟠 High | 48 hours | 5 days | 30 days | 60 days post-patch |
| 🟡 Medium | 5 days | 14 days | 60 days | 90 days post-patch |
| 🔵 Low | 7 days | 30 days | 90 days | 90 days post-patch |
| ⚪ Info | 14 days | 60 days | Best effort | N/A |

SLO clocks start from confirmed receipt of a valid, reproducible report.
Incomplete reports pause the SLO until sufficient information is provided.

---

## Safe Harbor

We consider good-faith security research conducted in accordance
with this policy to be authorised activity. We will not initiate
or support legal action against researchers who:

1. Report through the private channels defined in this document
2. Avoid accessing, modifying, or destroying real user or trade data
3. Refrain from testing against live, production, or broker systems
4. Do not exploit the vulnerability beyond what is necessary to
   demonstrate the issue to maintainers
5. Provide us reasonable time to remediate before any disclosure

This safe harbor covers:

- Claims under the Computer Fraud and Abuse Act (CFAA)
- DMCA Section 1201 anti-circumvention provisions
- Equivalent legislation in your jurisdiction

If a third party initiates legal action against a researcher for
activity conducted in good faith under this policy, we will make
our position in support of the researcher publicly known.

---

## Security Contacts

For **Critical** severity issues, contact both maintainers simultaneously.

| Role | GitHub Handle | Responsibility |
|---|---|---|
| Repo Owner | [@triqbit](https://github.com/triqbit) | Final escalation, release authority |
| Lead Reviewer | [@andonly1348](https://github.com/andonly1348) | Primary triage, patch coordination |
| CI/Security | [@xnessom](https://github.com/xnessom) | Dependency audits, CI pipeline |

---

## Acknowledgements

We publicly thank all researchers who responsibly disclose
vulnerabilities under this policy. Contributors will be credited
in the published GitHub Security Advisory and in
[`SECURITY_HALL_OF_FAME.md`](./docs/SECURITY_HALL_OF_FAME.md)
unless anonymity is explicitly requested at time of report.

---

## Policy Metadata

| Field | Value |
|---|---|
| Policy version | 1.0.0 |
| Effective date | 2026-05-01 |
| Review cadence | Quarterly |
| Next review | 2026-08-01 |
| Standard references | ISO/IEC 29147, CVSS v3.1, FIRST CVD Guidelines |
| Inspired by | [GitHub Security Policy](https://github.com/github/.github/blob/master/SECURITY.md) · [Google VRP](https://bughunters.google.com/about/rules) |

*To propose changes to this policy, open a PR targeting `main`
with the label `security-policy` and request review from
[@andonly1348](https://github.com/andonly1348).*
