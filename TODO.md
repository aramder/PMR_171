# CodeplugConverter TODO List

This document tracks planned features, enhancements, and known issues for the CodeplugConverter project.

---

## High Priority

### CTCSS Tone Encoding - ✅ COMPLETE AND VALIDATED
- [x] **Discovered correct fields**: Testing revealed emitYayin/receiveYayin are the correct fields (Jan 2026)
  - Test 07: rxCtcss/txCtcss fields are IGNORED by radio (always reset to 255)
  - Test 08: emitYayin/receiveYayin values PRESERVED, confirming correct implementation
- [x] **Complete CTCSS mapping table**: ✅ ALL 50 standard tones mapped (Tests 05-10, Jan 2026)
  - All CTCSS tones from 67.0 Hz to 254.1 Hz successfully mapped
  - Non-linear yayin encoding discovered (values 1-55 with gaps)
  - Complete lookup tables in `codeplug_converter/writers/pmr171_writer.py`
- [x] **Validation**: ✅ Test 11 confirmed 100% accuracy (Jan 18, 2026)
  - 25 test channels verified (common, edge, split, TX-only, RX-only, no-tone)
  - All emitYayin and receiveYayin values match perfectly
  - Split tones, TX-only, RX-only all confirmed functional
- **Status**: ✅ **VALIDATED AND PRODUCTION READY**
- **Documentation**: See `docs/Complete_Ctcss_Mapping.md` and `D:/Radio/Guohetec/Testing/11_Validation_Results.md`

### DCS (Digital Coded Squelch) Encoding - PENDING
- [ ] **Build DCS mapping table**: Research required - 104+ codes to map (Est: 6-8 hours)
  - Configure each DCS code in manufacturer software (D023N, D023I, etc.)
  - Download from radio and record emitYayin/receiveYayin values
  - Build complete DCS code → yayin mapping table
  - Add DCS support to _tone_to_yayin()
- **Note**: DCS codes likely use yayin values 100+ based on reserved gaps in CTCSS range
- **Impact**: MEDIUM - CTCSS covers most amateur radio use cases; DCS needed for some repeaters

### JSON Format Validation & Factory Software Compatibility
- [x] **Comprehensive test suite**: 24 tests validating PMR-171 JSON format compatibility (Jan 2026)
- [x] **Cross-validate with factory software output**: ✅ VALIDATED - See docs/Factory_Json_Comparison.md (Jan 2026)
  - [x] Verified field value ranges match factory software - Perfect match!
  - [x] Frequency encoding validated - Mathematically correct big-endian Hz
  - [x] Field structure confirmed - All 40+ fields match factory format
  - [ ] Test with actual radio hardware to confirm loadability - **Hardware testing needed**
- [x] **Additional JSON field analysis**: ✅ COMPLETE (Jan 2026)
  - [x] callFormat values documented: 0=analog, 2=digital (chType=0 vs chType=1)
  - [x] callId/ownId patterns documented: Big-endian 32-bit DMR IDs for digital channels
  - [x] chType=1 requirements verified: Requires callFormat=2, non-zero DMR IDs
  - [x] Default field values confirmed: txCc=2, all others 0 (matches factory)
- [ ] **Minor enhancement identified**: Update callFormat=2 for digital channels (currently always 0)
  - Impact: Low priority (only affects DMR channels, may work anyway)
  - Files to update: codeplug_converter/writers/pmr171_writer.py
  - See docs/Factory_Json_Comparison.md for details

### Core Functionality
- [x] **Dual frequency architecture**: PMR-171 requires TWO frequencies per memory channel (VFO A and VFO B), but CHIRP only provides one. **Solution**: When importing from single-frequency sources (CHIRP), program the same frequency into both VFO A and VFO B (simplex operation). No intermediate format needed. (Jan 2026)

- [ ] **UART Serial Transaction Analysis**: Analyze captured programming data to reverse engineer the PMR-171 UART protocol
  - [x] **Captured data available**: UART transaction logs stored in `tests/test_configs/Results/`
    - `07_readback_uart_monitor.spm` - Eltima Serial Monitor capture of Test 07 readback
    - `07_upload_uart_monitor.spm` - Upload operation for Test 07
    - `08_upload_uart_monitor.spm` - Upload operation for Test 08
    - `09_tone_pattern_test_manual_full_update_readback.spm` - Manual update readback
    - `09_upload_uart_monitor.spm` - Upload operation for Test 09
    - `10_complete_ctcss_mapping_test_readback.spm` - Test 10 readback
    - `11_complete_ctcss_validation_readback.spm` - Test 11 validation readback
    - `11_complete_ctcss_validation_readback_uploade.spm` - Test 11 upload (LARGEST - full transaction log)
  - [ ] **Phase 1: Extract and analyze capture format**
    - [ ] Parse Eltima .spm binary format to understand structure
    - [ ] Extract raw COM6 transaction data (TX/RX bytes with timestamps)
    - [ ] Convert to hex dumps for analysis (create analysis scripts in tests/test_configs/Results/)
    - [ ] Generate human-readable transcripts showing data flow
  - [ ] **Phase 2: Initial pattern recognition**
    - [ ] Compare 11_complete_ctcss_validation_readback_uploade.spm (upload) vs 11_complete_ctcss_validation_readback.spm (readback)
    - [ ] Identify repeating byte patterns (command headers, packet delimiters)
    - [ ] Look for ASCII strings (model name, version info)
    - [ ] Find correlation between known channel data and transmitted bytes
    - [ ] Map out transaction sequence (init → commands → data → verify)
  - [ ] **Phase 3: Decode packet structure**
    - [ ] Identify packet boundaries (start bytes, length fields, end bytes)
    - [ ] Extract suspected command codes from packet headers
    - [ ] Correlate CTCSS tone values (67.0Hz=0x01, 123.0Hz=0x03, etc.) with transmitted bytes
    - [ ] Find memory addresses or channel selectors
    - [ ] Identify data payload sections
  - [ ] **Phase 4: Checksum/CRC analysis**
    - [ ] Extract suspected checksum bytes from end of packets
    - [ ] Test common algorithms: CRC-16-CCITT, CRC-16-XMODEM, CRC-32, simple sum, XOR
    - [ ] Use online CRC calculators to test hypotheses
    - [ ] Implement validated checksum in Python
  - [ ] **Phase 5: Build protocol decoder**
    - [ ] Create `analyze_uart_capture.py` script in tests/test_configs/Results/
    - [ ] Parse .spm files and extract raw bytes
    - [ ] Implement packet parser based on discovered structure
    - [ ] Annotate packets with decoded information (command type, address, data, checksum)
    - [ ] Generate protocol documentation with examples
  - [ ] **Catalog capture files**: Document what each capture represents (already partially done via filenames)
    - [ ] Determine which are full codeplug operations vs partial updates
    - [ ] Identify read vs write transactions
  - [ ] **Identify communication parameters**:
    - [ ] Determine baud rate from capture timing
    - [ ] Identify data bits, parity, stop bits
    - [ ] Check for flow control signals
  - [ ] **Analyze packet structure**:
    - [ ] Identify packet start/sync patterns (header bytes)
    - [ ] Map command codes (read, write, verify, identify, etc.)
    - [ ] Determine address/memory location format
    - [ ] Analyze data payload structure
    - [ ] Identify checksum/CRC algorithm and location
    - [ ] Find packet terminator/footer bytes
  - [ ] **Document command sequences**:
    - [ ] Map initialization/handshake sequence
    - [ ] Document radio identification request/response
    - [ ] Analyze full codeplug read sequence
    - [ ] Analyze full codeplug write sequence
    - [ ] Document verification commands
  - [ ] **Reverse engineer checksums**:
    - [ ] Extract checksum bytes from multiple packets
    - [ ] Test common algorithms (CRC-16, CRC-32, XOR, simple sum)
    - [ ] Identify CRC polynomial and parameters if applicable
    - [ ] Implement checksum calculation in Python
  - [ ] **Create protocol specification document**: Document findings in `docs/PMR171_UART_PROTOCOL.md`
  - [ ] **Build packet examples**: Create annotated hex dumps showing packet structure

- [ ] **Direct PMR-171 programming via UART**: Implement direct radio programming without needing manufacturer software
  - Research UART command protocol (check PMR-171 manual for documentation)
  - If undocumented, use UART adapter or logic analyzer to sniff programming transactions
  - Implement Python UART communication (pyserial library)
  - Add "Program Radio" menu option with COM port selection
  - Include read/backup functionality to pull existing config from radio
  - Error handling and validation before writing to radio

### GUI Enhancements
- [x] **Channel renumbering**: Add +/- buttons to allow users to change channel numbers and automatically re-sort the channel list
- [x] **Add Channel button**: Toolbar with Motorola Astro CPS-style buttons for Add/Delete/Move/Duplicate channels

---

## Medium Priority

### Features
- [x] **CSV export**: Export channel data to CSV format for compatibility with other tools and spreadsheet analysis (Jan 2026)
- [x] **Bulk channel operations**: Select multiple channels for batch editing, deletion, or copying (Jan 2026)

### Format Support
- [ ] **Baofeng direct programming**: Read/write directly to Baofeng radios via USB cable (lower priority - may not be worth effort vs. using CHIRP)


---

## Low Priority / Nice to Have

- [x] **Undo/Redo**: Implement edit history for reverting changes (Jan 2026)
- [ ] **Channel zones/groups**: Organize channels into user-defined groups
- [ ] **Import/Export presets**: Save and load channel configurations
- [x] **Frequency calculator**: Repeater offset calculator and tone lookup
- [x] **Automatic frequency formatting**: Format frequency inputs to standard MHz precision (XXX.XXXXXX) with live tree view updates (Jan 2026)
- [x] **Channel validation**: Warn about out-of-band frequencies, invalid tones (Jan 2026)
- [ ] **Auto-programming**: Generate channels from repeater databases

---

## Known Issues / Bugs

### Status Bar Border (Visual Issue)
**Issue**: Status bar lacks a defined border at the top, creating a soft transition that doesn't look professional
- **Location**: Bottom of main window where status bar meets the tabbed content area
- **Impact**: Visual appearance - text overlaps with border area, no clear separation
- **Attempted Fixes** (Jan 17, 2026):
  - Added tk.Frame with bg='#AAAAAA' as 2px border line
  - Changed status bar from ttk.Frame to tk.Frame with bg='#F0F0F0'
  - Increased padding from (5, 2) to (10, 5)
  - Used tk.Label instead of ttk.Label for better control
- **Result**: Changes applied but no visible effect in the running application
- **Next Steps**: 
  - Investigate if ttk.Style is overriding the tk.Frame settings
  - Consider using ttk.Separator with different orientation/styling
  - May need platform-specific border implementation (Windows vs macOS vs Linux)
  - Test with different ttk themes to see if 'clam' theme is causing issues

### Channel Renumbering (Deferred)
**Issue**: Tree sorting doesn't update visually after changing channelLow in data structure
- **Attempted Fixes** (Jan 17, 2026 session):
  - Added +/- buttons and manual entry field for channel number editing
  - Implemented `_apply_channel_number_change()` to update data and rebuild tree
  - Added re-entrancy guards to prevent duplicate calls
  - Tree rebuild logic sorts channels correctly by int(channelLow)
  - Debug output confirmed: data updates, sorting happens, tree rebuilt
- **Root Cause**: Unknown. Tree items inserted in sorted order but display doesn't reflect it
- **Workaround**: Removed feature entirely. Channel number now read-only
- **Future Investigation**: May need different approach (detach/reattach items vs full rebuild, or investigate tkinter.Treeview refresh behavior)

---

## Architecture Notes

### Current Data Model (Jan 2026)
- **Storage Format**: PMR-171 JSON (direct radio format)
  - Channels keyed by string ID ("0", "1", "2", etc.)
  - Each channel has 40+ fields including vfoaFrequency1-4, vfobFrequency1-4, etc.
  - Frequency stored as big-endian 4-byte integers (Hz)
  
- **GUI Data Flow**:
  - `self.channels` dict holds all channel data
  - Tree displays sorted view with selectable columns
  - Detail tabs edit channels in-place
  - Live updates via StringVar/IntVar traces
  - Save writes entire `self.channels` back to JSON

- **Design Decision**: Single-frequency sources (CHIRP) duplicate freq to both VFOs A and B for simplex operation. This is the intended behavior, not a limitation.

### Recommended Future Architecture
```
Input Formats (CHIRP .img, Anytone .rdt, etc.)
    ↓
Internal/Intermediate Format (flexible, human-readable)
    ↓
GUI Editor (edit intermediate format)
    ↓
Export Formats (PMR-171 JSON, CSV, other radios)
```

This allows:
- Single freq sources → intermediate → dual freq export (with user input)
- Dual freq sources → intermediate → preserve both freqs
- Format-agnostic editing experience

---

## Implementation Notes

### What Works Well (Keep This Approach)
- **Live channel name editing**: StringVar trace → direct tree item update (no cursor reset)
- **Column selection**: Dynamic tree reconfiguration works cleanly
- **Data binding**: ComboBox changes → `_update_field()` → immediate save
- **Arrow navigation**: Up/Down for channels, Left/Right for tabs with collapse prevention
- **Professional styling**: Blue headers, proper fonts, MOTORTRBO/ASTRO 25 aesthetic
- **File operations**: Ctrl+O/Ctrl+S with datetime-based defaults

### Technical Hints
- **Frequency Display**: Use `freq_from_bytes()` helper to convert 4-byte big-endian to MHz
- **CTCSS/DCS Format**: 
  - 0 = "Off"
  - 1-255 = CTCSS tones (map via CTCSS_CODES)
  - 1000+ = DCS codes (e.g., 1023 = "D023N", 2023 = "D023R")
- **Channel Types**: 0=Analog, 1=DMR (affects which fields are enabled)
- **Tree Item Selection**: Use `tags=(ch_id,)` to map tree items back to channel IDs
- **Rebuild Performance**: Full tree rebuild is fast enough (<50ms for 100 channels)

### UART Programming Implementation Plan

#### Phase 1: Protocol Research & Discovery
1. **Documentation Review**
   - [ ] Search for PMR-171 service manual or programming documentation
   - [ ] Check manufacturer website for SDK or programming cable specs
   - [ ] Review FCC filings for technical details
   - [ ] Search online forums (RadioReference, QRZ, etc.) for protocol information

2. **Hardware Setup**
   - [ ] Acquire PMR-171 programming cable (USB/UART adapter)
   - [ ] Identify cable pinout (TX, RX, GND, power)
   - [ ] Test cable with factory programming software
   - [ ] Document cable specifications (chipset, voltage levels)

3. **Packet Capture & Analysis**
   - [ ] **Option A: Software Interception**
     - Install Wireshark or similar packet capture tool
     - Monitor USB/COM port during factory software operation
     - Capture full programming session (read + write operations)
   - [ ] **Option B: Hardware Interception**
     - Use logic analyzer (Saleae Logic, DSLogic, etc.)
     - Connect to UART TX/RX lines between cable and radio
     - Capture at multiple baud rates (9600, 19200, 38400, 57600, 115200)
     - Record timing diagrams and signal levels
   - [ ] **Capture Scenarios**:
     - Radio identification/handshake
     - Full codeplug read
     - Single channel read
     - Full codeplug write
     - Single channel write
     - Verify operation
     - Error conditions

4. **Protocol Analysis**
   - [ ] Identify communication parameters:
     - Baud rate (test common rates)
     - Data bits (typically 8)
     - Parity (None, Even, Odd)
     - Stop bits (1 or 2)
     - Flow control (None, RTS/CTS, XON/XOFF)
   - [ ] Analyze packet structure:
     - Header format (start bytes, sync patterns)
     - Command codes (read, write, verify, etc.)
     - Address/memory location format
     - Data payload format
     - Checksum/CRC algorithm (CRC-16, CRC-32, simple sum, XOR)
     - Footer/terminator bytes
   - [ ] Document command set:
     - Initialization/handshake commands
     - Read commands (single byte, block read)
     - Write commands (single byte, block write)
     - Radio info query (model, firmware version, serial number)
     - Memory map structure
   - [ ] Reverse engineer checksums:
     - Test with modified packets
     - Identify algorithm (CRC polynomial, initial value, XOR out)
     - Implement checksum calculation in Python

#### Phase 2: Protocol Implementation
1. **Python Serial Communication Setup**
   - [ ] Add `pyserial` to requirements.txt
   - [ ] Create `uart_interface.py` module
   - [ ] Implement serial port detection and enumeration
   - [ ] Add connection error handling (timeouts, disconnects)
   - [ ] Implement packet framing (start/stop detection)
   - [ ] Add logging for debugging (hex dump of all packets)

2. **Low-Level Protocol Functions**
   - [ ] Implement checksum calculation
   - [ ] Create packet builder (header + data + checksum)
   - [ ] Create packet parser (validate and extract data)
   - [ ] Add retry logic for failed commands
   - [ ] Implement timeouts and error recovery

3. **Radio Communication Commands**
   - [ ] Radio identification/handshake
   - [ ] Query radio info (model, firmware version)
   - [ ] Read memory block (with address and length)
   - [ ] Write memory block (with verification)
   - [ ] Read full codeplug
   - [ ] Write full codeplug
   - [ ] Verify codeplug after write

#### Phase 3: Hardware-in-the-Loop Testing
1. **Test Equipment Setup**
   - [ ] Connect PMR-171 radio via programming cable
   - [ ] Set up test environment with known good codeplug
   - [ ] Create backup of original radio configuration
   - [ ] Document radio serial number and firmware version

2. **Read Operation Testing**
   - [ ] Test radio identification
   - [ ] Read single memory location
   - [ ] Read memory block (small, then progressively larger)
   - [ ] Read full codeplug
   - [ ] Compare read data with factory software backup
   - [ ] Verify data integrity (checksums, format)

3. **Write Operation Testing (Critical - Start Small!)**
   - [ ] **Safety First**: 
     - Test on non-critical memory (scratch area if available)
     - Always backup before writing
     - Never write to bootloader or calibration areas
   - [ ] Write single byte to test area
   - [ ] Read back and verify
   - [ ] Write single channel data
   - [ ] Read back and verify channel works on radio
   - [ ] Write full codeplug (after extensive read testing)
   - [ ] Verify radio functionality after write

4. **Edge Case Testing**
   - [ ] Test with empty channels
   - [ ] Test with maximum channel count
   - [ ] Test with long channel names
   - [ ] Test with split frequencies (RX ≠ TX)
   - [ ] Test with all modes (FM, AM, SSB, DMR, etc.)
   - [ ] Test with CTCSS/DCS tones
   - [ ] Test error recovery (disconnect during write, corrupt data)

#### Phase 4: GUI Integration
1. **Programming Interface**
   - [ ] Add "Program Radio" menu item
   - [ ] Create COM port selection dialog
   - [ ] Add "Read from Radio" button with progress bar
   - [ ] Add "Write to Radio" button with confirmation dialog
   - [ ] Implement "Compare Radio vs File" diff view
   - [ ] Add "Backup Radio" quick save function

2. **Safety Features**
   - [ ] Warn before overwriting radio
   - [ ] Require user confirmation for write operations
   - [ ] Validate codeplug before writing (frequency ranges, field values)
   - [ ] Show summary of changes before writing
   - [ ] Create automatic backup before each write
   - [ ] Implement write verification with retry on failure

3. **User Experience**
   - [ ] Real-time progress indicators
   - [ ] Clear error messages (with troubleshooting hints)
   - [ ] Connection status indicator
   - [ ] Programming log viewer (for debugging)
   - [ ] Cancel operation support (safe abort)

#### Phase 5: Documentation & Validation
1. **Protocol Documentation**
   - [ ] Create protocol specification document
   - [ ] Document all command codes and responses
   - [ ] Create memory map diagram
   - [ ] Document checksum algorithm with examples
   - [ ] Add packet format diagrams

2. **User Documentation**
   - [ ] Write programming guide
   - [ ] Document cable requirements
   - [ ] Create troubleshooting guide
   - [ ] Add FAQ section
   - [ ] Include video tutorial

3. **Testing & Validation**
   - [ ] Test on multiple PMR-171 radios (different firmware versions)
   - [ ] Verify with community testers
   - [ ] Create automated test suite for protocol functions
   - [ ] Document any limitations or known issues

#### Tools & Resources Needed
- **Hardware**:
  - PMR-171 radio (primary test unit)
  - PMR-171 programming cable (USB-UART adapter)
  - Optional: Spare PMR-171 for destructive testing
  - Optional: Logic analyzer (Saleae Logic 8, DSLogic Plus, etc.)
  - Optional: USB protocol analyzer
  
- **Software**:
  - Factory programming software (for packet capture)
  - Wireshark or similar packet capture tool
  - Logic analyzer software (Saleae Logic, sigrok/PulseView)
  - Python with pyserial library
  - Hex editor (HxD, 010 Editor)
  
- **Documentation**:
  - Service manual (if available)
  - Programming cable pinout
  - Known good codeplug files (from D:\Radio\Guohetec)

#### Risk Mitigation
- **CRITICAL**: Always backup radio before any write operations
- **CRITICAL**: Never write to bootloader or calibration areas without documentation
- **CRITICAL**: Verify checksums before writing to prevent bricking
- Start with read-only operations until protocol is fully understood
- Test on non-critical memory areas first
- Keep factory programming software available as fallback
- Document recovery procedures in case of programming failure
- Consider having a spare radio for testing risky operations

### CSV Export Considerations
- Map PMR-171 fields to human-readable column names
- Include both RX and TX frequencies (VFO A and VFO B)
- Format CTCSS/DCS codes properly (not raw integers)
- Consider CHIRP-compatible CSV format for round-trip compatibility

---

## Session History

### January 18, 2026 (Afternoon Session)
- **Focus**: GUI filter improvements and DMR mode validation
- **Accomplishments**:
  - Added "Group by DMR" filter (separates Analog/Digital channels)
  - Added "Group by mode" filter (groups by USB, LSB, NFM, AM, DMR, etc.)
  - Made filter options mutually exclusive for clean UX
  - Fixed DMR mode validation error - added Mode 9 (DMR) to valid modes
  - Updated all documentation with DMR mode findings
- **Key Findings**:
  - Mode 9 = DMR was added in firmware update (not in original FCC v1.5 documentation)
  - Sample_Channels.json contains 8 DMR channels using mode 9
  - DMR channels have additional fields: chType, callId, ownId, rxCc, txCc, slot
- **Documentation Updated**:
  - `docs/Pmr171_Protocol.md` - Added Mode 9 (DMR) and DMR channel configuration section
  - `Gui_Features.md` - Added filter options documentation
  - `codeplug_converter/utils/validation.py` - Added Mode 9 to valid modes

### January 18, 2026 (Test 11 Validation Session)
- **Focus**: CTCSS mapping validation and test result verification
- **Accomplishments**:
  - Verified Test 11 CTCSS validation results from radio readback
  - Created automated verification script (`11_Verification_Results.py`)
  - Confirmed 100% accuracy on all 25 test channels
  - Documented complete validation results (`11_Validation_Results.md`)
  - Updated all documentation to reflect VALIDATED status
- **Key Findings**:
  - All emitYayin and receiveYayin values match perfectly (25/25 channels)
  - Split tones, TX-only, RX-only all confirmed functional
  - Channel name truncation at 12 chars is cosmetic only
  - CTCSS mapping is production-ready
- **Status**: CTCSS implementation marked as ✅ VALIDATED AND PRODUCTION READY
- **Next Steps**:
  - Begin DCS code mapping (104+ codes)
  - Implement CHIRP to PMR171 conversion using validated mapping
  - Continue with UART programming research

### January 17-18, 2026 (Evening Session)
- **Focus**: JSON format validation and UART programming planning
- **Accomplishments**:
  - Created comprehensive test suite: `tests/test_pmr171_format_validation.py` with 24 passing tests
  - Validated JSON format compatibility with factory software (Mode_Test.json)
  - All tests confirm correct encoding: frequencies, modes, channel structure, field types
  - Reviewed actual factory software output from D:\Radio\Guohetec\PMR-171_20260116.json
  - Created detailed 5-phase UART programming implementation plan
  - Documented protocol research methodology (packet capture, hardware interception)
  - Outlined hardware-in-the-loop testing approach with safety protocols
- **Key Findings**:
  - Factory software uses callFormat=0 for analog, callFormat=2 for digital channels
  - Confirmed dual VFO architecture (vfoaFrequency vs vfobFrequency)
  - Identified need for hardware testing with actual PMR-171 radio
- **Next Steps**: 
  - Cross-validate generated JSON with factory software files
  - Begin UART protocol research phase
  - Acquire programming cable and test equipment

### January 17, 2026 (Earlier Session)
- **Focus**: Channel renumbering feature debugging
- **Outcome**: Feature removed after multiple failed attempts
- **Lessons**: tkinter.Treeview may have hidden refresh issues; simpler approaches (read-only) preferred
- **Documentation**: Added comprehensive TODO items for dual-frequency architecture and UART programming
- **GUI Status**: Stable and functional without renumbering capability

---

## Completed Items

- [x] Undo/Redo with Ctrl+Z/Ctrl+Y support - state snapshot system for all edit operations (Jan 2026)
- [x] Professional GUI with MOTORTRBO/ASTRO 25 styling (Jan 2026)
- [x] Live channel name editing without cursor reset (Jan 2026)
- [x] Column selection and ordering (Jan 2026)
- [x] File menu with Open/Save functionality (Jan 2026)
- [x] Arrow key navigation (Up/Down for channels, Left/Right for tabs) (Jan 2026)
- [x] Window icon support (Jan 2026)
- [x] Data binding for all editable fields (Jan 2026)
- [x] CSV export functionality (Jan 2026)
- [x] Automatic frequency formatting with live tree view updates (Jan 2026)
- [x] Channel validation with visual warnings for out-of-band frequencies and invalid tones (Jan 2026)
- [x] Bulk channel operations with multi-select, right-click context menu, delete and duplicate (Jan 2026)
- [x] Comprehensive PMR-171 JSON format validation tests - 24 tests verifying compatibility with factory programming software (Jan 2026)
- [x] **GUI Filter Options** - "Group by DMR" and "Group by mode" with mutually exclusive selection (Jan 18, 2026)
- [x] **DMR Mode Validation** - Added Mode 9 (DMR) to valid modes in validation.py (Jan 18, 2026)
- [x] **CTCSS Tone Encoding - Complete mapping and validation** (Jan 18, 2026)
  - Discovered correct emitYayin/receiveYayin fields (Tests 07-08)
  - Mapped all 50 standard CTCSS tones (Tests 05-10)
  - Validated with 25 test channels - 100% accuracy (Test 11)
  - Split tones, TX-only, RX-only all confirmed functional
  - Production ready with complete lookup tables

---

## Notes

*Use this file to track development tasks and ideas. Move completed items to the "Completed Items" section with completion date.*

Last Updated: January 18, 2026
