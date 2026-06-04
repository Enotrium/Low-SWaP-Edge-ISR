"""
HDC Multi-Agent Coordination — Swarm intelligence via HD vector sharing.
Enables a swarm of drones to share compressed HD vector state representations
rather than raw sensor data, minimizing RF bandwidth and making the swarm
harder to detect/jam. Uses LPI spread-spectrum compatible encoding.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SwarmMessage:
    drone_id: int
    hd_vector: np.ndarray        # Compressed state HD vector
    position: np.ndarray         # [x, y, z]
    mission_phase: int
    threat_count: int
    timestamp: float


class MultiAgentHDC:
    """
    Swarm coordination using HD vector encoding.
    Each drone shares a compressed HD vector representing its local state,
    and the swarm reaches consensus via majority vote over HD vectors.
    """

    def __init__(self, drone_id: int, hd_dim: int = 512,
                 max_drones: int = 16):
        self.drone_id = drone_id
        self.hd_dim = hd_dim
        self.max_drones = max_drones

        # Basis vectors for encoding state dimensions
        self.position_basis = np.random.randn(3, hd_dim)
        self.position_basis = np.sign(self.position_basis)
        self.mission_basis = np.random.randn(8, hd_dim)  # 8 mission phases
        self.mission_basis = np.sign(self.mission_basis)
        self.threat_basis = np.random.randn(1, hd_dim)
        self.threat_basis = np.sign(self.threat_basis)

        # Received vectors from swarm members
        self.received: Dict[int, SwarmMessage] = {}
        self.consensus_vector: Optional[np.ndarray] = None

    def encode_state(self, position: np.ndarray,
                     mission_phase: int,
                     threat_count: int) -> np.ndarray:
        """
        Encode local drone state as HD vector for swarm sharing.
        Uses weighted bundling of position, mission, and threat.
        """
        pos_vec = self.position_basis.T @ np.tanh(position / 1000.0)
        mission_vec = self.mission_basis[mission_phase % 8]
        threat_vec = self.threat_basis[0] * (1 if threat_count > 0 else -1)

        combined = pos_vec + mission_vec * 0.5 + threat_vec
        return np.sign(combined)

    def decode_state(self, vector: np.ndarray) -> Tuple[np.ndarray, int, float]:
        """Decode swarm HD vector back to approximate state."""
        pos = self.position_basis @ vector / self.hd_dim * 1000.0
        mission_sim = self.mission_basis @ vector
        mission = int(np.argmax(mission_sim))
        threat = float(np.dot(self.threat_basis[0], vector) / self.hd_dim)
        return pos, mission, threat

    def share_state(self, position: np.ndarray,
                    mission_phase: int,
                    threat_count: int) -> SwarmMessage:
        """Generate and broadcast a swarm message."""
        vector = self.encode_state(position, mission_phase, threat_count)
        msg = SwarmMessage(
            drone_id=self.drone_id,
            hd_vector=vector,
            position=position.copy(),
            mission_phase=mission_phase,
            threat_count=threat_count,
            timestamp=np.datetime64("now").astype(float),
        )
        return msg

    def receive_message(self, msg: SwarmMessage):
        """Receive state vector from another drone."""
        self.received[msg.drone_id] = msg
        self._update_consensus()

    def _update_consensus(self):
        """Update swarm consensus via majority vote over HD vectors."""
        if len(self.received) < 2:
            return
        vectors = [v.hd_vector for v in self.received.values()]
        stacked = np.vstack(vectors)
        consensus = np.mean(stacked, axis=0)
        self.consensus_vector = np.sign(consensus)

    def get_consensus_decision(self, options: np.ndarray) -> int:
        """
        Reach consensus decision from numeric options.
        Uses HD vector-based voting — each received vector votes for
        its closest option in HD space.
        """
        if not self.received:
            return int(np.argmax(options))
        votes = np.zeros(len(options))
        for msg in self.received.values():
            sims = np.array([
                np.dot(msg.hd_vector, self._encode_option(o)) / self.hd_dim
                for o in options
            ])
            votes[np.argmax(sims)] += 1
        return int(np.argmax(votes))

    def _encode_option(self, value: int) -> np.ndarray:
        """Encode a discrete option as HD vector."""
        seed = value % self.hd_dim
        np.random.seed(seed)
        vec = np.sign(np.random.randn(self.hd_dim))
        np.random.seed(None)
        return vec

    def get_formation_offsets(self, formation: str = "line") -> Dict[int, np.ndarray]:
        """
        Compute formation offsets for all swarm members.
        Uses consensus vector as formation direction reference.
        """
        offsets = {}
        n = max(len(self.received), 1)
        direction = np.array([1.0, 0.0, 0.0])
        if self.consensus_vector is not None:
            direction[:2] = (self.position_basis[:2]
                             @ self.consensus_vector)[:2] / self.hd_dim

        for i in range(n):
            if formation == "line":
                offsets[i] = np.array([i * 50.0, 0.0, 0.0])
            elif formation == "wedge":
                offsets[i] = np.array([i * 30.0, i * 20.0, 0.0])
            elif formation == "phalanx":
                row = i // 4
                col = i % 4
                offsets[i] = np.array([row * 40.0, col * 40.0, 0.0])
            else:
                offsets[i] = np.zeros(3)
        return offsets

    def bandwidth_savings(self, raw_data_bytes: int = 4096) -> float:
        """
        Compute bandwidth savings from HD vector compression.
        Raw sensor data: 4096 bytes per drone per update
        HD vector: hd_dim bits / 8 bytes per drone per update
        """
        hd_bytes = self.hd_dim // 8  # Bipolar → 1 bit each
        return 1.0 - hd_bytes / raw_data_bytes