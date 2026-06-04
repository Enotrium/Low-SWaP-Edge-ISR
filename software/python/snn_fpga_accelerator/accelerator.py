"""
Weaponized SNN FPGA Accelerator — Main Interface.
Extends metr0jw's event-driven SNN with defense subsystems.

Copyright (c) 2024 — Defense Autonomous Systems
"""
from __future__ import annotations

import time
import struct
import threading
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from enum import IntEnum

from .spike_encoding import SpikeEvent
from .exceptions import (
    WeaponSafetyError, EWConfigurationError, APSEngagementError,
    SwarmCommunicationError, NavigationError, ConfigurationError
)

# Import generated parameters
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "config" / "generated"))
from snn_params import (
    TOTAL_NEURONS, NUM_GROUPS, EW_DECEPTION_TYPES,
    APS_ENABLED, SWARM_ENABLED, SWARM_HD_DIM
)


class MissionPhase(IntEnum):
    """Mission phases for autonomous ops."""
    STANDBY = 0
    SEARCH = 1
    TRACK = 2
    IDENTIFY = 3
    ENGAGE = 4
    BDA = 5          # Battle Damage Assessment
    RETREAT = 6
    RTB = 7           # Return to Base


class EWMode(IntEnum):
    """Electronic Warfare countermeasure modes."""
    OFF = 0
    RGPO = 1          # Range Gate Pull-Off
    VGPO = 2          # Velocity Gate Pull-Off
    IAM = 3           # Inverse Amplitude Modulation
    CROSS_EYE = 4     # Cross-Eye Jamming
    SATURATION = 5    # Saturation/Barrage Noise


class WeaponState(IntEnum):
    """Weapon system safety states."""
    SAFE = 0x00
    ARMED = 0x01
    AUTO_ENGAGE = 0x03
    OVERRIDE = 0xFF


class ThreatTrack:
    """Track state for a detected threat."""
    def __init__(self, track_id: int, aoa: float, range_m: float,
                 velocity_ms: float, threat_class: int):
        self.track_id = track_id
        self.aoa = aoa
        self.range_m = range_m
        self.velocity_ms = velocity_ms
        self.threat_class = threat_class
        self.timestamp = time.time()
        self.confidence = 0.5
        self.engaged = False
        self.kill_confirmed = False


@dataclass
class EWConfig:
    """Electronic Warfare configuration."""
    mode: EWMode = EWMode.OFF
    frequency_hops: int = 128
    pri_us: int = 1000
    target_frequency_mhz: float = 0.0
    deception_type: str = "range_gate_pull_off"

    def __post_init__(self):
        if self.deception_type not in EW_DECEPTION_TYPES:
            raise EWConfigurationError(f"Unknown deception type: {self.deception_type}")


@dataclass
class SwarmConfig:
    """Swarm coordination parameters."""
    drone_id: int = 0
    max_drones: int = 16
    hd_dim: int = SWARM_HD_DIM
    consensus_period_ms: int = 1
    spread_spectrum: bool = True


class WeaponSNNAccelerator:
    """
    Main accelerator class for the weaponized SNN FPGA system.

    Integrates:
    - Event-driven SNN for threat detection & classification
    - Electronic Warfare (EW) countermeasure generation
    - Active Protection System (APS) fire control
    - Swarm coordination via HD vectors
    - GPS-denied navigation
    - ECC fault tolerance monitoring
    """

    def __init__(
        self,
        bitstream_path: Optional[str] = None,
        simulation_mode: bool = True,
        weapon_safety: bool = True,
        drone_id: int = 0,
    ):
        self.simulation_mode = simulation_mode
        self.weapon_safety = weapon_safety
        self.mission_phase = MissionPhase.STANDBY
        self.weapon_state = WeaponState.SAFE
        self.drone_id = drone_id

        # Core SNN state
        self.num_neurons = TOTAL_NEURONS
        self.num_groups = NUM_GROUPS
        self.spike_count = 0
        self.spike_queue: Queue = Queue()
        self.output_queue: Queue = Queue()

        # Defense subsystems
        self.ew_config = EWConfig()
        self.swarm_config = SwarmConfig(drone_id=drone_id)
        self.active_tracks: Dict[int, ThreatTrack] = {}
        self.next_track_id = 0
        self.engagement_count = 0
        self.kill_count = 0

        # Navigation state
        self.position = np.array([0.0, 0.0, 0.0])
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([0.0, 0.0, 0.0])

        # Swarm state (HD vectors)
        self.swarm_vectors: Dict[int, np.ndarray] = {}
        self.consensus_vector: Optional[np.ndarray] = None

        # Fault monitoring
        self.ecc_errors = 0
        self.watchdog_kicks = 0
        self.last_watchdog_kick = time.time()

        logger.info(f"WeaponSNN Accelerator initialized (drone={drone_id}, "
                    f"sim={simulation_mode}, safety={weapon_safety})")

    # ── Mission Control ──────────────────────────────────────────────

    def set_mission_phase(self, phase: MissionPhase) -> None:
        """Transition mission phase."""
        old = self.mission_phase
        self.mission_phase = phase
        logger.info(f"Mission phase: {old.name} → {phase.name}")

    def arm_weapons(self, auto_engage: bool = False) -> None:
        """Arm weapon systems. Requires safety to be disengaged."""
        if self.weapon_safety:
            raise WeaponSafetyError("Weapon safety interlock active")
        self.weapon_state = WeaponState.AUTO_ENGAGE if auto_engage else WeaponState.ARMED
        logger.info(f"Weapons armed (mode={self.weapon_state.name})")

    def safe_weapons(self) -> None:
        """Immediately safe all weapon systems."""
        self.weapon_state = WeaponState.SAFE
        self.ew_config.mode = EWMode.OFF
        logger.info("Weapons safed")

    # ── Sensor Processing ────────────────────────────────────────────

    def process_sensor_input(self, sensor_type: int, data: np.ndarray) -> List[SpikeEvent]:
        """Encode sensor data into spike events."""
        spikes = []
        if sensor_type == 0:  # RWR
            for i, amp in enumerate(data):
                if amp > 10:  # Threshold
                    spikes.append(SpikeEvent(
                        neuron_id=i % 128, timestamp=time.time(), weight=amp / 255.0
                    ))
        elif sensor_type == 1:  # Acoustic
            for i, val in enumerate(data):
                if val > 0:
                    spikes.append(SpikeEvent(
                        neuron_id=128 + i % 128, timestamp=time.time(), weight=val
                    ))
        elif sensor_type == 2:  # RF
            for i, val in enumerate(data[:128]):
                spikes.append(SpikeEvent(
                    neuron_id=256 + i, timestamp=time.time(), weight=abs(val)
                ))
        return spikes

    # ── Inference Pipeline ───────────────────────────────────────────

    def infer(self, input_spikes: List[SpikeEvent]) -> np.ndarray:
        """Run SNN inference, return firing rates per group."""
        if self.simulation_mode:
            return self._simulate_inference(input_spikes)

        # Hardware path (future: PYNQ DMA / XRT)
        self.spike_count += len(input_spikes)
        for spike in input_spikes:
            self.spike_queue.put(spike)

        output_rates = np.zeros(self.num_groups)
        while not self.output_queue.empty():
            evt = self.output_queue.get()
            group = evt.neuron_id >> 7
            output_rates[group] += 1.0

        return output_rates

    def _simulate_inference(self, input_spikes: List[SpikeEvent]) -> np.ndarray:
        """Software simulation of SNN inference."""
        rates = np.zeros(self.num_groups)
        for spike in input_spikes:
            group = spike.neuron_id >> 7
            rates[group] += spike.weight
        return rates / max(len(input_spikes), 1)

    # ── Threat Detection & Classification ───────────────────────────

    def detect_threats(self, sensor_spikes: List[SpikeEvent]) -> List[ThreatTrack]:
        """Detect and classify threats from sensor spikes."""
        rates = self.infer(sensor_spikes)

        # Group 4-5 outputs indicate threat classification
        threat_conf = rates[4:6]
        threat_present = np.any(threat_conf > 0.3)

        if not threat_present:
            return []

        threats = []
        for i, conf in enumerate(threat_conf):
            if conf > 0.3:
                track = ThreatTrack(
                    track_id=self.next_track_id,
                    aoa=float(np.random.uniform(0, 360)),  # From sensor
                    range_m=float(np.random.uniform(100, 5000)),
                    velocity_ms=float(np.random.uniform(100, 1000)),
                    threat_class=i + 1,
                )
                track.confidence = float(conf)
                self.active_tracks[track.track_id] = track
                self.next_track_id += 1
                threats.append(track)

        logger.info(f"Threats detected: {len(threats)}")
        return threats

    # ── Electronic Warfare ───────────────────────────────────────────

    def configure_ew(self, config: EWConfig) -> None:
        """Configure EW countermeasure parameters."""
        self.ew_config = config
        logger.info(f"EW configured: mode={config.mode.name}, "
                    f"type={config.deception_type}")

    def deploy_countermeasure(self, target: ThreatTrack) -> Dict:
        """Deploy EW countermeasure against a threat track."""
        if self.weapon_state == WeaponState.SAFE:
            raise WeaponSafetyError("Weapons safed — cannot deploy EW")

        mode_val = int(self.ew_config.mode)
        result = {
            "target_id": target.track_id,
            "ew_mode": self.ew_config.mode.name,
            "deception_type": self.ew_config.deception_type,
            "frequency_hop_channel": hash(target.aoa) % 128,
            "pulse_amplitude": 2047,
            "phase": np.random.randint(0, 65536),
            "jamming_active": mode_val > 0,
        }

        logger.info(f"EW countermeasure deployed: {result['deception_type']} "
                    f"→ target {target.track_id}")
        return result

    # ── Active Protection System ─────────────────────────────────────

    def engage_threat(self, track_id: int) -> Dict:
        """Engage threat via hard-kill APS."""
        if self.weapon_state == WeaponState.SAFE:
            raise WeaponSafetyError("Weapons safed — cannot engage")

        if track_id not in self.active_tracks:
            raise APSEngagementError(f"Track {track_id} not found")

        track = self.active_tracks[track_id]
        track.engaged = True
        self.engagement_count += 1

        solution = {
            "track_id": track_id,
            "solution_quality": min(255, int(track.confidence * 255)),
            "fire_command": True,
            "intercept_time_us": int(track.range_m / track.velocity_ms * 1e6),
            "target_aoa_deg": track.aoa,
            "kill_confirmed": False,
        }

        logger.info(f"APS engage → track {track_id} "
                    f"(range={track.range_m:.0f}m, quality={solution['solution_quality']})")
        return solution

    def confirm_kill(self, track_id: int) -> bool:
        """Confirm kill from BDA sensors."""
        if track_id in self.active_tracks:
            self.active_tracks[track_id].kill_confirmed = True
            self.kill_count += 1
            logger.info(f"Kill confirmed: track {track_id} ({self.kill_count} total)")
            return True
        return False

    # ── Swarm Coordination ──────────────────────────────────────────

    def encode_swarm_vector(self) -> np.ndarray:
        """Encode local state as HD vector for swarm sharing."""
        vector = np.random.randint(0, 2, self.swarm_config.hd_dim).astype(np.int8)
        vector[vector == 0] = -1  # Bipolar encoding

        mission_val = int(self.mission_phase) * 2 - 1
        threat_count = len([t for t in self.active_tracks.values() if not t.kill_confirmed])

        vector[0:16] = mission_val
        vector[16:32] = (self.position[:16].astype(np.int8) > 0) * 2 - 1
        vector[32:48] = threat_count % 2 * 2 - 1

        self.swarm_vectors[self.drone_id] = vector
        return vector

    def receive_swarm_vector(self, drone_id: int, vector: np.ndarray) -> None:
        """Receive HD vector from another drone."""
        self.swarm_vectors[drone_id] = vector
        self._update_consensus()

    def _update_consensus(self) -> None:
        """Update swarm consensus via majority vote over HD vectors."""
        if len(self.swarm_vectors) < 2:
            return

        vectors = list(self.swarm_vectors.values())
        consensus = np.mean(vectors, axis=0)
        self.consensus_vector = (consensus > 0).astype(np.int8) * 2 - 1
        logger.debug(f"Swarm consensus updated ({len(vectors)} drones)")

    # ── Fault Monitoring ────────────────────────────────────────────

    def kick_watchdog(self) -> None:
        """Kick hardware watchdog timer."""
        self.watchdog_kicks += 1
        self.last_watchdog_kick = time.time()

    def check_ecc_status(self) -> bool:
        """Check ECC error status."""
        return self.ecc_errors == 0

    def get_status(self) -> Dict:
        """Get comprehensive system status."""
        return {
            "mission_phase": self.mission_phase.name,
            "weapon_state": self.weapon_state.name,
            "active_tracks": len([t for t in self.active_tracks.values() if not t.kill_confirmed]),
            "total_engagements": self.engagement_count,
            "kill_count": self.kill_count,
            "spike_count": self.spike_count,
            "swarm_size": len(self.swarm_vectors),
            "ecc_errors": self.ecc_errors,
            "watchdog_kicks": self.watchdog_kicks,
            "simulation_mode": self.simulation_mode,
            "position": self.position.tolist(),
        }

    # ── Navigation ──────────────────────────────────────────────────

    def update_position(self, imu_data: np.ndarray, optical_flow: Optional[np.ndarray] = None):
        """Update position estimate (GPS-denied)."""
        dt = 0.01  # 100Hz update
        self.velocity += imu_data[:3] * dt
        self.position += self.velocity * dt
        self.orientation = imu_data[3:6]

    def get_navigation_state(self) -> Dict:
        """Get navigation state."""
        return {
            "position": self.position.copy(),
            "velocity": self.velocity.copy(),
            "orientation": self.orientation.copy(),
            "gps_denied": True,
        }


class logger:
    """Simple logger for embedded use."""
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def debug(msg): print(f"[DEBUG] {msg}")
    @staticmethod
    def warning(msg): print(f"[WARN] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")
