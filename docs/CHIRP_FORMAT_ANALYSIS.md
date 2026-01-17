# CHIRP .img File Format Analysis

## Investigation Summary

**Date**: January 16, 2026  
**Files Analyzed**: My UV-5R.img, My UV-82.img  
**Discovery**: CHIRP embeds metadata as fake channels at the end of .img files

## The Mystery

Initially appeared to be ~95 corrupted channels with:
- Garbled names (e.g., "eyJtZW1fZXh", "tbWVudCI6ICJ", "9LCAicmNsYXN")
- Invalid frequencies (363 MHz, 457 MHz, 534 MHz for VHF radios)
- Suspicious patterns (base64-like character sequences)

## The Discovery

These are **NOT corrupted channels** - they are **CHIRP metadata stored as channel entries**!

### Evidence

**Channel 202 Raw Data:**
```
Hex: 39 31 36 36 00 00 00 00  00 ff 63 68 69 72 70 ee
     69 6d 67 00 01 65 79 4a  74 5a 57 31 66 5a 58 68
     
ASCII: "9166....chirp.img.eyJtZW1fZXh"
```

**Decoded Metadata (base64 → JSON):**
```json
{
  "mem_extra": {
    "0067_comment": "Ops Rptr",
    "0068_comment": "Ops Dir",
    "0069_comment": "Maint",
    "0070_comment": "Util Auto Equip",
    "0071_comment": "Adm Sec Rptr",
    "0072_comment": "Adm Sec Dir"
  },
  "rclass": "DynamicRadioAlias",
  "vendor": "Baofeng",
  "model": "UV-5R",
  "variant": "",
  "chirp_version": "next-20231003"
}
```

### Metadata Markers

CHIRP metadata channels contain:
- **Signature bytes**: `chirp` string embedded in channel data
- **File marker**: `img\x00` sequence
- **Base64 encoding**: Channel names are base64-encoded JSON fragments
- **High channel numbers**: Typically stored at positions 195-220+

### File Structure

```
Offset 0x0000: Channel 0 (real data)
Offset 0x0020: Channel 1 (real data)
...
Offset ~0x1900: Real channels end (~100-120 channels)
...
Offset ~0x1900+: CHIRP metadata starts
    - Contains base64-encoded JSON
    - Stores file version, radio model, comments
    - Invalid as actual radio channels
```

## Parser Updates

### Detection Logic

```python
# Skip CHIRP metadata channels
if b'chirp' in chunk or b'img\x00' in chunk:
    continue  # CHIRP metadata marker

# Skip base64-encoded metadata
if all characters in set('A-Za-z0-9+/='):
    continue  # Base64 metadata
```

### Results

**Before Filtering:**
- UV-32.img: 60 channels (clean file, no metadata)
- UV-5R.img: 56 channels → **16 real channels** (40 were metadata)
- UV-82.img: 39 channels → **9 real channels** (30 were metadata)

**After Filtering:**
- Total: 71 valid channels (vs 155 before)
- Removed: 84 metadata/invalid entries

## Remaining Questions

Some low-frequency channels still appear (4-62 MHz range):
- **Possible HF amateur bands** (legitimate but unusual)
- **BCD decoding artifacts** (needs further investigation)
- **Intentional test/memory channels** (user-created)

Examples:
- Channel 46: "DP5FP5F" - RX: 4.2004 MHz
- Channel 34: "PbwEPbwE" - RX: 31.1403 MHz
- Channel 38: "DPhEPhE" - RX: 81.3108 MHz

These may need additional validation or manual review.

## Lessons Learned

1. **Don't assume corruption** - proprietary formats use creative storage
2. **Look for patterns** - base64 names are a red flag
3. **Check for magic bytes** - `chirp`, `img` markers reveal purpose
4. **Examine raw binary** - hex dumps reveal hidden structure
5. **Decode everything** - base64 often hides metadata

## Recommendations

### For Parser Enhancement
- [ ] Add explicit CHIRP metadata section detection
- [ ] Parse and extract metadata for informational display
- [ ] Create separate handling for different file versions
- [ ] Log metadata information (CHIRP version, radio model)
- [ ] Better handling of mixed valid/metadata channels

### For User Documentation
- [ ] Document CHIRP file format quirks
- [ ] Warn about expected channel count differences
- [ ] Explain metadata storage mechanism
- [ ] Provide channel validation tips

## Technical Notes

**CHIRP Version**: next-20231003 (development build)  
**File Format**: UV-5R .img binary format  
**Channel Size**: 32 bytes per entry  
**Metadata Encoding**: Base64-encoded JSON fragments across multiple 32-byte blocks  
**Detection Reliability**: High (signatures are consistent)

## Future Work

- Document complete CHIRP .img format specification
- Create metadata extraction utility
- Support other CHIRP formats (.csv, .chirp archives)
- Validate low-frequency channels with radio testing
- Add option to preserve/export metadata
