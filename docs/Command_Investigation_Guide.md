# PMR-171 Unknown Command Investigation Guide

**Date:** January 22, 2026  
**Purpose:** Systematic investigation of discovered UART commands to determine their actual functions

## Quick Start

### Prerequisites
- PMR-171 radio connected via UART (COM3)
- Radio in programming mode
- Python environment with required packages

### Launch Interactive Investigation

```bash
# Start interactive investigation mode
python tests/investigate_commands.py --port COM3 --interactive
```

## Available Interactive Commands

Once in interactive mode, you have these commands:

### `list` - Show Discovered Commands
Lists all commands found during fuzzing, organized by priority:
```
>>> list
```

### `investigate <hex>` - Deep Dive into a Command
Runs systematic tests with different payloads:
```
>>> investigate 0x2E
>>> investigate 0x2D
```

### `consistency <hex>` - Test Response Stability
Sends same command 10 times to check if response varies:
```
>>> consistency 0x2E
```

### `send <hex> <data>` - Custom Payload Test
Send specific command with custom data:
```
>>> send 0x2E 0000
>>> send 0x2D
>>> send 0x20 0100
```

## Investigation Priority

### HIGH Priority Commands (Data Returns)

#### 0x2E - UNKNOWN_2E (30-byte response)
**Status:** Unknown function, returns significant data  
**Investigation Steps:**
1. Test consistency: Does it always return same 30 bytes?
2. Send with different payloads: Does input affect output?
3. Check radio display: Any visible changes?
4. Map byte structure: What do the 30 bytes represent?

**Test Sequence:**
```
>>> consistency 0x2E
>>> send 0x2E
>>> send 0x2E 0000
>>> send 0x2E 0001
>>> send 0x2E FFFF
```

**Expected Analysis:**
- If consistent: Likely reading radio state/configuration
- If varies: May be reading dynamic data (signal strength, battery, etc.)
- Correlate with radio display and behavior

**Potential Functions:**
- Radio status (battery, signal, mode indicators)
- Configuration summary (power level, squelch, etc.)
- Hardware information (version, serial, calibration)
- DMR-specific data (color code, time slot, contact info)

#### 0x2D - UNKNOWN_2D (2-byte response)
**Status:** Unknown function, returns minimal data  
**Investigation Steps:**
1. Test consistency: Always same 2 bytes?
2. Test with different payloads
3. Interpret as uint16 (BE and LE)

**Test Sequence:**
```
>>> consistency 0x2D
>>> send 0x2D
>>> send 0x2D 0000
>>> send 0x2D 0001
```

**Potential Functions:**
- Simple status flag or mode indicator
- Numeric value (RSSI, battery voltage, temperature)
- Configuration toggle state
- Error code or diagnostic value

### MEDIUM Priority Commands (FFT/Spectrum Related)

#### 0x20, 0x21, 0x22, 0x23 - FFT Configuration
**Status:** Believed to be spectrum/FFT configuration  
**Note:** May affect 0x39 spectrum data command behavior

**Investigation Strategy:**
1. Test each command individually
2. Try sequence: 0x20 → 0x21 → 0x22 → 0x23
3. Test with 0x39 before and after
4. Check if they configure FFT window, resolution, or mode

**Test Sequence:**
```
>>> send 0x39 0000      # Baseline spectrum read
>>> send 0x20 0100      # Try FFT config
>>> send 0x39 0000      # Check if spectrum changed
>>> send 0x21 0200
>>> send 0x39 0000
```

#### 0x04 - UNKNOWN_04 (0-2 byte response)
**Status:** Variable response length  
**Note:** Response varies between tests

**Investigation:**
- State-dependent command?
- Async data availability indicator?
- Buffer status query?

### LOW Priority Commands

#### 0x00 - PTT_ALIAS
**Status:** Responds with 0x07 (PTT command)  
**Note:** Likely just an alias for PTT control

#### 0x03, 0x0C-0x10 - Extended Mode Commands
**Status:** Return empty responses  
**Note:** May be mode switches or configuration commands with no feedback

## Byte Structure Analysis

### Analyzing 30-Byte Response (0x2E)

When you get the 30-byte response, analyze it systematically:

#### 1. Record Multiple Samples
```
>>> send 0x2E
# Note response: XX XX XX XX...
>>> send 0x2E
# Check if identical
```

#### 2. Change Radio State and Retest
- Change channel
- Change mode (FM ↔ DMR)
- Change power level
- Change squelch
- Enable/disable features
- Then test 0x2E again and compare

#### 3. Look for Patterns

**Common Patterns in Radio Status Data:**

| Bytes | Typical Content |
|-------|----------------|
| 0-1 | Frequency (BCD or binary) |
| 2-3 | Mode/settings flags |
| 4-7 | CTCSS/DCS codes |
| 8-9 | Power level, squelch |
| 10-15 | DMR-specific (Color Code, Time Slot, etc.) |
| 16-20 | Signal measurements (RSSI, battery) |
| 21-29 | Additional state/version info |

#### 4. Test Byte Interpretation

For each byte or byte pair, try:
- Decimal value
- Hexadecimal value
- BCD encoding
- Bit flags (binary)
- ASCII characters

#### 5. Document Findings

Create a byte map:
```
Byte 0-1:  [Frequency MSB] - Changes with channel
Byte 2:    [Mode flags] - Bit 0: FM/DMR, Bit 1: Power
Byte 3:    [TX/RX flags]
...
```

## Correlation with Radio Behavior

### Visual Indicators to Monitor

While testing commands, watch for:

**Display Changes:**
- Frequency display
- Mode indicator (FM/DMR)
- Channel name
- Icon indicators
- Menu state

**LED Behavior:**
- TX LED
- RX LED
- Scan indicator
- DMR network LED

**Audio Output:**
- Beeps or tones
- Alert sounds
- Volume changes

### Systematic State Testing

**Test Matrix:**

| Radio State | Test 0x2E | Compare Bytes | Notes |
|-------------|-----------|---------------|-------|
| CH 1, FM, Low power | Run test | Baseline | |
| CH 2, FM, Low power | Run test | Compare 0-1 | Freq change? |
| CH 1, FM, High power | Run test | Compare 2-3 | Power flag? |
| CH 1, DMR, Low power | Run test | Compare full | Mode change? |

### Recording Results

Document format:
```
Command: 0x2E
State: CH 1, FM Mode, Low Power, SQL 5
Response: 01 23 45 67 89 AB CD EF... (30 bytes)
Display: "146.520 FM"
Notes: No visible change on radio
```

## Creating Command Reference

### Template for Each Command

```markdown
### 0xXX - COMMAND_NAME

**Function:** [Determined purpose]

**Request Format:**
- Command: 0xXX
- Payload: [Required data format]
- Example: `AB CD 0xXX 00 00 CRC CRC`

**Response Format:**
- Command: 0xXX (echo)
- Payload Length: X bytes
- Data Structure:
  - Bytes 0-1: [Field description]
  - Bytes 2-3: [Field description]
  - ...

**Usage Example:**
```python
# Get radio status
packet = build_packet(0xXX, b'\x00\x00')
response = send_and_receive(packet)
status = parse_status(response)
```

**Notes:**
- [Dependencies, prerequisites]
- [Side effects, warnings]
- [Related commands]

**Discovered:** [Date]
**Verified:** [Date]
**Confidence:** [High/Medium/Low]
```

## Safety Protocols

### Before Testing

1. ✅ Backup radio configuration
2. ✅ Document current radio state
3. ✅ Have factory reset procedure ready
4. ✅ Test on non-critical channels
5. ✅ Monitor radio continuously

### During Testing

1. 🔍 Start with read-only appearing commands
2. 🔍 Test consistency before assuming command is safe
3. 🔍 Watch for unexpected behavior
4. 🔍 Document all observations
5. 🔍 Stop if radio behaves unexpectedly

### After Testing

1. 📝 Verify radio still functions normally
2. 📝 Document all findings
3. 📝 Update command reference
4. 📝 Share discoveries with project

## Advanced Investigation Techniques

### 1. Binary Search for Active Bytes

If command takes payload, find which bytes matter:

```
Test: 00 00 → Response A
Test: FF FF → Response B
If A ≠ B, bytes are significant

Test: FF 00 → Response C
Test: 00 FF → Response D
Identify which byte affects output
```

### 2. Bit Flag Analysis

For status bytes, toggle individual bits:

```
Send: 0x01 (bit 0 set)
Send: 0x02 (bit 1 set)
Send: 0x04 (bit 2 set)
...
Check radio for corresponding changes
```

### 3. Sequence Dependencies

Some commands may require setup:

```
# Test if 0x2E requires mode setting first
send 0x0A 00 00  # Set mode
send 0x2E        # Check if response changes
```

### 4. Comparative Analysis

Compare with known commands:

```
Known: 0x41 reads channel (26 bytes)
Unknown: 0x2E returns data (30 bytes)
Question: Is 0x2E extended channel data?

Test: Read CH1 with 0x41, then 0x2E
Compare: Look for overlapping data
```

## Expected Outcomes

### Success Criteria

By end of investigation session, you should have:

1. ✅ Consistency data for each HIGH priority command
2. ✅ Initial byte structure hypothesis for 0x2E (30 bytes)
3. ✅ Correlation data (what radio states affect responses)
4. ✅ Confidence level on each command's purpose
5. ✅ Documented in investigation results JSON

### Deliverables

1. **Investigation Report** (`investigation_YYYYMMDD_HHMMSS.json`)
   - Raw test results
   - Response data for all tests
   - Timestamps and conditions

2. **Command Reference Document** (update `Pmr171_Protocol.md`)
   - Add newly understood commands
   - Document byte structures
   - Include usage examples

3. **Follow-up Tasks List**
   - Commands needing more testing
   - Hypotheses to verify
   - Related features to explore

## Interactive Mode Tips

### Efficient Workflow

1. **Start with list** to see available commands
2. **Investigate high priority** commands first (0x2E, 0x2D)
3. **Use consistency** to verify stable responses
4. **Document as you go** - take notes outside the tool
5. **Test systematically** - don't skip around randomly

### Keyboard Shortcuts

- **Ctrl+C**: Cancel current operation (use 'quit' to exit properly)
- **Up Arrow**: Recall previous command
- **Tab**: (if implemented) Command completion

### Best Practices

```
# Good: Systematic testing
>>> consistency 0x2E
>>> send 0x2E
>>> send 0x2E 0000
>>> send 0x2E 0001
>>> send 0x2E FFFF

# Less Useful: Random testing
>>> send 0x2E 1234
>>> send 0x04
>>> investigate 0x10
>>> send 0x2E 5678
```

## Troubleshooting

### Radio Not Responding

1. Check connection: Is radio still connected?
2. Try known command: `send 0x41 0000` (read channel)
3. Power cycle radio and reconnect
4. Check programming mode is still active

### Inconsistent Responses

1. Radio state may be changing
2. Command may be reading dynamic data
3. Timing issues - try adding delays
4. Document the variation patterns

### Tool Errors

1. Check serial port permissions
2. Verify Python packages installed
3. Check for firmware updates
4. Review error logs

## Next Steps After Investigation

1. **Update Protocol Documentation**
   - Add command definitions to `Pmr171_Protocol.md`
   - Include byte structure diagrams
   - Add example code

2. **Implement in Library**
   - Add command constants to `pmr171_uart.py`
   - Create helper functions for new commands
   - Add to API documentation

3. **Create Tests**
   - Unit tests for new commands
   - Integration tests with real radio
   - Regression tests to prevent breaking changes

4. **Share Findings**
   - Update README with new capabilities
   - Create issues for follow-up work
   - Document in session summary

## Reference Materials

- [PMR-171 Protocol Documentation](Pmr171_Protocol.md)
- [UART Fuzzing Investigation](UART_Fuzzing_Investigation.md)
- [UART Testing Report](UART_Testing.md)
- [Investigation Tool Source](../tests/investigate_commands.py)

## Contact & Contribution

If you discover new commands or determine their functions:
1. Document thoroughly using this guide
2. Create detailed findings report
3. Submit to project repository
4. Share on project discussions

---

**Remember:** Safety first! Unknown commands could potentially:
- Change critical settings
- Erase configuration
- Put radio in unexpected state

Always backup, document, and test carefully.
