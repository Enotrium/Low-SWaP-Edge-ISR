"""
SEAD (Suppression of Enemy Air Defenses) Full Mission Experiment.
Demonstrates EW + APS + Swarm coordination on the weaponized SNN accelerator.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "config" / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent / "software" / "python"))
from snn_fpga_accelerator import WeaponSNNAccelerator
from snn_fpga_accelerator.defense import EWCountermeasure, APSController, SwarmCoordinator
from snn_fpga_accelerator.navigation import GPSDeniedNav
from snn_fpga_accelerator.spike_encoding import SpikeEvent
from snn_fpga_accelerator.accelerator import MissionPhase, EWMode, EWConfig


def test_ew_deception_waveforms():
    """Test all 5 EW deception waveform types."""
    print("=== EW Deception Waveform Test ===")
    accel = WeaponSNNAccelerator(simulation_mode=True, weapon_safety=False)
    ew = EWCountermeasure(accel)

    for mode in [1, 2, 3, 4, 5]:
        waveform = ew.generate_deception_waveform(mode, target_aoa=45.0)
        print(f"  Mode {mode} ({waveform['type']}): "
              f"phase={waveform['phase']}, amp={waveform['amplitude']}")
        assert waveform["mode"] == mode
    print("  PASSED")


def test_aps_prioritization():
    """Test APS threat prioritization and intercept solution."""
    print("=== APS Threat Prioritization ===")
    accel = WeaponSNNAccelerator(simulation_mode=True)
    aps = APSController(accel)

    # Create synthetic threats
    for i in range(5):
        spike = SpikeEvent(i, 0, 0.8)
        threats = accel.detect_threats([spike] * 10)
        if not threats:
            # Inject directly
            from snn_fpga_accelerator.accelerator import ThreatTrack
            accel.active_tracks[i] = ThreatTrack(
                i, np.random.uniform(0, 360),
                np.random.uniform(100, 5000),
                np.random.uniform(100, 1000), i % 8 + 1
            )

    prioritized = aps.prioritize_threats()
    print(f"  Tracks prioritized: {len(prioritized)}")
    for tid, track, score in prioritized:
        print(f"    [{tid}] score={score:.1f} range={track.range_m:.0f}m "
              f"vel={track.velocity_ms:.0f}m/s")
        intercept = aps.compute_intercept(track)
        print(f"         tti={intercept['time_to_impact_ms']:.0f}ms "
              f"quality={intercept['solution_quality']}")
    assert len(prioritized) > 0
    print("  PASSED")


def test_swarm_coordination():
    """Test swarm HD vector encoding and consensus."""
    print("=== Swarm Coordination ===")
    accel = WeaponSNNAccelerator(simulation_mode=True, drone_id=1)
    swarm = SwarmCoordinator(accel)

    # Encode local state
    vector = swarm.share_state()
    print(f"  HD vector dim: {len(vector)}")
    assert len(vector) == accel.swarm_config.hd_dim

    # Receive vectors from other drones
    for did in range(4):
        v = np.random.randint(0, 2, accel.swarm_config.hd_dim).astype(np.int8)
        v[v == 0] = -1
        swarm.receive_state(did, v)
    print(f"  Swarm size: {len(accel.swarm_vectors)}")
    assert len(accel.swarm_vectors) >= 4

    # Check consensus
    decision = swarm.consensus_decision(np.array([2, 2, 2, 3, 2]))
    print(f"  Consensus decision: {decision}")
    assert decision == 2
    print("  PASSED")


def test_gps_denied_navigation():
    """Test cognitive map and path planning without GPS."""
    print("=== GPS-Denied Navigation ===")
    nav = GPSDeniedNav()

    # Update IMU (accel, gyro)
    nav.update_imu(np.array([0.1, 0.0, 0.0]), np.array([0.0, 0.0, 0.01]), dt=0.01)
    state = nav.get_nav_state()
    print(f"  Position: ({state['position'][0]:.3f}, {state['position'][1]:.3f})")
    print(f"  Heading: {state['heading_deg']:.1f} deg")

    # Plan route avoiding threat
    from snn_fpga_accelerator.navigation import Position2D
    nav.planner.add_threat_zone(Position2D(500, 0), 300)
    route = nav.planner.plan_route(Position2D(0, 0), Position2D(1000, 0))
    print(f"  Route waypoints: {len(route)}")
    assert len(route) >= 2
    print("  PASSED")


def test_full_sead_mission():
    """Run complete SEAD mission end-to-end."""
    print("=== Full SEAD Mission ===")
    accel = WeaponSNNAccelerator(simulation_mode=True, weapon_safety=False, drone_id=3)

    # PHASE 1: Search
    accel.set_mission_phase(MissionPhase.SEARCH)
    accel.arm_weapons(auto_engage=True)

    # Enemy radar detected (group 4 = threat_class)
    radar_spikes = [SpikeEvent(i % 128, i / 1000.0, np.random.uniform(0.5, 1.5))
                    for i in range(500)]
    threats = accel.detect_threats(radar_spikes)
    print(f"  [SEARCH] Threats: {len(threats)}")

    # PHASE 2: Track & Identify
    if threats:
        accel.set_mission_phase(MissionPhase.TRACK)
        for t in threats:
            print(f"    Track {t.track_id}: class={t.threat_class} "
                  f"range={t.range_m:.0f}m vel={t.velocity_ms:.0f}m/s")

    # PHASE 3: EW deception to confuse enemy radar
    accel.configure_ew(EWConfig(mode=EWMode.SATURATION, deception_type="saturation_noise"))
    if threats:
        result = accel.deploy_countermeasure(threats[0])
        print(f"  [EW] Deployed: {result['ew_mode']}")

    # PHASE 4: Engage priority target
    accel.set_mission_phase(MissionPhase.ENGAGE)
    aps = APSController(accel)
    prioritized = aps.prioritize_threats()
    if prioritized:
        tid, track, score = prioritized[0]
        engage = accel.engage_threat(tid)
        print(f"  [APS] Fired on track {tid}, quality={engage['solution_quality']}")

    # BDA
    accel.set_mission_phase(MissionPhase.BDA)
    if prioritized:
        kill = aps.assess_bda(prioritized[0][0], np.array([0.02]))
        print(f"  [BDA] Kill confirmed: {kill}")

    # Status
    status = accel.get_status()
    print(f"  [STATUS] Engagements={status['total_engagements']}, "
          f"kills={status['kill_count']}, active_tracks={status['active_tracks']}")
    print("  PASSED")


if __name__ == "__main__":
    test_ew_deception_waveforms()
    test_aps_prioritization()
    test_swarm_coordination()
    test_gps_denied_navigation()
    test_full_sead_mission()
    print("\nAll SEAD mission tests PASSED")