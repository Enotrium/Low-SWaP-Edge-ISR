"""
HDC Multimodal Sensor Fusion — Fuses heterogeneous sensors into common HD vector space.
Radar + Acoustic + EO/IR → unified HD representation for threat identification.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MultimodalObservation:
    radar: Optional[np.ndarray] = None       # range-doppler bins
    acoustic: Optional[np.ndarray] = None    # FFT bins
    eoir: Optional[np.ndarray] = None        # pixel patch / FLIR
    timestamp: float = 0.0


class MultimodalHDC:
    """
    Fuses heterogeneous sensor data (radar, acoustic, EO/IR) into
    a common HD vector space using bind and bundle operations.

    Advantages over traditional fusion:
    - Dimensionality-agnostic (all inputs → same HD dim)
    - Missing modality tolerant (bundle remaining)
    - Lightweight: bind/bundle instead of deep fusion networks
    """

    def __init__(self, hd_dim: int = 2048):
        self.hd_dim = hd_dim
        # Per-modality random projection matrices
        self.radar_proj = np.random.randn(hd_dim, 128)
        self.acoustic_proj = np.random.randn(hd_dim, 256)
        self.eoir_proj = np.random.randn(hd_dim, 1024)
        for proj in [self.radar_proj, self.acoustic_proj, self.eoir_proj]:
            proj /= np.linalg.norm(proj, axis=1, keepdims=True)

    def encode_radar(self, radar_data: np.ndarray) -> np.ndarray:
        """Encode radar range-doppler data to HD vector."""
        if len(radar_data) == 0:
            return np.zeros(self.hd_dim)
        padded = np.zeros(128)
        padded[:len(radar_data)] = radar_data[:128]
        vec = self.radar_proj @ padded
        return np.sign(vec)

    def encode_acoustic(self, acoustic_data: np.ndarray) -> np.ndarray:
        """Encode acoustic FFT data to HD vector."""
        if len(acoustic_data) == 0:
            return np.zeros(self.hd_dim)
        padded = np.zeros(256)
        padded[:len(acoustic_data)] = acoustic_data[:256]
        vec = self.acoustic_proj @ padded
        return np.sign(vec)

    def encode_eoir(self, eoir_data: np.ndarray) -> np.ndarray:
        """Encode EO/IR pixel data to HD vector."""
        if len(eoir_data) == 0:
            return np.zeros(self.hd_dim)
        flat = eoir_data.flatten()[:1024]
        padded = np.zeros(1024)
        padded[:len(flat)] = flat
        vec = self.eoir_proj @ padded
        return np.sign(vec)

    def fuse(self, observation: MultimodalObservation,
             weights: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Fuse multiple sensor modalities into single HD vector.
        Missing modalities are simply excluded (graceful degradation).
        """
        if weights is None:
            weights = {"radar": 1.0, "acoustic": 1.0, "eoir": 0.5}

        vectors = []
        w_sum = 0.0

        if observation.radar is not None:
            vectors.append(weights["radar"] * self.encode_radar(observation.radar))
            w_sum += weights["radar"]
        if observation.acoustic is not None:
            vectors.append(weights["acoustic"]
                           * self.encode_acoustic(observation.acoustic))
            w_sum += weights["acoustic"]
        if observation.eoir is not None:
            vectors.append(weights["eoir"] * self.encode_eoir(observation.eoir))
            w_sum += weights["eoir"]

        if not vectors:
            return np.zeros(self.hd_dim)

        fused = np.sum(vectors, axis=0)
        return np.sign(fused)

    def similarity_matrix(self,
                          observations: List[MultimodalObservation]
                          ) -> np.ndarray:
        """Compute pairwise similarity matrix for observations."""
        n = len(observations)
        vectors = [self.fuse(obs) for obs in observations]
        sims = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                sims[i, j] = float(np.dot(vectors[i], vectors[j]) / self.hd_dim)
        return sims

    def classify(self, fused_vector: np.ndarray,
                 prototypes: np.ndarray) -> Tuple[int, float]:
        """
        Classify fused sensor vector against prototype vectors.
        Returns (class_id, confidence).
        """
        similarities = prototypes @ fused_vector
        best = np.argmax(similarities)
        conf = float(similarities[best] / self.hd_dim)
        return int(best), conf

    def modality_importance(self, observation: MultimodalObservation,
                           prototypes: np.ndarray) -> Dict[str, float]:
        """Compute per-modality contribution to classification."""
        fused = self.fuse(observation)
        base_conf = float(np.max(prototypes @ fused) / self.hd_dim)

        contributions = {}
        for mod, encoder in [
            ("radar", self.encode_radar),
            ("acoustic", self.encode_acoustic),
            ("eoir", self.encode_eoir),
        ]:
            if getattr(observation, mod) is not None:
                partial = self.fuse(observation, {mod: 1.0})
                conf = float(np.max(prototypes @ partial) / self.hd_dim)
                contributions[mod] = conf / max(base_conf, 1e-8)
            else:
                contributions[mod] = 0.0
        return contributions