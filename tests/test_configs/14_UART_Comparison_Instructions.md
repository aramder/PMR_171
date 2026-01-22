# Test 14: UART Capture Comparison - Manufacturer vs Our CPS

## Purpose
Compare UART write transactions between the manufacturer's CPS and our CPS to identify what's causing radio crashes when we write DMR configurations.

## Problem
Both Test 13 and Test 13A cause the radio to crash when written. We need to identify what we're doing differently from the manufacturer's software.

## Test Configuration
Configure 10 channels in manufacturer's software matching Test 13A layout:

| Ch# | Name | Type | Frequency | Call Type | DMR/DFM | Slot | DMR ID | Call ID | CC | CTCSS TX | CTCSS RX |
|-----|------|------|-----------|-----------|---------|------|--------|---------|----|---------|---------| 
| 0 | CF0_CH0 | DMR | 446.000 | Private | DFM | 1 | 3107683 | 1 | 1 | 67.0 | 67.0 |
| 1 | CF1_CH1 | DMR | 446.000 | Group | DMR | 1 | 3107683 | 9 | 1 | 71.9 | 71.9 |
| 2 | CF2_CH2 | DMR | 446.000 | All Call | DMR | 1 | 3107683 | 16 | 1 | 77.0 | 77.0 |
| 3 | CF0_CH3 | DMR | 446.000 | Private | DFM | 1 | 3107683 | 10000 | 1 | 82.5 | 82.5 |
| 4 | CF1_CH4 | DMR | 446.000 | Group | DMR | 1 | 3107683 | 91 | 1 | 88.5 | 88.5 |
| 5 | CF2_CH5 | DMR | 446.000 | All Call | DMR | 1 | 3107683 | 16 | 1 | 94.8 | 94.8 |
| 6 | ANALOG_REF | Analog | 446.000 | N/A | N/A | N/A | N/A | N/A | N/A | 100.0 | 100.0 |
| 7 | CF0_TS2 | DMR | 446.000 | Private | DFM | 2 | 3107683 | 1 | 1 | 103.5 | 103.5 |
| 8 | CF1_TS2 | DMR | 446.000 | Group | DMR | 2 | 3107683 | 9 | 1 | 107.2 | 107.2 |
| 9 | CF2_ALLCALL | DMR | 446.000 | All Call | DMR | 1 | 3107683 | 16 | 1 | 110.9 | 110.9 |

**Key Settings:**
- All frequencies: 446.000 MHz
- DMR ID: 3107683
- Color Code: 1 (both RX and TX)
- callFormat mapping: 0=Private, 1=Group, 2=All Call
- Display mode: Alternate between DFM and DMR if possible
- CTCSS tones: Sequential standard tones (67.0 Hz through 110.9 Hz)
- CTCSS TX = CTCSS RX for all channels (matched squelch)

## Test Procedure

### Part 1: Capture Manufacturer's Write

1. **Set up UART monitoring:**
   ```
   - Connect radio to PC via USB
   - Open Serial Port Monitor (or equivalent)
   - Monitor radio's COM port
   - Settings: 115200 baud, 8N1
   - Start recording/capturing
   ```

2. **Configure in manufacturer's software:**
   - Open manufacturer's CPS
   - Configure all 10 channels as specified in table above
   - Pay special attention to:
     - Setting DMR vs DFM display mode correctly
     - Call types (Private, Group, All)
     - Timeslot settings
   
3. **Write to radio:**
   - Write configuration to radio
   - Wait for successful completion
   - Verify radio doesn't crash
   - Verify channels display correctly on radio

4. **Save capture:**
   - Stop UART recording
   - Save as `tests/test_configs/Results/14_manufacturer_write_capture.spm` (or .txt)
   - Export as text if using Serial Port Monitor

5. **Read back from radio:**
   - Use manufacturer's software to read from radio
   - Save configuration if possible
   - Note all channel settings

### Part 2: Capture Our CPS Write (For Comparison)

6. **Reset capture:**
   - Clear previous capture data
   - Start new recording session

7. **Write with our CPS:**
   - Open PMR-171 CPS GUI
   - File → Open → `tests/test_configs/13a_dmr_dfm_safe_test.json`
   - Radio → Write to Radio
   - Observe if crash occurs
   - Note at what point crash happens if it does

8. **Save our capture:**
   - Stop UART recording
   - Save as `tests/test_configs/Results/14_our_cps_write_capture.spm` (or .txt)
   - Export as text

### Part 3: Analysis

9. **Compare captures:**
   - Open both capture files
   - Compare packet sequences
   - Look for differences in:
     - Initialization sequence
     - Packet structure
     - Data values
     - Command sequences
     - Checksums
   
10. **Identify crash point:**
    - If our write crashes, identify which packet causes it
    - Compare that packet to manufacturer's equivalent
    - Note any missing fields or incorrect values

## Key Things to Look For

1. **Initialization Differences:**
   - Does manufacturer send additional setup commands?
   - Are there any special handshake sequences?

2. **Packet Structure:**
   - Are packet sizes the same?
   - Are checksums calculated correctly?
   - Are there any padding bytes?

3. **Field Values:**
   - Check DMR-specific fields
   - Look for additional fields we're not setting
   - Compare byte-by-byte for each channel

4. **DMR vs DFM Display Control:**
   - Identify which bytes differ between DMR and DFM channels
   - This should reveal the actual field controlling the display

5. **Missing Fields:**
   - Are there fields the manufacturer sets that we don't?
   - Are there initialization values we're missing?

## Expected Outcome

By comparing the two captures, we should identify:
1. **What's causing the crash** - missing fields, incorrect values, or wrong sequence
2. **The DMR/DFM display control field** - by comparing channels with different display modes
3. **Any other missing functionality** - additional fields we need to implement

## Files

- Test config: `tests/test_configs/13a_dmr_dfm_safe_test.json`
- Manufacturer capture: `tests/test_configs/Results/14_manufacturer_write_capture.spm`
- Our CPS capture: `tests/test_configs/Results/14_our_cps_write_capture.spm`
- Analysis results: `tests/test_configs/Results/14_UART_Analysis.md`

## Next Steps After Analysis

Once differences are identified:
1. Update our code to match manufacturer's approach
2. Create Test 15 to verify fixes
3. Test that radio no longer crashes
4. Verify DMR/DFM display control works correctly
5. Update documentation with findings
