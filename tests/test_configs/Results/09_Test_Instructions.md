# Test 09: CTCSS Tone Pattern Discovery

**Purpose**: Determine the encoding pattern for CTCSS tones in emitYayin/receiveYayin fields

## Test File
`09_tone_pattern_test.json`

## What This Tests

This file contains 8 strategically-selected CTCSS tones designed to probe the encoding pattern:

| Ch | Tone Freq | Table Position | Purpose |
|----|-----------|----------------|---------|
| 0  | None      | -              | Control (no tone) |
| 1  | 71.9 Hz   | **2**          | Test if position 2 follows pattern |
| 2  | 74.4 Hz   | **3**          | Test early sequence |
| 3  | 85.4 Hz   | **7**          | Just before known 88.5 (pos 8→yayin 9) |
| 4  | 94.8 Hz   | **10**         | Mid-range sample |
| 5  | 110.9 Hz  | **15**         | Between known 100.0 and 123.0 |
| 6  | 131.8 Hz  | **20**         | Test middle of table |
| 7  | 141.3 Hz  | **22**         | Just before known 146.2 (pos 23→yayin 24) |
| 8  | 151.4 Hz  | **24**         | Between known 146.2 and 156.7 |
| 9  | 162.2 Hz  | **26**         | CRITICAL: Just after 156.7 anomaly |
| 10 | 186.2 Hz  | **30**         | Later position sample |
| 11 | 225.7 Hz  | **35**         | Test later range |
| 12 | 159.8 Hz  | **40**         | Near end of table |
| 13 | 189.9 Hz  | **45**         | Test late positions |
| 14 | 254.1 Hz  | **50**         | Last tone in table |

## Testing Procedure

### Step 1: Configure in Manufacturer Software
1. Open Guohetec programming software
2. Load `09_tone_pattern_test.json` into the software
3. **Use the software's CTCSS tone picker to configure each channel**:
   - Ch 0: No tone (leave as-is)
   - Ch 1: Set TX/RX tone to **71.9 Hz**
   - Ch 2: Set TX/RX tone to **74.4 Hz**
   - Ch 3: Set TX/RX tone to **85.4 Hz**
   - Ch 4: Set TX/RX tone to **94.8 Hz**
   - Ch 5: Set TX/RX tone to **110.9 Hz**
   - Ch 6: Set TX/RX tone to **131.8 Hz**
   - Ch 7: Set TX/RX tone to **141.3 Hz**
   - Ch 8: Set TX/RX tone to **151.4 Hz**
   - Ch 9: Set TX/RX tone to **162.2 Hz** ⚠️ CRITICAL TEST
   - Ch 10: Set TX/RX tone to **186.2 Hz**
   - Ch 11: Set TX/RX tone to **225.7 Hz**
   - Ch 12: Set TX/RX tone to **159.8 Hz**
   - Ch 13: Set TX/RX tone to **189.9 Hz**
   - Ch 14: Set TX/RX tone to **254.1 Hz** (last tone)

### Step 2: Upload to Radio
1. Connect radio
2. Upload the configured codeplug
3. Verify upload successful

### Step 3: Download from Radio
1. Read back the configuration from the radio
2. Save as `09_tone_pattern_test_readback.json`

### Step 4: Analyze Results
Run the analysis script:
```
python D:\Radio\Guohetec\Testing\extract_tone_mappings.py
```

Then compare with pattern analysis to crack the encoding!

## Expected Outcomes

### If Pattern is Linear (yayin = position + offset):
- Position 2 (71.9) should show consistent offset from position 1
- All subsequent tones should have same offset
- We can generate all 50 mappings immediately!

### If There's a Gap/Reserved Entry:
- Tones before the gap will have one offset
- Tones after the gap will have different offset
- Position 26 (162.2 Hz) is the critical test

### If Pattern is Complex:
- We'll still gain 8+ new mappings (total 14/50 = 28%)
- With 28% coverage, pattern should become clearer
- May need one more round of testing

## Why These Specific Tones?

1. **Position 2 & 3**: Confirm start of sequence
2. **Position 7**: Probe for gap before position 8 (where 88.5→9 suggests offset changes)
3. **Position 24**: Between known 23→24 and anomalous 25→27
4. **Position 26**: CRITICAL - if this has yayin=28 or 29, confirms gap at 26
5. **Positions 10, 15, 20, 30, 35, 40, 45, 50**: Binary search coverage

## Success Criteria

With these 8 new data points plus our existing 6, we'll have **14 of 50 tones (28% coverage)** - enough to confidently determine if there's an algorithmic pattern or if we need to continue manual mapping.

**Time Investment**: 15-20 minutes to configure  
**Potential Savings**: 1.5-2 hours if pattern is found

## After Testing

1. Run `python extract_tone_mappings.py` on the readback file
2. Run `python analyze_tone_pattern.py` with updated data
3. Update `_tone_to_yayin()` in `pmr171_writer.py` with new mappings
4. If pattern found, generate all 50 mappings programmatically!
