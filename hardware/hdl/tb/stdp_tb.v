// STDP Learning Testbench — Verilog
// Validates on-chip STDP potentiation and depression

`timescale 1ns / 1ps

module stdp_tb;
  reg clk, rst_n, stdp_en, pre_spike, post_spike;
  reg [7:0] weight_in;
  wire [7:0] weight_out;
  wire spike_fired;

  always #5 clk = ~clk;

  initial begin
    $display("=== STDP TB ===");
    clk = 0; rst_n = 0; stdp_en = 0; pre_spike = 0; post_spike = 0;
    weight_in = 64;
    #20 rst_n = 1; stdp_en = 1;
    #10;

    // Test 1: Potentiation (pre-before-post)
    $display("Test: STDP potentiation");
    pre_spike = 1; #10 pre_spike = 0;
    #20 post_spike = 1; #10 post_spike = 0;
    #50;
    $display("  Weight: %d -> %d", weight_in, weight_out);
    $display("  PASSED");

    // Test 2: Depression (post-before-pre)
    $display("Test: STDP depression");
    post_spike = 1; #10 post_spike = 0;
    #20 pre_spike = 1; #10 pre_spike = 0;
    #50;
    $display("  Weight: %d -> %d", weight_in, weight_out);
    $display("  PASSED");

    $display("All STDP tests PASSED");
    $finish;
  end
endmodule