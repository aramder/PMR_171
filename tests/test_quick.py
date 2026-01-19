#!/usr/bin/env python3
"""Quick test with short timeouts"""

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


def build_read_packet(channel: int = 0) -> bytes:
    data = struct.pack('>H', channel) + b'\x00' * 24
    length = 1 + len(data) + 2
    crc_data = bytes([length, 0x43]) + data
    crc = crc16_ccitt(crc_data)
    return PACKET_HEADER + bytes([length, 0x43]) + data + struct.pack('>H', crc)


def test(port, dtr, rts, desc):
    print(f"  {desc}: DTR={dtr} RTS={rts}...", end=" ", flush=True)
    try:
        ser = serial.Serial(port, 115200, timeout=0.5)
        ser.dtr = dtr
        ser.rts = rts
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(build_read_packet(0))
        ser.flush()
        resp = ser.read(50)
        ser.close()
        if resp:
            print(f"RESPONSE: {resp.hex()}")
            return resp[:4] == PACKET_HEADER
        print("no response")
        return False
    except Exception as e:
        print(f"error: {e}")
        return False


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"Quick test on {port}\n")
    
    combos = [
        (True, True, "Both high"),
        (True, False, "DTR only"),
        (False, True, "RTS only"),
        (False, False, "Both low"),
    ]
    
    for dtr, rts, desc in combos:
        if test(port, dtr, rts, desc):
            print(f"\n*** SUCCESS with {desc}! ***")
            return 0
    
    print("\nNo luck with static combos. Trying sequences...")
    
    # Try DTR toggle sequence
    print("\n  DTR toggle sequence...", end=" ", flush=True)
    try:
        ser = serial.Serial(port, 115200, timeout=0.5)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.dtr = True
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(build_read_packet(0))
        ser.flush()
        resp = ser.read(50)
        ser.close()
        if resp:
            print(f"RESPONSE: {resp.hex()}")
            if resp[:4] == PACKET_HEADER:
                print("\n*** SUCCESS with DTR toggle! ***")
                return 0
        else:
            print("no response")
    except Exception as e:
        print(f"error: {e}")
    
    print("\nDone. No working combo found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
