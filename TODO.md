# PMR-171 CPS TODO List

This document tracks planned features, enhancements, and known issues for the PMR-171 CPS project.

---

## High Priority

### CTCSS Tone Encoding - ✅ COMPLETE AND VALIDATED
- [x] **Discovered correct fields**: Testing revealed emitYayin/receiveYayin are the correct fields (Jan 2026)
  - Test 07: rxCtcss/txCtcss fields are IGNORED by radio (always reset to 255)
  - Test 08: emitYayin/receiveYayin values PRESERVED, confirming correct implementation
- [x] **Complete CTCSS mapping table**: ✅ ALL 50 standard tones mapped (Tests 05-10, Jan 2026)
  - All CTCSS tones from 67.0 Hz to 254.1 Hz successfully mapped
  - Non-linear yayin encoding discovered (values 1-55 with gaps)
  - Complete lookup tables in `pmr_171_cps/writers/pmr171_writer.py`
- [x] **Validation**: ✅ Test 11 confirmed 100% accuracy (Jan 18, 2026)
  - 25 test channels verified (common, edge, split, TX-only, RX-only, no-tone)
  - All emitYayin and receiveYayin values match perfectly
  - Split tones, TX-only, RX-only all confirmed functional
- **Status**: ✅ **VALIDATED AND PRODUCTION READY**
- **Documentation**: See `docs/Complete_Ctcss_Mapping.md` and `D:/Radio/Guohetec/Testing/11_Validation_Results.md`

### DCS (Digital Coded Squelch) Encoding - BACKBURNER
- [ ] **Build DCS mapping table**: Pending radio firmware support (Est: 6-8 hours when available)
  - Configure each DCS code in manufacturer software (D023N, D023I, etc.)
  - Download from radio and record emitYayin/receiveYayin values
  - Build complete DCS code → yayin mapping table
  - Add DCS support to _tone_to_yayin()
- **Note**: DCS appears unsupported by current PMR-171 firmware. Revisit if firmware updates add DCS support.
- **Impact**: LOW - CTCSS covers most use cases; DCS support pending hardware capability

### JSON Format Validation & Factory Software Compatibility
- [x] **Comprehensive test suite**: 24 tests validating PMR-171 JSON format compatibility (Jan 2026)
- [x] **Cross-validate with factory software output**: ✅ VALIDATED - See docs/Factory_Json_Comparison.md (Jan 2026)
  - [x] Verified field value ranges match factory software - Perfect match!
  - [x] Frequency encoding validated - Mathematically correct big-endian Hz
  - [x] Field structure confirmed - All 40+ fields match factory format
  - [x] Test with actual radio hardware to confirm loadability - ✅ Validated via UART test (Jan 19, 2026)
- [x] **Additional JSON field analysis**: ✅ COMPLETE (Jan 2026)
  - [x] callFormat values documented: 0=analog, 2=digital (chType=0 vs chType=1)
  - [x] callId/ownId patterns documented: Big-endian 32-bit DMR IDs for digital channels
  - [x] chType=1 requirements verified: Requires callFormat=2, non-zero DMR IDs
  - [x] Default field values confirmed: txCc=2, all others 0 (matches factory)
- [ ] **Minor enhancement identified**: Update callFormat=2 for digital channels (currently always 0)
  - Impact: Low priority (only affects DMR channels, may work anyway)
  - Files to update: pmr_171_cps/writers/pmr171_writer.py
  - See docs/Factory_Json_Comparison.md for details

### Core Functionality
- [x] **Dual frequency architecture**: PMR-171 requires TWO frequencies per memory channel (VFO A and VFO B), but CHIRP only provides one. **Solution**: When importing from single-frequency sources (CHIRP), program the same frequency into both VFO A and VFO B (simplex operation). No intermediate format needed. (Jan 2026)

- [x] **UART Serial Transaction Analysis**: ✅ COMPLETE - Protocol fully reverse engineered (Jan 19, 2026)
  - **Documentation**: See `docs/UART_Reverse_Engineering_Report.md`
  - [x] Packet structure decoded: 4-byte header (0xA5A5A5A5) + length + command + payload + CRC-16
  - [x] Command codes identified: 0x41 (read), 0x40 (write), 0x27 (identity), etc.
  - [x] CRC-16-CCITT algorithm implemented (polynomial 0x1021, initial 0xFFFF)
  - [x] Channel data structure mapped: 26 bytes (index, modes, frequencies, CTCSS, name)
  - [x] Communication parameters: 115200 baud, 8N1, DTR=HIGH, RTS=HIGH
  - [x] Programming sequence documented with timing considerations
  - [x] Python implementation complete in `pmr_171_cps/radio/pmr171_uart.py`
  - **Captured data archived**: UART transaction logs in `tests/test_configs/Results/*.spm`

- [ ] **Direct PMR-171 programming via UART**: 🔴 **BLOCKED - DMR Write Failure** (January 19-21, 2026)
  - [x] Implemented Python UART communication (pyserial library)
  - [x] Added "Program Radio" menu option with COM port selection
  - [x] Included read/backup functionality to pull existing config from radio
  - [x] Error handling and validation before writing to radio
  - [x] ✅ **Reading DMR channels**: Successfully reads manually programmed DMR channels
  - [x] ✅ **Writing Analog channels**: Works perfectly, fully validated
  - [ ] 🔴 **Writing DMR channels**: BLOCKED - Both our CPS and manufacturer's CPS fail
  - **Location**: `pmr_171_cps/radio/pmr171_uart.py`
  - **GUI Integration**: Radio menu with Read/Write to Radio options
  - **Test Script**: `tests/test_uart_read_write_verify.py`
  - **Status**: Analog programming complete; DMR write **blocked pending firmware/CPS fix**
  - **Issue**: See Known Issues → "DMR Write Failure" below for full details

- [x] **UART Verification Test Script**: ✅ COMPLETE AND VALIDATED (January 19, 2026)
  - **Location**: `tests/test_uart_read_write_verify.py`
  - **Documentation**: `docs/UART_Testing.md`
  - **Test Results**: 5/5 channels passed on initial validation run
  - **Verified Functionality**:
    - Reading and writing channel data
    - Multiple modes (NFM, AM, USB, LSB, WFM)
    - CTCSS tone encoding (RX/TX independent)
    - Channel names up to 11 characters
    - VHF and UHF frequencies
    - Empty/unused channels vs programmed channels
    - Automatic backup and restoration
  - **Command-line Usage**:
    ```bash
    # Run with default settings (10 random channels)
    python tests/test_uart_read_write_verify.py --port COM3 --yes
    
    # Run with specific channel count
    python tests/test_uart_read_write_verify.py --channels 5 --verbose
    
    # Dry run (read-only, no writes)
    python tests/test_uart_read_write_verify.py --dry-run
    
    # Run via pytest
    python -m pytest tests/test_uart_read_write_verify.py -v
    ```

### GUI Enhancements
- [x] **Channel renumbering**: Add +/- buttons to allow users to change channel numbers and automatically re-sort the channel list
- [x] **Add Channel button**: Toolbar with Motorola Astro CPS-style buttons for Add/Delete/Move/Duplicate channels

---

## Medium Priority

### UART Protocol Enhancements
- [ ] **Write acknowledgement payload verification**: Verify ACK packet payload matches sent data
  - Currently only validates CRC and command byte (0x40 or 0x43)
  - Should compare echoed payload against original write data
  - Could detect transmission errors not caught by CRC alone
  - **Location**: `pmr_171_cps/radio/pmr171_uart.py` - `write_channel()` and `write_dmr_data()` methods
  - **Implementation options**:
    1. Byte-by-byte comparison of payload
    2. Optional read-back verification after write
    3. Compare critical fields only (channel index, frequency, mode)
  - **Priority**: LOW - Current implementation works reliably; this is a robustness enhancement

### Documentation Tasks
- [x] **UART Reverse Engineering Report**: ✅ COMPLETE (January 19, 2026)
  - Comprehensive technical report documenting the protocol discovery process
  - Executive summary with key achievements and metrics
  - Glossary of terms (suitable for table of contents)
  - Methodology: 6-phase approach from reconnaissance to validation
  - Hardware setup with connection parameters (DTR/RTS discovery)
  - Packet structure analysis with field mappings
  - Implementation architecture and code examples
  - Challenges & solutions documented
  - Lessons learned for future projects
  - **Location**: `docs/UART_Reverse_Engineering_Report.md`
  - **Format**: Markdown optimized for document/PowerPoint conversion

- [x] **Icon Generation Writeup**: ✅ COMPLETE - Document the custom icon creation process (See: `docs/Icon_Generation.md`)
  - [x] Icon design rationale and visual elements
  - [x] Pillow/PIL generation script explanation
  - [x] Multi-resolution icon generation (16px to 256px)
  - [x] GUI integration with tkinter iconphoto()
  - [x] Cross-platform considerations
  - [x] Troubleshooting guide

### Features
- [x] **CSV export/import**: ✅ COMPLETE AND TESTED (Jan 21, 2026)
  - Export channel data to CSV format (17 columns including frequencies, modes, CTCSS, DMR settings)
  - Import from CSV with flexible column matching (case-insensitive headers)
  - Replace/Merge/Cancel options for existing data
  - Full undo support for import operations
  - Test script: `tests/test_csv_export_import.py` (14 channels, 100% round-trip accuracy)
- [x] **Bulk channel operations**: Select multiple channels for batch editing, deletion, or copying (Jan 2026)

### Format Support
*No additional format support planned - PMR-171 CPS focuses exclusively on PMR-171*


---

## Low Priority / Nice to Have

- [x] **Undo/Redo**: Implement edit history for reverting changes (Jan 2026)
- [ ] **Channel zones/groups**: Artificial zone scheme for logical channel organization
  - Channels assigned to zones with automatic memory slot indexing
  - Zone start indices at multiples of 10, 100, or user-defined value
    - Example: Zone 1 = channels 0-9, Zone 2 = channels 10-19, Zone 3 = channels 100-199
  - Allows mentally bookmarked groups based on leading digit(s)
  - Implementation: Custom JSON fields added to existing format
    - `zoneNumber`: Zone assignment (1, 2, 3, etc.)
    - `channelInZone`: Channel index within zone (0-9, 0-99, etc.)
  - **Not a radio function** - CPS-only feature for organization
  - **Compatibility testing needed**: Test if Guohetec utility ignores unrecognized JSON fields (may strip on load/save)
- [x] **Frequency calculator**: Repeater offset calculator and tone lookup
- [x] **Automatic frequency formatting**: Format frequency inputs to standard MHz precision (XXX.XXXXXX) with live tree view updates (Jan 2026)
- [x] **Channel validation**: Warn about out-of-band frequencies, invalid tones (Jan 2026)

---

## Known Issues / Bugs

### DMR Write Failure (Critical Blocking Issue) - 🔴 BLOCKED
**Issue**: Both our CPS and manufacturer's CPS fail to write DMR channels to the radio properly
- **Discovered**: January 21, 2026 during Test 13/14 validation attempts
- **Severity**: **CRITICAL** - Blocks all DMR write functionality
- **Impact**: Cannot program DMR channels via any CPS software
- **What Fails**:
  - **Our CPS**: Radio crashes when writing DMR configurations (Tests 13, 13A)
  - **Manufacturer CPS**: Write completes but DMR data is not retained
    - DMR channels (`chType: 1`) read back as analog (`chType: 0`)
    - DMR-specific fields (ownId, callId, slot, etc.) are zeroed in readback
    - Only partial data from channel 0 is retained
- **Investigation Summary**:
  - Created Test 13, 13A, 14 configurations
  - Attempted write with our CPS → radio crashes
  - Attempted write with manufacturer's CPS → data not retained
  - Analyzed manufacturer's write/readback JSONs
  - Identified several field encoding issues (slot field, color codes, etc.)
  - BUT: Fixing these doesn't help if manufacturer's CPS also fails
- **Root Cause**: Unknown - could be:
  - Radio firmware bug preventing DMR programming via UART
  - Manufacturer CPS bug (GH Terminal software issue)
  - Missing initialization sequence or special DMR mode activation
  - Fundamental incompatibility with this radio hardware/firmware version
- **What Works**:
  - ✅ Reading DMR channels (manually programmed via radio menus)
  - ✅ Writing analog channels (fully functional)
  - ✅ CTCSS encoding for all channels
  - ✅ Reading all DMR parameters (IDs, Color Codes, Slots, Call Types)
- **Workaround**: 
  - DMR channels must be programmed manually on the radio
  - Use CPS to read DMR config after manual programming
  - CPS can edit analog channels only
- **Documentation**:
  - `tests/test_configs/Results/14_Manufacturer_Analysis.md` - Complete analysis
  - `tests/test_configs/14_UART_Comparison_Instructions.md` - Test procedure
  - `docs/DMR_Display_Investigation.md` - Related display mode investigation
- **Priority**: 🔴 **BLOCKED** - Cannot proceed until:
  - Manufacturer provides firmware update, OR
  - Manufacturer provides working CPS version, OR
  - Deeper UART protocol analysis reveals missing initialization

### DMR Display Mode Label (Cosmetic Issue) - ON HOLD
**Issue**: DMR channels display as "DFM" instead of "DMR" on radio screen
- **Status**: **BLOCKED** by DMR Write Failure issue above
- **Impact**: Cannot test until DMR write functionality works
- **Investigation**: On hold pending resolution of write failure
- **Priority**: LOW - Cosmetic only, blocked by critical issue

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


---

## Implementation Notes

### What Works Well (Keep This Approach)
- **Live channel name editing**: StringVar trace → direct tree item update (no cursor reset)
- **Column selection**: Dynamic tree reconfiguration works cleanly
- **Data binding**: ComboBox changes → `_update_field()` → immediate save
- **Arrow navigation**: Up/Down for channels, Left/Right for tabs with collapse prevention
- **Styling**: Blue headers, proper fonts, MOTORTRBO/ASTRO 25 aesthetic
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

### UART Protocol Summary (✅ COMPLETE)

The UART programming protocol has been fully reverse engineered and documented. See `docs/UART_Reverse_Engineering_Report.md` for complete technical details.

**Quick Reference:**
- **Connection**: 115200 baud, 8N1, DTR=HIGH, RTS=HIGH
- **Packet Format**: `[A5 A5 A5 A5] [Length] [Command] [Payload] [CRC-16]`
- **Commands**: 0x41 (read), 0x40 (write), 0x27 (identity)
- **CRC**: CRC-16-CCITT, polynomial 0x1021, initial 0xFFFF
- **Channel Data**: 26 bytes per channel

**Implementation Files:**
- `pmr_171_cps/radio/pmr171_uart.py` - Python UART implementation
- `tests/test_uart_read_write_verify.py` - Validation test script

### CSV Export/Import (✅ IMPLEMENTED)
- **Export** (File → Export to CSV...): 17 columns with human-readable names
  - Channel, Name, RX/TX Frequency, Offset, Mode, Channel Type
  - RX/TX CTCSS/DCS, Power, Squelch Mode, Bandwidth
  - DMR fields: Own ID, Call ID, Slot, Color Codes (RX/TX)
- **Import** (File → Import from CSV...): Flexible parsing
  - Required columns: Channel, RX Frequency
  - Case-insensitive column matching
  - Auto-detection of CTCSS/DCS and DMR values
- **Test Coverage**: `tests/test_csv_export_import.py`

---

## Session History

### January 21, 2026 (Late Evening Session)
- **Focus**: DMR Write Failure Investigation
- **Accomplishments**:
  - Tested our CPS with Test 13 and 13A configurations → radio crashes
  - Set up UART capture comparison (Test 14)
  - Configured identical channels in manufacturer's CPS
  - Captured manufacturer's write and readback
  - **CRITICAL DISCOVERY**: Manufacturer's CPS also fails to write DMR properly
  - Created comprehensive analysis: `tests/test_configs/Results/14_Manufacturer_Analysis.md`
  - Documented field encoding differences (slot, color codes, CTCSS fields)
  - **Decision**: Pause DMR write development - issue is likely radio firmware/CPS bug
- **Key Findings**:
  - Manufacturer write: DMR channels (`chType: 1`) read back as analog (`chType: 0`)
  - Data corruption in readback - most channels blank
  - Slot field encoding issue identified (1-based vs 0-based)
  - Color code encoding differs (rxCc: 0 vs 1, txCc: 2 vs 1)
  - Missing rxCtcss/txCtcss fields
- **Status Update**:
  - DMR write functionality: 🔴 **BLOCKED - ON HOLD**
  - Cannot proceed without working manufacturer CPS or firmware update
  - Reading DMR works; Writing analog works; DMR write does not work
- **Documentation Updated**:
  - `tests/test_configs/Results/14_Manufacturer_Analysis.md` - Complete investigation
  - `TODO.md` - Updated with blocking issue status

### January 21, 2026 (Afternoon Session)
- **Focus**: CSV Import/Export Testing
- **Accomplishments**:
  - Verified CSV export/import functionality is complete and working
  - Created automated test script: `tests/test_csv_export_import.py`
  - Tested round-trip accuracy with 14 channels from Mode_Test.json - 100% match
  - Verified all 17 CSV columns export correctly (frequencies, modes, CTCSS, DMR settings)
  - Tested GUI CSV menu items (File → Export to CSV, File → Import from CSV)
- **Documentation Updated**:
  - `TODO.md` - Updated CSV feature status to ✅ COMPLETE AND TESTED
  - Added test script reference and validation results

### January 21, 2026 (Late Morning Session)
- **Focus**: DMR vs DFM Display Mode Investigation
- **Accomplishments**:
  - Analyzed existing sample data and documentation for DMR/DFM configurations
  - **Identified documentation discrepancy**: `DMR_Display_Investigation.md` and `DMR_Display_Modes.md` make conflicting claims about whether `callFormat` controls the display
  - Found issues in `examples/Mode_Test.json`: Channel 3 has wrong vfoaMode (3 instead of 9), Channel 9 has wrong chType (0 instead of 1)
  - Created **Test 13** configuration (`tests/test_configs/13_dmr_dfm_display_test.json`) with systematic `callFormat` variations
  - Created test instructions (`tests/test_configs/13_Test_Instructions.md`)
  - Updated both conflicting docs with discrepancy warnings and Test 13 references
- **Key Files Created**:
  - `tests/test_configs/13_dmr_dfm_display_test.json` - 10 channels testing callFormat 0/1/2/255
  - `tests/test_configs/13_Test_Instructions.md` - Complete test procedure
- **Documentation Updated**:
  - `docs/DMR_Display_Investigation.md` - Added discrepancy warning and Test 13 action item
  - `docs/DMR_Display_Modes.md` - Added discrepancy warning and Test 13 reference
  - `TODO.md` - Updated Known Issues with Test 13 details
- **🔴 ACTION REQUIRED**: Run Test 13 to resolve the documentation conflict

### January 20, 2026 (Afternoon Session)
- **Focus**: TODO cleanup and status review
- **Accomplishments**:
  - Updated TODO.md with current project status
  - Fixed Icon Generation Writeup status (all items complete → marked ✅ COMPLETE)
  - Marked UART Serial Transaction Analysis as ✅ COMPLETE (documented in UART_Reverse_Engineering_Report.md)
  - Updated last modified date
- **Project Status Summary** (All High Priority Items Complete!):
  - CTCSS Tone Encoding: ✅ VALIDATED AND PRODUCTION READY
  - UART Serial Transaction Analysis: ✅ COMPLETE (protocol fully reverse engineered)
  - Direct UART Programming: ✅ COMPLETE AND FUNCTIONAL
  - JSON Format Validation: ✅ COMPLETE (24 tests passing)
  - GUI Features: ✅ COMPLETE (filters, bulk ops, undo/redo, icons)
  - Documentation: ✅ COMPLETE (UART Report, Icon Generation, Protocol docs)
- **Remaining Work**:
  - Minor: Update callFormat=2 for digital channels
  - Backburner: DCS encoding (pending firmware support)
  - Low priority: Channel zones/groups, presets, auto-programming

### January 19, 2026 (Early Morning Session)
- **Focus**: TODO cleanup and UART GUI testing
- **Accomplishments**:
  - Reviewed and cleaned up TODO.md
  - Removed Baofeng support from roadmap (project focuses exclusively on PMR-171)
  - Removed Channel Renumbering from known issues (now working)
  - Moved DCS encoding to BACKBURNER status (pending firmware support)
  - Marked hardware testing as complete (validated via UART test script Jan 19)
  - Successfully launched GUI with UART connection to COM3
- **Key Findings**:
  - UART test script (`test_uart_read_write_verify.py`) validates hardware compatibility
  - GUI connects to radio with DTR=True, RTS=True
  - Direct UART programming is functional
- **Remaining High Priority Items**:
  - Update callFormat=2 for digital channels (minor)
  - Complete UART Serial Transaction Analysis (5 phases - documentation only)
- **Documentation Updated**:
  - `TODO.md` - Comprehensive cleanup and status updates

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
  - `pmr_171_cps/utils/validation.py` - Added Mode 9 to valid modes

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
- [x] **CSV import functionality** (Jan 21, 2026)
  - Flexible column matching (case-insensitive)
  - Replace/Merge/Cancel import options
  - Full undo support
  - Test script with 100% round-trip verification
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
- [x] **Direct PMR-171 UART Programming** (Jan 19, 2026)
  - Python UART communication via pyserial
  - GUI integration with Radio menu (Read/Write to Radio)
  - Verified with test script: `tests/test_uart_read_write_verify.py`
  - 5/5 channels passed validation
- [x] **Progress indicators for radio operations** (Jan 2026)
  - Progress bar dialog with Cancel button
  - Real-time status updates during read/write
  - Implemented in `_create_progress_dialog()` method

---

## Notes

*Use this file to track development tasks and ideas. Move completed items to the "Completed Items" section with completion date.*

Last Updated: January 21, 2026
