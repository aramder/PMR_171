#!/usr/bin/env python3
"""Test entering programming mode before reading channels"""

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


def send_and_receive(ser, packet: bytes, name: str) -> bytes:
    """Send packet, wait, and receive all data"""
    print(f"\n{name}:")
    print(f"  TX ({len(packet)}): {packet.hex()}")
    
    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()
    time.sleep(0.15)
    
    rx = ser.read(200)
    print(f"  RX ({len(rx)}): {rx.hex()[:80]}..." if len(rx) > 40 else f"  RX ({len(rx)}): {rx.hex()}")
    return rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Enter Programming Mode Before Read")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=1)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Try various mode/init commands before reading
    print("\n--- Testing initialization commands ---")
    
    # Command 0x27: Equipment Type Recognition
    pkt = build_packet(0x27, b'')
    send_and_receive(ser, pkt, "Equipment Type (0x27)")
    
    # Command 0x0B: Status Sync
    pkt = build_packet(0x0B, b'\x01')  # Try with payload
    send_and_receive(ser, pkt, "Status Sync (0x0B)")
    
    # Command 0x0A: Mode Setting - try different values
    for mode in [0, 1, 2]:
        pkt = build_packet(0x0A, bytes([mode]))
        send_and_receive(ser, pkt, f"Mode Setting (0x0A) mode={mode}")
    
    # Now try reading channel 50
    print("\n--- Now trying channel read ---")
    data = struct.pack('>H', 50) + b'\x00' * 24
    pkt = build_packet(0x43, data)
    rx = send_and_receive(ser, pkt, "Channel Read (0x43) ch=50")
    
    # Check if response is different from sent packet
    if rx == pkt:
        print("  *** STILL GETTING ECHO ONLY ***")
    elif len(rx) > len(pkt):
        print("  *** GOT MORE DATA - MIGHT HAVE RESPONSE! ***")
    elif len(rx) == 2 * len(pkt):
        print("  *** GOT ECHO + RESPONSE ***")
    
    ser.close()


if __name__ == "__main__":
    main()
