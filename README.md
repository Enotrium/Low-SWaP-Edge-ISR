#  SNN FPGA Accelerator for Low-SWaP Edge ISR

> Event-Driven Spiking Neural Network accelerator hardened for defense autonomous systems.
> Under $100 BOM, under 5W draw on XC7Z020 (PYNQ-Z2).

---

## SWaP Profile

| Dimension | Value | Provenance |
|---|---|---|
| Platform | AMD/Xilinx Zynq-7020 (XC7Z020-1CLG400C), PYNQ-Z2 carrier | `hardware/constraints/pynq_z2.xdc` |
| Flight integration | COTS dev board; optional custom ISR payload PCB | `docs/deployment.md` |
| Power (subsystem budget) | ≈1.41 W estimated, full breakdown per block | `docs/architecture.md` § Power Budget |
| Power (platform envelope) | <5 W target incl. board overhead; 5 V / 3 A input | `docs/deployment.md` |
| Cost | <$100 FPGA BOM target | — |
| Compute fabric | 2048 LIF neurons (16 groups × 128), 100 MHz, 16-bit membrane / 8-bit weights, on-chip STDP | `config/snn_params.yaml` |
| HD encoding | 512-dim hypervector swarm encoder | `hardware/hdl/rtl/weapon_systems/hd_swarm_encoder.v` |
| Inference latency | <100 cycles target (<1 µs @ 100 MHz) | Performance Targets below |

**Inference task:** event-driven multi-sensor ISR — spike-encoded RWR / acoustic / RF streams → SNN threat classification and tracking, with HDC cognitive-map navigation for GPS-denied operation and HD-vector swarm state sharing.

> ⚠️ Power and latency figures are **design estimates**, not measured silicon numbers. Post-synthesis and on-board measurements are pending; reproducible runs will be committed to the org [`evaluations`](https://github.com/Enotrium/evaluations) repo (`benchmark.py` → `experiments/benchmark_energy.py` → `hdc/efficiency.py`).

## Arthedain Platform Integration

This repo is the **hardware deployment tier of [Arthedain](https://github.com/Enotrium/arthedain)**, Enotrium's edge SNN/HDC platform:

- **Models** are developed and trained in Arthedain (Python/PyTorch, 125+ HDC modules). The `hdc/` package here mirrors `arthedain/hdc/` module-for-module (`cognitive_map`, `planner`, `multi_agent_hdc`, `multimodal_hdc`, `ecc`, `error_masking`, …).
- **Parameters** flow through `config/generate_params.py`, which emits matched Verilog (`.vh`), Python, and C/HLS headers from one `snn_params.yaml` — software and fabric stay in lockstep.
- **Execution** happens in this repo's RTL (`hardware/hdl/`) and Vitis HLS (`hardware/hls/`) implementations on the Zynq fabric.
- **Roadmap:** the hand-written Verilog here is slated to be superseded by generated, type-verified RTL from [Osgiliath](https://github.com/Enotrium/Osgiliath)'s `clash-hdc`.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   weapon_top.v (PYNQ-Z2)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   ┌──────────┐   │
│  │ 16 Neuron │ │  Spike   │  │ EW Decep │   │   APS    │   │
│  │  Groups   │→│  Router  │→ │ Generator│→  │  Fire    │   │
│  │ (LIF+STDP)│ │(Multicast│  │ (RGPO/   │   │ Control  │   │
│  └──────────┘  └──────────┘  │ VGPO/IAM │   └──────────┘   │
│                              │ /Noise)  │                  │
│  ┌──────────┐  ┌──────────┐  └──────────┘                  │
│  │ HD Swarm │  │   ECC    │                                │
│  │ Encoder  │  │ Fault    │  AXI4-Lite Config Regs         │
│  │ (512-dim)│  │ Injector │  (0x00-0x4C defense regs)      │
│  └──────────┘  └──────────┘                                │
└────────────────────────────────────────────────────────────┘
```

## Key Capabilities

### 1. Low-SWaP Edge ISR
Event-driven processing: power consumed **only when spikes occur** — critical for battery-constrained loitering drones. Process EO/IR or RF sensor data for **days instead of hours** on the same battery.

- `benchmark.py` → `experiments/benchmark_energy.py` → `hdc/efficiency.py`

### 2. On-Chip Continual Learning 
Update decision boundaries **without transmitting data** — no RF emissions to intercept, no satellite link dependency.

- `experiments/threat_detection.py` lines 7-26: concept drift, adversarial perturbation, 50-sample adaptation
- `tests/onchip_stdp_experiment.py` — STDP weight updates on FPGA fabric
- `tests/fpga_stdp_parity.py` — HW/SW parity validation

### 3. Electronic Warfare / Countermeasure Hardening
- **ECC protection** against SEU bit flips (radiation/EMP): `hdc/ecc.py`, `hardware/hdl/rtl/weapon_systems/ecc_fault_injector.v`
- **Graceful degradation**: `hdc/error_masking.py`
- **Adversarial robustness**: `hdc/oracle_defense.py`
- **Bounded <1μs latency**: Cycle-accurate RTL with no OS jitter

### 4. Autonomous Navigation (GPS-Denied)
- `hdc/cognitive_map.py` — Position encoding / SLAM
- `hdc/planner.py` — Mission path planning under uncertainty
- `hdc/drone_control.py` — Low-level flight policies
- `hdc/world_model.py` / `hdc/physics_world_model.py` — Vehicle dynamics prediction

### 5. Swarm Coordination (Multi-Agent, LPI)
- `hdc/multi_agent_hdc.py` — HD vector state sharing (compressed, LPI)
- `hardware/hdl/rtl/weapon_systems/hd_swarm_encoder.v` — FPGA-accelerated encoding

### 6. Sensor Fusion
- `hdc/multimodal_hdc.py` — Radar + Acoustic + EO/IR → common HD vector space
- `experiments/supply_chain.py`, `hdc/knowledge_graph.py` — Mission reasoning

---

## Concrete SEAD Mission Pipeline

```
Sense → Identify → Localize → Plan → Coordinate → Adapt
  │         │          │        │         │          │
  ▼         ▼          ▼        ▼         ▼          ▼
RWR +     SNN       HDC      HDC      multi_     onchip
acoustic  threat    cognitive planner  agent      STDP
spikes    class     map                       HD vectors
```

1. **Sense**: RWR + acoustic encoded as spike trains → SNN
2. **Identify**: SNN group 4-5 classify threat (SAM/AAA/AAM)
3. **Localize**: HDC cognitive map (GPS-denied)
4. **Plan**: Evasive route through threat zones
5. **Coordinate**: HD vector sharing with swarm
6. **Adapt**: On-chip STDP updates for new threat signatures

All on <$100 FPGA, <5W.

---

## File Structure

```
Low-SWaP-Edge-ISR/
├── config/
│   ├── snn_params.yaml          # System parameters
│   ├── generate_params.py       # Multi-format codegen
│   └── generated/
│       ├── snn_params.vh        # Verilog header (generated)
│       ├── snn_params.py        # Python constants (generated)
│       └── snn_params.h         # C/HLS header (generated)
├── hardware/
│   ├── hdl/
│   │   ├── rtl/
│   │   │   ├── common/
│   │   │   │   ├── fifo.v                # ECC-protected FIFO
│   │   │   │   └── snn_config_regs.v     # AXI4-Lite register file
│   │   │   ├── neurons/
│   │   │   │   └── lif_neuron.v          # LIF neuron with STDP
│   │   │   ├── router/
│   │   │   │   └── spike_router.v        # AER multicast router
│   │   │   ├── core/
│   │   │   │   └── neuron_group_core.v   # Parallel neuron group
│   │   │   ├── weapon_systems/
│   │   │   │   ├── ew_deception_generator.v  # EW waveforms
│   │   │   │   ├── aps_fire_control.v        # APS hard-kill
│   │   │   │   ├── hd_swarm_encoder.v        # HD swarm vectors
│   │   │   │   └── ecc_fault_injector.v      # SEU protection
│   │   │   └── top/
│   │   │       ├── snn_top.v                  # SNN + weapons
│   │   │       └── weapon_top.v               # Platform top
│   │   └── tb/
│   │       └── weapon_tb.v                    # System testbench
│   ├── hls/
│   │   ├── src/snn_top_hls.cpp               # Vitis HLS accelerator
│   │   ├── scripts/build_hls.tcl              # HLS build
│   │   └── include/
│   └── scripts/
│       └── build_vivado.tcl                   # Vivado build
├── software/python/snn_fpga_accelerator/
│   ├── __init__.py              # Package exports
│   ├── accelerator.py           # Main WeaponSNNAccelerator class
│   ├── defense.py               # EW, APS, Swarm, Classifier
│   ├── navigation.py            # GPS-denied nav, path planning
│   ├── spike_encoding.py        # Sensor-to-spike encoders
│   └── exceptions.py            # Defense exceptions
├── experiments/
│   ├── threat_detection.py      # Concept drift + adversarial tests
│   └── ew_aps_sead.py           # SEAD mission pipeline
├── tests/
│   └── onchip_stdp_experiment.py # FPGA STDP validation
└── docs/
```

## Build Instructions

### FPGA (Vivado)
```bash
cd hardware/scripts
vivado -source build_vivado.tcl
# Output: ../outputs/weapon_snn.bit
```

### HLS (Vitis)
```bash
cd hardware/hls/scripts
vitis_hls -f build_hls.tcl
```

### Python Tests
```bash
cd config
python generate_params.py          # Generate headers
cd ../experiments
python threat_detection.py         # Concept drift + learning
python ew_aps_sead.py              # Full SEAD mission
cd ../tests
python onchip_stdp_experiment.py   # STDP validation
```

## AXI Register Map (Defense Extensions)

| Address | Register       | Description                     |
|---------|----------------|---------------------------------|
| 0x30    | WEAPON_CTRL    | [0]=arm, [1]=auto-engage        |
| 0x34    | TARGET_ID      | Selected threat track ID        |
| 0x38    | EW_MODE        | 0=off, 1=RGPO, 2=VGPO, 3=IAM... |
| 0x3C    | APS_CMD        | Hard-kill fire trigger          |
| 0x40    | SWARM_STATE    | Drone role/state vector         |
| 0x44    | MISSION_STATE  | 0=standby, 1=search, 2=track... |
| 0x20    | STATUS         | ECC errors, FIFO overflow, etc. |
| 0x28    | VERSION        | "SNN" v2 (weaponized)           |

## Performance Targets

| Metric              | Target          |
|---------------------|-----------------|
| FPGA die cost       | <$100 (xc7z020) |
| Power draw          | <5W             |
| Inference latency   | <100 cycles     |
| EW waveform latency | <1 μs           |
| APS response        | <1 μs bounded   |
| SEU recovery        | Single-cycle ECC|

