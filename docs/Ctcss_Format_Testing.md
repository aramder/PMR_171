# CTCSS Format Testing Procedure

## Purpose
This document provides step-by-step instructions for testing which CTCSS encoding format the PMR-171 radio actually uses.

## Background
We've discovered two different CTCSS encoding methods in the codeplug files:

1. **Raw Format**: `value = frequency_hz × 10` (from SAMPLE_CHANNELS.json - actual radio readback)
2. **Index Format**: `value = index in tone table` (from test configs - based on documentation)

**We need to determine which format the radio actually uses.**

## Test File
`tests/test_configs/07_ctcss_format_test.json` contains paired channels testing both formats:

| Channels | Tone | Raw Value | Index Value |
|----------|------|-----------|-------------|
| 10-11 | 100.0 Hz | 1000 | 10 |
| 20-21 | 131.8 Hz | 1318 | 17 |
| 30-31 | 156.7 Hz | 1567 | 28 |
| 40-41 | 107.2 Hz | 1072 | 7 |

- Odd channel numbers (10, 20, 30, 40) = Index format
- Even channel numbers (11, 21, 31, 41) = Raw format

## Testing Procedure

### Phase 1: Factory Software Test

1. **Open Factory Software**
   - Launch the Guohetec PMR-171 programming software

2. **Load Test File**
   - Open `tests/test_configs/07_ctcss_format_test.json`
   - Note any errors or warnings

3. **Examine CTCSS Display**
   - For each channel, check if the CTCSS tone displays correctly:

   | Channel | Expected Tone | Format | Displays Correctly? |
   |---------|---------------|--------|---------------------|
   | 0 | No Tone | Both | ☐ |
   | 10 | 100.0 Hz | Index=10 | ☐ |
   | 11 | 100.0 Hz | Raw=1000 | ☐ |
   | 20 | 131.8 Hz | Index=17 | ☐ |
   | 21 | 131.8 Hz | Raw=1318 | ☐ |
   | 30 | 156.7 Hz | Index=28 | ☐ |
   | 31 | 156.7 Hz | Raw=1567 | ☐ |
   | 40 | 107.2 Hz | Index=7 | ☐ |
   | 41 | 107.2 Hz | Raw=1072 | ☐ |

4. **Document Results**
   - Note which channels show the correct tone frequency
   - Note any channels that show incorrect tones or errors
   - Take screenshots if possible

### Phase 2: Radio Programming Test

1. **Connect Radio**
   - Connect PMR-171 to computer via programming cable
   - Ensure radio is powered on

2. **Program to Radio**
   - Write the codeplug to the radio
   - Note any errors during programming

3. **Verify Channel Display**
   - On the radio screen, navigate to each channel
   - Check if the CTCSS tone indicator shows correctly:

   | Channel | Expected Display | Actually Shows? |
   |---------|------------------|-----------------|
   | 0 | No tone indicator | |
   | 10 | 100.0 Hz or "CT 100.0" | |
   | 11 | 100.0 Hz or "CT 100.0" | |
   | 20 | 131.8 Hz or "CT 131.8" | |
   | 21 | 131.8 Hz or "CT 131.8" | |
   | 30 | 156.7 Hz or "CT 156.7" | |
   | 31 | 156.7 Hz or "CT 156.7" | |
   | 40 | 107.2 Hz or "CT 107.2" | |
   | 41 | 107.2 Hz or "CT 107.2" | |

### Phase 3: Functional Test (Optional but Recommended)

**You'll need:**
- A second PMR-171 or compatible radio
- Or a CTCSS tone generator/decoder

**Test procedure:**

1. **Set up receiving radio**
   - Tune to 146.52 MHz
   - Enable CTCSS squelch with one of the test tones (e.g., 100.0 Hz)

2. **Test Channel 10 (Index format, 100.0 Hz)**
   - Transmit from test radio on channel 10
   - Does receiving radio's squelch open? ☐ Yes ☐ No

3. **Test Channel 11 (Raw format, 100.0 Hz)**
   - Transmit from test radio on channel 11
   - Does receiving radio's squelch open? ☐ Yes ☐ No

4. **Repeat for other tone pairs**
   - Test channels 20/21 (131.8 Hz)
   - Test channels 30/31 (156.7 Hz)
   - Test channels 40/41 (107.2 Hz)

5. **Verify with CTCSS decoder** (if available)
   - Use a service monitor or CTCSS decoder
   - Confirm the actual transmitted tone matches expectations

## Results Analysis

### Scenario A: Raw Format is Correct
- Channels 11, 21, 31, 41 (raw values) work correctly
- Channels 10, 20, 30, 40 (index values) show errors or wrong tones

**Action**: Use raw format (frequency × 10) in converter

### Scenario B: Index Format is Correct
- Channels 10, 20, 30, 40 (index values) work correctly  
- Channels 11, 21, 31, 41 (raw values) show errors or wrong tones

**Action**: Use index format with lookup table in converter

### Scenario C: Both Work (Unlikely)
- Both formats display and function correctly
- Radio may auto-detect and convert

**Action**: Prefer raw format for simplicity

### Scenario D: Neither Works
- Both formats show errors
- May indicate a different encoding entirely

**Action**: Read more codeplugs from working radios to find pattern

## Expected Outcome

Based on the evidence:
- **SAMPLE_CHANNELS.json** came from a working radio readback
- It uses raw format (1000, 1318, 1567, 1072)
- **Most likely**: Raw format is correct

But testing will confirm this conclusively.

## Recording Your Results

### Test Results Template

```
Date: _______________
Tester: _______________
Radio Firmware: _______________
Software Version: _______________

Phase 1 - Factory Software:
[ ] Loaded file successfully
[ ] No errors or warnings

Channel Display Results:
Ch 0:  [ ] Correct (no tone)
Ch 10: [ ] Correct (100.0 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 11: [ ] Correct (100.0 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 20: [ ] Correct (131.8 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 21: [ ] Correct (131.8 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 30: [ ] Correct (156.7 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 31: [ ] Correct (156.7 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 40: [ ] Correct (107.2 Hz)  [ ] Wrong (shows: _____)  [ ] Error
Ch 41: [ ] Correct (107.2 Hz)  [ ] Wrong (shows: _____)  [ ] Error

Phase 2 - Radio Programming:
[ ] Programmed successfully
[ ] Errors: ____________________

Radio Display Results:
Ch 0:  Shows: ________________
Ch 10: Shows: ________________
Ch 11: Shows: ________________
Ch 20: Shows: ________________
Ch 21: Shows: ________________
Ch 30: Shows: ________________
Ch 31: Shows: ________________
Ch 40: Shows: ________________
Ch 41: Shows: ________________

Phase 3 - Functional Test (Optional):
Ch 10: [ ] Opens squelch  [ ] Does not open squelch
Ch 11: [ ] Opens squelch  [ ] Does not open squelch
Ch 20: [ ] Opens squelch  [ ] Does not open squelch
Ch 21: [ ] Opens squelch  [ ] Does not open squelch
Ch 30: [ ] Opens squelch  [ ] Does not open squelch
Ch 31: [ ] Opens squelch  [ ] Does not open squelch
Ch 40: [ ] Opens squelch  [ ] Does not open squelch
Ch 41: [ ] Opens squelch  [ ] Does not open squelch

CONCLUSION:
[ ] Raw format is correct (channels 11, 21, 31, 41 work)
[ ] Index format is correct (channels 10, 20, 30, 40 work)
[ ] Both work (unexpected)
[ ] Neither work (need more investigation)

Additional Notes:
________________________________________________
________________________________________________
________________________________________________
```

## Next Steps After Testing

1. Update `docs/CTCSS_ANALYSIS.md` with confirmed format
2. Implement correct encoding in `codeplug_converter/parsers/chirp_parser.py`
3. Implement correct encoding in `codeplug_converter/writers/pmr171_writer.py`
4. Update all test configuration files to use correct format
5. Test converter with real CHIRP files containing CTCSS tones
6. Document DCS (Digital Coded Squelch) if radio supports it

## Questions to Answer

- ☐ Which encoding format does the radio actually use?
- ☐ Does "no tone" use 0 or 255?
- ☐ Can the radio accept both formats?
- ☐ Are there any tone frequency limitations?
- ☐ Does the radio support DCS codes?
- ☐ How are split tones (different RX/TX) displayed?

## Support

If you encounter issues or have questions:
1. Check `docs/CTCSS_ANALYSIS.md` for technical details
2. Review `examples/SAMPLE_CHANNELS.json` for working examples
3. Compare with actual radio readback files
4. Document any anomalies for further investigation
