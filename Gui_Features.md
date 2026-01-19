# Professional Radio Programming GUI

## Overview
The CodeplugConverter now features a professional radio programming interface modeled after industry-standard software like MOTORTRBO CPS and ASTRO 25 Mobile Depot.

## Interface Layout

### Main Window Structure
```
┌─────────────────────────────────────────────────────────────┐
│ File  Edit  View  Help                            [Menu Bar]│
├──────────────┬──────────────────────────────────────────────┤
│              │ Channel 5 - Thom UHF          [Header]       │
│ Channels     ├──────────────────────────────────────────────┤
│              │ ┌──────────────────────────────────────────┐ │
│ [Search:___] │ │ General │ RX │ TX │ DMR │ Adv │ Raw    │ │
│              │ └──────────────────────────────────────────┘ │
│ ┌──────────┐ │                                              │
│ │▼ Analog  │ │  Channel Number:     [5                  ]  │
│ │  Ch 0    │ │  Channel Name:       [Thom UHF          ]  │
│ │  Ch 1    │ │  Channel Type:       [Analog          ▼]  │
│ │  Ch 2    │ │  Mode:               [NFM             ▼]  │
│ │          │ │  Squelch Mode:       [CTCSS/DCS       ▼]  │
│ │▼ DMR     │ │  Power Level:        [High            ▼]  │
│ │  Ch 100  │ │  Bandwidth:          [Narrow (12.5kHz)▼]  │
│ │          │ │                                              │
│ └──────────┘ │                                              │
└──────────────┴──────────────────────────────────────────────┘
│ Total Channels: 46 | Ready                      [Status Bar]│
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Tree Navigation Panel (Left Side)
- **Organized Channel List**: Channels grouped by type (Analog/DMR) or by modulation mode
- **Tree Structure**: Expandable/collapsible groups
- **Quick Search**: Filter channels by name or frequency
- **At-a-Glance Info**: Shows channel number, name, RX frequency, and mode

#### Filter Options
The tree panel includes a filter bar with the following options:

| Filter | Description |
|--------|-------------|
| **Show empty channels** | Toggle to show/hide channels with no programmed data (Mode 255) |
| **Group by DMR** | Groups channels into "Analog Channels" and "DMR Channels" sections |
| **Group by mode** | Groups channels by modulation mode (USB, LSB, NFM, AM, DMR, etc.) |

**Notes:**
- "Group by DMR" and "Group by mode" are mutually exclusive - enabling one disables the other
- All filters work in combination with the search box
- Groups are automatically expanded when selected

### 2. Tabbed Detail View (Right Side)

#### **General Tab**
- Channel Number (read-only)
- Channel Name (editable)
- Channel Type (Analog/DMR dropdown)
- Mode (USB/LSB/NFM/WFM/DMR/etc.)
- Squelch Mode (Carrier/CTCSS/DCS)
- Power Level (High/Low)
- Bandwidth (Narrow 12.5kHz/Wide 25kHz)

#### **Frequency Tab** (RX/TX Combined)
**Three-column layout with copy tools:**

**Left Column - Receive (RX):**
- RX Frequency (MHz) - editable
- CTCSS/DCS Tone - editable
- Squelch Level (0-9 slider)
- Monitor Type (Open Squelch/Silent)

**Center Column - Copy Tools:**
- **Current Offset Display** - Auto-calculated (TX - RX)
- **Simplex Copy Buttons:**
  - `RX → TX (Simplex)` - Copy RX freq to TX (makes simplex)
  - `TX → RX (Simplex)` - Copy TX freq to RX (makes simplex)
- **Offset Input:** Custom offset in MHz
- **Preset Buttons:** +5.0, -5.0, +0.6 (common repeater offsets)
- **Offset Copy Buttons:**
  - `RX + Offset → TX` - Apply offset to RX, copy to TX
  - `TX + Offset → RX` - Apply offset to TX, copy to RX
- **Copy CTCSS/DCS Checkbox** - Enabled by default, copies tone settings when copying frequencies

**Right Column - Transmit (TX):**
- TX Frequency (MHz) - editable
- CTCSS/DCS Tone - editable
- Color Code (DMR, 0-15)
- Power Level (High/Low)

**Features:**
- Real-time offset calculation displayed
- Bi-directional frequency copying
- Optional offset application (positive or negative)
- CTCSS/DCS sync option (enabled by default)
- Common repeater offset presets (+5.0 MHz UHF, -0.6 MHz 2m)

#### **DMR Tab** (Digital Mode Radio)
- Call ID (DMR contact ID)
- Own ID (radio's DMR ID)
- RX Color Code (0-15)
- Timeslot (1 or 2)
- Talk Group
- Emergency Alarm (checkbox)

#### **Advanced Tab**
- Scrambler (on/off)
- Compander (on/off)
- VOX (voice activation)
- PTT ID (push-to-talk identification)
- Busy Lock
- Scan List assignment
- TOT - Time Out Timer (seconds)

#### **Raw Data Tab**
- Full JSON view of all channel parameters
- Read-only formatted display
- Useful for debugging or advanced users

### 3. Professional Styling
- **Color Scheme**: 
  - Header blue: `#0099CC` (matches MOTORTRBO style)
  - Tree background: Light gray `#F0F0F0`
  - Selection highlight: `#0066CC`
- **Fonts**: Arial for labels, Consolas for code/data
- **Layout**: Resizable paned window (adjustable split)

### 4. Menu Bar
- **File Menu**:
  - Save (placeholder for future implementation)
  - Exit
  
- **Edit Menu**:
  - Copy Channel
  - Delete Channel
  
- **View Menu**:
  - Refresh
  
- **Help Menu**:
  - About

### 5. Status Bar
- Total channel count
- Current status message
- Updates with channel selection

## Usage

### Viewing Channels
1. Launch the GUI with a converted JSON file:
   ```bash
   python -m codeplug_converter view channels.json
   ```

2. **Navigate**: Click on a channel in the tree to view details

3. **View Details**: Details appear in the right panel across 6 tabs

4. **Search**: Use the search box to filter channels

### Editing Channels (Future Feature)
Currently the interface is read-only for viewing. Future versions will support:
- Direct editing of channel parameters
- Saving modified configurations
- Copy/paste channels
- Adding/removing channels

## Design Philosophy

This interface follows industry standards from professional radio programming software:

1. **Tree + Detail View**: Mimics MOTORTRBO CPS, Astro 25, and other commercial software
2. **Tabbed Organization**: Separates settings into logical groups (General/RX/TX/DMR/Advanced)
3. **Form-Based Input**: Each parameter has its own labeled field with appropriate control (text box, dropdown, slider, checkbox)
4. **Visual Hierarchy**: Blue headers, grouped settings, clear labels
5. **Professional Look**: Clean, uncluttered, business-appropriate styling

## Comparison to Sample Software

### Similar to MOTORTRBO CPS
- Tree navigation on left
- Tabbed detail panel on right
- Blue header bars
- Form-based parameter entry
- Menu bar with File/Edit/View/Help

### Similar to ASTRO 25 Mobile Depot
- Table/grid view in tree
- Organized channel grouping
- Status bar at bottom
- Professional color scheme

### Similar to Radio Programming GUIs
- Dedicated tabs for RX/TX settings
- DMR-specific configuration tab
- Advanced features separated
- Raw data view for debugging

## Future Enhancements

Planned features:
- [ ] Save edited channels back to JSON
- [ ] Export to other formats (CHIRP .img, .csv)
- [ ] Import from multiple sources
- [ ] Drag-and-drop channel reordering
- [ ] Bulk edit multiple channels
- [ ] Frequency validation and warnings
- [ ] CTCSS/DCS tone picker with standard values
- [ ] DMR database integration
- [ ] Zone/scan list management
- [ ] Radio model profiles
- [ ] UART programming interface
