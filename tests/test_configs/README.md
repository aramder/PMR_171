# PMR-171 Test Configuration Files

This directory contains test configuration files for validating PMR-171 codeplug conversion functionality.

## Test Files

### Test 11: Complete CTCSS Validation ✅ READY

**File**: `11_complete_ctcss_validation.json`  
**Purpose**: Validate complete CTCSS tone mapping (all 50 standard tones)  
**Status**: Ready for testing  
**Channels**: 25 test scenarios

**Coverage**:
- Common tones (100.0, 123.0, 131.8, 141.3, 146.2, 156.7 Hz)
- Edge cases (67.0, 69.3, 250.3, 254.1 Hz)
- Mid-range tones (107.2, 162.2, 186.2 Hz)
- Split tone examples (different TX/RX)
- TX-only configurations
- RX-only configurations
- No tone baseline
- Coverage of all yayin offset ranges

**Instructions**: See `11_ValidationInstructions.md`

**Generator**: `11_complete_ctcss_validation.py`

### Historical Test Files

These files were used during the CTCSS mapping discovery process:

- **05_ctcss_dcs.json**: Initial CTCSS/DCS exploration
- **07_ctcss_format_test.json**: Format testing (index vs raw encoding)
- **08_untested_fields.json**: Field functionality testing

## CTCSS Mapping Status

**Current Status**: ✅ 100% COMPLETE (50/50 tones mapped)

All 50 standard CTCSS tones have been mapped to their yayin encoding values through systematic testing (Tests 05-10). The complete mapping is implemented in:
- `pmr_171_cps/writers/pmr171_writer.py`
- Documented in `docs/COMPLETE_CTCSS_MAPPING.md`

## Test History

| Test | Purpose | Result | Tones Mapped |
|------|---------|--------|--------------|
| 05 | Initial discovery | ✅ Success | 6 tones |
| 07 | Format confirmation | ✅ Success | Confirmed yayin encoding |
| 08 | Field testing | ✅ Success | Identified ignored fields |
| 09 | Pattern analysis | ✅ Success | 14 tones total |
| 10 | Complete coverage | ✅ Success | 50 tones total (100%) |
| 11 | Validation | ⚠️ Pending | Validate all mappings |

## Creating New Test Files

### Using the Generator Script

Example for Test 11:
```bash
python tests/test_configs/11_complete_ctcss_validation.py
```

### Manual Creation

Test files are JSON dictionaries with channel entries. Each channel must include:

**Required fields**:
- `emitYayin`: TX tone (0 = no tone)
- `receiveYayin`: RX tone (0 = no tone)
- `vfoaFrequency1-4`: RX frequency (4 bytes)
- `vfobFrequency1-4`: TX frequency (4 bytes)
- `vfoaMode`, `vfobMode`: Mode (6 = FM)
- `channelName`: Name with null terminator

**Important**:
- Set `txCtcss` and `rxCtcss` to 255 (ignored by radio)
- Use `emitYayin`/`receiveYayin` for CTCSS tones
- Channel indexes as string keys ("0", "1", etc.)

### CTCSS Tone Reference

Common tones and their yayin values:
```python
# Most common tones
100.0 Hz → yayin 13  # Most common in USA
123.0 Hz → yayin 19  # IRLP/EchoLink
131.8 Hz → yayin 21  # Common repeater
146.2 Hz → yayin 24  # Common repeater
```

See `docs/COMPLETE_CTCSS_MAPPING.md` for the complete 50-tone table.

## Validation Procedure

1. Generate test file using Python script
2. Copy JSON file to radio
3. Verify channels load correctly
4. Test tone functionality (RX detection, TX generation)
5. Read back configuration and compare
6. Document results

## Related Documentation

- `docs/CompleteCtcssMapping.md` - Complete CTCSS reference
- `docs/Test10CtcssFindings.md` - Test 10 detailed results
- `docs/CtcssAnalysis.md` - CTCSS field analysis
- `CtcssMappingsDiscovered.txt` - Quick reference
- `pmr_171_cps/writers/pmr171_writer.py` - Implementation

## Notes

All test files use 146.520 MHz (2m national simplex) for safety and ease of testing. Adjust frequencies as needed for your testing requirements.
