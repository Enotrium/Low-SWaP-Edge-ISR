"""
HDC Mission Path Planning under uncertainty.
Runs lightweight HD vector operations — feasible on small FPGAs.
"""
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from .cognitive_map import Position2D, CognitiveMap


@dataclass
class Waypoint:
    position: Position2D
    altitude_m: float = 100.0
    loiter_time_s: float = 0.0
    action: str = "transit"

    def distance_to(self, other: "Waypoint") -> float:
        return np.sqrt(
            (self.position.x - other.position.x) ** 2
            + (self.position.y - other.position.y) ** 2
        )


@dataclass
class ThreatZone:
    center: Position2D
    radius_m: float
    threat_type: str = "unknown"
    lethality: float = 0.5


class PathPlanner:
    """
    Mission path planner using HD vector operations.
    Plans routes around threat zones, minimizes exposure.
    """

    def __init__(self, cognitive_map: CognitiveMap):
        self.map = cognitive_map
        self.waypoints: List[Waypoint] = []
        self.current_leg: int = 0
        self.avoidance_zones: List[ThreatZone] = []

    def add_threat_zone(self, center: Position2D, radius_m: float,
                        threat_type: str = "unknown") -> None:
        self.avoidance_zones.append(ThreatZone(center, radius_m, threat_type))

    def _line_threat_distance(self, start: Position2D, end: Position2D,
                              zone: ThreatZone) -> float:
        """Compute minimum distance from line segment to threat zone center."""
        dx = end.x - start.x
        dy = end.y - start.y
        if dx == 0 and dy == 0:
            return np.sqrt((zone.center.x - start.x) ** 2
                           + (zone.center.y - start.y) ** 2)

        t = max(0.0, min(1.0, ((zone.center.x - start.x) * dx
                               + (zone.center.y - start.y) * dy)
                         / (dx ** 2 + dy ** 2)))
        closest_x = start.x + t * dx
        closest_y = start.y + t * dy
        return np.sqrt((zone.center.x - closest_x) ** 2
                       + (zone.center.y - closest_y) ** 2)

    def plan_route(self, start: Position2D, end: Position2D,
                   altitude_m: float = 100.0) -> List[Waypoint]:
        """Plan route from start to end, avoiding threat zones."""
        waypoints = [Waypoint(start, altitude_m, 0, "transit")]

        needs_diversion = False
        best_offset = np.array([0.0, 0.0])
        for zone in self.avoidance_zones:
            d = self._line_threat_distance(start, end, zone)
            if d < zone.radius_m:
                needs_diversion = True
                # Perpendicular offset direction
                dx = end.x - start.x
                dy = end.y - start.y
                direct = np.sqrt(dx ** 2 + dy ** 2)
                perp = np.array([-dy / direct, dx / direct])
                side = np.sign(perp[0] * (zone.center.y - start.y)
                              - perp[1] * (zone.center.x - start.x))
                best_offset += perp * zone.radius_m * 1.5 * side

        if needs_diversion:
            mid = Position2D(
                (start.x + end.x) / 2 + best_offset[0],
                (start.y + end.y) / 2 + best_offset[1],
            )
            waypoints.append(Waypoint(mid, altitude_m, 0, "evade"))

        waypoints.append(Waypoint(end, altitude_m, 0, "transit"))
        self.waypoints = waypoints
        return waypoints

    def compute_risk(self, position: Position2D) -> float:
        """Compute cumulative threat risk at a position."""
        risk = 0.0
        for zone in self.avoidance_zones:
            d = np.sqrt((position.x - zone.center.x) ** 2
                       + (position.y - zone.center.y) ** 2)
            if d < zone.radius_m:
                risk += zone.lethality * (1.0 - d / zone.radius_m)
        return min(risk, 1.0)

    def get_current_waypoint(self) -> Optional[Waypoint]:
        if self.current_leg < len(self.waypoints):
            return self.waypoints[self.current_leg]
        return None

    def advance_waypoint(self) -> None:
        if self.current_leg < len(self.waypoints) - 1:
            self.current_leg += 1

    def replan(self, current: Position2D, target: Position2D) -> List[Waypoint]:
        """Replan from current position due to new threats."""
        return self.plan_route(current, target)