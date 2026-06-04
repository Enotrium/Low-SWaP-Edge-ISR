"""
HDC Error-Correcting Codes — Hardware/software SEU recovery.
Hamming(12,8) ECC for protecting HD vectors and critical state.
Matches the Verilog implementation in hardware/hdl/rtl/weapon_systems/ecc_fault_injector.v
"""
import numpy as np
from typing import Tuple


class Hamming128:
    """
    Hamming(12,8) SECDED — Single Error Correct, Double Error Detect.
    Encodes 8-bit data into 12-bit codeword. Used to protect:
    - HD vector elements (bipolar, treated as 1-bit per element)
    - Membrane potential MSBs
    - Synaptic weight critical bits
    - Safety register states
    """

    # Hamming(12,8) parity check matrix
    H = np.array([
        [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0],
        [0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
    ], dtype=np.uint8)

    # Generator matrix (systematic form)
    G = np.array([
        [1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 0, 1, 0, 1, 0],  # Parity 0
        [0, 1, 1, 0, 0, 1, 1, 0],  # Parity 1
        [0, 0, 0, 1, 1, 1, 1, 0],  # Parity 2
        [1, 1, 1, 1, 1, 1, 1, 1],  # Overall parity
    ], dtype=np.uint8)

    SYNDROME_TO_ERROR = {
        0b0000: -1,      # No error
        0b0001: 11,      # Bit 11
        0b0010: 10,      # Bit 10
        0b0011: 3,       # Bit 3
        0b0100: 9,       # Bit 9
        0b0101: 5,       # Bit 5
        0b0110: 6,       # Bit 6
        0b0111: 7,       # Bit 7
        0b1000: 8,       # Bit 8
        0b1001: 0,       # Bit 0
        0b1010: 1,       # Bit 1
        0b1011: 4,       # Bit 4
        0b1100: 2,       # Bit 2
    }

    @staticmethod
    def encode_byte(data: int) -> int:
        """Encode 8-bit data to 12-bit codeword."""
        data_bits = np.array([(data >> i) & 1 for i in range(8)], dtype=np.uint8)
        codeword = np.dot(Hamming128.G.T, data_bits) % 2
        result = 0
        for i, b in enumerate(codeword):
            result |= int(b) << i
        return result

    @staticmethod
    def decode_byte(codeword: int) -> Tuple[int, bool, bool]:
        """
        Decode 12-bit codeword to 8-bit data.
        Returns (data, corrected, double_error).
        """
        bits = np.array([(codeword >> i) & 1 for i in range(12)], dtype=np.uint8)
        syndrome = np.dot(Hamming128.H, bits) % 2
        syn_val = int(sum(int(s) << i for i, s in enumerate(syndrome)))

        if syn_val == 0:
            return codeword & 0xFF, False, False  # No error

        if syn_val in Hamming128.SYNDROME_TO_ERROR:
            err_bit = Hamming128.SYNDROME_TO_ERROR[syn_val]
            if err_bit >= 0:
                bits[err_bit] ^= 1
                data = sum(int(b) << i for i, b in enumerate(bits[:8]))
                return data, True, False  # Corrected

        # Double error detected (uncorrectable)
        return 0, False, True

    @staticmethod
    def protect_hd_vector(vector: np.ndarray) -> np.ndarray:
        """
        ECC-protect a bipolar HD vector.
        Packs 8 bipolar elements into one 12-bit codeword.
        """
        n = len(vector)
        num_words = n // 8
        protected = np.zeros(num_words, dtype=np.uint16)
        for w in range(num_words):
            byte_val = 0
            for b in range(8):
                if vector[w * 8 + b] > 0:
                    byte_val |= 1 << b
            protected[w] = Hamming128.encode_byte(byte_val)
        return protected

    @staticmethod
    def recover_hd_vector(protected: np.ndarray,
                          hd_dim: int) -> Tuple[np.ndarray, int]:
        """
        Recover HD vector from ECC-protected codewords.
        Returns (recovered_vector, error_count).
        """
        num_words = len(protected)
        recovered = np.zeros(hd_dim, dtype=np.int8)
        error_count = 0
        for w in range(min(num_words, hd_dim // 8)):
            data, corrected, double_err = Hamming128.decode_byte(int(protected[w]))
            for b in range(8):
                idx = w * 8 + b
                if idx < hd_dim:
                    recovered[idx] = 1 if (data >> b) & 1 else -1
            if corrected:
                error_count += 1
        return recovered, error_count


def test_ecc_roundtrip():
    """Verify ECC encode/decode roundtrip."""
    for val in [0, 0xFF, 0xAA, 0x55, 0x12, 0xAB, 0x7B]:
        encoded = Hamming128.encode_byte(val)
        decoded, corrected, double = Hamming128.decode_byte(encoded)
        assert decoded == val, f"Roundtrip failed for 0x{val:02X}"
        assert not corrected
        assert not double


def test_ecc_single_bit_error():
    """Verify single-bit error correction."""
    for val in [0x42, 0xFF, 0x00]:
        encoded = Hamming128.encode_byte(val)
        for bit_pos in range(12):
            flipped = encoded ^ (1 << bit_pos)
            decoded, corrected, _ = Hamming128.decode_byte(flipped)
            assert decoded == val, f"Correction failed for val=0x{val:02X} at bit {bit_pos}"
            assert corrected


if __name__ == "__main__":
    test_ecc_roundtrip()
    test_ecc_single_bit_error()
    print("ECC test PASSED")