"""
HDC Oracle Defense — Adversarial robustness against spoofed sensor inputs.
Detects adversarial perturbations in sensor data by comparing
HD vector encodings against learned "oracle" distributions.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AdversarialAlert:
    sensor_index: int
    perturbation_magnitude: float
    confidence: float
    alert_level: str  # "green", "yellow", "red"


class OracleDefender:
    """
    Detects adversarial/spoofed sensor inputs using HD vector anomaly detection.
    Maintains per-sensor baseline HD vectors and flags deviations.

    Defense strategies:
    1. Mahalanobis distance in HD space (lightweight)
    2. Cosine similarity to oracle distribution
    3. Temporal consistency check (sudden jumps)
    """

    def __init__(self, hd_dim: int = 2048, num_sensors: int = 4):
        self.hd_dim = hd_dim
        self.num_sensors = num_sensors
        # Oracle distributions per sensor (mean vector + std)
        self.oracle_mean: List[np.ndarray] = [
            np.random.randn(hd_dim) for _ in range(num_sensors)
        ]
        self.oracle_std: List[float] = [1.0] * num_sensors
        self.oracle_cov_inv: List[np.ndarray] = [
            np.eye(hd_dim) for _ in range(num_sensors)
        ]
        # History per sensor for temporal checks
        self.history: List[List[np.ndarray]] = [[] for _ in range(num_sensors)]
        self.max_history = 20
        self.anomaly_threshold = 3.0  # sigma

    def fit_oracle(self, sensor_id: int, samples: List[np.ndarray]):
        """Fit oracle distribution from training samples."""
        if not samples:
            return
        stacked = np.vstack(samples)
        self.oracle_mean[sensor_id] = np.mean(stacked, axis=0)
        cov = np.cov(stacked, rowvar=False) + np.eye(self.hd_dim) * 1e-6
        self.oracle_cov_inv[sensor_id] = np.linalg.pinv(cov)
        self.oracle_std[sensor_id] = float(np.mean(np.sqrt(np.diag(cov))))

    def mahalanobis_distance(self, sensor_id: int,
                             vector: np.ndarray) -> float:
        """Mahalanobis distance from oracle distribution."""
        delta = vector - self.oracle_mean[sensor_id]
        return float(np.sqrt(delta @ self.oracle_cov_inv[sensor_id] @ delta))

    def cosine_similarity(self, sensor_id: int,
                          vector: np.ndarray) -> float:
        """Cosine similarity to oracle mean."""
        return float(np.dot(vector, self.oracle_mean[sensor_id])
                    / (np.linalg.norm(vector)
                       * np.linalg.norm(self.oracle_mean[sensor_id]) + 1e-8))

    def temporal_consistency(self, sensor_id: int,
                             vector: np.ndarray) -> float:
        """Check if new vector is consistent with recent history."""
        if len(self.history[sensor_id]) < 2:
            return 1.0
        recent = np.vstack(self.history[sensor_id][-5:])
        mean_recent = np.mean(recent, axis=0)
        return float(np.dot(vector, mean_recent)
                    / (np.linalg.norm(vector)
                       * np.linalg.norm(mean_recent) + 1e-8))

    def check_sensor(self, sensor_id: int,
                     hd_vector: np.ndarray) -> AdversarialAlert:
        """Check a sensor reading for adversarial perturbation."""
        # Update history
        self.history[sensor_id].append(hd_vector)
        if len(self.history[sensor_id]) > self.max_history:
            self.history[sensor_id].pop(0)

        mahal = self.mahalanobis_distance(sensor_id, hd_vector)
        cos = self.cosine_similarity(sensor_id, hd_vector)
        temp = self.temporal_consistency(sensor_id, hd_vector)

        # Composite anomaly score
        anomaly_score = mahal / self.oracle_std[sensor_id]

        if anomaly_score > 5 * self.anomaly_threshold:
            level = "red"
        elif anomaly_score > self.anomaly_threshold:
            level = "yellow"
        else:
            level = "green"

        return AdversarialAlert(
            sensor_index=sensor_id,
            perturbation_magnitude=float(anomaly_score),
            confidence=float(max(cos, temp)),
            alert_level=level,
        )

    def is_spoofed(self, sensor_id: int,
                   hd_vector: np.ndarray) -> bool:
        """Quick check: is the sensor input likely spoofed?"""
        alert = self.check_sensor(sensor_id, hd_vector)
        return alert.alert_level == "red"

    def generate_adversarial(self, sensor_id: int,
                             magnitude: float = 0.3) -> np.ndarray:
        """Generate an adversarial perturbation for testing."""
        base = self.oracle_mean[sensor_id]
        noise = np.random.randn(self.hd_dim) * magnitude
        return np.sign(base + noise)