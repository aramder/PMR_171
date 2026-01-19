#!/usr/bin/env python3
"""
PMR-171 Radio Initialization Test Script

This script tests different initialization sequences to find what
makes the radio respond to commands.

Based on the protocol documentation, we should try:
1. Equipment Type Recognition (0x27)
2. Status Synchronization (0x0B)
3. Mode Setting (0x0A)
4. Direct channel read (0x43)
"""

import sys
import time
import struct
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# Protocol constants
PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])
BAUDRATE = 115200

# Commands from protocol documentation
CMD_PTT_CONTROL = 0x07
CMD_MODE_SETTING = 0x0A
CMD_STATUS_SYNC = 0x0B
CMD_EQUIPMENT_TYPE = 0x27
CMD_POWER_CLASS = 0x28
CMD_RIT_SETTING = 0x29
CMD_SPECTRUM_DATA = 0x39
CMD_CHANNEL_WRITE = 0x40
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


def build_packet(command: int, data: bytes = b'') -> bytes:
    """Build a complete PMR-171 packet"""
    length = 1 + len(data) + 2  # cmd + data + crc
    crc_data = bytes([length, command]) + data
    crc = crc16_ccitt(crc_data)
    packet = PACKET_HEADER + bytes([length, command]) + data + struct.pack('>H', crc)
    return packet


def send_and_receive(ser: serial.Serial, packet: bytes, description: str, timeout: float = 2.0) -> bytes:
    """Send a packet and wait for response"""
    print(f"\n  Sending: {description}")
    print(f"    Packet ({len(packet)} bytes): {packet.hex()}")
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Send
    start = time.time()
    ser.write(packet)
    ser.flush()
    print(f"    Write time: {time.time()-start:.3f}s")
    
    # Wait for response
    ser.timeout = timeout
    response = ser.read(256)  # Read up to 256 bytes
    elapsed = time.time() - start
    
    if response:
        print(f"    Response ({len(response)} bytes, {elapsed:.3f}s): {response.hex()}")
        
        # Try to parse response
        if response[:4] == PACKET_HEADER:
            print(f"    Valid header! Response appears to be a PMR-171 packet")
            if len(response) >= 6:
                length = response[4]
                cmd = response[5]
                print(f"    Length: {length}, Command: 0x{cmd:02X}")
        else:
            print(f"    Warning: Response doesn't have expected header")
    else:
        print(f"    No response (timeout after {elapsed:.3f}s)")
    
    return response


def test_equipment_type(ser: serial.Serial):
    """Test Equipment Type Recognition command (0x27)"""
    print("\n" + "="*60)
    print("TEST: Equipment Type Recognition (0x27)")
    print("="*60)
    
    packet = build_packet(CMD_EQUIPMENT_TYPE)
    return send_and_receive(ser, packet, "Equipment Type Query")


def test_status_sync(ser: serial.Serial):
    """Test Status Synchronization command (0x0B)"""
    print("\n" + "="*60)
    print("TEST: Status Synchronization (0x0B)")
    print("="*60)
    
    packet = build_packet(CMD_STATUS_SYNC)
    return send_and_receive(ser, packet, "Status Sync Request")


def test_mode_setting(ser: serial.Serial, mode: int = 6):
    """Test Mode Setting command (0x0A)"""
    print("\n" + "="*60)
    print(f"TEST: Mode Setting (0x0A) - Mode {mode}")
    print("="*60)
    
    packet = build_packet(CMD_MODE_SETTING, bytes([mode]))
    return send_and_receive(ser, packet, f"Set Mode to {mode}")


def test_channel_read(ser: serial.Serial, channel: int = 0):
    """Test Channel Read command (0x43)"""
    print("\n" + "="*60)
    print(f"TEST: Channel Read (0x43) - Channel {channel}")
    print("="*60)
    
    # Channel read needs 26 bytes of data (channel index + padding)
    data = struct.pack('>H', channel) + b'\x00' * 24
    packet = build_packet(CMD_CHANNEL_READ, data)
    return send_and_receive(ser, packet, f"Read Channel {channel}")


def test_power_class(ser: serial.Serial, power: int = 50):
    """Test Power Class command (0x28)"""
    print("\n" + "="*60)
    print(f"TEST: Power Class (0x28) - Power {power}")
    print("="*60)
    
    packet = build_packet(CMD_POWER_CLASS, bytes([power]))
    return send_and_receive(ser, packet, f"Set Power to {power}")


def test_spectrum_data(ser: serial.Serial):
    """Test Spectrum Data Request command (0x39)"""
    print("\n" + "="*60)
    print("TEST: Spectrum Data Request (0x39)")
    print("="*60)
    
    packet = build_packet(CMD_SPECTRUM_DATA)
    return send_and_receive(ser, packet, "Request Spectrum Data", timeout=1.0)


def test_ptt(ser: serial.Serial, state: int = 0):
    """Test PTT Control command (0x07)"""
    print("\n" + "="*60)
    print(f"TEST: PTT Control (0x07) - State {state}")
    print("="*60)
    
    packet = build_packet(CMD_PTT_CONTROL, bytes([state]))
    return send_and_receive(ser, packet, f"PTT {'Press' if state else 'Release'}")


def test_raw_bytes(ser: serial.Serial):
    """Test sending raw bytes to see if radio responds to anything"""
    print("\n" + "="*60)
    print("TEST: Raw Byte Patterns")
    print("="*60)
    
    patterns = [
        (b'\xAA' * 8, "0xAA repeated"),
        (b'\x55' * 8, "0x55 repeated"),
        (PACKET_HEADER, "Just header (A5 A5 A5 A5)"),
        (b'\x00' * 8, "All zeros"),
        (b'\xFF' * 8, "All FF"),
    ]
    
    for pattern, desc in patterns:
        print(f"\n  Sending: {desc}")
        ser.reset_input_buffer()
        ser.write(pattern)
        ser.flush()
        time.sleep(0.5)
        response = ser.read(256)
        if response:
            print(f"    Response: {response.hex()}")
        else:
            print(f"    No response")


def test_different_baud_rates(port: str):
    """Test different baud rates"""
    print("\n" + "="*60)
    print("TEST: Different Baud Rates")
    print("="*60)
    
    baud_rates = [115200, 9600, 19200, 38400, 57600, 230400, 460800]
    
    for baud in baud_rates:
        print(f"\n  Testing {baud} baud...")
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
                write_timeout=None,
                rtscts=False,
                dsrdtr=False
            )
            
            # Try equipment type query
            packet = build_packet(CMD_EQUIPMENT_TYPE)
            ser.reset_input_buffer()
            ser.write(packet)
            ser.flush()
            
            response = ser.read(100)
            if response:
                print(f"    GOT RESPONSE at {baud} baud!")
                print(f"    Response: {response.hex()}")
                ser.close()
                return baud
            else:
                print(f"    No response")
            
            ser.close()
        except Exception as e:
            print(f"    Error: {e}")
    
    return None


def list_ports():
    """List available serial ports"""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable serial ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
        print(f"    HWID: {port.hwid}")
    return [p.device for p in ports]


def main():
    print("="*60)
    print("PMR-171 Radio Initialization Test")
    print("="*60)
    
    # Get port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        ports = list_ports()
        if not ports:
            print("\nNo serial ports found!")
            return 1
        port = ports[0]
        print(f"\nAuto-selected: {port}")
    
    print(f"\nUsing port: {port}")
    
    # First test different baud rates
    print("\n" + "#"*60)
    print("# PHASE 1: Find correct baud rate")
    print("#"*60)
    
    working_baud = test_different_baud_rates(port)
    
    if working_baud:
        print(f"\n*** Found working baud rate: {working_baud} ***")
        baud = working_baud
    else:
        print("\nNo response at any baud rate. Using default 115200.")
        baud = BAUDRATE
    
    # Open port for main tests
    print("\n" + "#"*60)
    print("# PHASE 2: Test initialization sequences")
    print("#"*60)
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
            write_timeout=None,
            rtscts=False,
            dsrdtr=False
        )
        print(f"\nPort opened: {port} at {baud} baud")
    except Exception as e:
        print(f"\nFailed to open port: {e}")
        return 1
    
    # Give time for radio to settle after port open
    time.sleep(0.5)
    
    # Test sequence 1: Equipment Type first
    print("\n" + "-"*60)
    print("Sequence 1: Equipment Type first")
    print("-"*60)
    
    resp = test_equipment_type(ser)
    if resp:
        print("SUCCESS: Radio responded to Equipment Type!")
    
    time.sleep(0.5)
    
    # Test sequence 2: Status Sync
    print("\n" + "-"*60)
    print("Sequence 2: Status Synchronization")
    print("-"*60)
    
    resp = test_status_sync(ser)
    if resp:
        print("SUCCESS: Radio responded to Status Sync!")
    
    time.sleep(0.5)
    
    # Test sequence 3: Direct channel read
    print("\n" + "-"*60)
    print("Sequence 3: Direct Channel Read")
    print("-"*60)
    
    resp = test_channel_read(ser, 0)
    if resp:
        print("SUCCESS: Radio responded to Channel Read!")
    
    time.sleep(0.5)
    
    # Test sequence 4: Try spectrum data (maybe wakes up radio)
    print("\n" + "-"*60)
    print("Sequence 4: Spectrum Data Request")
    print("-"*60)
    
    resp = test_spectrum_data(ser)
    if resp:
        print("Got spectrum data response!")
        # Now try channel read again
        time.sleep(0.3)
        resp2 = test_channel_read(ser, 0)
        if resp2:
            print("SUCCESS: Channel read works after spectrum!")
    
    # Test sequence 5: Raw byte patterns
    print("\n" + "-"*60)
    print("Sequence 5: Raw Byte Patterns")
    print("-"*60)
    
    test_raw_bytes(ser)
    
    # Close port
    ser.close()
    print("\n\nPort closed.")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("""
FINDINGS:
- If no responses at any baud rate, the radio may need:
  1. A specific USB driver mode
  2. The manufacturer software to initiate a session
  3. A hardware programming mode (button combination?)
  
NEXT STEPS:
- Monitor UART traffic while manufacturer software is running
- Look for initialization sequence in existing captures
- Check if radio has a "PC programming mode" setting
""")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
