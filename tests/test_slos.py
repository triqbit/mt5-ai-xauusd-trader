import os
import re

from scripts.verify_slos import TARGETS


def test_slo_targets_doc_exists():
    """Verify that the SLO targets documentation exists."""
    assert os.path.exists("docs/SLO_TARGETS.md")

def test_slo_targets_content_sections():
    """Verify that all mandatory sections are present in SLO_TARGETS.md."""
    with open("docs/SLO_TARGETS.md", "r") as f:
        content = f.read()

    required_sections = [
        r"## 1\. Availability SLOs",
        r"## 2\. CI/CD & Engineering SLOs",
        r"## 3\. Performance & Latency SLOs",
        r"## 4\. Operational Responsiveness",
        r"## 5\. Incident Recovery",
        r"## 6\. Error Budget Framework"
    ]
    for section in required_sections:
        assert re.search(section, content)

def test_slo_targets_values_alignment():
    """Verify that the documentation matches the verification script constants."""
    with open("docs/SLO_TARGETS.md", "r") as f:
        content = f.read()

    # Uptime Target (99.5%)
    uptime_pct = f"{TARGETS['UPTIME']*100:.1f}%"
    assert uptime_pct in content

    # CI Success Target (95.0%)
    ci_pct = f"{TARGETS['CI_SUCCESS']*100:.1f}%"
    assert ci_pct in content

    # RTO Target (15 mins)
    rto_min = int(TARGETS['RTO_SECONDS'] / 60)
    assert f"{rto_min} mins" in content or f"{rto_min} min" in content

    # Backtest Latency Targets
    assert f"{int(TARGETS['BACKTEST_P50']/60)} min" in content
    assert f"{int(TARGETS['BACKTEST_P95']/60)} min" in content
    assert f"{int(TARGETS['BACKTEST_P99']/60)} min" in content

    # Model Inference Latency Targets
    assert f"{int(TARGETS['INFERENCE_P50']*1000)}ms" in content
    assert f"{int(TARGETS['INFERENCE_P95']*1000)}ms" in content
    assert f"{int(TARGETS['INFERENCE_P99']*1000)}ms" in content

def test_alert_response_times():
    """Verify alert response time expectations are defined."""
    with open("docs/SLO_TARGETS.md", "r") as f:
        content = f.read()

    assert "P0 (Critical)" in content
    assert re.search(r"<\s*5\s*mins", content) # ACK for P0
    assert re.search(r"<\s*1\s*hour", content) # Resolution for P0

def test_error_budget_details():
    """Verify error budget details are present."""
    with open("docs/SLO_TARGETS.md", "r") as f:
        content = f.read()

    assert "216 Minutes" in content # 0.5% of 30 days
    assert "Stability Freeze Protocol" in content
    assert "incidents" in content.lower()

def test_slo_targets_links():
    """Verify that important links are present in SLO_TARGETS.md."""
    with open("docs/SLO_TARGETS.md", "r") as f:
        content = f.read()

    assert "[Monitoring Runbook](runbooks/06-monitoring-alert-triage.md)" in content
    assert "[Disaster Recovery Plan](DISASTER_RECOVERY.md)" in content
