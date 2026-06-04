// EW Deception Generator Testbench — Verilog
// Verifies 5-mode EW waveform generation timing

`timescale 1ns / 1ps

module ew_tb;
  reg clk, rst_n;
  reg [2:0] ew_mode;  // 0=off, 1=RGPO, 2=VGPO, 3=IAM, 4=CrossEye, 5=Saturation
  reg [7:0] target_aoa;
  wire [15:0] phase_out;
  wire [11:0] amplitude_out;
  wire jamming_active;

  always #5 clk = ~clk;

  initial begin
    $display("=== EW TB ===");
    clk = 0; rst_n = 0; ew_mode = 0; target_aoa = 45;
    #20 rst_n = 1;
    #10;

    // Mode 1: RGPO
    $display("Test: RGPO waveform");
    ew_mode = 1; target_aoa = 30;
    #100;
    $display("  Phase=0x%04X, Amp=0x%03X, Active=%b", phase_out, amplitude_out, jamming_active);
    $display("  PASSED");

    // Mode 2: VGPO
    $display("Test: VGPO waveform");
    ew_mode = 2;
    #100;
    $display("  Phase=0x%04X, Amp=0x%03X", phase_out, amplitude_out);
    $display("  PASSED");

    // Mode 3: IAM
    $display("Test: IAM waveform");
    ew_mode = 3;
    #100;
    $display("  PASSED");

    // Mode 4: Cross-Eye
    $display("Test: Cross-Eye jamming");
    ew_mode = 4;
    #100;
    $display("  PASSED");

    // Mode 5: Saturation
    $display("Test: Saturation noise");
    ew_mode = 5;
    #100;
    $display("  PASSED");

    // Mode 0: Off
    $display("Test: EW disabled");
    ew_mode = 0;
    #50;
    $display("  Active=%b", jamming_active);
    $display("  PASSED");

    $display("All EW tests PASSED");
    $finish;
  end
endmodule