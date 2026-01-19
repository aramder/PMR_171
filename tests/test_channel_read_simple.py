#!/usr/bin/env python3
"""Test simplified channel read - maybe padding is wrong"""

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


def send_and_wait(ser, pkt, name):
    print(f"\n{name}:")
    print(f"  TX ({len(pkt)}): {pkt.hex()}")
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.3)
    rx = ser.read(200)
    print(f"  RX ({len(rx)}): {rx.hex()}")
    return rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Different Channel Read Formats")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    ch = 50  # Known to have data
    
    # Try 1: Just channel index (2 bytes)
    pkt = build_packet(0x43, struct.pack('>H', ch))
    send_and_wait(ser, pkt, f"Ch {ch} - Just index (2 bytes)")
    
    # Try 2: Channel index + minimal padding (4 bytes total)
    pkt = build_packet(0x43, struct.pack('>H', ch) + b'\x00\x00')
    send_and_wait(ser, pkt, f"Ch {ch} - Index + 2 pad (4 bytes)")
    
    # Try 3: Full 26-byte format (current approach)
    pkt = build_packet(0x43, struct.pack('>H', ch) + b'\x00' * 24)
    send_and_wait(ser, pkt, f"Ch {ch} - Full 26 bytes")
    
    # Try 4: Maybe channel read uses a DIFFERENT command?
    # Try 0x42 (one before 0x43)
    pkt = build_packet(0x42, struct.pack('>H', ch))
    send_and_wait(ser, pkt, f"Ch {ch} - Command 0x42")
    
    # Try 5: 0x44 (one after 0x43)
    pkt = build_packet(0x44, struct.pack('>H', ch))
    send_and_wait(ser, pkt, f"Ch {ch} - Command 0x44")
    
    # Try 6: Maybe we need to request ALL channels start?
    # Some radios need a "start read" command first
    pkt = build_packet(0x43, b'\xff\xff')  # Special index?
    send_and_wait(ser, pkt, "Maybe start-read (0xFFFF)")
    
    ser.close()


if __name__ == "__main__":
    main()
