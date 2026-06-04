// ===========================================================================
// Auto-generated SNN Parameters — DO NOT EDIT MANUALLY
// Source: config/snn_params.yaml
// ===========================================================================
#ifndef SNN_PARAMS_H
#define SNN_PARAMS_H

// --- Core Architecture ---
#define SNN_NUM_GROUPS            16
#define SNN_NEURONS_PER_GROUP     128
#define SNN_TOTAL_NEURONS         2048
#define SNN_MAX_FANOUT_INTER      32
#define SNN_SPIKE_BUFFER_DEPTH    128
#define SNN_NUM_PARALLEL_UNITS    8

// --- Data Widths ---
#define SNN_DATA_WIDTH            16
#define SNN_WEIGHT_WIDTH          8
#define SNN_THRESHOLD_WIDTH       16
#define SNN_LEAK_WIDTH            8
#define SNN_REFRAC_WIDTH          8

// --- Defense Extensions ---
#define EW_ENABLED
#define APS_ENABLED
#define SWARM_ENABLED

#endif // SNN_PARAMS_H
