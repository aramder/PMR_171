# CTCSS/DCS Tone Encoding Research

## Status: IN PROGRESS

Based on testing results from Test 07 and Test 08, we have discovered that:
- **rxCtcss/txCtcss fields are COMPLETELY IGNORED by the PMR-171 radio**
- **emitYayin/receiveYayin fields ARE ACCEPTED and work correctly**

## What We Know

### Test 07 - CTCSS Format Test (FAILED)
- Tested various CTCSS encoding methods in rxCtcss/txCtcss
- ALL values were cleared to 255 in readback
- Proves these fields are not used by the radio

### Test 08 - Untested Fields (SUCCESS)
- emitYayin: Tested 0, 1 → Value 1 was PRESERVED ✅
- receiveYayin: Tested 0, 1 → Value 1 was PRESERVED ✅
- This confirms these are the CORRECT fields for tone encoding

## What We Need to Discover

### CTCSS Tone Mapping (50 tones)
We need to systematically test each CTCSS tone to build the complete mapping table:

| CTCSS Freq | Index | emitYayin Value | receiveYayin Value | Status |
|------------|-------|-----------------|--------------------| -------|
| 67.0 Hz    | 1     | ?               | ?                  | ❌ TODO |
| 71.9 Hz    | 2     | ?               | ?                  | ❌ TODO |
| 74.4 Hz    | 3     | ?               | ?                  | ❌ TODO |
| 77.0 Hz    | 4     | ?               | ?                  | ❌ TODO |
| 79.7 Hz    | 5     | ?               | ?                  | ❌ TODO |
| 82.5 Hz    | 6     | ?               | ?                  | ❌ TODO |
| 85.4 Hz    | 7     | ?               | ?                  | ❌ TODO |
| 88.5 Hz    | 8     | ?               | ?                  | ❌ TODO |
| 91.5 Hz    | 9     | ?               | ?                  | ❌ TODO |
| 94.8 Hz    | 10    | ?               | ?                  | ❌ TODO |
| 97.4 Hz    | 11    | ?               | ?                  | ❌ TODO |
| 100.0 Hz   | 12    | 1 (test)        | 1 (test)           | ⚠️ PLACEHOLDER |
| 103.5 Hz   | 13    | ?               | ?                  | ❌ TODO |
| 107.2 Hz   | 14    | ?               | ?                  | ❌ TODO |
| 110.9 Hz   | 15    | ?               | ?                  | ❌ TODO |
| 114.8 Hz   | 16    | ?               | ?                  | ❌ TODO |
| 118.8 Hz   | 17    | ?               | ?                  | ❌ TODO |
| 123.0 Hz   | 18    | ?               | ?                  | ❌ TODO |
| 127.3 Hz   | 19    | ?               | ?                  | ❌ TODO |
| 131.8 Hz   | 20    | ?               | ?                  | ❌ TODO |
| ... (30 more tones) | ... | ?         | ?                  | ❌ TODO |

### DCS Code Mapping (104+ codes)
DCS codes use a different encoding scheme that also needs to be researched:

| DCS Code | Polarity | emitYayin Value | receiveYayin Value | Status |
|----------|----------|-----------------|--------------------| -------|
| D023     | N        | ?               | ?                  | ❌ TODO |
| D023     | I        | ?               | ?                  | ❌ TODO |
| D025     | N        | ?               | ?                  | ❌ TODO |
| ... (100+ more codes) | ... | ?      | ?                  | ❌ TODO |

## Research Methodology

### For CTCSS Tones:
1. Use manufacturer software to configure a channel with specific CTCSS tone
2. Download configuration from radio to JSON
3. Read emitYayin/receiveYayin values from JSON
4. Record mapping in table
5. Repeat for all 50 standard CTCSS tones

### For DCS Codes:
1. Use manufacturer software to configure a channel with specific DCS code
2. Download configuration from radio to JSON
3. Read emitYayin/receiveYayin values from JSON
4. Record mapping in table
5. Repeat for all DCS codes (both N and I polarity)

## Implementation Plan

### Phase 1: Basic Infrastructure (COMPLETE ✅)
- [x] Update PMR171Writer to use emitYayin/receiveYayin fields
- [x] Add _tone_to_yayin() method (with placeholder implementation)
- [x] Add _ctcss_code_to_string() helper method
- [x] Update create_channel() to accept rx_tone/tx_tone strings
- [x] Set ignored fields to 0/255 (sqlevel, spkgain, dmodGain, rxCtcss, txCtcss, etc.)

### Phase 2: CTCSS Mapping (IN PROGRESS ⚠️)
- [ ] Configure each CTCSS tone in manufacturer software
- [ ] Download and analyze each configuration
- [ ] Build complete CTCSS mapping table
- [ ] Update _tone_to_yayin() with real values
- [ ] Test with multiple CTCSS tones

### Phase 3: DCS Mapping (TODO ❌)
- [ ] Configure DCS codes in manufacturer software
- [ ] Download and analyze each configuration
- [ ] Build complete DCS mapping table
- [ ] Add DCS support to _tone_to_yayin()
- [ ] Test with multiple DCS codes

### Phase 4: Validation & Documentation (TODO ❌)
- [ ] Create comprehensive test cases
- [ ] Verify all 50 CTCSS tones work correctly
- [ ] Verify DCS codes work correctly
- [ ] Update all documentation
- [ ] Update user guides with tone limitations

## Current Code Status

### PMR171Writer Changes:
- **create_channel()** now accepts `rx_tone` and `tx_tone` strings instead of codes
- **emitYayin/receiveYayin** are now populated from tone conversion
- **rxCtcss/txCtcss** are hardcoded to 255 (no tone marker)
- **Ignored fields** (sqlevel, spkgain, dmodGain, scrEn, etc.) set to 0

### Known Limitations:
⚠️ **TONE ENCODING IS INCOMPLETE**
- Only placeholder mapping exists for 100.0 Hz (value = 1)
- All other CTCSS tones will default to 0 (no tone)
- DCS codes are not yet supported
- This means **tones will not work** until mapping research is complete

## Testing Required

To complete the tone mapping research, create test files like:

```json
{
  "0": { "channelName": "67.0 Hz", "emitYayin": ?, "receiveYayin": ? },
  "1": { "channelName": "71.9 Hz", "emitYayin": ?, "receiveYayin": ? },
  "2": { "channelName": "74.4 Hz", "emitYayin": ?, "receiveYayin": ? },
  ...
}
```

Configure each in manufacturer software, upload to radio, download back, and record the actual values used.

## Related Files
- `codeplug_converter/writers/pmr171_writer.py` - Updated implementation
- `docs/CTCSS_ANALYSIS.md` - Original CTCSS field analysis
- `docs/CTCSS_FORMAT_TESTING.md` - Test 07 documentation
- `docs/UNTESTED_FIELDS_ANALYSIS.md` - Test 08 documentation
- `D:\Radio\Guohetec\Testing\07_ctcss_format_test.json` - CTCSS test data
- `D:\Radio\Guohetec\Testing\08_untested_fields.json` - Field validation data

## Timeline

**Estimated effort:** 
- CTCSS mapping: 3-4 hours (50 tones × 4 min each)
- DCS mapping: 6-8 hours (104+ codes × 4 min each)
- Testing & validation: 2-3 hours
- **Total: 11-15 hours of systematic testing**

## Priority

**HIGH PRIORITY** - Without this mapping:
- CTCSS tones will not work
- DCS codes will not work
- Amateur radio repeaters requiring tones will be inaccessible
- Privacy codes on PMR/FRS channels will not function

This is essential functionality for a codeplug converter.
