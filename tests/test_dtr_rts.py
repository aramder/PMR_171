#!/usr/bin/env python3
"""
Test DTR/RTS signal combinations for PMR-171 radio connection.

The radio likely requires specific DTR/RTS states to enter programming mode.
This script tries all combinations to find what works.
"""

import sys
import time
import struct

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# Protocol constants
PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])
BAUDRATE = 115200
CMD_CHANNEL_READ = 0x43


def crc16_ccitt(data: bytes) -> int:
    """Calculate CRC-16-CCITT"""
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


def build_channel_read_packet(channel: int = 0) -> bytes:
    """Build a channel read packet"""
    data = struct.pack('>H', channel) + b'\x00' * 24  # 26 bytes total
    length = 1 + len(data) + 2  # cmd + data + crc
    crc_data = bytes([length, CMD_CHANNEL_READ]) + data
    crc = crc16_ccitt(crc_data)
    packet = PACKET_HEADER + bytes([length, CMD_CHANNEL_READ]) + data + struct.pack('>H', crc)
    return packet


def test_dtr_rts_combination(port: str, dtr: bool, rts: bool, delay: float = 0.5) -> bool:
    """Test a specific DTR/RTS combination"""
    print(f"\n  Testing DTR={dtr}, RTS={rts}, delay={delay}s...")
    
    try:
        # Open port with specific DTR/RTS settings
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
            write_timeout=None,
            # Don't let pyserial set DTR/RTS automatically
        )
        
        # Set DTR/RTS explicitly
        ser.dtr = dtr
        ser.rts = rts
        
        # Wait for radio to respond to signal change
        time.sleep(delay)
        
        # Clear any pending data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send channel read command
        packet = build_channel_read_packet(0)
        ser.write(packet)
        ser.flush()
        
        # Wait for response
        response = ser.read(100)
        
        if response:
            print(f"    GOT RESPONSE! ({len(response)} bytes)")
            print(f"    Response: {response.hex()}")
            
            if response[:4] == PACKET_HEADER:
                print(f"    *** VALID PACKET HEADER! ***")
                ser.close()
                return True
            else:
                print(f"    (but not a valid packet)")
        else:
            print(f"    No response")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"    Error: {e}")
        return False


def test_dtr_rts_toggle_sequence(port: str) -> bool:
    """Test toggling DTR/RTS in sequence"""
    print("\n  Testing DTR/RTS toggle sequences...")
    
    sequences = [
        # (description, [(dtr, rts, delay), ...])
        ("DTR pulse high", [(False, False, 0.1), (True, False, 0.5), (True, False, 0.1)]),
        ("RTS pulse high", [(False, False, 0.1), (False, True, 0.5), (False, True, 0.1)]),
        ("Both pulse high", [(False, False, 0.1), (True, True, 0.5), (True, True, 0.1)]),
        ("DTR high, RTS toggle", [(True, False, 0.1), (True, True, 0.3), (True, False, 0.1)]),
        ("DTR toggle, RTS high", [(False, True, 0.1), (True, True, 0.3), (False, True, 0.1)]),
        ("Both low then high", [(False, False, 0.5), (True, True, 0.5)]),
        ("Both high then low", [(True, True, 0.5), (False, False, 0.5)]),
    ]
    
    for desc, sequence in sequences:
        print(f"\n    {desc}...")
        
        try:
            ser = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2.0,
                write_timeout=None,
            )
            
            # Execute sequence
            for dtr, rts, delay in sequence:
                ser.dtr = dtr
                ser.rts = rts
                time.sleep(delay)
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Try to communicate
            packet = build_channel_read_packet(0)
            ser.write(packet)
            ser.flush()
            
            response = ser.read(100)
            
            if response:
                print(f"      GOT RESPONSE! ({len(response)} bytes): {response.hex()}")
                if response[:4] == PACKET_HEADER:
                    print(f"      *** VALID PACKET! ***")
                    ser.close()
                    return True
            else:
                print(f"      No response")
            
            ser.close()
            
        except Exception as e:
            print(f"      Error: {e}")
    
    return False


def test_open_close_sequence(port: str) -> bool:
    """Test opening and closing the port multiple times"""
    print("\n  Testing open/close sequences...")
    
    try:
        # Open-close-open (sometimes resets USB device)
        print("    Opening port first time...")
        ser1 = serial.Serial(port, BAUDRATE, timeout=1)
        ser1.dtr = True
        ser1.rts = True
        time.sleep(0.3)
        ser1.close()
        
        print("    Waiting...")
        time.sleep(0.5)
        
        print("    Opening port second time...")
        ser2 = serial.Serial(port, BAUDRATE, timeout=2)
        ser2.dtr = True
        ser2.rts = True
        time.sleep(0.3)
        
        ser2.reset_input_buffer()
        
        # Try to communicate
        packet = build_channel_read_packet(0)
        ser2.write(packet)
        ser2.flush()
        
        response = ser2.read(100)
        
        if response:
            print(f"    GOT RESPONSE! ({len(response)} bytes): {response.hex()}")
            if response[:4] == PACKET_HEADER:
                print(f"    *** VALID PACKET! ***")
                ser2.close()
                return True
        else:
            print("    No response")
        
        ser2.close()
        return False
        
    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    print("="*70)
    print("PMR-171 DTR/RTS Signal Testing")
    print("="*70)
    
    # Get port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        ports = serial.tools.list_ports.comports()
        print("\nAvailable ports:")
        for p in ports:
            print(f"  {p.device}: {p.description}")
        
        if not ports:
            print("No serial ports found!")
            return 1
        
        port = ports[0].device
        print(f"\nAuto-selected: {port}")
    
    print(f"\nUsing port: {port}")
    
    # Test 1: All static DTR/RTS combinations
    print("\n" + "="*70)
    print("TEST 1: Static DTR/RTS combinations")
    print("="*70)
    
    combinations = [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ]
    
    for dtr, rts in combinations:
        if test_dtr_rts_combination(port, dtr, rts, delay=0.5):
            print(f"\n*** SUCCESS with DTR={dtr}, RTS={rts}! ***")
            return 0
    
    # Test 2: Different delays
    print("\n" + "="*70)
    print("TEST 2: DTR=True, RTS=True with different delays")
    print("="*70)
    
    for delay in [0.1, 0.2, 0.5, 1.0, 2.0]:
        if test_dtr_rts_combination(port, True, True, delay=delay):
            print(f"\n*** SUCCESS with delay={delay}s! ***")
            return 0
    
    # Test 3: Toggle sequences
    print("\n" + "="*70)
    print("TEST 3: DTR/RTS toggle sequences")
    print("="*70)
    
    if test_dtr_rts_toggle_sequence(port):
        print("\n*** SUCCESS with toggle sequence! ***")
        return 0
    
    # Test 4: Open/close sequence
    print("\n" + "="*70)
    print("TEST 4: Port open/close sequence")
    print("="*70)
    
    if test_open_close_sequence(port):
        print("\n*** SUCCESS with open/close sequence! ***")
        return 0
    
    # Failure summary
    print("\n" + "="*70)
    print("ALL TESTS FAILED")
    print("="*70)
    print("""
The radio is not responding to any DTR/RTS combination.

Possible causes:
1. The radio uses USB CDC-ACM protocol which doesn't have real DTR/RTS
2. The connection requires a specific USB control transfer
3. The radio needs to be in a specific menu/mode
4. There's a timing-sensitive boot sequence

Next steps:
1. Check if the radio has a "PC Mode" or "Programming Mode" menu
2. Try pressing specific buttons while connecting
3. Use USB packet capture (Wireshark + USBPcap) to see what the 
   manufacturer software sends at the USB level
4. Check if there's a firmware update for the radio
""")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
