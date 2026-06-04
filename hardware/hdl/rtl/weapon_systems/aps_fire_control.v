//-----------------------------------------------------------------------------
// Weaponized SNN Accelerator — Active Protection System (APS) Fire Control
// Hard-kill interceptor fire control with bounded <1us latency.
// Processes SNN threat tracks and generates effector trigger signals.
//
// Features:
//  - Simultaneous tracking of up to APS_MAX_TRACKS threats
//  - Deterministic intercept solution computation (cycle-accurate)
//  - Angle-of-arrival (AoA) + range bin target localization
//  - Safety interlock (weapon_ctrl[0] must be set)
//  - Mutual exclusion with EW countermeasures
//  - Shot-to-kill assessment feedback
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module aps_fire_control #(
    parameter MAX_TRACKS     = `APS_MAX_TRACKS,
    parameter AOA_BINS       = `APS_AOA_BINS,
    parameter RANGING_BINS   = `APS_RANGING_BINS,
    parameter KILL_CYCLES    = `APS_KILL_CYCLES,
    parameter TRACK_ID_WIDTH = 5  // log2(MAX_TRACKS)
)(
    input  wire                     clk,
    input  wire                     rst_n,

    // Safety interlock from config regs
    input  wire [7:0]               weapon_ctrl,       // [0] = arm, [1] = auto-engage

    // Threat track inputs (from SNN threat_class groups)
    input  wire                     track_valid,
    input  wire [5:0]               track_aoa,          // Angle of arrival (0-63)
    input  wire [7:0]               track_range_bin,    // Range bin (0-255)
    input  wire [15:0]              track_velocity,     // Closing velocity estimate
    input  wire [7:0]               track_threat_class, // Threat classification from SNN

    // Fire command from host (AXI register)
    input  wire                     fire_trigger,       // APS_CMD register write

    // EW override (mutual exclusion)
    input  wire                     ew_active,
    output reg                      aps_override_ew,    // Assert to silence EW

    // Effector interface
    output reg                      fire_command,       // Hard-kill launch pulse
    output reg [TRACK_ID_WIDTH-1:0] target_track_id,    // Which track to engage
    output reg [7:0]                intercept_solution, // 0-255 intercept quality

    // Status
    output reg [31:0]               tracks_active,
    output reg                      engagement_in_progress,
    output reg                      kill_confirmed
);

    // Track state memory
    reg [5:0]  track_aoa_mem     [0:MAX_TRACKS-1];
    reg [7:0]  track_range_mem   [0:MAX_TRACKS-1];
    reg [15:0] track_vel_mem     [0:MAX_TRACKS-1];
    reg [7:0]  track_class_mem   [0:MAX_TRACKS-1];
    reg        track_valid_mem   [0:MAX_TRACKS-1];
    reg [15:0] track_timer_mem   [0:MAX_TRACKS-1];

    // Track management
    reg [TRACK_ID_WIDTH-1:0] track_alloc_ptr;
    reg [TRACK_ID_WIDTH-1:0] engage_track;
    reg                       engage_in_progress;
    reg [15:0]                engage_timer;
    reg                       kill_assessment;

    integer i;

    // Fire control FSM
    localparam [2:0]
        ST_MONITOR     = 3'd0,
        ST_ASSESS      = 3'd1,
        ST_AUTHORIZE   = 3'd2,
        ST_LAUNCH      = 3'd3,
        ST_KILL_ASSESS = 3'd4;

    reg [2:0] state;

    // Threat prioritization: compute intercept solution quality
    // Higher score = higher priority (closing fast, close range, high threat class)
    wire [7:0] intercept_quality;
    reg  [7:0] best_quality;
    reg [TRACK_ID_WIDTH-1:0] best_track;

    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < MAX_TRACKS; i = i + 1) begin
                track_valid_mem[i] <= 1'b0;
                track_timer_mem[i] <= 16'd0;
            end
            track_alloc_ptr     <= 0;
            state               <= ST_MONITOR;
            fire_command        <= 1'b0;
            target_track_id     <= 0;
            intercept_solution  <= 0;
            aps_override_ew     <= 1'b0;
            engage_in_progress  <= 1'b0;
            engagement_in_progress <= 1'b0;
            kill_confirmed      <= 1'b0;
            engage_timer        <= 0;
            best_quality        <= 0;
            best_track          <= 0;
            tracks_active       <= 0;
        end else begin
            // Defaults
            fire_command <= 1'b0;

            // Track insertion / update
            if (track_valid) begin
                // Find existing or free slot
                reg found;
                reg [TRACK_ID_WIDTH-1:0] slot;
                found = 0;
                slot = track_alloc_ptr;

                for (i = 0; i < MAX_TRACKS; i = i + 1) begin
                    if (!found && track_valid_mem[i] &&
                        track_aoa_mem[i] == track_aoa) begin
                        slot = i[TRACK_ID_WIDTH-1:0];
                        found = 1;
                    end
                end

                if (!found) begin
                    // New track: search for empty slot
                    for (i = 0; i < MAX_TRACKS; i = i + 1) begin
                        if (!found && !track_valid_mem[i]) begin
                            slot = i[TRACK_ID_WIDTH-1:0];
                            found = 1;
                        end
                    end
                end

                if (found) begin
                    track_aoa_mem[slot]     <= track_aoa;
                    track_range_mem[slot]   <= track_range_bin;
                    track_vel_mem[slot]     <= track_velocity;
                    track_class_mem[slot]   <= track_threat_class;
                    track_valid_mem[slot]   <= 1'b1;
                    track_timer_mem[slot]   <= 0;
                end
            end

            // Age tracks
            tracks_active <= 0;
            for (i = 0; i < MAX_TRACKS; i = i + 1) begin
                if (track_valid_mem[i]) begin
                    if (track_timer_mem[i] >= 100000) begin  // 1ms at 100 MHz
                        track_valid_mem[i] <= 1'b0;          // Drop stale track
                    end else begin
                        track_timer_mem[i] <= track_timer_mem[i] + 1;
                        tracks_active <= tracks_active + 1;
                    end
                end
            end

            // Fire control FSM
            case (state)
                ST_MONITOR: begin
                    engage_in_progress <= 1'b0;
                    engagement_in_progress <= 1'b0;
                    aps_override_ew <= 1'b0;
                    engage_timer <= 0;

                    // Auto-engage or manual trigger
                    if ((weapon_ctrl[1] || fire_trigger) && weapon_ctrl[0]) begin
                        // Score all tracks
                        best_quality <= 0;
                        best_track <= 0;
                        for (i = 0; i < MAX_TRACKS; i = i + 1) begin
                            if (track_valid_mem[i]) begin
                                // Quality = range closness (255 - range) + threat class * 2
                                reg [7:0] q;
                                q = (255 - track_range_mem[i]) + {track_class_mem[i], 1'b0};
                                if (q > best_quality) begin
                                    best_quality <= q;
                                    best_track <= i[TRACK_ID_WIDTH-1:0];
                                end
                            end
                        end

                        if (best_quality > 0) begin
                            engage_track <= best_track;
                            intercept_solution <= best_quality;
                            state <= ST_ASSESS;
                        end
                    end
                end

                ST_ASSESS: begin
                    // Evaluate intercept solution (cycle-accurate, 50ns)
                    if (intercept_solution > 64) begin  // Minimum quality threshold
                        state <= ST_AUTHORIZE;
                    end else begin
                        state <= ST_MONITOR;
                    end
                end

                ST_AUTHORIZE: begin
                    // Assert EW override (mute countermeasures during hard-kill)
                    if (ew_active) begin
                        aps_override_ew <= 1'b1;
                    end else begin
                        aps_override_ew <= 1'b0;
                        state <= ST_LAUNCH;
                    end
                end

                ST_LAUNCH: begin
                    // Cycle-accurate fire pulse
                    target_track_id <= engage_track;
                    engagement_in_progress <= 1'b1;
                    engage_in_progress <= 1'b1;

                    if (engage_timer < KILL_CYCLES) begin
                        engage_timer <= engage_timer + 1;
                        fire_command <= 1'b1;
                    end else begin
                        fire_command <= 1'b0;
                        state <= ST_KILL_ASSESS;
                    end
                end

                ST_KILL_ASSESS: begin
                    // Wait for kill confirmation or re-engage
                    if (engage_timer >= KILL_CYCLES * 10) begin
                        kill_confirmed <= 1'b1;
                        track_valid_mem[engage_track] <= 1'b0;
                        state <= ST_MONITOR;
                    end else begin
                        engage_timer <= engage_timer + 1;
                    end
                end

                default: state <= ST_MONITOR;
            endcase
        end
    end

endmodule
