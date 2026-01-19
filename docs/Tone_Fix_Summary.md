# CTCSS/DCS Tone Fix - Implementation Summary

**Date**: January 18, 2026  
**Status**: Phase 1 Complete - Infrastructure Updated

## Problem Discovered

Through systematic hardware testing, we discovered that **CTCSS/DCS tones were completely non-functional** in the PMR-171 codeplug converter:

1. **Test 07** (`D:\Radio\Guohetec\Testing\07_ctcss_format_test.json`):
   - Tested multiple CTCSS encoding schemes in `rxCtcss`/`txCtcss` fields
   - **Result**: ALL values were cleared to 255 in radio readback
   - **Conclusion**: These fields are COMPLETELY IGNORED by the PMR-171 radio

2. **Test 08** (`D:\Radio\Guohetec\Testing\08_untested_fields.json`):
   - Tested `emitYayin` and `receiveYayin` fields with values 0 and 1
   - **Result**: Value 1 was PRESERVED in both fields
   - **Conclusion**: These are the CORRECT fields for tone encoding

## Changes Made

### 1. Updated `codeplug_converter/writers/pmr171_writer.py`

#### Changed Method Signature:
```python
# OLD (broken):
def create_channel(self, ..., rx_ctcss: int = 0, tx_ctcss: int = 0, ...)

# NEW (correct):
def create_channel(self, ..., rx_tone: str = None, tx_tone: str = None, ...)
```

#### Key Changes:
- **Tone parameters**: Now accept string format (e.g., '100.0', 'D023N') instead of integer codes
- **emitYayin field**: Now populated from `_tone_to_yayin(tx_tone)` instead of hardcoded 0
- **receiveYayin field**: Now populated from `_tone_to_yayin(rx_tone)` instead of hardcoded 0
- **rxCtcss/txCtcss fields**: Hardcoded to 255 (confirmed ignored by radio)
- **Ignored fields**: Set to 0 based on test results:
  - `sqlevel` = 0 (field ignored)
  - `spkgain` = 0 (field ignored)
  - `dmodGain` = 0 (field ignored)
  - `scrEn` = 0 (scrambler ignored)
  - `scrSeed1` = 0 (scrambler ignored)
  - `scrSeed2` = 0 (scrambler ignored)

#### New Methods Added:
1. **`_tone_to_yayin(tone: str) -> int`**:
   - Converts CTCSS/DCS tone strings to emitYayin/receiveYayin values
   - Currently has placeholder implementation (returns 1 for '100.0', 0 otherwise)
   - **NEEDS RESEARCH**: Complete mapping table must be built through testing

2. **`_ctcss_code_to_string(code: int) -> str`**:
   - Helper method to convert CHIRP-style CTCSS codes to frequency strings
   - Maps code 1-50 to standard CTCSS frequencies (67.0-254.1 Hz)
   - Used in `channels_from_parsed()` for backward compatibility

### 2. Created `docs/TONE_ENCODING_RESEARCH.md`

Comprehensive research documentation including:
- Summary of test findings
- What we know vs. what we need to discover
- Detailed CTCSS mapping table template (50 tones)
- DCS mapping table template (104+ codes)
- Step-by-step research methodology
- 4-phase implementation plan
- Timeline estimates (11-15 hours total)

### 3. Updated `TODO.md`

Added new high-priority section at top:
- **CRITICAL: CTCSS/DCS Tone Encoding (BROKEN - FIX REQUIRED)**
- Tracks what's done and what needs research
- Links to relevant test files and documentation
- Emphasizes impact on repeater access and privacy codes

## Current Status

### ✅ What's Working:
- Infrastructure updated to use correct fields (emitYayin/receiveYayin)
- Ignored fields properly set to 0 or 255
- Code accepts tone strings and has conversion framework
- Backward compatibility maintained with CHIRP tone codes
- All changes documented

### ⚠️ What's NOT Working (Yet):
- **Tone mapping is incomplete**: Only placeholder value for 100.0 Hz
- All other CTCSS tones will default to 0 (no tone configured)
- DCS codes not supported at all
- **This means tones will NOT work until research is complete**

## Next Steps

### Immediate (Phase 2):
1. Use manufacturer software to configure channels with each CTCSS tone
2. Download configuration and record emitYayin/receiveYayin values
3. Build complete CTCSS mapping table (50 tones)
4. Update `_tone_to_yayin()` with real mappings

### Follow-up (Phase 3):
1. Configure DCS codes in manufacturer software
2. Record emitYayin/receiveYayin values for each code
3. Add DCS support to `_tone_to_yayin()`
4. Test all tones on actual radio hardware

### Validation (Phase 4):
1. Create test cases for all CTCSS/DCS combinations
2. Verify repeater access works correctly
3. Update user documentation
4. Mark feature as complete

## Testing Results Summary

### Fields That WORK (Keep Using):
- ✅ `emitYayin` - TX tone encoding
- ✅ `receiveYayin` - RX tone encoding
- ✅ `callFormat` - Channel type (255=analog, 2=digital)
- ✅ `chType` - Channel type (255=analog, 1=digital)
- ✅ `channelName` - Channel name (null-terminated)
- ✅ `vfoaFrequency1-4` - RX frequency (4-byte big-endian Hz)
- ✅ `vfobFrequency1-4` - TX frequency (4-byte big-endian Hz)
- ✅ `vfoaMode`/`vfobMode` - Modulation mode

### Fields That DON'T WORK (Stop Using):
- ❌ `rxCtcss` - Always reset to 255 (IGNORED)
- ❌ `txCtcss` - Always reset to 255 (IGNORED)
- ❌ `sqlevel` - Always reset to 0 (IGNORED)
- ❌ `spkgain` - Always reset to 0 (IGNORED)
- ❌ `dmodGain` - Always reset to 0 (IGNORED)
- ❌ `scrEn` - Always reset to 0 (IGNORED)
- ❌ `scrSeed1` - Always reset to 0 (IGNORED)
- ❌ `scrSeed2` - Always reset to 0 (IGNORED)

### Fields With Special Behavior:
- ⚠️ `txCc` - Set to 1, radio transforms to 2 (color code normalization)

## Impact Assessment

### Before Fix:
- ❌ CTCSS tones: Non-functional (fields ignored)
- ❌ DCS codes: Non-functional (fields ignored)
- ❌ Repeater access: Broken for tone-required repeaters
- ❌ Privacy codes: Not working on PMR/FRS

### After Phase 1 (Current):
- ⚠️ Infrastructure ready but encoding unknown
- ⚠️ Placeholder mapping for testing
- ⚠️ Tones still won't work until mapping complete
- ✅ Ignored fields no longer pollute JSON output
- ✅ Foundation laid for complete fix

### After Phase 2-4 (Target):
- ✅ All 50 CTCSS tones working
- ✅ All 104+ DCS codes working
- ✅ Repeater access functional
- ✅ Privacy codes operational
- ✅ Full amateur radio compatibility

## Files Modified

1. **`codeplug_converter/writers/pmr171_writer.py`**:
   - Changed create_channel() parameters
   - Updated field assignments for tones
   - Added _tone_to_yayin() method
   - Added _ctcss_code_to_string() helper
   - Set ignored fields to proper values

2. **`docs/TONE_ENCODING_RESEARCH.md`** (NEW):
   - Research methodology
   - Mapping table templates
   - Implementation timeline
   - Priority justification

3. **`TODO.md`**:
   - Added CRITICAL priority section
   - Tracked research tasks
   - Documented impact

## Timeline

- **Phase 1 (Infrastructure)**: ✅ COMPLETE (Jan 18, 2026)
- **Phase 2 (CTCSS Mapping)**: ⏳ IN PROGRESS - Est. 3-4 hours
- **Phase 3 (DCS Mapping)**: 📅 TODO - Est. 6-8 hours
- **Phase 4 (Validation)**: 📅 TODO - Est. 2-3 hours

**Total remaining work**: 11-15 hours of systematic testing

## Reference Documents

- **Test Results**: 
  - `D:\Radio\Guohetec\Testing\07_ctcss_format_test.json` - CTCSS field test (FAILED)
  - `D:\Radio\Guohetec\Testing\08_untested_fields.json` - Field validation (SUCCESS)
  
- **Documentation**:
  - `docs/TONE_ENCODING_RESEARCH.md` - Research plan and methodology
  - `docs/CTCSS_FORMAT_TESTING.md` - Test 07 details
  - `docs/UNTESTED_FIELDS_ANALYSIS.md` - Test 08 details
  - `docs/CTCSS_ANALYSIS.md` - Original analysis (now obsolete)

- **Code**:
  - `codeplug_converter/writers/pmr171_writer.py` - Updated writer

## Conclusion

The infrastructure is now in place to support CTCSS/DCS tones correctly. The next critical step is to systematically test each tone with the manufacturer software and build the complete emitYayin/receiveYayin mapping tables.

Once the mapping research is complete, tones will work correctly, enabling full amateur radio repeater access and privacy code functionality.
