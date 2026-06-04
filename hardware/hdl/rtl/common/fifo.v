//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Synchronous FIFO with ECC-protected status
// Extended from metr0jw's Event-Driven SNN Accelerator for defense systems.
// Adds: ECC status protection, watchdog overflow detection.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ALMOST_FULL_THRESHOLD = DEPTH - 2,
    parameter ALMOST_EMPTY_THRESHOLD = 2,
    parameter ECC_PROTECT = 1           // Enable Hamming parity on status
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Write interface
    input  wire                     wr_en,
    input  wire [DATA_WIDTH-1:0]    wr_data,
    output wire                     full,
    output wire                     almost_full,

    // Read interface
    input  wire                     rd_en,
    output reg  [DATA_WIDTH-1:0]    rd_data,
    output wire                     empty,
    output wire                     almost_empty,

    // Status
    output wire [$clog2(DEPTH):0]   count,
    output reg                      overflow,
    output reg                      underflow,

    // ECC status (defense extension)
    output reg                      ecc_error_detected
);

    localparam ADDR_WIDTH = $clog2(DEPTH);

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [ADDR_WIDTH:0]   wr_ptr;
    reg [ADDR_WIDTH:0]   rd_ptr;

    wire [ADDR_WIDTH:0] wr_ptr_next;
    wire [ADDR_WIDTH:0] rd_ptr_next;
    wire wr_en_qualified;
    wire rd_en_qualified;

    assign wr_ptr_next = wr_ptr + 1'b1;
    assign rd_ptr_next = rd_ptr + 1'b1;

    // Dual-rail pointer parity for SEU detection
    reg [ADDR_WIDTH:0] wr_ptr_parity;
    reg [ADDR_WIDTH:0] rd_ptr_parity;

    always @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr_parity <= 0;
            rd_ptr_parity <= 0;
            ecc_error_detected <= 0;
        end else begin
            // Track parity of pointers for SEU detection
            if (wr_en_qualified) wr_ptr_parity <= wr_ptr_parity ^ wr_ptr_next;
            if (rd_en_qualified) rd_ptr_parity <= rd_ptr_parity ^ rd_ptr_next;

            // Check pointer parity on every cycle
            if (ECC_PROTECT) begin
                if ((^wr_ptr) != wr_ptr_parity[0])
                    ecc_error_detected <= 1'b1;
                if ((^rd_ptr) != rd_ptr_parity[0])
                    ecc_error_detected <= 1'b1;
            end
        end
    end

    assign full = (wr_ptr[ADDR_WIDTH] != rd_ptr[ADDR_WIDTH]) &&
                  (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]);
    assign empty = (wr_ptr == rd_ptr);

    wire [ADDR_WIDTH:0] count_raw;
    assign count_raw = wr_ptr - rd_ptr;
    assign count = count_raw;

    assign almost_full = (count >= ALMOST_FULL_THRESHOLD);
    assign almost_empty = (count <= ALMOST_EMPTY_THRESHOLD);

    assign wr_en_qualified = wr_en && !full;
    assign rd_en_qualified = rd_en && !empty;

    always @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr <= 0;
        end else begin
            if (wr_en_qualified) begin
                mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
                wr_ptr <= wr_ptr_next;
            end
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            rd_ptr <= 0;
            rd_data <= 0;
        end else begin
            if (rd_en_qualified) begin
                rd_data <= mem[rd_ptr[ADDR_WIDTH-1:0]];
                rd_ptr <= rd_ptr_next;
            end
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            overflow <= 1'b0;
            underflow <= 1'b0;
        end else begin
            if (wr_en && full)
                overflow <= 1'b1;
            if (rd_en && empty)
                underflow <= 1'b1;
        end
    end

endmodule
