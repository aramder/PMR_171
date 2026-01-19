"""Frequency conversion utilities"""


def frequency_to_bytes(freq_mhz: float) -> tuple:
    """Convert frequency in MHz to 4-byte representation
    
    PMR-171 uses big-endian 32-bit integer representing frequency in Hz.
    Example: 146.52 MHz → 146,520,000 Hz → [8, 152, 81, 64]
    
    Round to nearest Hz to avoid floating point errors.
    """
    freq_hz = round(freq_mhz * 1_000_000)  # Round to avoid 144.579999 issues
    
    # Big-endian encoding
    byte1 = (freq_hz >> 24) & 0xFF
    byte2 = (freq_hz >> 16) & 0xFF
    byte3 = (freq_hz >> 8) & 0xFF
    byte4 = freq_hz & 0xFF
    
    return (byte1, byte2, byte3, byte4)


def bytes_to_frequency(freq_bytes: tuple) -> float:
    """Convert 4-byte representation back to MHz
    
    Args:
        freq_bytes: Tuple of 4 bytes (big-endian)
        
    Returns:
        Frequency in MHz
    """
    freq_hz = ((freq_bytes[0] << 24) | 
               (freq_bytes[1] << 16) | 
               (freq_bytes[2] << 8) | 
               freq_bytes[3])
    return freq_hz / 1_000_000


def bcd_to_frequency(bcd_bytes: bytes) -> float:
    """Convert BCD encoded frequency to MHz
    
    CHIRP uses BCD (Binary Coded Decimal) format.
    Each byte represents two decimal digits.
    Example: [00 60 64 44] = 44.64.60.00 -> "446460" -> 446.460 MHz
    Stored in little-endian (reversed) order, frequency * 10.
    """
    if len(bcd_bytes) != 4 or all(b == 0 for b in bcd_bytes):
        return 0.0
    
    def bcd_to_int(bcd_byte):
        """Convert BCD byte to integer (each nibble is a digit)"""
        return (bcd_byte >> 4) * 10 + (bcd_byte & 0x0F)
    
    # Reverse for little-endian, then decode each BCD byte
    bcd_digits = [bcd_to_int(b) for b in reversed(bcd_bytes)]
    
    # Form frequency string: [44, 64, 60, 00] -> "44646000"
    # Insert decimal to get "4464.6000" then divide by 10 -> 446.46 MHz
    freq_int_str = f"{bcd_digits[0]:02d}{bcd_digits[1]:02d}{bcd_digits[2]:02d}{bcd_digits[3]:02d}"
    freq_with_decimal = freq_int_str[:4] + "." + freq_int_str[4:]  # Insert decimal after 4th digit
    freq_mhz = float(freq_with_decimal) / 10.0
    
    return freq_mhz
