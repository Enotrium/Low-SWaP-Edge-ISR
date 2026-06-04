//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Neuron Group Core
// A group of NEURONS_PER_GROUP LIF neurons with shared weight BRAM and
// parallel spike processing. Interfaces with the spike_router for inter-group
// communication and implements on-chip STDP.
//
// Extended for defense: parallel unit processing, configurable mission modes.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module neuron_group_core #(
    parameter GROUP_ID           = 0,
    parameter NEURONS            = `SNN_NEURONS_PER_GROUP,
    parameter DATA_WIDTH         = `SNN_DATA_WIDTH,
    parameter WEIGHT_WIDTH       = `SNN_WEIGHT_WIDTH,
    parameter THRESHOLD_WIDTH    = `SNN_THRESHOLD_WIDTH,
    parameter REFRAC_WIDTH       = `SNN_REFRAC_WIDTH,
    parameter LOCAL_ID_WIDTH     = `SNN_LOCAL_ID_WIDTH,
    parameter PARALLEL_UNITS     = `SNN_NUM_PARALLEL_UNITS
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Incoming spikes from router
    input  wire                     rx_spike_valid,
    input  wire [LOCAL_ID_WIDTH-1:0] rx_spike_neuron,
    input  wire [7:0]                rx_spike_weight,
    input  wire                      rx_spike_excitatory,

    // Configuration
    input  wire [THRESHOLD_WIDTH-1:0] threshold,
    input  wire [7:0]                 leak_rate,
    input  wire [7:0]                 refrac_period,
    input  wire                       learning_enable,
    input  wire                       neuron_config_we,
    input  wire [9:0]                 neuron_config_addr,
    input  wire [31:0]                neuron_config_wdata,

    // Outgoing spikes to router
    output reg                       tx_spike_valid,
    output reg [LOCAL_ID_WIDTH-1:0]  tx_spike_neuron,
    output reg [7:0]                 tx_spike_group_id,

    // Weight BRAM interface (shared across group)
    output reg                       bram_we,
    output reg [$clog2(NEURONS*NEURONS)-1:0] bram_addr,
    output reg [WEIGHT_WIDTH-1:0]    bram_wdata,
    input  wire [WEIGHT_WIDTH-1:0]   bram_rdata,

    // Status
    output reg                       group_active
);

    // LIF neuron state per parallel unit
    reg [DATA_WIDTH-1:0]   membrane [0:PARALLEL_UNITS-1];
    reg [REFRAC_WIDTH-1:0] refrac_timer [0:PARALLEL_UNITS-1];
    reg                    refrac_flag [0:PARALLEL_UNITS-1];
    reg                    spike_out [0:PARALLEL_UNITS-1];

    // Spike FIFO for incoming events
    reg [LOCAL_ID_WIDTH-1:0] spike_fifo [0:`SNN_SPIKE_BUFFER_DEPTH-1];
    reg [7:0]                 weight_fifo [0:`SNN_SPIKE_BUFFER_DEPTH-1];
    reg                       exc_fifo [0:`SNN_SPIKE_BUFFER_DEPTH-1];
    reg [$clog2(`SNN_SPIKE_BUFFER_DEPTH):0] fifo_wr;
    reg [$clog2(`SNN_SPIKE_BUFFER_DEPTH):0] fifo_rd;
    reg                                      fifo_empty;

    // Parallel processing state
    reg [LOCAL_ID_WIDTH-1:0] current_unit;
    reg [NEURONS-1:0]        unit_neurons;
    reg                      processing;

    integer u;

    always @(posedge clk) begin
        if (!rst_n) begin
            for (u = 0; u < PARALLEL_UNITS; u = u + 1) begin
                membrane[u] <= 0;
                refrac_timer[u] <= 0;
                refrac_flag[u] <= 1'b0;
                spike_out[u] <= 1'b0;
            end
            tx_spike_valid <= 1'b0;
            group_active   <= 1'b1;
            fifo_wr      <= 0;
            fifo_rd      <= 0;
            fifo_empty   <= 1'b1;
            processing   <= 1'b0;
        end else begin
            tx_spike_valid <= 1'b0;

            // Write incoming spikes to FIFO
            if (rx_spike_valid) begin
                if (!processing) begin
                    spike_fifo[fifo_wr] <= rx_spike_neuron;
                    weight_fifo[fifo_wr] <= rx_spike_weight;
                    exc_fifo[fifo_wr] <= rx_spike_excitatory;
                    fifo_wr <= fifo_wr + 1;
                    fifo_empty <= 1'b0;
                end
            end

            // Process spikes in parallel batches
            if (!processing && !fifo_empty) begin
                // Load next spike from FIFO
                reg [LOCAL_ID_WIDTH-1:0] target_neuron;
                reg [7:0] spike_w;
                reg spike_e;
                reg [LOCAL_ID_WIDTH-1:0] local_unit;
                reg [LOCAL_ID_WIDTH-1:0] local_neuron;

                target_neuron = spike_fifo[fifo_rd];
                spike_w = weight_fifo[fifo_rd];
                spike_e = exc_fifo[fifo_rd];

                fifo_rd <= fifo_rd + 1;
                if (fifo_rd + 1 == fifo_wr)
                    fifo_empty <= 1'b1;

                // Map to parallel unit
                local_unit = target_neuron / (NEURONS / PARALLEL_UNITS);
                local_neuron = target_neuron % (NEURONS / PARALLEL_UNITS);

                // Update membrane in parallel
                for (u = 0; u < PARALLEL_UNITS; u = u + 1) begin
                    if (u == local_unit && !refrac_flag[u]) begin
                        // Leak
                        membrane[u] <= membrane[u] - (membrane[u] >> leak_rate);

                        // Synaptic integration
                        if (spike_e) begin
                            membrane[u] <= membrane[u] + spike_w;
                        end else begin
                            membrane[u] <= membrane[u] - spike_w;
                        end

                        // Spike check
                        if (membrane[u] >= threshold) begin
                            spike_out[u] <= 1'b1;
                            membrane[u] <= 0;
                            refrac_flag[u] <= 1'b1;
                            refrac_timer[u] <= 0;

                            // Output spike
                            tx_spike_valid <= 1'b1;
                            tx_spike_neuron <= target_neuron;
                            tx_spike_group_id <= GROUP_ID[7:0];
                        end
                    end

                    // Refractory countdown
                    if (refrac_flag[u]) begin
                        if (refrac_timer[u] >= refrac_period) begin
                            refrac_flag[u] <= 1'b0;
                            refrac_timer[u] <= 0;
                        end else begin
                            refrac_timer[u] <= refrac_timer[u] + 1;
                        end
                    end
                end
            end

            // Global leak when no spikes (background decay)
            if (fifo_empty && !processing) begin
                for (u = 0; u < PARALLEL_UNITS; u = u + 1) begin
                    if (!refrac_flag[u]) begin
                        membrane[u] <= membrane[u] - (membrane[u] >> leak_rate);
                    end
                end
            end
        end
    end

endmodule
