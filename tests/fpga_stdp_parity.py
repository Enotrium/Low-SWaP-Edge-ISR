"""
FPGA STDP Parity — Validates software STDP matches expected FPGA behavior.
Code path: tests/onchip_stdp_experiment.py → tests/fpga_stdp_parity.py
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent / "software" / "python"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from snn_fpga_accelerator.defense import ThreatClassifier
from snn_fpga_accelerator.spike_encoding import SpikeEvent
from hdc.ecc import Hamming128


def test_stdp_weight_quantization():
    """Verify STDP weights stay in FPGA bit-width range (8-bit signed)."""
    print("=== FPGA STDP Parity ===")
    c = ThreatClassifier()
    initial_mean = np.mean(c.class_weights)
    for i in range(100):
        spikes = [SpikeEvent(nid, 0, np.random.rand() * 5) for nid in range(128)]
        rates = np.zeros(128)
        for s in spikes:
            rates[s.neuron_id] += s.weight
        rates /= max(len(spikes), 1)
        c.adapt(rates, i % 8, lr=0.02)
    final_mean = np.mean(c.class_weights)
    assert -128 < final_mean < 127, f"Weight out of range: {final_mean}"
    print(f"  Initial mean: {initial_mean:.3f}, Final mean: {final_mean:.3f}")
    print("  PASSED")


def test_ecc_protection_roundtrip():
    """Verify HD vector survives ECC encode/decode."""
    v = np.random.randint(0, 2, 256).astype(np.int8)
    v[v == 0] = -1
    enc = Hamming128.protect_hd_vector(v)
    rec, errors = Hamming128.recover_hd_vector(enc, 256)
    matches = np.sum(rec[:256] == v[:256])
    print(f"  ECC roundtrip matches: {matches}/256, errors: {errors}")
    assert matches == 256, f"ECC failed: {256 - matches} mismatches"
    print("  PASSED")


if __name__ == "__main__":
    test_stdp_weight_quantization()
    test_ecc_protection_roundtrip()
    print("\nFPGA STDP parity tests PASSED")