#!/usr/bin/env python3
"""Generate PMR-171 CPS application icon

Creates a professional radio programming software icon featuring:
- PMR-171 SDR transceiver front panel representation
- Color TFT display with spectrum waterfall
- VFO tuning knob in upper right
- PMR-171 text branding with proper fonts
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get a stylish bold title font at the specified size"""
    # Try bold/heavy fonts first for strong visual impact
    font_names = [
        "BAHNSCHRIFT.TTF",   # Bahnschrift - modern geometric sans (Windows 10+)
        "bahnschrift.ttf",
        "ariblk.ttf",        # Arial Black - very bold
        "Arial Black.ttf",
        "impact.ttf",        # Impact - bold condensed
        "Impact.ttf",
        "AGENCYB.TTF",       # Agency FB Bold - tech/industrial
        "Agency FB Bold.ttf",
        "trebucbd.ttf",      # Trebuchet Bold - distinctive
        "Trebuchet MS Bold.ttf",
        "arialbd.ttf",       # Arial Bold
        "Arial Bold.ttf",
    ]
    
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    
    # Fall back to default
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def create_pmr171_icon(size: int = 256) -> Image.Image:
    """Create the PMR-171 CPS icon based on actual radio appearance
    
    Args:
        size: Icon size in pixels (square)
        
    Returns:
        PIL Image object
    """
    # Create RGBA image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    s = size / 256
    
    # === WHITE BACKGROUND WITH ROUNDED CORNERS AND SHADOW ===
    bg_margin = int(4 * s)  # Small margin around the white background
    corner_radius = int(20 * s)  # Rounded corners
    
    # Draw subtle drop shadow (offset and blurred effect)
    shadow_offset = int(3 * s)
    shadow_color = (0, 0, 0, 40)  # Semi-transparent black
    draw.rounded_rectangle(
        [bg_margin + shadow_offset, bg_margin + shadow_offset, 
         size - bg_margin + shadow_offset, size - bg_margin + shadow_offset],
        radius=corner_radius,
        fill=shadow_color
    )
    
    # Draw main white background
    bg_color = '#F5F5F5'  # Slightly off-white for subtle depth
    draw.rounded_rectangle(
        [bg_margin, bg_margin, size - bg_margin, size - bg_margin],
        radius=corner_radius,
        fill=bg_color,
        outline='#E0E0E0',  # Light gray border
        width=max(1, int(1 * s))
    )
    
    # Add subtle gradient effect at top (lighter) - simple highlight line
    highlight_y = bg_margin + int(8 * s)
    draw.line(
        [(bg_margin + corner_radius, highlight_y), 
         (size - bg_margin - corner_radius, highlight_y)],
        fill='#FFFFFF',
        width=max(1, int(2 * s))
    )
    
    # Color palette
    chassis_black = '#1A1A1A'
    chassis_dark = '#252525'
    display_bg = '#000000'
    display_cyan = '#00DDFF'
    knob_silver = '#555555'
    button_dark = '#2D2D2D'
    text_color = '#000000'  # Black text
    
    # Get font (even larger and bolder)
    font_size = max(12, int(95 * s))  # Larger font
    font = get_font(font_size)
    
    # Calculate layout to center everything vertically
    # Radio height - taller to show detail
    radio_height = int(65 * s)
    
    # === TEXT "PMR" ABOVE RADIO ===
    pmr_text = "PMR"
    pmr_bbox = draw.textbbox((0, 0), pmr_text, font=font)
    pmr_width = pmr_bbox[2] - pmr_bbox[0]
    pmr_height = pmr_bbox[3] - pmr_bbox[1]
    
    # Calculate "171" text height
    num_bbox = draw.textbbox((0, 0), "171", font=font)
    num_height = num_bbox[3] - num_bbox[1]
    
    # Total content height - PMR at top, content centered below
    gap_pmr_radio = int(14 * s)  # Larger gap - PMR up a couple pixels
    gap_radio_171 = int(1 * s)   # Tiny gap below radio
    total_height = pmr_height + gap_pmr_radio + radio_height + gap_radio_171 + num_height
    
    start_y = (size - total_height) // 2 - int(5 * s)  # Shift down 10 pixels
    
    pmr_x = (size - pmr_width) // 2
    pmr_y = start_y
    
    draw.text((pmr_x, pmr_y), pmr_text, fill=text_color, font=font)
    
    # === MAIN CHASSIS (centered) ===
    margin_h = int(5 * s)
    chassis_top = pmr_y + pmr_height + gap_pmr_radio
    chassis_bottom = chassis_top + radio_height
    chassis_height = chassis_bottom - chassis_top
    
    corner_radius = int(6 * s)
    draw.rounded_rectangle(
        [margin_h, chassis_top, size - margin_h, chassis_bottom],
        radius=corner_radius,
        fill=chassis_black,
        outline=chassis_dark,
        width=max(1, int(2 * s))
    )
    
    # Top strip
    top_strip_height = int(10 * s)
    draw.rectangle(
        [margin_h + int(2 * s), chassis_top + int(2 * s), 
         size - margin_h - int(2 * s), chassis_top + top_strip_height],
        fill=chassis_dark
    )
    
    # === COLOR TFT DISPLAY ===
    display_left = int(80 * s)  # Shifted right 5 pixels
    display_top = chassis_top + int(12 * s)
    display_right = int(170 * s)  # Shifted right 5 pixels
    display_bottom = chassis_bottom - int(6 * s)
    
    bezel_pad = int(2 * s)
    draw.rectangle(
        [display_left - bezel_pad, display_top - bezel_pad,
         display_right + bezel_pad, display_bottom + bezel_pad],
        fill='#0D0D0D',
        outline='#333333',
        width=max(1, int(1 * s))
    )
    
    draw.rectangle(
        [display_left, display_top, display_right, display_bottom],
        fill=display_bg
    )
    
    # S-meter
    meter_left = display_left + int(4 * s)
    meter_width = int(40 * s)
    meter_height = int(3 * s)
    meter_top = display_top + int(2 * s)
    
    draw.rectangle([meter_left, meter_top, meter_left + int(20 * s), meter_top + meter_height], fill='#00BB00')
    draw.rectangle([meter_left + int(20 * s), meter_top, meter_left + int(30 * s), meter_top + meter_height], fill='#DDDD00')
    draw.rectangle([meter_left + int(30 * s), meter_top, meter_left + meter_width, meter_top + meter_height], fill='#DD0000')
    
    # Frequency display - xxx.xxx.xxx format (right justified)
    freq_top = display_top + int(8 * s)  # Shift down to avoid S-meter
    freq_y = freq_top
    digit_width = int(4 * s)
    digit_height = int(7 * s)
    digit_gap = int(2 * s)
    group_gap = int(3 * s)
    
    # Calculate total width and right-justify
    total_freq_width = 9 * digit_width + 8 * digit_gap + 2 * group_gap
    x = display_right - int(5 * s) - total_freq_width
    
    # Draw 3 groups of 3 digits with dots between
    for group in range(3):
        for d in range(3):
            draw.rectangle([x, freq_y, x + digit_width, freq_y + digit_height], fill=display_cyan)
            x += digit_width + digit_gap
        
        if group < 2:
            # Draw dot clearly between groups
            dot_size = int(2 * s)
            dot_y = freq_y + digit_height - dot_size
            dot_x = x - digit_gap // 2 + group_gap // 2
            draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], fill=display_cyan)
            x += group_gap
    
    # Spectrum/Waterfall
    waterfall_top = freq_top + int(12 * s)  # Shift down more
    waterfall_left = display_left + int(2 * s)
    waterfall_right = display_right - int(2 * s)
    waterfall_bottom = display_bottom - int(2 * s)
    
    draw.rectangle([waterfall_left, waterfall_top, waterfall_right, waterfall_bottom], fill='#000015')
    
    center_x = (waterfall_left + waterfall_right) // 2
    noise_y = waterfall_top + int(10 * s)
    
    # Spectrum peak (red)
    peak_height = int(8 * s)
    peak_points = [
        (waterfall_left, noise_y),
        (center_x - int(10 * s), noise_y),
        (center_x - int(5 * s), noise_y - int(2 * s)),
        (center_x - int(2 * s), noise_y - peak_height + int(2 * s)),
        (center_x, noise_y - peak_height),
        (center_x + int(2 * s), noise_y - peak_height + int(2 * s)),
        (center_x + int(5 * s), noise_y - int(2 * s)),
        (center_x + int(10 * s), noise_y),
        (waterfall_right, noise_y),
    ]
    draw.line(peak_points, fill='#FF4466', width=max(1, int(2 * s)))
    
    for y_off in range(1, int(peak_height)):
        progress = y_off / peak_height
        width = int(8 * s * (1 - progress * 0.7))
        if width > 0:
            draw.line([(center_x - width, noise_y - y_off), (center_x + width, noise_y - y_off)], fill='#FF3355', width=1)
    
    # Waterfall (blue)
    for i in range(5):
        y = noise_y + int(2 * s) + i * int(3 * s)
        if y >= waterfall_bottom:
            break
        width = max(int(2 * s), int(6 * s) - i * int(1 * s))
        colors = ['#6699FF', '#4477EE', '#3366DD', '#2255CC', '#1144AA']
        draw.rectangle([center_x - width, y, center_x + width, y + int(2 * s)], fill=colors[min(i, len(colors)-1)])
    
    draw.line([(center_x, waterfall_top), (center_x, waterfall_bottom)], fill='#0088FF', width=max(1, int(1 * s)))
    
    # === ANTENNA CONNECTORS (3 on left side, offset diagonally) ===
    # Based on real PMR-171: top-left corner, diagonal pattern going down-right
    # Positions (cx, cy) for each connector relative to chassis
    connector_radius = int(7 * s)
    
    # Antenna positions - adjusted
    connectors = [
        (margin_h + int(36 * s), chassis_top + int(14 * s)),   # Top - shifted right 3px more
        (margin_h + int(23 * s), chassis_top + int(32 * s)),   # Middle - shifted right 20px, down 2px
        (margin_h + int(32 * s), chassis_top + int(50 * s)),   # Bottom - shifted right 20px, down 2px
    ]
    
    for cx, cy in connectors:
        # Outer ring (silver)
        draw.ellipse(
            [cx - connector_radius, cy - connector_radius,
             cx + connector_radius, cy + connector_radius],
            fill='#888888',
            outline='#666666',
            width=max(1, int(1 * s))
        )
        # Inner circle (darker)
        inner_r = int(5 * s)
        draw.ellipse(
            [cx - inner_r, cy - inner_r,
             cx + inner_r, cy + inner_r],
            fill='#555555',
            outline='#444444',
            width=max(1, int(1 * s))
        )
        # Center pin (gold)
        pin_r = int(2 * s)
        draw.ellipse(
            [cx - pin_r, cy - pin_r,
             cx + pin_r, cy + pin_r],
            fill='#CC9933',
            outline='#AA7722',
            width=max(1, int(1 * s))
        )
    
    # === VFO KNOB (20% bigger, upper right corner) ===
    knob_center_x = int(230 * s)
    knob_center_y = chassis_top + int(20 * s)
    knob_radius = int(15 * s)  # 20% bigger (was 12)
    
    draw.ellipse(
        [knob_center_x - knob_radius, knob_center_y - knob_radius,
         knob_center_x + knob_radius, knob_center_y + knob_radius],
        fill=knob_silver,
        outline='#3D3D3D',
        width=max(1, int(1 * s))
    )
    
    inner_radius = int(10 * s)  # Proportionally larger (was 8)
    draw.ellipse(
        [knob_center_x - inner_radius, knob_center_y - inner_radius,
         knob_center_x + inner_radius, knob_center_y + inner_radius],
        fill='#404040',
        outline='#505050',
        width=max(1, int(1 * s))
    )
    
    # === TEXT "171" BELOW RADIO ===
    num_text = "171"
    num_bbox = draw.textbbox((0, 0), num_text, font=font)
    num_width = num_bbox[2] - num_bbox[0]
    num_x = (size - num_width) // 2
    num_y = chassis_bottom + gap_radio_171
    
    draw.text((num_x, num_y), num_text, fill=text_color, font=font)
    
    return img


def create_radio_only_icon(size: int = 64) -> Image.Image:
    """Create a radio-only icon (no text) for window titlebar
    
    The PMR-171 is a wide, flat transceiver - about 3:1 width to height ratio.
    This icon shows the radio centered in the square icon space with a white background.
    
    Args:
        size: Icon size in pixels (square)
        
    Returns:
        PIL Image object
    """
    # Create RGBA image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    s = size / 64  # Base scale for 64px icon
    
    # === WHITE BACKGROUND WITH ROUNDED CORNERS AND SHADOW ===
    bg_margin = int(1 * s)  # Small margin around the white background
    corner_radius = int(8 * s)  # Rounded corners (smaller for this icon)
    
    # Draw subtle drop shadow
    shadow_offset = int(1 * s)
    shadow_color = (0, 0, 0, 35)  # Semi-transparent black
    draw.rounded_rectangle(
        [bg_margin + shadow_offset, bg_margin + shadow_offset, 
         size - bg_margin + shadow_offset, size - bg_margin + shadow_offset],
        radius=corner_radius,
        fill=shadow_color
    )
    
    # Draw main white background
    bg_color = '#F5F5F5'  # Slightly off-white
    draw.rounded_rectangle(
        [bg_margin, bg_margin, size - bg_margin, size - bg_margin],
        radius=corner_radius,
        fill=bg_color,
        outline='#E0E0E0',  # Light gray border
        width=max(1, int(1 * s))
    )
    
    # Color palette
    chassis_black = '#1A1A1A'
    chassis_dark = '#252525'
    display_bg = '#000000'
    display_cyan = '#00DDFF'
    knob_silver = '#555555'
    
    # Radio dimensions - flat and wide like actual PMR-171
    # Radio is about 3:1 width:height ratio
    margin_h = int(4 * s)  # Increased margin to account for background padding
    radio_width = size - 2 * margin_h
    radio_height = int(20 * s)  # About 1/3 of icon height - flat like real radio
    
    # Center vertically
    radio_top = (size - radio_height) // 2
    radio_bottom = radio_top + radio_height
    radio_left = margin_h
    radio_right = size - margin_h
    
    # === MAIN CHASSIS ===
    corner_radius = int(3 * s)
    draw.rounded_rectangle(
        [radio_left, radio_top, radio_right, radio_bottom],
        radius=corner_radius,
        fill=chassis_black,
        outline=chassis_dark,
        width=max(1, int(1 * s))
    )
    
    # Top strip (darker area at top of radio)
    top_strip_height = int(4 * s)
    draw.rectangle(
        [radio_left + int(1 * s), radio_top + int(1 * s), 
         radio_right - int(1 * s), radio_top + top_strip_height],
        fill=chassis_dark
    )
    
    # === COLOR TFT DISPLAY (center-right of radio) ===
    display_left = int(22 * s)
    display_top = radio_top + int(4 * s)
    display_right = int(42 * s)
    display_bottom = radio_bottom - int(3 * s)
    
    # Display bezel
    bezel_pad = int(1 * s)
    draw.rectangle(
        [display_left - bezel_pad, display_top - bezel_pad,
         display_right + bezel_pad, display_bottom + bezel_pad],
        fill='#0D0D0D',
        outline='#333333',
        width=1
    )
    
    # Display screen
    draw.rectangle(
        [display_left, display_top, display_right, display_bottom],
        fill=display_bg
    )
    
    # S-meter bar (at top of display)
    meter_left = display_left + int(1 * s)
    meter_top = display_top + int(1 * s)
    meter_height = max(1, int(2 * s))
    
    draw.rectangle([meter_left, meter_top, meter_left + int(8 * s), meter_top + meter_height], fill='#00BB00')
    draw.rectangle([meter_left + int(8 * s), meter_top, meter_left + int(12 * s), meter_top + meter_height], fill='#DDDD00')
    draw.rectangle([meter_left + int(12 * s), meter_top, meter_left + int(16 * s), meter_top + meter_height], fill='#DD0000')
    
    # Spectrum waterfall area (below S-meter)
    waterfall_top = meter_top + meter_height + int(1 * s)
    waterfall_left = display_left + int(1 * s)
    waterfall_right = display_right - int(1 * s)
    waterfall_bottom = display_bottom - int(1 * s)
    
    draw.rectangle([waterfall_left, waterfall_top, waterfall_right, waterfall_bottom], fill='#000022')
    
    # Center line and signal peak
    center_x = (waterfall_left + waterfall_right) // 2
    draw.line([(center_x, waterfall_top), (center_x, waterfall_bottom)], fill='#0088FF', width=1)
    
    # === ANTENNA CONNECTORS (left side, diagonal layout) ===
    connector_radius = int(3 * s)
    
    # 3 connectors: top and bottom on right, middle on left (> pattern)
    connectors = [
        (radio_left + int(12 * s), radio_top + int(7 * s)),   # Top - right
        (radio_left + int(5 * s), radio_top + int(10 * s)),   # Middle - left
        (radio_left + int(12 * s), radio_top + int(13 * s)),  # Bottom - right
    ]
    
    for cx, cy in connectors:
        # Outer ring
        draw.ellipse(
            [cx - connector_radius, cy - connector_radius,
             cx + connector_radius, cy + connector_radius],
            fill='#888888',
            outline='#666666',
            width=1
        )
        # Inner circle
        inner_r = int(2 * s)
        draw.ellipse(
            [cx - inner_r, cy - inner_r,
             cx + inner_r, cy + inner_r],
            fill='#555555'
        )
        # Center pin (gold)
        pin_r = max(1, int(1 * s))
        draw.ellipse(
            [cx - pin_r, cy - pin_r,
             cx + pin_r, cy + pin_r],
            fill='#CC9933'
        )
    
    # === VFO KNOB (right side) ===
    knob_center_x = radio_right - int(8 * s)
    knob_center_y = (radio_top + radio_bottom) // 2
    knob_radius = int(6 * s)
    
    draw.ellipse(
        [knob_center_x - knob_radius, knob_center_y - knob_radius,
         knob_center_x + knob_radius, knob_center_y + knob_radius],
        fill=knob_silver,
        outline='#3D3D3D',
        width=1
    )
    
    inner_radius = int(4 * s)
    draw.ellipse(
        [knob_center_x - inner_radius, knob_center_y - inner_radius,
         knob_center_x + inner_radius, knob_center_y + inner_radius],
        fill='#404040'
    )
    
    return img


def main():
    """Generate icon files at various sizes"""
    output_dir = Path(__file__).parent.parent / 'pmr_171_cps' / 'assets'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Main application icon (with PMR 171 text)
    icon = create_pmr171_icon(256)
    
    icon_path = output_dir / 'pmr171_cps.png'
    icon.save(icon_path, 'PNG')
    print(f"Created: {icon_path}")
    
    sizes = [16, 32, 48, 64, 128]
    for size in sizes:
        small_icon = create_pmr171_icon(size)
        small_path = output_dir / f'pmr171_cps_{size}.png'
        small_icon.save(small_path, 'PNG')
        print(f"Created: {small_path}")
    
    # Create properly embedded multi-resolution ICO file
    # Windows needs actual resized images at each size, not just metadata
    ico_path = output_dir / 'pmr171_cps.ico'
    ico_images = []
    for size in [16, 24, 32, 48, 64, 128, 256]:
        ico_images.append(create_pmr171_icon(size))
    
    # Save ICO with all sizes embedded (largest first as base)
    ico_images[-1].save(
        ico_path, 
        format='ICO',
        append_images=ico_images[:-1],
        sizes=[(img.width, img.height) for img in ico_images]
    )
    print(f"Created: {ico_path} (with {len(ico_images)} embedded sizes)")
    
    # Window icon (radio only, no text)
    window_icon = create_radio_only_icon(64)
    window_icon_path = output_dir / 'pmr171_radio.png'
    window_icon.save(window_icon_path, 'PNG')
    print(f"Created: {window_icon_path}")
    
    # Additional window icon sizes
    for size in [16, 32, 48]:
        small_window_icon = create_radio_only_icon(size)
        small_path = output_dir / f'pmr171_radio_{size}.png'
        small_window_icon.save(small_path, 'PNG')
        print(f"Created: {small_path}")
    
    # Create ICO file for radio-only icon (for Windows titlebar)
    # Windows uses ICO files with embedded multiple sizes for best quality
    radio_ico_path = output_dir / 'pmr171_radio.ico'
    # Create images at all standard ICO sizes
    radio_ico_images = []
    for size in [16, 32, 48, 64]:
        radio_ico_images.append(create_radio_only_icon(size))
    # Save with the largest image, specifying all sizes
    radio_ico_images[-1].save(
        radio_ico_path, 
        format='ICO', 
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
        append_images=radio_ico_images[:-1]
    )
    print(f"Created: {radio_ico_path}")
    
    print(f"\nIcon generation complete!")


if __name__ == '__main__':
    main()
