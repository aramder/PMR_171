# Untested Fields Analysis

## Overview
This document details PMR-171 channel fields that have not been thoroughly tested in previous configurations.

## Test File
`tests/test_configs/08_untested_fields.json`

## Fields Being Tested

### 1. sqlevel (Squelch Level)
**Purpose**: Controls the squelch threshold for the channel  
**Test Channels**: 0-2  
**Values Tested**:
- Channel 0: `sqlevel=0` (most sensitive/open squelch)
- Channel 1: `sqlevel=5` (medium)
- Channel 2: `sqlevel=9` (least sensitive/tight squelch)

**Expected Range**: Likely 0-9 or 0-15  
**Expected Behavior**:
- Lower values = more sensitive (squelch opens with weaker signals)
- Higher values = less sensitive (requires stronger signal to open squelch)
- Factory software should display as squelch level setting
- Radio should adjust squelch threshold accordingly

### 2. spkgain (Speaker Gain/Volume)
**Purpose**: Per-channel speaker volume adjustment  
**Test Channels**: 10-12  
**Values Tested**:
- Channel 10: `spkgain=0` (minimum/default)
- Channel 11: `spkgain=5` (medium)
- Channel 12: `spkgain=15` (maximum)

**Expected Range**: Likely 0-15  
**Expected Behavior**:
- Controls audio output volume for this specific channel
- May be additive to global volume setting
- Factory software should show volume adjustment
- Radio should play audio at adjusted volume

### 3. dmodGain (Demodulator Gain)
**Purpose**: Adjusts receiver demodulator gain  
**Test Channels**: 20-22  
**Values Tested**:
- Channel 20: `dmodGain=0` (default/minimum)
- Channel 21: `dmodGain=5` (medium boost)
- Channel 22: `dmodGain=15` (maximum boost)

**Expected Range**: Likely 0-15  
**Expected Behavior**:
- Adjusts receiver sensitivity/gain
- May affect audio quality or noise
- Could be used to compensate for weak signals
- Higher values may increase background noise

### 4. scrEn + scrSeed1/scrSeed2 (Scrambler Enable + Seeds)
**Purpose**: Voice scrambling/privacy feature  
**Test Channels**: 30-31  
**Values Tested**:
- Channel 30: `scrEn=0` (scrambler off)
- Channel 31: `scrEn=1, scrSeed1=1234, scrSeed2=5678` (scrambler on with seeds)

**Expected Behavior**:
- `scrEn=0`: Normal clear audio
- `scrEn=1`: Audio is scrambled using the seed values
- Both radios must use identical seed values to communicate
- scrSeed1 and scrSeed2 form the scrambling algorithm key
- Factory software should show scrambler on/off and seed values
- Not compatible with CTCSS/DCS when enabled

**Note**: This is likely a simple analog voice inversion scrambler, NOT secure encryption. Easily defeated with proper equipment.

### 5. chBsMode (Channel Base/Busy Mode?)
**Purpose**: Unknown - possibly channel busy detection mode  
**Test Channels**: 40-41  
**Values Tested**:
- Channel 40: `chBsMode=0` (default)
- Channel 41: `chBsMode=1` (alternate mode)

**Expected Range**: Likely 0-1 (boolean)  
**Hypothesis**: May control busy channel lockout behavior or repeater mode
**Expected Behavior**: Unknown - requires testing to determine

### 6. emitYayin (Transmit Enable/Broadcast?)
**Purpose**: Unknown - Turkish word "yayin" means "broadcast"  
**Test Channels**: 50-51  
**Values Tested**:
- Channel 50: `emitYayin=0` (default)
- Channel 51: `emitYayin=1` (enabled)

**Expected Range**: Likely 0-1 (boolean)  
**Hypothesis**: May control TX enable, PTT lockout, or broadcast mode  
**Expected Behavior**: 
- 0 = Normal operation
- 1 = Possibly enables/disables transmit, or enables broadcast mode

### 7. receiveYayin (Receive Enable/Monitor?)
**Purpose**: Unknown - possibly receive enable or monitor mode  
**Test Channels**: 52-53  
**Values Tested**:
- Channel 52: `receiveYayin=0` (default)
- Channel 53: `receiveYayin=1` (enabled)

**Expected Range**: Likely 0-1 (boolean)  
**Hypothesis**: May control RX enable or monitor mode  
**Expected Behavior**:
- 0 = Normal operation
- 1 = Possibly RX-only mode or monitoring mode

## Fields NOT Included (Already Well-Tested)

These fields are already thoroughly tested in other test configurations:

- `callFormat` - Tested in 01-06
- `callId1-4` - Tested in 03 (DMR)
- `chType` - Tested in 01-06
- `channelHigh/Low` - Tested in 06 (edge cases)
- `channelName` - Tested in all configs
- `ownId1-4` - Tested in 03 (DMR)
- `rxCc/txCc` - Tested in 03 (DMR color codes)
- `rxCtcss/txCtcss` - Tested in 05, 07
- `slot` - Tested in 03 (DMR timeslots)
- `vfoaFrequency1-4` - Tested in all configs
- `vfoaMode/vfobMode` - Tested in 02 (all modes)

## Testing Procedure

### Phase 1: Factory Software
1. Load `08_untested_fields.json` into factory software
2. For each channel group, verify:
   - **Squelch (0-2)**: Check if squelch level displays/adjusts
   - **Speaker Gain (10-12)**: Check if volume setting displays
   - **Demod Gain (20-22)**: Check if gain adjustment displays
   - **Scrambler (30-31)**: Check if scrambler on/off shows, seed values display
   - **chBsMode (40-41)**: Note any visible difference between channels
   - **emitYayin (50-51)**: Note any TX-related indicators
   - **receiveYayin (52-53)**: Note any RX-related indicators

### Phase 2: Radio Programming
1. Program codeplug to radio
2. Navigate to each test channel
3. Document what displays on radio screen for each setting

### Phase 3: Functional Testing

**Squelch Test (Channels 0-2)**:
1. Set radio to each channel in sequence
2. Adjust RF generator or walk away from signal source
3. Note at what signal strength squelch opens for each channel
4. Expected: Ch0 opens with weakest signal, Ch2 requires strongest

**Speaker Gain Test (Channels 10-12)**:
1. Receive a signal on each channel
2. Note relative audio volume (without changing main volume knob)
3. Expected: Ch10 quietest, Ch12 loudest

**Demod Gain Test (Channels 20-22)**:
1. Receive a weak signal on each channel
2. Note audio quality and background noise
3. Expected: Ch22 may have more gain but also more noise

**Scrambler Test (Channels 30-31)**:
1. Have second radio transmit clear audio
2. Receive on Ch30 - should hear normally
3. Receive on Ch31 - audio should be scrambled/unintelligible
4. Set second radio to match seed values (1234, 5678) 
5. Should now hear clearly on Ch31

**chBsMode Test (Channels 40-41)**:
1. Compare behavior between the two channels
2. Test TX/RX on both
3. Try to trigger busy channel lockout
4. Document any differences

**emitYayin Test (Channels 50-51)**:
1. Attempt to transmit on Ch50 (emitYayin=0)
2. Attempt to transmit on Ch51 (emitYayin=1)
3. Note if PTT works differently
4. Check for any TX indicators

**receiveYayin Test (Channels 52-53)**:
1. Receive signal on Ch52 (receiveYayin=0)
2. Receive signal on Ch53 (receiveYayin=1)
3. Note any differences in RX behavior
4. Check for monitor mode indicators

## Expected Findings

### Likely Functional
- `sqlevel`: Almost certainly controls squelch threshold
- `spkgain`: Likely controls per-channel volume
- `scrEn/scrSeed1/scrSeed2`: Scrambler feature (common in commercial radios)

### Uncertain
- `dmodGain`: May or may not have audible effect
- `chBsMode`: Purpose unknown
- `emitYayin/receiveYayin`: Purpose unknown, may be unused

### Possibly Unused
Some fields may be present in the format but not actually implemented in firmware. Testing will reveal which fields actually affect radio behavior.

## Implementation Priority

After testing, implement in order of usefulness:

1. **High Priority**: sqlevel (essential for usability)
2. **High Priority**: scrEn/scrSeed1/scrSeed2 (if functional - useful privacy feature)
3. **Medium Priority**: spkgain (nice quality-of-life feature)
4. **Low Priority**: dmodGain (niche use case)
5. **TBD**: chBsMode, emitYayin, receiveYayin (depends on test results)

## Documentation Updates Needed

After testing, update:
1. This document with actual behavior observed
2. `tests/test_configs/README.md` with 08_untested_fields entry
3. CHIRP parser to handle these fields (if functional)
4. PMR171 writer to output these fields correctly
5. Field validation rules for value ranges

## Notes

- All test channels use VHF 146.52 MHz simplex for consistency
- All channels use NFM (mode 6)
- All channels have no CTCSS (rxCtcss=255, txCtcss=255)
- Standard format values: callFormat=255, chType=255, txCc=1

## Related Documentation

- `docs/CHIRP_FORMAT_ANALYSIS.md` - CHIRP field mappings
- `docs/FACTORY_JSON_COMPARISON.md` - PMR171 format details
- `tests/test_configs/README.md` - All test configurations
