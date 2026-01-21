# PMR-171 CPS (Customer Programming Software)

[![AI Written](https://img.shields.io/badge/Code-100%25%20AI%20Written-blue)](#ai-development)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Polyform%20NC-orange.svg)](LICENSE)

---

## Project Goals

This repository serves three purposes:

1. **Reverse Engineering** — Document the undocumented UART programming protocol of the Guohetec PMR-171 handheld radio, including packet structure, command codes, checksum algorithms, and CTCSS tone encoding.

2. **Customer Programming Software (CPS)** — Develop an open-source alternative to the manufacturer's proprietary programming software, providing a professional GUI for channel programming with direct radio read/write capability.

3. **AI-Assisted Development Experiment** — Demonstrate the use of AI tools for hardware reverse engineering tasks, with 100% of the code, tests, and documentation written by AI.

---

## 🤖 AI-Assisted Hardware Reverse Engineering

**This entire repository—every line of code, test, and documentation—was written by AI.** 

> *"A human has not typed a single word contained in this repository, well aside from this quote."*

This project demonstrates the powerful capability of AI tools for hardware reverse engineering tasks.

### Why AI for Reverse Engineering?

Reverse engineering involves pattern matching, protocol analysis, and systematic testing—tasks where AI excels:

- **Pattern Recognition**: Identifying byte sequences in UART captures
- **Protocol Decoding**: Mapping command structures and checksums
- **Test Generation**: Creating comprehensive validation suites
- **Documentation**: Producing detailed technical reports

While these are relatively straightforward engineering tasks individually, they require significant time and attention to detail. AI dramatically accelerates this process, making hardware reverse engineering accessible and efficient.

---

## 📻 What is the PMR-171 CPS?

PMR-171 CPS is a **Customer Programming Software** for the Guohetec PMR-171. It provides:

### Core CPS Features

| Feature | Status | Description |
|---------|--------|-------------|
| **GUI Editor** | ✅ Complete | Professional channel editor with Motorola ASTRO 25 styling |
| **UART Programming** | ✅ Complete | Direct read/write to radio without manufacturer software |
| **CTCSS Tones** | ✅ Complete | All 50 standard tones mapped and validated |
| **Multi-Mode** | ✅ Complete | NFM, WFM, AM, USB, LSB, CW, DMR support |
| **CSV Import/Export** | ✅ Complete | Import/export for spreadsheet analysis |
| **DCS Tones** | ⏸️ Pending | Awaiting radio firmware support |

### GUI Capabilities

- **Channel Table View**: Sortable, filterable list with column selection
- **Inline Editing**: Edit channel name, frequency, mode, tones directly
- **Bulk Operations**: Multi-select, delete, duplicate, move channels
- **Undo/Redo**: Full edit history with Ctrl+Z/Ctrl+Y
- **Validation**: Warnings for out-of-band frequencies and invalid settings
- **DMR Support**: Color code, timeslot, and DMR ID configuration

### Direct Radio Programming

```bash
# Launch the CPS GUI
python -m pmr_171_cps

# Or open an existing file
python -m pmr_171_cps view output.json
```

From the GUI:
- **Read from Radio**: Click the `📻➡ Read` toolbar button (or Ctrl+R)
- **Write to Radio**: Click the `📻⬅ Write` toolbar button (or Ctrl+W)
- **COM Port Selection**: Use arrow keys to navigate, Enter to connect

**Connection Parameters** (discovered through reverse engineering):
- Baud: 115200, 8N1
- DTR: HIGH (critical!)
- RTS: HIGH (critical!)

---

## 📊 Validation & Testing

### CTCSS Tone Validation

Comprehensive testing validated the CTCSS implementation:

| Test | Channels | Result | Coverage |
|------|----------|--------|----------|
| Tone Mapping | 50 | ✅ Pass | All standard CTCSS tones |
| Split Tones | 25 | ✅ Pass | Different TX/RX |
| TX-Only | 5 | ✅ Pass | Tone only on transmit |
| RX-Only | 5 | ✅ Pass | Tone only on receive |
| **Total** | **85** | **100%** | Full coverage |

### UART Read/Write Verification

```bash
python tests/test_uart_read_write_verify.py --port COM3 --channels 5 --yes
```

**Results**: 5/5 channels passed on validation run
- All modes tested (NFM, AM, USB, LSB, WFM)
- Frequency accuracy verified (VHF + UHF)
- Channel names up to 11 characters
- Automatic backup and restoration

### Test Suite

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pmr171_format_validation.py -v

# Run UART verification (requires radio connected)
pytest tests/test_uart_read_write_verify.py -v
```

**24 automated tests** verify JSON format compatibility with factory software.

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/aramder/PMR_171.git
cd PMR_171

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install
pip install -e .
```

### Launch GUI

```bash
# Start with empty editor (read from radio or open file)
python -m pmr_171_cps

# Or open an existing JSON file
python -m pmr_171_cps view examples/Mode_Test.json
```

---

## 📁 Repository Structure

```
PMR_171_CPS/
├── pmr_171_cps/                  # Main application
│   ├── gui/                      # GUI components
│   │   └── table_viewer.py       # Main CPS interface
│   ├── radio/                    # Radio communication
│   │   └── pmr171_uart.py        # UART protocol driver
│   ├── parsers/                  # File format parsers
│   │   └── chirp_parser.py       # CHIRP .img parser
│   ├── writers/                  # Output writers
│   │   └── pmr171_writer.py      # PMR-171 JSON + CTCSS
│   └── utils/                    # Utilities
│       ├── frequency.py          # Frequency conversion
│       └── validation.py         # Data validation
│
├── tests/                        # Test suite
│   ├── test_uart_read_write_verify.py   # Hardware validation
│   ├── test_pmr171_format_validation.py # Format tests
│   └── test_configs/             # Test configurations
│       └── Results/              # UART capture files (.spm)
│
├── docs/                         # Documentation
│   ├── UART_Reverse_Engineering_Report.md  # Full RE report
│   ├── UART_Testing.md           # UART test documentation
│   ├── Complete_Ctcss_Mapping.md # CTCSS tone table
│   ├── Pmr171_Protocol.md        # Protocol specification
│   └── Factory_Json_Comparison.md # Format validation
│
├── examples/                     # Example files
│   └── Mode_Test.json            # Sample codeplug
│
└── TODO.md                       # Development roadmap
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [UART Reverse Engineering Report](docs/UART_Reverse_Engineering_Report.md) | Complete protocol discovery documentation |
| [UART Testing](docs/UART_Testing.md) | Hardware test procedures and results |
| [CTCSS Mapping](docs/Complete_Ctcss_Mapping.md) | Complete tone → yayin value table |
| [PMR-171 Protocol](docs/Pmr171_Protocol.md) | Protocol specification and field definitions |
| [TODO](TODO.md) | Development roadmap and session history |

---

## 🔧 Technical Discoveries

### Key Reverse Engineering Findings

1. **DTR/RTS Required**: Radio won't respond without DTR=HIGH and RTS=HIGH
2. **CTCSS Field Names Misleading**: `rxCtcss`/`txCtcss` are IGNORED; `emitYayin`/`receiveYayin` control tones
   - *"Yayin" (亚音) is Mandarin for "sub-tone" — a literal translation of CTCSS (sub-audible tone)*
3. **Non-Linear Tone Encoding**: CTCSS tones use proprietary yayin values (1-55 with gaps)
4. **Dual VFO Architecture**: Each channel has VFO A (RX) and VFO B (TX) frequencies
5. **Mode 9 = DMR**: Added in firmware update, not in original documentation

### Packet Structure

```
┌────────┬────────┬────────┬─────────────┬──────────┐
│ Header │ Length │ Cmd ID │ Payload     │ Checksum │
│ (2 B)  │ (1 B)  │ (1 B)  │ (Variable)  │ (1 B)    │
└────────┴────────┴────────┴─────────────┴──────────┘
```

---

## 🎯 Project Status

### Completed ✅
- [x] GUI channel editor with professional styling
- [x] Direct UART read/write to radio
- [x] Complete CTCSS tone mapping (50 tones)
- [x] CSV import/export
- [x] Multi-mode support (NFM, AM, USB, LSB, DMR)
- [x] 24 automated format validation tests
- [x] Hardware-in-the-loop testing
- [x] Progress indicators for radio operations (with Cancel button)

### Remaining
- [ ] DCS tone support (pending firmware)
- [ ] Channel zones/groups
- [ ] Repeater database integration

---

## 📜 License

Polyform Noncommercial License 1.0.0 - see [LICENSE](LICENSE)

Free for personal use, research, and education. Commercial use requires separate license.

---

## 👤 Credits

**Developed by**: Aram Dergevorkian  
**All code written by**: AI (100%)

---

## 🤝 Contributing

Contributions welcome! This project demonstrates AI-assisted development:

1. Fork the repository
2. Describe the feature/fix you want in natural language
3. Use AI tools to implement
4. Submit PR with AI-generated code

---

*Last Updated: January 20, 2026*
