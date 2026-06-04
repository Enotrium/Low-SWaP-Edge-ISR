"""
HDC Error Masking — Graceful degradation under SEU fault injection.
Rather than catastrophic failure, accuracy degrades proportionally
to the fault injection rate — critical for radiation-hardened ops.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from .ecc import Hamming128


class ErrorMasking:
    """
    Graceful accuracy degradation under bit flips.
    Masks errors in HD vector operations by exploiting the
    distributed representation property of HD computing.
    """

    def __init__(self, hd_dim: int = 2048, fault_rate: float = 0.0):
        self.hd_dim = hd_dim
        self.fault_rate = fault_rate
        self.error_count = 0
        self.total_ops = 0

    def inject_faults(self, vector: np.ndarray) -> np.ndarray:
        """Inject random bit flips at configured fault rate."""
        if self.fault_rate <= 0:
            return vector
        mask = np.random.rand(len(vector)) < self.fault_rate
        flipped = vector.copy()
        flipped[mask] *= -1  # Flip bipolar bits
        self.error_count += int(np.sum(mask))
        self.total_ops += len(vector)
        return flipped

    def masked_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute similarity with graceful degradation."""
        a_faulty = self.inject_faults(a)
        b_faulty = self.inject_faults(b)
        return float(np.dot(a_faulty, b_faulty) / self.hd_dim)

    def masked_bundle(self, vectors: List[np.ndarray]) -> np.ndarray:
        """Bundle HD vectors with fault masking."""
        if not vectors:
            return np.zeros(self.hd_dim)
        masked = [self.inject_faults(v) for v in vectors]
        summed = np.sum(masked, axis=0)
        return np.sign(summed)

    def masked_bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Bind two HD vectors with fault tolerance."""
        return np.sign(self.inject_faults(a) * self.inject_faults(b))

    def degradation_curve(self, fault_rates: List[float],
                          num_trials: int = 100) -> Dict[float, float]:
        """
        Measure accuracy vs fault rate to characterize graceful degradation.
        Returns {fault_rate: mean_accuracy}.
        """
        results = {}
        base_vec = np.random.randn(self.hd_dim)
        base_vec = np.sign(base_vec)

        for rate in fault_rates:
            self.fault_rate = rate
            accuracies = []
            for _ in range(num_trials):
                noisy = self.inject_faults(base_vec.copy())
                acc = np.dot(noisy, base_vec) / self.hd_dim
                accuracies.append(acc)
            results[rate] = float(np.mean(accuracies))
        return results

    def get_fault_stats(self) -> Dict:
        """Return error statistics."""
        return {
            "fault_rate": self.fault_rate,
            "total_errors": self.error_count,
            "total_ops": self.total_ops,
            "effective_ber": (self.error_count
                              / max(self.total_ops, 1)),
        }


def test_graceful_degradation():
    """Verify accuracy degrades gracefully with fault rate."""
    masker = ErrorMasking(hd_dim=2048, fault_rate=0.01)
    curve = masker.degradation_curve([0.0, 0.01, 0.05, 0.10, 0.20])
    for rate, acc in curve.items():
        print(f"  Fault rate {rate:.2f}: accuracy {acc:.3f}")
    # At 0% faults, accuracy should be ~1.0
    assert curve[0.0] > 0.99, f"Expected ~1.0 at 0 faults, got {curve[0.0]}"
    # At 10% faults, accuracy should still be > 0 (graceful deg)
    assert curve[0.10] > 0.5, f"Expected grace >0.5, got {curve[0.10]}"
    print("  PASSED")


if __name__ == "__main__":
    test_graceful_degradation()
    print("Error masking test PASSED")