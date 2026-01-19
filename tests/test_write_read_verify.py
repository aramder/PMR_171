#!/usr/bin/env python3
"""Test write then read to verify the protocol works"""

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
    print(f"Test: Write to Ch 50, then Read Back")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=1)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.3)
    ser.reset_input_buffer()
    
    # Build channel write packet for channel 50
    ch_idx = 50
    rx_freq = 146520000  # 146.52 MHz
    tx_freq = 146520000
    mode = 6  # NFM
    rx_ctcss = 13  # 100.0 Hz
    tx_ctcss = 13
    name = b'TestCh50\x00\x00\x00\x00'  # 12 bytes
    
    # Build the 26-byte channel data
    ch_data = struct.pack('>H', ch_idx)      # 2: channel index
    ch_data += bytes([mode, mode])            # 2: rx/tx mode
    ch_data += struct.pack('>I', rx_freq)     # 4: rx freq
    ch_data += struct.pack('>I', tx_freq)     # 4: tx freq
    ch_data += bytes([rx_ctcss, tx_ctcss])    # 2: ctcss
    ch_data += name                            # 12: name
    
    print(f"\n1. Writing to channel {ch_idx}:")
    print(f"   Freq: {rx_freq/1e6:.6f} MHz, Mode: NFM, CTCSS: 100.0 Hz")
    print(f"   Name: 'TestCh50'")
    
    pkt = build_packet(0x40, ch_data)  # 0x40 = write
    print(f"   TX: {pkt.hex()}")
    
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.15)
    
    rx = ser.read(50)
    print(f"   RX ({len(rx)}): {rx.hex()}")
    
    # Now try to read it back
    print(f"\n2. Reading back channel {ch_idx}:")
    time.sleep(0.2)
    
    # Try 0x44 command (seems to be read)
    pkt = build_packet(0x44, struct.pack('>H', ch_idx))
    print(f"   TX: {pkt.hex()}")
    
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.15)
    
    rx = ser.read(50)
    print(f"   RX ({len(rx)}): {rx.hex()}")
    
    if len(rx) >= 34:
        # Parse response
        if rx[:4] == PACKET_HEADER:
            payload = rx[6:32]
            read_ch = struct.unpack('>H', payload[0:2])[0]
            read_freq = struct.unpack('>I', payload[4:8])[0]
            read_name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
            
            print(f"\n3. Parsed Response:")
            print(f"   Channel: {read_ch}")
            print(f"   Frequency: {read_freq/1e6:.6f} MHz")
            print(f"   Name: '{read_name}'")
            
            if read_freq == rx_freq:
                print(f"\n   *** SUCCESS! Write/Read verified! ***")
            elif read_freq == 0:
                print(f"\n   *** Read returned zeros - write may not have persisted ***")
    
    ser.close()


if __name__ == "__main__":
    main()
