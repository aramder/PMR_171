#!/usr/bin/env python3
"""Try to discover the correct read command/sequence"""

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


def send_recv(ser, cmd, data=b'', wait=0.2, label=''):
    pkt = build_packet(cmd, data)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    rx = ser.read(100)
    
    # Check if response differs from request
    is_echo = (rx == pkt) or (len(rx) > 0 and rx.hex() == pkt.hex()[:len(rx.hex())])
    
    if label:
        status = "ECHO" if is_echo else "RESPONSE"
        print(f"{label}: {status}")
        print(f"  TX: {pkt.hex()}")
        print(f"  RX: {rx.hex()}")
    return rx, is_echo


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Discovery: Find the Read Command")
    print(f"="*60)
    print(f"\nRadio shows: TestCh50 at 146.520 MHz")
    print(f"We need to find how to READ this data back.\n")
    
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    ch = 50  # Channel we know has data
    
    # Try different commands that might be "read"
    print("="*60)
    print("Testing different commands around 0x40-0x4F:")
    print("="*60)
    
    for cmd in range(0x40, 0x50):
        time.sleep(0.1)
        # Just send channel index
        rx, is_echo = send_recv(ser, cmd, struct.pack('>H', ch), wait=0.15)
        
        if len(rx) >= 34 and not is_echo:
            # Parse and check for frequency data
            if len(rx) > 14:
                freq = struct.unpack('>I', rx[10:14])[0]
                if freq > 0:
                    print(f"\n*** CMD 0x{cmd:02X} returned freq {freq/1e6:.6f} MHz! ***")
                    print(f"  Full response: {rx.hex()}")
                else:
                    print(f"CMD 0x{cmd:02X}: Response but freq=0")
        elif not is_echo and len(rx) > 0:
            print(f"CMD 0x{cmd:02X}: Got {len(rx)} bytes (non-echo): {rx.hex()[:40]}")
    
    # Try commands in 0x80-0x8F range (sometimes read commands are offset)
    print("\n" + "="*60)
    print("Testing commands 0x80-0x8F:")
    print("="*60)
    
    for cmd in range(0x80, 0x90):
        time.sleep(0.1)
        rx, is_echo = send_recv(ser, cmd, struct.pack('>H', ch), wait=0.15)
        
        if len(rx) > 10 and not is_echo:
            freq = struct.unpack('>I', rx[10:14])[0] if len(rx) > 14 else 0
            if freq > 0:
                print(f"\n*** CMD 0x{cmd:02X} returned freq {freq/1e6:.6f} MHz! ***")
            else:
                print(f"CMD 0x{cmd:02X}: Got {len(rx)} bytes: {rx.hex()[:40]}")
    
    # Try empty payload
    print("\n" + "="*60)
    print("Testing 0x43/0x44 with empty payload:")
    print("="*60)
    
    rx, _ = send_recv(ser, 0x43, b'', label="0x43 empty")
    rx, _ = send_recv(ser, 0x44, b'', label="0x44 empty")
    
    # Try with 0xFF padding
    print("\n" + "="*60)
    print("Testing with 0xFF padding:")
    print("="*60)
    
    data = struct.pack('>H', ch) + b'\xFF' * 24
    rx, _ = send_recv(ser, 0x43, data, label="0x43 with 0xFF pad")
    
    ser.close()


if __name__ == "__main__":
    main()
