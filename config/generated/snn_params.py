"""Auto-generated SNN Parameters — DO NOT EDIT MANUALLY."""

# --- Core Architecture ---
NUM_GROUPS = 16
NEURONS_PER_GROUP = 128
MAX_NEURONS = 128
TOTAL_NEURONS = 2048
MAX_FANOUT_INTER = 32
SPIKE_BUFFER_DEPTH = 128
NUM_PARALLEL_UNITS = 8

# --- Data Widths ---
DATA_WIDTH = 16
WEIGHT_WIDTH = 8
THRESHOLD_WIDTH = 16
LEAK_WIDTH = 8
REFRAC_WIDTH = 8

# --- FPGA Target ---
FPGA_PART = "xc7z020clg400-1"
BOARD = "tul.com.tw:pynq-z2:part0:1.0"
CLOCK_PERIOD_NS = 10

# --- Defense Extensions ---
EW_ENABLED = True
EW_PRI_CYCLES = 100
EW_FH_CHANNELS = 128
EW_DRFM_DEPTH = 4096
EW_DECEPTION_TYPES = ['range_gate_pull_off', 'velocity_gate_pull_off',
                      'inverse_amplitude_modulation', 'cross_eye_jamming',
                      'saturation_noise']
APS_ENABLED = True
APS_INTERCEPT_LATENCY_NS = 500
APS_AOA_BINS = 64
APS_RANGING_BINS = 256
APS_MAX_TRACKS = 32
SWARM_ENABLED = True
SWARM_MAX_DRONES = 16
SWARM_HD_DIM = 512

# --- Group Name → Index Mapping ---
GROUP_NAMES = {
    0: "sensor_radar",
    1: "sensor_acoustic",
    2: "sensor_rf",
    3: "sensor_fusion",
    4: "threat_class_0",
    5: "threat_class_1",
    6: "countermeasure",
    7: "navigation",
    8: "path_planning",
    9: "swarm_coord",
    10: "ew_cm_generation",
    11: "active_protection",
    12: "knowledge_graph",
    13: "reserve_1",
    14: "reserve_2",
    15: "actuator_output",
}

# --- Connection Map ---
CONNECTIONS = [
    (0, 3), (1, 3), (2, 3),
    (3, 4), (3, 5),
    (4, 6), (5, 6),
    (4, 7), (5, 7),
    (7, 8),
    (6, 10), (6, 11),
    (9, 8), (9, 6),
    (12, 8),
    (8, 15), (10, 15), (11, 15),
    (6, 3), (11, 4),
    (9, 9),
]
