#!/usr/bin/env python3
"""Analyze UART logs to understand the read protocol"""

import struct
from pathlib import Path

PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])


def extract_packets(data):
    """Extract all valid packets from binary data"""
    packets = []
    idx = 0
    while idx < len(data) - 10:
        pos = data.find(PACKET_HEADER, idx)
        if pos == -1:
            break
        if pos + 6 > len(data):
            break
        
        length = data[pos + 4]
        cmd = data[pos + 5]
        
        if length >= 3 and length <= 50:
            packet_end = pos + 5 + length
            if packet_end <= len(data):
                packet = data[pos:packet_end]
                packets.append({
                    'pos': pos,
                    'length': length,
                    'cmd': cmd,
                    'data': packet,
                    'payload': packet[6:-2] if len(packet) > 8 else b''
                })
        idx = pos + 1
    return packets


def parse_channel_payload(payload):
    """Parse a 26-byte channel payload"""
    if len(payload) < 26:
        return None
    
    return {
        'ch_idx': struct.unpack('>H', payload[0:2])[0],
        'rx_mode': payload[2],
        'tx_mode': payload[3],
        'rx_freq': struct.unpack('>I', payload[4:8])[0],
        'tx_freq': struct.unpack('>I', payload[8:12])[0],
        'rx_ctcss': payload[12],
        'tx_ctcss': payload[13],
        'name': payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
    }


def main():
    # Analyze the readback captures
    capture_files = [
        Path('tests/test_configs/Results/07_readback_uart_monitor.spm'),
        Path('tests/test_configs/Results/10_complete_ctcss_mapping_test_readback.spm'),
        Path('tests/test_configs/Results/11_complete_ctcss_validation_readback.spm'),
    ]
    
    for capture_path in capture_files:
        if not capture_path.exists():
            print(f"Skipping {capture_path.name} - not found")
            continue
        
        print(f"\n{'='*60}")
        print(f"Analyzing: {capture_path.name}")
        print(f"{'='*60}")
        
        data = capture_path.read_bytes()
        packets = extract_packets(data)
        
        # Count by command type
        cmd_counts = {}
        for pkt in packets:
            cmd = pkt['cmd']
            cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
        
        print(f"\nCommand frequency (total {len(packets)} packets):")
        for cmd, count in sorted(cmd_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"  0x{cmd:02X}: {count} packets")
        
        # Look for 0x41 packets specifically
        cmd_41_packets = [p for p in packets if p['cmd'] == 0x41]
        print(f"\n0x41 (potential read) packets: {len(cmd_41_packets)}")
        
        # Show first few 0x41 packets with channel data
        found_with_freq = 0
        for pkt in cmd_41_packets[:20]:
            payload = pkt['payload']
            if len(payload) >= 26:
                ch = parse_channel_payload(payload)
                if ch and ch['rx_freq'] > 0:
                    found_with_freq += 1
                    if found_with_freq <= 5:
                        print(f"  Ch {ch['ch_idx']:3d}: {ch['rx_freq']/1e6:.6f} MHz, name='{ch['name']}'")
        
        print(f"  ... {found_with_freq} packets with frequency data")
        
        # Look for 0x43 packets - what were they used for?
        cmd_43_packets = [p for p in packets if p['cmd'] == 0x43]
        print(f"\n0x43 packets: {len(cmd_43_packets)}")
        if cmd_43_packets:
            # Show first few
            for pkt in cmd_43_packets[:3]:
                payload = pkt['payload']
                if len(payload) >= 26:
                    ch = parse_channel_payload(payload)
                    if ch:
                        freq_str = f"{ch['rx_freq']/1e6:.6f} MHz" if ch['rx_freq'] > 0 else "0"
                        print(f"  Ch {ch['ch_idx']:3d}: {freq_str}, name='{ch['name']}'")
        
        # Look for 0x40 packets (write)
        cmd_40_packets = [p for p in packets if p['cmd'] == 0x40]
        print(f"\n0x40 (write) packets: {len(cmd_40_packets)}")
        if cmd_40_packets:
            for pkt in cmd_40_packets[:3]:
                payload = pkt['payload']
                if len(payload) >= 26:
                    ch = parse_channel_payload(payload)
                    if ch:
                        freq_str = f"{ch['rx_freq']/1e6:.6f} MHz" if ch['rx_freq'] > 0 else "0"
                        print(f"  Ch {ch['ch_idx']:3d}: {freq_str}, name='{ch['name']}'")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
Based on analysis:
- 0x40 = WRITE channel to radio
- 0x41 = READ channel from radio (returns full channel data!)
- 0x43 = May be write echo/acknowledgment

The key discovery: Use 0x41 with channel index to READ!
""")


if __name__ == "__main__":
    main()
