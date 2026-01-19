# Usage Guide

## Installation

### From Source

```bash
cd PMR_171_CPS
pip install -e .
```

This installs the package in "editable" mode, meaning changes to the source code will immediately affect the installed package.

### Development Installation

```bash
cd PMR_171_CPS
pip install -e ".[dev]"
```

This includes development dependencies like pytest.

## Command Line Usage

### Converting CHIRP Files

The simplest way to convert CHIRP .img files:

```bash
python -m pmr_171_cps convert file1.img file2.img -o output.json
```

Options:
- `-o, --output`: Specify output filename (default: output.json)
- `--no-dedupe`: Disable automatic duplicate removal

### Viewing Channel Data

View a PMR-171 JSON file in a table:

```bash
python -m pmr_171_cps view output.json
```

This opens an interactive GUI window with:
- Scrollable channel table
- Key channel information (frequency, mode, CTCSS, etc.)
- Double-click any row for full channel details

### Backwards Compatibility

Old command syntax still works:

```bash
# View command (old style)
python -m pmr_171_cps --view output.json

# Default conversion (old style)
cd Codeplugs/Guohetec
python -m pmr_171_cps
```

## Python API Usage

### Basic Conversion

```python
from pmr_171_cps import ChirpParser, PMR171Writer
from pathlib import Path

# Parse CHIRP file
parser = ChirpParser()
channels = parser.parse(Path("radio.img"))

# Convert to PMR-171 format
writer = PMR171Writer(dmr_id=3107683)
pmr_channels = writer.channels_from_parsed(channels)

# Save to JSON
writer.write(pmr_channels, Path("output.json"))
```

### Advanced: Manual Channel Creation

```python
from pmr_171_cps import PMR171Writer

writer = PMR171Writer(dmr_id=3107683)

# Create a simplex FM channel
channel = writer.create_channel(
    index=0,
    name="Local Rpt",
    rx_freq=146.94,
    tx_freq=146.34,  # Repeater offset
    mode='FM',
    rx_ctcss=1000,   # 100.0 Hz (stored as 1/10 Hz)
    tx_ctcss=1000
)

# Create a DMR channel
dmr_channel = writer.create_channel(
    index=1,
    name="DMR TG 91",
    rx_freq=446.00,
    mode='DMR',
    is_digital=True,
    callId1=0, callId2=0, callId3=0, callId4=91,  # TG 91
    ownId1=0x2F, ownId2=0x6C, ownId3=0x03, ownId4=0x00  # DMR ID 3107683
)

# Save channels
channels = {"0": channel, "1": dmr_channel}
writer.write(channels, Path("custom.json"))
```

### Using the GUI Programmatically

```python
from pmr_171_cps import view_channel_file
from pathlib import Path

# Open channel viewer
view_channel_file(Path("output.json"), title="My Channels")
```

### Frequency Utilities

```python
from pmr_171_cps import frequency_to_bytes, bytes_to_frequency

# Convert frequency to PMR-171 format
freq_bytes = frequency_to_bytes(146.52)  # Returns (8, 184, 81, 64)

# Convert back
freq_mhz = bytes_to_frequency(freq_bytes)  # Returns 146.52
```

### Validation Utilities

```python
from pmr_171_cps.utils import is_valid_frequency

# Check if frequency is valid
if is_valid_frequency(146.52, strict=True):
    print("Valid VHF frequency")

# Relaxed validation (allows airband, commercial, etc.)
if is_valid_frequency(118.0, strict=False):
    print("Valid airband frequency")
```

## File Format Details

### PMR-171 JSON Format

Each channel has 40+ fields:

```json
{
  "0": {
    "channelName": "Local Rpt\u0000",
    "channelLow": 0,
    "channelHigh": 0,
    "vfoaFrequency1": 8,    // RX frequency (big-endian)
    "vfoaFrequency2": 184,
    "vfoaFrequency3": 81,
    "vfoaFrequency4": 64,
    "vfobFrequency1": 8,    // TX frequency
    "vfobFrequency2": 180,
    "vfobFrequency3": 183,
    "vfobFrequency4": 224,
    "vfoaMode": 6,          // NFM
    "vfobMode": 6,
    "chType": 0,            // 0=analog, 1=digital
    "rxCtcss": 1000,        // 100.0 Hz (stored * 10)
    "txCtcss": 1000,
    "txCc": 2,              // Color code
    // ... many more fields
  }
}
```

### CHIRP .img Format

Binary format, 32 bytes per channel:
- Bytes 0-3: RX frequency (BCD, little-endian, freq*10)
- Bytes 4-7: TX frequency (BCD, little-endian, freq*10)
- Bytes 8-15: Tone/squelch settings
- Bytes 16-31: Channel name (ASCII, 0xFF padded)

## Common Tasks

### Merge Multiple Radios

```python
from pathlib import Path
from pmr_171_cps.__main__ import convert_chirp_files

files = [
    Path("radio1.img"),
    Path("radio2.img"),
    Path("radio3.img")
]

convert_chirp_files(files, Path("merged.json"), deduplicate=True)
```

### Extract Specific Frequencies

```python
import json
from pathlib import Path
from pmr_171_cps.utils import bytes_to_frequency

# Load channels
with open("output.json") as f:
    channels = json.load(f)

# Filter VHF channels only
vhf_channels = {}
for ch_id, ch in channels.items():
    rx_freq = bytes_to_frequency((
        ch['vfoaFrequency1'],
        ch['vfoaFrequency2'],
        ch['vfoaFrequency3'],
        ch['vfoaFrequency4']
    ))
    
    if 136 <= rx_freq <= 174:  # VHF band
        vhf_channels[ch_id] = ch

# Save VHF-only channels
with open("vhf_only.json", "w") as f:
    json.dump(vhf_channels, f, indent=2)
```

### Change All Channels to a Different Mode

```python
import json

with open("output.json") as f:
    channels = json.load(f)

# Change all to WFM
for ch in channels.values():
    ch['vfoaMode'] = 5  # WFM
    ch['vfobMode'] = 5

with open("wfm_channels.json", "w") as f:
    json.dump(channels, f, indent=2)
```

## Troubleshooting

### No Channels Parsed

If parser finds 0 valid channels:
1. Check file is a CHIRP .img file (not .csv)
2. Verify frequencies are in valid ranges (136-174 MHz VHF, 400-520 MHz UHF)
3. Try with `strict_validation=False` in parser

### Duplicate Channels

Duplicates are automatically detected based on:
- Channel name
- RX frequency

Use `--no-dedupe` to keep all channels.

### Unicode Errors

Windows terminal may not display Unicode correctly. The tool uses ASCII-safe fallbacks internally, but JSON files may contain Unicode characters.

## Next Steps

- Read [ChirpFormatAnalysis.md](ChirpFormatAnalysis.md) for technical details
- See [examples/](../examples/) for sample files
- Check [README.md](../README.md) for roadmap and features
