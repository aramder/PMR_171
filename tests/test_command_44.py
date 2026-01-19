#!/usr/bin/env python3
"""Test command 0x44 - might be the actual read command"""

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


def send_and_receive(ser, pkt, name, wait=0.2):
    print(f"\n{name}:")
    print(f"  TX ({len(pkt)}): {pkt.hex()}")
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    rx = ser.read(200)
    print(f"  RX ({len(rx)}): {rx.hex()}")
    
    # Check if response differs from TX
    if rx != pkt and len(rx) > 0:
        # Parse response
        if rx[:4] == PACKET_HEADER and len(rx) >= 8:
            length = rx[4]
            cmd = rx[5]
            crc_start = 4 + 1 + length - 2
            if crc_start + 2 <= len(rx):
                rx_crc = struct.unpack('>H', rx[crc_start:crc_start+2])[0]
                tx_crc = struct.unpack('>H', pkt[-2:])[0]
                if rx_crc != tx_crc:
                    print(f"  ** DIFFERENT CRC! TX crc={tx_crc:04x}, RX crc={rx_crc:04x} **")
                    print(f"  ** This is likely a REAL response, not echo! **")
    
    return rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Command 0x44 (Possible Read Command)")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Wake up with status sync
    pkt = build_packet(0x0B, b'\x00')
    send_and_receive(ser, pkt, "Wake up (0x0B)")
    
    # Test 0x44 with various channel numbers
    for ch in [0, 50, 51]:
        # Just channel index (2 bytes)
        pkt = build_packet(0x44, struct.pack('>H', ch))
        rx = send_and_receive(ser, pkt, f"0x44 Ch {ch} - 2 bytes")
        
        # Parse if we got 34 bytes (full response)
        if len(rx) >= 34:
            # Skip header and length
            payload = rx[6:32]  # 26 bytes of channel data
            ch_idx = struct.unpack('>H', payload[0:2])[0]
            freq = struct.unpack('>I', payload[4:8])[0]
            name_bytes = payload[14:26]
            name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')
            print(f"  Parsed: Ch {ch_idx}, Freq {freq/1e6:.6f} MHz, Name '{name}'")
    
    # Also compare 0x43 vs 0x44
    print("\n--- Direct Comparison 0x43 vs 0x44 ---")
    
    ch = 50
    pkt43 = build_packet(0x43, struct.pack('>H', ch))
    pkt44 = build_packet(0x44, struct.pack('>H', ch))
    
    rx43 = send_and_receive(ser, pkt43, f"0x43 Ch {ch}")
    time.sleep(0.3)
    rx44 = send_and_receive(ser, pkt44, f"0x44 Ch {ch}")
    
    ser.close()


if __name__ == "__main__":
    main()
