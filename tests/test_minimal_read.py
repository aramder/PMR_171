#!/usr/bin/env python3
"""Test minimal channel read - 2-byte payload works best"""

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


def read_channel_minimal(ser, ch_num):
    """Read channel using minimal 2-byte payload"""
    ser.reset_input_buffer()
    
    pkt = build_packet(0x43, struct.pack('>H', ch_num))
    ser.write(pkt)
    ser.flush()
    time.sleep(0.15)
    
    rx = ser.read(100)
    return rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Minimal Channel Read (2-byte payload)")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Read several channels
    channels_to_test = [0, 1, 2, 3, 40, 50, 51, 52, 60, 61]
    
    for ch in channels_to_test:
        rx = read_channel_minimal(ser, ch)
        
        print(f"\nChannel {ch:3d}:")
        print(f"  Raw ({len(rx)}): {rx.hex()}")
        
        if len(rx) >= 34:
            # Response format analysis
            # Our TX was 10 bytes, RX is 34 bytes
            # Looks like: echo(10) + response_data(22) + crc(2)?
            # Or: full 34-byte response packet
            
            # Skip to data portion - first 10 bytes might be echo
            if rx[:10].hex() == build_packet(0x43, struct.pack('>H', ch)).hex():
                # First 10 bytes = echo, rest is response
                response = rx[10:]
                print(f"  After echo ({len(response)}): {response.hex()}")
            else:
                # Try parsing as complete response
                if rx[:4] == PACKET_HEADER:
                    length = rx[4]
                    cmd = rx[5]
                    payload = rx[6:6+length-3]  # -3 for cmd and crc
                    print(f"  Packet: len={length}, cmd=0x{cmd:02X}")
                    print(f"  Payload ({len(payload)}): {payload.hex()}")
                    
                    if len(payload) >= 14:
                        ch_idx = struct.unpack('>H', payload[0:2])[0]
                        freq = struct.unpack('>I', payload[4:8])[0] if len(payload) >= 8 else 0
                        name = payload[14:26] if len(payload) >= 26 else b''
                        try:
                            name_str = name.split(b'\x00')[0].decode('ascii', errors='replace')
                        except:
                            name_str = ''
                        print(f"  Channel {ch_idx}: {freq/1e6:.6f} MHz, name='{name_str}'")
    
    ser.close()


if __name__ == "__main__":
    main()
