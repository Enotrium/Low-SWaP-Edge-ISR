# Weaponized SNN FPGA Accelerator — Architecture

## System Overview

This accelerator integrates an event-driven Spiking Neural Network with defense subsystems on a <$100 FPGA (XC7Z020). The design targets low-SWaP autonomous platforms (drones, loitering munitions) operating in contested electromagnetic environments.

## Neuron Group Allocation

| Group | Function                   | Neurons | Connections     |
|-------|----------------------------|---------|-----------------|
| 0     | Sensor RWR (radar warning) | 128     | → 1, 4, 5      |
| 1     | Sensor Acoustic            | 128     | → 0, 4         |
| 2     | Sensor RF/COMINT           | 128     | → 3, 4         |
| 3     | Feature Extraction         | 128     | → 4, 5         |
| 4     | Threat Classification      | 128     | → 5, 14        |
| 5     | Threat Tracking            | 128     | → 14           |
| 6-9   | Navigation (HDC cognitive) | 128×4   | → 10, 11       |
| 10    | Path Planning              | 128     | → 13           |
| 11    | Flight Control             | 128     | →  default      |
| 12    | Mission State              | 128     | → 9, 10, 13    |
| 13    | EW Control                 | 128     | → EW generator |
| 14    | APS Fire Control           | 128     | → APS clk |
| 15    | Swarm Coordination         | 128     | → HD encoder   |

## Clock Domains

| Clock   | Frequency | Domain          |
|---------|-----------|-----------------|
| sys_clk | 100 MHz   | Primary SNN     |
| axi_clk | 100 MHz   | AXI4-Lite config|
| ew_dac  | 200 MHz   | EW DAC output   |
| aps_io  | 100 MHz   | APS effector    |

## Power Budget (XC7Z020, estimated)

| Subsystem        | Power (mW) |
|------------------|------------|
| Neuron Groups ×16| 800        |
| Spike Router     | 150        |
| EW Generator     | 45         |
| APS Controller   | 30         |
| Swarm Encoder    | 60         |
| ECC + Config     | 25         |
| Clocking         | 100        |
| I/O              | 200        |
| **Total**        | **~1,410** |

## Dataflow

```
Sensors (RWR/Acoustic/RF)
       │
       ▼
  sensor_to_spike ──► AER Spike Train (32-bit packets)
       │
       ▼
  [FIFO] ──► Spike Router (round-robin multicast)
       │
       ▼
  Neuron Groups (16× parallel LIF neurons)
       │
       ├──► Threat Class Group ──► APS Fire Control ──► Hard-kill Effector
       ├──► EW Control Group   ──► EW Generator ──► DAC/RF Frontend
       ├──► Nav Groups         ──► HDC Cognitive Map (GPS-denied)
       └──► Swarm Group        ──► HD Encoder ──► LPI Radio
```

## Safety Architecture

- Hardware safety interlock (WEAPON_CTRL[0]) on all effector outputs
- Two-person rule: ARM and AUTO_ENGAGE must both be set
- EW and APS mutually exclusive (APS overrides EW during engagement)
- Watchdog timer with countdown
- ECC on all critical state registers