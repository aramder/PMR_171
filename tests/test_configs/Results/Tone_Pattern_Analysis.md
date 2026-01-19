# CTCSS Tone Encoding Pattern Analysis

**Date**: January 18, 2026  
**Goal**: Determine if yayin values follow a predictable pattern

## Discovered Mappings

| Frequency | Standard Table Position | yayin Value | Difference |
|-----------|------------------------|-------------|------------|
| 67.0 Hz   | 1                      | 1           | 0          |
| 88.5 Hz   | 8                      | 9           | +1         |
| 100.0 Hz  | 12                     | 13          | +1         |
| 123.0 Hz  | 18                     | 19          | +1         |
| 146.2 Hz  | 23                     | 24          | +1         |
| 156.7 Hz  | 25                     | 27          | +2         |

## Pattern Analysis

### Hypothesis 1: yayin = table_position + constant
**Result**: ❌ FAILED  
**Reason**: Differences vary (0, 1, 2) - not consistent

### Hypothesis 2: Gap at position 26
**Result**: ❌ FAILED  
**Reason**: If gap at position 26:
- Positions 1-25 should map to yayin = position
- But 88.5 Hz (position 8) maps to yayin=9 (not 8)

### Hypothesis 3: yayin = table_position + 1, with exceptions
**Result**: 🤔 PARTIALLY MATCHES  
**Pattern**: 
- Most tones: yayin = position + 1
- Exception: 67.0 Hz: yayin = position (no offset)
- Exception: 156.7 Hz: yayin = position + 2

**Problem**: Why exceptions? Not enough data to determine rule.

## Observations

### 1. Limited Sample Size
With only 6 data points out of 50 total tones, we cannot reliably determine the pattern:
- 12% coverage is insufficient for pattern detection
- Need at least 10-15 samples to confirm a hypothesis
- Edge cases and exceptions may not be representative

### 2. Non-Sequential yayin Values
The yayin values (1, 9, 13, 19, 24, 27) have varying gaps:
- Gap between 1 and 9 = 8
- Gap between 9 and 13 = 4
- Gap between 13 and 19 = 6
- Gap between 19 and 24 = 5
- Gap between 24 and 27 = 3

This irregular spacing suggests the encoding is NOT a simple linear function.

### 3. Possible Explanations

#### A. Radio Uses Different Tone Ordering
The manufacturer may order tones differently than the standard CHIRP table:
- By usage frequency (most common first)
- By regional preference
- Alphabetically by label
- Some proprietary ordering

#### B. Non-Contiguous Internal Table
The radio's internal tone table may have:
- Reserved/unused entries
- Gaps for future tones
- Special entries (all-call, selective call, etc.)

#### C. Encoding Scheme
The encoding might be:
- BCD (Binary Coded Decimal)
- Packed format with special markers
- Related to hardware PLL frequency divisors
- Tone frequency * multiplier

### 4. Pattern Hypothesis That Might Work

Looking at position 25 (156.7 Hz) having yayin=27:
- If position 26 is reserved/skipped
- Then: yayin = position (for pos 1-25) + number_of_gaps_before_position
- But this doesn't explain 67.0 being exact match while 88.5 is +1

## Recommendations

### Strategy 1: Continue Case-by-Case Mapping (Current Approach)
✅ **RECOMMENDED FOR NOW**
- We have 6 tones working
- Add more as we test them
- No risk of incorrect assumptions
- Pattern may emerge with more data

### Strategy 2: Test Adjacent Tones
Test tones near our known mappings to find pattern:
- Test 71.9 Hz (position 2) - if yayin=2, confirms starting pattern
- Test 85.4 Hz (position 7) - check if gap exists before position 8
- Test 154.0 Hz (position 24) - between our known position 23 and 25
- Test 162.2 Hz (position 26) - critical position after the +2 anomaly

### Strategy 3: Binary Search Pattern
Once we have ~10 samples:
- Test tone at position 25 (middle of range)
- Test tone at position 12
- Test tone at position 38
- Narrow down pattern with strategic samples

## Conclusion

**With only 6 samples (12% coverage), we cannot reliably determine the encoding pattern.**

The safest approach is to continue mapping tones one-by-one as we test them. However, strategic testing of a few key positions (2, 7, 24, 26) could help us identify the pattern and potentially map all 50 tones algorithmically.

## Action Items

1. ✅ Use discovered 6 mappings immediately (already implemented)
2. ⚠️ Test 3-4 strategic tones to probe for pattern:
   - 71.9 Hz (position 2)
   - 85.4 Hz (position 7)  
   - 151.4 Hz (position 24)
   - 162.2 Hz (position 26)
3. 📋 Re-analyze pattern with 10+ samples
4. 🎯 If pattern found, generate all 50 mappings algorithmically
5. ✅ If no pattern, continue manual mapping

**Estimated Time Savings if Pattern Found**: 1.5-2 hours
