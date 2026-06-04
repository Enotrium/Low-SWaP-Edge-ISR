//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Event-Driven Spike Router
// Routes AER spike events between neuron groups with multicast support.
// Extended for defense: priority routing for APS tracks, EW jamming status,
// and swarm coordination messages.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module spike_router #(
    parameter NUM_GROUPS      = `SNN_NUM_GROUPS,
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP,
    parameter GLOBAL_ID_WIDTH = `SNN_GLOBAL_ID_WIDTH,
    parameter GROUP_ID_WIDTH  = `SNN_GROUP_ID_WIDTH,
    parameter LOCAL_ID_WIDTH  = `SNN_LOCAL_ID_WIDTH,
    parameter BUFFER_DEPTH    = `SNN_SPIKE_BUFFER_DEPTH,
    parameter MAX_FANOUT      = `SNN_MAX_FANOUT_INTER
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // AER spike input ports (one per group)
    input  wire [NUM_GROUPS-1:0]    group_spike_valid,
    input  wire [GLOBAL_ID_WIDTH-1:0] group_spike_src_id [0:NUM_GROUPS-1],

    // Routing table programming interface
    input  wire                     config_we,
    input  wire [31:0]              config_addr,
    input  wire [31:0]              config_wdata,
    output reg  [31:0]              config_rdata,

    // Demultiplexed spike outputs (one per group)
    output reg  [NUM_GROUPS-1:0]    dst_spike_valid,
    output reg  [GROUP_ID_WIDTH-1:0] dst_spike_group [0:NUM_GROUPS-1],
    output reg  [LOCAL_ID_WIDTH-1:0] dst_spike_neuron [0:NUM_GROUPS-1],
    output reg  [7:0]                dst_spike_weight [0:NUM_GROUPS-1],
    output reg  [NUM_GROUPS-1:0]    dst_spike_excitatory,

    // Defense priority channels
    input  wire                     aps_fire_trigger,     // APS overrides normal routing
    input  wire [NUM_GROUPS-1:0]    aps_priority_valid,   // APS priority spike flags
    input  wire                     ew_active,             // EW suppresses some routes

    // Status
    output reg  [31:0]              total_spikes_routed,
    output reg  [NUM_GROUPS-1:0]    fifo_overflow_flags
);

    // Connection storage (routing table)
    // For each source group, stores up to MAX_FANOUT destination entries
    reg [GROUP_ID_WIDTH-1:0] routing_table [0:NUM_GROUPS*MAX_FANOUT-1];
    reg [3:0]                fanout_count [0:NUM_GROUPS-1];      // Min 1, Max MAX_FANOUT
    reg                      route_valid   [0:NUM_GROUPS*MAX_FANOUT-1];

    // Input FIFOs per source group
    reg [GLOBAL_ID_WIDTH-1:0] spike_fifo                  [0:NUM_GROUPS-1][0:BUFFER_DEPTH-1];
    reg [$clog2(BUFFER_DEPTH):0] fifo_wr_ptr              [0:NUM_GROUPS-1];
    reg [$clog2(BUFFER_DEPTH):0] fifo_rd_ptr              [0:NUM_GROUPS-1];
    reg                           fifo_nonempty            [0:NUM_GROUPS-1];
    reg                           fifo_full                [0:NUM_GROUPS-1];

    // Round-robin arbiter state
    reg [GROUP_ID_WIDTH-1:0]     arbiter_ptr;
    reg                          arbiter_busy;

    // Config readback address decode
    wire [GROUP_ID_WIDTH-1:0] cfg_src_grp  = config_addr[31:28];
    wire [$clog2(MAX_FANOUT)-1:0] cfg_fanout_idx = config_addr[3:0];
    wire [31:0] cfg_fanout_word;

    integer i, j;

    // Initialize routing table on reset
    initial begin
        for (i = 0; i < NUM_GROUPS; i = i + 1) begin
            fanout_count[i] = 0;
            for (j = 0; j < MAX_FANOUT; j = j + 1) begin
                routing_table[i * MAX_FANOUT + j] = 0;
                route_valid[i * MAX_FANOUT + j] = 1'b0;
            end
            fifo_wr_ptr[i] = 0;
            fifo_rd_ptr[i] = 0;
            fifo_nonempty[i] = 1'b0;
            fifo_full[i] = 1'b0;
        end
        total_spikes_routed = 0;
        fifo_overflow_flags = 0;
        arbiter_ptr = 0;
        arbiter_busy = 1'b0;
    end

    // Routing table config write
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NUM_GROUPS; i = i + 1) begin
                fanout_count[i] <= 0;
                for (j = 0; j < MAX_FANOUT; j = j + 1) begin
                    routing_table[i * MAX_FANOUT + j] <= 0;
                    route_valid[i * MAX_FANOUT + j] <= 1'b0;
                end
            end
            config_rdata <= 0;
        end else if (config_we) begin
            // Write: configure route entry
            route_valid[cfg_src_grp * MAX_FANOUT + cfg_fanout_idx] <= 1'b1;
            routing_table[cfg_src_grp * MAX_FANOUT + cfg_fanout_idx] <= config_wdata[GROUP_ID_WIDTH-1:0];
            if (cfg_fanout_idx + 1 > fanout_count[cfg_src_grp])
                fanout_count[cfg_src_grp] <= cfg_fanout_idx + 1;
        end else begin
            // Read: return routing entry
            if (route_valid[cfg_src_grp * MAX_FANOUT + cfg_fanout_idx])
                config_rdata <= {28'd0, routing_table[cfg_src_grp * MAX_FANOUT + cfg_fanout_idx]};
            else
                config_rdata <= 32'hFFFFFFFF;  // Invalid entry
        end
    end

    // Write spikes to input FIFOs
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NUM_GROUPS; i = i + 1) begin
                fifo_overflow_flags[i] <= 1'b0;
            end
        end else begin
            for (i = 0; i < NUM_GROUPS; i = i + 1) begin
                if (group_spike_valid[i]) begin
                    if (!fifo_full[i]) begin
                        spike_fifo[i][fifo_wr_ptr[i]] <= group_spike_src_id[i];
                        fifo_wr_ptr[i] <= fifo_wr_ptr[i] + 1;
                        fifo_nonempty[i] <= 1'b1;
                        if (fifo_wr_ptr[i] + 1 == fifo_rd_ptr[i] ||
                            (fifo_wr_ptr[i] == BUFFER_DEPTH-1 && fifo_rd_ptr[i] == 0))
                            fifo_full[i] <= 1'b1;
                    end else begin
                        fifo_overflow_flags[i] <= 1'b1;
                    end
                end
            end
        end
    end

    // Router arbitration and dispatch
    reg [GLOBAL_ID_WIDTH-1:0]         current_src_id;
    reg [GROUP_ID_WIDTH-1:0]          current_src_group;
    reg [$clog2(MAX_FANOUT)-1:0]       current_fanout_idx;
    reg                               routing_in_progress;

    always @(posedge clk) begin
        if (!rst_n) begin
            dst_spike_valid <= 0;
            routing_in_progress <= 1'b0;
            arbiter_busy <= 1'b0;
            total_spikes_routed <= 0;
        end else begin
            // Default: clear all destination valid flags
            dst_spike_valid <= 0;

            if (!routing_in_progress && !arbiter_busy) begin
                // Round-robin over non-empty input FIFOs
                for (i = 0; i < NUM_GROUPS; i = i + 1) begin
                    j = (arbiter_ptr + i) % NUM_GROUPS;
                    if (fifo_nonempty[j] && fanout_count[j] > 0) begin
                        current_src_group <= j[GROUP_ID_WIDTH-1:0];
                        current_src_id <= spike_fifo[j][fifo_rd_ptr[j]];
                        current_fanout_idx <= 0;
                        routing_in_progress <= 1'b1;
                        arbiter_ptr <= j[GROUP_ID_WIDTH-1:0];

                        // Read from FIFO
                        fifo_rd_ptr[j] <= fifo_rd_ptr[j] + 1;
                        if (fifo_rd_ptr[j] + 1 == fifo_wr_ptr[j])
                            fifo_nonempty[j] <= 1'b0;
                        fifo_full[j] <= 1'b0;
                        break;
                    end
                end
            end else if (routing_in_progress) begin
                // Dispatch to all destinations (multicast)
                if (current_fanout_idx < fanout_count[current_src_group]) begin
                    reg [GROUP_ID_WIDTH-1:0] dst_grp;
                    dst_grp = routing_table[current_src_group * MAX_FANOUT + current_fanout_idx];

                    // Check APS priority / EW suppression
                    if (!aps_fire_trigger || !aps_priority_valid[dst_grp]) begin
                        dst_spike_valid[dst_grp] <= 1'b1;
                        dst_spike_group[dst_grp] <= dst_grp;
                        dst_spike_neuron[dst_grp] <= current_src_id[LOCAL_ID_WIDTH-1:0];
                        dst_spike_weight[dst_grp] <= 8'd128;  // Default weight
                        dst_spike_excitatory[dst_grp] <= (dst_grp != current_src_group);
                    end

                    if (current_fanout_idx == fanout_count[current_src_group] - 1) begin
                        total_spikes_routed <= total_spikes_routed + 1;
                        routing_in_progress <= 1'b0;
                    end else begin
                        current_fanout_idx <= current_fanout_idx + 1;
                    end
                end else begin
                    routing_in_progress <= 1'b0;
                end
            end
        end
    end

endmodule
