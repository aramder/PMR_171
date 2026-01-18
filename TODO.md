# CodeplugConverter TODO List

This document tracks planned features, enhancements, and known issues for the CodeplugConverter project.

---

## High Priority

### Core Functionality
- [ ] **Dual frequency architecture**: PMR-171 requires TWO frequencies per memory channel (VFO A and VFO B), but CHIRP only provides one. Need to:
  - Design an intermediate JSON format that supports dual frequencies per channel
  - Update GUI to display/edit both VFO A and VFO B frequencies
  - Add "Export to PMR-171" menu option that converts from intermediate format to PMR-171 compatible JSON
  - Current single-frequency channels should default to using same frequency for both VFOs (simplex operation)

- [ ] **Direct PMR-171 programming via UART**: Implement direct radio programming without needing manufacturer software
  - Research UART command protocol (check PMR-171 manual for documentation)
  - If undocumented, use UART adapter or logic analyzer to sniff programming transactions
  - Implement Python UART communication (pyserial library)
  - Add "Program Radio" menu option with COM port selection
  - Include read/backup functionality to pull existing config from radio
  - Error handling and validation before writing to radio

### GUI Enhancements
- [ ] **Channel renumbering**: Add +/- buttons to allow users to change channel numbers and automatically re-sort the channel list

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
- [ ] **Frequency calculator**: Repeater offset calculator and tone lookup
- [x] **Automatic frequency formatting**: Format frequency inputs to standard MHz precision (XXX.XXXXXX) with live tree view updates (Jan 2026)
- [x] **Channel validation**: Warn about out-of-band frequencies, invalid tones (Jan 2026)
- [ ] **Auto-programming**: Generate channels from repeater databases

---

## Known Issues / Bugs

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

- **Limitation**: Currently tied to PMR-171 format
  - Single-frequency sources (CHIRP) duplicate freq to both VFOs
  - No clean separation between "working format" and "export format"
  - This works for now but needs redesign for dual-frequency support

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

### UART Programming Research Needed
- Check PMR-171 user manual for programming protocol documentation
- If undocumented, capture transactions with:
  - USB-to-UART adapter (CP2102, FTDI, etc.) + Wireshark/putty logging
  - Logic analyzer (Saleae, DSLogic) on TX/RX lines during programming
- Likely protocol: Simple command/response over 9600-115200 baud
- Python implementation: Use `pyserial` library (add to requirements.txt)
- Consider adding progress bar for radio programming operations

### CSV Export Considerations
- Map PMR-171 fields to human-readable column names
- Include both RX and TX frequencies (VFO A and VFO B)
- Format CTCSS/DCS codes properly (not raw integers)
- Consider CHIRP-compatible CSV format for round-trip compatibility

---

## Session History

### January 17, 2026
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

---

## Notes

*Use this file to track development tasks and ideas. Move completed items to the "Completed Items" section with completion date.*

Last Updated: January 18, 2026
