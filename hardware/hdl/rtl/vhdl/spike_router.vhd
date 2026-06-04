-- AER Spike Router — VHDL Core
-- Round-robin multicast dispatch with APS/EW priority arbitration

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.snn_config_pkg.all;

entity spike_router is
  port (
    clk          : in  std_logic;
    rst_n        : in  std_logic;
    spike_in     : in  spike_packet_t;
    spike_ready  : out std_logic;
    spike_out_00 : out spike_packet_t;
    spike_out_01 : out spike_packet_t;
    spike_out_02 : out spike_packet_t;
    spike_out_03 : out spike_packet_t;
    spike_out_04 : out spike_packet_t;
    spike_out_05 : out spike_packet_t;
    spike_out_06 : out spike_packet_t;
    spike_out_07 : out spike_packet_t;
    spike_out_08 : out spike_packet_t;
    spike_out_09 : out spike_packet_t;
    spike_out_10 : out spike_packet_t;
    spike_out_11 : out spike_packet_t;
    spike_out_12 : out spike_packet_t;
    spike_out_13 : out spike_packet_t;
    spike_out_14 : out spike_packet_t;
    spike_out_15 : out spike_packet_t;
    aps_priority : in  std_logic;
    ew_priority  : in  std_logic;
    fifo_full    : out std_logic;
    fifo_empty   : out std_logic
  );
end spike_router;

architecture rtl of spike_router is
  type group_arr is array (0 to 15) of spike_packet_t;
  signal gp        : group_arr := (others => SPIKE_PACKET_NULL);
  signal rr        : unsigned(3 downto 0) := X"0";
  type fifo_mem is array (0 to 15) of spike_packet_t;
  signal f_mem     : fifo_mem := (others => SPIKE_PACKET_NULL);
  signal f_wr, f_rd : unsigned(3 downto 0) := X"0";
  signal f_cnt     : unsigned(4 downto 0) := "00000";
  signal conn      : std_logic_vector(0 to 15) := (others => '1');
begin
  process(clk, rst_n) begin
    if rst_n = '0' then
      f_wr <= X"0"; f_rd <= X"0"; f_cnt <= "00000";
      f_mem <= (others => SPIKE_PACKET_NULL);
    elsif rising_edge(clk) then
      if spike_in.valid = '1' and f_cnt < 16 then
        f_mem(to_integer(f_wr)) <= spike_in;
        f_wr <= f_wr + 1; f_cnt <= f_cnt + 1;
      end if;
      if f_cnt > 0 and gp(0).valid = '0' then
        f_rd <= f_rd + 1; f_cnt <= f_cnt - 1;
      end if;
    end if;
  end process;
  fifo_full <= '1' when f_cnt = 16 else '0';
  fifo_empty <= '1' when f_cnt = 0 else '0';
  spike_ready <= not (f_cnt = 16);

  process(clk, rst_n)
    variable g : integer range 0 to 15;
  begin
    if rst_n = '0' then
      gp <= (others => SPIKE_PACKET_NULL); rr <= X"0";
    elsif rising_edge(clk) then
      gp <= (others => SPIKE_PACKET_NULL);
      if f_cnt > 0 then
        if aps_priority = '1' and conn(14) = '1' then
          gp(14) <= f_mem(to_integer(f_rd));
        elsif ew_priority = '1' and conn(13) = '1' then
          gp(13) <= f_mem(to_integer(f_rd));
        else
          for i in 0 to 3 loop
            g := (to_integer(rr) + i) mod 16;
            if conn(g) = '1' then
              gp(g) <= f_mem(to_integer(f_rd));
            end if;
          end loop;
          rr <= rr + 4;
        end if;
      end if;
    end if;
  end process;

  spike_out_00 <= gp(0);  spike_out_01 <= gp(1);  spike_out_02 <= gp(2);
  spike_out_03 <= gp(3);  spike_out_04 <= gp(4);  spike_out_05 <= gp(5);
  spike_out_06 <= gp(6);  spike_out_07 <= gp(7);  spike_out_08 <= gp(8);
  spike_out_09 <= gp(9);  spike_out_10 <= gp(10); spike_out_11 <= gp(11);
  spike_out_12 <= gp(12); spike_out_13 <= gp(13); spike_out_14 <= gp(14);
  spike_out_15 <= gp(15);
end rtl;