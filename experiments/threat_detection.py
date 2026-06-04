"""
Weaponized SNN Threat Detection Experiment.
Tests concept drift, adversarial perturbation, and continual learning.

Code path: experiments/threat_detection.py -> tests/onchip_stdp_experiment.py
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent / "software" / "python"))
from snn_fpga_accelerator import WeaponSNNAccelerator
from snn_fpga_accelerator.defense import ThreatClassifier
from snn_fpga_accelerator.spike_encoding import SpikeEvent, SpikeEncoder
from snn_params import TOTAL_NEURONS, NUM_GROUPS


def test_concept_drift():
    """Test SNN robustness to environmental changes mid-deployment."""
    print("=== Test: Concept Drift ===")
    accel = WeaponSNNAccelerator(simulation_mode=True, weapon_safety=False)
    classifier = ThreatClassifier()

    phase1_spikes = [SpikeEvent(i % 128, 0, np.random.rand()) for i in range(100)]
    phase2_spikes = [SpikeEvent(i % 128, 0, np.random.rand() * 2) for i in range(100)]

    rates1 = accel.infer(phase1_spikes)
    rates2 = accel.infer(phase2_spikes)
    drift = np.max(np.abs(rates2 - rates1))
    print(f"  Drift magnitude: {drift:.4f}")
    assert drift > 0, "No drift detected - unexpected"
    print("  PASSED")


def test_adversarial_perturbation():
    """Test EW hardening against jamming/spoofing."""
    print("=== Test: Adversarial Perturbation ===")
    accel = WeaponSNNAccelerator(simulation_mode=True)
    clean_spikes = [SpikeEvent(i % 128, 0, 1.0) for i in range(50)]
    perturbed = clean_spikes + [SpikeEvent(i % 128, 0, 10.0) for i in range(5)]

    clean_rates = accel.infer(clean_spikes)
    adv_rates = accel.infer(perturbed)
    ratio = np.mean(adv_rates[4:6]) / max(np.mean(clean_rates[4:6]), 1e-6)
    print(f"  Perturbation ratio: {ratio:.2f}")
    assert ratio < 5, "Adversarial perturbation too impactful"
    print("  PASSED")


def test_continual_learning():
    """Test on-chip adaptation to new threat class with 50 samples."""
    print("=== Test: Continual Learning ===")
    classifier = ThreatClassifier()
    initial = classifier.class_weights.copy()

    for i in range(50):
        sample = np.random.randn(128) * 0.2 + np.eye(8, 128)[i % 8]
        classifier.adapt(sample, i % 8, lr=0.05)

    delta = np.max(np.abs(classifier.class_weights - initial))
    print(f"  Weight delta after 50 samples: {delta:.4f}")
    assert delta > 0, "No learning occurred"
    assert classifier.training_samples == 50
    print("  PASSED")


def test_full_sead_mission():
    """SEAD (Suppression of Enemy Air Defenses) end-to-end test."""
    print("=== Test: Full SEAD Mission Pipeline ===")
    accel = WeaponSNNAccelerator(simulation_mode=True, weapon_safety=False)

    # Arm weapons
    accel.arm_weapons(auto_engage=True)

    # Simulate RWR sensor spikes
    sensor_spikes = SpikeEncoder.encode_sensor("radar", np.random.rand(200).tolist())

    # Detect threats
    threats = accel.detect_threats(sensor_spikes)
    print(f"  Threats detected: {len(threats)}")

    # Deploy EW if threats found
    if threats:
        result = accel.deploy_countermeasure(threats[0])
        print(f"  EW deployed: {result['deception_type']}")

    # Engage high-priority threats
    from snn_fpga_accelerator.defense import APSController
    aps = APSController(accel)
    prioritized = aps.prioritize_threats()
    for tid, track, score in prioritized[:1]:
        if score > 10:
            engage = accel.engage_threat(tid)
            print(f"  APS engage: track={tid}, quality={engage['solution_quality']}")

    status = accel.get_status()
    print(f"  Final status: {status['mission_phase']}, "
          f"engagements={status['total_engagements']}")
    print("  PASSED")


if __name__ == "__main__":
    test_concept_drift()
    test_adversarial_perturbation()
    test_continual_learning()
    test_full_sead_mission()
    print("\nAll threat detection tests PASSED")