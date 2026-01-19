#!/usr/bin/env python3
"""
Analyze UART captures to find the connection/handshake sequence.

The manufacturer software has a connect/disconnect button. The UART captures
should show what commands are sent at the start of a session.
"""

import sys
import struct
from pathlib import Path

# Protocol constants
PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])
SPECTRUM_HEADER = bytes([0x7E, 0x7E, 0x7E, 0x7E])

# Known commands
COMMANDS = {
    0x07: "PTT Control",
    0x0A: "Mode Setting",
    0x0B: "Status Synchronization",
    0x27: "Equipment Type Recognition",
    0x28: "Power Class",
    0x29: "RIT Setting",
    0x39: "Spectrum Data Request",
    0x40: "Channel Write",
    0x43: "Channel Read",
}


def find_all_packets(data: bytes) -> list:
    """Find all valid packets in raw data"""
    packets = []
    pos = 0
    
    while pos < len(data):
        # Find next header
        idx = data.find(PACKET_HEADER, pos)
        if idx == -1:
            break
        
        # Check if we have enough bytes for minimal packet
        if idx + 8 > len(data):
            break
        
        length = data[idx + 4]
        
        # Sanity check length
        if length < 3 or length > 250:
            pos = idx + 1
            continue
        
        packet_size = 4 + 1 + length  # header + length byte + (cmd + data + crc)
        
        if idx + packet_size > len(data):
            break
        
        packet = data[idx:idx + packet_size]
        command = packet[5]
        payload = packet[6:-2]
        
        packets.append({
            'position': idx,
            'raw': packet,
            'length': length,
            'command': command,
            'command_name': COMMANDS.get(command, f"Unknown (0x{command:02X})"),
            'payload': payload,
        })
        
        pos = idx + packet_size
    
    return packets


def analyze_spm_file(filepath: Path):
    """Analyze an .spm file for packets"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {filepath.name}")
    print(f"{'='*70}")
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Find all packets
    packets = find_all_packets(data)
    print(f"Found {len(packets)} packets")
    
    if not packets:
        print("No packets found!")
        return []
    
    # Show first 20 packets (likely includes connection sequence)
    print("\n=== First 20 Packets (Connection Sequence?) ===")
    for i, pkt in enumerate(packets[:20]):
        cmd = pkt['command']
        name = pkt['command_name']
        payload_hex = pkt['payload'].hex() if pkt['payload'] else "(empty)"
        
        # For channel commands, decode channel number
        extra = ""
        if cmd == 0x40 or cmd == 0x43:  # Channel write/read
            if len(pkt['payload']) >= 2:
                ch_idx = struct.unpack('>H', pkt['payload'][:2])[0]
                extra = f" [Channel {ch_idx}]"
        
        print(f"  [{i:3d}] @{pkt['position']:6d}: {name:30s}{extra}")
        if len(payload_hex) <= 60:
            print(f"         Payload: {payload_hex}")
        else:
            print(f"         Payload: {payload_hex[:60]}...")
    
    # Analyze command distribution
    cmd_counts = {}
    for pkt in packets:
        cmd = pkt['command']
        cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
    
    print("\n=== Command Distribution ===")
    for cmd, count in sorted(cmd_counts.items()):
        name = COMMANDS.get(cmd, "Unknown")
        print(f"  0x{cmd:02X} ({name}): {count}")
    
    # Look for non-channel commands at the start (likely connection sequence)
    print("\n=== Non-Channel Commands (Possible Init Sequence) ===")
    for i, pkt in enumerate(packets):
        cmd = pkt['command']
        if cmd not in (0x40, 0x43):  # Not channel read/write
            print(f"  [{i:3d}] @{pkt['position']:6d}: 0x{cmd:02X} {pkt['command_name']}")
            print(f"         Raw: {pkt['raw'].hex()}")
            if i > 50:
                print("  ... (stopping at 50)")
                break
    
    return packets


def main():
    results_dir = Path("tests/test_configs/Results")
    
    # Analyze upload captures (most likely to have connect sequence)
    spm_files = sorted(results_dir.glob("*_upload_uart_monitor.spm"))
    
    if not spm_files:
        print("No upload UART monitor files found!")
        return 1
    
    print("="*70)
    print("UART Capture Analysis - Looking for Connection Sequence")
    print("="*70)
    
    # Analyze the first upload file
    all_packets = []
    for spm_file in spm_files[:3]:  # Analyze first 3
        packets = analyze_spm_file(spm_file)
        all_packets.extend(packets)
    
    # Also check readback files
    print("\n\n" + "="*70)
    print("Also checking readback files...")
    print("="*70)
    
    readback_files = sorted(results_dir.glob("*_readback*.spm"))
    for spm_file in readback_files[:2]:  # First 2 readback files
        analyze_spm_file(spm_file)
    
    # Summary
    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Look for the FIRST few packets in each capture. These should be the
connection handshake before channel read/write operations begin.

Common patterns to look for:
- Equipment Type (0x27) - query device ID
- Status Sync (0x0B) - get current radio state  
- Mode Setting (0x0A) - prepare radio for programming

The connection sequence might also include:
- A specific "enter programming mode" command
- A handshake with specific data bytes
- DTR/RTS control (not visible in packet data)
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
