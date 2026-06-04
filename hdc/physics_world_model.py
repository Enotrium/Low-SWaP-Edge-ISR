"""
HDC Physics World Model — Vehicle dynamics prediction with aerodynamics.
Extends world_model.py with drag, gravity, and control surface physics.
"""
import numpy as np
from typing import List
from .world_model import WorldModel, VehicleState


class PhysicsWorldModel(WorldModel):
    """
    HD-encoded physics model incorporating:
    - Aerodynamic drag (quadratic velocity damping)
    - Gravity
    - Control surface moments
    - Mass-inertia approximations

    Uses HD vector encoding for state but applies analytical physics
    in the decode-predict-reencode loop.
    """

    def __init__(self, hd_dim: int = 2048):
        super().__init__(hd_dim)
        self.mass_kg = 2.5        # small UAS
        self.drag_coeff = 0.02    # Cd * A / mass
        self.gravity = 9.81
        self.inertia_roll = 0.05
        self.inertia_pitch = 0.05
        self.inertia_yaw = 0.08

    def predict(self, state: VehicleState, dt: float = 0.01,
                control_cmds: np.ndarray = None) -> VehicleState:
        """Analytical physics prediction with HD encoding."""
        # Aerodynamic drag
        v_mag = np.sqrt(state.vx ** 2 + state.vy ** 2 + state.vz ** 2)
        drag_ax = -self.drag_coeff * v_mag * state.vx
        drag_ay = -self.drag_coeff * v_mag * state.vy
        drag_az = -self.drag_coeff * v_mag * state.vz

        # Control inputs (roll, pitch, yaw_rate, thrust)
        cmd = np.zeros(4) if control_cmds is None else control_cmds
        thrust = cmd[3] * 20.0  # 0-1 throttle → m/s²

        # Body-frame accelerations
        ax = drag_ax + np.sin(state.pitch) * thrust
        ay = drag_ay - np.sin(state.roll) * thrust
        az = drag_az + np.cos(state.roll) * np.cos(state.pitch) * thrust - self.gravity

        # Angular accelerations
        roll_dd = cmd[0] / self.inertia_roll
        pitch_dd = cmd[1] / self.inertia_pitch
        yaw_dd = cmd[2] / self.inertia_yaw

        next_state = VehicleState(
            x=state.x + state.vx * dt,
            y=state.y + state.vy * dt,
            z=state.z + state.vz * dt,
            vx=state.vx + ax * dt,
            vy=state.vy + ay * dt,
            vz=state.vz + az * dt,
            roll=state.roll + state.roll * dt,  # simplified
            pitch=state.pitch + state.pitch * dt,
            yaw=state.yaw + state.yaw * dt,
        )
        next_state.roll += roll_dd * dt
        next_state.pitch += pitch_dd * dt
        next_state.yaw += yaw_dd * dt

        return next_state

    def predict_with_uncertainty(self, state: VehicleState, dt: float = 0.01,
                                 noise_std: float = 0.1) -> List[VehicleState]:
        """Predict with Monte Carlo uncertainty sampling."""
        samples = []
        for _ in range(20):
            noisy = VehicleState(
                x=state.x + np.random.randn() * noise_std,
                y=state.y + np.random.randn() * noise_std,
                z=state.z + np.random.randn() * noise_std,
                vx=state.vx + np.random.randn() * noise_std * 0.5,
                vy=state.vy + np.random.randn() * noise_std * 0.5,
                vz=state.vz + np.random.randn() * noise_std * 0.5,
                roll=state.roll, pitch=state.pitch, yaw=state.yaw,
            )
            samples.append(self.predict(noisy, dt))
        return samples

    def check_recovery(self, state: VehicleState) -> bool:
        """Check if current state is recoverable (not in unrecoverable dive)."""
        if state.z < 0 or state.z > 5000:
            return False
        if abs(state.roll) > np.radians(90):
            return False
        if abs(state.pitch) > np.radians(70):
            return False
        if abs(state.vz) > 30:
            return False
        return True