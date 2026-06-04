#!/usr/bin/env python3
"""
Parameter Generator — Single Source of Truth for SNN Accelerator.

Reads snn_params.yaml and generates:
  - config/generated/snn_params.vh   (Verilog `include header)
  - config/generated/snn_params.py   (Python constants)
  - config/generated/snn_params.h    (HLS/C++ header)

Author: Adapted from metr0jw's Event-Driven SNN Accelerator
"""

import os
import sys
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

def load_params() -> dict:
    yaml_path = SCRIPT_DIR / "snn_params.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)

def generate_verilog(params: dict) -> str:
    arch = params["architecture"]
    widths = params["widths"]
    wmem = params.get("weight_memory", {})
    defense = params.get("defense", {})

    num_groups = len(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))
    max_neurons = max(arch.get("group_sizes", [arch["neurons_per_group"]]))
    total_neurons = sum(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))
    global_id_width = (num_groups.bit_length() - 1) + (max_neurons.bit_length() - 1)

    lines = [
        "// ===========================================================================",
        "// Auto-generated SNN Parameters — DO NOT EDIT MANUALLY",
        "// Source: config/snn_params.yaml",
        "// Generator: config/generate_params.py",
        "// ===========================================================================",
        "",
        "`ifndef SNN_PARAMS_VH",
        "`define SNN_PARAMS_VH",
        "",
        "// --- Core Architecture ---",
        f"`define SNN_NUM_GROUPS            {num_groups}",
        f"`define SNN_NEURONS_PER_GROUP     {arch['neurons_per_group']}",
        f"`define SNN_MAX_NEURONS           {max_neurons}",
        f"`define SNN_TOTAL_NEURONS         {total_neurons}",
        f"`define SNN_MAX_FANOUT_INTER      {arch['max_fanout_inter']}",
        f"`define SNN_SPIKE_BUFFER_DEPTH    {arch['spike_buffer_depth']}",
        f"`define SNN_NUM_PARALLEL_UNITS    {arch.get('num_parallel_units', 4)}",
        f"`define SNN_GLOBAL_ID_WIDTH       {global_id_width}",
        f"`define SNN_GROUP_ID_WIDTH        {(num_groups.bit_length() - 1)}",
        f"`define SNN_LOCAL_ID_WIDTH        {(max_neurons.bit_length() - 1)}",
        "",
        "// --- Data Widths ---",
        f"`define SNN_DATA_WIDTH            {widths['data_width']}",
        f"`define SNN_WEIGHT_WIDTH          {widths['weight_width']}",
        f"`define SNN_THRESHOLD_WIDTH       {widths['threshold_width']}",
        f"`define SNN_LEAK_WIDTH            {widths['leak_width']}",
        f"`define SNN_REFRAC_WIDTH          {widths['refrac_width']}",
        f"`define SNN_WEIGHT_FLAG_WIDTH     {widths.get('weight_with_flag_width', widths['weight_width'] + 1)}",
        "",
        "// --- Router ---",
        f"`define SNN_ROUTER_BUFFER_DEPTH   {arch.get('router_buffer_depth', 512)}",
        f"`define SNN_ROUTER_FIFO_DEPTH     {arch.get('router_fifo_depth', 32)}",
        "",
        "// --- Defense Extensions ---",
    ]

    if defense.get("ew", {}).get("enabled", False):
        ew = defense["ew"]
        lines += [
            "",
            "// --- Electronic Warfare ---",
            f"`define EW_ENABLED",
            f"`define EW_PRI_CYCLES          {ew['pulse_repetition_interval'] // 10}",  # 10ns clock
            f"`define EW_FH_CHANNELS         {ew['frequency_hopping_channels']}",
            f"`define EW_DRFM_DEPTH          {ew['drfm_capture_depth']}",
        ]

    if defense.get("aps", {}).get("enabled", False):
        aps = defense["aps"]
        lines += [
            "",
            "// --- Active Protection System ---",
            f"`define APS_ENABLED",
            f"`define APS_AOA_BINS           {aps['aoa_bins']}",
            f"`define APS_RANGING_BINS       {aps['ranging_bins']}",
            f"`define APS_MAX_TRACKS         {aps['simultaneous_tracks']}",
            f"`define APS_KILL_CYCLES        {aps['hard_kill_actuation_cycles']}",
        ]

    if defense.get("swarm", {}).get("enabled", False):
        swarm = defense["swarm"]
        lines += [
            "",
            "// --- Swarm Coordination ---",
            f"`define SWARM_ENABLED",
            f"`define SWARM_MAX_DRONES       {swarm['max_drones']}",
            f"`define SWARM_HD_DIM           {swarm['hd_vector_dim']}",
            f"`define SWARM_CONSENSUS_CYCLES {swarm['consensus_period_us'] * 100}",  # 10ns clock
        ]

    if defense.get("navigation", {}).get("gps_denied", False):
        nav = defense["navigation"]
        lines += [
            "",
            "// --- GPS-Denied Navigation ---",
            f"`define NAV_GPS_DENIED",
            f"`define NAV_SLAM_CELLS         {nav['slam_cells']}",
            f"`define NAV_ANGLE_BINS         {nav['angle_bins']}",
        ]

    if defense.get("continual_learning", {}).get("enabled", False):
        cl = defense["continual_learning"]
        lines += [
            "",
            "// --- Continual Learning ---",
            f"`define CL_ENABLED",
            f"`define CL_ADAPT_SAMPLES       {cl['adaptation_samples']}",
            f"`define CL_TRACE_DECAY_BITS    {cl.get('trace_decay_bits', 8)}",
        ]

    if defense.get("ecc", {}).get("enabled", False):
        ecc = defense["ecc"]
        lines += [
            "",
            "// --- Error Correction / Fault Tolerance ---",
            f"`define ECC_ENABLED",
            f"`define ECC_PARITY_BITS        {ecc['hamming_parity_bits']}",
            f"`define ECC_WATCHDOG_CYCLES    {ecc['watchdog_timer_cycles']}",
        ]

    lines += [
        "",
        "`endif // SNN_PARAMS_VH",
        "",
    ]
    return "\n".join(lines)


def generate_python(params: dict) -> str:
    arch = params["architecture"]
    widths = params["widths"]
    defense = params.get("defense", {})

    num_groups = len(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))
    total_neurons = sum(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))

    lines = [
        '"""Auto-generated SNN Parameters — DO NOT EDIT MANUALLY."""',
        "",
        "# --- Core Architecture ---",
        f"NUM_GROUPS = {num_groups}",
        f"NEURONS_PER_GROUP = {arch['neurons_per_group']}",
        f"MAX_NEURONS = {max(arch.get('group_sizes', [arch['neurons_per_group']]))}",
        f"TOTAL_NEURONS = {total_neurons}",
        f"MAX_FANOUT_INTER = {arch['max_fanout_inter']}",
        f"SPIKE_BUFFER_DEPTH = {arch['spike_buffer_depth']}",
        f"NUM_PARALLEL_UNITS = {arch.get('num_parallel_units', 4)}",
        "",
        "# --- Data Widths ---",
        f"DATA_WIDTH = {widths['data_width']}",
        f"WEIGHT_WIDTH = {widths['weight_width']}",
        f"THRESHOLD_WIDTH = {widths['threshold_width']}",
        f"LEAK_WIDTH = {widths['leak_width']}",
        f"REFRAC_WIDTH = {widths['refrac_width']}",
        "",
        "# --- FPGA Target ---",
        f'FPGA_PART = "{params["target"]["fpga_part"]}"',
        f'BOARD = "{params["target"]["board"]}"',
        f'CLOCK_PERIOD_NS = {params["target"]["clock_period_ns"]}',
        "",
        "# --- Neuron Group Names ---",
    ]

    for ng in params.get("neuron_groups", []):
        lines.append(f'GROUP_{ng["name"].upper()} = {ng["name"]}')

    # Group name → index mapping
    lines.append("")
    lines.append("# --- Defense Extensions ---")
    if defense.get("ew", {}).get("enabled", False):
        ew = defense["ew"]
        lines += [
            "EW_ENABLED = True",
            f"EW_PRI_CYCLES = {ew['pulse_repetition_interval'] // 10}",
            f"EW_FH_CHANNELS = {ew['frequency_hopping_channels']}",
            f"EW_DRFM_DEPTH = {ew['drfm_capture_depth']}",
            f"EW_DECEPTION_TYPES = {ew['deception_waveform_types']}",
        ]
    if defense.get("aps", {}).get("enabled", False):
        aps = defense["aps"]
        lines += [
            "APS_ENABLED = True",
            f"APS_INTERCEPT_LATENCY_NS = {aps['intercept_latency_ns']}",
            f"APS_AOA_BINS = {aps['aoa_bins']}",
            f"APS_RANGING_BINS = {aps['ranging_bins']}",
            f"APS_MAX_TRACKS = {aps['simultaneous_tracks']}",
        ]
    if defense.get("swarm", {}).get("enabled", False):
        swarm = defense["swarm"]
        lines += [
            "SWARM_ENABLED = True",
            f"SWARM_MAX_DRONES = {swarm['max_drones']}",
            f"SWARM_HD_DIM = {swarm['hd_vector_dim']}",
        ]

    lines += [
        "",
        "# --- Group Name → Index Mapping ---",
        "GROUP_NAMES = {",
    ]
    for i, ng in enumerate(params.get("neuron_groups", [])):
        lines.append(f'    {i}: "{ng["name"]}",')
    lines += [
        "}",
        "",
        "# --- Connection Map ---",
        "CONNECTIONS = [",
    ]
    for conn in params.get("connections", []):
        lines.append(f"    ({conn['src_group']}, {conn['dst_group']}),")
    lines += [
        "]",
        "",
    ]
    return "\n".join(lines)


def generate_hls(params: dict) -> str:
    arch = params["architecture"]
    widths = params["widths"]
    defense = params.get("defense", {})

    num_groups = len(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))
    total_neurons = sum(arch.get("group_sizes", [arch["neurons_per_group"]] * 16))

    lines = [
        "// ===========================================================================",
        "// Auto-generated SNN Parameters — DO NOT EDIT MANUALLY",
        "// Source: config/snn_params.yaml",
        "// ===========================================================================",
        "#ifndef SNN_PARAMS_H",
        "#define SNN_PARAMS_H",
        "",
        "// --- Core Architecture ---",
        f"#define SNN_NUM_GROUPS            {num_groups}",
        f"#define SNN_NEURONS_PER_GROUP     {arch['neurons_per_group']}",
        f"#define SNN_TOTAL_NEURONS         {total_neurons}",
        f"#define SNN_MAX_FANOUT_INTER      {arch['max_fanout_inter']}",
        f"#define SNN_SPIKE_BUFFER_DEPTH    {arch['spike_buffer_depth']}",
        f"#define SNN_NUM_PARALLEL_UNITS    {arch.get('num_parallel_units', 4)}",
        "",
        "// --- Data Widths ---",
        f"#define SNN_DATA_WIDTH            {widths['data_width']}",
        f"#define SNN_WEIGHT_WIDTH          {widths['weight_width']}",
        f"#define SNN_THRESHOLD_WIDTH       {widths['threshold_width']}",
        f"#define SNN_LEAK_WIDTH            {widths['leak_width']}",
        f"#define SNN_REFRAC_WIDTH          {widths['refrac_width']}",
        "",
        "// --- Defense Extensions ---",
    ]
    if defense.get("ew", {}).get("enabled", False):
        lines.append('#define EW_ENABLED')
    if defense.get("aps", {}).get("enabled", False):
        lines.append('#define APS_ENABLED')
    if defense.get("swarm", {}).get("enabled", False):
        lines.append('#define SWARM_ENABLED')
    lines += [
        "",
        "#endif // SNN_PARAMS_H",
        "",
    ]
    return "\n".join(lines)


def main():
    params = load_params()

    gen_dir = SCRIPT_DIR / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)

    # Verilog
    vh_path = gen_dir / "snn_params.vh"
    vh_path.write_text(generate_verilog(params))
    print(f"Generated: {vh_path}")

    # Python
    py_path = gen_dir / "snn_params.py"
    py_path.write_text(generate_python(params))
    print(f"Generated: {py_path}")

    # HLS C++
    h_path = gen_dir / "snn_params.h"
    h_path.write_text(generate_hls(params))
    print(f"Generated: {h_path}")

    print("\nAll parameters generated successfully.")


if __name__ == "__main__":
    main()
