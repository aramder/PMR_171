#!/usr/bin/env python3
"""
Focused DTR/RTS test - the relay clicks indicate the radio responds to these signals!

We need to find the correct sequence that puts it into programming mode.
"""

import sys
import time
import struct

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed")
    sys.exit(1)

PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])
BAUDRATE = 115200
CMD_CHANNEL_READ = 0x43


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


def build_channel_read_packet(channel: int = 0) -> bytes:
    data = struct.pack('>H', channel) + b'\x00' * 24
    length = 1 + len(data) + 2
    crc_data = bytes([length, CMD_CHANNEL_READ]) + data
    crc = crc16_ccitt(crc_data)
    packet = PACKET_HEADER + bytes([length, CMD_CHANNEL_READ]) + data + struct.pack('>H', crc)
    return packet


def try_communicate(ser) -> bool:
    """Try to communicate with radio, return True if successful"""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    packet = build_channel_read_packet(0)
    ser.write(packet)
    ser.flush()
    
    response = ser.read(50)
    
    if response and response[:4] == PACKET_HEADER:
        print(f"    *** SUCCESS! Response: {response.hex()} ***")
        return True
    return False


def test_sequence(port: str, dtr_states: list, rts_states: list, delays: list, desc: str) -> bool:
    """Test a specific sequence of DTR/RTS states"""
    print(f"\n  {desc}")
    print(f"    DTR: {dtr_states}")
    print(f"    RTS: {rts_states}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            timeout=1.0,
            write_timeout=None,
        )
        
        # Execute sequence
        for i, (dtr, rts, delay) in enumerate(zip(dtr_states, rts_states, delays)):
            ser.dtr = dtr
            ser.rts = rts
            print(f"    Step {i}: DTR={dtr}, RTS={rts}, waiting {delay}s...")
            time.sleep(delay)
        
        # Try to communicate
        print("    Trying to communicate...")
        success = try_communicate(ser)
        
        ser.close()
        return success
        
    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"DTR/RTS Click Test - Port: {port}")
    print(f"="*60)
    
    # The relay clicking suggests DTR toggling has an effect
    # Let's try sequences that might put radio into programming mode
    
    sequences = [
        # (DTR_list, RTS_list, delays_list, description)
        
        # Simple DTR toggle
        ([False, True], [False, False], [0.1, 0.5],
         "DTR low->high, RTS low"),
         
        ([True, False], [False, False], [0.1, 0.5],
         "DTR high->low, RTS low"),
        
        # Simple RTS toggle
        ([False, False], [False, True], [0.1, 0.5],
         "DTR low, RTS low->high"),
         
        ([False, False], [True, False], [0.1, 0.5],
         "DTR low, RTS high->low"),
        
        # Both start high
        ([True, True], [True, True], [0.5, 0.1],
         "Both high, wait"),
        
        # DTR pulse
        ([False, True, False], [False, False, False], [0.1, 0.1, 0.5],
         "DTR pulse (low-high-low)"),
        
        # RTS pulse
        ([False, False, False], [False, True, False], [0.1, 0.1, 0.5],
         "RTS pulse (low-high-low)"),
        
        # DTR on, then RTS on
        ([True, True], [False, True], [0.3, 0.5],
         "DTR high first, then RTS high"),
        
        # RTS on, then DTR on
        ([False, True], [True, True], [0.3, 0.5],
         "RTS high first, then DTR high"),
        
        # Long wait after DTR high
        ([True], [True], [2.0],
         "Both high, long wait (2s)"),
        
        # Manufacturer software might do: DTR low->high to enter prog mode
        ([False, True, True], [False, False, False], [0.5, 0.2, 0.5],
         "DTR low, wait, then high (enter prog mode?)"),
        
        # Or: Open with DTR/RTS already set
        ([True], [True], [0.3],
         "Start with both high"),
         
        ([True], [False], [0.3],
         "DTR high only"),
         
        ([False], [True], [0.3],
         "RTS high only"),
    ]
    
    print("\nTesting sequences (you should hear clicks on some)...")
    print("Looking for the one that allows communication...\n")
    
    for dtr_states, rts_states, delays, desc in sequences:
        if test_sequence(port, dtr_states, rts_states, delays, desc):
            print(f"\n*** FOUND WORKING SEQUENCE: {desc} ***")
            return 0
        time.sleep(0.5)  # Brief pause between tests
    
    print("\n" + "="*60)
    print("No working sequence found yet.")
    print("="*60)
    print("""
The relay clicking is a good sign! It means:
- DTR signals ARE reaching the radio
- The radio does respond to hardware control lines

Possible issues:
1. The programming mode might require a specific timing
2. The radio might need to be in a specific state/menu
3. There might be additional requirements

Questions:
1. Does the radio show anything on screen when it clicks?
2. Does the manufacturer software show "Connected" status?
3. What exactly does the manufacturer software show when connecting?
""")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
