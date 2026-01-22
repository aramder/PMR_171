# PMR-171 Command Cross-Reference Analysis

**Date:** January 22, 2026  
**Source:** PMR171Manual2_1updated2026.pdf - Appendix 2: PMR-171 Control Protocol  
**Purpose:** Cross-reference fuzzing discoveries with official protocol documentation

## MAJOR DISCOVERY: Commands 0x2D and 0x2E Are Documented!

The manual's Appendix 2 contains the complete protocol specification, which explains several of our "unknown" commands!

---

## HIGH Priority Commands - IDENTIFIED

### 0x2D - Standing Wave/Meter Synchronization Command ✅ CONFIRMED

**Official Documentation (Page 36-37):**

**Command Name:** Standing wave meter, S meter, ALC meter, transmit power meter synchronization command

**Purpose:** Polling command for meter readings

**Request Format:**
```
0xA5 0xA5 0xA5 0xA5 [length] 0x2D [CRC_H] [CRC_L]
```

**Response Format:**
```
0xA5 0xA5 0xA5 0xA5 [length] 0x2D [TX_PWR/S-Meter] [SWR/AUD/ALC] [CRC_H] [CRC_L]
```

**Response Byte Structure (2 bytes payload):**

**Byte 1: TX Power or S-Meter**
- 0-34: S-Meter value (when BIT7 = 0, receiving)
- 0-34: Transmit Power value (when BIT7 = 1, transmitting)

**Byte 2: SWR/AUD/ALC (encoded in BIT7 and BIT6)**
- BIT7=0, BIT6=0 (00): SWR value (0-34)
- BIT7=0, BIT6=1 (01): AUD value (0-34) 
- BIT7=1, BIT6=0 (10): ALC value (0-34)

**Investigation Implications:**
- This is a **polling command** - controller sends it to request current meter readings
- Response varies based on TX/RX state and what meter is being displayed
- Values 0-34 map to meter deflection levels

---

### 0x2E - Parameter Synchronization Command ✅ CONFIRMED

**Official Documentation (Page 37):**

**Command Name:** Parameter synchronization command (timing polling implements synchronization)

**Purpose:** Returns comprehensive radio state and settings

**Request Format:**
```
0xA5 0xA5 0xA5 0xA5 [length] 0x2E [Data Packet] [CRC_H] [CRC_L]
```

**Response Format (30 bytes payload!):**
```
0xA5 0xA5 0xA5 0xA5 [length] 0x2E 
[SVOL] [HVOL] [MIC] [CMP] [BAS] [TRB] [RFG] [IFG] [SQL] [AGC] 
[AMP] [NR] [NB] [PEAK] [SPAN] [REF] [SPEED] [T-CTSS] [R-CTSS] 
[L-VOICE] [L-TIME] [KEY_MODE] [TX_RX] [TRAINING] [STF] [STG] 
[KEY_SPEED] [DECODE] [THRESHOLD] [data_format]
[CRC_H] [CRC_L]
```

**30-Byte Payload Structure:**

| Byte | Parameter | Description | Value Range |
|------|-----------|-------------|-------------|
| 0 | SVOL | Speaker volume | 0-30 |
| 1 | HVOL | Headphone volume | 0-80 |
| 2 | MIC | Microphone gain | 0-100 |
| 3 | CMP | Compression ratio | 0-14 |
| 4 | BAS | Bass EQ | 0-40 |
| 5 | TRB | Treble EQ | 0-40 |
| 6 | RFG | RF Gain | 0-100 |
| 7 | IFG | IF Gain | 0-80 |
| 8 | SQL | Squelch level | 0-20 |
| 9 | AGC | Auto gain control speed | 0-5 |
| 10 | AMP | Pre-amplifier | 0=AMPA, 1=AMPB |
| 11 | NR | Noise Reduction | 0=off, 1=on |
| 12 | NB | Noise Blanker | 0=off, 1=on |
| 13 | PEAK | Peak threshold | 0-20 |
| 14 | SPAN | Spectrum bandwidth | 0-5 (48K/24K/12K/6K/3K/1.5K) |
| 15 | REF | Spectrum reference level | 1-20 |
| 16 | SPEED | Spectrum refresh rate | 1-30 |
| 17 | T-CTSS | Transmit CTCSS | See CTCSS table |
| 18 | R-CTSS | Receive CTCSS | See CTCSS table |
| 19 | L-VOICE | Preamble rate | Index value |
| 20 | L-TIME | Preamble duration | 50-300 |
| 21 | KEY_MODE | CW key type | 0=AUTO-L, 1=AUTO-R, 2=KEY |
| 22 | TX_RX | Send/receive conv time | 0-50 (×10) |
| 23 | TRAINING | CW practice mode | 0=off, 1=on |
| 24 | STF | CW side-tone frequency | 40-20 (×10) |
| 25 | STG | CW side-tone volume | 0-15 |
| 26 | KEY_SPEED | CW auto key speed | 5-48 WPM |
| 27 | DECODE | CW decode switch | 0=off, 1=on |
| 28 | THRESHOLD | CW decode threshold | 1-50 |
| 29 | data_format | USB data format | 0=USB, 1=SDR |

**Investigation Implications:**
- This is THE comprehensive status read command
- Returns ALL major radio settings in one packet
- Perfect for synchronizing external controller with radio state
- Should be used by control software for initial sync

---

## MEDIUM Priority Commands - PARTIALLY IDENTIFIED

### 0x20 - PEAK Threshold Setting ✅ CONFIRMED

**Official Documentation (Page 34):**

**Command Name:** PEAK Threshold setting command

**Request Format:**
```
0xA5 0xA5 0xA5 0xA5 [length] 0x20 [NR_Threshold] [CRC_H] [CRC_L]
```

**Parameter:** NR Threshold: 0-20, Step 1

**Note:** Manual shows command as 0x20 for PEAK, which conflicts with our fuzzing finding that it returns empty. This needs investigation.

### 0x21-0x23 - Sky Tuning and Spectrum Commands

Looking at the protocol documentation:

- **0x21:** Sky tuning setting command (Page 34)
  - Controls antenna tuner: 0=off, 1=on, 2=start tuning
  
- **0x22:** Spectrum bandwidth command (Page 34)
  - SPAN: 0-5 (48K, 24K, 12K, 6K, 3K, 1.5K)
  
- **0x23:** Spectral reference level command (Page 34)
  - REF: 1-20

**Investigation Note:** These commands may return empty acknowledgments but affect spectrum display behavior (0x39).

### 0x04 - Not Documented

Command 0x04 is NOT in the official protocol documentation. This remains truly unknown.

---

## LOW Priority Commands

### 0x00 - PTT Alias ✅ CONFIRMED

**Official Documentation (Page 29):**

**Command Name:** PTT command

**Command Code:** 0x07 (primary)

**Finding:** Our fuzzing shows 0x00 also triggers PTT response (0x07), suggesting it's an alias or shortcut command not officially documented.

### 0x03, 0x0C-0x10 - Various States

Checking documented commands in this range:

- **0x03:** Not documented
- **0x0C:** Shutdown command (Page 31)
  - 0=Power off, 1=Power on
  - May return empty response
  
- **0x0D-0x10:** AF menu commands (Page 31-32)
  - These are setting commands that may not return data
  - 0x0D: Speaker volume (0-30)
  - 0x0E: Headphone volume (0-80)
  - 0x0F: MIC gain (0-100)
  - 0x10: Compression ratio (0-14)

---

## Complete Protocol Command Map

From the manual, here are ALL documented commands:

| Command | Name | Function |
|---------|------|----------|
| 0x07 | PTT_CONTROL | PTT press/release |
| 0x09 | FREQ_SETTING | Set VFOA/VFOB frequency |
| 0x0A | MODE_SETTING | Set operating mode |
| 0x0B | STATUS_SYNC | Get comprehensive status (80+ bytes) |
| 0x0C | SHUTDOWN | Power on/off |
| 0x0D | SPEAKER_VOL | Speaker volume (0-30) |
| 0x0E | HEADPHONE_VOL | Headphone volume (0-80) |
| 0x0F | MIC_GAIN | Microphone gain (0-100) |
| 0x10 | COMPRESSION | Voice compression (0-14) |
| 0x11 | BASS_EQ | Bass equalization (0-40) |
| 0x12 | TREBLE_EQ | Treble equalization (0-40) |
| 0x13 | RF_GAIN | RF gain (0-100) |
| 0x14 | IF_GAIN | IF gain (0-80) |
| 0x15 | SQL | Squelch level (0-20) |
| 0x16 | AGC | Auto gain control (0-5) |
| 0x17 | AMP | Pre-amplifier (0-1) |
| 0x18 | FILTER | Digital filter selection |
| 0x19 | NR | Noise Reduction on/off |
| 0x1A | NB | Noise Blanker on/off |
| 0x1B | AB_FREQ | A/B frequency selection |
| 0x1C | SPLIT | Split frequency on/off |
| 0x1D | BAND | Band selection |
| 0x1E | NR_THRESHOLD | NR threshold (1-200) |
| 0x1F | NB_THRESHOLD | NB threshold (0-15) |
| 0x20 | PEAK_THRESHOLD | PEAK threshold (0-20) |
| 0x21 | SKY_TUNE | Antenna tuner control |
| 0x22 | SPECTRUM_BW | Spectrum bandwidth (0-5) |
| 0x23 | SPECTRUM_REF | Spectrum reference level (1-20) |
| 0x24 | SPECTRUM_SPEED | Spectrum refresh rate (1-30) |
| 0x25 | SPECTRUM_MODE | Spectrum display mode |
| 0x26 | CTCSS | Analog sub-tones |
| 0x27 | EQUIPMENT_TYPE | Device type recognition |
| 0x28 | POWER_CLASS | Power level (0-100) |
| 0x29 | RIT | Receive frequency offset (0-120) |
| 0x2A | XIT | Transmit frequency offset (0-120) |
| 0x2B | L_TIME | Preamble duration (50-300) |
| 0x2C | POWER_LEVEL | High/Low power switch |
| **0x2D** | **METER_SYNC** | **Standing wave/S/ALC meter** ⭐ |
| **0x2E** | **PARAM_SYNC** | **30-byte parameter sync** ⭐ |
| 0x2F | KEY_TYPE | CW key type |
| 0x30 | SIDETONE_VOL | Side-tone volume |
| 0x31 | SIDETONE_FREQ | Side-tone frequency |
| 0x32 | TX_RX_TIME | TX/RX conversion time |
| 0x33 | USB_FORMAT | USB data format |
| 0x34 | TRAINING | CW practice mode |
| 0x35 | KEY_SPEED | CW key speed (5-48) |
| 0x36 | CW_DECODE | CW decode on/off |
| 0x37 | CW_THRESHOLD | CW decode threshold (1-50) |
| 0x38 | MESH | MESH telemetry (LORA) |
| 0x39 | SPECTRUM_DATA | Spectrum data (80 or 256 bytes) |

---

## Investigation Action Items

### Updated Command Priorities

**✅ SOLVED - HIGH Priority:**
1. **0x2E** - Parameter synchronization (30 bytes) - **FULLY DOCUMENTED**
2. **0x2D** - Meter synchronization (2 bytes) - **FULLY DOCUMENTED**

**🔍 NEEDS VERIFICATION - MEDIUM Priority:**
3. **0x20** - PEAK threshold (manual says it takes parameter, but fuzzing shows empty response)
4. **0x21** - Sky tune control (should return status?)
5. **0x22** - Spectrum bandwidth (should return status?)
6. **0x23** - Spectrum reference (should return status?)
7. **0x04** - NOT DOCUMENTED - truly unknown

**📝 UNDERSTOOD - LOW Priority:**
8. **0x00** - PTT alias (undocumented but understood)
9. **0x03** - NOT DOCUMENTED
10. **0x0C-0x10** - Setting commands (may have empty responses)

---

## Investigation Testing Plan

### Phase 1: Verify Documented Commands (0x2D, 0x2E)

Test **0x2D - Meter Sync:**
```
1. Send empty 0x2D request
2. Expect 2-byte response
3. Parse byte 1: Check BIT7 for TX/RX state
4. Parse byte 2: Check BIT7-BIT6 for meter type
5. Test during RX and TX to see value changes
6. Correlate with radio display meters
```

Test **0x2E - Parameter Sync:**
```
1. Send empty 0x2E request
2. Expect 30-byte response
3. Parse all 30 bytes according to manual structure
4. Change radio settings one by one
5. Read 0x2E after each change
6. Verify correct byte changes
7. Create complete byte map
```

### Phase 2: Verify Spectrum Commands (0x20-0x23)

```
1. Send 0x39 to get baseline spectrum
2. Send 0x20 with different PEAK values
3. Send 0x39 again - did spectrum change?
4. Repeat for 0x21, 0x22, 0x23
5. Determine if they're write-only or return status
```

### Phase 3: Investigate Unknown 0x04

```
1. Test in different modes (FM, SSB, CW, DMR)
2. Test in different states (TX, RX, idle)
3. Test with different payloads
4. Look for patterns in variable response
```

---

## Key Insights from Manual

### CRC Verification

The manual provides the exact CRC algorithm (Appendix 2-1, Page 39):
- **CRC Mode:** CRC16/CCITT-FALSE
- **Initial Value:** 0xFFFF
- **Polynomial:** 0x1021
- C code implementation provided

### Packet Structure

```
[Header: 0xA5 0xA5 0xA5 0xA5] 
[Length: 1 byte]
[Command: 1 byte]
[Data: Variable]
[CRC_H: 1 byte]
[CRC_L: 1 byte]
```

### Status Synchronization (0x0B)

Command 0x0B returns even MORE data than 0x2E (80+ bytes):
- TX/RX state
- Mode for VFOA and VFOB
- Frequencies
- A/B selection
- NR/NB status
- RIT/XIT values
- Filter bandwidth
- Spectrum settings
- Voltage
- UTC time
- Status bar flags
- Meter values

**This is the MASTER status command for complete synchronization!**

---

## Recommendations

1. **Update `investigate_commands.py`** to include manual documentation for 0x2D and 0x2E

2. **Add 0x0B testing** - This might be even more useful than 0x2E for comprehensive status

3. **Update protocol documentation** with complete command reference from manual

4. **Create parser functions** for 0x2D (2 bytes) and 0x2E (30 bytes) responses

5. **Add CRC verification** using the algorithm from the manual

6. **Test spectrum commands** to determine if they're write-only or return status

7. **Document 0x04** as truly unknown - not in official protocol

---

## Conclusion

**Major Success:** Commands 0x2D and 0x2E are fully documented in the manual!

- **0x2D** is for reading meters (SWR, S-meter, ALC, power)
- **0x2E** is for reading ALL radio parameters (30 bytes)
- **0x0B** is the even bigger brother (80+ bytes comprehensive status)

The fuzzing exercise successfully rediscovered official protocol commands that weren't previously documented in our project. The manual provides complete specifications for implementation.

**Next Step:** Implement parsers for these commands and integrate into the PMR-171 library for full radio control functionality.
