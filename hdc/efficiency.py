"""
HDC Efficiency — Power/energy quantification for CPU vs SNN/HDC comparison.
Quantifies energy savings from event-driven SNN + HD vector ops on FPGA.
"""
import numpy as np
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EnergyMetrics:
    cpu_joules: float
    snn_joules: float
    hdc_joules: float
    total_snn_hdc_joules: float
    ops_per_joule_cpu: float
    ops_per_joule_snn: float
    improvement_factor: float
    ops_count: int


class EfficiencyBenchmark:
    """
    Compare energy consumption:
    - CPU: floating-point DNN inference
    - SNN: event-driven spikes on FPGA (<5W)
    - HDC: HD vector bind/bundle/permute on FPGA

    Key assumptions (XC7Z020, PYNQ-Z2):
    - FPGA idle: 1.5W, active: 3.5W (logic + BRAM)
    - CPU (Cortex-A9): 0.4W active
    - Spike energy: ~10 pJ/spike on dedicated LIF fabric
    - HD op energy: ~1 nJ per 2048-dim bipolar operation
    """

    # Constants (measured/estimated for XC7Z020)
    FPGA_IDLE_POWER_W = 1.5
    FPGA_ACTIVE_POWER_W = 3.5
    CPU_ACTIVE_POWER_W = 0.4
    SNN_SPIKE_ENERGY_J = 10e-12      # 10 pJ per spike
    HDC_OP_ENERGY_J_2048 = 1e-9       # 1 nJ per HD bundle/bind
    DDR_ACCESS_ENERGY_J = 1e-9        # 1 nJ per DDR read

    def __init__(self, hd_dim: int = 2048, num_neurons: int = 2048):
        self.hd_dim = hd_dim
        self.num_neurons = num_neurons

    def cpu_inference_energy(self, ops_count: int,
                             seconds: float) -> float:
        """CPU energy for floating-point inference."""
        return seconds * self.CPU_ACTIVE_POWER_W

    def snn_energy(self, num_spikes: int,
                   compute_time_s: float) -> float:
        """SNN energy for event-driven inference."""
        spike_energy = num_spikes * self.SNN_SPIKE_ENERGY_J
        idle_time = max(0, 0.001 - compute_time_s)
        fpga_energy = (compute_time_s * self.FPGA_ACTIVE_POWER_W
                      + idle_time * self.FPGA_IDLE_POWER_W)
        return spike_energy + fpga_energy

    def hdc_energy(self, num_bind: int, num_bundle: int,
                   num_permute: int) -> float:
        """HDC energy for vector operations."""
        ops = num_bind + num_bundle + num_permute
        return ops * self.HDC_OP_ENERGY_J_2048

    def benchmark(self, num_samples: int = 1000) -> EnergyMetrics:
        """Run full energy benchmark comparing CPU vs SNN+HDC."""
        # Simulated inference workload
        dims = (256, 784)  # Sample input → hidden layer
        weights = np.random.randn(*dims)
        sample = np.random.randn(dims[1])

        # CPU: matrix multiply
        t0 = time.perf_counter()
        for _ in range(num_samples):
            _ = sample @ weights.T
        t1 = time.perf_counter()
        cpu_time = (t1 - t0)
        cpu_joules = self.cpu_inference_energy(
            num_samples * dims[0] * dims[1], cpu_time
        )

        # SNN: spike-based (simulated)
        num_spikes = int(num_samples * self.num_neurons * 0.05)  # 5% firing
        snn_time = num_spikes * 10e-9  # 10 ns per spike
        snn_joules = self.snn_energy(num_spikes, snn_time)

        # HDC: bundle + bind
        hdc_joules = self.hdc_energy(
            num_bind=num_samples,
            num_bundle=num_samples // 10,
            num_permute=num_samples,
        )

        total_snn_hdc = snn_joules + hdc_joules

        return EnergyMetrics(
            cpu_joules=cpu_joules,
            snn_joules=snn_joules,
            hdc_joules=hdc_joules,
            total_snn_hdc_joules=total_snn_hdc,
            ops_per_joule_cpu=(num_samples / cpu_joules
                               if cpu_joules > 0 else float("inf")),
            ops_per_joule_snn=(num_samples / total_snn_hdc
                               if total_snn_hdc > 0 else float("inf")),
            improvement_factor=(cpu_joules / total_snn_hdc
                                if total_snn_hdc > 0 else float("inf")),
            ops_count=num_samples,
        )

    def sweep_workload(self, workload_sizes: List[int]) -> List[EnergyMetrics]:
        """Sweep workload size to find energy break-even point."""
        return [self.benchmark(n) for n in workload_sizes]


def test_efficiency():
    """Verify SNN+HDC energy improvement over CPU."""
    bench = EfficiencyBenchmark(hd_dim=2048, num_neurons=2048)
    metrics = bench.benchmark(num_samples=1000)

    print(f"  CPU energy:     {metrics.cpu_joules:.4f} J")
    print(f"  SNN energy:     {metrics.snn_joules:.6f} J")
    print(f"  HDC energy:     {metrics.hdc_joules:.6f} J")
    print(f"  SNN+HDC total:  {metrics.total_snn_hdc_joules:.6f} J")
    print(f"  Improvement:    {metrics.improvement_factor:.1f}x")

    assert metrics.improvement_factor > 1.0, \
        f"Expected SNN+HDC to be more efficient than CPU"
    print("  PASSED")


if __name__ == "__main__":
    test_efficiency()
    print("Efficiency benchmark PASSED")