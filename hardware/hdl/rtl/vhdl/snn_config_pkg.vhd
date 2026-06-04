-- SNN Configuration Package — Types, constants, and records for weaponized SNN
-- VHDL core: types shared across lif_neuron, spike_router, neuron_group_core

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package snn_config_pkg is

  -- SNN Architecture
  constant TOTAL_NEURONS   : integer := 2048;
  constant NUM_GROUPS      : integer := 16;
  constant NEURONS_PER_GROUP : integer := 128;
  constant DATA_WIDTH      : integer := 16;
  constant WEIGHT_WIDTH    : integer := 8;
  constant THRESHOLD_WIDTH : integer := 16;
  constant REFRAC_WIDTH    : integer := 8;
  constant LEAK_WIDTH      : integer := 4;
  constant GLOBAL_ID_WIDTH : integer := 11;
  constant GROUP_ID_WIDTH  : integer := 4;
  constant LOCAL_ID_WIDTH  : integer := 7;

  -- Spike Routing
  constant SPIKE_BUFFER_DEPTH : integer := 4096;
  constant MAX_FANOUT_INTER   : integer := 4;
  constant NUM_PARALLEL_UNITS : integer := 16;

  -- AER Spike Packet
  type spike_packet_t is record
    neuron_id  : unsigned(GLOBAL_ID_WIDTH - 1 downto 0);
    group_id   : unsigned(GROUP_ID_WIDTH - 1 downto 0);
    local_id   : unsigned(LOCAL_ID_WIDTH - 1 downto 0);
    weight     : signed(WEIGHT_WIDTH - 1 downto 0);
    valid      : std_logic;
  end record;

  constant SPIKE_PACKET_NULL : spike_packet_t := (
    neuron_id => (others => '0'),
    group_id  => (others => '0'),
    local_id  => (others => '0'),
    weight    => (others => '0'),
    valid     => '0'
  );

  -- LIF Neuron State
  type lif_state_t is record
    membrane   : signed(DATA_WIDTH - 1 downto 0);
    refractory : unsigned(REFRAC_WIDTH - 1 downto 0);
    last_spike : std_logic;
  end record;

  -- STDP Learning Parameters
  constant STDP_ALPHA_POT : integer := 1;  -- Q8 fixed-point: 0.01
  constant STDP_ALPHA_DEP : integer := 1;  -- Q8 fixed-point: 0.012
  constant STDP_WINDOW    : integer := 20;  -- cycles

  -- Electronic Warfare
  type ew_mode_t is (
    EW_OFF, EW_RGPO, EW_VGPO, EW_IAM, EW_CROSS_EYE, EW_SATURATION
  );

  constant EW_DRFM_DEPTH    : integer := 4096;
  constant EW_FH_CHANNELS   : integer := 128;
  constant EW_PHASE_WIDTH   : integer := 16;
  constant EW_AMPLITUDE_WIDTH : integer := 12;

  -- Active Protection System
  constant APS_MAX_TRACKS : integer := 32;
  constant APS_AOA_BINS   : integer := 64;
  constant APS_RANGING_BINS : integer := 256;
  constant APS_KILL_CYCLES  : integer := 100;

  -- Swarm HD Encoding
  constant SWARM_HD_DIM    : integer := 512;
  constant SWARM_MAX_DRONES : integer := 16;

  -- ECC Configuration
  constant ECC_WATCHDOG_CYCLES : integer := 100000;
  constant ECC_SYNDROME_WIDTH  : integer := 4;

  -- Safety / Configuration Register Addresses (AXI4-Lite)
  constant REG_STATUS        : std_logic_vector(7 downto 0) := x"20";
  constant REG_VERSION       : std_logic_vector(7 downto 0) := x"28";
  constant REG_WEAPON_CTRL   : std_logic_vector(7 downto 0) := x"30";
  constant REG_TARGET_ID     : std_logic_vector(7 downto 0) := x"34";
  constant REG_EW_MODE       : std_logic_vector(7 downto 0) := x"38";
  constant REG_APS_CMD       : std_logic_vector(7 downto 0) := x"3C";
  constant REG_SWARM_STATE   : std_logic_vector(7 downto 0) := x"40";
  constant REG_MISSION_STATE : std_logic_vector(7 downto 0) := x"44";
  constant REG_WATCHDOG      : std_logic_vector(7 downto 0) := x"4C";

  -- Derived types
  type mem_array_t is array (natural range <>) of signed(DATA_WIDTH - 1 downto 0);
  type weight_array_t is array (natural range <>) of signed(WEIGHT_WIDTH - 1 downto 0);
  type spike_array_t is array (natural range <>) of spike_packet_t;

end package;