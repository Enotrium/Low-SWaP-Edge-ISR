//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Unified Weapon System Top
// Integrates SNN, EW, APS, and Swarm into a single coherent defense system.
// This is the top-level module that connects to the platform (PYNQ-Z2).
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module weapon_top #(
    parameter CORE_CLOCK_MHZ = 100
)(
    input  wire                     sys_clk_p,
    input  wire                     sys_clk_n,
    input  wire                     sys_rst_n,

    // DDR3 interface (for weight storage / state logging)
    inout  wire [14:0]              ddr_addr,
    inout  wire [2:0]               ddr_ba,
    inout  wire                     ddr_cas_n,
    inout  wire                     ddr_ck_n,
    inout  wire                     ddr_ck_p,
    inout  wire                     ddr_cke,
    inout  wire                     ddr_cs_n,
    inout  wire [3:0]               ddr_dm,
    inout  wire [31:0]              ddr_dq,
    inout  wire [3:0]               ddr_dqs_n,
    inout  wire [3:0]               ddr_dqs_p,
    inout  wire                     ddr_odt,
    inout  wire                     ddr_ras_n,
    inout  wire                     ddr_reset_n,
    inout  wire                     ddr_we_n,

    // AXI4-Lite configuration (from PS)
    input  wire [7:0]               s_axi_awaddr,
    input  wire [2:0]               s_axi_awprot,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [1:0]               s_axi_bresp,
    output wire                     s_axi_bvalid,
    input  wire                     s_axi_bready,
    input  wire [7:0]               s_axi_araddr,
    input  wire [2:0]               s_axi_arprot,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output wire [31:0]              s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output wire                     s_axi_rvalid,
    input  wire                     s_axi_rready,

    // --- Sensor Inputs (via EMIO) ---
    // Radar Warning Receiver
    input  wire                     rwr_pulse,
    input  wire [11:0]              rwr_frequency,
    input  wire [7:0]               rwr_amplitude,

    // Acoustic sensor
    input  wire                     acoustic_trigger,
    input  wire [7:0]               acoustic_class,

    // RF/COMINT
    input  wire                     rf_signal_detect,
    input  wire [15:0]              rf_iq_data,

    // --- EW Outputs (to DAC / RF frontend) ---
    output wire [15:0]              ew_dac_phase,
    output wire [11:0]              ew_dac_amplitude,
    output wire                     ew_dac_valid,
    output wire [7:0]               ew_hop_channel,

    // --- APS Outputs (to effector) ---
    output wire                     aps_fire_ctrl,
    output wire [4:0]               aps_target,
    output wire [7:0]               aps_solution_quality,

    // --- Swarm Radio Interface ---
    output wire                     swarm_tx_valid,
    output wire [511:0]             swarm_tx_data,
    input  wire                     swarm_rx_valid,
    input  wire [511:0]             swarm_rx_data,

    // --- Mission Status (to GCS datalink) ---
    output wire [31:0]              status_threat_count,
    output wire [31:0]              status_engagement_count,
    output wire                     status_mission_active,
    output wire                     status_safety_armed
);

    // Internal clock generation (use MMCM/PLL in real implementation)
    wire clk_100mhz;
    wire clk_locked;
    wire rst_n_sync;

    // Simplified clocking (replace with MMCM for real system)
    // For simulation: clk_100mhz = sys_clk_p
    assign clk_100mhz = sys_clk_p;
    assign rst_n_sync = sys_rst_n;

    // Sensor encoding into AER spikes
    wire [31:0] sensor_spike_data;
    wire        sensor_spike_valid;

    // Encode sensor inputs into spike events for the SNN
    sensor_to_spike #(
        .NUM_SENSORS(3)
    ) sensor_enc (
        .clk(clk_100mhz), .rst_n(rst_n_sync),
        .rwr_pulse(rwr_pulse),
        .rwr_frequency(rwr_frequency),
        .rwr_amplitude(rwr_amplitude),
        .acoustic_trigger(acoustic_trigger),
        .acoustic_class(acoustic_class),
        .rf_signal_detect(rf_signal_detect),
        .rf_iq_data(rf_iq_data),
        .spike_out(sensor_spike_data),
        .spike_valid(sensor_spike_valid)
    );

    // Main SNN accelerator
    snn_top snn_core (
        .clk(clk_100mhz),
        .rst_n(rst_n_sync),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awprot(s_axi_awprot),
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
        .s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .sensor_spike_data(sensor_spike_data),
        .sensor_spike_valid(sensor_spike_valid),
        .ew_phase(ew_dac_phase),
        .ew_amplitude(ew_dac_amplitude),
        .ew_pulse_valid(ew_dac_valid),
        .ew_channel(ew_hop_channel),
        .ew_jamming_active(),
        .aps_fire(aps_fire_ctrl),
        .aps_target_id(aps_target),
        .aps_solution(aps_solution_quality),
        .hd_vector_valid(swarm_tx_valid),
        .hd_vector(swarm_tx_data),
        .hd_vector_drone_id(),
        .hd_rx_valid(swarm_rx_valid),
        .hd_rx_vector(swarm_rx_data),
        .hd_rx_drone_id(0),
        .total_spikes(status_threat_count),
        .active_tracks(),
        .kill_confirmed(),
        .ecc_error_flag(),
        .watchdog_timeout_flag()
    );

    assign status_engagement_count = status_threat_count;  // Simplified
    assign status_mission_active = 1'b1;
    assign status_safety_armed = 1'b1;

endmodule


//-----------------------------------------------------------------------------
// Sensor-to-Spike Encoder (Simple AER encoding for defense sensors)
//-----------------------------------------------------------------------------
module sensor_to_spike #(
    parameter NUM_SENSORS = 3
)(
    input  wire                     clk,
    input  wire                     rst_n,

    input  wire                     rwr_pulse,
    input  wire [11:0]              rwr_frequency,
    input  wire [7:0]               rwr_amplitude,

    input  wire                     acoustic_trigger,
    input  wire [7:0]               acoustic_class,

    input  wire                     rf_signal_detect,
    input  wire [15:0]              rf_iq_data,

    output reg  [31:0]              spike_out,
    output reg                      spike_valid
);

    reg [1:0] sensor_sel;

    always @(posedge clk) begin
        if (!rst_n) begin
            spike_out   <= 0;
            spike_valid <= 1'b0;
            sensor_sel  <= 0;
        end else begin
            spike_valid <= 1'b0;

            // Round-robin sensor polling
            case (sensor_sel)
                2'd0: begin
                    if (rwr_pulse) begin
                        // AER: {freq[11:0], amp[7:0], sensor_id=0, group=0, neuron}
                        spike_out <= {4'd0, rwr_frequency, rwr_amplitude, 8'h00};
                        spike_valid <= 1'b1;
                    end
                    sensor_sel <= 1;
                end
                2'd1: begin
                    if (acoustic_trigger) begin
                        spike_out <= {4'd1, 12'd0, acoustic_class, 8'h01};
                        spike_valid <= 1'b1;
                    end
                    sensor_sel <= 2;
                end
                2'd2: begin
                    if (rf_signal_detect) begin
                        spike_out <= {4'd2, 4'd0, rf_iq_data[15:8], rf_iq_data[7:0], 8'h02};
                        spike_valid <= 1'b1;
                    end
                    sensor_sel <= 0;
                end
                default: sensor_sel <= 0;
            endcase
        end
    end

endmodule
