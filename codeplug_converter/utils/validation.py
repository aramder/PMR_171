"""Channel validation utilities"""


def is_valid_frequency(freq_mhz: float, strict: bool = True) -> bool:
    """Check if frequency is in valid amateur/commercial radio bands
    
    Args:
        freq_mhz: Frequency in MHz
        strict: If True, only allow Baofeng UV-5R/UV-82 ranges
        
    Returns:
        True if frequency is valid
    """
    if strict:
        # Strict Baofeng UV-5R/UV-82 ranges
        return (
            (136 <= freq_mhz <= 174) or      # VHF
            (220 <= freq_mhz <= 225) or      # 1.25m band
            (400 <= freq_mhz <= 520)         # UHF
        )
    else:
        # Broader ranges for other radios
        return (
            (118 <= freq_mhz <= 174) or      # Airband + VHF
            (200 <= freq_mhz <= 260) or      # 220 MHz band expanded
            (400 <= freq_mhz <= 520) or      # UHF
            (700 <= freq_mhz <= 985)         # Commercial UHF
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
