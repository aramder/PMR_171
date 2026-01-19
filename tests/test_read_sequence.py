#!/usr/bin/env python3
"""Test different read sequences"""

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


def send_recv(ser, cmd, data=b'', wait=0.15):
    pkt = build_packet(cmd, data)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    rx = ser.read(100)
    return pkt, rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Read Sequence Variations")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # The 0x44 ch=0 response was:
    # a5a5a5a51d440000010101010000000100000001010000000000500000000001c702
    # After header/len/cmd: 0000 01 01 01010000000100000001010000000000500000000001
    # Byte 0-1: channel 0
    # Byte 2-3: mode rx/tx = 01 01
    # The rest looks like configuration, not frequency
    
    print("\n1. Try reading channel 50 with 2-byte index, then parse as settings:")
    tx, rx = send_recv(ser, 0x44, struct.pack('>H', 50))
    print(f"  TX: {tx.hex()}")
    print(f"  RX: {rx.hex()}")
    if len(rx) >= 34:
        # This might be settings, not channel data
        print(f"  Breakdown:")
        for i, b in enumerate(rx[6:-2]):
            if b != 0:
                print(f"    Byte {i}: {b} (0x{b:02x})")
    
    # Maybe try calling the radio to switch to channel 50 first?
    print("\n2. Try using 0x0C (maybe channel select?):")
    tx, rx = send_recv(ser, 0x0C, struct.pack('>H', 50))
    print(f"  TX: {tx.hex()}")
    print(f"  RX: {rx.hex()}")
    
    # Then read
    tx, rx = send_recv(ser, 0x44, b'')
    print(f"  Then 0x44 empty: {rx.hex()}")
    
    # Try 0x41 - might be channel request
    print("\n3. Try 0x41 variations:")
    for data in [b'', struct.pack('>H', 50), struct.pack('>H', 50) + b'\x01']:
        tx, rx = send_recv(ser, 0x41, data)
        print(f"  0x41 data={data.hex() if data else 'empty'}: RX={rx.hex()[:60]}...")
    
    # Try to request "all channels" with 0xFFFF
    print("\n4. Try 0x43 with 0xFFFF (all channels?):")
    tx, rx = send_recv(ser, 0x43, b'\xff\xff')
    print(f"  TX: {tx.hex()}")
    print(f"  RX: {rx.hex()}")
    
    # Try 0x45 variations
    print("\n5. Try 0x45:")
    for data in [b'', struct.pack('>H', 50)]:
        tx, rx = send_recv(ser, 0x45, data)
        label = data.hex() if data else 'empty'
        print(f"  0x45 data={label}: RX={rx.hex()}")
    
    ser.close()


if __name__ == "__main__":
    main()
