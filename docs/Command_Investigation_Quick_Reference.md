# Command Investigation Quick Reference Card

## 🚀 Quick Start

```bash
# Connect radio to COM3, then:
python tests/investigate_commands.py --port COM3 --interactive
```

## 📋 Command Priority List

### 🔴 HIGH Priority (Test First)

| Command | Returns | Investigation Focus |
|---------|---------|---------------------|
| **0x2E** | 30 bytes | Map byte structure, test consistency, correlate with radio state |
| **0x2D** | 2 bytes | Determine if status/measurement, test consistency |

### 🟡 MEDIUM Priority

| Command | Returns | Investigation Focus |
|---------|---------|---------------------|
| **0x20** | Empty | Test with 0x39, may configure FFT |
| **0x21** | Empty | Test with 0x39, may configure FFT |
| **0x22** | Empty | Test with 0x39, may configure FFT |
| **0x23** | Empty | Test with 0x39, may configure FFT |
| **0x04** | Variable | Determine pattern of variation |

### 🟢 LOW Priority

| Command | Returns | Notes |
|---------|---------|-------|
| **0x00** | 0x07 | PTT alias, confirmed |
| **0x03** | Empty | Purpose unknown |
| **0x0C-0x10** | Empty | May need prerequisites |

## 🎯 Investigation Workflow

### Phase 1: Command 0x2E (30-byte response)

```
1. >>> consistency 0x2E         # Test 10 times - same response?
2. >>> send 0x2E                # Get baseline
3. >>> send 0x2E 0000           # Test with payload
4. >>> send 0x2E 0001           # Test variation
5. >>> send 0x2E FFFF           # Test boundary

Then change radio and repeat:
- Change channel → test 0x2E → note byte changes
- Change mode → test 0x2E → note byte changes  
- Change power → test 0x2E → note byte changes
- Change squelch → test 0x2E → note byte changes
```

**Document:** Which bytes change when you change each setting

### Phase 2: Command 0x2D (2-byte response)

```
1. >>> consistency 0x2D         # Same 2 bytes every time?
2. >>> send 0x2D                # Baseline
3. >>> send 0x2D 0000           # With payload
4. >>> send 0x2D FFFF           # Boundary test

Interpret the 2 bytes as:
- uint16 big-endian
- uint16 little-endian  
- Two separate uint8 values
- Bit flags
```

**Document:** Does value correlate with radio measurement?

### Phase 3: FFT Commands (0x20-0x23)

```
# Baseline spectrum reading
>>> send 0x39 0000

# Test each FFT config command
>>> send 0x20 0100
>>> send 0x39 0000              # Spectrum changed?

>>> send 0x21 0200
>>> send 0x39 0000              # Spectrum changed?

>>> send 0x22 0400
>>> send 0x39 0000              # Spectrum changed?

>>> send 0x23 0800
>>> send 0x39 0000              # Spectrum changed?

# Try sequence
>>> send 0x20 0100
>>> send 0x21 0200  
>>> send 0x22 0400
>>> send 0x23 0800
>>> send 0x39 0000              # Combined effect?
```

## 📝 Documentation Template

Use while testing:

```
Command: 0xXX
Time: [HH:MM]
Radio State: [CH#, Mode, Power, SQL]
Request: [Hex bytes]
Response: [Hex bytes]
Display: [What radio shows]
Notes: [Observations]
```

## 🔍 Byte Analysis Checklist

For multi-byte responses, check:

- [ ] Consistent across multiple tests?
- [ ] Changes with channel number?
- [ ] Changes with frequency?
- [ ] Changes with FM ↔ DMR mode?
- [ ] Changes with power level?
- [ ] Changes with squelch?
- [ ] Contains frequency (BCD or binary)?
- [ ] Contains CTCSS/DCS codes?
- [ ] Contains signal strength (RSSI)?
- [ ] Contains battery voltage?
- [ ] Contains mode flags?
- [ ] Contains DMR data (CC, TS)?
- [ ] ASCII text present?
- [ ] Firmware version info?

## 🎓 Common Patterns

### Frequency Encoding
- BCD: `14 65 20` = 146.520 MHz
- Binary: `01 4C 5C 00` = 1,393,760 = 146.520 MHz * 10000

### Mode Flags (typical)
- Bit 0: FM/DMR (0=FM, 1=DMR)
- Bit 1: Power (0=Low, 1=High)
- Bit 2: Bandwidth (0=12.5kHz, 1=25kHz)
- Bit 3: Scan enable
- Bit 4-7: Other features

### CTCSS/DCS
- CTCSS: Index 01-50 (or 00=Off)
- DCS: Code directly (e.g., 023, 754)
- See Complete_Ctcss_Mapping.md

## ⚠️ Safety Reminders

**Before Each Session:**
- [ ] Radio backed up
- [ ] Radio in programming mode
- [ ] COM port correct (COM3)
- [ ] Ready to factory reset if needed

**During Testing:**
- ⚠️ Watch radio display for anomalies
- ⚠️ Stop if radio behaves unexpectedly  
- ⚠️ Test known command first (0x41 0000)
- ⚠️ Document everything

**After Testing:**
- [ ] Verify radio works normally
- [ ] Save investigation results
- [ ] Update documentation
- [ ] Commit findings to repo

## 📊 Success Metrics

After investigation, you should know:

1. ✅ **0x2E Function:** [What it reads/reports]
2. ✅ **0x2E Byte Map:** [What each byte means]  
3. ✅ **0x2D Function:** [What it measures]
4. ✅ **FFT Commands:** [How they affect 0x39]
5. ✅ **Confidence Level:** [High/Med/Low for each]

## 🔗 Related Files

**Investigation Tool:**
- `tests/investigate_commands.py`

**Documentation:**
- `docs/Command_Investigation_Guide.md` - Full guide
- `docs/Command_Investigation_Findings_Template.md` - Results template
- `docs/UART_Fuzzing_Investigation.md` - Fuzzing background
- `docs/Pmr171_Protocol.md` - Known commands

**Results:**
- `tests/fuzz_results/investigation_*.json` - Auto-saved results

## 💡 Pro Tips

1. **Copy-paste friendly:** Keep a text editor open to copy hex responses quickly

2. **Radio state notation:** Use shorthand like "CH2-DMR-H-S5" = Channel 2, DMR, High power, Squelch 5

3. **Diff tool:** Use online hex diff tool to compare responses

4. **Binary calc:** Keep calculator in programmer mode for hex/dec/bin

5. **Screenshot everything:** Capture radio display for each test

6. **Voice notes:** Record observations while testing (hands free!)

7. **Break frequency:** Take breaks every 30 min to stay sharp

## 🎯 Today's Mission

Focus on determining:

**Primary Goal:** What does 0x2E's 30-byte response contain?

**Secondary Goal:** What does 0x2D's 2-byte response represent?

**Bonus Goal:** Do 0x20-0x23 configure spectrum analyzer?

---

**Ready to investigate? Connect radio and run:**
```bash
python tests/investigate_commands.py --port COM3 --interactive
```

Then type `list` to see commands and start with:
```
>>> consistency 0x2E
```

Good luck! 🔬
