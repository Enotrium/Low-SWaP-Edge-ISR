//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — LIF Neuron Core with STDP Learning
// Leaky Integrate-and-Fire with event-driven update and on-chip STDP.
// Extended for defense: configurable thresholds per mission phase, ECC
// protection on membrane state.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module lif_neuron #(
    parameter DATA_WIDTH     = `SNN_DATA_WIDTH,
    parameter WEIGHT_WIDTH   = `SNN_WEIGHT_WIDTH,
    parameter THRESHOLD_WIDTH = `SNN_THRESHOLD_WIDTH,
    parameter REFRAC_WIDTH   = `SNN_REFRAC_WIDTH,
    parameter LEAK_WIDTH     = `SNN_LEAK_WIDTH,
    parameter LOCAL_ID       = 0,
    parameter GROUP_ID       = 0
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Synaptic input (AER event)
    input  wire                     spike_in_valid,
    input  wire [DATA_WIDTH-1:0]    spike_in_weight,
    input  wire                     spike_in_excitatory,

    // Configuration
    input  wire [THRESHOLD_WIDTH-1:0] threshold,
    input  wire [LEAK_WIDTH-1:0]      leak_rate,       // Shift-based: tau ≈ 1/(2^leak_rate)
    input  wire [REFRAC_WIDTH-1:0]    refrac_period,
    input  wire                       learning_enable,

    // Output spike
    output reg                      spike_out,
    output reg [7:0]                spike_out_group_id,
    output reg [7:0]                spike_out_local_id,

    // STDP learning ports
    input  wire                     pre_trace_valid,   // Pre-synaptic spike timing
    input  wire [15:0]              pre_trace_value,
    output wire [15:0]              post_trace_value,  // Post-synaptic spike timing
    output reg                      post_trace_valid,

    // Weight update interface (STDP)
    output reg                      weight_update_en,
    output reg [WEIGHT_WIDTH-1:0]   weight_update_delta,
    output reg                      weight_update_potentiation, // 1=pot, 0=depress

    // State monitoring
    output reg [DATA_WIDTH-1:0]     membrane_potential,
    output reg                      in_refrac,
    output reg                      neuron_active
);

    // Membrane potential with ECC protection
    reg  [DATA_WIDTH-1:0] mem_pot;
    reg  [DATA_WIDTH-1:0] mem_pot_shadow;  // Parity shadow for SEU detection

    // State
    reg [REFRAC_WIDTH-1:0] refrac_timer;
    reg                    refrac_flag;
    reg [15:0]             post_trace;

    // STDP time constants (shift-based for hardware efficiency)
    localparam STDP_TAU_PRE  = 5;   // ~20ms pre-synaptic trace decay (shift)
    localparam STDP_TAU_POST = 6;   // ~40ms post-synaptic trace decay (shift)

    // ECC detection
    wire ecc_mismatch = (mem_pot != mem_pot_shadow);

    always @(posedge clk) begin
        if (!rst_n) begin
            mem_pot       <= {DATA_WIDTH{1'b0}};
            mem_pot_shadow <= {DATA_WIDTH{1'b0}};
            refrac_timer  <= 0;
            refrac_flag   <= 1'b0;
            spike_out     <= 1'b0;
            post_trace    <= 0;
            post_trace_valid <= 1'b0;
            weight_update_en <= 1'b0;
            neuron_active <= 1'b0;
        end else begin
            // Defaults
            spike_out <= 1'b0;
            post_trace_valid <= 1'b0;
            weight_update_en <= 1'b0;
            neuron_active <= 1'b1;

            // ECC: recover from single-bit error
            if (ecc_mismatch) begin
                mem_pot <= mem_pot_shadow;
            end

            // Leak: shift-based exponential decay (applied every timestep)
            // V(t) = V(t-1) - V(t-1) >> leak_rate
            if (!refrac_flag) begin
                mem_pot <= mem_pot - (mem_pot >> leak_rate);
            end

            // Refractory period counter
            if (refrac_flag) begin
                if (refrac_timer >= refrac_period) begin
                    refrac_flag <= 1'b0;
                    refrac_timer <= 0;
                end else begin
                    refrac_timer <= refrac_timer + 1;
                end
            end

            // Synaptic integration (event-driven: only when spike arrives)
            if (spike_in_valid && !refrac_flag) begin
                if (spike_in_excitatory) begin
                    if (mem_pot + spike_in_weight < mem_pot)
                        mem_pot <= {DATA_WIDTH{1'b1}};  // Saturation clamp
                    else
                        mem_pot <= mem_pot + spike_in_weight;
                end else begin
                    if (spike_in_weight > mem_pot)
                        mem_pot <= 0;  // Underflow clamp
                    else
                        mem_pot <= mem_pot - spike_in_weight;
                end
            end

            // Spike generation
            if (!refrac_flag && mem_pot >= threshold) begin
                spike_out <= 1'b1;
                mem_pot   <= 0;  // Reset
                refrac_flag <= 1'b1;
                refrac_timer <= 0;

                // Post-synaptic trace for STDP
                post_trace <= {DATA_WIDTH{1'b1}};  // Spike-time marker
                post_trace_valid <= 1'b1;

                // STDP weight update
                if (learning_enable && pre_trace_valid) begin
                    weight_update_en <= 1'b1;
                    weight_update_potentiation <= 1'b1;
                    // Potentiation: Δw ∝ pre_trace
                    weight_update_delta <= pre_trace_value[WEIGHT_WIDTH-1:0] >> STDP_TAU_PRE;
                end
            end

            // Post-trace decay (if not just spiked)
            if (post_trace > 0 && !(spike_in_valid && mem_pot >= threshold)) begin
                post_trace <= post_trace - (post_trace >> STDP_TAU_POST);
            end

            // Shadow register for ECC
            mem_pot_shadow <= mem_pot;
        end
    end

    assign membrane_potential = mem_pot;
    assign in_refrac = refrac_flag;
    assign post_trace_value = post_trace;

    // Output spike address
    always @(*) begin
        spike_out_group_id = GROUP_ID[7:0];
        spike_out_local_id = LOCAL_ID[7:0];
    end

endmodule
