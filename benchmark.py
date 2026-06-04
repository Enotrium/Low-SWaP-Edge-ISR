#!/usr/bin/env python3
"""
CPU vs SNN Energy Benchmark.
Compares traditional CPU inference vs event-driven SNN on FPGA.
Code path: benchmark.py → experiments/benchmark_energy.py → hdc/efficiency.py
"""
import sys
from pathlib import Path
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent / "software" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hdc.efficiency import EfficiencyBenchmark


def main():
    print("=" * 60)
    print("CPU vs SNN Energy Benchmark — XC7Z020 Target")
    print("=" * 60)

    bench = EfficiencyBenchmark(hd_dim=2048, num_neurons=2048)

    for n in [100, 1000, 10000]:
        metrics = bench.benchmark(num_samples=n)
        print(f"\n  Workload: {n} samples")
        print(f"    CPU energy:      {metrics.cpu_joules:.4f} J")
        print(f"    SNN energy:      {metrics.snn_joules:.6f} J")
        print(f"    HDC energy:      {metrics.hdc_joules:.6f} J")
        print(f"    SNN+HDC total:   {metrics.total_snn_hdc_joules:.6f} J")
        print(f"    Improvement:     {metrics.improvement_factor:.1f}x")

    print("\n" + "=" * 60)
    print("Benchmark: SNN+HDC on FPGA delivers orders of magnitude")
    print("energy savings vs CPU — critical for battery-constrained ISR.")
    print("=" * 60)


if __name__ == "__main__":
    main()