# PMR-171 UART Fuzzing Investigation

**Date:** January 21, 2026  
**Purpose:** Investigate PMR-171 UART interface to discover unknown commands and features

## Overview

This document describes the systematic fuzzing of the PMR-171 UART interface to identify:
- Unknown or undocumented command IDs
- Hidden diagnostic or configuration modes
- Alternative packet structures
- Edge cases and boundary conditions
- Additional DMR or feature-specific commands

## Methodology

### 1. Command ID Space Exploration

The PMR-171 uses a single-byte command field in its packet structure. We systematically test all possible command values (0x00-0xFF) to discover which ones elicit responses from the radio.

**Known Commands (from protocol documentation):**
- `0x07` - PTT Control
- `0x0A` - Mode Setting
- `0x0B` - Status Synchronization
- `0x27` - Equipment Type Recognition
- `0x28` - Power Class
- `0x29` - RIT Setting
- `0x39` - Spectrum Data Request
- `0x40` - Channel Write
- `0x41` - Channel Read
- `0x43` - DMR Data Write
- `0x44` - DMR Data Read

### 2. Payload Variation Testing

For each command, we test various payload configurations:
- Empty payloads (0 bytes)
- Minimal payloads (2 bytes - channel index format)
- Standard payloads (26 bytes - full channel data)
- Oversized payloads (up to 255 bytes)
- Boundary values (0x0000, 0xFFFF, etc.)

### 3. Sequence Testing

Test command sequences to identify dependencies or state machines:
- Write/Read pairs (0x40/0x41, 0x43/0x44)
- Mode changes followed by reads
- Status queries after configuration changes

### 4. Response Pattern Analysis

For each test:
- Record whether the radio responds
- Verify CRC of response packets
- Analyze response command codes
- Compare response data patterns
- Identify correlations with input data

## Fuzzing Script Usage

The fuzzing script `tests/fuzz_uart_commands.py` provides several testing modes:

### Basic Usage

Test all command IDs with known-safe payloads:
```bash
python tests/fuzz_uart_commands.py --port COM6
```

### Test Only Known Commands

Safe mode - tests only documented commands with variations:
```bash
python tests/fuzz_uart_commands.py --port COM6 --known-only
```

### Test Specific Range

Test a subset of command IDs:
```bash
python tests/fuzz_uart_commands.py --port COM6 --range 0x20-0x50
```

### Quick Test

Faster testing with fewer variations:
```bash
python tests/fuzz_uart_commands.py --port COM6 --quick
```

## Safety Considerations

### Write Command Protection

The fuzzer includes safety checks for commands that modify radio memory:
- Commands `0x40` (Channel Write) and `0x43` (DMR Data Write) require explicit user confirmation
- Backup your radio configuration before running full fuzzing tests
- Consider using `--known-only` mode first to minimize risk

### Recommended Testing Approach

1. **Start with known commands**: Run with `--known-only` flag first
2. **Test read commands**: Focus on read operations (0x41, 0x44)
3. **Backup configuration**: Read and save all channels before write testing
4. **Incremental testing**: Test small command ranges at a time
5. **Monitor radio**: Watch for unusual behavior or display changes

## Expected Results

### Known Command Responses

Commands that should reliably respond:

| Command | Expected Response | Response Size |
|---------|-------------------|---------------|
| 0x0B | Status data | Variable (~80+ bytes) |
| 0x27 | Equipment type | Variable |
| 0x39 | Spectrum data | 80 or 256 bytes |
| 0x41 | Channel data | 26 bytes |
| 0x44 | DMR data | 26 bytes |

### Commands with State Dependencies

These commands may only work in certain radio modes:
- `0x07` (PTT Control) - requires appropriate frequency/mode
- `0x0A` (Mode Setting) - may affect subsequent commands
- `0x28` (Power Class) - may have mode-specific constraints

### Potential Discovery Areas

Areas where undocumented commands might exist:

1. **0x00-0x06**: Low command IDs often reserved for system functions
2. **0x0C-0x26**: Gap in known commands
3. **0x2A-0x38**: Gap between RIT and Spectrum commands
4. **0x42**: Between channel read/write commands
5. **0x45-0xFF**: Large unexplored space

## Output Files

The fuzzer generates two files per run:

### 1. JSON Results File
`tests/fuzz_results/fuzz_results_YYYYMMDD_HHMMSS.json`

Contains detailed results for every test:
```json
{
  "metadata": {
    "start_time": "2026-01-21T23:45:00",
    "end_time": "2026-01-21T23:50:00",
    "port": "COM6",
    "total_tests": 512,
    "successful_responses": 45,
    "valid_crc_responses": 45
  },
  "results": [
    {
      "timestamp": "2026-01-21T23:45:01",
      "command": "0x41",
      "command_name": "CHANNEL_READ",
      "description": "Read channel 0",
      "data_sent": "0000",
      "response_received": true,
      "response_command": "0x41",
      "response_data": "...",
      "crc_valid": true
    }
  ]
}
```

### 2. Markdown Summary Report
`tests/fuzz_results/fuzz_results_YYYYMMDD_HHMMSS.md`

Human-readable summary including:
- Test statistics
- Command response rates
- Detailed results for successful responses
- Analysis of discovered patterns

## Analysis Guidelines

### Identifying New Commands

A command is potentially useful if:
1. **Radio responds** with a valid packet (CRC passes)
2. **Response varies** with different input data
3. **Response is consistent** across multiple tests with same input
4. **Payload structure** can be reverse-engineered

### Red Flags

Be cautious of commands that:
- Cause radio to reset or hang
- Produce garbled display output
- Change radio behavior permanently
- Respond inconsistently to same input

### Correlating with Radio Behavior

During fuzzing, monitor:
- Radio display for mode/setting changes
- LED indicators for state changes
- Audio output for tones or signals
- Current draw for power state changes

## Research Questions

### 1. Configuration Commands

Are there commands for:
- Factory reset?
- Firmware update mode?
- Self-test/diagnostics?
- Hardware version query?
- Calibration data access?

### 2. Advanced Features

Potential undocumented features:
- Additional digital modes beyond DMR?
- Encryption settings?
- Repeater configuration?
- Advanced scanning modes?
- Custom function buttons?

### 3. DMR Extended Commands

DMR-specific queries:
- Contact list management?
- Zone/channel group config?
- GPS/APRS data?
- SMS/text messaging?
- Hotspot mode settings?

## Example Findings

### Pattern: Command Pairs

Commands often come in write/read pairs:
- `0x40` (Write) / `0x41` (Read) - Channel data
- `0x43` (Write) / `0x44` (Read) - DMR data

**Hypothesis**: Other pairs might exist following this pattern:
- `0x42` could be related to channel operations
- `0x45` could be another DMR-related command
- Even-numbered commands might be writes, odd-numbered reads

### Pattern: Command Groups

Commands appear to be grouped by function:
- `0x07-0x0B`: Radio control (PTT, mode, status)
- `0x27-0x29`: Settings (equipment, power, RIT)
- `0x39`: Data transfer (spectrum)
- `0x40-0x44`: Memory operations (channel, DMR)

### Pattern: Response Echo

Some commands echo the request:
- Write commands (0x40, 0x43) echo back the same command code
- Read commands (0x41, 0x44) also use same command in response
- This is likely an acknowledgment pattern

## Next Steps

### Phase 1: Safe Exploration
- [x] Document existing packet structure
- [x] Create fuzzing script with safety checks
- [ ] Run `--known-only` test to establish baseline
- [ ] Test command ID ranges with read-only operations

### Phase 2: Command Discovery
- [ ] Systematically test all command IDs (0x00-0xFF)
- [ ] Identify which commands produce responses
- [ ] Document response patterns for new commands
- [ ] Correlate with radio behavior observations

### Phase 3: Payload Analysis
- [ ] For responding commands, test payload variations
- [ ] Identify payload structure and field meanings
- [ ] Test boundary conditions and error handling
- [ ] Document any state-dependent behaviors

### Phase 4: Feature Testing
- [ ] Test discovered commands in different radio modes
- [ ] Verify commands work consistently
- [ ] Document any useful new features
- [ ] Update protocol documentation

## Related Documentation

- [PMR-171 Protocol Documentation](Pmr171_Protocol.md)
- [UART Testing Report](UART_Testing.md)
- [UART Reverse Engineering](UART_Reverse_Engineering_Report.md)
- [DMR Display Investigation](DMR_Display_Investigation.md)

## Safety Disclaimer

⚠️ **WARNING**: Fuzzing can potentially:
- Corrupt radio configuration
- Put radio in unexpected states
- Damage firmware (unlikely but possible)
- Void warranty

**Always**:
- Back up your configuration first
- Test on non-critical channels
- Monitor radio behavior during testing
- Have a way to factory reset if needed
- Start with safe, read-only operations

## Contributing

If you discover new commands or features:
1. Document the command ID and purpose
2. Describe the packet structure
3. Note any prerequisites or state requirements
4. Provide example packets with CRC
5. Test for consistency and side effects
6. Update the protocol documentation

## References

- PMR-171 FCC Filing: https://fcc.report/FCC-ID/2BEJV-PMR-171/7105057.pdf
- Project Repository: https://github.com/aramder/PMR_171
