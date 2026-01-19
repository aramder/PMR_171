#!/usr/bin/env python3
"""Test reading specific channels that should have data"""

import sys
import time
import struct
import serial

PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        cur = byte << 8
        for _ in range(8):
            if (crc ^ cur) & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
            cur = (cur << 1) & 0xFFFF
    return crc


def build_read_packet(channel: int) -> bytes:
    data = struct.pack('>H', channel) + b'\x00' * 24
    length = 1 + len(data) + 2
    crc_data = bytes([length, 0x43]) + data
    crc = crc16_ccitt(crc_data)
    return PACKET_HEADER + bytes([length, 0x43]) + data + struct.pack('>H', crc)


def read_channel(ser, channel: int) -> dict:
    """Read a single channel and return parsed data"""
    # Send request
    packet = build_read_packet(channel)
    ser.write(packet)
    ser.flush()
    
    # Read response
    header = ser.read(4)
    if len(header) < 4:
        return {'error': 'timeout waiting for header'}
    
    if header != PACKET_HEADER:
        return {'error': f'invalid header: {header.hex()}'}
    
    length_byte = ser.read(1)
    if not length_byte:
        return {'error': 'timeout waiting for length'}
    
    length = length_byte[0]
    remaining = ser.read(length)
    if len(remaining) < length:
        return {'error': f'incomplete data: {len(remaining)}/{length}'}
    
    # Parse response
    cmd = remaining[0]
    data = remaining[1:length-2]
    
    if len(data) < 26:
        return {'error': f'data too short: {len(data)}'}
    
    index = struct.unpack('>H', data[0:2])[0]
    rx_mode = data[2]
    tx_mode = data[3]
    rx_freq = struct.unpack('>I', data[4:8])[0]
    tx_freq = struct.unpack('>I', data[8:12])[0]
    rx_ctcss = data[12]
    tx_ctcss = data[13]
    
    name_bytes = data[14:26]
    try:
        name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')
    except:
        name = ""
    
    return {
        'index': index,
        'rx_mode': rx_mode,
        'tx_mode': tx_mode,
        'rx_freq_mhz': rx_freq / 1_000_000,
        'tx_freq_mhz': tx_freq / 1_000_000,
        'rx_ctcss': rx_ctcss,
        'tx_ctcss': tx_ctcss,
        'name': name,
        'raw_data': data.hex()
    }


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Reading Specific Channels from {port}")
    print(f"="*60)
    
    # Channels to test - based on screenshot these should have data
    test_channels = [0, 1, 2, 3, 40, 50, 51, 52, 53, 54, 55]
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    print(f"\nReading {len(test_channels)} channels...\n")
    
    for ch in test_channels:
        result = read_channel(ser, ch)
        
        if 'error' in result:
            print(f"Ch {ch:3d}: ERROR - {result['error']}")
        else:
            freq = result['rx_freq_mhz']
            name = result['name'] if result['name'] else '(empty)'
            mode = result['rx_mode']
            
            # Flag channels that appear empty but might not be
            if freq == 0:
                status = "EMPTY/0Hz"
            else:
                status = f"{freq:.6f} MHz"
            
            print(f"Ch {ch:3d}: {status:>18s}  mode={mode}  name='{name}'")
            
            # Show raw data for debugging
            if ch in [0, 1, 50, 51]:
                print(f"        Raw: {result['raw_data'][:60]}...")
    
    ser.close()
    print(f"\n{'='*60}")
    print("If channels 0-3 show as empty but should have data,")
    print("the issue may be:")
    print("  1. Wrong channel index in request")
    print("  2. Radio returning wrong channel data")
    print("  3. Data parsing error")
    print("="*60)


if __name__ == "__main__":
    main()
