# Test 11: Complete CTCSS Validation

## Objective

Validate that the complete CTCSS mapping discovered from Test 10 works correctly when uploaded to the PMR-171 radio.

## Test File

**File**: `tests/test_configs/11_complete_ctcss_validation.json`  
**Channels**: 25 test channels  
**Status**: ✅ Ready for testing

## Test Coverage

This test validates:
1. ✅ **Common tones** - Most frequently used by repeaters
2. ✅ **Edge cases** - Lowest (67.0) and highest (254.1) frequencies
3. ✅ **Split tones** - Different TX and RX tones
4. ✅ **TX-only** - Transmit tone without receive
5. ✅ **RX-only** - Receive tone without transmit
6. ✅ **No tone** - Baseline comparison
7. ✅ **Offset ranges** - Coverage across all yayin offset patterns

## Channel Layout

### Common Tones (Channels 0-5)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 0 | 100.0Hz Both | 100.0 | 100.0 | 13/13 |
| 1 | 123.0Hz Both | 123.0 | 123.0 | 19/19 |
| 2 | 131.8Hz Both | 131.8 | 131.8 | 21/21 |
| 3 | 141.3Hz Both | 141.3 | 141.3 | 23/23 |
| 4 | 146.2Hz Both | 146.2 | 146.2 | 24/24 |
| 5 | 156.7Hz Both | 156.7 | 156.7 | 27/27 |

### Edge Cases (Channels 10-13)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 10 | 67.0Hz Both | 67.0 | 67.0 | 1/1 |
| 11 | 69.3Hz Both | 69.3 | 69.3 | 2/2 |
| 12 | 250.3Hz Both | 250.3 | 250.3 | 54/54 |
| 13 | 254.1Hz Both | 254.1 | 254.1 | 55/55 |

### Mid-Range Tones (Channels 14-16)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 14 | 107.2Hz Both | 107.2 | 107.2 | 15/15 |
| 15 | 162.2Hz Both | 162.2 | 162.2 | 29/29 |
| 16 | 186.2Hz Both | 186.2 | 186.2 | 37/37 |

### Split Tones (Channels 20-22)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 20 | Split 100/131 | 100.0 | 131.8 | 13/21 |
| 21 | Split 123/146 | 123.0 | 146.2 | 19/24 |
| 22 | Split 67/254 | 67.0 | 254.1 | 1/55 |

### TX-Only Tones (Channels 25-26)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 25 | TX Only 100 | 100.0 | None | 13/0 |
| 26 | TX Only 123 | 123.0 | None | 19/0 |

### RX-Only Tones (Channels 27-28)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 27 | RX Only 100 | None | 100.0 | 0/13 |
| 28 | RX Only 131 | None | 131.8 | 0/21 |

### Baseline & Range Tests (Channels 30, 35-38)
| Ch | Name | TX Tone | RX Tone | yayin TX/RX |
|----|------|---------|---------|-------------|
| 30 | No Tone | None | None | 0/0 |
| 35 | 94.8Hz Both | 94.8 | 94.8 | 11/11 |
| 36 | 151.4Hz Both | 151.4 | 151.4 | 26/26 |
| 37 | 218.1Hz Both | 218.1 | 218.1 | 46/46 |
| 38 | 229.1Hz Both | 229.1 | 229.1 | 49/49 |

## Test Procedure

### Step 1: Load Test File into Radio

1. Copy `11_complete_ctcss_validation.json` to the radio
2. Power on the radio
3. Radio should read the file automatically
4. Verify 25 channels are loaded

### Step 2: Visual Verification

For each channel, navigate to it on the radio and verify:

**Channels 0-5, 10-16, 30, 35-38** (Standard both TX/RX):
- Check TX tone displays correctly
- Check RX tone displays correctly
- Both should match the expected frequency

**Channels 20-22** (Split tones):
- Verify TX tone shows first frequency
- Verify RX tone shows second frequency
- Confirm they are different

**Channels 25-26** (TX-only):
- Verify TX tone is set
- Verify RX tone is OFF/None

**Channels 27-28** (RX-only):
- Verify TX tone is OFF/None
- Verify RX tone is set

**Channel 30** (No tone):
- Verify both TX and RX tones are OFF/None

### Step 3: Functional Testing

#### Test A: Receive Tone Detection
1. Use another radio to transmit on 146.520 MHz with various CTCSS tones
2. For each test channel, verify:
   - Radio opens squelch ONLY when correct RX tone is received
   - Radio ignores transmissions without tone (channel 30 should open for all)
   - Split tone channels respond to correct RX tone

#### Test B: Transmit Tone Generation
1. Use a tone decoder or another radio with CTCSS decode
2. Transmit on each test channel
3. Verify:
   - Correct TX tone is encoded
   - TX-only channels encode tone
   - RX-only channels transmit without tone (channel 27-28)
   - No-tone channel transmits without tone

#### Test C: Split Tone Operation
Focus on channels 20-22:
1. Verify radio transmits with TX tone
2. Verify radio only opens squelch for RX tone
3. Confirm TX and RX tones are different as configured

### Step 4: Factory Software Verification

1. Open `11_complete_ctcss_validation.json` in Guohetec factory software
2. Verify all tones display correctly:
   - Correct frequencies shown
   - Split tones show different TX/RX
   - TX-only and RX-only configurations display properly
3. Try uploading to radio from factory software
4. Verify configuration matches expectations

### Step 5: Read Back and Verify

1. After loading test file, read configuration back from radio
2. Save as `11_complete_ctcss_validation_readback.json`
3. Compare with original:
   - All emitYayin values should match
   - All receiveYayin values should match
   - No unexpected changes

## Expected Results

### Success Criteria

✅ All 25 channels load without errors  
✅ All CTCSS tones display correctly in radio menu  
✅ Receive tone detection works (radio only opens for correct tone)  
✅ Transmit tone generation verified (correct tones encoded)  
✅ Split tones function properly (different TX/RX)  
✅ TX-only and RX-only configurations work  
✅ No tone channel works as baseline (carrier squelch)  
✅ Factory software displays all tones correctly  
✅ Readback matches original configuration  

### If Problems Occur

**Symptom**: Tones don't display correctly in radio menu
- **Likely cause**: Incorrect yayin values
- **Action**: Compare readback with original, identify mismatches

**Symptom**: Radio doesn't open squelch with correct tone
- **Likely cause**: receiveYayin encoding issue
- **Action**: Test with known-working tone (e.g., 100.0 Hz = yayin 13)

**Symptom**: Transmitted tone incorrect or missing
- **Likely cause**: emitYayin encoding issue
- **Action**: Use tone decoder to verify actual transmitted frequency

**Symptom**: Split tones don't work
- **Likely cause**: Radio may not support split tones in this mode
- **Action**: Verify split tone support in radio manual

## Quick Validation Checklist

Use this for rapid testing:

- [ ] Load file into radio successfully
- [ ] Ch 0: 100.0 Hz displays correctly
- [ ] Ch 1: 123.0 Hz displays correctly  
- [ ] Ch 20: Split tone 100/131 displays correctly
- [ ] Ch 25: TX-only 100 Hz displays correctly
- [ ] Ch 27: RX-only 100 Hz displays correctly
- [ ] Ch 30: No tone displays correctly
- [ ] Receive test: Radio opens only for correct tone
- [ ] Transmit test: Correct tone encoded
- [ ] Factory software opens file without errors
- [ ] Readback matches original

## Documentation

After testing, document results:

1. Create `11_VALIDATION_RESULTS.md` with:
   - Success/failure for each test scenario
   - Any unexpected behavior
   - Confirmation of yayin values
   - Screenshots if helpful

2. If all tests pass:
   - Mark CTCSS implementation as VALIDATED
   - Update `docs/COMPLETE_CTCSS_MAPPING.md` with validation status
   - Update `codeplug_converter/writers/pmr171_writer.py` comments

3. If issues found:
   - Document specific problems
   - Identify which yayin values are incorrect
   - Create corrective test if needed

## Related Files

- **Test file**: `tests/test_configs/11_complete_ctcss_validation.json`
- **Generator**: `tests/test_configs/11_complete_ctcss_validation.py`
- **Mapping ref**: `docs/COMPLETE_CTCSS_MAPPING.md`
- **Code impl**: `codeplug_converter/writers/pmr171_writer.py`

## Notes

This test validates the complete CTCSS mapping discovered through Tests 05-10. Success means the CodeplugConverter can now properly convert CHIRP files with ANY standard CTCSS tone to PMR-171 format!

**Frequency**: All channels use 146.520 MHz (2m simplex) for safety and ease of testing.
