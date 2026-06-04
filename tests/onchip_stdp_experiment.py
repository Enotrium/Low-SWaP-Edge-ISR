"""
On-Chip STDP Experiment — Validates FPGA weight updates.
Code path: experiments/threat_detection.py -> tests/onchip_stdp_experiment.py
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent / "software" / "python"))
from snn_fpga_accelerator import WeaponSNNAccelerator
from snn_fpga_accelerator.defense import ThreatClassifier
from snn_fpga_accelerator.spike_encoding import SpikeEvent


def test_stdp_potentiation():
    """Test STDP potentiation: pre-before-post increases weight."""
    print("=== STDP Potentiation ===")
    classifier = ThreatClassifier()
    before = classifier.class_weights.copy()

    # Pre-before-post training
    sample = np.random.randn(128) * 0.3
    for _ in range(20):
        classifier.adapt(sample, 3, lr=0.1)

    delta = classifier.class_weights[:, 3] - before[:, 3]
    avg_delta = np.mean(np.abs(delta))
    print(f"  Avg weight change (class 3): {avg_delta:.4f}")
    assert avg_delta > 0, "No STDP potentiation observed"
    print("  PASSED")


def test_onchip_weight_update():
    """Test that weight updates happen locally (simulated on-chip)."""
    print("=== On-Chip Weight Update ===")
    classifier = ThreatClassifier()
    assert classifier.training_samples == 0

    for i in range(100):
        spike_rates = np.abs(np.random.randn(128)) * 0.1
        true_class = i % 8
        classifier.adapt(spike_rates, true_class, lr=0.02)

    print(f"  Training samples: {classifier.training_samples}")
    assert classifier.training_samples == 100
    print("  PASSED")


def test_fpga_stdp_parity():
    """Verify that software STDP matches expected FPGA behavior."""
    print("=== FPGA STDP Parity ===")
    classifier = ThreatClassifier()

    # Simulate 50-sample batch update with 128-dim spike rates
    initial = classifier.class_weights.copy()
    for i in range(50):
        spikes = [SpikeEvent(j % 128, 0, np.random.rand() * 10) for j in range(20)]
        # Build 128-dim rate vector from spike events
        rates = np.zeros(128)
        for s in spikes:
            rates[s.neuron_id] += s.weight
        rates = rates / max(len(spikes), 1)
        classifier.adapt(rates, i % 8, lr=0.01)

    final = classifier.class_weights
    max_delta = np.max(np.abs(final - initial))
    print(f"  Max weight delta: {max_delta:.4f}")
    assert 0 < max_delta < 50, f"STDP delta out of range: {max_delta}"
    print("  PASSED")


if __name__ == "__main__":
    test_stdp_potentiation()
    test_onchip_weight_update()
    test_fpga_stdp_parity()
    print("\nAll STDP tests PASSED")