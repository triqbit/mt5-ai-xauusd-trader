import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.research.rare_event_simulator import RareEventConfig, RareEventSimulator, RareEventType
from src.research.reporting import RareEventSection, RareEventSummary


def verify_integration():
    print("Verifying RareEventSimulator -> ResearchReporting integration...")

    simulator = RareEventSimulator(seed=42)
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=200)
    _df, result = simulator.generate_scenario(config)

    # 1. Test to_report_summary conversion
    summary = result.to_report_summary()
    assert isinstance(summary, RareEventSummary)
    assert summary.event_type == "flash_crash"
    assert hasattr(summary, "peak_impact_pct")
    print(f"✓ RareEventResult.to_report_summary() produced {type(summary)}")

    # 2. Test RareEventSection population
    scenarios = [result.to_report_summary()]
    section = RareEventSection(scenarios=scenarios, insights="Test insights")
    assert len(section.scenarios) == 1
    assert section.scenarios[0].event_type == "flash_crash"
    print(f"✓ RareEventSection correctly populated with {len(section.scenarios)} scenario(s)")

    print("\nIntegration verification SUCCESSFUL.")


if __name__ == "__main__":
    try:
        verify_integration()
    except Exception as e:
        print(f"\nIntegration verification FAILED: {e}")
        sys.exit(1)
