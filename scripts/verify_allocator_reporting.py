import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.research.reporting import AllocationSection
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig


def verify_reporting():
    allocator = CapitalAllocator(total_budget=100000.0)

    s1 = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
        performance_multiplier=1.2,
    )
    allocator.add_strategy(s1)
    allocator.update_allocation("s1", 20000.0)

    # Trigger some rejections
    allocator.request_allocation("unknown", 0.01)

    section = allocator.to_report_section()

    print(f"Section type: {type(section)}")
    assert isinstance(section, AllocationSection)

    print(f"Total Heat: {section.total_heat_pct}%")
    assert section.total_heat_pct == 20.0

    print(f"Allocations count: {len(section.allocations)}")
    assert len(section.allocations) == 1
    assert section.allocations[0].name == "s1"
    assert section.allocations[0].multiplier == 1.2

    print(f"Rejection summary: {section.rejection_summary}")
    assert section.rejection_summary["STRATEGY_NOT_FOUND"] == 1

    print("Reporting integration verified successfully!")


if __name__ == "__main__":
    try:
        verify_reporting()
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
