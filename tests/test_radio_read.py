#!/usr/bin/env python3
"""
Standalone test script for PMR-171 radio reading.

This script tests the serial communication with the radio
independently from the GUI to help diagnose connection issues.

Usage:
    python tests/test_radio_read.py [COM_PORT]
    
Example:
    python tests/test_radio_read.py COM3
"""

import sys
import time
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, '.')

from pmr_171_cps.radio.pmr171_uart import (
    PMR171Radio, 
    list_serial_ports,
    SERIAL_AVAILABLE,
    build_packet,
    Command,
    PACKET_HEADER
)


def test_list_ports():
    """Test listing available serial ports"""
    print("\n" + "="*60)
    print("STEP 1: Listing Available Serial Ports")
    print("="*60)
    
    ports = list_serial_ports()
    if not ports:
        print("  No serial ports found!")
        return None
    
    print(f"  Found {len(ports)} port(s):")
    for i, port in enumerate(ports):
        print(f"    [{i}] {port['port']}: {port['description']}")
        print(f"        HWID: {port['hwid']}")
    
    return ports


def test_raw_serial(port: str):
    """Test raw serial communication without protocol"""
    print("\n" + "="*60)
    print(f"STEP 2: Testing Raw Serial Connection on {port}")
    print("="*60)
    
    try:
        import serial
        
        print(f"  Opening {port} at 115200 baud...")
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
            write_timeout=None,
            rtscts=False,
            dsrdtr=False
        )
        
        print(f"  Port opened successfully!")
        print(f"    is_open: {ser.is_open}")
        print(f"    baudrate: {ser.baudrate}")
        print(f"    timeout: {ser.timeout}")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        # Build a simple channel read packet for channel 0
        # Channel read command: 0x43, with 26 bytes of data (channel index + padding)
        import struct
        channel_index = 0
        data = struct.pack('>H', channel_index) + b'\x00' * 24
        
        # Calculate packet
        length = 1 + len(data) + 2  # cmd + data + crc
        
        # CRC calculation
        def crc16_ccitt(data_bytes):
            crc = 0xFFFF
            for byte in data_bytes:
                cur = byte << 8
                for _ in range(8):
                    if (crc ^ cur) & 0x8000:
                        crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                    else:
                        crc = (crc << 1) & 0xFFFF
                    cur = (cur << 1) & 0xFFFF
            return crc
        
        crc_data = bytes([length, Command.CHANNEL_READ]) + data
        crc = crc16_ccitt(crc_data)
        
        packet = PACKET_HEADER + bytes([length, Command.CHANNEL_READ]) + data + struct.pack('>H', crc)
        
        print(f"\n  Sending channel 0 read request...")
        print(f"    Packet ({len(packet)} bytes): {packet.hex()}")
        
        # Send packet
        start_time = time.time()
        bytes_written = ser.write(packet)
        ser.flush()
        write_time = time.time() - start_time
        
        print(f"    Bytes written: {bytes_written}")
        print(f"    Write time: {write_time:.3f}s")
        
        # Try to read response
        print(f"\n  Waiting for response (timeout: {ser.timeout}s)...")
        start_time = time.time()
        
        # Try reading header first
        header = ser.read(4)
        header_time = time.time() - start_time
        
        if len(header) == 0:
            print(f"    No response received (timeout after {header_time:.3f}s)")
            print("    The radio may not be responding to commands.")
        elif len(header) < 4:
            print(f"    Partial header received: {header.hex()} ({len(header)} bytes, {header_time:.3f}s)")
        else:
            print(f"    Header received: {header.hex()} ({header_time:.3f}s)")
            
            if header == PACKET_HEADER:
                print("    Header is valid! Reading rest of packet...")
                
                # Read length
                length_byte = ser.read(1)
                if length_byte:
                    resp_length = length_byte[0]
                    print(f"    Length byte: {resp_length}")
                    
                    # Read remaining data
                    remaining = ser.read(resp_length)
                    print(f"    Remaining data ({len(remaining)} bytes): {remaining.hex()}")
                    
                    if len(remaining) == resp_length:
                        print("    Complete packet received!")
                        
                        # Parse channel data
                        if resp_length >= 27:  # cmd + 26 bytes data
                            cmd = remaining[0]
                            payload = remaining[1:resp_length-2]
                            print(f"    Command: 0x{cmd:02X}")
                            print(f"    Payload ({len(payload)} bytes): {payload.hex()}")
                            
                            if len(payload) >= 26:
                                ch_idx = struct.unpack('>H', payload[0:2])[0]
                                rx_mode = payload[2]
                                tx_mode = payload[3]
                                rx_freq = struct.unpack('>I', payload[4:8])[0]
                                tx_freq = struct.unpack('>I', payload[8:12])[0]
                                rx_ctcss = payload[12]
                                tx_ctcss = payload[13]
                                name = payload[14:26].split(b'\x00')[0].decode('ascii', errors='replace')
                                
                                print(f"\n    CHANNEL DATA:")
                                print(f"      Index: {ch_idx}")
                                print(f"      RX Mode: {rx_mode}, TX Mode: {tx_mode}")
                                print(f"      RX Freq: {rx_freq/1e6:.6f} MHz")
                                print(f"      TX Freq: {tx_freq/1e6:.6f} MHz")
                                print(f"      RX CTCSS: {rx_ctcss}, TX CTCSS: {tx_ctcss}")
                                print(f"      Name: '{name}'")
            else:
                print(f"    Invalid header! Expected: {PACKET_HEADER.hex()}")
        
        # Check if there's any data in buffer
        remaining_data = ser.read(100)
        if remaining_data:
            print(f"\n    Additional data in buffer: {remaining_data.hex()}")
        
        ser.close()
        print("\n  Port closed.")
        return True
        
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pmr171_class(port: str):
    """Test using the PMR171Radio class"""
    print("\n" + "="*60)
    print(f"STEP 3: Testing PMR171Radio Class on {port}")
    print("="*60)
    
    try:
        radio = PMR171Radio(port)
        
        print("  Connecting...")
        radio.connect()
        print(f"    Connected: {radio.is_connected}")
        
        print("\n  Attempting to read channel 0...")
        start_time = time.time()
        try:
            channel = radio.read_channel(0)
            read_time = time.time() - start_time
            print(f"    SUCCESS! Read in {read_time:.3f}s")
            print(f"    {channel}")
        except Exception as e:
            read_time = time.time() - start_time
            print(f"    FAILED after {read_time:.3f}s: {type(e).__name__}: {e}")
        
        print("\n  Disconnecting...")
        radio.disconnect()
        print("    Disconnected.")
        return True
        
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_read_multiple_channels(port: str, count: int = 5):
    """Test reading multiple channels"""
    print("\n" + "="*60)
    print(f"STEP 4: Testing Reading {count} Channels on {port}")
    print("="*60)
    
    try:
        radio = PMR171Radio(port)
        radio.connect()
        
        def progress_callback(current, total, message):
            print(f"    [{current}/{total}] {message}")
        
        print(f"  Reading first {count} channels...")
        channels = radio.read_selected_channels(
            list(range(count)),
            progress_callback=progress_callback
        )
        
        print(f"\n  Read {len(channels)} channels:")
        for ch in channels:
            print(f"    {ch}")
        
        radio.disconnect()
        return True
        
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("PMR-171 Radio Read Test Script")
    print("="*60)
    
    if not SERIAL_AVAILABLE:
        print("ERROR: pyserial is not installed!")
        print("Install it with: pip install pyserial")
        return 1
    
    # Get port from command line or list available
    if len(sys.argv) > 1:
        port = sys.argv[1]
        print(f"\nUsing specified port: {port}")
    else:
        ports = test_list_ports()
        if not ports:
            print("\nNo serial ports available. Connect the radio and try again.")
            return 1
        
        # Try to find the PMR-171 port
        port = None
        for p in ports:
            # Look for common USB-serial identifiers
            if 'USB' in p['description'].upper() or 'CH340' in p['description'].upper():
                port = p['port']
                break
        
        if not port:
            port = ports[0]['port']
        
        print(f"\nAuto-selected port: {port}")
        print("(Pass port as argument to specify: python tests/test_radio_read.py COM3)")
    
    # Run tests
    print("\n" + "#"*60)
    print("# Starting Tests")
    print("#"*60)
    
    # Test 1: List ports (already done if auto-selecting)
    if len(sys.argv) <= 1:
        pass  # Already done above
    else:
        test_list_ports()
    
    # Test 2: Raw serial test
    raw_result = test_raw_serial(port)
    
    if raw_result:
        # Test 3: PMR171Radio class test
        class_result = test_pmr171_class(port)
        
        if class_result:
            # Test 4: Multiple channel read
            test_read_multiple_channels(port, count=3)
    
    print("\n" + "="*60)
    print("Tests Complete")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
