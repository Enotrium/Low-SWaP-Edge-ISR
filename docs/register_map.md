# AXI4-Lite Register Map — Weaponized SNN

Base address: 0x43C0_0000

## Core SNN Registers (Standard)

| Offset | Name | Bits | Access | Description |
|--------|------|------|--------|-------------|
| 0x00 | SNN_CTRL | 31:0 | RW | [0]=enable, [1]=reset, [2]=stdp_enable |
| 0x04 | NUM_NEURONS | 15:0 | RO | 2048 |
| 0x08 | NUM_GROUPS | 7:0 | RO | 16 |
| 0x0C | SPIKE_COUNT | 31:0 | RO | Total spikes processed |
| 0x10 | OUTPUT_RATE_0 | 15:0 | RO | Group 0 firing rate |
| 0x14 | OUTPUT_RATE_1 | 15:0 | RO | Group 1 firing rate |
| 0x18 | OUTPUT_RATE_2 | 15:0 | RO | Group 2 firing rate |
| 0x1C | OUTPUT_RATE_3 | 15:0 | RO | Group 3 firing rate |

## Defense Extension Registers

| Offset | Name | Bits | Access | Description |
|--------|------|------|--------|-------------|
| 0x20 | STATUS | 31:0 | RO | [0]=fifo_overflow, [1]=ecc_error, [2]=watchdog_expired, [7:4]=ecc_syndrome |
| 0x24 | THREAT_CLASS | 7:0 | RO | Detected threat class (1-8) |
| 0x28 | VERSION | 31:0 | RO | "SNN" v2 = 0x534E4E02 |
| 0x30 | WEAPON_CTRL | 1:0 | RW | [0]=arm, [1]=auto_engage |
| 0x34 | TARGET_ID | 7:0 | RW | Selected threat track ID |
| 0x38 | EW_MODE | 2:0 | RW | 0=OFF, 1=RGPO, 2=VGPO, 3=IAM, 4=CrossEye, 5=Saturation |
| 0x3C | APS_CMD | 0:0 | RW | 1=fire hard-kill effector on TARGET_ID |
| 0x40 | SWARM_STATE | 31:0 | RW | Bit-packed swarm status vector |
| 0x44 | MISSION_STATE | 2:0 | RW | 0=STANDBY, 1=SEARCH, 2=TRACK, 3=IDENTIFY, 4=ENGAGE, 5=BDA |
| 0x48 | THREAT_DISTRIBUTION_MONITOR | 31:0 | RO | Concept drift detection output |
| 0x4C | WATCHDOG | 31:0 | RW | Write any value to kick watchdog; read remaining cycles |

## WEAPON_CTRL (0x30) Field Definitions

| Bit | Name | Description |
|-----|------|-------------|
| 0 | ARM | Set to 1 to unlock effector outputs. Cleared by watchdog expiry |
| 1 | AUTO_ENGAGE | Set to 1 to enable autonomous engagement |
| 7:2 | Reserved | Write 0 |

Both ARM and AUTO_ENGAGE must be set for any effector activation.

## STATUS (0x20) Field Definitions

| Bit | Name | Description |
|-----|------|-------------|
| 0 | FIFO_OVERFLOW | Spike input FIFO overflow |
| 1 | ECC_ERROR | ECC-correctable memory error |
| 2 | WATCHDOG_EXPIRED | Watchdog timer expired |
| 3 | ECC_DOUBLE | ECC double error (uncorrectable) |
| 7:4 | ECC_SYNDROME | Last ECC syndrome value |
| 15:8 | GROUP_ACTIVE | Active neuron groups (one-hot) |

## EW_MODE (0x38) Values

| Value | Mode | Description |
|-------|------|-------------|
| 0x0 | OFF | EW silent |
| 0x1 | RGPO | Range Gate Pull-Off |
| 0x2 | VGPO | Velocity Gate Pull-Off |
| 0x3 | IAM | Inverse Amplitude Modulation |
| 0x4 | CROSS_EYE | Cross-Eye Jamming |
| 0x5 | SATURATION | Barrage/Saturation Noise |

## Safety Notes

1. All weapon registers (0x30-0x44) are ECC-protected (Hamming 12,8)
2. Writing WEAPON_CTRL requires both ARM and AUTO_ENGAGE set simultaneously
3. Watchdog (0x4C) must be kicked within WATCHDOG_CYCLES or SAFE is forced
4. APS_CMD is automatically cleared after KILL_CYCLES
5. EW and APS are mutually exclusive; APS has priority

## Python Access Example

```python
from snn_fpga_accelerator import WeaponSNNAccelerator

accel = WeaponSNNAccelerator(simulation_mode=True)
status = accel.get_status()
print(f"Weapon state: {status['weapon_state']}")
print(f"Active tracks: {status['active_tracks']}")