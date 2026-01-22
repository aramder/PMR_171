#!/usr/bin/env python3
"""
PMR-171 UART Command Fuzzer

This script systematically tests the UART interface to discover:
- Unknown command IDs
- Alternate packet structures
- Hidden features or diagnostic modes
- Response patterns for different inputs

Usage:
    python tests/fuzz_uart_commands.py --port COM6
    python tests/fuzz_uart_commands.py --port COM6 --range 0x00-0xFF
    python tests/fuzz_uart_commands.py --port COM6 --known-only
"""

import argparse
import json
import logging
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pmr_171_cps.radio.pmr171_uart import (
    PMR171Radio, build_packet, parse_packet, crc16_ccitt,
    PACKET_HEADER, Command
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UARTFuzzer:
    """Fuzzer for PMR-171 UART commands"""
    
    # Known commands from protocol documentation
    KNOWN_COMMANDS = {
        0x07: "PTT_CONTROL",
        0x0A: "MODE_SETTING",
        0x0B: "STATUS_SYNC",
        0x27: "EQUIPMENT_TYPE",
        0x28: "POWER_CLASS",
        0x29: "RIT_SETTING",
        0x39: "SPECTRUM_DATA",
        0x40: "CHANNEL_WRITE",
        0x41: "CHANNEL_READ",
        0x43: "DMR_DATA_WRITE",
        0x44: "DMR_DATA_READ",
    }
    
    def __init__(self, port: str, output_dir: str = "tests/fuzz_results", skip_write: bool = False):
        """
        Initialize fuzzer
        
        Args:
            port: Serial port name
            output_dir: Directory to save results
            skip_write: Skip write commands without prompting
        """
        self.port = port
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.skip_write = skip_write
        
        self.radio = None
        self.results = []
        self.start_time = None
        
    def connect(self) -> bool:
        """
        Connect to radio
        
        Returns:
            True if connection successful
        """
        try:
            self.radio = PMR171Radio(self.port)
            self.radio.connect()
            logger.info(f"Connected to radio on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from radio"""
        if self.radio:
            self.radio.disconnect()
            logger.info("Disconnected from radio")
    
    def send_and_log(self, command: int, data: bytes, description: str) -> Dict:
        """
        Send command and log response
        
        Args:
            command: Command byte
            data: Data payload
            description: Description of test
            
        Returns:
            Dictionary with test results
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'command': f"0x{command:02X}",
            'command_name': self.KNOWN_COMMANDS.get(command, 'UNKNOWN'),
            'description': description,
            'data_sent': data.hex() if data else "",
            'data_sent_len': len(data),
            'success': False,
            'response_received': False,
            'response_command': None,
            'response_data': None,
            'response_len': 0,
            'crc_valid': False,
            'error': None
        }
        
        try:
            # Build and send packet
            packet = build_packet(command, data)
            result['packet_sent'] = packet.hex()
            
            logger.debug(f"Sending: CMD=0x{command:02X}, Data={data.hex()}, Desc='{description}'")
            
            self.radio._send_packet(packet)
            time.sleep(0.1)  # Give radio time to process
            
            # Try to receive response
            try:
                response = self.radio._receive_packet()
                result['response_received'] = True
                result['response_full'] = response.hex()
                
                # Parse response
                cmd, payload, crc_valid = parse_packet(response)
                result['response_command'] = f"0x{cmd:02X}"
                result['response_data'] = payload.hex() if payload else ""
                result['response_len'] = len(payload)
                result['crc_valid'] = crc_valid
                result['success'] = True
                
                logger.info(f"✓ CMD 0x{command:02X}: Response 0x{cmd:02X}, {len(payload)} bytes, CRC={crc_valid}")
                
            except Exception as e:
                result['error'] = f"No response: {str(e)}"
                logger.warning(f"✗ CMD 0x{command:02X}: No response ({e})")
                
        except Exception as e:
            result['error'] = f"Send failed: {str(e)}"
            logger.error(f"✗ CMD 0x{command:02X}: Send failed ({e})")
        
        self.results.append(result)
        return result
    
    def fuzz_command_ids(self, start: int = 0x00, end: int = 0xFF):
        """
        Fuzz command ID space
        
        Args:
            start: Start command ID
            end: End command ID
        """
        logger.info(f"Fuzzing command IDs from 0x{start:02X} to 0x{end:02X}")
        
        for cmd in range(start, end + 1):
            # Skip if we want to be cautious about write commands
            if cmd in [0x40, 0x43] and not self._confirm_write_commands():
                logger.warning(f"Skipping write command 0x{cmd:02X}")
                continue
            
            # Test with no payload
            self.send_and_log(cmd, b'', f"Empty payload test for 0x{cmd:02X}")
            time.sleep(0.05)
            
            # Test with minimal payload (2 bytes, like channel read)
            self.send_and_log(cmd, b'\x00\x00', f"2-byte payload test for 0x{cmd:02X}")
            time.sleep(0.05)
    
    def fuzz_known_commands(self):
        """Test known commands with various payloads"""
        logger.info("Fuzzing known commands with variations")
        
        # Test 0x07 - PTT Control
        logger.info("Testing 0x07 (PTT Control)")
        for value in [0x00, 0x01, 0x02, 0xFF]:
            self.send_and_log(0x07, bytes([value]), f"PTT with value {value}")
            time.sleep(0.1)
        
        # Test 0x0A - Mode Setting
        logger.info("Testing 0x0A (Mode Setting)")
        for mode in range(0, 16):  # Test modes 0-15
            self.send_and_log(0x0A, bytes([mode]), f"Mode setting: {mode}")
            time.sleep(0.1)
        
        # Test 0x0B - Status Sync (no payload)
        logger.info("Testing 0x0B (Status Sync)")
        self.send_and_log(0x0B, b'', "Status sync request")
        time.sleep(0.2)
        
        # Test 0x27 - Equipment Type
        logger.info("Testing 0x27 (Equipment Type)")
        self.send_and_log(0x27, b'', "Equipment type request")
        time.sleep(0.1)
        
        # Test 0x28 - Power Class
        logger.info("Testing 0x28 (Power Class)")
        for power in [0, 25, 50, 75, 100]:
            self.send_and_log(0x28, bytes([power]), f"Power class: {power}")
            time.sleep(0.1)
        
        # Test 0x29 - RIT Setting
        logger.info("Testing 0x29 (RIT Setting)")
        for rit in [0, 60, 120]:
            self.send_and_log(0x29, bytes([rit]), f"RIT setting: {rit}")
            time.sleep(0.1)
        
        # Test 0x39 - Spectrum Data
        logger.info("Testing 0x39 (Spectrum Data)")
        self.send_and_log(0x39, b'', "Spectrum data request")
        time.sleep(0.2)
        
        # Test 0x41 - Channel Read
        logger.info("Testing 0x41 (Channel Read)")
        for ch in [0, 1, 100, 999]:
            data = struct.pack('>H', ch)
            self.send_and_log(0x41, data, f"Read channel {ch}")
            time.sleep(0.15)
        
        # Test 0x44 - DMR Data Read
        logger.info("Testing 0x44 (DMR Data Read)")
        for ch in [0, 50, 100]:
            data = struct.pack('>H', ch)
            self.send_and_log(0x44, data, f"Read DMR data channel {ch}")
            time.sleep(0.15)
    
    def fuzz_payload_sizes(self, command: int = 0x41):
        """
        Test a command with varying payload sizes
        
        Args:
            command: Command to test
        """
        logger.info(f"Fuzzing payload sizes for command 0x{command:02X}")
        
        # Test various payload lengths
        for size in [0, 1, 2, 4, 8, 16, 26, 32, 64, 128, 255]:
            payload = bytes([0x00] * size)
            self.send_and_log(command, payload, f"Payload size {size} bytes")
            time.sleep(0.1)
    
    def fuzz_boundary_values(self):
        """Test boundary values in channel reads"""
        logger.info("Testing boundary values")
        
        # Channel index boundaries
        test_channels = [
            0x0000,  # First channel
            0x0001,  # Second channel
            0x03E7,  # Channel 999 (last valid)
            0x03E8,  # Channel 1000 (first invalid)
            0xFFFF,  # Maximum value
        ]
        
        for ch in test_channels:
            data = struct.pack('>H', ch)
            self.send_and_log(0x41, data, f"Channel boundary test: {ch}")
            time.sleep(0.15)
    
    def discover_command_patterns(self):
        """Look for patterns in command space"""
        logger.info("Discovering command patterns")
        
        # Test command sequences
        sequences = [
            (0x40, 0x41),  # Write/Read pair
            (0x43, 0x44),  # DMR Write/Read pair
            (0x0A, 0x0B),  # Mode then Status
        ]
        
        for cmd1, cmd2 in sequences:
            logger.info(f"Testing sequence: 0x{cmd1:02X} -> 0x{cmd2:02X}")
            
            # Send first command with minimal payload
            self.send_and_log(cmd1, struct.pack('>H', 0), f"Sequence part 1: 0x{cmd1:02X}")
            time.sleep(0.2)
            
            # Send second command
            self.send_and_log(cmd2, struct.pack('>H', 0), f"Sequence part 2: 0x{cmd2:02X}")
            time.sleep(0.2)
    
    def _confirm_write_commands(self) -> bool:
        """
        Ask user to confirm testing write commands
        
        Returns:
            True if user confirms
        """
        if self.skip_write:
            logger.info("Skipping write commands (--skip-write flag set)")
            return False
            
        print("\n*** WARNING: About to test WRITE commands (0x40, 0x43) ***")
        print("   These commands modify radio memory!")
        print("   Ensure you have a backup of your configuration.")
        response = input("   Continue? (yes/no): ").strip().lower()
        return response == 'yes'
    
    def save_results(self):
        """Save fuzzing results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"fuzz_results_{timestamp}.json"
        
        summary = {
            'metadata': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat(),
                'port': self.port,
                'total_tests': len(self.results),
                'successful_responses': sum(1 for r in self.results if r['response_received']),
                'valid_crc_responses': sum(1 for r in self.results if r.get('crc_valid', False)),
            },
            'results': self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
        
        # Also create a summary report
        self._create_summary_report(filename.with_suffix('.md'))
    
    def _create_summary_report(self, filename: Path):
        """Create human-readable summary report"""
        with open(filename, 'w') as f:
            f.write("# PMR-171 UART Fuzzing Results\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Port:** {self.port}\n\n")
            f.write(f"**Total Tests:** {len(self.results)}\n\n")
            
            # Successful responses
            successful = [r for r in self.results if r['response_received']]
            f.write(f"**Successful Responses:** {len(successful)} / {len(self.results)}\n\n")
            
            # Discovered commands
            f.write("## Discovered Command Responses\n\n")
            f.write("| Command | Name | Response Count | CRC Valid |\n")
            f.write("|---------|------|----------------|------------|\n")
            
            command_stats = {}
            for r in successful:
                cmd = r['command']
                if cmd not in command_stats:
                    command_stats[cmd] = {
                        'name': r['command_name'],
                        'count': 0,
                        'crc_valid': 0
                    }
                command_stats[cmd]['count'] += 1
                if r.get('crc_valid', False):
                    command_stats[cmd]['crc_valid'] += 1
            
            for cmd, stats in sorted(command_stats.items()):
                f.write(f"| {cmd} | {stats['name']} | {stats['count']} | {stats['crc_valid']} |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for r in successful:
                f.write(f"### {r['command']} - {r['command_name']}\n\n")
                f.write(f"**Description:** {r['description']}\n\n")
                f.write(f"**Data Sent:** `{r['data_sent']}` ({r['data_sent_len']} bytes)\n\n")
                f.write(f"**Response Command:** {r['response_command']}\n\n")
                f.write(f"**Response Data:** `{r['response_data']}` ({r['response_len']} bytes)\n\n")
                f.write(f"**CRC Valid:** {r['crc_valid']}\n\n")
                f.write("---\n\n")
        
        logger.info(f"Summary report saved to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Fuzz PMR-171 UART interface to discover commands'
    )
    parser.add_argument(
        '--port',
        required=True,
        help='Serial port (e.g., COM6, /dev/ttyUSB0)'
    )
    parser.add_argument(
        '--range',
        default='0x00-0xFF',
        help='Command ID range to test (e.g., 0x00-0xFF, 0x20-0x50)'
    )
    parser.add_argument(
        '--known-only',
        action='store_true',
        help='Only test known commands with variations'
    )
    parser.add_argument(
        '--output-dir',
        default='tests/fuzz_results',
        help='Output directory for results'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test mode (fewer variations)'
    )
    parser.add_argument(
        '--skip-write',
        action='store_true',
        help='Skip write commands (0x40, 0x43) without prompting'
    )
    
    args = parser.parse_args()
    
    # Parse range
    if '-' in args.range:
        start_str, end_str = args.range.split('-')
        start = int(start_str, 16)
        end = int(end_str, 16)
    else:
        start = int(args.range, 16)
        end = start
    
    # Create fuzzer
    fuzzer = UARTFuzzer(args.port, args.output_dir, skip_write=args.skip_write)
    
    try:
        # Connect to radio
        if not fuzzer.connect():
            return 1
        
        fuzzer.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("PMR-171 UART Fuzzer")
        logger.info("=" * 60)
        
        if args.known_only:
            # Test only known commands
            fuzzer.fuzz_known_commands()
        else:
            # Full fuzzing suite
            if not args.quick:
                fuzzer.fuzz_command_ids(start, end)
            
            fuzzer.fuzz_known_commands()
            fuzzer.fuzz_payload_sizes()
            fuzzer.fuzz_boundary_values()
            fuzzer.discover_command_patterns()
        
        logger.info("=" * 60)
        logger.info("Fuzzing complete!")
        logger.info("=" * 60)
        
        # Save results
        fuzzer.save_results()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nFuzzing interrupted by user")
        fuzzer.save_results()
        return 1
        
    except Exception as e:
        logger.error(f"Fuzzing failed: {e}", exc_info=True)
        return 1
        
    finally:
        fuzzer.disconnect()


if __name__ == '__main__':
    sys.exit(main())
