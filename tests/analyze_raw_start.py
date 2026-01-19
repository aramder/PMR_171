#!/usr/bin/env python3
"""
Analyze what's at the START of the UART captures BEFORE the first protocol packet.
This might reveal the connection handshake.
"""

import sys
from pathlib import Path

PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])


def analyze_start(filepath: Path):
    """Look at the data before the first packet header"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {filepath.name}")
    print(f"{'='*70}")
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Find first packet header
    first_header = data.find(PACKET_HEADER)
    
    print(f"File size: {len(data)} bytes")
    print(f"First packet header at position: {first_header}")
    
    if first_header == -1:
        print("No packet headers found!")
        return
    
    print(f"\n=== Data BEFORE first packet ({first_header} bytes) ===")
    
    # Show first 500 bytes
    pre_data = data[:first_header]
    
    # Try to find patterns in the pre-header data
    print(f"\n--- First 200 bytes (hex) ---")
    hex_dump(pre_data[:200])
    
    print(f"\n--- Last 200 bytes before packet (hex) ---")
    if first_header > 200:
        hex_dump(pre_data[-200:])
    else:
        print("(already shown above)")
    
    # Look for text strings (SPM file metadata)
    print(f"\n--- Looking for text strings ---")
    find_strings(pre_data)
    
    # Look for any 0xA5 bytes that might be partial headers
    print(f"\n--- 0xA5 bytes in pre-header data ---")
    a5_positions = [i for i, b in enumerate(pre_data) if b == 0xA5]
    print(f"Found {len(a5_positions)} instances of 0xA5")
    if a5_positions:
        print(f"Positions (first 20): {a5_positions[:20]}")
    
    # Look for other patterns
    print(f"\n--- Looking for potential command patterns ---")
    
    # Check if there are any bytes that look like commands
    for pattern in [b'\x27', b'\x0b', b'\x0a', b'\x07']:
        count = pre_data.count(pattern)
        if count > 0:
            positions = []
            pos = 0
            while True:
                pos = pre_data.find(pattern, pos)
                if pos == -1:
                    break
                positions.append(pos)
                pos += 1
            print(f"Pattern 0x{pattern[0]:02X}: {count} occurrences at {positions[:10]}")


def hex_dump(data: bytes, width: int = 16):
    """Print hex dump of data"""
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        # Try to show ASCII representation
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {i:06X}: {hex_str:<48s} | {ascii_str}")


def find_strings(data: bytes, min_length: int = 4):
    """Find printable ASCII strings in binary data"""
    strings = []
    current = []
    
    for i, b in enumerate(data):
        if 32 <= b < 127:
            current.append(chr(b))
        else:
            if len(current) >= min_length:
                strings.append((i - len(current), ''.join(current)))
            current = []
    
    if len(current) >= min_length:
        strings.append((len(data) - len(current), ''.join(current)))
    
    for pos, s in strings[:20]:
        print(f"  @{pos}: '{s}'")
    
    if len(strings) > 20:
        print(f"  ... and {len(strings) - 20} more strings")


def main():
    results_dir = Path("tests/test_configs/Results")
    
    # Analyze all upload files
    spm_files = list(results_dir.glob("*.spm"))
    
    if not spm_files:
        print("No .spm files found!")
        return 1
    
    print("="*70)
    print("Raw Start Analysis - Looking for Pre-Packet Data")
    print("="*70)
    
    for spm_file in sorted(spm_files)[:5]:  # First 5 files
        analyze_start(spm_file)
    
    print("\n\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
If the pre-packet data is .spm file metadata, then the protocol
packets are the ONLY serial data captured.

This means the connection is likely handled through:
1. DTR/RTS hardware flow control signals
2. Simply opening the serial port (radio auto-detects)
3. USB device enumeration/driver handshake

Try experimenting with DTR/RTS settings when opening the port:
- ser.dtr = True/False
- ser.rts = True/False
- Different combinations and timing
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
