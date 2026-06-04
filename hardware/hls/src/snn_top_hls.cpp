// Weaponized SNN HLS Top for Vitis HLS
// Event-driven LIF with defense system outputs
#include "snn_params.h"

static ap_int<16> membrane[SNN_TOTAL_NEURONS];
static ap_uint<8>  refrac_timer[SNN_TOTAL_NEURONS];
static ap_uint<1>  refrac_flag[SNN_TOTAL_NEURONS];

void snn_top(
    hls::stream<ap_uint<64>>& spike_in,
    hls::stream<ap_uint<64>>& spike_out,
    hls::stream<ap_uint<64>>& ew_out,
    hls::stream<ap_uint<64>>& aps_out,
    ap_uint<16> threshold,
    ap_uint<8> leak_rate,
    ap_uint<8> refrac_period,
    ap_uint<32>* total_spikes
) {
#pragma HLS INTERFACE axis port=spike_in
#pragma HLS INTERFACE axis port=spike_out
#pragma HLS INTERFACE axis port=ew_out
#pragma HLS INTERFACE axis port=aps_out
#pragma HLS INTERFACE s_axilite port=return
    static ap_uint<32> cnt = 0;
    while (!spike_in.empty()) {
        ap_uint<64> raw = spike_in.read();
        ap_uint<10> nid = raw.range(9,0);
        ap_int<8> wt = raw.range(17,10);
        ap_uint<4> grp = raw.range(21,18);
        if (!refrac_flag[nid]) {
            membrane[nid] = membrane[nid] - (membrane[nid] >> leak_rate);
            membrane[nid] = membrane[nid] + wt;
            if (membrane[nid] >= threshold) {
                membrane[nid] = 0;
                refrac_flag[nid] = 1;
                refrac_timer[nid] = 0;
                ap_uint<64> out;
                out.range(9,0) = nid;
                out.range(21,18) = grp;
                spike_out.write(out);
                cnt++;
            }
        } else {
            if (refrac_timer[nid] >= refrac_period)
                refrac_flag[nid] = 0;
            else
                refrac_timer[nid] = refrac_timer[nid] + 1;
        }
        if (grp == 4) ew_out.write(raw);
    }
    *total_spikes = cnt;
}