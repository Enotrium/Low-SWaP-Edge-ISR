"""
HDC Cognitive Map — GPS-denied position encoding and SLAM.
PositionEncoder, CircularAngleEncoder for spatial awareness.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Position2D:
    """2D position estimate with uncertainty."""
    x: float = 0.0
    y: float = 0.0
    uncertainty: float = 1.0


class PositionEncoder:
    """
    Encode 2D position into HD vector for spatial reasoning.
    Uses grid-cell-like encoding with random projection.
    """

    def __init__(self, hd_dim: int = 2048, grid_resolution: int = 128):
        self.hd_dim = hd_dim
        self.grid_resolution = grid_resolution
        # Random projection matrix for grid cell encoding
        self.projection = np.random.randn(hd_dim, grid_resolution * grid_resolution)
        self.projection /= np.linalg.norm(self.projection, axis=1, keepdims=True)
        self._id_vectors: Dict[int, np.ndarray] = {}

    def encode(self, x: float, y: float, world_scale: float = 10000.0) -> np.ndarray:
        """Encode 2D position to HD bipolar vector."""
        gx = int(((x + world_scale / 2) / world_scale) * self.grid_resolution)
        gy = int(((y + world_scale / 2) / world_scale) * self.grid_resolution)
        gx = max(0, min(self.grid_resolution - 1, gx))
        gy = max(0, min(self.grid_resolution - 1, gy))
        grid_id = gx * self.grid_resolution + gy
        if grid_id not in self._id_vectors:
            self._id_vectors[grid_id] = self.projection[:, grid_id]
        vec = self._id_vectors[grid_id]
        return np.sign(vec)  # Bipolar quantize

    def decode(self, vector: np.ndarray, world_scale: float = 10000.0) -> Position2D:
        """Decode HD vector back to 2D position (approximate)."""
        similarities = self.projection.T @ vector
        best_idx = np.argmax(similarities)
        gx = best_idx // self.grid_resolution
        gy = best_idx % self.grid_resolution
        x = (gx / self.grid_resolution - 0.5) * world_scale
        y = (gy / self.grid_resolution - 0.5) * world_scale
        confidence = float(similarities[best_idx] / self.hd_dim)
        return Position2D(x, y, 1.0 - confidence)


class CircularAngleEncoder:
    """
    Encode continuous angles (bearing, heading) into HD vectors.
    Uses circular convolution — angles 0° and 360° encode to identical vectors.
    """

    def __init__(self, hd_dim: int = 2048, num_basis: int = 360):
        self.hd_dim = hd_dim
        self.num_basis = num_basis
        self.basis = np.random.randn(num_basis, hd_dim)
        self.basis = np.sign(self.basis)

    def encode(self, angle_deg: float) -> np.ndarray:
        """Encode angle to HD bipolar vector (circular)."""
        angle_deg %= 360
        idx = int(angle_deg / 360 * self.num_basis)
        return self.basis[idx].copy()

    def similarity(self, angle_a: float, angle_b: float) -> float:
        """HD cosine similarity between two angles."""
        va = self.encode(angle_a)
        vb = self.encode(angle_b)
        return float(np.dot(va, vb) / self.hd_dim)

    def add_angles(self, a_deg: float, b_deg: float) -> float:
        """Perform circular addition via HD vectors."""
        va = self.encode(a_deg)
        vb = self.encode(b_deg)
        summed = va + vb
        similarities = self.basis @ summed
        best = np.argmax(similarities)
        return float(best) / self.num_basis * 360


class CognitiveMap:
    """
    GPS-denied SLAM using HD vector encoding.
    Tracks visited cells, landmarks, and builds an occupancy-like map.
    """

    def __init__(self, hd_dim: int = 2048, cells: int = 1024):
        self.position_encoder = PositionEncoder(hd_dim)
        self.angle_encoder = CircularAngleEncoder(hd_dim // 2)
        self.hd_dim = hd_dim
        self.cells = cells
        self.cell_activations = np.zeros(cells)
        self.landmarks: Dict[int, Position2D] = {}
        self.visited_cells: set = set()

    def encode_position(self, x: float, y: float) -> np.ndarray:
        """Encode position as HD vector representation."""
        cell_x = int((x + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_y = int((y + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_id = cell_x * int(np.sqrt(self.cells)) + cell_y
        self.visited_cells.add(cell_id)
        self.cell_activations[cell_id] = 1.0
        return self.cell_activations

    def update_landmark(self, landmark_id: int, bearing_deg: float,
                        estimated_range_m: float) -> None:
        """Update landmark position from bearing/range measurement (Kalman-like)."""
        bearing_rad = np.radians(bearing_deg)
        if landmark_id in self.landmarks:
            existing = self.landmarks[landmark_id]
            alpha = 0.3
            existing.x += alpha * (estimated_range_m * np.cos(bearing_rad) - existing.x)
            existing.y += alpha * (estimated_range_m * np.sin(bearing_rad) - existing.y)
            existing.uncertainty *= (1.0 - alpha)
        else:
            self.landmarks[landmark_id] = Position2D(
                x=estimated_range_m * np.cos(bearing_rad),
                y=estimated_range_m * np.sin(bearing_rad),
                uncertainty=10.0,
            )

    def get_familiarity(self, x: float, y: float) -> float:
        """Return familiarity score — how often this location was visited."""
        cell_x = int((x + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_y = int((y + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_id = cell_x * int(np.sqrt(self.cells)) + cell_y
        return self.cell_activations[cell_id]

    def bind(self, pos_vec: np.ndarray, angle_vec: np.ndarray) -> np.ndarray:
        """Bind position and angle HD vectors (XOR-like bundling)."""
        return np.sign(pos_vec + angle_vec)

    def bundle(self, vectors: List[np.ndarray]) -> np.ndarray:
        """Bundle multiple HD vectors via summation with threshold."""
        if not vectors:
            return np.zeros(self.hd_dim)
        summed = np.sum(vectors, axis=0)
        return np.sign(summed)