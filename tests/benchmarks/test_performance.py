import time

from src.research.rare_event_simulator import RareEventConfig, RareEventSimulator, RareEventType


def test_performance():
    simulator = RareEventSimulator(seed=42)
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=10000)
    start_time = time.time()
    df, _ = simulator.generate_scenario(config)
    end_time = time.time()
    duration = end_time - start_time
    print(f"Generated {len(df)} bars in {duration:.4f} seconds")
    assert duration < 1.0
