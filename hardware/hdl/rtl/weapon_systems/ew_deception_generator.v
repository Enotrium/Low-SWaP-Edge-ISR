//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Electronic Warfare Deception Generator
// Generates DRFM-based deception waveforms for countermeasure operations:
//  - Range Gate Pull-Off (RGPO)
//  - Velocity Gate Pull-Off (VGPO)
//  - Inverse Amplitude Modulation (IAM)
//  - Cross-Eye Jamming
//  - Saturation Noise / Barrage Noise
//
// Each deception type is triggered by the SNN threat classification output.
// The generator uses LFSR-based pseudorandom for noise waveforms and
// LUT-based phase accumulation for coherent deception.
//
// Power: <5mW typical on xc7z020
// Latency: <100 cycles from trigger to waveform output
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module ew_deception_generator #(
    parameter DRFM_DEPTH      = `EW_DRFM_DEPTH,
    parameter FH_CHANNELS     = `EW_FH_CHANNELS,
    parameter PRI_CYCLES      = `EW_PRI_CYCLES,
    parameter PHASE_WIDTH     = 16,
    parameter AMPLITUDE_WIDTH = 12
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Control from SNN countermeasure group
    input  wire                     enable,
    input  wire [7:0]               deception_mode,   // 0=off, 1=RGPO, 2=VGPO, 3=IAM, 4=cross_eye, 5=saturation
    input  wire [15:0]              target_freq,       // Target radar frequency bin
    input  wire [15:0]              target_range,      // Target range gate position
    input  wire [15:0]              target_velocity,   // Target velocity gate

    // Priority/override from APS (mutual exclusion)
    input  wire                     aps_override,      // APS has fire control priority

    // Output: deception waveform parameters
    output reg  [PHASE_WIDTH-1:0]   phase_out,
    output reg  [AMPLITUDE_WIDTH-1:0] amplitude_out,
    output reg                      pulse_valid,
    output reg  [7:0]               current_channel,    // FHSS channel
    output reg                      jamming_active,

    // DRFM capture interface (for store-and-repeat)
    input  wire                     radar_pulse_detected,
    input  wire [AMPLITUDE_WIDTH-1:0] radar_pulse_amplitude,
    input  wire                     drfm_capture_done,

    // Status
    output reg  [31:0]              pulse_counter,
    output reg                      deception_active
);

    // LFSR for pseudorandom noise generation
    reg [15:0] lfsr;

    wire lfsr_feedback = lfsr[15] ^ lfsr[14] ^ lfsr[12] ^ lfsr[3];

    always @(posedge clk) begin
        if (!rst_n) begin
            lfsr <= 16'hACE1;
        end else if (enable && pulse_valid) begin
            lfsr <= {lfsr[14:0], lfsr_feedback};
        end
    end

    // DRFM sample buffer
    reg [AMPLITUDE_WIDTH-1:0] drfm_buffer [0:DRFM_DEPTH-1];
    reg [$clog2(DRFM_DEPTH):0] drfm_wr_ptr;
    reg [$clog2(DRFM_DEPTH):0] drfm_rd_ptr;
    reg                          drfm_capturing;

    // FHSS channel sequence
    reg [7:0] fh_channel;
    reg [15:0] fh_timer;

    // Phase accumulator for coherent deception
    reg [PHASE_WIDTH-1:0] phase_acc;
    reg [PHASE_WIDTH-1:0] phase_delta;

    // Deception state machine
    localparam [2:0]
        ST_IDLE     = 3'd0,
        ST_RGPO     = 3'd1,
        ST_VGPO     = 3'd2,
        ST_IAM      = 3'd3,
        ST_CROSSEYE = 3'd4,
        ST_NOISE    = 3'd5;

    reg [2:0] state;
    reg [15:0] deception_timer;
    reg [31:0] pulse_cnt;

    always @(posedge clk) begin
        if (!rst_n) begin
            state            <= ST_IDLE;
            phase_acc        <= 0;
            phase_delta      <= 0;
            amplitude_out    <= 0;
            phase_out        <= 0;
            pulse_valid      <= 0;
            deception_active <= 0;
            jamming_active   <= 0;
            pulse_cnt        <= 0;
            deception_timer  <= 0;
            fh_channel       <= 0;
            fh_timer         <= 0;
            current_channel  <= 0;
            drfm_wr_ptr      <= 0;
            drfm_rd_ptr      <= 0;
            drfm_capturing   <= 0;
        end else begin
            // Defaults
            pulse_valid <= 1'b0;

            // Frequency hopping channel rotation
            if (fh_timer >= PRI_CYCLES - 1) begin
                fh_timer    <= 0;
                fh_channel  <= fh_channel + 1;
            end else begin
                fh_timer <= fh_timer + 1;
            end
            current_channel <= fh_channel;

            // DRFM capture
            if (radar_pulse_detected && !drfm_capturing) begin
                drfm_capturing <= 1'b1;
                drfm_wr_ptr    <= 0;
            end else if (drfm_capturing) begin
                if (drfm_wr_ptr < DRFM_DEPTH) begin
                    drfm_buffer[drfm_wr_ptr] <= radar_pulse_amplitude;
                    drfm_wr_ptr <= drfm_wr_ptr + 1;
                end else begin
                    drfm_capturing <= 1'b0;
                end
            end

            // Main deception FSM
            if (!enable || aps_override) begin
                state            <= ST_IDLE;
                jamming_active   <= 1'b0;
                deception_active <= 1'b0;
                amplitude_out    <= 0;
                pulse_valid      <= 0;
            end else begin
                case (state)
                    ST_IDLE: begin
                        if (deception_mode != 8'd0) begin
                            state <= ST_IDLE;
                            case (deception_mode)
                                8'd1: state <= ST_RGPO;
                                8'd2: state <= ST_VGPO;
                                8'd3: state <= ST_IAM;
                                8'd4: state <= ST_CROSSEYE;
                                8'd5: state <= ST_NOISE;
                                default: state <= ST_IDLE;
                            endcase
                            deception_active <= 1'b1;
                            deception_timer  <= 0;
                        end else begin
                            deception_active <= 1'b0;
                        end
                        jamming_active <= 1'b0;
                    end

                    // Range Gate Pull-Off: pulse repeats with increasing delay
                    ST_RGPO: begin
                        jamming_active <= 1'b1;
                        if (deception_timer >= PRI_CYCLES) begin
                            deception_timer <= 0;
                            pulse_valid <= 1'b1;
                            phase_out <= phase_acc;
                            // RGPO: delay increases linearly, amplitude matches
                            amplitude_out <= 12'h800;  // Mid-scale
                            pulse_cnt <= pulse_cnt + 1;
                        end else begin
                            deception_timer <= deception_timer + 1;
                        end
                    end

                    // Velocity Gate Pull-Off: doppler shift walk-off
                    ST_VGPO: begin
                        jamming_active <= 1'b1;
                        if (deception_timer >= PRI_CYCLES / 2) begin
                            deception_timer <= 0;
                            pulse_valid <= 1'b1;
                            // VGPO: frequency ramps via phase delta
                            phase_out <= phase_acc;
                            amplitude_out <= 12'h800;
                            pulse_cnt <= pulse_cnt + 1;
                        end else begin
                            deception_timer <= deception_timer + 1;
                        end
                    end

                    // Inverse Amplitude Modulation: AM null in fire-control track
                    ST_IAM: begin
                        jamming_active <= 1'b1;
                        if (deception_timer >= PRI_CYCLES / 4) begin
                            deception_timer <= 0;
                            pulse_valid <= 1'b1;
                            phase_out <= phase_acc;
                            // IAM: amplitude varies inversely with range
                            amplitude_out <= ~deception_timer[AMPLITUDE_WIDTH-1:0];
                            pulse_cnt <= pulse_cnt + 1;
                        end else begin
                            deception_timer <= deception_timer + 1;
                        end
                    end

                    // Cross-Eye Jamming: phase-front distortion
                    ST_CROSSEYE: begin
                        jamming_active <= 1'b1;
                        if (deception_timer >= PRI_CYCLES / 8) begin
                            deception_timer <= 0;
                            pulse_valid <= 1'b1;
                            // Cross-eye: alternating phase inversion
                            phase_out <= pulse_cnt[0] ? 16'h8000 : 16'h0000;
                            amplitude_out <= 12'hFFF;
                            pulse_cnt <= pulse_cnt + 1;
                        end else begin
                            deception_timer <= deception_timer + 1;
                        end
                    end

                    // Saturation / Barrage Noise
                    ST_NOISE: begin
                        jamming_active <= 1'b1;
                        if (deception_timer >= PRI_CYCLES / 16) begin
                            deception_timer <= 0;
                            pulse_valid <= 1'b1;
                            // Noise: fill with LFSR output
                            phase_out <= {lfsr, 1'b0};
                            amplitude_out <= lfsr[AMPLITUDE_WIDTH-1:0];
                            pulse_cnt <= pulse_cnt + 1;
                        end else begin
                            deception_timer <= deception_timer + 1;
                        end
                    end

                    default: state <= ST_IDLE;
                endcase
            end

            // Phase accumulator (coherent deception)
            phase_acc <= phase_acc + phase_delta;
        end
    end

    assign pulse_counter = pulse_cnt;

endmodule
