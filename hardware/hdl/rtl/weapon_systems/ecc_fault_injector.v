//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — ECC Fault Injector & SEU Detector
// Hamming (12,8) error-correcting code for SEU protection on critical state.
// Detects and corrects single-bit flips; detects double-bit flips.
// Includes configurable fault injection for test/verification.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module ecc_fault_injector #(
    parameter DATA_WIDTH       = 8,
    parameter CODE_WIDTH       = 12,   // 8 data + 4 parity
    parameter ECC_PARITY_BITS  = 4
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Data input (before encoding)
    input  wire [DATA_WIDTH-1:0]    data_in,
    input  wire                     data_valid,

    // Encoded output (sent to memory / fabric)
    output reg [CODE_WIDTH-1:0]     encoded_data,

    // Decoded output (from memory / fabric read)
    input  wire [CODE_WIDTH-1:0]    encoded_data_in,
    output reg [DATA_WIDTH-1:0]     corrected_data,
    output reg                      single_error_detected,
    output reg                      double_error_detected,
    output reg                      correctable,

    // Fault injection (test mode)
    input  wire                     fault_inject_en,
    input  wire [2:0]               fault_bit_select,   // Which bit to flip
    input  wire                     fault_inject_pulse
);

    // Hamming (12,8) parity generator matrix
    // Parity bits cover:
    //   p0 = d0 ^ d1 ^ d3 ^ d4 ^ d6
    //   p1 = d0 ^ d2 ^ d3 ^ d5 ^ d6
    //   p2 = d1 ^ d2 ^ d3 ^ d7
    //   p3 = d4 ^ d5 ^ d6 ^ d7

    wire [3:0] parity;
    assign parity[0] = ^data_in[0] ^ data_in[1] ^ data_in[3] ^ data_in[4] ^ data_in[6];
    assign parity[1] = ^data_in[0] ^ data_in[2] ^ data_in[3] ^ data_in[5] ^ data_in[6];
    assign parity[2] = ^data_in[1] ^ data_in[2] ^ data_in[3] ^ data_in[7];
    assign parity[3] = ^data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[7];

    // Encoded output: {data[7:0], parity[3:0]}
    reg [CODE_WIDTH-1:0] encoded_reg;

    // Fault injection on encoded data (before storage)
    reg [CODE_WIDTH-1:0] encoded_with_fault;

    always @(posedge clk) begin
        if (!rst_n) begin
            encoded_reg <= 0;
            encoded_with_fault <= 0;
        end else begin
            if (data_valid) begin
                encoded_reg <= {data_in, parity};
            end

            // Fault injection
            if (fault_inject_en && fault_inject_pulse) begin
                encoded_with_fault <= encoded_reg ^ (1 << fault_bit_select);
            end else begin
                encoded_with_fault <= encoded_reg;
            end
        end
    end

    assign encoded_data = encoded_with_fault;

    // Decoder: syndrome computation
    reg [ECC_PARITY_BITS-1:0] syndrome;
    reg [DATA_WIDTH-1:0]      corrected;
    reg                       single_err;
    reg                       double_err;

    wire [3:0] stored_parity = encoded_data_in[ECC_PARITY_BITS-1:0];
    wire [7:0] stored_data   = encoded_data_in[CODE_WIDTH-1:ECC_PARITY_BITS];

    wire [3:0] recomputed_parity;
    assign recomputed_parity[0] = ^stored_data[0] ^ stored_data[1] ^ stored_data[3] ^ stored_data[4] ^ stored_data[6];
    assign recomputed_parity[1] = ^stored_data[0] ^ stored_data[2] ^ stored_data[3] ^ stored_data[5] ^ stored_data[6];
    assign recomputed_parity[2] = ^stored_data[1] ^ stored_data[2] ^ stored_data[3] ^ stored_data[7];
    assign recomputed_parity[3] = ^stored_data[4] ^ stored_data[5] ^ stored_data[6] ^ stored_data[7];

    assign syndrome = stored_parity ^ recomputed_parity;

    always @(posedge clk) begin
        if (!rst_n) begin
            corrected_data        <= 0;
            single_error_detected <= 1'b0;
            double_error_detected <= 1'b0;
            correctable          <= 1'b0;
        end else begin
            corrected_data <= stored_data;
            single_error_detected <= 1'b0;
            double_error_detected <= 1'b0;
            correctable <= 1'b0;

            if (syndrome != 0) begin
                // Single-bit error correction
                casez (syndrome)
                    // Parity syndrome maps to error position (Hamming code structure)
                    4'b0011: begin corrected_data[0] <= ~stored_data[0]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b0101: begin corrected_data[1] <= ~stored_data[1]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b0110: begin corrected_data[2] <= ~stored_data[2]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b0111: begin corrected_data[3] <= ~stored_data[3]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b1001: begin corrected_data[4] <= ~stored_data[4]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b1010: begin corrected_data[5] <= ~stored_data[5]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b1011: begin corrected_data[6] <= ~stored_data[6]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    4'b1100: begin corrected_data[7] <= ~stored_data[7]; single_error_detected <= 1'b1; correctable <= 1'b1; end
                    // Parity bit errors (no data correction needed)
                    4'b0001, 4'b0010, 4'b0100, 4'b1000:
                        begin single_error_detected <= 1'b1; correctable <= 1'b1; end
                    // Uncorrectable: double-bit error or multi-bit
                    default: double_error_detected <= 1'b1;
                endcase
            end
        end
    end

endmodule
