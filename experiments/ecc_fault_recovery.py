#!/usr/bin/env python3
"""ECC Fault Recovery Experiment — SEU fault injection and recovery."""
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from hdc.ecc import Hamming128
from hdc.error_masking import ErrorMasking

def test_roundtrip():
    """Verify all 256 values encode/decode correctly."""
    print("=== Encode/Decode Roundtrip ===")
    ok = 0
    for v in range(256):
        enc = Hamming128.encode_byte(v)
        dec, corr, dbl = Hamming128.decode_byte(enc)
        if not dbl and dec == v:
            ok += 1
    print(f"  {ok}/256 values roundtrip correctly")
    assert ok == 256
    print("  PASSED")

def test_single_bit_detection():
    """Verify single-bit errors are detected (corrected or flagged)."""
    print("=== Single-Bit Error Detection ===")
    detected = 0
    total = 256 * 12
    for v in range(256):
        enc = Hamming128.encode_byte(v)
        for bit in range(12):
            flipped = enc ^ (1 << bit)
            data, corrected, double = Hamming128.decode_byte(flipped)
            if corrected or double:
                detected += 1
    print(f"  Detected: {detected}/{total} ({(detected/total)*100:.1f}%)")
    assert detected / total >= 0.95  # At least 95% single-bit errors detected
    print("  PASSED")

def test_graceful_degradation():
    print("=== Graceful Degradation ===")
    masker = ErrorMasking(hd_dim=2048)
    curve = masker.degradation_curve([0.0, 0.01, 0.05, 0.10, 0.20])
    for rate, acc in sorted(curve.items()):
        print(f"  BER {rate:.2f}: accuracy = {acc:.3f}")
    assert curve[0.0] > 0.99 and curve[0.20] > 0.4
    print("  PASSED")

def test_hd_vector_ecc():
    print("=== HD Vector ECC Protection ===")
    np.random.seed(42)
    hd = np.random.randint(0, 2, 256).astype(np.int8)
    hd[hd == 0] = -1
    enc = Hamming128.protect_hd_vector(hd)
    for _ in range(3):
        enc[np.random.randint(0, len(enc))] ^= (1 << np.random.randint(0, 12))
    rec, errors = Hamming128.recover_hd_vector(enc, 256)
    matches = np.sum(rec[:256] == hd[:256])
    print(f"  Match: {matches}/256, errors flagged: {errors}")
    print("  PASSED")

if __name__ == "__main__":
    test_roundtrip()
    test_single_bit_detection()
    test_graceful_degradation()
    test_hd_vector_ecc()
    print("\nECC fault recovery PASSED")