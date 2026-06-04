# Weapon Safety Architecture

## Overview
The SNN FPGA accelerator implements a hardware-gated safety architecture to ensure autonomous weapons operate only under strict conditions. Safety is enforced at the RTL level — not dependent on software (no OS jitter, no stack overflow vulnerabilities).

## Safety Interlock

### Two-Person Rule (Hardware)
```
WEAPON_CTRL Register (0x30):
  Bit 0 — ARM          (set to 1 to unlock effectors)
  Bit 1 — AUTO_ENGAGE  (set to 1 to enable autonomous engagement)

  Both bits must be set simultaneously for any effector output.
  A watchdog timer (0x4C) clears ARM after WATCHDOG_CYCLES.
```

### Hardware Interlock Chain
```
ARM ─┬─→ AND ─→ Effector Enable
     │          ↑
AUTO_ENGAGE       │
     │            │
WATCHDOG_OK ─────┘
```

### Weapon State Machine
| State       | Register | Effect |
|-------------|----------|--------|
| SAFE        | 0x00     | All effectors disabled, EW silent |
| ARMED       | 0x01     | EW enabled, APS disarmed |
| AUTO_ENGAGE | 0x03     | All effectors enabled |
| OVERRIDE    | 0xFF     | Administrative override (debug only) |

## Subsystem-Specific Safeties

### Electronic Warfare
- EW output disabled when SAFE
- EW frequency hopping controlled independently
- EW and APS mutually exclusive (APS overrides EW during engagement)

### Active Protection System
- Safety interlock required for any hard-kill effector
- Kill confirmation from BDA (Battle Damage Assessment) before re-engage
- Maximum track limit enforced in hardware (APS_MAX_TRACKS = 32)

### Swarm Coordination
- LPI spread-spectrum for all inter-drone comms
- Encrypted HD vector encoding
- Bandwidth savings: ~98% vs raw sensor data (512 bits vs 4096 bytes)

## ECC Protection of Safety State
All safety-critical registers (WEAPON_CTRL, TARGET_ID, APS_CMD) are ECC-protected:
- Hamming(12,8) SECDED
- Single-bit SEU corrected in one cycle
- Double-bit error detected, triggers SAFE

## Watchdog Timer
- Configured in REG_WATCHDOG (0x4C)
- Counts down from WATCHDOG_CYCLES
- If not kicked before expiry, force SAFE
- Hardware-implemented, cannot be disabled by software

## Failure Modes & Recovery
| Failure | Detection | Response |
|---------|-----------|----------|
| SEU in safety reg | ECC syndrome | Correct or SAFE |
| Watchdog timeout | Timer expiry | Force SAFE |
| FIFO overflow | Overflow flag | Stall input |
| Double-bit error | ECC detect | SAFE, log error |
| Power loss | POR | SAFE on boot |