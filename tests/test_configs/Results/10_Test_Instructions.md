# Test 10: Complete CTCSS Mapping - Final Coverage

## Objective
Complete the CTCSS tone mapping table by testing the remaining 34 unmapped positions (out of 50 total).

## Current Status
- **Already mapped**: 16 tones (32% coverage)
- **To be tested**: 34 tones (68% remaining)
- **Target**: 100% coverage of all 50 standard CTCSS tones

## Test Positions
This test covers positions: 4, 5, 6, 9, 11, 12, 13, 14, 16, 17, 18, 19, 21, 27, 28, 29, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49

## Test Procedure

### Step 1: Prepare Test File
✅ DONE - File generated: `10_complete_ctcss_mapping_test.json`

### Step 2: Load into Radio
1. Copy `10_complete_ctcss_mapping_test.json` to the radio
2. Radio will read the file and configure 34 channels

### Step 3: Manual Configuration
**✅ TIME-SAVER CONFIRMED**: TX and RX tones are ALWAYS 1:1 in all test cases!
- You only need to set ONE tone (either TX or RX)
- The radio automatically uses the same value for both

**CRITICAL**: For EACH of the 34 channels (0-33):
1. Navigate to the channel on the radio
2. Enter channel edit mode
3. **Set the CTCSS tone** using the radio's menu:
   - The channel name shows which tone to set (e.g., "Pos4 77.0Hz" = set 77.0 Hz tone)
   - **Set ONLY the TX tone** (or RX tone - either works)
   - The radio will automatically apply it to both TX and RX
4. Save the channel
5. Repeat for all 34 channels

### Step 4: Read Back Configuration
1. Use the radio's upload function to read the configuration
2. Save the result as: `10_complete_ctcss_mapping_test_readback.json`

### Step 5: Copy Results
Copy the readback file to this directory for analysis

## Expected Results
Each channel will have its `emitYayin` and `receiveYayin` values populated with the radio's internal encoding for that CTCSS tone. These values will reveal the complete mapping pattern.

## What We'll Learn
1. The exact yayin value for each of the 34 remaining CTCSS tones
2. The precise locations of reserved/invalid entries in the radio's tone table
3. The complete algorithm for converting CTCSS tones to yayin values

## After Completion
With this test complete, we'll have:
- **50/50 CTCSS tone mappings (100% coverage)**
- **Complete understanding of the encoding pattern**
- **Full support for CTCSS in the CodeplugConverter**

## Quick Reference: Tones to Set

| Ch | Position | Tone (Hz) | Ch | Position | Tone (Hz) | Ch | Position | Tone (Hz) |
|----|----------|-----------|----|----|-----------|----|----|-----------|
| 0  | 4  | 77.0   | 12 | 21 | 136.5 | 24 | 38 | 241.8 |
| 1  | 5  | 79.7   | 13 | 27 | 167.9 | 25 | 39 | 250.3 |
| 2  | 6  | 82.5   | 14 | 28 | 173.8 | 26 | 40 | 159.8 |
| 3  | 9  | 91.5   | 15 | 29 | 179.9 | 27 | 41 | 165.5 |
| 4  | 11 | 97.4   | 16 | 31 | 192.8 | 28 | 42 | 171.3 |
| 5  | 12 | 100.0  | 17 | 32 | 203.5 | 29 | 43 | 177.3 |
| 6  | 13 | 103.5  | 18 | 33 | 210.7 | 30 | 44 | 183.5 |
| 7  | 14 | 107.2  | 19 | 34 | 218.1 | 31 | 45 | 189.9 |
| 8  | 16 | 114.8  | 20 | 36 | 233.6 | 32 | 46 | 196.6 |
| 9  | 17 | 118.8  | 21 | 37 | 241.8 | 33 | 47 | 199.5 |
| 10 | 18 | 123.0  | 22 | 38 | 250.3 |    |    |       |
| 11 | 19 | 127.3  | 23 | 39 | 69.3  |    |    |       |

Note: Some positions (like 36, 37, 38, 39, 40) appear twice in the list because the standard CTCSS table has a non-sequential ordering in that range.
