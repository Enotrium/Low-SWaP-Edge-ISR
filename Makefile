.PHONY: test synth bitstream hls clean docs

PYTHON := python3
VIVADO := vivado
VITIS_HLS := vitis_hls

# ── Python Tests ────────────────────────────────────────────────────
test:
	cd config && $(PYTHON) generate_params.py
	cd experiments && $(PYTHON) threat_detection.py
	cd experiments && $(PYTHON) ew_aps_sead.py
	cd experiments && $(PYTHON) benchmark_energy.py
	cd experiments && $(PYTHON) ecc_fault_recovery.py
	cd experiments && $(PYTHON) supply_chain.py
	cd tests && $(PYTHON) onchip_stdp_experiment.py
	cd tests && $(PYTHON) fpga_stdp_parity.py

test-threat:
	cd config && $(PYTHON) generate_params.py
	cd experiments && $(PYTHON) threat_detection.py

test-sead:
	cd config && $(PYTHON) generate_params.py
	cd experiments && $(PYTHON) ew_aps_sead.py

test-energy:
	cd experiments && $(PYTHON) benchmark_energy.py

test-fault:
	cd experiments && $(PYTHON) ecc_fault_recovery.py

# ── FPGA Synthesis ──────────────────────────────────────────────────
synth:
	cd hardware/scripts && $(VIVADO) -source build_vivado.tcl

hls:
	cd hardware/hls/scripts && $(VITIS_HLS) -f build_hls.tcl

bitstream: synth hls

# ── Documentation ───────────────────────────────────────────────────
docs:
	@echo "See docs/ — architecture.md, safety.md, threat_model.md, deployment.md, register_map.md"

# ── Clean ───────────────────────────────────────────────────────────
clean:
	rm -rf __pycache__ software/python/snn_fpga_accelerator/__pycache__
	rm -rf experiments/__pycache__ tests/__pycache__ config/__pycache__
	rm -rf hardware/outputs/
	rm -rf *.vcd *.wlf transcript work/
	find . -name "*.pyc" -delete
	find . -name ".DS_Store" -delete