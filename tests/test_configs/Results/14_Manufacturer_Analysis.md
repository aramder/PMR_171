# Test 14: Manufacturer CPS Analysis - Critical Findings

**Date**: January 21, 2026  
**Status**: 🔴 **CRASH CAUSE IDENTIFIED**

## Executive Summary

Analysis of the manufacturer's Test 14 configuration reveals **the likely cause of our radio crashes**: incorrect `slot` field encoding.

## Critical Finding: Slot Field Encoding

### The Problem
**We use 1-based slot numbering. The radio uses 0-based slot numbering.**

| Our Code | Manufacturer | Actual Meaning |
|----------|--------------|----------------|
| `slot: 1` | `slot: 0` | Timeslot 1 |
| `slot: 2` | `slot: 1` | Timeslot 2 |

### Evidence from Manufacturer's Data

Looking at channels 7 and 8 in manufacturer's write file:
```json
"7": {
  "channelName": "CF0_TS2",
  "slot": 0,  // <- We used slot: 2 for TS2!
  ...
}
"8": {
  "channelName": "CF01_TS2",
  "slot": 0,  // <- We used slot: 2 for TS2!
  ...
}
```

**ALL manufacturer channels use `slot: 0`**, even though some should be on timeslot 2 based on their names.

### Why This Causes Crashes

Writing `slot: 1` or `slot: 2` puts the slot field out of valid range:
- Valid values: `0` (TS1) or `1` (TS2)  
- We were writing: `1` (TS2) or `2` (INVALID - causes crash)

## Other Critical Differences

### 1. Color Code Fields

**Manufacturer's Pattern:**
```json
"rxCc": 0,
"txCc": 2
```

**What We Were Using:**
```json
"rxCc": 1,
"txCc": 1
```

**Analysis**: The manufacturer uses `rxCc: 0` consistently, but varies `txCc`. Color code 1 should be:
- `rxCc: 0`
- `txCc: 2`

This non-obvious encoding suggests:
- `rxCc` might use 0-based indexing: 0=CC1, 1=CC2, etc.
- `txCc` might use a different encoding or have an offset

### 2. CTCSS/DCS Field Usage

**Manufacturer sets:**
```json
"rxCtcss": 0,   // or 255
"txCtcss": 0    // or 255
```

**Pattern:**
- When CTCSS tones are used (`emitYayin` / `receiveYayin` != 0): `rxCtcss: 0, txCtcss: 0`
- When no CTCSS/values vary: Sometimes `255`

**We were NOT setting these fields** - potentially causing issues.

### 3. DMR Channels Read Back as Analog

**Manufacturer Write** (channels 0-9):
```json
"chType": 1  // DMR
```

**Readback** (channels 0-9):
```json
"chType": 0  // Shows as ANALOG!
```

This is extremely concerning - the manufacturer's DMR channels are reading back as analog. This might be:
- A separate bug in the read operation
- Or the readback is from a crashed state

### 4. Channel 6 (Analog Reference)

**Manufacturer Write:**
```json
"6": {
  "chType": 255,  // <- Special value for analog!
  ...
}
```

**Our Test:**
```json
"6": {
  "chType": 0,  // We used 0
  ...
}
```

**Possible Issue**: Using `chType: 255` for analog might be required instead of `chType: 0`.

### 5. Uninitialized DMR Fields

When `chType: 0` (analog), manufacturer sets:
```json
"ownId1": 0,
"ownId2": 0,
"ownId3": 0,
"ownId4": 0,
"callId1": 0,
"callId2": 0,
"callId3": 0,
"callId4": 0
```

We might not be zeroing these for analog channels.

## Field-by-Field Comparison

### Channel 0 (DMR, Private Call, TS1)

| Field | Our Value | Manufacturer | Status |
|-------|-----------|--------------|--------|
| chType | 1 | 1 | ✓ Match |
| slot | 1 | 0 | ✗ **WRONG** |
| callFormat | 0 | 0 | ✓ Match |
| rxCc | 1 | 0 | ✗ Different |
| txCc | 1 | 2 | ✗ Different |
| emitYayin | 1 | 1 | ✓ Match |
| receiveYayin | 1 | 1 | ✓ Match |
| rxCtcss | (not set) | 0 | ✗ Missing |
| txCtcss | (not set) | 0 | ✗ Missing |

### Channel 6 (Analog)

| Field | Our Value | Manufacturer | Status |
|-------|-----------|--------------|--------|
| chType | 0 | 255 | ✗ **WRONG** |
| vfoaMode | 0 | 6 | ✗ Different |
| vfobMode | 0 | 6 | ✗ Different |

## Required Code Fixes

### Fix 1: Slot Field (CRITICAL)
```python
# WRONG (current):
"slot": 1  # for TS1
"slot": 2  # for TS2

# CORRECT:
"slot": 0  # for TS1
"slot": 1  # for TS2
```

### Fix 2: Color Code Fields
```python
# For Color Code 1:
"rxCc": 0,  # Not 1!
"txCc": 2   # Not 1!

# Need to determine the encoding pattern:
# CC1: rxCc=0, txCc=2
# CC2: rxCc=?, txCc=?
# etc.
```

### Fix 3: Add Missing CTCSS Fields
```python
# Always include these fields:
"rxCtcss": 0,   # Default when using yayin
"txCtcss": 0    # Default when using yayin
```

### Fix 4: Analog Channel Type
```python
# For analog channels:
"chType": 255  # Not 0!
# OR investigate if 0 is actually correct
```

## Test Plan

### Step 1: Fix Slot Field
1. Update writer to use 0-based slot numbering
2. Test with minimal DMR config (2-3 channels)
3. Verify no crash

### Step 2: Fix Color Code
1. Research rxCc/txCc encoding
2. Update color code conversion
3. Test with varying color codes

### Step 3: Add Missing Fields
1. Ensure rxCtcss/txCtcss always present
2. Verify analog channel handling

### Step 4: Full Test
1. Re-run Test 13A with all fixes
2. Verify radio stability
3. Confirm channels work correctly

## Files to Update

1. **`pmr_171_cps/writers/pmr171_writer.py`**
   - Fix slot field: subtract 1 from input value
   - Fix color code encoding
   - Add rxCtcss/txCtcss fields
   - Fix analog channel type

2. **`pmr_171_cps/radio/pmr171_uart.py`** (if needed)
   - Verify read operation slot handling
   - Check color code read conversion

## Next Steps

1. **IMMEDIATE**: Fix slot field encoding (this is causing the crash)
2. **HIGH PRIORITY**: Fix color code fields
3. **MEDIUM**: Add rxCtcss/txCtcss fields
4. **LOW**: Investigate analog chType and readback issues

## Questions Remaining

1. **Color Code Encoding**: What's the pattern for rxCc/txCc?
   - Need to test multiple color codes with manufacturer software
   - Or analyze more UART captures

2. **Analog chType**: Should it be 0 or 255?
   - Manufacturer uses 255 in one place
   - But readback shows 0

3. **DMR Readback Issue**: Why do DMR channels read back as analog?
   - Is this expected?
   - Or does it indicate the write failed?

4. **Frequency Mismatch**: Channel 0 shows 26.149.107.128 (444.000 MHz?) instead of 446.000 MHz
   - Need to verify frequency encoding

## Confidence Level

**Slot Field Fix**: 🔴 **99% confident** this is the crash cause
**Color Code Fix**: 🟡 **75% confident** this is needed
**Other Fixes**: 🟢 **50% confident** these are optional but recommended

---

## CRITICAL UPDATE: Manufacturer CPS Issue Discovered

**Date**: January 21, 2026

### Findings

After attempting to use the manufacturer's CPS to program DMR channels, it was discovered that:

1. **Manufacturer's CPS also fails to write DMR properly**
   - Write operation appears to complete
   - Radio does not retain the DMR configuration correctly
   - Channels do not function as DMR after programming

2. **Readback shows corruption**
   - DMR channels (written as `chType: 1`) read back as analog (`chType: 0`)
   - Only channel 0 shows any data retained
   - Channels 1-5, 7-9 are essentially blank in readback
   - All DMR-specific fields are zeroed out

3. **Both CPS implementations fail**
   - Our CPS: Radio crashes
   - Manufacturer's CPS: Write appears to succeed but data is not retained

### Implications

**DMR programming functionality is BLOCKED** until one of the following occurs:

1. **Manufacturer firmware issue is resolved**
   - The radio firmware may have a bug preventing DMR programming
   - Firmware update may be needed

2. **Manufacturer CPS issue is resolved**
   - The GH Terminal CPS may have a bug
   - Updated CPS version may be needed

3. **Alternative programming method discovered**
   - Manual programming via radio menus may be the only working method
   - UART protocol may need deeper reverse engineering

### Current Status

**DMR Programming**: 🔴 **BLOCKED - ON HOLD**

The investigation cannot proceed further without:
- Working DMR programming via manufacturer's CPS
- Or firmware/CPS update from manufacturer
- Or significantly deeper UART protocol analysis

### What Works

✅ **Reading DMR channels**: Can successfully read DMR channels that were manually programmed on the radio  
✅ **Analog programming**: Writing analog channels works correctly  
✅ **CTCSS programming**: CTCSS tones work correctly  
✅ **Color Code reading**: Can read DMR color codes from manually programmed channels  

### What Doesn't Work

❌ **Writing DMR channels**: Both our CPS and manufacturer's CPS fail  
❌ **DMR/DFM display control**: Cannot test until writing works  
❌ **Complete DMR workflow**: Blocked on writing functionality  

### Recommendation

**Pause DMR write development** until the underlying issue is resolved. Focus on:
1. Analog channel programming (working)
2. Reading DMR channels (working)
3. CTCSS/DCS functionality (working)
4. Other radio features

When manufacturer provides working DMR programming:
1. Capture working UART transactions
2. Compare with our implementation
3. Implement fixes
4. Resume DMR write development
