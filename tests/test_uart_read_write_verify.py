#!/usr/bin/env python3
"""
UART Read/Write Verification Test Script for PMR-171 Radio

This script validates the UART implementation by performing read/write/verify
cycles on randomly selected channels, then restoring the original data.

Test Flow (per channel):
  1. Read current state from radio (store as "before" snapshot)
  2. Modify channel data with known test values
  3. Write modified channel to radio
  4. Read channel back from radio (store as "after" snapshot)
  5. Compare "after" snapshot with expected values
  6. Restore original channel data (write "before" snapshot back)
  7. Verify restoration by reading again

Usage:
  # Run with pytest
  python -m pytest tests/test_uart_read_write_verify.py -v
  
  # Run standalone with default settings (10 random channels)
  python tests/test_uart_read_write_verify.py
  
  # Run with specific channel count
  python tests/test_uart_read_write_verify.py --channels 5
  
  # Run with specific COM port
  python tests/test_uart_read_write_verify.py --port COM6
  
  # Dry run (read-only, no writes)
  python tests/test_uart_read_write_verify.py --dry-run

Author: PMR-171 CPS Project
Date: January 2026
"""

import argparse
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit('\\', 2)[0].rsplit('/', 2)[0])

from pmr_171_cps.radio.pmr171_uart import (
    PMR171Radio,
    ChannelData,
    Mode,
    CTCSS_TONES,
    list_serial_ports,
    PMR171Error,
    ConnectionError,
    CommunicationError,
    TimeoutError,
    CRCError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Configuration
# ============================================================================

@dataclass
class TestConfig:
    """Configuration for UART verification tests"""
    port: str = ""  # COM port (auto-detect if empty)
    channels: int = 10  # Number of channels to test
    dry_run: bool = False  # If True, read-only mode (no writes)
    channel_range: Tuple[int, int] = (0, 999)  # Valid channel range
    timeout: float = 2.0  # Serial timeout
    delay_between_ops: float = 0.1  # Delay between operations (seconds)
    

@dataclass
class TestResult:
    """Result of a single channel test"""
    channel_index: int
    success: bool
    phase: str  # Phase where failure occurred (if any)
    error_message: str = ""
    original_data: Optional[ChannelData] = None
    test_data: Optional[ChannelData] = None
    readback_data: Optional[ChannelData] = None
    restored_data: Optional[ChannelData] = None
    mismatch_details: str = ""


@dataclass
class TestSummary:
    """Summary of all test results"""
    total_channels: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_channels += 1
        if result.success:
            self.passed += 1
        else:
            self.failed += 1
    
    def add_skip(self, reason: str):
        self.skipped += 1
        self.errors.append(f"SKIP: {reason}")
    
    def print_summary(self):
        """Print formatted test summary"""
        print("\n" + "=" * 70)
        print("UART READ/WRITE VERIFICATION TEST SUMMARY")
        print("=" * 70)
        print(f"Total Channels Tested: {self.total_channels}")
        print(f"  [PASS] Passed: {self.passed}")
        print(f"  [FAIL] Failed: {self.failed}")
        print(f"  [SKIP] Skipped: {self.skipped}")
        
        if self.failed > 0:
            print("\n" + "-" * 70)
            print("FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"\n  Channel {result.channel_index}: {result.phase}")
                    print(f"    Error: {result.error_message}")
                    if result.mismatch_details:
                        print(f"    Details:\n{result.mismatch_details}")
        
        if self.errors:
            print("\n" + "-" * 70)
            print("ERRORS/SKIPS:")
            for error in self.errors:
                print(f"  {error}")
        
        print("\n" + "=" * 70)
        overall = "PASSED" if self.failed == 0 and self.passed > 0 else "FAILED"
        print(f"OVERALL RESULT: {overall}")
        print("=" * 70)


# ============================================================================
# Test Data Generation
# ============================================================================

# Test frequencies across VHF/UHF bands
TEST_FREQUENCIES = [
    144_000_000,   # 2m band start
    146_520_000,   # 2m calling freq
    147_999_000,   # 2m band edge
    222_000_000,   # 1.25m band
    430_000_000,   # 70cm band start
    446_000_000,   # FRS/GMRS
    449_950_000,   # 70cm band edge
    462_562_500,   # FRS exact freq
    467_712_500,   # FRS exact freq
    100_000_000,   # Edge case - low
    500_000_000,   # Edge case - high
]

# Test channel names
TEST_NAMES = [
    "TEST_CH",     # Standard test name
    "ABCDEFGHIJK", # Max length (11 chars + null)
    "123456789",   # Numeric name
    "A",           # Single char
    "",            # Empty name
    "test lower",  # Lowercase
    "MIX_123_ab",  # Mixed chars
    "REPEATER-1",  # Common naming style
    "WX CHANNEL",  # Space in name
    "EMERGENCY!",  # Punctuation
]

# Test CTCSS tone indices (0 = off, then various tones)
TEST_CTCSS_INDICES = [0, 1, 10, 19, 25, 38, 50, 55]  # Off + various tones

# Test modes
TEST_MODES = [Mode.NFM, Mode.AM, Mode.USB, Mode.LSB, Mode.WFM]


def generate_test_data(original: ChannelData, test_id: int) -> ChannelData:
    """
    Generate test data that differs from the original channel.
    
    Args:
        original: Original channel data
        test_id: Test identifier for deterministic variation
        
    Returns:
        Modified ChannelData for testing
    """
    # Select test values based on test_id for reproducibility
    freq_idx = test_id % len(TEST_FREQUENCIES)
    name_idx = test_id % len(TEST_NAMES)
    ctcss_idx = test_id % len(TEST_CTCSS_INDICES)
    mode_idx = test_id % len(TEST_MODES)
    
    # Generate test frequency (different from original)
    test_rx_freq = TEST_FREQUENCIES[freq_idx]
    # TX freq slightly offset for split testing
    test_tx_freq = test_rx_freq + (600_000 if test_id % 2 == 0 else 0)
    
    # Generate test name
    test_name = TEST_NAMES[name_idx]
    
    # Generate test tones
    test_rx_ctcss = TEST_CTCSS_INDICES[ctcss_idx]
    test_tx_ctcss = TEST_CTCSS_INDICES[(ctcss_idx + 1) % len(TEST_CTCSS_INDICES)]
    
    # Generate test mode
    test_mode = TEST_MODES[mode_idx]
    
    return ChannelData(
        index=original.index,
        rx_mode=test_mode,
        tx_mode=test_mode,
        rx_freq_hz=test_rx_freq,
        tx_freq_hz=test_tx_freq,
        rx_ctcss_index=test_rx_ctcss,
        tx_ctcss_index=test_tx_ctcss,
        name=test_name
    )


# ============================================================================
# Comparison and Verification
# ============================================================================

def channel_to_hex(channel: ChannelData) -> str:
    """Convert channel data to hex string for debugging"""
    data = channel.to_dict()
    hex_parts = []
    hex_parts.append(f"Index: {channel.index:04X}")
    hex_parts.append(f"RX Mode: {channel.rx_mode:02X}")
    hex_parts.append(f"TX Mode: {channel.tx_mode:02X}")
    hex_parts.append(f"RX Freq: {channel.rx_freq_hz:08X} ({channel.rx_freq_mhz:.6f} MHz)")
    hex_parts.append(f"TX Freq: {channel.tx_freq_hz:08X} ({channel.tx_freq_mhz:.6f} MHz)")
    hex_parts.append(f"RX CTCSS: {channel.rx_ctcss_index:02X} ({channel.rx_ctcss_hz or 'Off'})")
    hex_parts.append(f"TX CTCSS: {channel.tx_ctcss_index:02X} ({channel.tx_ctcss_hz or 'Off'})")
    hex_parts.append(f"Name: '{channel.name}' ({channel.name.encode('ascii', errors='replace').hex()})")
    return "\n".join(hex_parts)


def compare_channels(expected: ChannelData, actual: ChannelData) -> Tuple[bool, str]:
    """
    Compare two channels and return mismatch details.
    
    Args:
        expected: Expected channel data
        actual: Actual channel data read from radio
        
    Returns:
        Tuple of (match_success, mismatch_details_string)
    """
    mismatches = []
    
    # Compare each field
    if expected.rx_mode != actual.rx_mode:
        mismatches.append(f"RX Mode: expected {expected.rx_mode} ({expected.rx_mode_name}), "
                         f"got {actual.rx_mode} ({actual.rx_mode_name})")
    
    if expected.tx_mode != actual.tx_mode:
        mismatches.append(f"TX Mode: expected {expected.tx_mode} ({expected.tx_mode_name}), "
                         f"got {actual.tx_mode} ({actual.tx_mode_name})")
    
    if expected.rx_freq_hz != actual.rx_freq_hz:
        mismatches.append(f"RX Freq: expected {expected.rx_freq_hz} ({expected.rx_freq_mhz:.6f} MHz), "
                         f"got {actual.rx_freq_hz} ({actual.rx_freq_mhz:.6f} MHz)")
    
    if expected.tx_freq_hz != actual.tx_freq_hz:
        mismatches.append(f"TX Freq: expected {expected.tx_freq_hz} ({expected.tx_freq_mhz:.6f} MHz), "
                         f"got {actual.tx_freq_hz} ({actual.tx_freq_mhz:.6f} MHz)")
    
    if expected.rx_ctcss_index != actual.rx_ctcss_index:
        mismatches.append(f"RX CTCSS: expected {expected.rx_ctcss_index} ({expected.rx_ctcss_hz or 'Off'}), "
                         f"got {actual.rx_ctcss_index} ({actual.rx_ctcss_hz or 'Off'})")
    
    if expected.tx_ctcss_index != actual.tx_ctcss_index:
        mismatches.append(f"TX CTCSS: expected {expected.tx_ctcss_index} ({expected.tx_ctcss_hz or 'Off'}), "
                         f"got {actual.tx_ctcss_index} ({actual.tx_ctcss_hz or 'Off'})")
    
    # Name comparison (strip and compare - radio may pad/truncate)
    expected_name = expected.name.strip()[:11]  # Radio truncates to 11 chars
    actual_name = actual.name.strip()
    if expected_name != actual_name:
        mismatches.append(f"Name: expected '{expected_name}', got '{actual_name}'")
    
    if mismatches:
        details = "\n".join(f"    - {m}" for m in mismatches)
        hex_dump = f"\n  Expected:\n{channel_to_hex(expected)}\n\n  Actual:\n{channel_to_hex(actual)}"
        return False, details + hex_dump
    
    return True, ""


# ============================================================================
# Channel Selection
# ============================================================================

def select_test_channels(config: TestConfig) -> List[int]:
    """
    Select channels to test.
    
    Strategy:
    - Include some low channels (0-99)
    - Include some middle channels (400-599)
    - Include some high channels (900-999)
    - Random selection within each range
    
    Args:
        config: Test configuration
        
    Returns:
        List of channel indices to test
    """
    min_ch, max_ch = config.channel_range
    total_channels = max_ch - min_ch + 1
    
    # Determine how many channels from each range
    count = min(config.channels, total_channels)
    
    # Define ranges (low, mid, high)
    ranges = [
        (0, 99),      # Low channels
        (400, 599),   # Middle channels  
        (900, 999),   # High channels
    ]
    
    selected = []
    channels_per_range = max(1, count // len(ranges))
    
    for start, end in ranges:
        # Clamp to valid range
        start = max(start, min_ch)
        end = min(end, max_ch)
        if start <= end:
            available = list(range(start, end + 1))
            selected.extend(random.sample(available, min(channels_per_range, len(available))))
    
    # Fill remaining with random channels if needed
    remaining = count - len(selected)
    if remaining > 0:
        all_channels = set(range(min_ch, max_ch + 1)) - set(selected)
        if all_channels:
            selected.extend(random.sample(list(all_channels), min(remaining, len(all_channels))))
    
    # Sort for orderly testing
    selected.sort()
    
    return selected[:config.channels]


# ============================================================================
# Main Test Logic
# ============================================================================

def test_single_channel(
    radio: PMR171Radio,
    channel_index: int,
    test_id: int,
    config: TestConfig
) -> TestResult:
    """
    Test a single channel with read/write/verify/restore cycle.
    
    Args:
        radio: Connected radio interface
        channel_index: Channel to test
        test_id: Test identifier for data generation
        config: Test configuration
        
    Returns:
        TestResult with outcome and details
    """
    result = TestResult(channel_index=channel_index, success=False, phase="init")
    
    try:
        # Phase 1: Read original data
        result.phase = "read_original"
        logger.info(f"Channel {channel_index}: Reading original data...")
        original = radio.read_channel(channel_index)
        result.original_data = original
        logger.debug(f"  Original: {original}")
        time.sleep(config.delay_between_ops)
        
        if config.dry_run:
            # Dry run - just verify we can read
            result.phase = "dry_run_complete"
            result.success = True
            logger.info(f"Channel {channel_index}: DRY RUN - Read successful")
            return result
        
        # Phase 2: Generate and write test data
        result.phase = "write_test"
        test_data = generate_test_data(original, test_id)
        result.test_data = test_data
        logger.info(f"Channel {channel_index}: Writing test data...")
        logger.debug(f"  Test data: {test_data}")
        
        success = radio.write_channel(test_data)
        if not success:
            result.error_message = "Write command returned failure"
            return result
        time.sleep(config.delay_between_ops)
        
        # Phase 3: Read back and verify
        result.phase = "verify_write"
        logger.info(f"Channel {channel_index}: Reading back for verification...")
        readback = radio.read_channel(channel_index)
        result.readback_data = readback
        logger.debug(f"  Readback: {readback}")
        
        match, mismatch_details = compare_channels(test_data, readback)
        if not match:
            result.error_message = "Verification failed - data mismatch after write"
            result.mismatch_details = mismatch_details
            # Still try to restore original
        time.sleep(config.delay_between_ops)
        
        # Phase 4: Restore original data
        result.phase = "restore_original"
        logger.info(f"Channel {channel_index}: Restoring original data...")
        success = radio.write_channel(original)
        if not success:
            result.error_message = "Restore write command returned failure"
            return result
        time.sleep(config.delay_between_ops)
        
        # Phase 5: Verify restoration
        result.phase = "verify_restore"
        logger.info(f"Channel {channel_index}: Verifying restoration...")
        restored = radio.read_channel(channel_index)
        result.restored_data = restored
        
        restore_match, restore_mismatch = compare_channels(original, restored)
        if not restore_match:
            result.error_message = "Restoration verification failed"
            result.mismatch_details = restore_mismatch
            return result
        
        # All phases passed
        if not match:
            # Write verification failed but restoration succeeded
            result.phase = "verify_write"
            return result
        
        result.phase = "complete"
        result.success = True
        logger.info(f"Channel {channel_index}: [PASS] All phases passed")
        return result
        
    except TimeoutError as e:
        result.error_message = f"Timeout: {e}"
        logger.error(f"Channel {channel_index}: Timeout in phase {result.phase}: {e}")
    except CRCError as e:
        result.error_message = f"CRC Error: {e}"
        logger.error(f"Channel {channel_index}: CRC error in phase {result.phase}: {e}")
    except CommunicationError as e:
        result.error_message = f"Communication Error: {e}"
        logger.error(f"Channel {channel_index}: Communication error in phase {result.phase}: {e}")
    except Exception as e:
        result.error_message = f"Unexpected error: {e}"
        logger.error(f"Channel {channel_index}: Unexpected error in phase {result.phase}: {e}")
    
    return result


def run_verification_tests(config: TestConfig) -> TestSummary:
    """
    Run the full verification test suite.
    
    Args:
        config: Test configuration
        
    Returns:
        TestSummary with all results
    """
    summary = TestSummary()
    
    # Auto-detect port if not specified
    if not config.port:
        ports = list_serial_ports()
        if not ports:
            summary.add_skip("No serial ports found")
            return summary
        
        # Look for likely PMR-171 port (often CH340 or similar USB-UART)
        for port_info in ports:
            port = port_info['port']
            desc = port_info['description'].lower()
            if 'ch340' in desc or 'usb' in desc or 'serial' in desc:
                config.port = port
                break
        
        if not config.port:
            config.port = ports[0]['port']  # Use first available
        
        logger.info(f"Auto-detected serial port: {config.port}")
    
    # Select channels to test
    channels = select_test_channels(config)
    logger.info(f"Selected {len(channels)} channels for testing: {channels}")
    
    # Connect to radio
    try:
        radio = PMR171Radio(config.port, timeout=config.timeout)
        radio.connect()
        logger.info(f"Connected to radio on {config.port}")
    except ConnectionError as e:
        summary.add_skip(f"Failed to connect to radio: {e}")
        return summary
    except Exception as e:
        summary.add_skip(f"Connection error: {e}")
        return summary
    
    try:
        # Test each channel
        for i, channel_index in enumerate(channels):
            logger.info(f"\n--- Testing channel {channel_index} ({i+1}/{len(channels)}) ---")
            result = test_single_channel(radio, channel_index, i, config)
            summary.add_result(result)
            
            if not result.success:
                logger.warning(f"Channel {channel_index} FAILED in phase: {result.phase}")
    
    finally:
        radio.disconnect()
        logger.info("Disconnected from radio")
    
    return summary


# ============================================================================
# Pytest Integration
# ============================================================================

# Global config for pytest - can be modified by conftest.py or command line
_pytest_config = TestConfig()


def pytest_configure(config):
    """Configure pytest with command line options"""
    global _pytest_config
    
    if hasattr(config.option, 'uart_port') and config.option.uart_port:
        _pytest_config.port = config.option.uart_port
    if hasattr(config.option, 'uart_channels') and config.option.uart_channels:
        _pytest_config.channels = config.option.uart_channels
    if hasattr(config.option, 'uart_dry_run') and config.option.uart_dry_run:
        _pytest_config.dry_run = config.option.uart_dry_run


@pytest.fixture(scope="module")
def radio_connection():
    """Pytest fixture for radio connection"""
    config = _pytest_config
    
    if not config.port:
        ports = list_serial_ports()
        if not ports:
            pytest.skip("No serial ports available")
        config.port = ports[0]['port']
    
    try:
        radio = PMR171Radio(config.port, timeout=config.timeout)
        radio.connect()
        yield radio
    except Exception as e:
        pytest.skip(f"Cannot connect to radio: {e}")
    finally:
        if 'radio' in locals():
            radio.disconnect()


@pytest.fixture(scope="module")
def test_channels():
    """Pytest fixture for channel selection"""
    return select_test_channels(_pytest_config)


class TestUARTReadWriteVerify:
    """Pytest test class for UART verification"""
    
    def test_radio_connection(self, radio_connection):
        """Test that radio is connected and responsive"""
        assert radio_connection.is_connected
        
        # Try to get radio info
        info = radio_connection.get_radio_info()
        assert info.get('connected', False) or 'error' not in info
    
    def test_read_channel(self, radio_connection, test_channels):
        """Test reading channels from radio"""
        if not test_channels:
            pytest.skip("No test channels selected")
        
        channel_index = test_channels[0]
        channel = radio_connection.read_channel(channel_index)
        
        assert channel is not None
        assert channel.index == channel_index
        assert 0 <= channel.rx_freq_hz <= 600_000_000  # Reasonable freq range
    
    @pytest.mark.skipif(_pytest_config.dry_run, reason="Dry run mode - skipping writes")
    def test_write_and_verify_channel(self, radio_connection, test_channels):
        """Test writing and verifying a channel"""
        if not test_channels:
            pytest.skip("No test channels selected")
        
        channel_index = test_channels[0]
        
        # Read original
        original = radio_connection.read_channel(channel_index)
        
        try:
            # Write test data
            test_data = generate_test_data(original, 0)
            success = radio_connection.write_channel(test_data)
            assert success, "Write command failed"
            
            # Read back and verify
            time.sleep(0.1)
            readback = radio_connection.read_channel(channel_index)
            
            match, details = compare_channels(test_data, readback)
            assert match, f"Verification failed:\n{details}"
            
        finally:
            # Always restore original
            radio_connection.write_channel(original)
    
    @pytest.mark.skipif(_pytest_config.dry_run, reason="Dry run mode - skipping writes")
    def test_full_verification_cycle(self, radio_connection, test_channels):
        """Test full read/write/verify/restore cycle on all selected channels"""
        config = _pytest_config
        summary = TestSummary()
        
        for i, channel_index in enumerate(test_channels):
            result = test_single_channel(radio_connection, channel_index, i, config)
            summary.add_result(result)
        
        # Assert overall success
        assert summary.failed == 0, f"{summary.failed} channels failed verification"


# ============================================================================
# Command Line Interface
# ============================================================================

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="PMR-171 UART Read/Write Verification Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Run with defaults (10 channels, auto-detect port)
  %(prog)s --channels 5         # Test 5 channels
  %(prog)s --port COM6          # Use specific COM port
  %(prog)s --dry-run            # Read-only mode (no writes)
  %(prog)s -v                   # Verbose output
        """
    )
    
    parser.add_argument(
        '--channels', '-c',
        type=int,
        default=10,
        help='Number of channels to test (default: 10)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=str,
        default='',
        help='Serial port (e.g., COM6, /dev/ttyUSB0). Auto-detect if not specified.'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Dry run mode - read only, no writes to radio'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--list-ports', '-l',
        action='store_true',
        help='List available serial ports and exit'
    )
    
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt (auto-confirm writes)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for command line usage"""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # List ports if requested
    if args.list_ports:
        ports = list_serial_ports()
        if ports:
            print("Available serial ports:")
            for p in ports:
                print(f"  {p['port']}: {p['description']}")
        else:
            print("No serial ports found")
        return 0
    
    # Create config
    config = TestConfig(
        port=args.port,
        channels=args.channels,
        dry_run=args.dry_run
    )
    
    print("=" * 70)
    print("PMR-171 UART READ/WRITE VERIFICATION TEST")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Port: {config.port or 'Auto-detect'}")
    print(f"  Channels to test: {config.channels}")
    print(f"  Mode: {'DRY RUN (read-only)' if config.dry_run else 'Full read/write/verify'}")
    print()
    
    if not config.dry_run and not args.yes:
        print("WARNING: This test WILL WRITE to your radio!")
        print("Original channel data will be backed up and restored.")
        print()
        response = input("Continue? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
    elif not config.dry_run:
        print("WARNING: Auto-confirmed with --yes flag. Writing to radio.")
        print()
    
    # Run tests
    summary = run_verification_tests(config)
    
    # Print results
    summary.print_summary()
    
    return 0 if summary.failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
