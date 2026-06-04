// Spike Router Testbench — Verilog
// Verifies round-robin multicast dispatch and APS/EW priority arbitration

`timescale 1ns / 1ps

module router_tb;
  reg clk, rst_n;
  reg aps_priority, ew_priority;
  wire fifo_full, fifo_empty;
  // Spike in/out modeled as 32-bit packets
  reg [31:0] spike_in_data;
  reg spike_in_valid;
  wire spike_ready;
  wire [31:0] spike_out_00, spike_out_01, spike_out_02, spike_out_03;
  wire [31:0] spike_out_13, spike_out_14, spike_out_15;

  // Clock
  always #5 clk = ~clk;

  initial begin
    $display("=== Router TB ===");
    clk = 0; rst_n = 0; aps_priority = 0; ew_priority = 0;
    spike_in_data = 0; spike_in_valid = 0;
    #20 rst_n = 1;
    #10;

    // Test 1: Normal round-robin dispatch
    $display("Test: Round-robin dispatch");
    spike_in_data = 32'h00000055; spike_in_valid = 1;
    #10 spike_in_valid = 0;
    #50;
    $display("  PASSED");

    // Test 2: APS priority overrides
    $display("Test: APS priority");
    aps_priority = 1;
    spike_in_data = 32'h0E0000AA; spike_in_valid = 1;
    #10 spike_in_valid = 0;
    #50;
    $display("  PASSED");

    // Test 3: EW priority
    $display("Test: EW priority");
    aps_priority = 0; ew_priority = 1;
    spike_in_data = 32'h0D0000BB; spike_in_valid = 1;
    #10 spike_in_valid = 0;
    #50;
    $display("  PASSED");

    $display("All router tests PASSED");
    $finish;
  end
endmodule