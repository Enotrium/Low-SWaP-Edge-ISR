-- Neuron Group Core — VHDL
-- 128-neuron LIF group with parallel processing and shared weight BRAM

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.snn_config_pkg.all;

entity neuron_group_core is
  generic (
    GROUP_ID : integer := 0
  );
  port (
    clk       : in  std_logic;
    rst_n     : in  std_logic;
    spike_in  : in  spike_packet_t;
    spike_out : out spike_packet_t;
    stdp_en   : in  std_logic;
    pre_spike : in  std_logic_vector(NEURONS_PER_GROUP - 1 downto 0);
    post_spike: in  std_logic_vector(NEURONS_PER_GROUP - 1 downto 0);
    weight_wr_en   : in  std_logic;
    weight_wr_addr : in  unsigned(LOCAL_ID_WIDTH - 1 downto 0);
    weight_wr_data : in  signed(WEIGHT_WIDTH - 1 downto 0);
    group_rate     : out unsigned(15 downto 0)
  );
end neuron_group_core;

architecture rtl of neuron_group_core is
  type mem_array is array (0 to NEURONS_PER_GROUP - 1) of signed(DATA_WIDTH - 1 downto 0);
  type wgt_array is array (0 to NEURONS_PER_GROUP - 1) of signed(WEIGHT_WIDTH - 1 downto 0);
  signal membrane    : mem_array := (others => (others => '0'));
  signal weights     : wgt_array := (others => to_signed(64, WEIGHT_WIDTH));
  signal refractory  : unsigned(NEURONS_PER_GROUP * REFRAC_WIDTH - 1 downto 0);
  signal spike_vec   : std_logic_vector(NEURONS_PER_GROUP - 1 downto 0);
  signal spike_count : unsigned(15 downto 0) := X"0000";
  signal local_id    : unsigned(LOCAL_ID_WIDTH - 1 downto 0);
begin
  local_id <= spike_in.local_id;

  -- Parallel LIF for all 128 neurons
  gen_neurons: for i in 0 to NEURONS_PER_GROUP - 1 generate
    signal nid : integer := GROUP_ID * NEURONS_PER_GROUP + i;
  begin
    process(clk, rst_n)
      variable current_w : signed(WEIGHT_WIDTH - 1 downto 0);
      variable current_m : signed(DATA_WIDTH - 1 downto 0);
      variable threshold : signed(DATA_WIDTH - 1 downto 0) := X"7FFF";
    begin
      if rst_n = '0' then
        membrane(i) <= (others => '0');
        spike_vec(i) <= '0';
      elsif rising_edge(clk) then
        current_m := membrane(i);
        current_w := weights(i);
        -- Leak
        if current_m > 0 then
          current_m := current_m - to_signed(LEAK_WIDTH, DATA_WIDTH);
        end if;
        -- Integrate
        if spike_in.valid = '1' and local_id = to_unsigned(i, LOCAL_ID_WIDTH) then
          current_m := current_m + resize(current_w * spike_in.weight, DATA_WIDTH);
        end if;
        -- Fire
        if current_m >= threshold then
          spike_vec(i) <= '1';
          current_m := (others => '0');
        else
          spike_vec(i) <= '0';
        end if;
        membrane(i) <= current_m;
      end if;
    end process;
  end generate;

  -- Weight update
  process(clk) begin
    if rising_edge(clk) then
      if weight_wr_en = '1' then
        weights(to_integer(weight_wr_addr)) <= weight_wr_data;
      end if;
    end if;
  end process;

  -- Spike aggregation
  process(clk) begin
    if rising_edge(clk) then
      spike_count <= (others => '0');
      for i in 0 to NEURONS_PER_GROUP - 1 loop
        if spike_vec(i) = '1' then
          spike_count <= spike_count + 1;
        end if;
      end loop;
    end if;
  end process;

  spike_out.neuron_id <= to_unsigned(GROUP_ID * NEURONS_PER_GROUP, GLOBAL_ID_WIDTH);
  spike_out.group_id  <= to_unsigned(GROUP_ID, GROUP_ID_WIDTH);
  spike_out.local_id  <= (others => '0');
  spike_out.weight    <= to_signed(1, WEIGHT_WIDTH);
  spike_out.valid     <= '1' when spike_count > 0 else '0';
  group_rate          <= spike_count;
end rtl;