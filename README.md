# Radio Configuration Converter

A Python tool for converting various radio configuration formats to Guohetec PMR-171 JSON format and other formats.

## Features

- **Multiple Format Support**: 
  - ✅ CHIRP .img binary files (Baofeng UV-5R, UV-82, UV-32, etc.)
  - 🚧 Anytone .rdt files (planned)
  - 🚧 Motorola .ctb/.xctb files (planned)
  - 🚧 CSV import/export (planned)

- **Smart Channel Management**:
  - Automatic duplicate detection and removal
  - Multi-file merging with sequential renumbering
  - Frequency validation (VHF/UHF amateur bands)
  - CHIRP metadata filtering

- **GUI Tools**:
  - Interactive channel table viewer
  - Double-click for detailed channel information
  - Scrollable, sortable interface

- **Data Quality**:
  - Strict frequency validation
  - Corrupted channel detection
  - Unicode-safe name handling
  - DMR ID configuration

## Installation

```bash
# Clone the repository
cd CodeplugConverter

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in development mode
pip install -e .
```

## Quick Start

### Convert CHIRP Files

```bash
# Convert multiple CHIRP .img files
python -m codeplug_converter convert file1.img file2.img -o output.json

# Or use default files (backwards compatible)
cd Codeplugs/Guohetec
python -m codeplug_converter
```

### View Channel Data

```bash
# View a JSON file in table format
python -m codeplug_converter view output.json

# Or use old syntax (backwards compatible)
python -m codeplug_converter --view output.json
```

### Python API

```python
from codeplug_converter import ChirpParser, PMR171Writer
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

## Project Structure

```
CodeplugConverter/
├── codeplug_converter/          # Main package
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # CLI entry point
│   ├── parsers/             # File format parsers
│   │   ├── base_parser.py   # Abstract parser interface
│   │   └── chirp_parser.py  # CHIRP .img parser
│   ├── writers/             # Output format writers
│   │   └── pmr171_writer.py # PMR-171 JSON writer
│   ├── gui/                 # GUI components
│   │   └── table_viewer.py  # Channel table viewer
│   └── utils/               # Utilities
│       ├── frequency.py     # Frequency conversion
│       └── validation.py    # Data validation
├── tests/                   # Test suite
├── examples/                # Example files
├── docs/                    # Documentation
├── setup.py                 # Package setup
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Configuration

### DMR ID

Set your DMR ID in the writer:

```python
writer = PMR171Writer(dmr_id=YOUR_DMR_ID)
```

Or modify the default in `codeplug_converter/writers/pmr171_writer.py`:

```python
DMR_ID = 3107683  # Change to your DMR ID
```

### Mode Mappings

The tool supports all PMR-171 modes:
- 0: USB (Upper Sideband)
- 1: LSB (Lower Sideband)
- 2: CWR (CW Reverse)
- 3: CWL (CW Lower)
- 4: AM (Amplitude Modulation)
- 5: WFM (Wide FM)
- 6: NFM (Narrow FM) - default for FM
- 7: DIGI (Generic Digital)
- 8: PKT (Packet)
- 9: DMR (Digital Mobile Radio)

## Development Roadmap

### Phase 1: CHIRP Support ✅
- [x] CHIRP .img binary parser
- [x] PMR-171 JSON output
- [x] Multi-file consolidation
- [x] Duplicate detection
- [x] Table viewer GUI
- [x] CHIRP metadata filtering
- [x] Frequency validation

### Phase 2: Additional Formats 🚧
- [ ] Anytone .rdt parser (D878UV II)
- [ ] Motorola .ctb/.xctb parser (XPR series)
- [ ] Motorola .cpg parser (XTS series)
- [ ] CSV import/export (CHIRP-compatible)

### Phase 3: Enhanced GUI 🚧
- [ ] File browser/open dialogs
- [ ] Inline channel editing
- [ ] Bulk operations (frequency offset, mode change)
- [ ] Search/filter/sort functionality

### Phase 4: UART Programming 🚧
- [ ] Serial interface (pyserial)
- [ ] PMR-171 protocol reverse engineering
- [ ] Read/write codeplug from radio

### Phase 5: Advanced Features 🚧
- [ ] Repeater database integration
- [ ] Cross-format conversion
- [ ] Channel import from online databases
- [ ] Backup/restore functionality

### Phase 6: Distribution 🚧
- [ ] Standalone executable (PyInstaller)
- [ ] Auto-update system
- [ ] User documentation
- [ ] Video tutorials

## Testing

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_chirp_parser.py

# With coverage
pytest --cov=codeplug_converter
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Known Issues

- CHIRP embeds metadata as fake channels at end of file (automatically filtered)
- Some UV-5R/UV-82 files may contain corrupted channels (automatically filtered)
- Unicode characters in channel names may not display correctly in Windows terminal

## TODO / Future Features

### GUI Enhancements
- [ ] **Channel renumbering**: Add +/- buttons to allow users to change channel numbers and automatically re-sort the channel list
- [ ] **Bulk operations**: Select multiple channels for batch editing (delete, move, copy)
- [ ] **Undo/Redo**: Implement edit history for reverting changes
- [ ] **Channel zones/groups**: Organize channels into user-defined groups
- [ ] **Import/Export presets**: Save and load channel configurations

### Format Support
- [ ] **Anytone .rdt**: Read/write Anytone codeplug format
- [ ] **Motorola .ctb/.xctb**: MOTOTRBO CPS format support
- [ ] **CSV**: Generic CSV import/export with field mapping
- [ ] **CHIRP CSV**: Direct import from CHIRP CSV exports

### Features
- [ ] **Frequency calculator**: Repeater offset calculator and tone lookup
- [ ] **Channel validation**: Warn about out-of-band frequencies, invalid tones
- [ ] **Auto-programming**: Generate channels from repeater databases
- [ ] **Backup/restore**: Save previous versions before changes

## License

MIT License - see LICENSE file for details

## Credits

- CHIRP format documentation: https://chirp.danplanet.com/
- PMR-171 specifications: Reverse engineered
- Developed by: Aram Dermenjyan

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
