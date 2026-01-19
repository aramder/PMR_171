#!/usr/bin/env python3
"""Test skipping echo to read actual response"""

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
    print(f"Test: Skip Echo and Read Actual Response")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Test channel 50 (should have data)
    ch = 50
    packet = build_read_packet(ch)
    
    print(f"\nSending read request for channel {ch}:")
    print(f"  Packet ({len(packet)} bytes): {packet.hex()}")
    
    ser.write(packet)
    ser.flush()
    
    # Wait and read ALL available data
    time.sleep(0.2)
    all_data = ser.read(500)
    
    print(f"\nReceived total {len(all_data)} bytes:")
    print(f"  Data: {all_data.hex()}")
    
    # Find ALL packet headers in response
    print(f"\nPacket analysis:")
    pos = 0
    packet_num = 0
    while pos < len(all_data):
        idx = all_data.find(PACKET_HEADER, pos)
        if idx == -1:
            break
        
        packet_num += 1
        if idx + 5 <= len(all_data):
            length = all_data[idx + 4]
            packet_end = idx + 5 + length
            if packet_end <= len(all_data):
                pkt_data = all_data[idx:packet_end]
                cmd = all_data[idx + 5]
                
                # Parse channel data
                if len(pkt_data) > 32:
                    payload = pkt_data[6:-2]
                    ch_idx = struct.unpack('>H', payload[0:2])[0]
                    freq = struct.unpack('>I', payload[4:8])[0]
                    name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
                    
                    is_echo = (pkt_data == packet)
                    print(f"  Packet {packet_num} @{idx}:")
                    print(f"    Type: {'ECHO' if is_echo else 'RESPONSE'}")
                    print(f"    Channel: {ch_idx}, Freq: {freq/1e6:.6f} MHz")
                    print(f"    Name: '{name}'")
                    print(f"    Raw: {pkt_data.hex()[:60]}...")
        pos = idx + 1
    
    if packet_num == 0:
        print("  No packets found!")
    elif packet_num == 1:
        print(f"\n*** Only 1 packet - either echo only, or radio doesn't send separate response ***")
    else:
        print(f"\n*** Found {packet_num} packets - first might be echo, second is response ***")
    
    ser.close()


if __name__ == "__main__":
    main()
