-- LIF Neuron with On-Chip STDP — VHDL Core
-- 16-bit membrane, 8-bit weight, leaky integrate-and-fire with STDP learning

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.snn_config_pkg.all;

entity lif_neuron is
  generic (
    NEURON_ID : integer := 0
  );
  port (
    clk          : in  std_logic;
    rst_n        : in  std_logic;
    -- Spike I/O
    spike_in     : in  spike_packet_t;
    spike_out    : out spike_packet_t;
    -- STDP control
    stdp_enable  : in  std_logic;
    pre_spike    : in  std_logic;
    post_spike   : in  std_logic;
    weight_in    : in  signed(WEIGHT_WIDTH - 1 downto 0);
    weight_out   : out signed(WEIGHT_WIDTH - 1 downto 0);
    -- State monitoring
    membrane_out : out signed(DATA_WIDTH - 1 downto 0)
  );
end lif_neuron;

architecture rtl of lif_neuron is

  -- Membrane potential
  signal membrane   : signed(DATA_WIDTH - 1 downto 0) := (others => '0');
  signal refractory : unsigned(REFRAC_WIDTH - 1 downto 0) := (others => '0');
  signal threshold : signed(DATA_WIDTH - 1 downto 0) := to_signed(32767, DATA_WIDTH);

  -- STDP state
  signal weight_int   : signed(WEIGHT_WIDTH - 1 downto 0) := to_signed(64, WEIGHT_WIDTH);
  signal pre_trace    : signed(WEIGHT_WIDTH - 1 downto 0) := (others => '0');
  signal post_trace   : signed(WEIGHT_WIDTH - 1 downto 0) := (others => '0');
  signal trace_timer  : unsigned(7 downto 0) := (others => '0');

  -- Spike generation
  signal spike_pending : std_logic := '0';

begin

  -- STDP Learning Process
  stdp_proc: process(clk, rst_n)
  begin
    if rst_n = '0' then
      pre_trace   <= (others => '0');
      post_trace  <= (others => '0');
      trace_timer <= (others => '0');
    elsif rising_edge(clk) then
      if stdp_enable = '1' then
        -- Pre-synaptic trace decay
        if pre_spike = '1' then
          pre_trace <= to_signed(100, WEIGHT_WIDTH);  -- Set trace
        elsif trace_timer > 0 then
          pre_trace <= shift_right(pre_trace, 1);  -- Exponential decay
        end if;

        -- Post-synaptic trace decay
        if post_spike = '1' then
          post_trace <= to_signed(100, WEIGHT_WIDTH);
        elsif trace_timer > 0 then
          post_trace <= shift_right(post_trace, 1);
        end if;

        -- STDP weight update
        if pre_spike = '1' and post_trace > 0 then
          -- Pre-before-post: potentiation
          weight_int <= weight_int + resize(shift_right(post_trace, 3), WEIGHT_WIDTH);
        elsif post_spike = '1' and pre_trace > 0 then
          -- Post-before-pre: depression
          weight_int <= weight_int - resize(shift_right(pre_trace, 3), WEIGHT_WIDTH);
        end if;

        if pre_spike = '1' or post_spike = '1' then
          trace_timer <= to_unsigned(STDP_WINDOW, 8);
        elsif trace_timer > 0 then
          trace_timer <= trace_timer - 1;
        end if;
      end if;
    end if;
  end process;

  -- LIF Membrane Integration
  lif_proc: process(clk, rst_n)
    variable input_current : signed(DATA_WIDTH - 1 downto 0);
  begin
    if rst_n = '0' then
      membrane    <= (others => '0');
      refractory  <= (others => '0');
      spike_pending <= '0';
    elsif rising_edge(clk) then
      if refractory > 0 then
        refractory <= refractory - 1;
        membrane   <= (others => '0');  -- Reset during refractory
      else
        -- Leak (small decay)
        if membrane > 0 then
          membrane <= membrane - to_signed(LEAK_WIDTH, DATA_WIDTH);
        end if;

        -- Synaptic integration
        if spike_in.valid = '1' then
          input_current := resize(weight_int * spike_in.weight, DATA_WIDTH);
          membrane <= membrane + input_current;
        end if;

        -- Spike generation
        if membrane >= threshold then
          spike_pending <= '1';
          membrane   <= (others => '0');
          refractory <= to_unsigned(5, REFRAC_WIDTH);  -- 5-cycle refractory
        else
          spike_pending <= '0';
        end if;
      end if;
    end if;
  end process;

  -- Output assignments
  spike_out.neuron_id <= to_unsigned(NEURON_ID, GLOBAL_ID_WIDTH);
  spike_out.group_id  <= to_unsigned(NEURON_ID / NEURONS_PER_GROUP, GROUP_ID_WIDTH);
  spike_out.local_id  <= to_unsigned(NEURON_ID mod NEURONS_PER_GROUP, LOCAL_ID_WIDTH);
  spike_out.weight    <= weight_int;
  spike_out.valid     <= spike_pending;

  weight_out   <= weight_int;
  membrane_out <= membrane;

end rtl;