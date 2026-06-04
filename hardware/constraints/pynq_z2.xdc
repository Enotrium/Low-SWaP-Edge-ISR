# PYNQ-Z2 Constraints for Weaponized SNN Accelerator
# Target: xc7z020clg400-1, 100 MHz system clock

# Clock
set_property PACKAGE_PIN H16 [get_ports sys_clk_p]
set_property IOSTANDARD LVCMOS33 [get_ports sys_clk_p]

# Reset
set_property PACKAGE_PIN G15 [get_ports sys_rst_n]
set_property IOSTANDARD LVCMOS33 [get_ports sys_rst_n]

# Clock constraint
create_clock -period 10.000 -name sys_clk [get_ports sys_clk_p]

# Timing constraints
set_output_delay -clock sys_clk 2.0 [get_ports {ew_dac_phase[*]}]
set_output_delay -clock sys_clk 2.0 [get_ports {ew_dac_amplitude[*]}]
set_output_delay -clock sys_clk 2.0 [get_ports {aps_fire_ctrl}]
set_output_delay -clock sys_clk 2.0 [get_ports {swarm_tx_data[*]}]