# CTCSS Tone Analysis

## Overview
Analysis of CTCSS (Continuous Tone-Coded Squelch System) tones in the PMR171 codeplug format based on the SAMPLE_CHANNELS.json readback.

## Data Source
File: `examples/SAMPLE_CHANNELS.json`

## CTCSS Fields
Each channel has two CTCSS-related fields:
- `rxCtcss`: Receive CTCSS tone
- `txCtcss`: Transmit CTCSS tone

## Format Analysis

### Storage Format
CTCSS tones are stored as **integer values representing the tone frequency in tenths of Hz**.

### Examples from SAMPLE_CHANNELS.json

| Channel | Channel Name | rxCtcss | txCtcss | Actual Frequency |
|---------|--------------|---------|---------|------------------|
| 0-9 | Simplex channels | 0 | 0 | None (disabled) |
| 10 | RPT 147.240+ | 1000 | 1000 | 100.0 Hz |
| 11 | RPT 146.640- | 1318 | 1318 | 131.8 Hz |
| 12 | RPT 147.000+ | 1567 | 1567 | 156.7 Hz |
| 20 | RPT 449.100- | 1072 | 1072 | 107.2 Hz |
| 21 | RPT 444.100+ | 1000 | 1000 | 100.0 Hz |
| 40-46 | NOAA Weather | 0 | 0 | None (disabled) |
| 50-61 | DMR Channels | 0 | 0 | N/A (digital) |

### Conversion Formula
```
CTCSS Frequency (Hz) = rxCtcss / 10.0
```

**Examples:**
- `1000` → 100.0 Hz
- `1318` → 131.8 Hz  
- `1567` → 156.7 Hz
- `1072` → 107.2 Hz
- `0` → No CTCSS (disabled)

## Standard CTCSS Tones

The standard CTCSS tones are defined by the EIA as follows (50 tones):

| Hz | Code | Hz | Code | Hz | Code | Hz | Code |
|----|------|----|------|----|------|----|------|
| 67.0 | XZ | 94.8 | ZA | 127.3 | 4B | 171.3 | 6A |
| 69.3 | WZ | 97.4 | ZB | 131.8 | 5Z | 173.8 | 6B |
| 71.9 | XA | 100.0 | 1Z | 136.5 | 5A | 177.3 | 7Z |
| 74.4 | XB | 103.5 | 1A | 141.3 | 5B | 179.9 | 7A |
| 77.0 | YZ | 107.2 | 1B | 146.2 | 6Z | 183.5 | M1 |
| 79.7 | YA | 110.9 | 2Z | 151.4 | 7A | 186.2 | 8Z |
| 82.5 | YB | 114.8 | 2A | 156.7 | 7B | 189.9 | 9Z |
| 85.4 | ZZ | 118.8 | 2B | 159.8 | -- | 192.8 | 9A |
| 88.5 | ZA | 123.0 | 3Z | 162.2 | 8Z | 196.6 | 0Z |
| 91.5 | ZB | 125.0 | -- | 165.5 | 8A | 199.5 | 0A |
|  |  |  |  | 167.9 | 9Z | 203.5 | 0B |
|  |  |  |  | 169.4 | -- | 206.5 | -- |
|  |  |  |  |  |  | 210.7 | -- |
|  |  |  |  |  |  | 218.1 | -- |
|  |  |  |  |  |  | 225.7 | -- |
|  |  |  |  |  |  | 229.1 | -- |
|  |  |  |  |  |  | 233.6 | -- |
|  |  |  |  |  |  | 241.8 | -- |
|  |  |  |  |  |  | 250.3 | -- |
|  |  |  |  |  |  | 254.1 | -- |

## Observed Values in Sample Data

From SAMPLE_CHANNELS.json, the following CTCSS tones are used:
1. **100.0 Hz** (1000) - Standard tone "1Z", used on channels 10 and 21
2. **107.2 Hz** (1072) - Standard tone "1B", used on channel 20
3. **131.8 Hz** (1318) - Standard tone "5Z", used on channel 11
4. **156.7 Hz** (1567) - Standard tone "7B", used on channel 12

All observed tones match standard CTCSS frequencies.

## Usage Patterns

1. **Simplex Channels**: No CTCSS (rxCtcss=0, txCtcss=0)
2. **Repeater Channels**: Same CTCSS on both RX and TX (most common)
3. **Weather Channels**: No CTCSS
4. **DMR Channels**: No CTCSS (uses Color Code instead via rxCc/txCc fields)

## Implementation Notes

### Reading CTCSS from PMR171
```python
def decode_ctcss(ctcss_value):
    """Convert PMR171 CTCSS value to frequency in Hz"""
    if ctcss_value == 0:
        return None  # No CTCSS
    return ctcss_value / 10.0
```

### Writing CTCSS to PMR171
```python
def encode_ctcss(frequency_hz):
    """Convert CTCSS frequency in Hz to PMR171 format"""
    if frequency_hz is None or frequency_hz == 0:
        return 0  # No CTCSS
    return int(frequency_hz * 10)
```

### Validation
When converting from other formats (like CHIRP), validate that:
1. The CTCSS tone is one of the standard 50 tones
2. The value is within range: 67.0 Hz to 254.1 Hz
3. Round to nearest 0.1 Hz when converting

## CHIRP Compatibility

CHIRP typically stores CTCSS tones as floating-point values (e.g., "100.0" or "131.8").
When converting:
- From CHIRP: Parse string/float → multiply by 10 → store as integer
- To CHIRP: Read integer → divide by 10 → format as string with 1 decimal place

## Related Fields

Note that digital channels use different squelch mechanisms:
- **DMR channels**: Use `rxCc` and `txCc` (Color Code) instead of CTCSS
- **Analog channels**: Use `rxCtcss` and `txCtcss`

The `chType` field determines which squelch system is active:
- `chType=0`: Analog (uses CTCSS)
- `chType=1`: Digital/DMR (uses Color Code)

## ✅ COMPLETE CTCSS ENCODING CONFIRMED AND VALIDATED

After extensive testing (Tests 05-11), we have **fully mapped and validated** the CTCSS encoding system:

### Confirmed Encoding: emitYayin/receiveYayin Fields

The PMR171 radio uses **emitYayin and receiveYayin** fields with a non-linear lookup table:

- **Field**: `emitYayin` = TX CTCSS tone, `receiveYayin` = RX CTCSS tone
- **Encoding**: Non-linear yayin values (1-55 for CTCSS)
- **No tone**: `0`
- **Status**: ✅ **VALIDATED** - All 50 standard CTCSS tones mapped and verified (Test 11)

### IMPORTANT: Unused Fields

The following fields are **IGNORED** by the radio (confirmed via Test 07):
- `txCtcss`: Always set to 255 (ignored)
- `rxCtcss`: Always set to 255 (ignored)

**The radio ONLY uses emitYayin and receiveYayin for CTCSS tones.**

**Validation**: Test 11 confirmed all 25 test channels (including edge cases, split tones, TX-only, RX-only) work correctly with 100% accuracy.

### Complete CTCSS Mapping (50/50 Tones)

| Frequency (Hz) | yayin | Frequency (Hz) | yayin |
|----------------|-------|----------------|-------|
| 67.0 | 1 | 165.5 | 30 |
| 69.3 | 2 | 167.9 | 31 |
| 71.9 | 3 | 171.3 | 32 |
| 74.4 | 4 | 173.8 | 33 |
| 77.0 | 5 | 177.3 | 34 |
| 79.7 | 6 | 179.9 | 35 |
| 82.5 | 7 | 183.5 | 36 |
| 85.4 | 8 | 186.2 | 37 |
| 88.5 | 9 | 189.9 | 38 |
| 91.5 | 10 | 192.8 | 39 |
| 94.8 | 11 | 196.6 | 40 |
| 97.4 | 12 | 199.5 | 41 |
| 100.0 | 13 | 203.5 | 42 |
| 103.5 | 14 | 206.5 | 43 |
| 107.2 | 15 | 210.7 | 44 |
| 110.9 | 16 | 218.1 | 46 |
| 114.8 | 17 | 225.7 | 48 |
| 118.8 | 18 | 229.1 | 49 |
| 123.0 | 19 | 233.6 | 50 |
| 127.3 | 20 | 241.8 | 52 |
| 131.8 | 21 | 250.3 | 54 |
| 136.5 | 22 | 254.1 | 55 |
| 141.3 | 23 | | |
| 146.2 | 24 | | |
| 151.4 | 26 | | |
| 156.7 | 27 | | |
| 159.8 | 28 | | |
| 162.2 | 29 | | |

### Reserved yayin Values (Gaps)

These yayin values are **not assigned** to CTCSS tones:
- **25**: Gap between 146.2 Hz (24) and 151.4 Hz (26)
- **45**: Gap between 210.7 Hz (44) and 218.1 Hz (46)
- **47**: Gap between 225.7 Hz (48) and 229.1 Hz (49)
- **51**: Gap between 233.6 Hz (50) and 241.8 Hz (52)
- **53**: Gap between 241.8 Hz (52) and 250.3 Hz (54)

These are likely:
- Reserved for non-standard CTCSS tones (125.0, 169.4, etc.)
- Placeholder entries in firmware
- Used for DCS codes (which start at yayin 100+)

### Test History

1. **Test 05**: Initial 6 mappings discovered
2. **Test 07**: Confirmed emitYayin/receiveYayin encoding (not txCtcss/rxCtcss)
3. **Test 09**: 14 mappings, discovered non-linear pattern
4. **Test 10**: 34 new mappings → **100% complete (50/50 tones)**

## Key Findings (Historical)

**INITIAL ANALYSIS (OUTDATED):**
1. ⚠️ TWO DIFFERENT CTCSS encoding formats were initially considered
2. Format 1 (Raw): Values are integers (frequency × 10), 0 = no tone
3. Format 2 (Index): Values are indexes (0-50), 255 = no tone

**CONFIRMED (Tests 07-11):**
1. ✅ Radio uses **emitYayin/receiveYayin** (NOT txCtcss/rxCtcss)
2. ✅ Encoding is **non-linear lookup table** (yayin values 1-55)
3. ✅ Separate RX and TX values allow split tones
4. ✅ All 50 standard CTCSS tones mapped and validated
5. ✅ DMR channels don't use CTCSS (they use Color Code via rxCc/txCc)
6. ✅ Complete mapping table in `docs/COMPLETE_CTCSS_MAPPING.md`

## Implementation Status

✅ **COMPLETE AND VALIDATED** (January 18, 2026)

1. ✅ Complete CTCSS mapping table (50/50 tones)
2. ✅ Implemented in `codeplug_converter/writers/pmr171_writer.py`
3. ✅ Validated via Test 11 (25 test channels, 100% accuracy)
4. ✅ Split tones, TX-only, RX-only all confirmed working
5. ✅ Documentation complete in `docs/COMPLETE_CTCSS_MAPPING.md`

## Next Steps

1. **Future**: Map DCS codes (likely yayin 100+)
2. **Future**: Test non-standard CTCSS tones (125.0, 169.4)
3. **Future**: Implement CHIRP to PMR171 conversion using validated mapping
