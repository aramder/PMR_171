# Q900 vs PMR-171 Protocol Comparison

**Date:** January 22, 2026  
**Purpose:** Compare Q900 manual with PMR-171 to identify any new command information

---

## Executive Summary

The Q900 and PMR-171 are **SISTER RADIOS** from the same manufacturer (Chongqing Guohe Electronic Technology Co., Ltd) using **IDENTICAL UART protocols**.

**Key Finding:** The Q900 manual provides NO new information about commands 0x2D or 0x2E beyond what's in the PMR-171 manual. Both radios share the exact same protocol documentation.

---

## Radio Comparison

### Manufacturer
**Same:** Chongqing Guohe Electronic Technology Co., Ltd.  
- Website: www.guohedz.com
- Both use same contact info and location

### Radio Specifications

| Feature | PMR-171 | Q900 |
|---------|---------|------|
| **Type** | Full-mode SDR | Full-mode SDR |
| **RX Range** | 100kHz - 2GHz | 300kHz - 1.6GHz |
| **TX Bands** | 160m - 70cm | 160m - 70cm |
| **Modes** | FT8, USB, LSB, CW, AM, FM, RTTY, DMR | FT8, USB, LSB, CW, AM, FM, RTTY, DMR |
| **Power** | 9-18VDC | 5-32VDC |
| **Battery** | 5AH external | 4.9AH internal |
| **Weight** | ≤2kg | ≤2kg |
| **Tuner** | 160-4m | 6-160m |
| **TCXO** | ±0.5ppm | ±0.5ppm |

**Conclusion:** These are variant models of the same radio platform.

---

## Protocol Comparison

### Packet Structure
**IDENTICAL in both manuals:**

```
0xA5 0xA5 0xA5 0xA5 [Packet Length] [Command Type] [DATA] [CRC HIGH] [CRC LOW]
```

### CRC Algorithm
**IDENTICAL:** CRC16/CCITT-FALSE
- Initial value: 0xFFFF
- Polynomial: 0x1021
- Same C code implementation in both manuals

### Command Set
**IDENTICAL:** Both manuals document the exact same commands (0x07 - 0x39)

---

## Commands 0x2D and 0x2E - EXACT MATCH

### Command 0x2D - Meter Synchronization

**PMR-171 Manual (Page 36-37):**
```
39. Standing wave meter, S meter, ALC meter, transmit power meter synchronization command
```

**Q900 Manual (Page 50):**
```
39. Synchronous command of standing wave meter, S meter, ALC meter and transmit power meter
```

**Response Format (Both Identical):**
- Byte 1: TX Power / S-Meter (BIT7 indicates TX/RX)
- Byte 2: SWR/AUD/ALC (BIT7-BIT6 encode meter type)

**NO ADDITIONAL INFORMATION in Q900 manual**

### Command 0x2E - Parameter Synchronization

**PMR-171 Manual (Page 37):**
```
40. Parameter synchronization command (timing polling implements synchronization)
Returns 30 bytes: SVOL, HVOL, MIC, CMP, BAS, TRB, RFG, IFG, SQL, AGC, AMP, NR, NB, PEAK, SPAN, REF, SPEED, T-CTSS, R-CTSS, L-VOICE, L-TIME, KEY_MODE, TX_RX, TRAINING, STF, STG, KEY_SPEED, DECODE, THRESHOLD, data_format
```

**Q900 Manual (Page 51):**
```
40. Parameter synchronization command (timing polling for synchronization)
Returns 30 bytes: [Same exact list]
```

**NO ADDITIONAL INFORMATION in Q900 manual**

---

## What's Different (Minor)

### Hardware Variations

1. **Power Supply Range**
   - PMR-171: 9-18VDC
   - Q900: 5-32VDC (wider range)

2. **Battery Design**
   - PMR-171: External 5AH clip-on battery
   - Q900: Internal 4.9AH battery

3. **Antenna Tuner Range**
   - PMR-171: 160-4m bands
   - Q900: 6-160m bands

4. **Receive Range**
   - PMR-171: 100kHz - 2GHz (wider)
   - Q900: 300kHz - 1.6GHz

### Documentation Style

The Q900 manual has slightly better organization but contains NO new technical information about the protocol or commands.

---

## Critical Finding: Crash Issues Likely Affect Both

Since Q900 and PMR-171 use **identical protocols**, the crash issues we discovered with commands 0x2D and 0x2E would likely affect **BOTH radio models**.

### Evidence
1. Same manufacturer
2. Same firmware architecture
3. Same command structure
4. Same protocol version (V1.5)
5. Same CRC algorithm
6. Same command documentation

### Implication

⚠️ **WARNING:** If you have a Q900 radio, the same safety warnings apply:
- Commands 0x2D and 0x2E may cause crashes with rapid polling
- Use extreme caution with these commands
- Follow same safety protocols as documented for PMR-171

---

## Protocol Version Notes

Both manuals state: **"Q900/PMR-171 control protocol V1.5"**

This confirms they're using the same protocol revision.

### Change Notification (Both Identical)

Both manuals include the same protocol change note about swapping ALC/AUD definitions in command 0x2D response byte 2.

**Original:**
- BIT7=0, BIT6=1: ALC
- BIT7=1, BIT6=0: AUD

**After Change:**
- BIT7=0, BIT6=1: AUD
- BIT7=1, BIT6=0: ALC

---

## No New Command Information

After thorough review of the Q900 manual Appendix 2 (protocol section), there is:

❌ **NO new commands** beyond those in PMR-171  
❌ **NO additional details** about 0x2D or 0x2E behavior  
❌ **NO warnings** about crash issues  
❌ **NO rate limiting guidance**  
❌ **NO stability information**  
❌ **NO safe polling recommendations**  

The Q900 manual is essentially a copy of the PMR-171 protocol documentation with model-specific hardware differences noted in the hardware sections.

---

## Conclusions

### What We Learned
1. **Q900 = PMR-171 Protocol Twin** - Same protocol, different hardware variants
2. **No New Safety Info** - Q900 manual has same crash blind spots
3. **Crash Risk Universal** - Issues likely affect all radios in this family
4. **Manufacturer Awareness** - No warnings suggest manufacturer may not be aware of crash issues

### What This Means for Our Investigation

✅ **Our findings apply to both radio models**  
✅ **Documentation is consistent** (no conflicts to resolve)  
✅ **Crash reports should mention both models**  
✅ **Safety warnings apply to entire product line**  

### Recommendations

1. **Test Q900 if available** - Verify crash behavior is identical
2. **Report to manufacturer** - Include both PMR-171 and Q900 in bug report
3. **Update documentation** - Note that findings apply to both models
4. **Community awareness** - Warn users of both radio types

---

## Additional Observations

### Protocol Documentation Quality

Both manuals provide:
- ✅ Complete command reference
- ✅ Byte-level specifications
- ✅ CRC algorithm source code
- ✅ Data structure definitions
- ❌ NO timing constraints or rate limits
- ❌ NO buffer size limitations
- ❌ NO stability warnings
- ❌ NO firmware version dependencies

**Gap:** Neither manual addresses safe polling practices or system stability.

### Firmware Upgrade Process

Both radios use **identical upgrade procedures:**
- DFU mode via BAND + Power key
- Bootloader + Application architecture
- USB flash drive for firmware
- Same dfusedemo tool

This further confirms they're the same platform.

---

## Summary

**Answer to "Any new information?"**

**NO** - The Q900 manual provides zero additional information about commands 0x2D and 0x2E beyond what's in the PMR-171 manual. 

The protocols are **100% identical**, and therefore:
- Our crash findings apply to Q900
- Our safety warnings apply to Q900
- Our investigation methods work for Q900
- Our documentation is valid for both models

The Q900 is simply a hardware variant (internal battery, wider voltage range) of the same radio platform using the identical protocol.

---

## Files Referenced

📄 PMR171Manual2_1updated2026.pdf - Appendix 2 (Pages 29-41)  
📄 FullmodeSDRRadioQ900Usermanual2.pdf - Appendix 2 (Pages 40-57)  
📄 Our investigation documents (all applicable to both models)

**Status:** No new command information discovered. Both radios share identical crash risks.
