#!/usr/bin/env python3
"""Test clean write/read sequence with proper delays"""

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


def drain_and_wait(ser, label=""):
    """Clear any pending data"""
    time.sleep(0.1)
    leftover = ser.read(500)
    if leftover and label:
        print(f"  [{label}] Drained {len(leftover)} bytes: {leftover.hex()[:40]}...")
    ser.reset_input_buffer()
    time.sleep(0.05)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Clean Write/Read Sequence")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    
    # Clean start
    drain_and_wait(ser, "init")
    
    # First, send equipment type to verify connection
    print("\n1. Equipment Type Query (0x27):")
    pkt = build_packet(0x27)
    ser.write(pkt)
    ser.flush()
    time.sleep(0.2)
    rx = ser.read(50)
    print(f"   TX: {pkt.hex()}")
    print(f"   RX: {rx.hex()}")
    
    drain_and_wait(ser, "after 0x27")
    
    # Write to channel 60 (use different channel to avoid any caching)
    ch_idx = 60
    rx_freq = 446025000  # 446.025 MHz (FRS channel 1)
    mode = 6  # NFM
    
    ch_data = struct.pack('>H', ch_idx)      # channel index
    ch_data += bytes([mode, mode])            # rx/tx mode  
    ch_data += struct.pack('>I', rx_freq)     # rx freq
    ch_data += struct.pack('>I', rx_freq)     # tx freq
    ch_data += bytes([0, 0])                  # no ctcss
    ch_data += b'FRS Ch 1\x00\x00\x00\x00'    # 12-byte name
    
    print(f"\n2. Write to channel {ch_idx}:")
    print(f"   Data: {rx_freq/1e6:.6f} MHz, NFM, name='FRS Ch 1'")
    
    pkt = build_packet(0x40, ch_data)
    print(f"   TX ({len(pkt)}): {pkt.hex()}")
    
    ser.write(pkt)
    ser.flush()
    time.sleep(0.3)  # Longer wait for write
    
    rx = ser.read(100)
    print(f"   RX ({len(rx)}): {rx.hex()}")
    
    drain_and_wait(ser, "after write")
    time.sleep(0.5)  # Extra wait
    
    # Read it back using 0x43 with FULL 26-byte payload (like original protocol)
    print(f"\n3. Read back using 0x43 (full payload):")
    
    read_data = struct.pack('>H', ch_idx) + b'\x00' * 24
    pkt = build_packet(0x43, read_data)
    print(f"   TX ({len(pkt)}): {pkt.hex()}")
    
    ser.write(pkt)
    ser.flush()
    time.sleep(0.3)
    
    rx = ser.read(100)
    print(f"   RX ({len(rx)}): {rx.hex()}")
    
    if len(rx) >= 34:
        # Parse - response should be 34 bytes
        payload = rx[6:32]
        parsed_ch = struct.unpack('>H', payload[0:2])[0]
        parsed_mode_rx = payload[2]
        parsed_mode_tx = payload[3]
        parsed_rx_freq = struct.unpack('>I', payload[4:8])[0]
        parsed_tx_freq = struct.unpack('>I', payload[8:12])[0]
        parsed_name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
        
        print(f"\n4. Parsed Response:")
        print(f"   Channel: {parsed_ch}")
        print(f"   RX Mode: {parsed_mode_rx}, TX Mode: {parsed_mode_tx}")
        print(f"   RX Freq: {parsed_rx_freq/1e6:.6f} MHz")
        print(f"   TX Freq: {parsed_tx_freq/1e6:.6f} MHz")
        print(f"   Name: '{parsed_name}'")
        
        if parsed_rx_freq == rx_freq:
            print(f"\n   *** SUCCESS! ***")
        elif parsed_rx_freq > 0:
            print(f"\n   *** GOT DATA (but different): {parsed_rx_freq/1e6:.6f} MHz ***")
        else:
            print(f"\n   *** Read returned zeros ***")
    
    ser.close()


if __name__ == "__main__":
    main()
