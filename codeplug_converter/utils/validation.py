"""Channel validation utilities"""


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
    """Validate a channel and return list of warnings
    
    Args:
        channel_data: PMR-171 channel data dictionary
        
    Returns:
        List of warning strings (empty if valid)
    """
    warnings = []
    
    # Import frequency conversion from utils
    import struct
    
    # Validate RX frequency
    rx_freq_bytes = struct.pack('>I', 
        (channel_data.get('vfoaFrequency1', 0) << 24) |
        (channel_data.get('vfoaFrequency2', 0) << 16) |
        (channel_data.get('vfoaFrequency3', 0) << 8) |
        channel_data.get('vfoaFrequency4', 0))
    rx_freq_hz = struct.unpack('>I', rx_freq_bytes)[0]
    rx_freq_mhz = rx_freq_hz / 1_000_000
    
    if not is_valid_frequency(rx_freq_mhz, strict=False):
        band_name = get_frequency_band_name(rx_freq_mhz)
        warnings.append(f"RX frequency {rx_freq_mhz:.6f} MHz is out of valid bands ({band_name})")
    
    # Validate TX frequency
    tx_freq_bytes = struct.pack('>I',
        (channel_data.get('vfobFrequency1', 0) << 24) |
        (channel_data.get('vfobFrequency2', 0) << 16) |
        (channel_data.get('vfobFrequency3', 0) << 8) |
        channel_data.get('vfobFrequency4', 0))
    tx_freq_hz = struct.unpack('>I', tx_freq_bytes)[0]
    tx_freq_mhz = tx_freq_hz / 1_000_000
    
    if not is_valid_frequency(tx_freq_mhz, strict=False):
        band_name = get_frequency_band_name(tx_freq_mhz)
        warnings.append(f"TX frequency {tx_freq_mhz:.6f} MHz is out of valid bands ({band_name})")
    
    # Validate RX CTCSS/DCS
    rx_ctcss = channel_data.get('rxCtcss', 0)
    if rx_ctcss > 0:
        if rx_ctcss >= 1000:
            if not is_valid_ctcss_tone(rx_ctcss):
                warnings.append(f"RX CTCSS tone {rx_ctcss/10:.1f} Hz is not standard")
        else:
            if not is_valid_dcs_code(rx_ctcss):
                warnings.append(f"RX DCS code {rx_ctcss} is not standard")
    
    # Validate TX CTCSS/DCS
    tx_ctcss = channel_data.get('txCtcss', rx_ctcss)
    if tx_ctcss > 0:
        if tx_ctcss >= 1000:
            if not is_valid_ctcss_tone(tx_ctcss):
                warnings.append(f"TX CTCSS tone {tx_ctcss/10:.1f} Hz is not standard")
        else:
            if not is_valid_dcs_code(tx_ctcss):
                warnings.append(f"TX DCS code {tx_ctcss} is not standard")
    
    return warnings
