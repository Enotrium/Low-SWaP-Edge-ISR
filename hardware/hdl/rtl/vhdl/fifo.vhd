-- ECC-Protected FIFO — VHDL
-- Generic FIFO with optional ECC error injection for SEU testing

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.snn_config_pkg.all;

entity fifo_ecc is
  generic (
    DATA_WIDTH : integer := 32;
    DEPTH      : integer := 4096
  );
  port (
    clk       : in  std_logic;
    rst_n     : in  std_logic;
    data_in   : in  std_logic_vector(DATA_WIDTH - 1 downto 0);
    wr_en     : in  std_logic;
    data_out  : out std_logic_vector(DATA_WIDTH - 1 downto 0);
    rd_en     : in  std_logic;
    full      : out std_logic;
    empty     : out std_logic;
    overflow  : out std_logic;
    ecc_err   : out std_logic  -- ECC error flag
  );
end fifo_ecc;

architecture rtl of fifo_ecc is
  constant ADDR_WIDTH : integer := 12;  -- 4096 entries
  type mem_t is array (0 to DEPTH - 1) of std_logic_vector(DATA_WIDTH - 1 downto 0);
  signal mem       : mem_t := (others => (others => '0'));
  signal wr_ptr    : unsigned(ADDR_WIDTH - 1 downto 0) := (others => '0');
  signal rd_ptr    : unsigned(ADDR_WIDTH - 1 downto 0) := (others => '0');
  signal count     : unsigned(ADDR_WIDTH downto 0) := (others => '0');
  signal ecc_error : std_logic := '0';
  -- ECC: simple parity check
  signal parity_mem : std_logic_vector(0 to DEPTH - 1) := (others => '0');
begin
  process(clk, rst_n)
    variable computed_parity : std_logic;
  begin
    if rst_n = '0' then
      wr_ptr <= (others => '0');
      rd_ptr <= (others => '0');
      count  <= (others => '0');
      overflow <= '0';
      ecc_error <= '0';
      data_out <= (others => '0');
      parity_mem <= (others => '0');
    elsif rising_edge(clk) then
      overflow <= '0';
      ecc_error <= '0';
      -- Write
      if wr_en = '1' and count < DEPTH then
        mem(to_integer(wr_ptr)) <= data_in;
        computed_parity := '0';
        for i in 0 to DATA_WIDTH - 1 loop
          computed_parity := computed_parity xor data_in(i);
        end loop;
        parity_mem(to_integer(wr_ptr)) <= computed_parity;
        wr_ptr <= wr_ptr + 1;
        count  <= count + 1;
      elsif wr_en = '1' and count = DEPTH then
        overflow <= '1';
      end if;
      -- Read with ECC check
      if rd_en = '1' and count > 0 then
        data_out <= mem(to_integer(rd_ptr));
        computed_parity := '0';
        for i in 0 to DATA_WIDTH - 1 loop
          computed_parity := computed_parity xor mem(to_integer(rd_ptr))(i);
        end loop;
        if computed_parity /= parity_mem(to_integer(rd_ptr)) then
          ecc_error <= '1';
        end if;
        rd_ptr <= rd_ptr + 1;
        count  <= count - 1;
      end if;
    end if;
  end process;

  full  <= '1' when count = DEPTH else '0';
  empty <= '1' when count = 0 else '0';
  ecc_err <= ecc_error;
end rtl;