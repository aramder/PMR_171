"""Channel validation utilities for PMR-171 programming

Protocol Reference: docs/PMR171_PROTOCOL.md

PMR-171 Channel Data Constraints (from UART protocol analysis):
- Channel Index: 0-999 (1000 channels max)
- Channel Name: 11 characters max (12 bytes with null terminator)
- CTCSS Index: 0-55 (0=None, 1-55=tone frequencies)
- Mode: 0-9 (USB, LSB, CWR, CWL, AM, WFM, NFM, DIGI, PKT, DMR), 255=empty
- Frequency: Big-endian 32-bit Hz (practical range ~100kHz to 1GHz)
- CRC: CRC-16-CCITT (polynomial 0x1021, init 0xFFFF)
"""

# PMR-171 Protocol Constants
PMR171_MAX_CHANNELS = 1000
PMR171_MAX_CHANNEL_NAME_LENGTH = 11  # 12 bytes - 1 for null terminator
PMR171_CTCSS_MAX_INDEX = 55
PMR171_MIN_FREQUENCY_HZ = 100_000  # 100 kHz
PMR171_MAX_FREQUENCY_HZ = 1_000_000_000  # 1 GHz

# Valid mode values for PMR-171
PMR171_VALID_MODES = {
    0: "USB",
    1: "LSB", 
    2: "CWR",
    3: "CWL",
    4: "AM",
    5: "WFM",
    6: "NFM",
    7: "DIGI",
    8: "PKT",
    9: "DMR",
    255: "Empty/Unused"
}

# CTCSS Tone Table (index -> frequency Hz) from protocol analysis
PMR171_CTCSS_TONES = {
    0: None, 1: 67.0, 2: 69.3, 3: 71.9, 4: 74.4, 5: 77.0, 6: 79.7,
    7: 82.5, 8: 85.4, 9: 88.5, 10: 91.5, 11: 94.8, 12: 97.4, 13: 100.0,
    14: 103.5, 15: 107.2, 16: 110.9, 17: 114.8, 18: 118.8, 19: 123.0,
    20: 127.3, 21: 131.8, 22: 136.5, 23: 141.3, 24: 146.2, 25: 150.0,
    26: 151.4, 27: 156.7, 28: 159.8, 29: 162.2, 30: 165.5, 31: 167.9,
    32: 171.3, 33: 173.8, 34: 177.3, 35: 179.9, 36: 183.5, 37: 186.2,
    38: 189.9, 39: 192.8, 40: 196.6, 41: 199.5, 42: 203.5, 43: 206.5,
    44: 210.7, 45: 213.8, 46: 218.1, 47: 221.3, 48: 225.7, 49: 229.1,
    50: 233.6, 51: 237.1, 52: 241.8, 53: 245.5, 54: 250.3, 55: 254.1
}


def validate_pmr171_channel_name(name: str) -> tuple:
    """Validate channel name for PMR-171 protocol constraints
    
    Args:
        name: Channel name string
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if name is None:
        return True, None  # Empty name is valid
    
    # Strip null terminators for validation
    clean_name = name.rstrip('\u0000').strip()
    
    if len(clean_name) > PMR171_MAX_CHANNEL_NAME_LENGTH:
        return False, f"Channel name exceeds {PMR171_MAX_CHANNEL_NAME_LENGTH} characters (got {len(clean_name)})"
    
    # Check for non-ASCII characters (PMR-171 uses ASCII)
    try:
        clean_name.encode('ascii')
    except UnicodeEncodeError:
        return False, "Channel name contains non-ASCII characters"
    
    return True, None


def validate_pmr171_ctcss_index(index: int) -> tuple:
    """Validate CTCSS tone index for PMR-171 protocol
    
    Args:
        index: CTCSS tone index (0-55)
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if index < 0:
        return False, f"CTCSS index cannot be negative (got {index})"
    
    if index > PMR171_CTCSS_MAX_INDEX:
        return False, f"CTCSS index exceeds maximum {PMR171_CTCSS_MAX_INDEX} (got {index})"
    
    return True, None


def validate_pmr171_mode(mode: int) -> tuple:
    """Validate mode value for PMR-171 protocol
    
    Args:
        mode: Mode value (0-9 or 255)
              0=USB, 1=LSB, 2=CWR, 3=CWL, 4=AM, 5=WFM, 6=NFM, 7=DIGI, 8=PKT, 9=DMR
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if mode not in PMR171_VALID_MODES:
        valid_modes = ', '.join(f"{k}={v}" for k, v in PMR171_VALID_MODES.items() if k != 255)
        return False, f"Invalid mode {mode}. Valid modes: {valid_modes}"
    
    return True, None


def validate_pmr171_channel_index(index: int) -> tuple:
    """Validate channel index for PMR-171 protocol
    
    Args:
        index: Channel index (0-999)
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if index < 0:
        return False, f"Channel index cannot be negative (got {index})"
    
    if index >= PMR171_MAX_CHANNELS:
        return False, f"Channel index exceeds maximum {PMR171_MAX_CHANNELS - 1} (got {index})"
    
    return True, None


def validate_pmr171_frequency(freq_hz: int) -> tuple:
    """Validate frequency value for PMR-171 protocol
    
    Args:
        freq_hz: Frequency in Hz
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if freq_hz < PMR171_MIN_FREQUENCY_HZ:
        return False, f"Frequency below minimum {PMR171_MIN_FREQUENCY_HZ / 1_000_000:.3f} MHz"
    
    if freq_hz > PMR171_MAX_FREQUENCY_HZ:
        return False, f"Frequency exceeds maximum {PMR171_MAX_FREQUENCY_HZ / 1_000_000:.0f} MHz"
    
    return True, None


def ctcss_index_to_hz(index: int) -> float:
    """Convert CTCSS index to frequency in Hz
    
    Args:
        index: CTCSS tone index (0-55)
        
    Returns:
        Frequency in Hz, or None if index is 0 or invalid
    """
    return PMR171_CTCSS_TONES.get(index, None)


def ctcss_hz_to_index(freq_hz: float) -> int:
    """Convert CTCSS frequency to index
    
    Args:
        freq_hz: CTCSS frequency in Hz
        
    Returns:
        Index (0-55), or 0 if no matching tone found
    """
    if freq_hz is None or freq_hz == 0:
        return 0
    
    # Find closest matching tone
    for idx, tone in PMR171_CTCSS_TONES.items():
        if tone is not None and abs(tone - freq_hz) < 0.1:
            return idx
    
    return 0  # No match found


def truncate_channel_name(name: str, max_length: int = PMR171_MAX_CHANNEL_NAME_LENGTH) -> str:
    """Truncate channel name to fit PMR-171 protocol limit
    
    Forces channel name to fit within protocol constraints.
    
    Args:
        name: Channel name string
        max_length: Maximum characters (default: 11)
        
    Returns:
        Truncated name, stripped and ASCII-safe
    """
    if name is None:
        return ""
    
    # Strip null terminators and whitespace
    clean_name = name.rstrip('\u0000').strip()
    
    # Replace non-ASCII characters with '?'
    ascii_name = ""
    for c in clean_name:
        try:
            c.encode('ascii')
            ascii_name += c
        except UnicodeEncodeError:
            ascii_name += '?'
    
    # Truncate to max length
    return ascii_name[:max_length]


def format_channel_name_for_storage(name: str) -> str:
    """Format channel name for storage in PMR-171 format
    
    Truncates to 11 chars, pads to 12 bytes with null terminator.
    
    Args:
        name: Channel name string
        
    Returns:
        16-character string with null padding (PMR-171 storage format)
    """
    truncated = truncate_channel_name(name)
    # Pad to 16 chars with nulls for storage (per PMR-171 internal format)
    return truncated.ljust(16, '\u0000')[:16]


def is_valid_frequency(freq_mhz: float, strict: bool = True) -> bool:
    """Check if frequency is in valid amateur/commercial radio bands
    
    Args:
        freq_mhz: Frequency in MHz
        strict: If True, only allow common amateur/commercial ranges (recommended for handheld radios)
        
    Returns:
        True if frequency is valid
    
    TODO: Review overlapping frequency ranges in broad mode validation.
          Some bands overlap (e.g., shortwave broadcast overlaps with amateur HF bands,
          commercial UHF overlaps with amateur 70cm). This works for now but may need
          refinement if precise band identification becomes critical.
    """
    if strict:
        # Strict ranges for typical handheld/mobile transceivers (UV-5R, UV-82, etc.)
        return (
            (136.000 <= freq_mhz <= 174.000) or      # VHF (2m + commercial)
            (216.000 <= freq_mhz <= 225.000) or      # 1.25m band
            (400.000 <= freq_mhz <= 520.000)         # UHF (70cm + commercial)
        )
    else:
        # Broader ranges including HF, VHF, UHF, and SHF amateur and commercial allocations
        return (
            # LF/MF Amateur
            (0.1357 <= freq_mhz <= 0.1378) or        # 2200m
            (0.472 <= freq_mhz <= 0.479) or          # 630m
            # HF Amateur Bands
            (1.800 <= freq_mhz <= 2.000) or          # 160m
            (3.500 <= freq_mhz <= 4.000) or          # 80m
            (5.330 <= freq_mhz <= 5.405) or          # 60m
            (7.000 <= freq_mhz <= 7.300) or          # 40m
            (10.100 <= freq_mhz <= 10.150) or        # 30m
            (14.000 <= freq_mhz <= 14.350) or        # 20m
            (18.068 <= freq_mhz <= 18.168) or        # 17m
            (21.000 <= freq_mhz <= 21.450) or        # 15m
            (24.890 <= freq_mhz <= 24.990) or        # 12m
            (26.960 <= freq_mhz <= 27.410) or        # CB / 11m
            (28.000 <= freq_mhz <= 29.700) or        # 10m
            # Shortwave Broadcast
            (2.300 <= freq_mhz <= 26.100) or         # SW Broadcast
            # VHF
            (30.000 <= freq_mhz <= 50.000) or        # VHF Low
            (50.000 <= freq_mhz <= 54.000) or        # 6m
            (88.000 <= freq_mhz <= 108.000) or       # FM Broadcast
            (108.000 <= freq_mhz <= 137.000) or      # Aviation
            (137.000 <= freq_mhz <= 138.000) or      # Weather Satellite
            (144.000 <= freq_mhz <= 174.000) or      # 2m + VHF High
            (174.000 <= freq_mhz <= 225.000) or      # VHF TV/1.25m
            # UHF
            (400.000 <= freq_mhz <= 512.000) or      # 70cm + UHF Business/TV
            (512.000 <= freq_mhz <= 698.000) or      # UHF TV (reallocated)
            (698.000 <= freq_mhz <= 960.000) or      # 700/800/900 MHz
            (902.000 <= freq_mhz <= 928.000) or      # 33cm
            (1215.000 <= freq_mhz <= 1300.000) or    # GPS/23cm
            (1452.000 <= freq_mhz <= 1660.000) or    # L-Band
            # SHF
            (2300.000 <= freq_mhz <= 2500.000) or    # 13cm/2.4GHz ISM
            (2700.000 <= freq_mhz <= 2900.000) or    # S-Band
            (3300.000 <= freq_mhz <= 3500.000) or    # 9cm
            (5650.000 <= freq_mhz <= 5925.000) or    # 5cm/5.8GHz ISM
            (10000.000 <= freq_mhz <= 10500.000) or  # 3cm
            (24000.000 <= freq_mhz <= 24250.000)     # 1.2cm and higher
        )


def is_chirp_metadata(chunk: bytes, name: str) -> bool:
    """Detect CHIRP metadata channels
    
    CHIRP embeds metadata as fake channels at the end of the file,
    containing base64-encoded JSON with radio model, version, etc.
    
    Args:
        chunk: 32-byte channel data chunk
        name: Decoded channel name
        
    Returns:
        True if this appears to be CHIRP metadata
    """
    # Check for CHIRP signature markers
    if b'chirp' in chunk or b'img\x00' in chunk:
        return True
    
    # Check for base64-like names (CHIRP stores metadata this way)
    if name and len(name) >= 6:
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        name_chars = set(name)
        if len(name_chars - base64_chars) == 0 and not any(c.isspace() for c in name):
            # All base64 chars, no spaces - likely metadata
            return True
    
    return False


def is_corrupted_channel(chunk: bytes, name: str, rx_freq: float) -> bool:
    """Detect corrupted/invalid channel data
    
    Args:
        chunk: 32-byte channel data chunk
        name: Decoded channel name
        rx_freq: Decoded RX frequency in MHz
        
    Returns:
        True if channel appears corrupted
    """
    # Empty slot (all FF bytes)
    if all(b == 0xff for b in chunk):
        return True
    
    # Channels with replacement characters (encoding errors)
    if '�' in name:
        return True
    
    # Too short name (likely corrupted)
    if name and len(name.strip()) < 2:
        return True
    
    # Check printable ASCII ratio
    if name:
        printable_count = sum(1 for c in name if c.isprintable() and c != '�' and ord(c) >= 32)
        if len(name) > 0 and printable_count < len(name) * 0.5:
            return True
    
    # Suspicious repetitive frequencies (like 165.165165)
    freq_str = f"{rx_freq:.6f}"
    if freq_str.count(freq_str[0:3]) >= 2:  # Same 3 digits repeat
        return True
    
    return False


def get_frequency_band_name(freq_mhz: float) -> str:
    """Get the name of the frequency band with detailed amateur and commercial allocations
    
    Args:
        freq_mhz: Frequency in MHz
        
    Returns:
        Band name string
    """
    # Very Low Frequency (VLF) - Submarine Communications
    if 0.0001 <= freq_mhz < 0.0095:
        return "VLF (Unallocated/Submarine)"
    
    # Low Frequency (LF)
    elif 0.1357 <= freq_mhz <= 0.1378:
        return "2200m Amateur (LF)"
    elif 0.415 <= freq_mhz <= 0.525:
        return "600m (AM Broadcast)"
    elif 0.472 <= freq_mhz <= 0.479:
        return "630m Amateur (MF)"
    elif 0.510 <= freq_mhz <= 1.710:
        return "AM Broadcast (Medium Wave)"
    
    # High Frequency (HF) - Amateur Bands
    elif 1.800 <= freq_mhz <= 2.000:
        return "160m Amateur (HF)"
    elif 3.500 <= freq_mhz <= 4.000:
        return "80m Amateur (HF)"
    elif 5.330 <= freq_mhz <= 5.405:
        return "60m Amateur (HF)"
    elif 7.000 <= freq_mhz <= 7.300:
        return "40m Amateur (HF)"
    elif 10.100 <= freq_mhz <= 10.150:
        return "30m Amateur (HF)"
    elif 14.000 <= freq_mhz <= 14.350:
        return "20m Amateur (HF)"
    elif 18.068 <= freq_mhz <= 18.168:
        return "17m Amateur (HF)"
    elif 21.000 <= freq_mhz <= 21.450:
        return "15m Amateur (HF)"
    elif 24.890 <= freq_mhz <= 24.990:
        return "12m Amateur (HF)"
    elif 26.960 <= freq_mhz <= 27.410:
        return "CB / 11m (27 MHz)"
    elif 28.000 <= freq_mhz <= 29.700:
        return "10m Amateur (HF)"
    
    # Shortwave Broadcast
    elif 2.300 <= freq_mhz <= 26.100:
        return "Shortwave Broadcast (HF)"
    
    # VHF Low
    elif 30.000 <= freq_mhz <= 50.000:
        return "VHF Low (Government/Commercial)"
    
    # 6 Meters
    elif 50.000 <= freq_mhz <= 54.000:
        return "6m Amateur (VHF)"
    
    # VHF Mid
    elif 54.000 <= freq_mhz <= 72.000:
        return "VHF TV Ch 2-4 (Reallocated)"
    elif 76.000 <= freq_mhz <= 88.000:
        return "VHF TV Ch 5-6 (Reallocated)"
    elif 88.000 <= freq_mhz <= 108.000:
        return "FM Broadcast (VHF)"
    elif 108.000 <= freq_mhz <= 118.000:
        return "Aviation VOR/ILS (VHF)"
    elif 118.000 <= freq_mhz <= 137.000:
        return "Airband Voice (VHF)"
    
    # Weather Satellites
    elif 137.000 <= freq_mhz <= 138.000:
        return "Weather Satellite (VHF)"
    
    # 2 Meters
    elif 144.000 <= freq_mhz <= 148.000:
        return "2m Amateur (VHF)"
    
    # VHF High
    elif 148.000 <= freq_mhz <= 174.000:
        return "VHF High (Government/Commercial)"
    elif 174.000 <= freq_mhz <= 216.000:
        return "VHF TV Ch 7-13 (Reallocated)"
    
    # 1.25 Meters
    elif 219.000 <= freq_mhz <= 225.000:
        return "1.25m Amateur (VHF)"
    
    # UHF Low
    elif 225.000 <= freq_mhz <= 400.000:
        return "UHF Government/Military"
    
    # 70 Centimeters
    elif 420.000 <= freq_mhz <= 450.000:
        return "70cm Amateur (UHF)"
    
    # UHF Mid - Land Mobile/Public Safety
    elif 450.000 <= freq_mhz <= 470.000:
        return "UHF Business/Public Safety"
    elif 470.000 <= freq_mhz <= 512.000:
        return "UHF TV Ch 14-20 (Reallocated)"
    elif 512.000 <= freq_mhz <= 608.000:
        return "UHF TV Ch 21-36 (Reallocated)"
    elif 608.000 <= freq_mhz <= 614.000:
        return "UHF (Radio Astronomy)"
    elif 614.000 <= freq_mhz <= 698.000:
        return "UHF TV Ch 38-51 (Reallocated)"
    
    # 700 MHz Public Safety & LTE
    elif 698.000 <= freq_mhz <= 806.000:
        return "700 MHz (LTE/Public Safety)"
    elif 806.000 <= freq_mhz <= 824.000:
        return "800 MHz (Public Safety TX)"
    elif 824.000 <= freq_mhz <= 849.000:
        return "Cellular (UHF)"
    elif 851.000 <= freq_mhz <= 869.000:
        return "800 MHz (Public Safety RX)"
    elif 869.000 <= freq_mhz <= 896.000:
        return "Cellular (UHF)"
    
    # 33 Centimeters
    elif 902.000 <= freq_mhz <= 928.000:
        return "33cm Amateur (UHF)"
    
    # Paging & Misc UHF
    elif 929.000 <= freq_mhz <= 960.000:
        return "Paging/Mobile (UHF)"
    
    # 23 Centimeters
    elif 1240.000 <= freq_mhz <= 1300.000:
        return "23cm Amateur (UHF)"
    
    # GPS & GNSS
    elif 1215.000 <= freq_mhz <= 1240.000:
        return "GPS/GNSS L2 (Navigation)"
    elif 1559.000 <= freq_mhz <= 1610.000:
        return "GPS/GNSS L1 (Navigation)"
    
    # L-Band Satellites
    elif 1452.000 <= freq_mhz <= 1492.000:
        return "L-Band (Digital Audio)"
    elif 1525.000 <= freq_mhz <= 1559.000:
        return "L-Band (Mobile Satellite)"
    elif 1610.000 <= freq_mhz <= 1660.000:
        return "L-Band (Iridium/Mobile Sat)"
    
    # 13 Centimeters
    elif 2300.000 <= freq_mhz <= 2310.000:
        return "13cm Amateur Part 1 (SHF)"
    elif 2390.000 <= freq_mhz <= 2450.000:
        return "13cm Amateur Part 2 (SHF)"
    
    # ISM 2.4 GHz
    elif 2400.000 <= freq_mhz <= 2500.000:
        return "2.4 GHz ISM (WiFi)"
    
    # S-Band
    elif 2700.000 <= freq_mhz <= 2900.000:
        return "S-Band (Radar/Weather)"
    
    # 9 Centimeters
    elif 3300.000 <= freq_mhz <= 3500.000:
        return "9cm Amateur (SHF)"
    
    # 5 Centimeters
    elif 5650.000 <= freq_mhz <= 5925.000:
        return "5cm Amateur (SHF)"
    
    # ISM 5.8 GHz
    elif 5725.000 <= freq_mhz <= 5875.000:
        return "5.8 GHz ISM (WiFi)"
    
    # 3 Centimeters
    elif 10000.000 <= freq_mhz <= 10500.000:
        return "3cm Amateur (SHF)"
    
    # X-Band
    elif 8000.000 <= freq_mhz <= 12000.000:
        return "X-Band (Radar/Satellite)"
    
    # Ku-Band
    elif 12000.000 <= freq_mhz <= 18000.000:
        return "Ku-Band (Satellite)"
    
    # K/Ka-Band
    elif 18000.000 <= freq_mhz <= 40000.000:
        return "K/Ka-Band (Satellite)"
    
    # Above 24 GHz - Various Amateur Allocations
    elif freq_mhz >= 24000.000:
        return "Millimeter Wave (24+ GHz)"
    
    else:
        return "Out of Band"


def is_valid_ctcss_tone(tone_value: int) -> bool:
    """Check if CTCSS tone value is valid
    
    Args:
        tone_value: Raw CTCSS tone value from radio (1000+ = CTCSS in tenths of Hz)
        
    Returns:
        True if valid CTCSS tone
    """
    if tone_value == 0:
        return True  # Off is valid
    
    if tone_value < 1000:
        return False  # Not a CTCSS tone (might be DCS)
    
    # Standard CTCSS tones (in tenths of Hz)
    valid_tones = [
        670, 719, 744, 770, 797, 825, 854, 885, 915,
        948, 974, 1000, 1035, 1072, 1109, 1148, 1188,
        1230, 1273, 1318, 1365, 1413, 1462, 1514, 1567,
        1622, 1679, 1738, 1799, 1862, 1928, 2035, 2107,
        2181, 2257, 2336, 2418, 2503
    ]
    
    return tone_value in valid_tones


def is_valid_dcs_code(code_value: int) -> bool:
    """Check if DCS code is valid
    
    Args:
        code_value: Raw DCS code value (1-511 for standard DCS)
        
    Returns:
        True if valid DCS code
    """
    if code_value == 0:
        return True  # Off is valid
    
    if code_value >= 1000:
        return False  # This is CTCSS, not DCS
    
    # Standard DCS codes
    valid_codes = [
        23, 25, 26, 31, 32, 36, 43, 47, 51, 53,
        54, 65, 71, 72, 73, 74, 114, 115, 116, 122,
        125, 131, 132, 134, 143, 145, 152, 155, 156, 162,
        165, 172, 174, 205, 212, 223, 225, 226, 243, 244,
        245, 246, 251, 252, 255, 261, 263, 265, 266, 271,
        274, 306, 311, 315, 325, 331, 332, 343, 346, 351,
        356, 364, 365, 371, 411, 412, 413, 423, 431, 432,
        445, 446, 452, 454, 455, 462, 464, 465, 466, 503,
        506, 516, 523, 526, 532, 546, 565, 606, 612, 624,
        627, 631, 632, 654, 662, 664, 703, 712, 723, 731,
        732, 734, 743, 754
    ]
    
    return code_value in valid_codes


def validate_channel(channel_data: dict) -> list:
    """Validate a channel against PMR-171 protocol constraints
    
    Validates all channel fields based on protocol specifications from UART analysis.
    
    Args:
        channel_data: PMR-171 channel data dictionary
        
    Returns:
        List of warning strings (empty if valid)
    """
    warnings = []
    
    import struct
    
    # === PMR-171 Protocol Validation ===
    
    # 1. Validate channel name (max 11 chars ASCII)
    channel_name = channel_data.get('channelName', '')
    is_valid, error = validate_pmr171_channel_name(channel_name)
    if not is_valid:
        warnings.append(f"Channel name: {error}")
    
    # 2. Validate channel index (0-999)
    channel_index = channel_data.get('channelLow', 0)
    is_valid, error = validate_pmr171_channel_index(channel_index)
    if not is_valid:
        warnings.append(f"Channel index: {error}")
    
    # 3. Validate mode (0-8 or 255)
    mode = channel_data.get('vfoaMode', 6)
    is_valid, error = validate_pmr171_mode(mode)
    if not is_valid:
        warnings.append(f"Mode: {error}")
    
    # 4. Validate RX frequency
    rx_freq_hz = (
        (channel_data.get('vfoaFrequency1', 0) << 24) |
        (channel_data.get('vfoaFrequency2', 0) << 16) |
        (channel_data.get('vfoaFrequency3', 0) << 8) |
        channel_data.get('vfoaFrequency4', 0)
    )
    rx_freq_mhz = rx_freq_hz / 1_000_000
    
    is_valid, error = validate_pmr171_frequency(rx_freq_hz)
    if not is_valid:
        warnings.append(f"RX Frequency: {error}")
    elif not is_valid_frequency(rx_freq_mhz, strict=False):
        band_name = get_frequency_band_name(rx_freq_mhz)
        warnings.append(f"RX frequency {rx_freq_mhz:.6f} MHz may be out of amateur/commercial bands ({band_name})")
    
    # 5. Validate TX frequency
    tx_freq_hz = (
        (channel_data.get('vfobFrequency1', 0) << 24) |
        (channel_data.get('vfobFrequency2', 0) << 16) |
        (channel_data.get('vfobFrequency3', 0) << 8) |
        channel_data.get('vfobFrequency4', 0)
    )
    tx_freq_mhz = tx_freq_hz / 1_000_000
    
    is_valid, error = validate_pmr171_frequency(tx_freq_hz)
    if not is_valid:
        warnings.append(f"TX Frequency: {error}")
    elif not is_valid_frequency(tx_freq_mhz, strict=False):
        band_name = get_frequency_band_name(tx_freq_mhz)
        warnings.append(f"TX frequency {tx_freq_mhz:.6f} MHz may be out of amateur/commercial bands ({band_name})")
    
    # 6. Validate RX CTCSS index (0-55 for PMR-171 protocol)
    rx_ctcss_index = channel_data.get('rxCtcss', 0)
    # Check if using protocol index format (0-55)
    if rx_ctcss_index <= PMR171_CTCSS_MAX_INDEX:
        is_valid, error = validate_pmr171_ctcss_index(rx_ctcss_index)
        if not is_valid:
            warnings.append(f"RX CTCSS: {error}")
    else:
        # Legacy format (tone value in tenths of Hz)
        if rx_ctcss_index >= 1000 and not is_valid_ctcss_tone(rx_ctcss_index):
            warnings.append(f"RX CTCSS tone {rx_ctcss_index/10:.1f} Hz is not standard")
        elif rx_ctcss_index > 0 and rx_ctcss_index < 1000 and not is_valid_dcs_code(rx_ctcss_index):
            warnings.append(f"RX DCS code {rx_ctcss_index} is not standard")
    
    # 7. Validate TX CTCSS index (0-55 for PMR-171 protocol)
    tx_ctcss_index = channel_data.get('txCtcss', rx_ctcss_index)
    if tx_ctcss_index <= PMR171_CTCSS_MAX_INDEX:
        is_valid, error = validate_pmr171_ctcss_index(tx_ctcss_index)
        if not is_valid:
            warnings.append(f"TX CTCSS: {error}")
    else:
        # Legacy format
        if tx_ctcss_index >= 1000 and not is_valid_ctcss_tone(tx_ctcss_index):
            warnings.append(f"TX CTCSS tone {tx_ctcss_index/10:.1f} Hz is not standard")
        elif tx_ctcss_index > 0 and tx_ctcss_index < 1000 and not is_valid_dcs_code(tx_ctcss_index):
            warnings.append(f"TX DCS code {tx_ctcss_index} is not standard")
    
    return warnings
