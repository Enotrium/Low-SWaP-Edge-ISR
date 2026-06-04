// ===========================================================================
// Auto-generated SNN Parameters — DO NOT EDIT MANUALLY
// Source: config/snn_params.yaml
// Generator: config/generate_params.py
// ===========================================================================

`ifndef SNN_PARAMS_VH
`define SNN_PARAMS_VH

// --- Core Architecture ---
`define SNN_NUM_GROUPS            16
`define SNN_NEURONS_PER_GROUP     128
`define SNN_MAX_NEURONS           128
`define SNN_TOTAL_NEURONS         2048
`define SNN_MAX_FANOUT_INTER      32
`define SNN_SPIKE_BUFFER_DEPTH    128
`define SNN_NUM_PARALLEL_UNITS    8
`define SNN_GLOBAL_ID_WIDTH       11
`define SNN_GROUP_ID_WIDTH        4
`define SNN_LOCAL_ID_WIDTH        7

// --- Data Widths ---
`define SNN_DATA_WIDTH            16
`define SNN_WEIGHT_WIDTH          8
`define SNN_THRESHOLD_WIDTH       16
`define SNN_LEAK_WIDTH            8
`define SNN_REFRAC_WIDTH          8
`define SNN_WEIGHT_FLAG_WIDTH     9

// --- Router ---
`define SNN_ROUTER_BUFFER_DEPTH   512
`define SNN_ROUTER_FIFO_DEPTH     32

// --- Defense Extensions ---

// --- Electronic Warfare ---
`define EW_ENABLED
`define EW_PRI_CYCLES          100
`define EW_FH_CHANNELS         128
`define EW_DRFM_DEPTH          4096

// --- Active Protection System ---
`define APS_ENABLED
`define APS_AOA_BINS           64
`define APS_RANGING_BINS       256
`define APS_MAX_TRACKS         32
`define APS_KILL_CYCLES        100

// --- Swarm Coordination ---
`define SWARM_ENABLED
`define SWARM_MAX_DRONES       16
`define SWARM_HD_DIM           512
`define SWARM_CONSENSUS_CYCLES 100000

// --- GPS-Denied Navigation ---
`define NAV_GPS_DENIED
`define NAV_SLAM_CELLS         1024
`define NAV_ANGLE_BINS         360

// --- Continual Learning ---
`define CL_ENABLED
`define CL_ADAPT_SAMPLES       50
`define CL_TRACE_DECAY_BITS    8

// --- Error Correction / Fault Tolerance ---
`define ECC_ENABLED
`define ECC_PARITY_BITS        4
`define ECC_WATCHDOG_CYCLES    100000

`endif // SNN_PARAMS_VH
