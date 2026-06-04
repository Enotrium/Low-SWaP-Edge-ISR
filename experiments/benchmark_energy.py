#!/usr/bin/env python3
"""
Energy Benchmark Experiment — Quantifies SNN+HDC power savings.
Code path: benchmark.py → experiments/benchmark_energy.py → hdc/efficiency.py
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent / "software" / "python"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from hdc.efficiency import EfficiencyBenchmark


def test_energy_sweep():
    """Sweep workload sizes to find energy break-even."""
    print("=== Energy Benchmark Sweep ===")
    bench = EfficiencyBenchmark(hd_dim=2048, num_neurons=2048)
    for n in [100, 500, 1000, 5000, 10000]:
        m = bench.benchmark(num_samples=n)
        print(f"  N={n:5d}: CPU={m.cpu_joules:.4f}J  "
              f"SNN={m.snn_joules:.6f}J  "
              f"HDC={m.hdc_joules:.6f}J  "
              f"Speedup={m.improvement_factor:.0f}x")
        assert m.improvement_factor > 1.0
    print("  PASSED")


def test_fpga_power_budget():
    """Validate FPGA stays under 5W budget."""
    print("=== FPGA Power Budget Validation ===")
    bench = EfficiencyBenchmark()
    # Full 2048-neuron activation
    n_spikes = 2048 * 50  # 50 spikes per neuron
    snn_w = bench.SNN_SPIKE_ENERGY_J * n_spikes / 0.001
    fpga_active_w = bench.FPGA_ACTIVE_POWER_W
    total_w = snn_w + fpga_active_w
    print(f"  SNN dynamic: {snn_w:.2f}W, FPGA active: {fpga_active_w:.2f}W")
    print(f"  Total: {total_w:.2f}W")
    assert total_w < 5.0, f"Power budget exceeded: {total_w:.2f}W > 5W"
    print("  PASSED")


if __name__ == "__main__":
    test_energy_sweep()
    test_fpga_power_budget()
    print("\nEnergy benchmark PASSED")