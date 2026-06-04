"""
HDC Drone Control — Low-level flight control policies.
Uses HD vector bind/bundle/permute for lightweight, FPGA-friendly control.
"""
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FlightState:
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    throttle: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    alt: float = 0.0


@dataclass
class ControlCommand:
    roll_cmd: float = 0.0      # radians
    pitch_cmd: float = 0.0     # radians
    yaw_rate_cmd: float = 0.0  # rad/s
    throttle_cmd: float = 0.0  # 0-1


class DroneController:
    """
    HD vector-based flight controller.
    Encodes flight states and desired setpoints as HD vectors,
    then computes control output via similarity search.
    """

    def __init__(self, hd_dim: int = 1024):
        self.hd_dim = hd_dim
        self.state_dim = 8  # roll, pitch, yaw, throttle, vx, vy, vz, alt
        # Random HD basis vectors for each state dimension
        self.state_basis = np.random.randn(self.state_dim, hd_dim)
        self.state_basis = np.sign(self.state_basis)
        # Control output basis
        self.ctrl_basis = np.random.randn(4, hd_dim)  # roll, pitch, yaw_rate, throttle
        self.ctrl_basis = np.sign(self.ctrl_basis)
        # PID gains in HD space
        self.kp = 0.5
        self.kd = 0.1

    def encode_state(self, state: FlightState) -> np.ndarray:
        """Encode flight state as HD vector via weighted bundling."""
        vals = np.array([
            state.roll, state.pitch, state.yaw, state.throttle,
            state.vx, state.vy, state.vz, state.alt,
        ])
        # Normalize to [-1, 1]
        scaled = np.clip(vals / max(np.max(np.abs(vals)), 1e-6), -1, 1)
        vector = self.state_basis.T @ scaled
        return np.sign(vector)

    def encode_setpoint(self, target: FlightState) -> np.ndarray:
        """Encode desired setpoint."""
        return self.encode_state(target)

    def compute_control(self, current: FlightState,
                        target: FlightState) -> ControlCommand:
        """Compute control output from current state and target setpoint."""
        state_vec = self.encode_state(current)
        target_vec = self.encode_state(target)

        # Error vector in HD space
        error_vec = target_vec - state_vec

        # Project onto control basis
        cmd = self.ctrl_basis @ error_vec
        cmd = np.clip(cmd * self.kp / self.hd_dim, -1, 1)

        return ControlCommand(
            roll_cmd=float(cmd[0]),
            pitch_cmd=float(cmd[1]),
            yaw_rate_cmd=float(cmd[2]),
            throttle_cmd=float(np.clip(cmd[3], 0, 1)),
        )

    def stabilized_hover(self, current: FlightState) -> ControlCommand:
        """Compute control to achieve stabilized hover."""
        target = FlightState(alt=current.alt + 1.0)  # slight climb
        return self.compute_control(current, target)

    def waypoint_nav(self, current: FlightState,
                     target_pos: Tuple[float, float, float],
                     v_max: float = 10.0) -> ControlCommand:
        """Navigate toward a 3D waypoint."""
        dx = target_pos[0] - 0  # assume current at origin
        dy = target_pos[1] - 0
        dz = target_pos[2] - current.alt
        dist = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        if dist < 1e-6:
            return self.stabilized_hover(current)
        target = FlightState(
            vx=np.clip(dx / dist * v_max, -v_max, v_max),
            vy=np.clip(dy / dist * v_max, -v_max, v_max),
            vz=np.clip(dz / dist * v_max, -v_max, v_max),
            alt=target_pos[2],
            yaw=current.yaw + np.arctan2(dy, dx),
        )
        return self.compute_control(current, target)