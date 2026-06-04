# PYNQ-Z2 Deployment Guide

## Hardware Requirements
- **Board**: PYNQ-Z2 (Digilent, XC7Z020-1CLG400C)
- **Carrier**: Custom ISR payload PCB (optional)
- **Sensors**: RWR frontend, acoustic array, EO/IR gimbal
- **Effectors**: EW DAC + RF frontend, APS hard-kill actuator
- **Power**: 5V/3A via USB or 7-15V barrel jack

## Pre-Flight Checklist

### 1. FPGA Bitstream
```bash
cd hardware/scripts
cpu generate_params.py    # Generate Verilog/Python/C headers
vivado -source build_civado.tcl
# Output: hardware/outputs/weapon_snn.bit
```

### 2. SD Card Image
1. Download PYNQ-Z2 v2.7 image from pynq.io
2. Flash to SD card (≥16 GB)
3. Mount BOOT partition, copy:
   - `weapon_snn.bit` → `/boot/weapon_snn.bit`
   - `weapon_top.hwh` → `/boot/weapon_top.hwh`
4. Create `/boot/config.txt`:
```
bitstream=weapon_snn.bit
```

### 3. Board Setup
1. Insert SD card into PYNQ-Z2
2. Set JP4 (boot) to SD position
3. Connect sensors/effectors to PMOD/Arduino headers:
   - JA: EW DAC output (12-bit)
   - JB: APS fire control
   - JC: Sensor input (RWR)
   - JD: Swarm radio UART
4. Connect Ethernet or Wi-Fi dongle
5. Power on

## Software Deployment

### Install Python Package
```bash
ssh xilinx@pynq
pip install snn-fpga-accelerator
```

### Initialize on Boot
```python
from snn_fpga_accelerator import WeaponSNNAccelerator

accel = WeaponSNNAccelerator(
    bitstream_path="/boot/weapon_snn.bit",
    simulation_mode=False,
    weapon_safety=True,
    drone_id=0
)
```

### Verify Hardware
```python
status = accel.get_status()
print(status)
# {'mission_phase': 'STANDBY', 'weapon_state': 'SAFE', ...}
```

## Mission Configuration

### SEAD Mission Config
```python
from snn_fpga_accelerator import MissionPhase, EWMode, EWConfig

# Phase 1: Search & Track
accel.set_mission_phase(MissionPhase.SEARCH)

# Arm weapons (requires physical safety key)
accel.weapon_safety = False  # HARDWARE KEY
accel.arm_weapons(auto_engage=False)

# Configure EW
accel.configure_ew(EWConfig(mode=EWMode.SATURATION))
```

### GPS-Denied Navigation Config
```python
from snn_fpga_accelerator.navigation import GPSDeniedNav, Position2D

nav = GPSDeniedNav()
nav.planner.add_threat_zone(Position2D(500, 0), 300)  # SAM site
route = nav.planner.plan_route(Position2D(0, 0), Position2D(1000, 0))
```

### Swarm Config
```python
from snn_fpga_accelerator.defense import SwarmCoordinator

swarm = SwarmCoordinator(accel)
vec = swarm.share_state()
# Broadcast vec to other drones via LPI radio
```

## Performance Monitoring
```bash
# Monitor power
cat /sys/class/hwmon/hwmon0/power1_input  # FPGA core power (mW)
cat /sys/class/hwmon/hwmon0/temp1_input   # FPGA temp (°C)

# Check ECC status
python -c "from snn_fpga_accelerator import WeaponSNNAccelerator; a=WeaponSNNAccelerator(); print(a.check_ecc_status())"
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Bitstream not loaded | `dmesg \| grep fpga` |
| No sensor data | Verify PMOD connections, run `sensor_to_spike.py` test |
| EW output muted | Check WEAPON_CTRL register (must be 0x03) |
| STDP not updating | Verify `stdp_enabled: true` in snn_params.yaml |
| ECC errors logged | Check radiation environment; increase fault_threshold |