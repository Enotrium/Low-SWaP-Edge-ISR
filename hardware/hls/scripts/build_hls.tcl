# Vitis HLS Build Script for Weaponized SNN Accelerator
open_project weapon_snn_hls -reset
set_top snn_top
add_files ../src/snn_top_hls.cpp
add_files -tb ../../hdl/tb/weapon_tb.v
open_solution solution1 -reset
set_part {xc7z020clg400-1}
create_clock -period 10 -name clk
csynth_design
cosim_design -trace_level all
export_design -flow impl -rtl verilog -format ip_catalog
puts "=== HLS Build Complete ==="