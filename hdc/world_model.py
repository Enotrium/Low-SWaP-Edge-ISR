"""
HDC World Model — Internal physics models for predicting vehicle dynamics.
Runs as lightweight HD vector operations on FPGA.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time


@dataclass
class VehicleState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array([
            self.x, self.y, self.z,
            self.vx, self.vy, self.vz,
            self.roll, self.pitch, self.yaw,
        ])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "VehicleState":
        return cls(*arr.tolist())


class WorldModel:
    """
    HD vector-based world model for predicting future states.
    Encodes vehicle state as HD vector and predicts next state via
    HD vector operations (bind/bundle/permute) instead of matrix math.
    """

    def __init__(self, hd_dim: int = 2048, state_dim: int = 9):
        self.hd_dim = hd_dim
        self.state_dim = state_dim
        # Random basis for each state dimension
        self.basis = np.random.randn(state_dim, hd_dim)
        self.basis = np.sign(self.basis)
        # Transition learned via Hebbian-like bundling
        self.transition = np.zeros((state_dim, hd_dim))
        self.n_updates = 0

    def encode(self, state: VehicleState) -> np.ndarray:
        """Encode vehicle state as HD vector."""
        vals = state.to_array()
        scaled = np.tanh(vals / 100.0)  # squash to [-1, 1]
        vector = self.basis.T @ scaled
        return np.sign(vector)

    def decode(self, vector: np.ndarray) -> VehicleState:
        """Decode HD vector back to vehicle state."""
        similarities = self.basis @ vector
        return VehicleState.from_array(similarities * 100.0 / self.hd_dim)

    def predict(self, state: VehicleState, dt: float = 0.01) -> VehicleState:
        """Predict next state using HD transition model."""
        state_vec = self.encode(state)
        predicted_vec = self.transition @ state_vec
        predicted_vec = np.sign(predicted_vec)
        return self.decode(predicted_vec)

    def update(self, prev_state: VehicleState,
               curr_state: VehicleState, lr: float = 0.01) -> None:
        """Update HD transition model from observation (Hebbian)."""
        prev_vec = self.encode(prev_state)
        curr_vec = self.encode(curr_state)
        self.transition += lr * np.outer(
            self.basis @ np.sign(curr_vec),
            prev_vec
        )
        self.n_updates += 1

    def predict_trajectory(self, state: VehicleState,
                           steps: int = 100,
                           dt: float = 0.01) -> List[VehicleState]:
        """Predict trajectory over multiple time steps."""
        traj = [state]
        current = state
        for _ in range(steps):
            current = self.predict(current, dt)
            traj.append(current)
        return traj

    def evaluate_prediction_error(self,
                                   true_traj: List[VehicleState],
                                   pred_traj: List[VehicleState]) -> float:
        """Mean squared error over trajectory."""
        errors = []
        for t, p in zip(true_traj, pred_traj):
            err = np.sum((t.to_array() - p.to_array()) ** 2)
            errors.append(err)
        return float(np.mean(errors))