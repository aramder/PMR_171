# PMR-171 Command Investigation Findings

**Investigation Date:** [YYYY-MM-DD]  
**Investigator:** [Name]  
**Radio Firmware:** [Version if known]  
**Investigation Session:** [Session ID/Number]

## Session Overview

**Duration:** [Start time] to [End time]  
**Commands Tested:** [List of command IDs]  
**Key Discoveries:** [Brief summary]  
**Radio Configuration:** [Backup file reference]

## Command: 0x2E - UNKNOWN_2E (30-byte response)

### Basic Characteristics

**Consistency Test Results:**
- Tests performed: [Number]
- Identical responses: [Yes/No]
- Response variation: [None/Minor/Significant]

**Baseline Response (Radio Default State):**
```
Hex: [30 bytes in hex format]
Dec: [Byte values in decimal]
```

### State Correlation Tests

#### Test 1: Channel Change
**Before:** Channel 1 (146.520 MHz FM)
```
Response: [30 bytes]
```

**After:** Channel 2 (146.540 MHz FM)
```
Response: [30 bytes]
Changed Bytes: [Byte positions that changed]
```

**Analysis:** [What changed and hypothesis why]

#### Test 2: Mode Change
**Before:** FM Mode
```
Response: [30 bytes]
```

**After:** DMR Mode
```
Response: [30 bytes]
Changed Bytes: [Byte positions that changed]
```

**Analysis:** [What changed and hypothesis why]

#### Test 3: Power Level Change
**Before:** Low Power
```
Response: [30 bytes]
```

**After:** High Power
```
Response: [30 bytes]
Changed Bytes: [Byte positions that changed]
```

**Analysis:** [What changed and hypothesis why]

#### Test 4: Squelch Level Change
**Before:** Squelch Level 3
```
Response: [30 bytes]
```

**After:** Squelch Level 8
```
Response: [30 bytes]
Changed Bytes: [Byte positions that changed]
```

**Analysis:** [What changed and hypothesis why]

### Payload Testing

**Empty Payload (no data):**
```
Request: AB CD 2E [CRC CRC]
Response: [30 bytes]
```

**Payload 0x0000:**
```
Request: AB CD 2E 00 00 [CRC CRC]
Response: [30 bytes]
Different from empty: [Yes/No]
```

**Payload 0x0001:**
```
Request: AB CD 2E 00 01 [CRC CRC]
Response: [30 bytes]
```

**Payload 0xFFFF:**
```
Request: AB CD 2E FF FF [CRC CRC]
Response: [30 bytes]
```

**Conclusion:** Payload [does/does not] affect response

### Byte Structure Hypothesis

| Byte(s) | Interpreted As | Value Example | Meaning Hypothesis | Confidence |
|---------|----------------|---------------|-------------------|------------|
| 0-1 | uint16_be | 0x1234 | [Hypothesis] | Low/Med/High |
| 2 | flags | 0x05 | [Bit meanings] | Low/Med/High |
| 3 | uint8 | 0x10 | [Hypothesis] | Low/Med/High |
| 4-5 | uint16_le | 0x5678 | [Hypothesis] | Low/Med/High |
| ... | ... | ... | ... | ... |

### Radio Behavior Observations

**Display Changes:** [Any changes observed]

**LED Activity:** [Any LED changes]

**Audio Output:** [Any beeps or sounds]

**Other Effects:** [Any other observable changes]

### Determined Function

**Command Purpose:** [Best hypothesis of what this command does]

**Confidence Level:** [Low/Medium/High]

**Supporting Evidence:**
1. [Evidence point 1]
2. [Evidence point 2]
3. [Evidence point 3]

**Conflicting Data:**
- [Any observations that don't fit hypothesis]

---

## Command: 0x2D - UNKNOWN_2D (2-byte response)

### Basic Characteristics

**Consistency Test Results:**
- Tests performed: [Number]
- Identical responses: [Yes/No]
- Response variation: [None/Minor/Significant]

**Baseline Response:**
```
Hex: [XX XX]
Dec: [DDD DDD]
As uint16_be: [Value]
As uint16_le: [Value]
```

### State Correlation Tests

#### Various Radio States
| Radio State | Response (Hex) | Response (Dec) | Notes |
|-------------|----------------|----------------|-------|
| CH1 FM Low | XX XX | DDD DDD | Baseline |
| CH2 FM Low | XX XX | DDD DDD | [Changed?] |
| CH1 FM High | XX XX | DDD DDD | [Changed?] |
| CH1 DMR Low | XX XX | DDD DDD | [Changed?] |
| SQL Level 5 | XX XX | DDD DDD | [Changed?] |
| SQL Level 8 | XX XX | DDD DDD | [Changed?] |

### Payload Testing

**Empty Payload:**
```
Response: [XX XX]
```

**Payload 0x0000:**
```
Response: [XX XX]
```

**Payload 0x0001:**
```
Response: [XX XX]
```

**Payload 0xFFFF:**
```
Response: [XX XX]
```

### Interpretation Attempts

**As Status Flag:**
- Bit 0 (0x01): [Meaning if set]
- Bit 1 (0x02): [Meaning if set]
- Bit 2 (0x04): [Meaning if set]
- ...

**As Numeric Value:**
- Range observed: [Min] to [Max]
- Possible units: [Voltage, dBm, Celsius, etc.]
- Correlation with: [Radio measurement]

**As Error Code:**
- Value meanings: [If applicable]

### Determined Function

**Command Purpose:** [Best hypothesis]

**Confidence Level:** [Low/Medium/High]

**Supporting Evidence:**
1. [Evidence point 1]
2. [Evidence point 2]

---

## FFT/Spectrum Commands (0x20-0x23)

### Individual Command Tests

#### 0x20 - FFT Config?
**Test Results:**
```
Response: [Empty/Data]
Effect on 0x39: [None/Changed spectrum data]
```

#### 0x21 - FFT Config?
**Test Results:**
```
Response: [Empty/Data]
Effect on 0x39: [None/Changed spectrum data]
```

#### 0x22 - FFT Config?
**Test Results:**
```
Response: [Empty/Data]
Effect on 0x39: [None/Changed spectrum data]
```

#### 0x23 - FFT Config?
**Test Results:**
```
Response: [Empty/Data]
Effect on 0x39: [None/Changed spectrum data]
```

### Sequence Testing

**Test: 0x20 → 0x21 → 0x22 → 0x23**
```
Result: [Description]
Effect on spectrum: [Description]
```

### Determined Function

**Purpose:** [Hypothesis for these commands]

**Confidence:** [Low/Medium/High]

---

## Other Commands Tested

### 0x04 - Variable Response

**Response Lengths Observed:**
- Empty response: [X times]
- 1-byte response: [X times]
- 2-byte response: [X times]

**Pattern:** [State-dependent? Random? Time-based?]

### 0x00 - PTT Alias

**Confirmed:** Returns 0x07 response (PTT command)

**Usage:** [Appears to be alias/shortcut for PTT]

### 0x03, 0x0C-0x10 - Empty Response Commands

**All return empty responses**

**Hypothesis:** 
- May be configuration commands with no acknowledgment
- May require specific prerequisites to respond
- May be deprecated/unused commands

---

## Overall Findings Summary

### Commands Successfully Identified

1. **0x2E:** [Function determined] - Confidence: [Level]
2. **0x2D:** [Function determined] - Confidence: [Level]
3. **0x20-0x23:** [Function determined] - Confidence: [Level]

### Commands Requiring Further Investigation

1. **0x04:** [Why variable response?]
2. **0x0C-0x10:** [What are prerequisites?]
3. **Others:** [List]

### Unexpected Discoveries

1. [Discovery 1]
2. [Discovery 2]
3. [Discovery 3]

### Questions for Follow-up

1. [Question 1]
2. [Question 2]
3. [Question 3]

---

## Technical Notes

### Radio Behavior Observations

**Normal Operation:** [Any changes to normal radio function during testing]

**Anomalies:** [Any unexpected behavior]

**Recovery:** [Any issues requiring reset or recovery]

### Tool Performance

**Investigation Tool:** [Worked well/Issues encountered]

**Suggestions:** [Improvements for tool or process]

---

## Next Steps

### Immediate Actions
- [ ] Update protocol documentation with confirmed commands
- [ ] Implement helper functions for new commands
- [ ] Create unit tests for verified functions
- [ ] Share findings with project

### Future Investigation
- [ ] Test commands in different firmware versions
- [ ] Investigate command interactions/dependencies
- [ ] Test edge cases and boundary conditions
- [ ] Explore command sequences

---

## Appendices

### A. Raw Investigation Log

```
[Timestamp] >>> consistency 0x2E
[Timestamp] Response: [Data]
[Timestamp] >>> send 0x2E 0000
[Timestamp] Response: [Data]
...
```

### B. Radio Configuration Backup

**File:** [Path to backup]  
**Channels:** [List or description]  
**Settings:** [Key settings]

### C. Test Environment

**Computer:** [OS, Python version]  
**Serial Port:** [COM3, settings]  
**Cables:** [Type, length]  
**Other Tools:** [UART monitor, etc.]

---

**Investigation Complete:** [Date/Time]  
**Results Saved:** [Path to JSON output]  
**Status:** [Success/Partial/Needs follow-up]
