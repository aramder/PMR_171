#!/usr/bin/env python3
"""Test unlocking channel read - try various mode sequences"""

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


def send_receive(ser, cmd, data=b'', label=''):
    pkt = build_packet(cmd, data)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.15)
    rx = ser.read(100)
    if label:
        print(f"  {label}: TX={pkt.hex()[:30]}... RX({len(rx)})={rx.hex()[:50]}...")
    return rx


def read_ch50(ser):
    """Read channel 50 and check if we get real data"""
    pkt = build_packet(0x44, struct.pack('>H', 50))
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.15)
    rx = ser.read(100)
    
    # Check if we got real data (non-zero frequency)
    if len(rx) >= 34:
        freq = struct.unpack('>I', rx[10:14])[0] if len(rx) > 14 else 0
        return freq > 0, freq, rx
    return False, 0, rx


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: Unlock Channel Read Mode")
    print(f"="*60)
    
    ser = serial.Serial(port, 115200, timeout=2)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.5)
    ser.reset_input_buffer()
    
    # Test 1: Read immediately after connect
    print("\n1. Read right after connect:")
    has_data, freq, rx = read_ch50(ser)
    print(f"   Result: {'HAS DATA!' if has_data else 'Empty'}, freq={freq/1e6:.6f}")
    
    # Test 2: Send Status Sync first
    print("\n2. After Status Sync (0x0B):")
    send_receive(ser, 0x0B, b'\x00')
    has_data, freq, rx = read_ch50(ser)
    print(f"   Result: {'HAS DATA!' if has_data else 'Empty'}, freq={freq/1e6:.6f}")
    
    # Test 3: Send Equipment Type first
    print("\n3. After Equipment Type (0x27):")
    send_receive(ser, 0x27)
    has_data, freq, rx = read_ch50(ser)
    print(f"   Result: {'HAS DATA!' if has_data else 'Empty'}, freq={freq/1e6:.6f}")
    
    # Test 4: Try sequence 0x27 then 0x0B
    print("\n4. After 0x27 then 0x0B sequence:")
    ser.reset_input_buffer()
    time.sleep(0.2)
    send_receive(ser, 0x27)
    time.sleep(0.1)
    send_receive(ser, 0x0B, b'\x00')
    time.sleep(0.1)
    has_data, freq, rx = read_ch50(ser)
    print(f"   Result: {'HAS DATA!' if has_data else 'Empty'}, freq={freq/1e6:.6f}")
    
    # Test 5: Try all mode settings
    print("\n5. After each Mode Setting (0x0A):")
    for mode in range(10):
        send_receive(ser, 0x0A, bytes([mode]))
        has_data, freq, rx = read_ch50(ser)
        if has_data:
            print(f"   Mode {mode}: HAS DATA! freq={freq/1e6:.6f}")
            break
        else:
            print(f"   Mode {mode}: Empty")
    
    # Test 6: Try different command variants
    print("\n6. Try command variations:")
    
    # 0x43 with full 26-byte payload
    print("   0x43 full payload:")
    data = struct.pack('>H', 50) + b'\x00' * 24
    rx = send_receive(ser, 0x43, data)
    if len(rx) >= 34:
        freq = struct.unpack('>I', rx[10:14])[0]
        print(f"     Freq: {freq/1e6:.6f} MHz")
    
    # 0x43 with just index
    print("   0x43 just index:")
    rx = send_receive(ser, 0x43, struct.pack('>H', 50))
    if len(rx) >= 34:
        freq = struct.unpack('>I', rx[10:14])[0]
        print(f"     Freq: {freq/1e6:.6f} MHz")
    
    ser.close()
    
    print("\n" + "="*60)
    print("If all reads return Empty, the channels may have been")
    print("cleared during our testing. Try using the manufacturer")
    print("software to verify/reprogram the radio.")
    print("="*60)


if __name__ == "__main__":
    main()
