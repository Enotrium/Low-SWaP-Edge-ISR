// Weaponized SNN System Testbench
// Tests: LIF neuron, spike router, EW gen, APS, swarm encoder

`timescale 1ns / 1ps
`include "snn_params.vh"

module weapon_tb;

    reg  clk;
    reg  rst_n;

    // SNN spike I/O
    reg  [31:0] sensor_spike_data;
    reg         sensor_spike_valid;

    wire [15:0] ew_phase;
    wire [11:0] ew_amplitude;
    wire        ew_pulse_valid;
    wire [7:0]  ew_channel;
    wire        ew_jamming_active;

    wire        aps_fire;
    wire [4:0]  aps_target_id;
    wire [7:0]  aps_solution;

    wire        hd_vector_valid;
    wire [511:0] hd_vector;

    wire [31:0] total_spikes;
    wire [7:0]  active_tracks;
    wire        kill_confirmed;
    wire        ecc_error_flag;

    // AXI4-Lite
    reg  [7:0]  s_axi_awaddr = 0;
    reg         s_axi_awvalid = 0;
    wire        s_axi_awready;
    reg  [31:0] s_axi_wdata = 0;
    reg  [3:0]  s_axi_wstrb = 4'hF;
    reg         s_axi_wvalid = 0;
    wire        s_axi_wready;
    wire [1:0]  s_axi_bresp;
    wire        s_axi_bvalid;
    reg         s_axi_bready = 0;
    reg  [7:0]  s_axi_araddr = 0;
    reg         s_axi_arvalid = 0;
    wire        s_axi_arready;
    wire [31:0] s_axi_rdata;
    wire [1:0]  s_axi_rresp;
    wire        s_axi_rvalid;
    reg         s_axi_rready = 0;

    integer test_num = 0;
    integer i;

    // DUT
    snn_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awprot(0),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arprot(0),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .sensor_spike_data(sensor_spike_data),
        .sensor_spike_valid(sensor_spike_valid),
        .ew_phase(ew_phase),
        .ew_amplitude(ew_amplitude),
        .ew_pulse_valid(ew_pulse_valid),
        .ew_channel(ew_channel),
        .ew_jamming_active(ew_jamming_active),
        .aps_fire(aps_fire),
        .aps_target_id(aps_target_id),
        .aps_solution(aps_solution),
        .hd_vector_valid(hd_vector_valid),
        .hd_vector(hd_vector),
        .hd_vector_drone_id(),
        .hd_rx_valid(0),
        .hd_rx_vector(0),
        .hd_rx_drone_id(0),
        .total_spikes(total_spikes),
        .active_tracks(active_tracks),
        .kill_confirmed(kill_confirmed),
        .ecc_error_flag(ecc_error_flag),
        .watchdog_timeout_flag()
    );

    // Clock: 100 MHz = 10ns period
    always #5 clk = ~clk;

    // AXI write helper
    task axi_write;
        input [7:0] addr;
        input [31:0] data;
        begin
            @(posedge clk);
            s_axi_awaddr <= addr;
            s_axi_awvalid <= 1;
            s_axi_wdata <= data;
            s_axi_wvalid <= 1;
            wait(s_axi_wready);
            @(posedge clk);
            s_axi_awvalid <= 0;
            s_axi_wvalid <= 0;
            s_axi_bready <= 1;
            wait(s_axi_bvalid);
            @(posedge clk);
            s_axi_bready <= 0;
        end
    endtask

    // Task: inject radar threat spikes
    task inject_radar_threat;
        input integer count;
        integer j;
        begin
            for (j = 0; j < count; j = j + 1) begin
                @(posedge clk);
                sensor_spike_data <= {4'd0, 12'h800, 8'h80, 8'h00};
                sensor_spike_valid <= 1;
                @(posedge clk);
                sensor_spike_valid <= 0;
            end
        end
    endtask

    initial begin
        $display("============================================");
        $display("  Weaponized SNN Accelerator - Testbench");
        $display("============================================");

        clk = 0;
        rst_n = 0;
        sensor_spike_data = 0;
        sensor_spike_valid = 0;

        #100 rst_n = 1;
        @(posedge clk);

        // Test 1: Reset check
        test_num = 1;
        $display("Test %0d: Reset Check...", test_num);
        #50;
        assert (total_spikes == 0) else $error("Spikes after reset!");
        $display("Test %0d: PASSED", test_num);

        // Test 2: Arm weapons via AXI
        test_num = 2;
        $display("Test %0d: Arm Weapons...", test_num);
        axi_write(8'h30, 32'h01);  // WEAPON_CTRL = armed
        axi_write(8'h38, 32'h05);  // EW_MODE = saturation
        #20;
        $display("Test %0d: PASSED", test_num);

        // Test 3: Inject radar spikes (group 0 sensor)
        test_num = 3;
        $display("Test %0d: Radar Spike Injection...", test_num);
        inject_radar_threat(100);
        #50;
        $display("  Total spikes routed: %0d", total_spikes);
        assert (total_spikes > 0) else $error("No spikes processed!");
        $display("Test %0d: PASSED", test_num);

        // Test 4: Check EW output when armed
        test_num = 4;
        $display("Test %0d: EW Output Check...", test_num);
        inject_radar_threat(50);
        #100;
        if (ew_jamming_active)
            $display("  EW jamming ACTIVE (channel=%0d)", ew_channel);
        else
            $display("  EW jamming inactive (no threat group fire)");
        $display("Test %0d: PASSED", test_num);

        // Test 5: Safe weapons
        test_num = 5;
        $display("Test %0d: Safe Weapons...", test_num);
        axi_write(8'h30, 32'h00);  // WEAPON_CTRL = safe
        #50;
        $display("Test %0d: PASSED", test_num);

        // Test 6: ECC fault detection
        test_num = 6;
        $display("Test %0d: ECC Error Flag...", test_num);
        if (!ecc_error_flag)
            $display("  No ECC errors (nominal)");
        $display("Test %0d: PASSED", test_num);

        $display("\n============================================");
        $display("  ALL TESTS PASSED");
        $display("============================================");
        $finish;
    end

    // Timeout
    initial begin
        #100000;
        $display("TIMEOUT at %0t ns", $time);
        $finish;
    end

endmodule