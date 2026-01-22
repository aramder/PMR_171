# Command 0x2E Test Results - RADIO CRASH INCIDENT

**Date:** January 22, 2026, 12:42 AM  
**Test:** Command 0x2E (Parameter Synchronization)  
**Result:** Data received successfully BUT radio crashed  
**Severity:** ⚠️ HIGH - Command may cause instability

---

## Test Summary

The investigation tool successfully sent command 0x2E five times with different payloads and received consistent 30-byte responses. However, **the radio crashed after the test completed**.

### Test Execution

All 5 tests completed successfully:
1. Empty payload - ✓ 30 bytes received
2. Single zero byte - ✓ 30 bytes received  
3. Two zero bytes - ✓ 30 bytes received
4. 0x0100 payload - ✓ 30 bytes received
5. 0x0001 payload - ✓ 30 bytes received

**Response Consistency:** 100% - All responses identical (payload independent)

---

## Received Data

**Raw Hex Response:**
```
0b17150016143232010300a0000f00111a01010064530f004b0f14000501
```

**Byte Array (Decimal):**
```
[11, 23, 21, 0, 22, 20, 50, 50, 1, 3, 0, 160, 0, 15, 0, 17, 26, 1, 1, 0, 100, 83, 15, 0, 75, 15, 20, 0, 5, 1]
```

---

## Data Analysis (Per Manual Specification)

Parsing the 30 bytes according to the official protocol documentation:

| Byte | Parameter | Value (Dec) | Value (Hex) | Interpretation |
|------|-----------|-------------|-------------|----------------|
| 0 | SVOL | 11 | 0x0B | Speaker volume = 11/30 |
| 1 | HVOL | 23 | 0x17 | Headphone volume = 23/80 |
| 2 | MIC | 21 | 0x15 | Microphone gain = 21/100 |
| 3 | CMP | 0 | 0x00 | Compression OFF |
| 4 | BAS | 22 | 0x16 | Bass EQ = 22/40 |
| 5 | TRB | 20 | 0x14 | Treble EQ = 20/40 |
| 6 | RFG | 50 | 0x32 | RF Gain = 50/100 |
| 7 | IFG | 50 | 0x32 | IF Gain = 50/80 |
| 8 | SQL | 1 | 0x01 | Squelch = 1/20 |
| 9 | AGC | 3 | 0x03 | AGC speed = 3/5 |
| 10 | AMP | 0 | 0x00 | Pre-amp = AMPA |
| 11 | NR | 160 | 0xA0 | **⚠️ INVALID - Should be 0 or 1!** |
| 12 | NB | 0 | 0x00 | Noise Blanker OFF |
| 13 | PEAK | 15 | 0x0F | PEAK threshold = 15/20 |
| 14 | SPAN | 0 | 0x00 | Spectrum BW = 48K |
| 15 | REF | 17 | 0x11 | Spectrum ref level = 17/20 |
| 16 | SPEED | 26 | 0x1A | Spectrum refresh = 26/30 |
| 17 | T-CTSS | 1 | 0x01 | TX CTCSS = 67.0 Hz |
| 18 | R-CTSS | 1 | 0x01 | RX CTCSS = 67.0 Hz |
| 19 | L-VOICE | 0 | 0x00 | Preamble rate index = 0 |
| 20 | L-TIME | 100 | 0x64 | Preamble duration = 100 |
| 21 | KEY_MODE | 83 | 0x53 | **⚠️ INVALID - Should be 0-2!** |
| 22 | TX_RX | 15 | 0x0F | TX/RX conv time = 150ms |
| 23 | TRAINING | 0 | 0x00 | CW training OFF |
| 24 | STF | 75 | 0x4B | Side-tone freq = 750 Hz |
| 25 | STG | 15 | 0x0F | Side-tone volume = 15/15 |
| 26 | KEY_SPEED | 20 | 0x14 | CW speed = 20 WPM |
| 27 | DECODE | 0 | 0x00 | CW decode OFF |
| 28 | THRESHOLD | 5 | 0x05 | CW threshold = 5/50 |
| 29 | data_format | 1 | 0x01 | USB format = SDR mode |

---

## ⚠️ ANOMALIES DETECTED

### Invalid Values Found:

1. **Byte 11 (NR) = 160 (0xA0)**
   - **Expected:** 0 or 1 (OFF/ON)
   - **Actual:** 160
   - **Analysis:** This is way out of range! Could indicate memory corruption or protocol mismatch

2. **Byte 21 (KEY_MODE) = 83 (0x53)**
   - **Expected:** 0 (AUTO-L), 1 (AUTO-R), or 2 (KEY)
   - **Actual:** 83
   - **Analysis:** Also invalid! Possible data corruption

### Possible Causes:

1. **Protocol Version Mismatch**
   - Radio firmware may use different byte order or structure
   - Manual may document newer protocol version

2. **Data Corruption During Crash**
   - Radio may have been in unstable state
   - Crash could have corrupted response data

3. **Byte Order/Interpretation Error**
   - Bytes 11 and 21 might be part of multi-byte fields
   - Specification may have errors or updates

---

## Radio Crash Details

**Symptoms:**
- Test completed successfully (all 5 iterations)
- Data received consistently
- Radio crashed AFTER test completion
- Timing suggests crash occurred during/after disconnect

**Crash Timing:**
```
00:42:32 - Connected
00:42:32 - Test started
00:42:34 - Test completed (5 iterations)
00:42:34 - Results saved
[CRASH OCCURRED AFTER THIS POINT]
```

**Possible Crash Causes:**

1. **Command Overload**
   - 5 rapid requests of 0x2E in 2 seconds
   - Radio may not handle rapid polling well
   - Recommendation: Add delays between requests

2. **State Inconsistency**
   - 0x2E reads deep internal state
   - Radio may need to be in specific mode
   - Invalid state during read could cause crash

3. **Firmware Bug**
   - Command 0x2E may have known issues
   - Documented in manual but unstable in practice
   - May require specific preconditions

4. **Buffer Overflow**
   - Rapid repeated access to 30-byte buffer
   - Memory management issue in firmware
   - Crash during cleanup/disconnect

---

## Recommendations

### Immediate Actions

1. **⚠️ USE CAUTION with 0x2E command**
   - Limit to single queries, not rapid polling
   - Add 1-2 second delays between calls
   - Monitor radio for instability

2. **Test with Single Request**
   - Try one 0x2E request only
   - Check if radio remains stable
   - Verify if crash is request-count related

3. **Verify Radio State Before Testing**
   - Ensure radio is idle (not transmitting)
   - Check display is responsive
   - Confirm no ongoing operations

### Investigation Priorities

1. **Test 0x0B Status Command Instead**
   - 0x0B may be more stable
   - Returns even more data (80+ bytes)
   - Could be safer alternative

2. **Test 0x2D (2-byte meter command)**
   - Simpler command, less data
   - May be more stable
   - Good for verifying radio responsiveness

3. **Implement Rate Limiting**
   - Add configurable delay between commands
   - Default to 500ms minimum between requests
   - Allow user to increase if needed

### Protocol Clarification Needed

1. **Verify Byte Structure**
   - Bytes 11 and 21 have invalid values
   - May indicate protocol documentation errors
   - Contact manufacturer for clarification?

2. **Test in Different Radio States**
   - FM mode vs SSB vs DMR
   - Idle vs receiving vs transmitting
   - Different spectrum settings

3. **Compare with Known-Good Software**
   - Test with manufacturer's official software
   - Capture 0x2E responses from official app
   - Compare byte structures

---

## Valid Data Extracted

Despite the anomalies and crash, some data appears valid:

### Audio Settings (Bytes 0-5)
- Speaker volume: 11 (reasonable)
- Headphone volume: 23 (reasonable)
- MIC gain: 21 (reasonable)
- Compression: OFF (valid)
- Bass/Treble: 22/20 (reasonable)

### RF Settings (Bytes 6-10)
- RF Gain: 50 (matches factory default!)
- IF Gain: 50 (matches factory default!)
- Squelch: 1 (very low, typical)
- AGC: 3 (mid-range, reasonable)
- Pre-amp: AMPA (valid)

### Spectrum Settings (Bytes 14-16)
- Bandwidth: 48K (widest, valid)
- Reference level: 17 (reasonable)
- Refresh rate: 26 (fast, valid)

### CTCSS Settings (Bytes 17-18)
- TX/RX CTCSS: Both 67.0 Hz (valid, first tone)

### CW Settings (Bytes 23-28)
- Training: OFF (valid)
- Side-tone: 750 Hz (standard)
- Volume: Max (15/15)
- Speed: 20 WPM (reasonable)
- Decode: OFF (valid)

### USB Format (Byte 29)
- SDR mode (1) - Makes sense for spectrum display

---

## Conclusions

1. **Command 0x2E IS FUNCTIONAL** - Returns 30 bytes as documented
2. **Command IS POTENTIALLY UNSTABLE** - Caused radio crash
3. **Data HAS ANOMALIES** - Bytes 11 and 21 show invalid values
4. **MOST DATA IS VALID** - ~28 of 30 bytes appear reasonable

### Risk Assessment

- **High Risk:** Rapid polling of 0x2E
- **Medium Risk:** Single 0x2E query with delays
- **Low Risk:** Alternative commands (0x0B, 0x2D)

### Next Steps

1. Power cycle radio to recover
2. Test 0x2D (simpler 2-byte command)
3. Test 0x0B (comprehensive status)
4. Single-shot test of 0x2E with delays
5. Document firmware version of radio
6. Consider reporting crash to manufacturer

---

## Files Generated

- Test results JSON: `tests/fuzz_results/investigation_20260122_004234.json`
- This analysis: `docs/Command_0x2E_Test_Results.md`

**Status:** ⚠️ COMMAND FUNCTIONAL BUT UNSTABLE - USE WITH EXTREME CAUTION
