"""
Defense subsystem modules for the weaponized SNN FPGA accelerator.
EW countermeasures, APS, swarm coordinator, and threat classifier.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .accelerator import (
    WeaponSNNAccelerator, ThreatTrack, EWConfig, EWMode,
    WeaponState, MissionPhase, SwarmConfig
)


class EWCountermeasure:
    """Electronic Warfare countermeasure controller."""

    DECEPTION_WAVEFORMS = {
        1: "range_gate_pull_off",
        2: "velocity_gate_pull_off",
        3: "inverse_amplitude_modulation",
        4: "cross_eye_jamming",
        5: "saturation_noise",
    }

    def __init__(self, accelerator: WeaponSNNAccelerator):
        self.accel = accelerator
        self.config = EWConfig()
        self.drfm_buffer: np.ndarray = np.zeros(4096, dtype=np.int16)
        self.pulse_history: List[Dict] = []

    def analyze_radar_pulse(self, frequency_mhz: float, amplitude: float,
                            pulse_width_us: float) -> Dict:
        """Analyze incoming radar pulse and determine optimal deception."""
        analysis = {
            "frequency_mhz": frequency_mhz,
            "amplitude_db": 20 * np.log10(max(amplitude, 1e-6)),
            "pulse_width_us": pulse_width_us,
            "likely_band": self._classify_band(frequency_mhz),
            "recommended_mode": self._select_countermeasure(frequency_mhz, amplitude),
        }

        self.pulse_history.append(analysis)
        return analysis

    def _classify_band(self, freq_mhz: float) -> str:
        """Classify radar frequency band."""
        if freq_mhz < 300:       return "VHF"
        elif freq_mhz < 1000:    return "UHF"
        elif freq_mhz < 2000:    return "L"
        elif freq_mhz < 4000:    return "S"
        elif freq_mhz < 8000:    return "C"
        elif freq_mhz < 12000:   return "X"
        elif freq_mhz < 18000:   return "Ku"
        elif freq_mhz < 27000:   return "K"
        elif freq_mhz < 40000:   return "Ka"
        else:                    return "mmWave"

    def _select_countermeasure(self, freq_mhz: float, amp: float) -> int:
        """Select optimal countermeasure mode based on pulse analysis."""
        if amp > 200:       # High power -> saturation
            return 5
        elif freq_mhz > 8000:  # X-band or higher -> coherent
            return 4
        elif amp > 100:     # Medium power -> RGPO
            return 1
        else:               # Low power -> VGPO
            return 2

    def generate_deception_waveform(self, mode: int, target_aoa: float) -> Dict:
        """Generate deception waveform parameters for FPGA."""
        if mode not in self.DECEPTION_WAVEFORMS:
            mode = 1  # Default RGPO

        waveform = {
            "mode": mode,
            "type": self.DECEPTION_WAVEFORMS[mode],
            "phase": np.random.randint(0, 65536),
            "amplitude": np.random.randint(0, 4096),
            "pri_cycles": 100,
            "fh_channel": int(hash(str(target_aoa)) % 128),
        }

        if mode == 1:  # RGPO - ramp delay
            waveform["delay_ramp_slope"] = 10  # ns per pulse
        elif mode == 2:  # VGPO - ramp frequency
            waveform["doppler_ramp_hz"] = 500
        elif mode == 4:  # Cross-eye
            waveform["phase_inversion"] = True

        return waveform


class APSController:
    """Active Protection System fire control."""

    def __init__(self, accelerator: WeaponSNNAccelerator):
        self.accel = accelerator
        self.track_history: Dict[int, List[ThreatTrack]] = {}
        self.engagement_log: List[Dict] = []

    def prioritize_threats(self) -> List[Tuple[int, ThreatTrack, float]]:
        """Prioritize active threats by intercept solution quality."""
        scored = []
        for tid, track in self.accel.active_tracks.items():
            if track.kill_confirmed:
                continue
            # Score: close range + high velocity + high threat class = high priority
            score = (5000 - track.range_m) / 5000 * 100  # Range score
            score += track.velocity_ms / 1000 * 50        # Velocity score
            score += track.threat_class * 25              # Class score
            score *= track.confidence                     # Confidence weight
            scored.append((tid, track, score))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored

    def compute_intercept(self, track: ThreatTrack) -> Dict:
        """Compute intercept solution for a threat track."""
        intercept = {
            "time_to_impact_ms": track.range_m / max(track.velocity_ms, 1) * 1000,
            "lead_angle_deg": np.degrees(np.arcsin(
                min(1.0, track.velocity_ms / 1500))),  # Simplified
            "solution_quality": min(255, int(track.confidence * 255)),
            "engage_range_m": track.range_m,
        }
        intercept["fire_command"] = intercept["time_to_impact_ms"] < 500
        return intercept

    def assess_bda(self, track_id: int, post_engagement_sensors: np.ndarray) -> bool:
        """Battle Damage Assessment from post-engagement sensor data."""
        # Simplified BDA: check for reduced threat signature
        threat_signature = np.mean(post_engagement_sensors)
        kill_confirmed = threat_signature < 0.1

        if kill_confirmed:
            self.accel.confirm_kill(track_id)
            self.engagement_log.append({
                "track_id": track_id,
                "result": "kill",
                "timestamp": track_id,
            })

        return kill_confirmed


class SwarmCoordinator:
    """Multi-agent swarm coordination via HD vectors."""

    def __init__(self, accelerator: WeaponSNNAccelerator):
        self.accel = accelerator
        self.config = SwarmConfig(drone_id=accelerator.drone_id)
        self.formation: Optional[np.ndarray] = None
        self.shared_threat_map: Dict[int, List[ThreatTrack]] = {}

    def share_state(self) -> np.ndarray:
        """Encode and share local state as HD vector."""
        return self.accel.encode_swarm_vector()

    def receive_state(self, drone_id: int, hd_vector: np.ndarray) -> None:
        """Receive and process HD vector from another drone."""
        self.accel.receive_swarm_vector(drone_id, hd_vector)

        # Decode threat information from HD vector
        has_threat = np.mean(hd_vector[32:48]) > 0
        if has_threat:
            self.shared_threat_map[drone_id] = [
                ThreatTrack(tid, 0, 0, 0, 1)
                for tid in range(np.sum(hd_vector[40:48] > 0).astype(int))
            ]

    def get_formation_position(self, drone_id: int, swarm_size: int) -> np.ndarray:
        """Compute formation position based on swarm size and ID."""
        if swarm_size <= 0:
            return np.array([0.0, 0.0, 0.0])

        # Circular formation
        angle = 2 * np.pi * drone_id / swarm_size
        radius = 50.0  # 50m separation
        return np.array([
            radius * np.cos(angle),
            radius * np.sin(angle),
            0.0
        ])

    def consensus_decision(self, votes: np.ndarray) -> int:
        """Reach consensus on mission decision via majority vote."""
        if len(votes) == 0:
            return int(self.accel.mission_phase)
        return int(np.bincount(votes.astype(int)).argmax())


class ThreatClassifier:
    """SNN-based threat type classification."""

    THREAT_CLASSES = {
        0: "unknown",
        1: "SAM_radar",          # Surface-to-Air Missile radar
        2: "AAA_radar",          # Anti-Aircraft Artillery radar
        3: "AAM_radar",          # Air-to-Air Missile radar
        4: "CW_illuminator",     # Continuous Wave illuminator
        5: "laser_designator",   # Laser target designator
        6: "passive_radar",      # Passive RF emitter
        7: "comms_jammer",       # Communications jammer
    }

    def __init__(self):
        self.class_weights = np.random.randn(128, 8) * 0.1
        self.training_samples = 0

    def classify(self, spike_rates: np.ndarray) -> Tuple[int, str, float]:
        """Classify threat from SNN spike rates."""
        scores = spike_rates @ self.class_weights
        class_id = int(np.argmax(scores))
        confidence = float(np.max(scores) / (np.sum(np.abs(scores)) + 1e-6))

        return class_id, self.THREAT_CLASSES.get(class_id, "unknown"), confidence

    def adapt(self, spike_rates: np.ndarray, true_class: int, lr: float = 0.01) -> None:
        """Online adaptation (continual learning) for new threat signatures."""
        scores = spike_rates @ self.class_weights
        target = np.zeros(8)
        target[true_class] = 1.0
        error = target - scores

        # Hebbian-like update
        self.class_weights += lr * np.outer(spike_rates, error)
        self.training_samples += 1
