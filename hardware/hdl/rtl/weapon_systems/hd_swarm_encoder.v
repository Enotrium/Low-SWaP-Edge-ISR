//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Hyperdimensional Swarm Vector Encoder
// Encodes SNN spike outputs into binary HD vectors for multi-drone swarm
// coordination. Maps neural firing patterns to compressed state vectors
// that can be transmitted over LPI (Low Probability of Intercept) links.
//
// Each drone's SNN state is encoded as an HD vector:
//   state_vector = bind(threat_map, position, velocity, mission_phase)
// Swarm consensus is achieved via bundle (sum) of received drone vectors.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module hd_swarm_encoder #(
    parameter HD_DIM        = `SWARM_HD_DIM,
    parameter MAX_DRONES    = `SWARM_MAX_DRONES,
    parameter DRONE_ID_WIDTH = 4,   // log2(MAX_DRONES)
    parameter SPIKE_BITS    = 128   // Number of spike inputs to encode
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Spike inputs from SNN (one per encoded dimension)
    input  wire [SPIKE_BITS-1:0]    spike_pattern,
    input  wire                     spike_valid,
    input  wire [7:0]               drone_id,            // This drone's ID

    // Position / state inputs (from navigation group)
    input  wire [15:0]              position_x,
    input  wire [15:0]              position_y,
    input  wire [15:0]              velocity_x,
    input  wire [15:0]              velocity_y,
    input  wire [7:0]               mission_state,

    // HD vector output (binary: 1 bit per dimension)
    output reg                      hd_vector_valid,
    output reg [HD_DIM-1:0]         hd_vector,
    output reg [DRONE_ID_WIDTH-1:0] hd_vector_drone_id,

    // Received HD vectors from swarm (bundled consensus)
    input  wire                     rx_vector_valid,
    input  wire [HD_DIM-1:0]        rx_vector,
    input  wire [DRONE_ID_WIDTH-1:0] rx_vector_drone_id,

    // Consensus output (bundled swarm state)
    output reg                      consensus_valid,
    output reg [HD_DIM-1:0]         consensus_vector,

    // Status
    output reg [7:0]                swarm_size
);

    // HD encoding: permute base vectors to encode state dimensions
    // Using LFSR-based permutation for deterministic hardware mapping

    // Base HD vectors (stored in distributed LUT, one per dimension type)
    reg [HD_DIM-1:0] base_threat_vec;
    reg [HD_DIM-1:0] base_pos_vec;
    reg [HD_DIM-1:0] base_vel_vec;
    reg [HD_DIM-1:0] base_mission_vec;

    // Local LFSR for permute operations
    reg [15:0] perm_lfsr;

    // Consensus accumulator (bundle = majority vote)
    reg [3:0] consensus_bits [0:HD_DIM-1];  // 4-bit saturating counter per dim
    reg [DRONE_ID_WIDTH-1:0] drone_count;

    // FSM
    localparam [2:0]
        ST_IDLE      = 3'd0,
        ST_ENCODE    = 3'd1,
        ST_BUNDLE    = 3'd2,
        ST_OUTPUT    = 3'd3;

    reg [2:0] state;
    reg [9:0] encode_idx;
    reg [9:0] bundle_idx;

    integer i;

    always @(posedge clk) begin
        if (!rst_n) begin
            state             <= ST_IDLE;
            hd_vector_valid   <= 1'b0;
            consensus_valid   <= 1'b0;
            hd_vector         <= 0;
            consensus_vector  <= 0;
            encode_idx        <= 0;
            bundle_idx        <= 0;
            drone_count       <= 0;
            swarm_size        <= 0;
            perm_lfsr         <= 16'hBEEF;
        end else begin
            hd_vector_valid <= 1'b0;
            consensus_valid <= 1'b0;

            // LFSR update for permutation
            perm_lfsr <= {perm_lfsr[14:0], perm_lfsr[15] ^ perm_lfsr[13] ^ perm_lfsr[12] ^ perm_lfsr[10]};

            case (state)
                ST_IDLE: begin
                    encode_idx <= 0;

                    if (spike_valid) begin
                        // Generate base vectors from spike pattern
                        state <= ST_ENCODE;

                        // Base vector generation: map spike pattern to HD space
                        // Each spike dimension maps to a permuted position in the HD vector
                        for (i = 0; i < HD_DIM; i = i + 1) begin
                            // Simple projection: XOR with LFSR-permuted pattern
                            base_threat_vec[i]   <= spike_pattern[i % SPIKE_BITS] ^ perm_lfsr[0];
                            base_pos_vec[i]      <= position_x[i % 16] ^ perm_lfsr[1];
                            base_vel_vec[i]      <= velocity_x[i % 16] ^ perm_lfsr[2];
                            base_mission_vec[i]  <= mission_state[i % 8] ^ perm_lfsr[3];
                        end
                    end

                    // Process received swarn vectors (bundle accumulation)
                    if (rx_vector_valid) begin
                        drone_count <= drone_count + 1;
                        for (i = 0; i < HD_DIM; i = i + 1) begin
                            if (rx_vector[i])
                                consensus_bits[i] <= consensus_bits[i] + 1;
                        end
                    end
                end

                ST_ENCODE: begin
                    // HD vector = bind(threat, pos, vel, mission)
                    // XOR-based binding (invertible)
                    if (encode_idx < HD_DIM) begin
                        hd_vector[encode_idx] <= base_threat_vec[encode_idx] ^
                                                  base_pos_vec[encode_idx]    ^
                                                  base_vel_vec[encode_idx]    ^
                                                  base_mission_vec[encode_idx];
                        encode_idx <= encode_idx + 1;
                    end else begin
                        hd_vector_valid  <= 1'b1;
                        hd_vector_drone_id <= drone_id[DRONE_ID_WIDTH-1:0];
                        state <= ST_BUNDLE;
                    end
                end

                ST_BUNDLE: begin
                    // Generate consensus from accumulated votes
                    if (drone_count > 0 && bundle_idx < HD_DIM) begin
                        // Majority vote: threshold = drone_count / 2
                        consensus_vector[bundle_idx] <=
                            (consensus_bits[bundle_idx] > {1'b0, drone_count[DRONE_ID_WIDTH-1:1]});
                        bundle_idx <= bundle_idx + 1;
                    end else if (bundle_idx >= HD_DIM) begin
                        consensus_valid <= 1'b1;
                        swarm_size <= drone_count;
                        bundle_idx <= 0;
                        drone_count <= 0;
                        // Clear consensus counters
                        for (i = 0; i < HD_DIM; i = i + 1)
                            consensus_bits[i] <= 0;
                        state <= ST_OUTPUT;
                    end else begin
                        state <= ST_OUTPUT;
                    end
                end

                ST_OUTPUT: begin
                    state <= ST_IDLE;
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
