//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — AXI4-Lite Configuration Register File
// Extended register map for defense systems:
//   0x30  WEAPON_CTRL     [RW] Weapon enable, safety interlocks
//   0x34  TARGET_ID       [RW] Target track ID for engagement
//   0x38  EW_MODE         [RW] EW countermeasure mode select
//   0x3C  APS_CMD         [W]  Active protection system fire command
//   0x40  SWARM_STATE     [RW] Swarm role/state vector
//   0x44  MISSION_STATE   [RW] Mission phase (search/track/engage)
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module snn_config_regs #(
    parameter C_S_AXI_ADDR_WIDTH = 8,
    parameter C_S_AXI_DATA_WIDTH = 32
)(
    // AXI4-Lite Interface
    input  wire                              s_axi_aclk,
    input  wire                              s_axi_aresetn,

    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire [2:0]                        s_axi_awprot,
    input  wire                              s_axi_awvalid,
    output wire                              s_axi_awready,

    input  wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [C_S_AXI_DATA_WIDTH/8-1:0]   s_axi_wstrb,
    input  wire                              s_axi_wvalid,
    output wire                              s_axi_wready,

    output wire [1:0]                        s_axi_bresp,
    output wire                              s_axi_bvalid,
    input  wire                              s_axi_bready,

    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire [2:0]                        s_axi_arprot,
    input  wire                              s_axi_arvalid,
    output wire                              s_axi_arready,

    output wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output wire [1:0]                        s_axi_rresp,
    output wire                              s_axi_rvalid,
    input  wire                              s_axi_rready,

    // Configuration Outputs
    output wire                              router_config_we,
    output wire [31:0]                       router_config_addr,
    output wire [31:0]                       router_config_wdata,
    input  wire [31:0]                       router_config_rdata,

    output wire                              neuron_config_we,
    output wire [9:0]                        neuron_config_addr,
    output wire [31:0]                       neuron_config_wdata,

    output wire [15:0]                       global_threshold,
    output wire [7:0]                        global_leak_rate,
    output wire [7:0]                        global_refrac_period,

    // Defense Extension Registers
    output reg  [7:0]                        weapon_ctrl,       // Safety interlock, arm state
    output reg  [15:0]                       target_track_id,   // Selected target
    output reg  [7:0]                        ew_mode,           // EW waveform select
    output reg                              aps_fire_trigger,   // APS hard-kill pulse
    output reg  [15:0]                       swarm_state,       // Swarm mode vector
    output reg  [7:0]                        mission_phase,     // Mission FSM state

    // Status Inputs
    input  wire [31:0]                       router_spike_count,
    input  wire [31:0]                       neuron_spike_count,
    input  wire                              fifo_overflow,
    input  wire [7:0]                        active_neurons,
    input  wire [31:0]                       throughput_counter,
    input  wire [31:0]                       service_cycles_counter,
    input  wire                              ecc_error,
    input  wire                              watchdog_timeout
);

    // Register Address Map (word-aligned)
    localparam ADDR_CONFIG_CTRL      = 5'h00;  // 0x00
    localparam ADDR_CONFIG_ADDR      = 5'h01;  // 0x04
    localparam ADDR_CONFIG_WDATA     = 5'h02;  // 0x08
    localparam ADDR_CONFIG_RDATA     = 5'h03;  // 0x0C
    localparam ADDR_THRESHOLD        = 5'h04;  // 0x10
    localparam ADDR_NEURON_PARAMS    = 5'h05;  // 0x14
    localparam ADDR_ROUTER_SPIKE_CNT = 5'h06;  // 0x18
    localparam ADDR_NEURON_SPIKE_CNT = 5'h07;  // 0x1C
    localparam ADDR_STATUS           = 5'h08;  // 0x20
    localparam ADDR_THROUGHPUT       = 5'h09;  // 0x24
    localparam ADDR_VERSION          = 5'h0A;  // 0x28
    localparam ADDR_SERVICE_CYCLES   = 5'h0B;  // 0x2C
    localparam ADDR_WEAPON_CTRL      = 5'h0C;  // 0x30 — Weapon safety
    localparam ADDR_TARGET_ID        = 5'h0D;  // 0x34 — Target track
    localparam ADDR_EW_MODE          = 5'h0E;  // 0x38 — EW waveform
    localparam ADDR_APS_CMD          = 5'h0F;  // 0x3C — APS trigger
    localparam ADDR_SWARM_STATE      = 5'h10;  // 0x40 — Swarm config
    localparam ADDR_MISSION_STATE    = 5'h11;  // 0x44 — Mission phase
    localparam ADDR_ECC_STATUS       = 5'h12;  // 0x48 — ECC error flags
    localparam ADDR_WATCHDOG         = 5'h13;  // 0x4C — Watchdog kick

    // AXI interface registers
    reg  aw_ready;
    reg  w_ready;
    reg  [1:0] b_resp;
    reg  b_valid;
    reg  ar_ready;
    reg  [C_S_AXI_DATA_WIDTH-1:0] r_data;
    reg  [1:0] r_resp;
    reg  r_valid;

    reg  [C_S_AXI_ADDR_WIDTH-1:0] aw_addr;
    reg  [C_S_AXI_ADDR_WIDTH-1:0] ar_addr;
    reg  aw_en;

    assign s_axi_awready = aw_ready;
    assign s_axi_wready  = w_ready;
    assign s_axi_bresp   = b_resp;
    assign s_axi_bvalid  = b_valid;
    assign s_axi_arready = ar_ready;
    assign s_axi_rdata   = r_data;
    assign s_axi_rresp   = r_resp;
    assign s_axi_rvalid  = r_valid;

    // Configuration registers
    reg  [31:0] reg_config_ctrl;
    reg  [31:0] reg_config_addr;
    reg  [31:0] reg_config_wdata;
    reg  [15:0] reg_threshold;
    reg  [7:0]  reg_leak_rate;
    reg  [7:0]  reg_refrac_period;
    reg         config_we_pulse;
    reg  [1:0]  config_target;

    // Watchdog counter
    reg [31:0] watchdog_kick_cnt;
    reg        watchdog_kick_seen;

    assign router_config_we    = config_we_pulse & (config_target == 2'd0);
    assign router_config_addr  = reg_config_addr;
    assign router_config_wdata = reg_config_wdata;

    assign neuron_config_we    = config_we_pulse & (config_target == 2'd1);
    assign neuron_config_addr  = reg_config_addr[9:0];
    assign neuron_config_wdata = reg_config_wdata;

    assign global_threshold    = reg_threshold;
    assign global_leak_rate    = reg_leak_rate;
    assign global_refrac_period = reg_refrac_period;

    // AXI Write Address
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            aw_ready <= 1'b0;
            aw_en    <= 1'b1;
            aw_addr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~aw_ready && s_axi_awvalid && s_axi_wvalid && aw_en) begin
                aw_ready <= 1'b1;
                aw_addr  <= s_axi_awaddr;
                aw_en    <= 1'b0;
            end else if (s_axi_bready && b_valid) begin
                aw_en    <= 1'b1;
                aw_ready <= 1'b0;
            end else begin
                aw_ready <= 1'b0;
            end
        end
    end

    // AXI Write Data
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            w_ready <= 1'b0;
        end else begin
            if (~w_ready && s_axi_wvalid && s_axi_awvalid && aw_en) begin
                w_ready <= 1'b1;
            end else begin
                w_ready <= 1'b0;
            end
        end
    end

    wire write_en = aw_ready && s_axi_awvalid && w_ready && s_axi_wvalid;
    wire [4:0] write_addr = aw_addr[C_S_AXI_ADDR_WIDTH-1:2];

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            reg_config_ctrl  <= 32'd0;
            reg_config_addr  <= 32'd0;
            reg_config_wdata <= 32'd0;
            reg_threshold    <= 16'd100;
            reg_leak_rate    <= 8'h03;
            reg_refrac_period <= 8'd10;
            config_we_pulse  <= 1'b0;
            config_target    <= 2'd0;
            weapon_ctrl      <= 8'h00;    // Safe/disabled on reset
            target_track_id  <= 16'd0;
            ew_mode          <= 8'd0;
            aps_fire_trigger <= 1'b0;
            swarm_state      <= 16'd0;
            mission_phase    <= 8'd0;
            watchdog_kick_cnt <= 32'd0;
            watchdog_kick_seen <= 1'b0;
        end else begin
            config_we_pulse <= 1'b0;
            aps_fire_trigger <= 1'b0;    // Pulse-only

            if (write_en) begin
                case (write_addr)
                    ADDR_CONFIG_CTRL: begin
                        if (s_axi_wstrb[0]) begin
                            reg_config_ctrl[7:0] <= s_axi_wdata[7:0];
                            config_target        <= s_axi_wdata[1:0];
                        end
                    end
                    ADDR_CONFIG_ADDR: begin
                        if (s_axi_wstrb[0]) reg_config_addr[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_config_addr[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_config_addr[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_config_addr[31:24] <= s_axi_wdata[31:24];
                    end
                    ADDR_CONFIG_WDATA: begin
                        if (s_axi_wstrb[0]) reg_config_wdata[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_config_wdata[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_config_wdata[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_config_wdata[31:24] <= s_axi_wdata[31:24];
                        config_we_pulse <= 1'b1;
                    end
                    ADDR_THRESHOLD: begin
                        if (s_axi_wstrb[0]) reg_threshold[7:0]  <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_threshold[15:8] <= s_axi_wdata[15:8];
                    end
                    ADDR_NEURON_PARAMS: begin
                        if (s_axi_wstrb[0]) reg_leak_rate    <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_refrac_period <= s_axi_wdata[15:8];
                    end
                    // Defense extension registers
                    ADDR_WEAPON_CTRL: begin
                        if (s_axi_wstrb[0]) weapon_ctrl <= s_axi_wdata[7:0];
                    end
                    ADDR_TARGET_ID: begin
                        if (s_axi_wstrb[0]) target_track_id[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) target_track_id[15:8]  <= s_axi_wdata[15:8];
                    end
                    ADDR_EW_MODE: begin
                        if (s_axi_wstrb[0]) ew_mode <= s_axi_wdata[7:0];
                    end
                    ADDR_APS_CMD: begin
                        if (s_axi_wstrb[0]) aps_fire_trigger <= s_axi_wdata[0];
                    end
                    ADDR_SWARM_STATE: begin
                        if (s_axi_wstrb[0]) swarm_state[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) swarm_state[15:8]  <= s_axi_wdata[15:8];
                    end
                    ADDR_MISSION_STATE: begin
                        if (s_axi_wstrb[0]) mission_phase <= s_axi_wdata[7:0];
                    end
                    ADDR_WATCHDOG: begin
                        watchdog_kick_seen <= 1'b1;
                    end
                    default: ;
                endcase
            end

            // Watchdog counter
            if (watchdog_kick_seen) begin
                watchdog_kick_cnt <= 32'd0;
                watchdog_kick_seen <= 1'b0;
            end else if (watchdog_kick_cnt < `ECC_WATCHDOG_CYCLES) begin
                watchdog_kick_cnt <= watchdog_kick_cnt + 1'b1;
            end
        end
    end

    assign watchdog_timeout = (watchdog_kick_cnt >= `ECC_WATCHDOG_CYCLES);

    // AXI Write Response
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            b_valid <= 1'b0;
            b_resp  <= 2'b00;
        end else begin
            if (write_en && ~b_valid) begin
                b_valid <= 1'b1;
                b_resp  <= 2'b00;
            end else if (s_axi_bready && b_valid) begin
                b_valid <= 1'b0;
            end
        end
    end

    // AXI Read Address
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            ar_ready <= 1'b0;
            ar_addr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~ar_ready && s_axi_arvalid) begin
                ar_ready <= 1'b1;
                ar_addr  <= s_axi_araddr;
            end else begin
                ar_ready <= 1'b0;
            end
        end
    end

    wire [4:0] read_addr = ar_addr[C_S_AXI_ADDR_WIDTH-1:2];

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            r_data  <= 32'd0;
            r_valid <= 1'b0;
            r_resp  <= 2'b00;
        end else begin
            if (ar_ready && s_axi_arvalid && ~r_valid) begin
                r_valid <= 1'b1;
                r_resp  <= 2'b00;
                case (read_addr)
                    ADDR_CONFIG_CTRL:       r_data <= reg_config_ctrl;
                    ADDR_CONFIG_ADDR:       r_data <= reg_config_addr;
                    ADDR_CONFIG_WDATA:      r_data <= reg_config_wdata;
                    ADDR_CONFIG_RDATA:      r_data <= router_config_rdata;
                    ADDR_THRESHOLD:         r_data <= {16'd0, reg_threshold};
                    ADDR_NEURON_PARAMS:     r_data <= {16'd0, reg_refrac_period, reg_leak_rate};
                    ADDR_ROUTER_SPIKE_CNT:  r_data <= router_spike_count;
                    ADDR_NEURON_SPIKE_CNT:  r_data <= neuron_spike_count;
                    ADDR_STATUS:            r_data <= {22'd0, watchdog_timeout, ecc_error, active_neurons, fifo_overflow};
                    ADDR_THROUGHPUT:        r_data <= throughput_counter;
                    ADDR_VERSION:           r_data <= 32'h534E4E02;  // "SNN" + v2 (weaponized)
                    ADDR_SERVICE_CYCLES:    r_data <= service_cycles_counter;
                    ADDR_WEAPON_CTRL:       r_data <= {24'd0, weapon_ctrl};
                    ADDR_TARGET_ID:         r_data <= {16'd0, target_track_id};
                    ADDR_EW_MODE:           r_data <= {24'd0, ew_mode};
                    ADDR_APS_CMD:           r_data <= {31'd0, aps_fire_trigger};
                    ADDR_SWARM_STATE:       r_data <= {16'd0, swarm_state};
                    ADDR_MISSION_STATE:     r_data <= {24'd0, mission_phase};
                    ADDR_ECC_STATUS:        r_data <= {30'd0, watchdog_timeout, ecc_error};
                    ADDR_WATCHDOG:          r_data <= watchdog_kick_cnt;
                    default:                r_data <= 32'hDEADBEEF;
                endcase
            end else if (r_valid && s_axi_rready) begin
                r_valid <= 1'b0;
            end
        end
    end

    wire _unused = &{s_axi_awprot, s_axi_arprot, 1'b0};

endmodule
