# PMR-171 UART Read/Write Verification Testing

This document describes the automated UART verification test system for validating the PMR-171 radio read/write functionality.

## Overview

The `tests/test_uart_read_write_verify.py` script performs comprehensive validation of the UART communication implementation by:

1. Reading current channel state from radio
2. Writing modified test data
3. Reading back to verify changes
4. Restoring original data
5. Verifying restoration

This ensures the UART implementation correctly handles all channel data fields and doesn't corrupt existing radio configurations.

## Test Script Location

```
tests/test_uart_read_write_verify.py
```

## Features

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--port PORT` | `-p` | Serial port (e.g., COM3, /dev/ttyUSB0). Auto-detects if not specified. |
| `--channels N` | `-c` | Number of channels to test (default: 10) |
| `--dry-run` | `-n` | Read-only mode - no writes to radio |
| `--verbose` | `-v` | Enable detailed debug logging |
| `--list-ports` | `-l` | List available serial ports and exit |
| `--yes` | `-y` | Skip confirmation prompt (auto-confirm writes) |

### Usage Examples

```bash
# List available serial ports
python tests/test_uart_read_write_verify.py --list-ports

# Run with default settings (10 random channels, auto-detect port)
python tests/test_uart_read_write_verify.py

# Run with specific COM port
python tests/test_uart_read_write_verify.py --port COM3

# Test 5 channels with verbose output
python tests/test_uart_read_write_verify.py --channels 5 --verbose

# Dry run mode (read-only, safe for verification)
python tests/test_uart_read_write_verify.py --dry-run

# Auto-confirm writes (for automated testing)
python tests/test_uart_read_write_verify.py --port COM3 --yes

# Run via pytest
python -m pytest tests/test_uart_read_write_verify.py -v
```

## Test Flow

For each channel tested, the script performs the following phases:

### Phase 1: Read Original Data
- Reads the current channel configuration from the radio
- Stores this as the "before" snapshot for later restoration

### Phase 2: Write Test Data
- Generates test data with varied:
  - Frequencies (VHF/UHF bands)
  - Modes (NFM, AM, USB, LSB, WFM)
  - CTCSS tones (various frequencies)
  - Channel names (various lengths and characters)
- Writes this test data to the radio

### Phase 3: Verify Write
- Reads the channel back from the radio
- Compares with expected test data
- Reports any mismatches with detailed hex dumps

### Phase 4: Restore Original
- Writes the original "before" snapshot back to the radio
- Ensures the channel is returned to its pre-test state

### Phase 5: Verify Restoration
- Reads the channel one more time
- Confirms the original data was restored correctly

## Test Data Variations

The script tests various data combinations to ensure comprehensive coverage:

### Test Frequencies
```python
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
```

### Test Channel Names
```python
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
```

### Test CTCSS Tones
```python
TEST_CTCSS_INDICES = [0, 1, 10, 19, 25, 38, 50, 55]
# 0 = Off
# 1 = 67.0 Hz
# 10 = 91.5 Hz
# 19 = 123.0 Hz
# 25 = 150.0 Hz
# 38 = 189.9 Hz
# 50 = 233.6 Hz
# 55 = 254.1 Hz
```

### Test Modes
```python
TEST_MODES = [Mode.NFM, Mode.AM, Mode.USB, Mode.LSB, Mode.WFM]
```

## Channel Selection Strategy

The script selects channels from across the full channel range to test different memory areas:

- **Low channels (0-99)**: Tests beginning of memory
- **Middle channels (400-599)**: Tests middle memory area
- **High channels (900-999)**: Tests end of memory

This ensures any memory addressing issues are detected regardless of channel position.

## Safety Features

### Automatic Backup
- Original channel data is always read and stored before any modifications
- Data is restored automatically after each test, regardless of success/failure

### Confirmation Prompt
- By default, the script prompts for confirmation before writing
- Use `--dry-run` for read-only testing
- Use `--yes` to skip confirmation (for automated testing)

### Error Recovery
- If a write fails, the script still attempts to restore original data
- Detailed error messages help diagnose issues
- All exceptions are caught and reported

## Output Format

### Success Output
```
======================================================================
UART READ/WRITE VERIFICATION TEST SUMMARY
======================================================================
Total Channels Tested: 5
  [PASS] Passed: 5
  [FAIL] Failed: 0
  [SKIP] Skipped: 0

======================================================================
OVERALL RESULT: PASSED
======================================================================
```

### Failure Output (Example)
```
======================================================================
UART READ/WRITE VERIFICATION TEST SUMMARY
======================================================================
Total Channels Tested: 5
  [PASS] Passed: 4
  [FAIL] Failed: 1
  [SKIP] Skipped: 0

----------------------------------------------------------------------
FAILED TESTS:

  Channel 50: verify_write
    Error: Verification failed - data mismatch after write
    Details:
    - RX Freq: expected 144000000 (144.000000 MHz), got 144000001 (144.000001 MHz)

  Expected:
Index: 0032
RX Mode: 06
TX Mode: 06
RX Freq: 08954400 (144.000000 MHz)
TX Freq: 08963040 (144.600000 MHz)
RX CTCSS: 00 (Off)
TX CTCSS: 01 (67.0)
Name: 'TEST_CH' (544553545f4348)

  Actual:
Index: 0032
RX Mode: 06
TX Mode: 06
RX Freq: 08954401 (144.000001 MHz)
...

======================================================================
OVERALL RESULT: FAILED
======================================================================
```

## Test Results Log

### January 19, 2026 - Initial Validation

**Configuration:**
- Port: COM3
- Channels tested: 5
- Mode: Full read/write/verify

**Channels Tested:**
| Channel | Frequency | Mode | RX Tone | TX Tone | Name |
|---------|-----------|------|---------|---------|------|
| 24 | 144.0000 MHz | NFM | Off | 67.0 Hz | TEST_CH |
| 52 | 146.5200 MHz | AM | 67.0 Hz | 91.5 Hz | ABCDEFGHIJK |
| 78 | 147.9990 MHz | USB | 91.5 Hz | 123.0 Hz | 123456789 |
| 455 | 222.0000 MHz | LSB | 123.0 Hz | 150.0 Hz | A |
| 964 | 430.0000 MHz | WFM | 150.0 Hz | 189.9 Hz | (empty) |

**Results:**
```
Total Channels Tested: 5
  [PASS] Passed: 5
  [FAIL] Failed: 0
  [SKIP] Skipped: 0

OVERALL RESULT: PASSED
```

**Verified Functionality:**
- ✓ Reading and writing channel data
- ✓ Multiple modes (NFM, AM, USB, LSB, WFM)
- ✓ CTCSS tone encoding (RX/TX independent)
- ✓ Channel names up to 11 characters
- ✓ VHF frequencies (144-148 MHz)
- ✓ UHF frequencies (222 MHz, 430 MHz)
- ✓ Empty/unused channels vs programmed channels
- ✓ Data restoration after testing

## Pytest Integration

The script can also be run via pytest for integration with CI/CD pipelines:

```bash
# Run all UART tests
python -m pytest tests/test_uart_read_write_verify.py -v

# Run specific test
python -m pytest tests/test_uart_read_write_verify.py::TestUARTReadWriteVerify::test_radio_connection -v
```

### Available Pytest Tests

| Test | Description |
|------|-------------|
| `test_radio_connection` | Verifies radio is connected and responsive |
| `test_read_channel` | Tests reading a single channel |
| `test_write_and_verify_channel` | Tests write/verify cycle on one channel |
| `test_full_verification_cycle` | Full test on all selected channels |

## Troubleshooting

### "No serial ports found"
- Ensure the radio is connected and powered on
- Check that the USB driver is installed (CH340 or similar)
- Try running `--list-ports` to see available ports

### "Failed to connect to radio"
- Radio may not be in programming mode
- Check DTR/RTS settings (script sets both high)
- Try disconnecting and reconnecting the cable
- Ensure no other software is using the COM port

### "Timeout waiting for packet header"
- Radio may have disconnected or lost sync
- Try reducing the number of channels tested
- Increase delay between operations if needed

### "CRC verification failed"
- Serial communication issue
- Check cable connections
- Reduce baud rate if needed (modify in pmr171_uart.py)

## Related Files

- `pmr_171_cps/radio/pmr171_uart.py` - UART communication implementation
- `docs/Pmr171_Protocol.md` - Protocol documentation
- `TODO.md` - Full specification of test requirements

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-19 | 1.0 | Initial implementation with full test coverage |
