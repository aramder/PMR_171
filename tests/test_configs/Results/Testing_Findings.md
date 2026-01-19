# PMR-171 Testing Findings - Radio Format Truth

**Date**: January 18, 2026  
**Source**: Actual radio readback testing comparing uploaded JSON vs. what the radio accepted/stored

## Executive Summary

The PMR-171 radio is the **ultimate source of truth** for data format validity. Testing revealed critical discrepancies between what we send and what the radio actually stores, particularly for CTCSS/DCS tones and certain field values.

---

## Critical Finding #1: CTCSS/DCS Tone Storage

### ❌ **WRONG**: `rxCtcss`/`txCtcss` fields (indexes 0-186)
### ✅ **CORRECT**: `emitYayin`/`receiveYayin` fields (different encoding)

**Evidence**: When CTCSS tones were manually set in the manufacturer's software and read back:
- All `rxCtcss`/`txCtcss` values were **cleared to 0**
- Tone information was **stored in `emitYayin`/`receiveYayin` instead**

### Tone Encoding in emitYayin/receiveYayin

| CTCSS Frequency | Original Index (rxCtcss) | emitYayin/receiveYayin Value | Relationship |
|-----------------|--------------------------|------------------------------|--------------|
| None (off) | 255 | 0 | N/A |
| 67.0 Hz | 0 | 1 | index + 1 |
| 88.5 Hz | 5 | 9 | differs |
| 100.0 Hz | 10 | 13 | index + 3 |
| 123.0 Hz | 17 | 19 | index + 2 |
| 146.2 Hz | 23 | 24 | index + 1 |
| 156.7 Hz | 28 | 27 | index - 1 |

**Pattern**: The relationship between CTCSS table index and emitYayin/receiveYayin value is **NOT simple offset** - it varies per tone and requires reverse engineering the actual mapping.

### Split Tone Support

Split tones (RX tone ≠ TX tone) work correctly:
- **Channel 5**: RX=100.0 Hz (receiveYayin=53), TX=146.2 Hz (emitYayin=4)
- **RX-only**: receiveYayin=5, emitYayin=0
- **TX-only**: emitYayin=5, receiveYayin=0

### DCS Code Storage

DCS codes (023, 754, 114) were **also cleared** - the radio doesn't accept DCS codes through our current format. These likely also use emitYayin/receiveYayin with a different encoding scheme that needs investigation via UART monitoring of manual DCS configuration.

---

## Critical Finding #2: txCc Value Transformation

### Scenario A: Upload with txCc=1, No Manual Changes
**File**: `01_readback.json`

**Result**: Radio **changed txCc from 1 → 2** for all channels

### Scenario B: Manual Configuration in Manufacturer Software  
**File**: `05_manual_CTCSS_only_readback_uart_monitored.json`

**Result**: Radio **kept txCc=1** for all channels

### Conclusion

- The radio's **native/preferred value is txCc=2** for channels without manual intervention
- The manufacturer software **preserves txCc=1** when manually configuring channels
- This suggests **txCc=1 is correct for our use** since we're mimicking manual configuration

---

## Critical Finding #3: callFormat and chType Values

### What We Send (Based on Real Radio Dump)
- Analog: `callFormat=255, chType=255`
- Digital: `callFormat=2, chType=1`

### What Radio Actually Stores

**From 01_readback.json** (simple analog, no manual changes):
- Programmed channels (0-2): `callFormat=255, chType=255` → **ACCEPTED unchanged**
- Empty channels (3-29, etc.): `callFormat=255, chType=255` → **ACCEPTED unchanged**
- Channels 256+: `callFormat=0, chType=0` (uninitialized/factory default)

**From 05_manual_CTCSS_only_readback_uart_monitored.json** (manually configured):
- All programmed channels (0-12): `callFormat=255→0, chType=255→0`
- All empty channels: `callFormat=0, chType=0`

### Conclusion

Two different storage patterns:
1. **Direct radio programming (01)**: Preserves `callFormat=255, chType=255`
2. **Manufacturer software programming (05)**: Converts to `callFormat=0, chType=0`

For maximum compatibility, we should use `callFormat=255, chType=255` as this matches what an actual radio dump shows, but be aware the manufacturer software may normalize it to 0.

---

## Read/Write Cycle Data Flow

### Upload Cycle
```
User JSON → Manufacturer Software → Radio Memory
```

### What Happens During Upload

1. **Accepted Fields** (preserved as-is):
   - Frequencies (vfoaFrequency, vfobFrequency)
   - Modes (vfoaMode, vfobMode)
   - Channel names
   - Channel numbers (channelHigh/channelLow)
   - callFormat (kept at 255 or normalized to 0)
   - chType (kept at 255 or normalized to 0)

2. **Transformed Fields** (radio modifies):
   - `txCc`: 1 → 2 (unless manually configured, then stays 1)
   - `rxCtcss`/`txCtcss`: Cleared to 0 (tones go to emitYayin/receiveYayin)
   - `callFormat`/`chType`: May normalize 255 → 0

3. **Ignored Fields** (radio doesn't use):
   - `rxCtcss`/`txCtcss` for CTCSS/DCS tones (uses emitYayin/receiveYayin instead)

### Readback Cycle
```
Radio Memory → Manufacturer Software → JSON Export
```

What we read back represents the **radio's internal storage format** - the absolute truth.

---

## Field Usage Summary

| Field | Purpose | We Send | Radio Stores | Notes |
|-------|---------|---------|--------------|-------|
| `callFormat` | Channel type | 255 (analog) | 255 or 0 | Either accepted |
| `chType` | Channel type | 255 (analog) | 255 or 0 | Either accepted |
| `txCc` | Color code/TX setting | 1 | 1 or 2 | Changes to 2 unless manually set |
| `rxCtcss` | **UNUSED** | Any | **0** | Cleared! Don't use |
| `txCtcss` | **UNUSED** | Any | **0** | Cleared! Don't use |
| `emitYayin` | **TX tone** | 0 | Tone value | **USE THIS for TX tone** |
| `receiveYayin` | **RX tone** | 0 | Tone value | **USE THIS for RX tone** |
| `vfoaFrequency` | RX frequency | Bytes | Unchanged | ✅ Works |
| `vfobFrequency` | TX frequency | Bytes | Unchanged | ✅ Works |
| `vfoaMode`/`vfobMode` | Mode | 0-9 | Unchanged | ✅ Works |
| `channelName` | Name | String | Unchanged | ✅ Works (15 char max) |

---

## Implications for CodeplugConverter

### HIGH PRIORITY FIXES NEEDED

1. **CTCSS/DCS Tone Handling**
   - **STOP using** `rxCtcss`/`txCtcss` fields
   - **START using** `emitYayin`/`receiveYayin` fields
   - Need to reverse engineer the tone encoding mapping
   - Requires capturing UART traffic when manually setting various CTCSS/DCS codes

2. **txCc Value**
   - Current default of `txCc=1` appears correct
   - Be aware radio may change it to 2 during certain operations
   - Not critical to fix, but document the behavior

3. **callFormat/chType Values**
   - Current use of 255 for analog is correct (matches real radio dump)
   - Manufacturer software may normalize to 0, but that's acceptable
   - No changes needed

### Investigation Needed

**DCS Tone Mapping**:
1. Manually configure DCS codes on radio (023, 114, 754, etc.)
2. Download configuration while monitoring UART
3. Analyze emitYayin/receiveYayin values
4. Build DCS code → emitYayin/receiveYayin mapping table

**CTCSS Tone Mapping**:
1. Build complete mapping table from additional test uploads
2. Test edge cases (split tones, RX-only, TX-only)
3. Verify mapping is consistent across all CTCSS frequencies

---

## Test File Status

| File | Upload Success | Readback Match | CTCSS/DCS Work | Notes |
|------|----------------|----------------|----------------|-------|
| 01_simple_analog.json | ✅ Yes | ⚠️ txCc changed | N/A | No tones tested |
| 05_ctcss_dcs.json | ⚠️ Partial | ❌ No | ❌ No | Tones cleared, need emitYayin |
| 02_multi_mode.json | ? | ? | ? | Not yet analyzed |
| 03_digital_dmr.json | ? | ? | ? | Not yet analyzed |
| 04_mixed_analog_digital.json | ? | ? | ? | Not yet analyzed |
| 06_edge_cases.json | ? | ? | ? | Not yet analyzed |

---

## Recommended Testing Protocol

### For Future CTCSS/DCS Testing:

1. **Manual Configuration Method**:
   - Open manufacturer software
   - Manually set each CTCSS tone one at a time
   - Download from radio with UART monitoring
   - Record emitYayin/receiveYayin values
   - Build mapping table

2. **DCS Configuration** (Currently Unknown):
   - Configure DCS on the radio directly (manufacturer software can't set DCS)
   - Download from radio with UART monitoring
   - Analyze emitYayin/receiveYayin encoding for DCS
   - Document the pattern

3. **Validation**:
   - Update PMR171Writer to use emitYayin/receiveYayin
   - Re-test all tone configurations
   - Verify tones work correctly on-air

---

## Data Format Truth Table

| Scenario | callFormat | chType | txCc | rxCtcss/txCtcss | emitYayin/receiveYayin |
|----------|------------|--------|------|-----------------|------------------------|
| Real radio dump | 255 | 255 | 2 | 255 (no tone) | 0 (no tone) |
| Our generated file | 255 | 255 | 1 | 0-186 | 0 |
| After simple upload | 255 | 255 | 2 | 0 | 0 |
| After manual config | 0 | 0 | 1 | 0 | 1-255 (tone) |

---

## Conclusion

**The Radio IS the Authority**. What comes back from a readback is the definitive format. Key takeaways:

1. ✅ **Frequencies work correctly** - no issues
2. ✅ **Channel names work** - no issues  
3. ✅ **Modes work** - no issues
4. ⚠️ **txCc behavior** - changes from 1→2, but not critical
5. ❌ **CTCSS/DCS BROKEN** - completely wrong fields used!

**Next Steps**:
1. Map CTCSS tones to emitYayin/receiveYayin values
2. Discover DCS encoding (requires radio-side DCS configuration)
3. Update PMR171Writer to use correct tone fields
4. Re-test with corrected implementation

The good news: We now know exactly what's wrong and how to fix it!
