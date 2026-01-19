#!/usr/bin/env python3
"""Test raw serial response to diagnose sync issues"""

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


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Raw Response Test on {port}")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.3)
    ser.reset_input_buffer()
    
    # Test reading channel 50 (known to have data based on screenshot)
    for ch in [0, 50, 51]:
        print(f"\n--- Reading channel {ch} ---")
        
        # Clear buffer
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        # Send request
        packet = build_read_packet(ch)
        print(f"Sent ({len(packet)} bytes): {packet.hex()}")
        ser.write(packet)
        ser.flush()
        
        # Read all available data with timeout
        time.sleep(0.1)  # Wait for response
        response = ser.read(200)  # Read up to 200 bytes
        print(f"Received ({len(response)} bytes): {response.hex()}")
        
        # Try to find all packet headers in response
        pos = 0
        packet_num = 0
        while pos < len(response):
            idx = response.find(PACKET_HEADER, pos)
            if idx == -1:
                break
            
            packet_num += 1
            if idx + 5 <= len(response):
                length = response[idx + 4]
                packet_end = idx + 5 + length
                if packet_end <= len(response):
                    pkt_data = response[idx:packet_end]
                    cmd = response[idx + 5]
                    print(f"  Packet {packet_num} @{idx}: cmd=0x{cmd:02X}, len={length}, data={pkt_data.hex()}")
                else:
                    print(f"  Packet {packet_num} @{idx}: incomplete (need {packet_end}, have {len(response)})")
            pos = idx + 1
        
        if packet_num == 0:
            print("  No valid packets found!")
        elif packet_num > 1:
            print(f"  *** Found {packet_num} packets - radio may be echoing or double-responding ***")
    
    ser.close()
    print("\n" + "="*60)
    print("Analysis:")
    print("="*60)
    print("""
If you see multiple packets per request:
- First packet might be echo of sent data
- Second packet is the actual response
- Need to skip echo and read response

If first packet looks like sent data, the radio has echo enabled.
""")


if __name__ == "__main__":
    main()
