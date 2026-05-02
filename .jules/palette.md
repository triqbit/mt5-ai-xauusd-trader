# Palette's Journal - UX & Accessibility Learnings

## 2026-05-22 - [Standardizing CLI UX with Rich]
**Learning:** Terminal-based trading bots often suffer from "log-spam" where critical startup failures (config errors, health checks) are buried in flat text. Using structured tables and status spinners significantly improves the operator's ability to diagnose startup issues at a glance.
**Action:** Replace text-based health and config reports with `rich` tables and use `console.status` for long-running startup tasks like MT5 connection.
