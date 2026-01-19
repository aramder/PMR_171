# PMR-171 CPS Icon Generation

This document describes how the application icons were created and integrated into the GUI.

## Overview

The PMR-171 CPS application uses a custom-generated icon that visually represents the PMR-171 SDR transceiver. The icon features:

- PMR-171 transceiver front panel representation
- Color TFT display with spectrum/waterfall visualization
- VFO tuning knob
- Antenna connectors in realistic positions
- "PMR 171" text branding

## Icon Files

All icon files are stored in `pmr_171_cps/assets/`:

| File | Size | Description |
|------|------|-------------|
| `pmr171_cps.png` | 256x256 | Main application icon (with text) |
| `pmr171_cps_16.png` | 16x16 | Small icon size |
| `pmr171_cps_32.png` | 32x32 | Standard icon size |
| `pmr171_cps_48.png` | 48x48 | Medium icon size |
| `pmr171_cps_64.png` | 64x64 | Large icon size |
| `pmr171_cps_128.png` | 128x128 | Extra-large icon size |
| `pmr171_cps.ico` | Multi-res | Windows ICO with all sizes embedded |
| `pmr171_radio.png` | 64x64 | Radio-only icon (no text) |
| `pmr171_radio_*.png` | Various | Radio-only at multiple sizes |

## Generation Script

The icons are generated programmatically using Python and Pillow (PIL).

### Location
```
scripts/generate_icon.py
```

### Requirements
```bash
pip install Pillow
```

### Running the Generator
```bash
python scripts/generate_icon.py
```

This will regenerate all icon files in `pmr_171_cps/assets/`.

### Key Functions

#### `create_pmr171_icon(size)`
Creates the main application icon with:
- White rounded-rectangle background with subtle shadow
- PMR-171 chassis representation (dark gray/black)
- Color TFT display with:
  - S-meter (green/yellow/red bar)
  - Frequency display (xxx.xxx.xxx format in cyan)
  - Spectrum/waterfall visualization (red peak, blue waterfall)
- Three antenna connectors (SMA-style with gold center pins)
- VFO tuning knob (silver with dark center)
- "PMR" text above and "171" text below the radio

#### `create_radio_only_icon(size)`
Creates a compact radio-only icon (no text) suitable for window titlebars at small sizes.

#### `get_font(size)`
Attempts to load stylish bold fonts in order of preference:
1. Bahnschrift (modern geometric sans)
2. Arial Black
3. Impact
4. Agency FB Bold
5. Trebuchet Bold
6. Arial Bold
7. Default system font

## GUI Integration

### Loading the Icon

The icon is loaded in `pmr_171_cps/gui/table_viewer.py` in the `show()` method:

```python
def show(self):
    # ... window creation ...
    
    # Set window icon
    icon_path = Path(__file__).parent.parent / 'assets' / 'pmr171_cps.png'
    if icon_path.exists():
        try:
            icon = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, icon)
        except:
            pass  # Icon loading failed, continue without it
```

### How It Works

1. **Path Resolution**: The icon path is resolved relative to the module location:
   - `Path(__file__).parent` = `pmr_171_cps/gui/`
   - `.parent` = `pmr_171_cps/`
   - `/ 'assets' / 'pmr171_cps.png'` = `pmr_171_cps/assets/pmr171_cps.png`

2. **Loading**: `tk.PhotoImage` loads the PNG file directly (tkinter supports PNG format)

3. **Setting**: `root.iconphoto(True, icon)` sets the icon for:
   - Window titlebar (small icon)
   - Windows taskbar (medium icon)
   - Alt+Tab switcher (varies by OS)

4. **Error Handling**: The icon loading is wrapped in try/except to gracefully handle:
   - Missing icon file
   - Corrupted image
   - tkinter compatibility issues

### Cross-Platform Behavior

| Platform | Titlebar | Taskbar | Notes |
|----------|----------|---------|-------|
| Windows | ✓ | ✓ | Works well with PNG via iconphoto() |
| Linux | ✓ | ✓ | Native support for PNG icons |
| macOS | ✓ | ✓ | Dock icon support varies |

## Design Decisions

### Why PNG Instead of ICO?

While Windows traditionally uses ICO files, tkinter's `iconphoto()` method with PNG provides:
- Simpler cross-platform code
- Direct support without platform checks
- Good quality at all sizes (tkinter handles scaling)

The ICO file is still generated and available if platform-specific handling is needed in the future.

### Why a Single PNG File?

Using `pmr171_cps.png` (256x256) as the source:
- tkinter automatically scales for titlebar (typically 16-24px)
- Windows taskbar uses a scaled version that looks acceptable
- Simplifies the code (no need to select between multiple sizes)

### Color Scheme

The icon uses colors that match the PMR-171 radio:
- Dark chassis: `#1A1A1A` (near-black)
- Display background: `#000000` (black)
- Display text/graphics: `#00DDFF` (cyan)
- Spectrum peak: `#FF4466` (red)
- Waterfall: Blue gradient
- Knob: `#555555` (dark silver)
- Connector pins: `#CC9933` (gold)

## Regenerating Icons

If you need to modify the icon design:

1. Edit `scripts/generate_icon.py`
2. Run `python scripts/generate_icon.py`
3. Test with `python -m pmr_171_cps view examples/Mode_Test.json`
4. Verify icon appears in:
   - Window titlebar
   - Windows taskbar
   - Alt+Tab preview

## Troubleshooting

### Icon Not Appearing

1. **Check file exists**: Verify `pmr_171_cps/assets/pmr171_cps.png` exists
2. **Check file size**: Should be ~6KB (not 0 bytes)
3. **Check permissions**: File should be readable

### Icon Looks Blurry

The 256x256 source icon is scaled by tkinter. For better quality at small sizes:
- Consider using `pmr171_cps_32.png` for titlebar
- Or implement platform-specific ICO handling for Windows

### Icon Shows Default Python Icon

This usually means icon loading failed silently. Check:
- PNG file is valid (open in image viewer)
- Path resolution is correct
- No exceptions during loading (add print statements to debug)

## Future Improvements

Potential enhancements:
1. Use ICO file on Windows for better multi-resolution support
2. Add high-DPI variants for 4K displays
3. Create macOS .icns file for native Dock integration
4. Add icon to Windows executable when packaged with PyInstaller
