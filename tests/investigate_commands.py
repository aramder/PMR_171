#!/usr/bin/env python3
"""
PMR-171 UART Command Investigation Tool

Focused investigation of discovered commands to understand their function.

Usage:
    python tests/investigate_commands.py --port COM3 --command 0x2E
    python tests/investigate_commands.py --port COM3 --interactive
"""

import argparse
import json
import logging
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pmr_171_cps.radio.pmr171_uart import (
    PMR171Radio, build_packet, parse_packet, PACKET_HEADER
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Commands discovered during fuzzing
DISCOVERED_COMMANDS = {
    # Data-returning commands (high priority)
    0x2D: {"name": "UNKNOWN_2D", "returns": "2 bytes", "priority": "HIGH"},
    0x2E: {"name": "UNKNOWN_2E", "returns": "30 bytes", "priority": "HIGH"},
    
    # Spectrum/FFT configuration (medium priority)
    0x20: {"name": "UNKNOWN_20", "returns": "empty", "priority": "MEDIUM", "note": "FFT related"},
    0x21: {"name": "UNKNOWN_21", "returns": "empty", "priority": "MEDIUM", "note": "FFT related"},
    0x22: {"name": "UNKNOWN_22", "returns": "empty", "priority": "MEDIUM", "note": "FFT related"},
    0x23: {"name": "UNKNOWN_23", "returns": "empty", "priority": "MEDIUM", "note": "FFT related"},
    
    # System commands
    0x00: {"name": "PTT_ALIAS", "returns": "0x07 response", "priority": "LOW"},
    0x03: {"name": "UNKNOWN_03", "returns": "empty", "priority": "LOW"},
    0x04: {"name": "UNKNOWN_04", "returns": "0-2 bytes", "priority": "MEDIUM"},
    
    # Extended mode commands
    0x0C: {"name": "UNKNOWN_0C", "returns": "empty", "priority": "LOW"},
    0x0D: {"name": "UNKNOWN_0D", "returns": "empty", "priority": "LOW"},
    0x0E: {"name": "UNKNOWN_0E", "returns": "empty", "priority": "LOW"},
    0x0F: {"name": "UNKNOWN_0F", "returns": "empty", "priority": "LOW"},
    0x10: {"name": "UNKNOWN_10", "returns": "empty", "priority": "LOW"},
}


class CommandInvestigator:
    """Investigate specific UART commands in detail"""
    
    def __init__(self, port: str):
        self.port = port
        self.radio = None
        self.results = []
        
    def connect(self) -> bool:
        try:
            self.radio = PMR171Radio(self.port)
            self.radio.connect()
            logger.info(f"Connected to {self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        if self.radio:
            self.radio.disconnect()
            
    def send_command(self, command: int, data: bytes = b'') -> Dict:
        """Send command and capture detailed response"""
        result = {
            'command': f"0x{command:02X}",
            'data_sent': data.hex(),
            'data_len': len(data),
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'response': None
        }
        
        try:
            packet = build_packet(command, data)
            logger.info(f"Sending 0x{command:02X} with {len(data)} bytes data")
            
            self.radio._send_packet(packet)
            time.sleep(0.15)
            
            try:
                response = self.radio._receive_packet()
                cmd, payload, crc_valid = parse_packet(response)
                
                result['success'] = True
                result['response'] = {
                    'command': f"0x{cmd:02X}",
                    'payload': payload.hex(),
                    'payload_len': len(payload),
                    'payload_bytes': list(payload),
                    'crc_valid': crc_valid,
                    'full_packet': response.hex()
                }
                
                logger.info(f"✓ Response: 0x{cmd:02X}, {len(payload)} bytes, CRC={crc_valid}")
                if len(payload) > 0:
                    logger.info(f"  Payload: {payload.hex()}")
                    logger.info(f"  Bytes: {list(payload)}")
                    
            except Exception as e:
                result['error'] = str(e)
                logger.warning(f"✗ No response: {e}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ Send failed: {e}")
            
        self.results.append(result)
        return result
    
    def investigate_command(self, command: int, iterations: int = 5):
        """Investigate a command with multiple test cases"""
        logger.info("=" * 60)
        logger.info(f"Investigating Command 0x{command:02X}")
        if command in DISCOVERED_COMMANDS:
            info = DISCOVERED_COMMANDS[command]
            logger.info(f"  Name: {info['name']}")
            logger.info(f"  Known to return: {info['returns']}")
            logger.info(f"  Priority: {info['priority']}")
            if 'note' in info:
                logger.info(f"  Note: {info['note']}")
        logger.info("=" * 60)
        
        test_cases = [
            (b'', "Empty payload"),
            (b'\x00', "Single zero byte"),
            (b'\x00\x00', "Two zero bytes"),
            (b'\x01\x00', "0x0100"),
            (b'\x00\x01', "0x0001"),
            (b'\xFF\xFF', "0xFFFF"),
        ]
        
        for i, (payload, description) in enumerate(test_cases[:iterations], 1):
            logger.info(f"\nTest {i}/{iterations}: {description}")
            self.send_command(command, payload)
            time.sleep(0.2)
    
    def compare_responses(self, command: int, count: int = 10):
        """Send same command multiple times to check consistency"""
        logger.info(f"\nConsistency test for 0x{command:02X} ({count} iterations)")
        
        responses = []
        for i in range(count):
            result = self.send_command(command, b'')
            if result.get('success') and result.get('response'):
                responses.append(result['response']['payload'])
            time.sleep(0.1)
        
        if responses:
            unique = set(responses)
            logger.info(f"Unique responses: {len(unique)}")
            if len(unique) == 1:
                logger.info("  ✓ Response is CONSISTENT")
            else:
                logger.info("  ⚠ Response VARIES:")
                for resp in unique:
                    logger.info(f"    {resp}")
    
    def analyze_payload_structure(self, command: int, payload_hex: str):
        """Analyze payload structure and suggest meanings"""
        payload = bytes.fromhex(payload_hex)
        logger.info(f"\nPayload Analysis for 0x{command:02X}:")
        logger.info(f"  Hex: {payload_hex}")
        logger.info(f"  Length: {len(payload)} bytes")
        logger.info(f"  Bytes: {list(payload)}")
        
        # Try common interpretations
        if len(payload) >= 2:
            u16_be = struct.unpack('>H', payload[:2])[0]
            u16_le = struct.unpack('<H', payload[:2])[0]
            logger.info(f"  As uint16 BE: {u16_be} (0x{u16_be:04X})")
            logger.info(f"  As uint16 LE: {u16_le} (0x{u16_le:04X})")
            
        if len(payload) >= 4:
            u32_be = struct.unpack('>I', payload[:4])[0]
            u32_le = struct.unpack('<I', payload[:4])[0]
            logger.info(f"  As uint32 BE: {u32_be} (0x{u32_be:08X})")
            logger.info(f"  As uint32 LE: {u32_le} (0x{u32_le:08X})")
            
        # Check for ASCII
        try:
            text = payload.decode('ascii')
            if text.isprintable():
                logger.info(f"  As ASCII: '{text}'")
        except:
            pass
    
    def save_results(self, filename: str = None):
        """Save investigation results"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tests/fuzz_results/investigation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\nResults saved to {filename}")


def interactive_mode(investigator: CommandInvestigator):
    """Interactive command investigation"""
    print("\n" + "=" * 60)
    print("PMR-171 Command Investigation - Interactive Mode")
    print("=" * 60)
    print("\nCommands:")
    print("  investigate <hex>  - Investigate a command (e.g., investigate 0x2E)")
    print("  send <hex> <data>  - Send command with data (e.g., send 0x2E 0000)")
    print("  consistency <hex>  - Test response consistency")
    print("  list               - List discovered commands")
    print("  quit               - Exit")
    print()
    
    while True:
        try:
            cmd = input(">>> ").strip()
            
            if cmd.lower() in ['quit', 'exit', 'q']:
                break
                
            elif cmd.lower() == 'list':
                print("\nDiscovered Commands (Priority Order):")
                for priority in ['HIGH', 'MEDIUM', 'LOW']:
                    print(f"\n{priority} Priority:")
                    for cmd_id, info in sorted(DISCOVERED_COMMANDS.items()):
                        if info['priority'] == priority:
                            print(f"  0x{cmd_id:02X}: {info['name']} - {info['returns']}")
                            if 'note' in info:
                                print(f"         ({info['note']})")
                                
            elif cmd.lower().startswith('investigate '):
                hex_str = cmd.split()[1]
                command = int(hex_str, 16)
                investigator.investigate_command(command)
                
            elif cmd.lower().startswith('send '):
                parts = cmd.split()
                command = int(parts[1], 16)
                data = bytes.fromhex(parts[2]) if len(parts) > 2 else b''
                result = investigator.send_command(command, data)
                if result.get('success') and result.get('response'):
                    payload = result['response']['payload']
                    if payload:
                        investigator.analyze_payload_structure(command, payload)
                        
            elif cmd.lower().startswith('consistency '):
                hex_str = cmd.split()[1]
                command = int(hex_str, 16)
                investigator.compare_responses(command)
                
            else:
                print("Unknown command. Type 'quit' to exit or 'list' for commands.")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Investigate discovered PMR-171 UART commands'
    )
    parser.add_argument('--port', required=True, help='Serial port')
    parser.add_argument('--command', help='Command to investigate (e.g., 0x2E)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--consistency', action='store_true', help='Test response consistency')
    
    args = parser.parse_args()
    
    investigator = CommandInvestigator(args.port)
    
    try:
        if not investigator.connect():
            return 1
        
        if args.interactive:
            interactive_mode(investigator)
        elif args.command:
            command = int(args.command, 16)
            investigator.investigate_command(command)
            if args.consistency:
                investigator.compare_responses(command)
        else:
            # Default: investigate high-priority commands
            logger.info("Investigating HIGH priority commands...")
            for cmd_id, info in DISCOVERED_COMMANDS.items():
                if info['priority'] == 'HIGH':
                    investigator.investigate_command(cmd_id, iterations=3)
                    time.sleep(0.5)
        
        investigator.save_results()
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nInvestigation interrupted")
        investigator.save_results()
        return 1
    except Exception as e:
        logger.error(f"Investigation failed: {e}", exc_info=True)
        return 1
    finally:
        investigator.disconnect()


if __name__ == '__main__':
    sys.exit(main())
