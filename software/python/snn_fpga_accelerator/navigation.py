"""
GPS-denied navigation and path planning modules.
Implements cognitive map, circular angle encoding, and mission planning.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Position2D:
    """2D position with uncertainty."""
    x: float = 0.0
    y: float = 0.0
    uncertainty: float = 1.0

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y])


@dataclass
class Waypoint:
    """Mission waypoint."""
    position: Position2D
    altitude_m: float = 100.0
    loiter_time_s: float = 0.0
    action: str = "transit"  # transit, orbit, engage, observe

    def distance_to(self, other: 'Waypoint') -> float:
        return np.sqrt((self.position.x - other.position.x)**2 +
                      (self.position.y - other.position.y)**2)


class CognitiveMap:
    """Position encoder for GPS-denied spatial awareness."""

    def __init__(self, cells: int = 1024):
        self.cells = cells
        self.cell_activations = np.zeros(cells)
        self.landmarks: Dict[int, Position2D] = {}
        self.visited_cells = set()

    def encode_position(self, x: float, y: float) -> np.ndarray:
        """Encode position as HD vector representation."""
        cell_x = int((x + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_y = int((y + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_id = cell_x * int(np.sqrt(self.cells)) + cell_y
        self.visited_cells.add(cell_id)
        self.cell_activations[cell_id] = 1.0
        return self.cell_activations

    def update_landmark(self, landmark_id: int, bearing: float,
                        estimated_range: float) -> None:
        """Update landmark position from bearing/range measurement."""
        if landmark_id in self.landmarks:
            existing = self.landmarks[landmark_id]
            # Simple Kalman-like update
            alpha = 0.3
            existing.x += alpha * (estimated_range * np.cos(bearing) - existing.x)
            existing.y += alpha * (estimated_range * np.sin(bearing) - existing.y)
            existing.uncertainty *= (1 - alpha)
        else:
            self.landmarks[landmark_id] = Position2D(
                x=estimated_range * np.cos(bearing),
                y=estimated_range * np.sin(bearing),
                uncertainty=10.0
            )

    def get_familiarity(self, x: float, y: float) -> float:
        """Return familiarity score for a position (SLAM loop closure)."""
        cell_x = int((x + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_y = int((y + 5000) / 10000 * np.sqrt(self.cells)) % int(np.sqrt(self.cells))
        cell_id = cell_x * int(np.sqrt(self.cells)) + cell_y
        return self.cell_activations[cell_id]


class PathPlanner:
    """Mission path planning under uncertainty."""

    def __init__(self, cognitive_map: CognitiveMap):
        self.map = cognitive_map
        self.waypoints: List[Waypoint] = []
        self.current_leg = 0
        self.avoidance_zones: List[Tuple[Position2D, float]] = []

    def add_threat_zone(self, center: Position2D, radius_m: float) -> None:
        """Add threat zone to avoid in planning."""
        self.avoidance_zones.append((center, radius_m))

    def plan_route(self, start: Position2D, end: Position2D,
                   altitude_m: float = 100.0) -> List[Waypoint]:
        """Plan route from start to end, avoiding threat zones."""
        direct_dist = np.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)

        # Check if direct route intersects threat zones
        needs_diversion = False
        for zone_center, zone_radius in self.avoidance_zones:
            # Line-point distance check
            dx = end.x - start.x
            dy = end.y - start.y
            t = max(0, min(1, ((zone_center.x - start.x) * dx +
                              (zone_center.y - start.y) * dy) / (dx**2 + dy**2)))
            closest_x = start.x + t * dx
            closest_y = start.y + t * dy
            dist = np.sqrt((zone_center.x - closest_x)**2 +
                          (zone_center.y - closest_y)**2)
            if dist < zone_radius:
                needs_diversion = True
                break

        waypoints = [Waypoint(start, altitude_m, 0, "transit")]

        if needs_diversion:
            # Create diversion waypoints around threat zones
            mid_x = (start.x + end.x) / 2
            mid_y = (start.y + end.y) / 2
            # Offset perpendicular to threat
            offset = 1000.0  # 1km offset
            perp_x = -(end.y - start.y) / direct_dist * offset
            perp_y = (end.x - start.x) / direct_dist * offset
            waypoints.append(Waypoint(
                Position2D(mid_x + perp_x, mid_y + perp_y),
                altitude_m, 0, "transit"
            ))

        waypoints.append(Waypoint(end, altitude_m, 0, "transit"))
        self.waypoints = waypoints
        return waypoints

    def get_current_waypoint(self) -> Optional[Waypoint]:
        """Get current navigation target waypoint."""
        if self.current_leg < len(self.waypoints):
            return self.waypoints[self.current_leg]
        return None

    def advance_waypoint(self) -> None:
        """Advance to next waypoint in route."""
        if self.current_leg < len(self.waypoints) - 1:
            self.current_leg += 1


class GPSDeniedNav:
    """Integrated GPS-denied navigation system."""

    def __init__(self):
        self.cognitive_map = CognitiveMap(cells=1024)
        self.planner = PathPlanner(self.cognitive_map)
        self.position = Position2D()
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.heading_deg = 0.0

    def update_imu(self, accel: np.ndarray, gyro: np.ndarray, dt: float = 0.01) -> None:
        """Update from IMU measurements."""
        self.velocity[0] += accel[0] * dt
        self.velocity[1] += accel[1] * dt
        self.position.x += self.velocity[0] * dt
        self.position.y += self.velocity[1] * dt
        self.heading_deg += np.degrees(gyro[2]) * dt
        self.heading_deg %= 360

    def update_optical_flow(self, flow_x: float, flow_y: float, dt: float = 0.01) -> None:
        """Correct position from optical flow."""
        correction = 0.1
        self.position.x += flow_x * correction
        self.position.y += flow_y * correction

    def correct_position(self, landmark_id: int, bearing: float,
                         est_range: float) -> None:
        """Position correction from landmark observation."""
        self.cognitive_map.update_landmark(landmark_id, bearing, est_range)

    def get_nav_state(self) -> Dict:
        """Get complete navigation state."""
        return {
            "position": (self.position.x, self.position.y),
            "position_uncertainty": self.position.uncertainty,
            "velocity": self.velocity.tolist(),
            "heading_deg": self.heading_deg,
            "gps_denied": True,
            "landmarks_known": len(self.cognitive_map.landmarks),
            "cells_visited": len(self.cognitive_map.visited_cells),
        }
