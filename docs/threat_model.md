# Adversarial Threat Model

## Assumed Threat Environment
The weaponized SNN accelerator operates in contested electromagnetic environments:
- Radar warning receivers (RWR) detecting SAM/AAA radar
- Acoustic sensors detecting gunfire and vehicle signatures
- RF/COMINT intercept of adversary communications

## Threat Classes (SNN Groups 4-5)

| Class | Threat Type | Signature | Countermeasure |
|-------|------------|-----------|----------------|
| 1 | SAM (Surface-to-Air Missile) | Ku-band tracking radar, CW illumination | RGPO, Cross-Eye |
| 2 | AAA (Anti-Aircraft Artillery) | X-band fire control, acoustic muzzle blast | Saturation noise, evasive maneuver |
| 3 | AAM (Air-to-Air Missile) | Active radar homing, IR plume | VGPO, flares via APS |
| 4 | MANPADS | IR/UV dual-band | Directed IR countermeasures |
| 5 | SAM Search Radar | S-band volume search | Stand-off, low-RCS routing |
| 6 | EW Jammer | Broadband noise, deceptive | Frequency hopping, LPI waveform |
| 7 | UAV Swarm | Multistatic radar, optical | Swarm defense, hard-kill |
| 8 | Unknown/Novel | Anomalous signature | On-chip STDP adaptation |

## Adversarial Capabilities Assumed

### Jamming
- Broadband noise jamming (barrage)
- Deceptive jamming (range/velocity gate pull-off)
- DRFM-based coherent jamming
- Multistatic jammer networks

### Spoofing
- GPS spoofing (mitigated by GPS-denied navigation via HDC cognitive map)
- Sensor spoofing (detected by oracle_defense anomaly detection)
- Communication spoofing (encrypted HD vector encoding)

### Kinetic
- SAM engagement envelopes (0-100km, 0-30km altitude)
- AAA engagement (0-5km range, 0-3km altitude)
- MANPADS (0-5km range, 0-4km altitude)

### Environmental
- Radiation-induced SEU (ECC protected)
- EMP (hardened FPGA I/O)
- Temperature extremes (-40°C to +85°C, industrial grade)

## EW Threat Library

### RGPO (Range Gate Pull-Off)
Targets range-tracking radars by progressively delaying radar return.
Parameters: pull-off rate, final range offset, pull-off profile.

### VGPO (Velocity Gate Pull-Off)
Targets Doppler radars by shifting return frequency.
Parameters: frequency offset rate, final Doppler shift.

### IAM (Inverse Amplitude Modulation)
Transmits amplitude-modulated waveform inverse to victim radar.
Disrupts conical scan and monopulse tracking.

### Cross-Eye Jamming
Coherent jamming using two spatially separated antennas.
Creates angular deception against monopulse radars.

### Saturation/Barrage Noise
Broadband noise transmission across radar bandwidth.
Denies range and Doppler information.

## Detection & Resilience

### Concept Drift Detection
`experiments/threat_detection.py` monitors THREAT_DISTRIBUTION_MONITOR (0x48) for environmental changes. When drift exceeds threshold, triggers on-chip STDP adaptation without external comms.

### Adversarial Perturbation Detection
`hdc/oracle_defense.py` compares sensor HD vectors against learned oracle distributions. Flags anomalies via Mahalanobis distance (>3σ threshold).

### Fault Resilience
- ECC (Hamming 12,8) on all critical state
- Graceful accuracy degradation (not catastrophic failure)
- Single-cycle SEU correction