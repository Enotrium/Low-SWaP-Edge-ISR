"""
HDC Error-Correcting Codes — Hardware/software SEU recovery.
Hamming(12,8) SECDED with precomputed lookup tables.
"""
import numpy as np
from typing import Tuple


def _build_tables():
    """Build encode+decode lookup tables for Hamming(12,8) SECDED."""
    enc = {}
    dec = {}
    # Encode: data(0-255) → codeword(0-4095)
    for d in range(256):
        b = [int(bool(d & (1 << i))) for i in range(8)]
        p0 = b[0] ^ b[1] ^ b[3] ^ b[4] ^ b[6] ^ b[7]
        p1 = b[0] ^ b[2] ^ b[3] ^ b[5] ^ b[6] ^ b[7]
        p2 = b[1] ^ b[2] ^ b[3] ^ b[5] ^ b[6]
        cw = d | (p0 << 8) | (p1 << 9) | (p2 << 10)
        p3 = bin(cw & 0xFFF).count('1') % 2
        enc[d] = cw | (p3 << 11)

    # Decode table: brute-force by encoding clean data then flipping bits
    # For each codeword(0-4095), find if it's clean, single-error, or double-error
    import collections
    # First: mark all clean codewords
    clean = {enc[d]: d for d in range(256)}

    # Init all 4096 with (data, corrected=False, double=False)
    for cw in range(4096):
        if cw in clean:
            dec[cw] = (clean[cw], False, False)
        else:
            # Check if it's a single-bit error away from a clean codeword
            found = False
            for bit in range(12):
                parent = cw ^ (1 << bit)
                if parent in clean:
                    dec[cw] = (clean[parent], True, False)
                    found = True
                    break
            if not found:
                dec[cw] = (cw & 0xFF, False, True)
    return enc, dec


_ENC, _DEC = _build_tables()


class Hamming128:
    """Hamming(12,8) SECDED ECC for HD vectors and critical state."""

    @staticmethod
    def encode_byte(data: int) -> int:
        return _ENC[data & 0xFF]

    @staticmethod
    def decode_byte(codeword: int) -> Tuple[int, bool, bool]:
        return _DEC[codeword & 0xFFF]

    @staticmethod
    def protect_hd_vector(vector: np.ndarray) -> np.ndarray:
        n = len(vector)
        num_words = n // 8
        protected = np.zeros(num_words, dtype=np.uint16)
        for w in range(num_words):
            byte_val = 0
            for b in range(8):
                if vector[w * 8 + b] > 0:
                    byte_val |= 1 << b
            protected[w] = _ENC[byte_val]
        return protected

    @staticmethod
    def recover_hd_vector(protected: np.ndarray, hd_dim: int) -> Tuple[np.ndarray, int]:
        num_words = len(protected)
        recovered = np.zeros(hd_dim, dtype=np.int8)
        error_count = 0
        for w in range(min(num_words, hd_dim // 8)):
            data, corrected, _ = _DEC[int(protected[w]) & 0xFFF]
            for b in range(8):
                idx = w * 8 + b
                if idx < hd_dim:
                    recovered[idx] = 1 if (data >> b) & 1 else -1
            if corrected:
                error_count += 1
        return recovered, error_count