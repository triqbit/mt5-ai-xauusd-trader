# Palette's Journal - UX & Accessibility Learnings

## 2026-05-22 - [Standardizing CLI UX with Rich]
**Learning:** Terminal-based trading bots often suffer from "log-spam" where critical startup failures (config errors, health checks) are buried in flat text. Using structured tables and status spinners significantly improves the operator's ability to diagnose startup issues at a glance.
**Action:** Replace text-based health and config reports with `rich` tables and use `console.status` for long-running startup tasks like MT5 connection.

## 2026-05-23 - [Dynamic Report Navigation]
**Learning:** Hardcoded section numbering in multi-section reports leads to a fragmented user experience when optional sections are omitted. Dynamic numbering and an interactive Table of Contents (TOC) are essential for institutional-grade readability and accessibility.
**Action:** Implement Jinja2-based dynamic numbering and TOC anchor links in all multi-section HTML/Markdown templates.

## 2026-05-24 - [Situational Awareness in Institutional Reports]
**Learning:** For long-form institutional research reports, operators lose situational awareness of their progress and struggle with jargon-heavy metrics. Real-time visual feedback (scroll progress) and contextual documentation (hover tooltips) bridge the gap between high-density data and human-readable insights.
**Action:** Add scroll progress indicators and descriptive metric tooltips to institutional HTML report templates.
