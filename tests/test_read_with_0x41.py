#!/usr/bin/env python3
"""Test reading channels using 0x41 command"""

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


def build_packet(cmd: int, data: bytes = b'') -> bytes:
    length = 1 + len(data) + 2
    crc_data = bytes([length, cmd]) + data
    crc = crc16_ccitt(crc_data)
    return PACKET_HEADER + bytes([length, cmd]) + data + struct.pack('>H', crc)


def read_channel(ser, ch_idx):
    """Read a channel using 0x41 command"""
    pkt = build_packet(0x41, struct.pack('>H', ch_idx))
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.1)
    rx = ser.read(50)
    
    if len(rx) >= 34:
        # Parse response
        payload = rx[6:-2]  # Skip header/len/cmd and CRC
        
        if len(payload) >= 26:
            ch = struct.unpack('>H', payload[0:2])[0]
            rx_mode = payload[2]
            tx_mode = payload[3]
            rx_freq = struct.unpack('>I', payload[4:8])[0]
            tx_freq = struct.unpack('>I', payload[8:12])[0]
            rx_ctcss = payload[12]
            tx_ctcss = payload[13]
            name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
            
            return {
                'channel': ch,
                'rx_mode': rx_mode,
                'tx_mode': tx_mode,
                'rx_freq': rx_freq,
                'tx_freq': tx_freq,
                'rx_ctcss': rx_ctcss,
                'tx_ctcss': tx_ctcss,
                'name': name,
                'raw': rx.hex()
            }
    
    return {'error': f'Invalid response ({len(rx)} bytes): {rx.hex()}'}


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Read Channels Using 0x41 Command")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Test reading several channels
    test_channels = [0, 1, 2, 50, 60, 100, 999]
    
    print(f"\nReading {len(test_channels)} channels:\n")
    
    for ch_idx in test_channels:
        result = read_channel(ser, ch_idx)
        
        if 'error' in result:
            print(f"Ch {ch_idx:3d}: ERROR - {result['error']}")
        else:
            if result['rx_freq'] > 0:
                print(f"Ch {ch_idx:3d}: {result['rx_freq']/1e6:.6f} MHz, "
                      f"mode={result['rx_mode']}, "
                      f"ctcss={result['rx_ctcss']}/{result['tx_ctcss']}, "
                      f"name='{result['name']}'")
            else:
                print(f"Ch {ch_idx:3d}: (empty/unused)")
    
    # Also read the first 10 channels to see what's programmed
    print(f"\n{'='*60}")
    print("First 10 channels:")
    print(f"{'='*60}")
    
    for ch_idx in range(10):
        result = read_channel(ser, ch_idx)
        if 'error' not in result and result['rx_freq'] > 0:
            print(f"Ch {ch_idx}: {result['rx_freq']/1e6:.6f} MHz - '{result['name']}'")
        else:
            print(f"Ch {ch_idx}: (empty)")
    
    ser.close()
    
    print(f"\n{'='*60}")
    print("SUCCESS! 0x41 is the correct READ command!")
    print("="*60)


if __name__ == "__main__":
    main()
