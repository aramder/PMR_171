#!/usr/bin/env python3
"""Test channel read with various timing parameters"""

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
    print(f"Test: Channel Read Timing")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=3)  # Longer timeout
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # First send Status Sync to "wake up" the radio
    print("\nWaking up radio with Status Sync...")
    pkt = build_packet(0x0B, b'\x00')
    ser.write(pkt)
    ser.flush()
    time.sleep(0.2)
    rx = ser.read(100)
    print(f"  Got {len(rx)} bytes: {rx.hex()}")
    
    # Now try channel read with LONGER wait
    print("\n--- Channel Read Tests ---")
    
    for ch in [0, 50]:
        print(f"\nReading channel {ch}...")
        ser.reset_input_buffer()
        
        data = struct.pack('>H', ch) + b'\x00' * 24
        pkt = build_packet(0x43, data)
        
        print(f"  TX ({len(pkt)}): {pkt.hex()}")
        
        ser.write(pkt)
        ser.flush()
        
        # Wait longer for response
        time.sleep(0.5)
        
        # Read all available
        rx = b''
        while True:
            chunk = ser.read(100)
            if not chunk:
                break
            rx += chunk
        
        print(f"  RX ({len(rx)}): {rx.hex()}")
        
        if len(rx) >= 34:
            # Parse the last packet (skip echo if present)
            if len(rx) >= 68:
                # Have echo + response
                resp = rx[34:]
                print(f"  Possible response: {resp.hex()}")
            
            # Parse channel data
            payload_start = rx.rfind(PACKET_HEADER) + 6  # After header + length + cmd
            if payload_start < len(rx):
                payload = rx[payload_start:payload_start+26]
                if len(payload) >= 14:
                    ch_idx = struct.unpack('>H', payload[0:2])[0]
                    freq = struct.unpack('>I', payload[4:8])[0]
                    name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace') if len(payload) >= 26 else ''
                    print(f"  Channel {ch_idx}: {freq/1e6:.6f} MHz, name='{name}'")
    
    ser.close()


if __name__ == "__main__":
    main()
