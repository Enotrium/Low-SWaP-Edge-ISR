# Vivado Project Build Script for Weaponized SNN Accelerator
# Targets: PYNQ-Z2 (xc7z020clg400-1)

set project_name weapon_snn
set part xc7z020clg400-1
set top_module weapon_top

create_project $project_name ./build -part $part -force
set_property target_language Verilog [current_project]

# Add RTL source files
add_files -norecurse {
    ../hdl/rtl/common/fifo.v
    ../hdl/rtl/common/snn_config_regs.v
    ../hdl/rtl/neurons/lif_neuron.v
    ../hdl/rtl/router/spike_router.v
    ../hdl/rtl/core/neuron_group_core.v
    ../hdl/rtl/weapon_systems/ew_deception_generator.v
    ../hdl/rtl/weapon_systems/aps_fire_control.v
    ../hdl/rtl/weapon_systems/hd_swarm_encoder.v
    ../hdl/rtl/weapon_systems/ecc_fault_injector.v
    ../hdl/rtl/top/snn_top.v
    ../hdl/rtl/top/weapon_top.v
}

# Add testbench
add_files -fileset sim_1 -norecurse {
    ../hdl/tb/weapon_tb.v
}

# Include paths
set_property include_dirs ../config/generated [get_fileset sources_1]

# Set top-level
set_property top $top_module [get_fileset sources_1]
set_property top weapon_tb [get_fileset sim_1]

# Create block design constraints
read_xdc ../constraints/pynq_z2.xdc

# Run synthesis
synth_design -top $top_module -part $part -flatten_hierarchy rebuilt

# Run implementation
opt_design
place_design
route_design

# Generate bitstream
write_bitstream -force ../outputs/weapon_snn.bit

# Reports
report_timing_summary -file ../outputs/timing.rpt
report_utilization -file ../outputs/utilization.rpt
report_power -file ../outputs/power.rpt

puts "=== Build Complete ==="
puts "Bitstream: ../outputs/weapon_snn.bit"