#!/usr/bin/env python3
"""Test if 0x44 iterates through channels"""

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


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: 0x44 Iterator Pattern")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Send 0x44 with empty payload multiple times
    print("\nSending 0x44 (empty) multiple times to see if it iterates:")
    print("-"*60)
    
    for i in range(10):
        pkt = build_packet(0x44, b'')
        ser.reset_input_buffer()
        ser.write(pkt)
        ser.flush()
        time.sleep(0.1)
        rx = ser.read(50)
        
        if len(rx) >= 34:
            ch_idx = struct.unpack('>H', rx[6:8])[0]
            mode = rx[8]
            freq = struct.unpack('>I', rx[10:14])[0]
            name = rx[20:32].split(b'\x00')[0].decode('ascii', errors='replace')
            
            status = f"{freq/1e6:.6f} MHz" if freq > 0 else "EMPTY"
            print(f"Read {i+1}: Ch {ch_idx:4d} mode={mode} {status:>18} name='{name}'")
        else:
            print(f"Read {i+1}: Got {len(rx)} bytes: {rx.hex()}")
    
    # Now try: Start from channel 0 by sending 0x44 with ch=0 first
    print("\n" + "-"*60)
    print("Try setting read position to ch 0:")
    
    # Send 0x44 with channel 0
    pkt = build_packet(0x44, struct.pack('>H', 0))
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.1)
    rx = ser.read(50)
    print(f"  0x44 ch=0: {rx.hex()}")
    
    # Now send empty 0x44 to see what we get
    print("\nNow sending empty 0x44 to iterate:")
    for i in range(5):
        pkt = build_packet(0x44, b'')
        ser.reset_input_buffer()
        ser.write(pkt)
        ser.flush()
        time.sleep(0.1)
        rx = ser.read(50)
        
        if len(rx) >= 34:
            ch_idx = struct.unpack('>H', rx[6:8])[0]
            freq = struct.unpack('>I', rx[10:14])[0]
            name = rx[20:32].split(b'\x00')[0].decode('ascii', errors='replace')
            status = f"{freq/1e6:.6f} MHz" if freq > 0 else "EMPTY"
            print(f"  Ch {ch_idx:4d}: {status:>18} name='{name}'")
        else:
            print(f"  Got {len(rx)} bytes: {rx.hex()}")
    
    ser.close()


if __name__ == "__main__":
    main()
