"""Radio programming GUI for channel data"""

import copy
import csv
import json
import logging
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ..utils.validation import (
    validate_channel, get_frequency_band_name, 
    truncate_channel_name, format_channel_name_for_storage,
    PMR171_MAX_CHANNEL_NAME_LENGTH
)

# Try to import UART radio interface
try:
    from ..radio.pmr171_uart import (
        PMR171Radio, PMR171Error, list_serial_ports,
        ChannelData, codeplug_to_channels, channels_to_codeplug,
        SERIAL_AVAILABLE
    )
except ImportError:
    SERIAL_AVAILABLE = False
    PMR171Radio = None


# Cohesive blue color palette for the GUI (MOTOTRBO CPS style)
BLUE_PALETTE = {
    'primary': '#0078D7',       # Primary blue - buttons, links (Windows blue)
    'primary_dark': '#005A9E',  # Darker blue - pressed states
    'header': '#00B0F0',        # Header cyan - section headers (MOTOTRBO style bright cyan)
    'header_dark': '#0099CC',   # Slightly darker cyan for gradients
    'hover': '#33CCFF',         # Hover cyan - button hover states (lighter cyan)
    'light': '#E0F7FF',         # Light cyan - tooltip background, highlights
    'lighter': '#F0FBFF',       # Very light cyan - subtle backgrounds
    'accent': '#0099FF',        # Accent blue - focus indicators
    'border': '#80D4FF',        # Border cyan - tooltip/popup borders
    'link': '#0066CC',          # Link blue - navigation links
    'selection': '#3399FF',     # Selection blue - selected items in lists
}


class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background=BLUE_PALETTE['light'], foreground="#003366",
                        relief=tk.SOLID, borderwidth=1,
                        font=('Arial', 9), padx=5, pady=3)
        label.pack()
    
    def hide_tooltip(self, event=None):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


class ChannelTableViewer:
    """Radio programming interface with tree navigation and tabbed detail view
    
    PMR-171 CPS (Customer Programming Software)
    Developed by Aram Dergevorkian (aram@aramd.net)
    """
    
    # Track if current data is unsaved (from fresh read or new file)
    _is_unsaved_fresh_read: bool = False
    
    MODE_NAMES = {
        0: "USB", 1: "LSB", 2: "CWR", 3: "CWL",
        4: "AM", 5: "WFM", 6: "NFM", 7: "DIGI",
        8: "PKT", 9: "DMR", 10: "?"
    }
    
    CHANNEL_TYPES = {0: "Analog", 1: "DMR"}
    SQUELCH_MODES = {0: "Carrier", 1: "CTCSS/DCS", 2: "Optional Signal"}
    POWER_LEVELS = {0: "Low", 1: "Medium", 2: "High", 3: "Turbo"}
    
    # Standard CTCSS/PL tones in Hz
    CTCSS_TONES = [
        "67.0", "71.9", "74.4", "77.0", "79.7", "82.5", "85.4", "88.5", "91.5",
        "94.8", "97.4", "100.0", "103.5", "107.2", "110.9", "114.8", "118.8",
        "123.0", "127.3", "131.8", "136.5", "141.3", "146.2", "151.4", "156.7",
        "162.2", "167.9", "173.8", "179.9", "186.2", "192.8", "203.5", "210.7",
        "218.1", "225.7", "233.6", "241.8", "250.3"
    ]
    
    # Standard DCS codes - D###N followed by D###R
    _DCS_BASE = [
        '023', '025', '026', '031', '032', '036', '043', '047', '051', '053',
        '054', '065', '071', '072', '073', '074', '114', '115', '116', '122',
        '125', '131', '132', '134', '143', '145', '152', '155', '156', '162',
        '165', '172', '174', '205', '212', '223', '225', '226', '243', '244',
        '245', '246', '251', '252', '255', '261', '263', '265', '266', '271',
        '274', '306', '311', '315', '325', '331', '332', '343', '346', '351',
        '356', '364', '365', '371', '411', '412', '413', '423', '431', '432',
        '445', '446', '452', '454', '455', '462', '464', '465', '466', '503',
        '506', '516', '523', '526', '532', '546', '565', '606', '612', '624',
        '627', '631', '632', '654', '662', '664', '703', '712', '723', '731',
        '732', '734', '743', '754'
    ]
    DCS_CODES = [f'D{code}N' for code in _DCS_BASE] + [f'D{code}R' for code in _DCS_BASE]
    
    # Combined CTCSS/DCS list for dropdowns: CTCSS tones, then D###N codes, then D###R codes
    CTCSS_DCS_COMBINED = ['Off'] + CTCSS_TONES + DCS_CODES
    
    def __init__(self, channels: Dict[str, Dict], title: str = "PMR-171 CPS"):
        """Initialize viewer
        
        Args:
            channels: Dictionary of channel data
            title: Window title
            radio_config: RadioConfig instance (defaults to PMR-171 if not specified)
        """
        self.channels = channels
        self.title = title
        self.current_file: Optional[Path] = None  # Track currently open file
        self.selected_channel: Optional[str] = None
        self.current_channel: Optional[str] = None  # Track current channel for updates
        self.root = None
        self.channel_tree = None
        self.detail_notebook = None
        
        # Undo/Redo stacks - each entry is a deep copy of self.channels
        self.undo_stack: List[Dict[str, Dict]] = []
        self.redo_stack: List[Dict[str, Dict]] = []
        self.max_undo_levels = 50  # Limit memory usage
        
        # Filter settings (initialized in show() after root window created)
        self.show_empty_channels = None
        self.group_by_type = None  # Separate Analog/DMR into groups (legacy name for compatibility)
        self.group_by_mode = None  # Group channels by modulation mode (NFM, AM, DMR, etc.)
        self.search_var = None  # Search filter text
        
        # Channel selection for read/write operations
        self.channel_checkboxes: Dict[str, tk.BooleanVar] = {}  # ch_id -> BooleanVar
        self.cancel_operation = False  # Flag for cancelling read/write
        
        # Available columns for tree view (ordered as desired)
        # Note: Tree column (#0) is used for R/W checkbox, 'ch' column shows channel number
        self.available_columns = {
            'ch': {'label': 'Ch', 'width': 50, 'extract': lambda ch: str(ch.get('channelLow', ''))},  # Channel number
            'name': {'label': 'Name', 'width': 120, 'extract': lambda ch: ch.get('channelName', '').rstrip('\u0000').strip() or "(empty)"},
            'rx_freq': {'label': 'RX Freq', 'width': 90, 'extract': lambda ch: self.freq_from_bytes(ch['vfoaFrequency1'], ch['vfoaFrequency2'], ch['vfoaFrequency3'], ch['vfoaFrequency4'])},
            'rx_ctcss': {'label': 'RX CTCSS/DCS', 'width': 90, 'extract': lambda ch: self.ctcss_dcs_from_value(ch.get('rxCtcss', 0))},
            'tx_freq': {'label': 'TX Freq', 'width': 90, 'extract': lambda ch: self.freq_from_bytes(ch['vfobFrequency1'], ch['vfobFrequency2'], ch['vfobFrequency3'], ch['vfobFrequency4'])},
            'tx_ctcss': {'label': 'TX CTCSS/DCS', 'width': 90, 'extract': lambda ch: self.ctcss_dcs_from_value(ch.get('txCtcss', ch.get('rxCtcss', 0)))},
            'mode': {'label': 'Mode', 'width': 60, 'extract': lambda ch: self.MODE_NAMES.get(ch.get('vfoaMode', 6), 'NFM')}
        }
        
        # Default selected columns (shown by default) - tree #0 is R/W checkbox
        self.selected_columns = ['ch', 'name', 'rx_freq', 'mode']
        
        # Style colors (using centralized palette)
        self.colors = {
            'header_bg': BLUE_PALETTE['header'],    # Header color
            'header_fg': 'white',
            'selected_bg': BLUE_PALETTE['primary'],  # Primary blue for selection
            'tree_bg': '#F0F0F0'
        }
    
    @staticmethod
    def freq_from_bytes(f1: int, f2: int, f3: int, f4: int) -> str:
        """Decode frequency from 4 bytes to MHz string"""
        freq_hz = struct.unpack('>I', bytes([f1, f2, f3, f4]))[0]
        freq_mhz = freq_hz / 1_000_000
        # Format with appropriate precision, flag out-of-range values
        if freq_mhz < 1 or freq_mhz > 1000:
            return f"{freq_mhz:.6f} ⚠"
        return f"{freq_mhz:.6f}"
    
    @staticmethod
    def ctcss_dcs_from_value(value: int) -> str:
        """Convert CTCSS/DCS value to display string"""
        if value == 0:
            return "Off"
        elif value >= 1000:
            # CTCSS tone
            return f"{value / 10:.1f}"
        else:
            # DCS code
            return str(value)
    
    def _ctcss_value_to_display(self, value: int) -> str:
        """Convert CTCSS/DCS integer value to dropdown-compatible display string
        
        PMR-171 format:
        - 0 = Off
        - 670-2503 = CTCSS tone (value / 10 = Hz, e.g., 1000 = 100.0 Hz)
        - DCS codes stored differently
        
        Args:
            value: Integer value from channel data
            
        Returns:
            Display string matching dropdown options (e.g., "Off", "100.0", "D023N")
        """
        if value == 0:
            return "Off"
        elif 670 <= value <= 2503:
            # CTCSS tone - convert to Hz string
            tone_hz = value / 10
            return f"{tone_hz:.1f}"
        else:
            # Try to match as DCS code or return raw value
            return str(value)
    
    @staticmethod
    def id_from_bytes(b1: int, b2: int, b3: int, b4: int) -> str:
        """Decode DMR ID from 4 bytes"""
        if b1 == 0 and b2 == 0 and b3 == 0 and b4 == 0:
            return "-"
        dmr_id = struct.unpack('>I', bytes([b1, b2, b3, b4]))[0]
        return str(dmr_id)
    
    @staticmethod
    def format_frequency(freq_str: str) -> str:
        """Format frequency string to standard MHz format (XXX.XXXXXX)
        
        Args:
            freq_str: Frequency as string (may have various formats)
            
        Returns:
            Formatted frequency string with 6 decimal places
        """
        try:
            # Remove any trailing warning symbols
            freq_str = freq_str.replace(' ⚠', '').strip()
            # Parse the frequency
            freq_mhz = float(freq_str)
            # Format with 6 decimal places (MHz.kHz Hz)
            return f"{freq_mhz:.6f}"
        except (ValueError, AttributeError):
            # If parsing fails, return original
            return freq_str
    
    @staticmethod
    def get_standard_offset(freq_mhz: float) -> float:
        """Get standard repeater offset for a given frequency in MHz
        
        Based on RadioReference wiki with extended ranges for VHF (30-300 MHz)
        and UHF (300-3000 MHz) bands.
        
        Args:
            freq_mhz: Frequency in MHz
            
        Returns:
            Standard offset in MHz (positive or negative)
        """
        # ===== VHF BAND (30-300 MHz) =====
        
        # 10m / Low VHF (29-54 MHz): -0.5 MHz default
        if 29 <= freq_mhz < 54:
            return -0.5
        
        # Mid VHF (54-148 MHz): +0.6 MHz (2m standard)
        # Covers VHF-Lo public safety, NOAA weather (162 MHz area), etc.
        if 54 <= freq_mhz < 148:
            return 0.6
        
        # 2m Ham and VHF High (148-174 MHz): +0.6 MHz
        # Includes NOAA weather (162.xxx), MURS, business band
        if 148 <= freq_mhz < 174:
            return 0.6
        
        # VHF High (174-216 MHz): +0.6 MHz (TV broadcast, but use VHF standard)
        if 174 <= freq_mhz < 216:
            return 0.6
        
        # 220-225 MHz (1.25m): -1.6 MHz
        if 216 <= freq_mhz < 225:
            return -1.6
        
        # Upper VHF (225-300 MHz): +1.0 MHz (military air, etc.)
        if 225 <= freq_mhz < 300:
            return 1.0
        
        # ===== UHF BAND (300-3000 MHz) =====
        
        # Lower UHF (300-406 MHz): +5.0 MHz
        if 300 <= freq_mhz < 406:
            return 5.0
        
        # Federal UHF (406-420 MHz): +9 MHz
        if 406 <= freq_mhz < 420:
            return 9.0
        
        # 70cm Ham and UHF (420-512 MHz): +5 MHz
        if 420 <= freq_mhz < 512:
            return 5.0
        
        # UHF 512-698 MHz: +5 MHz
        if 512 <= freq_mhz < 698:
            return 5.0
        
        # 700 MHz (698-806 MHz): +30 MHz
        if 698 <= freq_mhz < 806:
            return 30.0
        
        # 800 MHz (806-896 MHz): -45 MHz
        if 806 <= freq_mhz < 896:
            return -45.0
        
        # 900 MHz (896-960 MHz): -39 MHz
        if 896 <= freq_mhz < 960:
            return -39.0
        
        # 33cm / 900 MHz+ (960-1300 MHz): -12 MHz
        if 960 <= freq_mhz < 1300:
            return -12.0
        
        # Upper microwave (1300-3000 MHz): -12 MHz default
        if 1300 <= freq_mhz <= 3000:
            return -12.0
        
        # Outside typical amateur/commercial bands
        return 0.0
    
    def show(self):
        """Display the radio programming interface
        
        Can be launched with empty channels - user can open files or read from radio.
        """
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("1600x900")
        
        # Start maximized (cross-platform)
        try:
            self.root.state('zoomed')  # Windows
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)  # Linux
            except tk.TclError:
                pass  # Fallback to default geometry if maximizing fails
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / 'assets' / 'pmr171_cps.png'
        if icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
            except:
                pass  # Icon loading failed, continue without it
        
        # Create menu bar
        self._create_menu_bar()
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Header.TLabel', 
                       background=self.colors['header_bg'],
                       foreground=self.colors['header_fg'],
                       font=('Arial', 10, 'bold'),
                       padding=8)
        
        # Configure checkbox styles for better visual indication
        # Default (unselected) state - gray indicator box
        style.configure('Toggle.TCheckbutton',
                       font=('Arial', 9))
        style.map('Toggle.TCheckbutton',
                 indicatorcolor=[('selected', BLUE_PALETTE['primary']), ('!selected', '#FFFFFF')],
                 indicatorrelief=[('selected', 'flat'), ('!selected', 'sunken')],
                 background=[('active', BLUE_PALETTE['lighter'])])
        
        # Configure notebook styling with visible border
        style.configure('TNotebook', borderwidth=2, relief='solid')
        style.configure('TNotebook.Tab', padding=[8, 4])

        # === CPS-STYLE TOOLBAR (Green buttons like MOTOTRBO CPS 2.0) ===
        self._create_cps_toolbar()
        
        # === FILE IDENTIFIER LABEL (shows filename like CPS shows serial number) ===
        self._create_file_identifier()

        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # LEFT PANEL: Tree navigation
        left_frame = ttk.Frame(main_paned, width=300)
        self._create_tree_navigation(left_frame)
        main_paned.add(left_frame, weight=1)
        
        # RIGHT PANEL: Tabbed detail view
        right_frame = ttk.Frame(main_paned)
        self._create_detail_panel(right_frame)
        main_paned.add(right_frame, weight=3)
        
        # Status bar
        self._create_status_bar()
        
        # Start GUI
        self.root.mainloop()
    
    def _create_cps_toolbar(self):
        """Create CPS-style toolbar with blue buttons"""
        # Toolbar frame with gray background
        toolbar_frame = tk.Frame(self.root, bg='#F0F0F0', height=80)
        toolbar_frame.pack(fill=tk.X, side=tk.TOP)
        toolbar_frame.pack_propagate(False)  # Fixed height
        
        # Inner frame with padding
        inner_frame = tk.Frame(toolbar_frame, bg='#F0F0F0')
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Button style - blue background using centralized palette
        button_bg = BLUE_PALETTE['primary']
        button_fg = 'white'
        button_font = ('Arial', 9)
        icon_font = ('Arial', 16)
        btn_width = 75
        btn_height = 60
        
        def create_cps_button(parent, icon_text, label_text, command, tooltip_text):
            """Create a CPS-style button with icon and label, centered content"""
            btn_frame = tk.Frame(parent, bg=button_bg, width=btn_width, height=btn_height,
                               relief=tk.RAISED, bd=2)
            btn_frame.pack(side=tk.LEFT, padx=3)
            btn_frame.pack_propagate(False)
            
            # Center container to hold icon and label
            center_frame = tk.Frame(btn_frame, bg=button_bg)
            center_frame.place(relx=0.5, rely=0.5, anchor='center')
            
            # Icon label (centered)
            icon_label = tk.Label(center_frame, text=icon_text, font=icon_font, 
                                bg=button_bg, fg=button_fg)
            icon_label.pack()
            
            # Text label (centered)
            text_label = tk.Label(center_frame, text=label_text, font=button_font,
                                bg=button_bg, fg=button_fg)
            text_label.pack()
            
            # Store command reference on btn_frame for consistent access
            btn_frame.command = command
            
            # Click handler that works on any part of the button
            def on_click(event):
                command()
            
            # Bind click events to all parts including btn_frame
            btn_frame.bind('<Button-1>', on_click)
            center_frame.bind('<Button-1>', on_click)
            icon_label.bind('<Button-1>', on_click)
            text_label.bind('<Button-1>', on_click)
            
            # Also bind to ButtonRelease for more reliable clicking
            btn_frame.bind('<ButtonRelease-1>', lambda e: None)  # Prevent event propagation issues
            
            # Bind hover events to btn_frame and propagate to children
            def on_enter(event):
                self._on_cps_button_enter(btn_frame)
            def on_leave(event):
                self._on_cps_button_leave(btn_frame, button_bg)
            
            btn_frame.bind('<Enter>', on_enter)
            btn_frame.bind('<Leave>', on_leave)
            
            # Add tooltip
            ToolTip(btn_frame, tooltip_text)
            
            return btn_frame
        
        # File operations group
        create_cps_button(inner_frame, "📂", "Open", self._open_file, "Open JSON file (Ctrl+O)")
        create_cps_button(inner_frame, "💾", "Save", self._save_file, "Save JSON file (Ctrl+S)")
        
        # Separator
        sep_frame = tk.Frame(inner_frame, width=2, bg='#CCCCCC')
        sep_frame.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=5)
        
        # Radio operations group (Read/Write - placeholder for UART programming)
        # Icons: Radio with arrows showing data direction
        # Read = data flows FROM radio (right arrow pointing out)
        # Write = data flows TO radio (left arrow pointing in)
        self.read_btn = create_cps_button(inner_frame, "📻➡", "Read", self._read_from_radio, 
                                         "Read from radio (download codeplug) (Ctrl+R)")
        self.write_btn = create_cps_button(inner_frame, "📻⬅", "Write", self._write_to_radio,
                                          "Write to radio (upload codeplug) (Ctrl+W)")
    
    def _on_cps_button_enter(self, btn_frame):
        """Handle mouse enter on CPS button (hover effect)"""
        hover_color = BLUE_PALETTE['hover']  # Light blue on hover
        btn_frame.config(bg=hover_color)
        # Update all children recursively
        def update_children(widget, color):
            for child in widget.winfo_children():
                try:
                    child.config(bg=color)
                except:
                    pass
                update_children(child, color)
        update_children(btn_frame, hover_color)
    
    def _on_cps_button_leave(self, btn_frame, original_bg):
        """Handle mouse leave on CPS button"""
        btn_frame.config(bg=original_bg)
        # Update all children recursively
        def update_children(widget, color):
            for child in widget.winfo_children():
                try:
                    child.config(bg=color)
                except:
                    pass
                update_children(child, color)
        update_children(btn_frame, original_bg)
    
    def _create_file_identifier(self):
        """Update window title to show current file (no separate banner)"""
        # File identifier is now shown in window title only
        # Update title with filename if available
        if self.current_file:
            self.root.title(f"{self.title} - {self.current_file.name}")
        else:
            self.root.title(self.title)
    
    def _update_file_identifier(self, filepath: Path = None):
        """Update the window title with current filename"""
        self.current_file = filepath
        if filepath:
            self.root.title(f"{self.title} - {filepath.name}")
        else:
            self.root.title(self.title)
    
    def _read_from_radio(self):
        """Read codeplug from radio via UART (selective or all channels)
        
        Shows a dialog to select which channels to read, then reads directly
        into the current codeplug.
        """
        logger.info("=== _read_from_radio() called ===")
        
        if not SERIAL_AVAILABLE:
            logger.error("pyserial not available")
            messagebox.showerror(
                "pyserial Not Installed",
                "The pyserial library is required for radio programming.\n\n"
                "Install it with:\n"
                "    pip install pyserial",
                parent=self.root
            )
            return
        
        # Show serial port selection dialog
        port = self._select_serial_port("Read from Radio")
        if not port:
            logger.info("User cancelled port selection")
            return
        
        logger.info(f"Selected port: {port}")
        
        # Check if specific channels are selected in the R/W Selection panel
        selected_ids = self._get_selected_channel_ids()
        selected_count = len(selected_ids)
        logger.info(f"Selected channel IDs for read: {selected_ids[:10]}... (total: {selected_count})")
        
        # Show read destination dialog (channel range + where to save)
        read_options = self._show_read_destination_dialog(selected_count)
        if not read_options:
            logger.info("User cancelled read destination dialog")
            return
        
        read_mode = read_options['read_mode']
        to_new_file = read_options['to_new_file']
        new_filepath = read_options.get('filepath')
        logger.info(f"User selected read mode: {read_mode}, to_new_file: {to_new_file}")
        
        # Determine channels to read based on mode
        if read_mode == 'selected':
            # Read only selected channels
            channel_indices = [int(ch_id) for ch_id in selected_ids if ch_id.isdigit()]
            total_channels = len(channel_indices)
        elif read_mode == 'first50':
            # Read first 50 channels
            channel_indices = list(range(50))
            total_channels = 50
        else:  # 'all'
            # Read all 1000 channels
            channel_indices = None
            total_channels = 1000
        
        logger.info(f"Read mode: {read_mode}, total_channels: {total_channels}")
        
        # Create progress dialog
        progress_dialog = self._create_progress_dialog("Reading from Radio", total_channels)
        
        try:
            logger.info(f"Connecting to radio on {port}...")
            radio = PMR171Radio(port)
            radio.connect()
            logger.info("Connected to radio")
            
            def progress_callback(current, total, message):
                progress_dialog['var'].set(current)
                progress_dialog['label'].config(text=message)
                progress_dialog['dialog'].update()
            
            def cancel_check():
                return self.cancel_operation
            
            # Read channels based on mode
            if read_mode in ('selected', 'first50'):
                logger.info(f"Reading {len(channel_indices)} selected/first50 channels...")
                # Selected or first 50 - use read_selected_channels with specific indices
                channels_read = radio.read_selected_channels(
                    channel_indices, progress_callback, cancel_check)
                was_cancelled = self.cancel_operation
                radio.disconnect()
                
                logger.info(f"Read complete. Channels read: {len(channels_read)}, was_cancelled: {was_cancelled}")
                
                # Close progress dialog
                progress_dialog['dialog'].destroy()
                
                if was_cancelled:
                    messagebox.showinfo(
                        "Read Cancelled",
                        f"Read operation cancelled.\n"
                        f"Read {len(channels_read)} of {total_channels} selected channels.",
                        parent=self.root
                    )
                
                if channels_read:
                    logger.info(f"Processing {len(channels_read)} read channels...")
                    
                    # Log first few channels for debugging
                    for i, ch in enumerate(channels_read[:5]):
                        logger.debug(f"  Channel {ch.index}: rx_freq={ch.rx_freq_mhz:.6f} MHz, name='{ch.name}'")
                    
                    # Save state for undo
                    self._save_state("Read selected channels from radio")
                    logger.info("Saved undo state")
                    
                    # Handle destination: new codeplug vs update current
                    if to_new_file:
                        logger.info("Creating fresh codeplug (to_new_file=True)")
                        # Create fresh codeplug with only the read channels
                        self.channels = {}
                        
                        # Set a default filename for fresh reads
                        now = datetime.now()
                        suggested_filename = f"radio_readback_{now.strftime('%y%m%d_%H%M')}.json"
                        suggested_path = Path(__file__).parent.parent.parent / suggested_filename
                        self._update_file_identifier(suggested_path)
                        self._is_unsaved_fresh_read = True
                        logger.info(f"Set suggested filename for fresh read: {suggested_filename}")
                    else:
                        logger.info(f"Updating current codeplug (self.channels has {len(self.channels)} channels)")
                    
                    # Add/update the read channels
                    for ch in channels_read:
                        ch_key = str(ch.index)
                        new_data = ch.to_dict()
                        if not to_new_file and ch_key in self.channels:
                            # Debug logging for updates
                            old_freq = (
                                (self.channels[ch_key].get('vfoaFrequency1', 0) << 24) |
                                (self.channels[ch_key].get('vfoaFrequency2', 0) << 16) |
                                (self.channels[ch_key].get('vfoaFrequency3', 0) << 8) |
                                self.channels[ch_key].get('vfoaFrequency4', 0)
                            )
                            new_freq = (
                                (new_data.get('vfoaFrequency1', 0) << 24) |
                                (new_data.get('vfoaFrequency2', 0) << 16) |
                                (new_data.get('vfoaFrequency3', 0) << 8) |
                                new_data.get('vfoaFrequency4', 0)
                            )
                            logger.info(f"Channel {ch_key}: Old freq={old_freq/1e6:.6f} MHz -> New freq={new_freq/1e6:.6f} MHz")
                        else:
                            logger.info(f"Channel {ch_key}: Adding channel")
                        self.channels[ch_key] = new_data
                    
                    logger.info(f"After update, self.channels has {len(self.channels)} channels")
                    
                    # Clear current channel to force re-selection
                    old_channel = self.current_channel
                    self.current_channel = None
                    logger.info(f"Reset current_channel from {old_channel} to None")
                    
                    # Rebuild tree - this will auto-select first channel
                    logger.info("Rebuilding channel tree...")
                    self._rebuild_channel_tree()
                    logger.info("Channel tree rebuilt")
                    
                    # Now explicitly select and display the originally selected channel
                    if old_channel and old_channel in self.channels:
                        logger.info(f"Re-selecting previous channel {old_channel}")
                        # Find the tree item for this channel and select it
                        for item in self._get_all_channel_items():
                            tags = self.channel_tree.item(item, 'tags')
                            if tags and tags[0] == old_channel:
                                self.channel_tree.selection_set(item)
                                self.channel_tree.focus(item)
                                self.channel_tree.see(item)
                                # Manually update current_channel and populate tabs
                                self.current_channel = old_channel
                                ch_data = self.channels[old_channel]
                                ch_name = ch_data['channelName'].rstrip('\u0000').strip() or "(empty)"
                                self.detail_header.config(text=f"Channel {old_channel} - {ch_name}")
                                self._populate_general_tab(ch_data)
                                self._populate_freq_tab(ch_data)
                                self._populate_dmr_tab(ch_data)
                                self._populate_advanced_tab(ch_data)
                                self._populate_raw_tab(ch_data)
                                logger.info(f"Re-selected and populated channel {old_channel}")
                                break
                    
                    if not was_cancelled:
                        messagebox.showinfo(
                            "Read Complete",
                            f"Successfully read {len(channels_read)} channels from radio.",
                            parent=self.root
                        )
                    self.status_label.config(text=f"Read {len(channels_read)} channels from radio")
                else:
                    logger.warning("No channels were read from radio!")
            else:
                # Read all channels
                logger.info("Reading ALL 1000 channels...")
                from ..radio.pmr171_uart import channels_to_codeplug
                channels_read = radio.read_all_channels(
                    progress_callback, include_empty=True, cancel_check=cancel_check)
                was_cancelled = self.cancel_operation
                radio.disconnect()
                
                logger.info(f"Read complete. Channels read: {len(channels_read)}, was_cancelled: {was_cancelled}")
                
                # Close progress dialog
                progress_dialog['dialog'].destroy()
                
                if was_cancelled:
                    messagebox.showinfo(
                        "Read Cancelled",
                        f"Read operation cancelled.\n"
                        f"Read {len(channels_read)} of 1000 channels.",
                        parent=self.root
                    )
                
                if channels_read:
                    logger.info(f"Converting {len(channels_read)} channels to codeplug format...")
                    # Convert to codeplug format
                    codeplug = channels_to_codeplug(channels_read)
                    logger.info(f"Codeplug created with {len(codeplug)} channels")
                    
                    # Count non-empty channels
                    non_empty = sum(1 for ch in codeplug.values() 
                                  if ch.get('vfoaMode', 255) != 255 and 
                                  (ch.get('vfoaFrequency1', 0) != 0 or ch.get('vfoaFrequency2', 0) != 0))
                    logger.info(f"Non-empty channels: {non_empty}")
                    
                    # Update current codeplug directly
                    logger.info("Updating current codeplug with read data")
                    self._save_state("Read from radio")
                    logger.info("Saved undo state")
                    
                    logger.info(f"Replacing self.channels (was {len(self.channels)}) with codeplug ({len(codeplug)})")
                    self.channels = codeplug
                    self.current_channel = None
                    
                    # Set a default filename for fresh reads (user will choose when saving)
                    now = datetime.now()
                    suggested_filename = f"radio_readback_{now.strftime('%y%m%d_%H%M')}.json"
                    suggested_path = Path(__file__).parent.parent.parent / suggested_filename
                    self._update_file_identifier(suggested_path)
                    self._is_unsaved_fresh_read = True  # Mark as unsaved fresh read
                    logger.info(f"Set suggested filename for fresh read: {suggested_filename}")
                    
                    # Rebuild tree
                    logger.info("Rebuilding channel tree...")
                    self._rebuild_channel_tree()
                    logger.info("Channel tree rebuilt")
                    
                    if not was_cancelled:
                        messagebox.showinfo(
                            "Read Complete",
                            f"Successfully read {len(codeplug)} channels from radio.\n"
                            f"({non_empty} programmed, {len(codeplug) - non_empty} empty)\n\n"
                            f"Use File > Save to save this data.",
                            parent=self.root
                        )
                    self.status_label.config(text=f"Read {len(codeplug)} channels from radio")
                else:
                    logger.warning("No channels were read from radio!")
            
            logger.info("=== _read_from_radio() completed successfully ===")
            
        except PMR171Error as e:
            logger.error(f"PMR171Error: {e}")
            progress_dialog['dialog'].destroy()
            messagebox.showerror("Read Error", f"Failed to read from radio:\n\n{e}", parent=self.root)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            progress_dialog['dialog'].destroy()
            messagebox.showerror("Error", f"Unexpected error:\n\n{e}", parent=self.root)
    
    def _write_to_radio(self):
        """Write codeplug to radio via UART (selective or all channels)"""
        if not SERIAL_AVAILABLE:
            messagebox.showerror(
                "pyserial Not Installed",
                "The pyserial library is required for radio programming.\n\n"
                "Install it with:\n"
                "    pip install pyserial",
                parent=self.root
            )
            return
        
        if not self.channels:
            messagebox.showwarning(
                "No Channels",
                "No channel data to write. Please load or create channels first.",
                parent=self.root
            )
            return
        
        # Show serial port selection dialog
        port = self._select_serial_port("Write to Radio")
        if not port:
            return
        
        # Check if specific channels are selected
        selected_ids = self._get_selected_channel_ids()
        selected_count = len(selected_ids)
        
        # Determine write mode
        if selected_count > 0:
            # Selective write
            result = messagebox.askyesnocancel(
                "Write Mode",
                f"You have {selected_count} channels selected for writing.\n\n"
                "Yes = Write only selected channels\n"
                "No = Write ALL channels in codeplug\n"
                "Cancel = Abort",
                parent=self.root
            )
            if result is None:
                return
            write_selected_only = result
        else:
            # No selection - write all
            programmed = sum(1 for ch in self.channels.values() 
                            if ch.get('vfoaMode', 255) != 255)
            result = messagebox.askyesno(
                "Confirm Write",
                f"Write all {len(self.channels)} channels ({programmed} programmed) to radio on {port}?\n\n"
                "⚠️ WARNING: This will overwrite channels on the radio!\n\n"
                "Make sure:\n"
                "• The radio is connected and powered on\n"
                "• You have a backup of your current radio configuration\n"
                "• The channel data has been validated\n\n"
                "Tip: Use the selection tools to write specific channels only.",
                parent=self.root
            )
            if not result:
                return
            write_selected_only = False
        
        # Build list of channels to write
        if write_selected_only:
            channels_to_write = []
            for ch_id in selected_ids:
                if ch_id in self.channels:
                    channels_to_write.append(ChannelData.from_dict(self.channels[ch_id]))
            total_channels = len(channels_to_write)
        else:
            channels_to_write = codeplug_to_channels(self.channels)
            total_channels = len(channels_to_write)
        
        # Create progress dialog
        progress_dialog = self._create_progress_dialog("Writing to Radio", total_channels)
        
        try:
            radio = PMR171Radio(port)
            radio.connect()
            
            def progress_callback(current, total, message):
                progress_dialog['var'].set(current)
                progress_dialog['label'].config(text=message)
                progress_dialog['dialog'].update()
            
            def cancel_check():
                return self.cancel_operation
            
            # Write channels
            success_count = radio.write_all_channels(
                channels_to_write, progress_callback, cancel_check)
            was_cancelled = self.cancel_operation
            radio.disconnect()
            
            # Close progress dialog
            progress_dialog['dialog'].destroy()
            
            if was_cancelled:
                messagebox.showinfo(
                    "Write Cancelled",
                    f"Write operation cancelled.\n"
                    f"Wrote {success_count} of {total_channels} channels.",
                    parent=self.root
                )
            else:
                mode_str = "selected" if write_selected_only else "total"
                messagebox.showinfo(
                    "Write Complete",
                    f"Successfully wrote {success_count} of {total_channels} {mode_str} channels to radio.",
                    parent=self.root
                )
            self.status_label.config(text=f"Wrote {success_count} channels to radio")
            
        except PMR171Error as e:
            progress_dialog['dialog'].destroy()
            messagebox.showerror("Write Error", f"Failed to write to radio:\n\n{e}", parent=self.root)
        except Exception as e:
            progress_dialog['dialog'].destroy()
            messagebox.showerror("Error", f"Unexpected error:\n\n{e}", parent=self.root)
    
    def _select_serial_port(self, title: str) -> Optional[str]:
        """Show dialog to select a serial port
        
        Args:
            title: Dialog title
            
        Returns:
            Selected port name or None if cancelled
        """
        ports = list_serial_ports()
        
        if not ports:
            messagebox.showwarning(
                "No Serial Ports",
                "No serial ports found.\n\n"
                "Please connect the programming cable and try again.",
                parent=self.root
            )
            return None
        
        # Create port selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header_frame = tk.Frame(dialog, bg=BLUE_PALETTE['header'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text="Select Serial Port", font=('Arial', 11, 'bold'),
                bg=BLUE_PALETTE['header'], fg='white').pack(side=tk.LEFT, padx=10, pady=8)
        
        # Port list frame
        list_frame = ttk.Frame(dialog, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox with ports
        port_listbox = tk.Listbox(list_frame, font=('Consolas', 10),
                                 yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        port_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=port_listbox.yview)
        
        # Add ports to listbox
        for port_info in ports:
            display = f"{port_info['port']} - {port_info['description']}"
            port_listbox.insert(tk.END, display)
        
        # Select first port by default
        if ports:
            port_listbox.selection_set(0)
        
        # Result holder
        selected_port = {'value': None}
        
        # Button frame
        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            selection = port_listbox.curselection()
            if selection:
                selected_port['value'] = ports[selection[0]]['port']
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        def on_double_click(event):
            on_ok()
        
        port_listbox.bind('<Double-Button-1>', on_double_click)
        port_listbox.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Return>', lambda e: on_ok())
        
        ttk.Button(button_frame, text="Connect", command=on_ok, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", 
                  command=lambda: self._refresh_port_list(port_listbox, ports), width=12).pack(side=tk.RIGHT, padx=5)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog to close
        self.root.wait_window(dialog)
        
        return selected_port['value']
    
    def _refresh_port_list(self, listbox: tk.Listbox, ports: list):
        """Refresh the serial port list"""
        new_ports = list_serial_ports()
        ports.clear()
        ports.extend(new_ports)
        
        listbox.delete(0, tk.END)
        for port_info in new_ports:
            display = f"{port_info['port']} - {port_info['description']}"
            listbox.insert(tk.END, display)
        
        if new_ports:
            listbox.selection_set(0)
    
    def _show_read_destination_dialog(self, selected_count: int) -> Optional[dict]:
        """Show dialog to select which channels to read and where to put the data
        
        Args:
            selected_count: Number of channels currently selected
            
        Returns:
            Dictionary with 'read_mode' and 'to_new_file' keys, or None if cancelled
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Read from Radio")
        dialog.geometry("500x520")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Header
        header_frame = tk.Frame(dialog, bg=BLUE_PALETTE['header'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text="Read from Radio - Options", font=('Arial', 11, 'bold'),
                bg=BLUE_PALETTE['header'], fg='white').pack(side=tk.LEFT, padx=10, pady=8)
        
        # Content
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Result holder
        result = {'value': None}
        
        # === Channel Range Selection ===
        ttk.Label(content, text="Which channels to read:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Default selection based on whether channels are selected
        if selected_count > 0:
            default_range = 'selected'
        else:
            default_range = 'first50'  # Default to first 50 for faster reads
        
        range_var = tk.StringVar(value=default_range)
        
        range_frame = ttk.Frame(content)
        range_frame.pack(fill=tk.X, pady=5)
        
        # Option: Selected channels (always show, but indicate count)
        selected_text = f"Read {selected_count} selected channel(s)" if selected_count > 0 else "Read selected channels (0 selected)"
        selected_rb = ttk.Radiobutton(range_frame, 
            text=selected_text, 
            variable=range_var, value='selected')
        selected_rb.pack(anchor='w', padx=10, pady=3)
        
        selected_desc = ttk.Label(range_frame,
            text="    Only reads channels you've checked (☑) in the channel list.",
            font=('Arial', 9), foreground='#666666')
        selected_desc.pack(anchor='w', padx=10)
        
        # Disable selected option if no channels are selected
        if selected_count == 0:
            selected_rb.config(state='disabled')
        
        # Option: First 50 channels (quick read)
        first50_rb = ttk.Radiobutton(range_frame, text="Read first 50 channels (quick)", 
                                     variable=range_var, value='first50')
        first50_rb.pack(anchor='w', padx=10, pady=(8, 3))
        
        first50_desc = ttk.Label(range_frame,
            text="    Fast option - reads channels 0-49 only.",
            font=('Arial', 9), foreground='#666666')
        first50_desc.pack(anchor='w', padx=10)
        
        # Option: All 1000 channels
        all_rb = ttk.Radiobutton(range_frame, text="Read ALL 1000 channels (full backup)", 
                                 variable=range_var, value='all')
        all_rb.pack(anchor='w', padx=10, pady=(8, 3))
        
        all_desc = ttk.Label(range_frame,
            text="    Complete backup - takes several minutes.",
            font=('Arial', 9), foreground='#666666')
        all_desc.pack(anchor='w', padx=10)
        
        # === Destination Selection ===
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        ttk.Label(content, text="Where to put the data:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        dest_var = tk.StringVar(value='new_file')  # Default to new file for safety
        
        dest_frame = ttk.Frame(content)
        dest_frame.pack(fill=tk.X, pady=5)
        
        # Option 1: New file (creates fresh codeplug in memory)
        new_file_rb = ttk.Radiobutton(dest_frame, text="Read to NEW codeplug (recommended)", 
                                       variable=dest_var, value='new_file')
        new_file_rb.pack(anchor='w', padx=10, pady=3)
        
        new_file_desc = ttk.Label(dest_frame, 
            text="    Creates a fresh codeplug with only the radio data.\n"
                 "    Your currently open file is NOT modified until you Save.",
            font=('Arial', 9), foreground='#666666')
        new_file_desc.pack(anchor='w', padx=10)
        
        # Option 2: Update current (if file is open)
        current_file_name = self.current_file.name if self.current_file else "(no file open)"
        update_rb = ttk.Radiobutton(dest_frame, 
            text=f"Update current codeplug ({current_file_name})", 
            variable=dest_var, value='update_current')
        update_rb.pack(anchor='w', padx=10, pady=(8, 3))
        
        update_desc = ttk.Label(dest_frame, 
            text="    Replaces channel data in the currently open codeplug.\n"
                 "    Changes can be undone with Edit > Undo.",
            font=('Arial', 9), foreground='#666666')
        update_desc.pack(anchor='w', padx=10)
        
        # Button frame with LARGE prominent Start Read button
        button_frame = tk.Frame(dialog, bg='#E8E8E8', pady=15)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def on_start_read():
            read_mode = range_var.get()  # 'selected', 'first50', or 'all'
            to_new_file = (dest_var.get() == 'new_file')
            result['value'] = {
                'read_mode': read_mode,
                'to_new_file': to_new_file,
                'filepath': None  # No file created yet - just in memory
            }
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # LARGE prominent Start Read button
        start_btn = tk.Button(button_frame, text="📻  Start Read", command=on_start_read, 
                             width=20, height=2, font=('Arial', 12, 'bold'),
                             bg=BLUE_PALETTE['primary'], fg='white',
                             activebackground=BLUE_PALETTE['primary_dark'], activeforeground='white',
                             cursor='hand2')
        start_btn.pack(side=tk.LEFT, padx=15)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, 
                              width=12, height=2, font=('Arial', 10))
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog
        self.root.wait_window(dialog)
        
        return result['value']
    
    def _show_read_options_dialog(self, selected_count: int) -> Optional[dict]:
        """Show dialog to select which channels to read
        
        Args:
            selected_count: Number of channels currently selected in R/W Selection panel
            
        Returns:
            Dictionary with 'read_mode' key ('selected', 'first50', or 'all'), 
            or None if cancelled
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Read from Radio")
        dialog.geometry("450x320")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Header
        header_frame = tk.Frame(dialog, bg=BLUE_PALETTE['header'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text="Read from Radio - Select Channels", font=('Arial', 11, 'bold'),
                bg=BLUE_PALETTE['header'], fg='white').pack(side=tk.LEFT, padx=10, pady=8)
        
        # Content
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Result holder
        result = {'value': None}
        
        # === Channel Range Selection ===
        ttk.Label(content, text="Which channels to read:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Default selection based on whether channels are selected
        if selected_count > 0:
            default_range = 'selected'
        else:
            default_range = 'first50'  # Default to first 50 for faster reads
        
        range_var = tk.StringVar(value=default_range)
        
        range_frame = ttk.Frame(content)
        range_frame.pack(fill=tk.X, pady=5)
        
        # Option: Selected channels (always show, but indicate count)
        selected_text = f"Read {selected_count} selected channel(s)" if selected_count > 0 else "Read selected channels (0 selected)"
        selected_rb = ttk.Radiobutton(range_frame, 
            text=selected_text, 
            variable=range_var, value='selected')
        selected_rb.pack(anchor='w', padx=10, pady=3)
        
        selected_desc = ttk.Label(range_frame,
            text="    Only reads channels you've checked (☑) in the channel list.",
            font=('Arial', 9), foreground='#666666')
        selected_desc.pack(anchor='w', padx=10)
        
        # Disable selected option if no channels are selected
        if selected_count == 0:
            selected_rb.config(state='disabled')
        
        # Option: First 50 channels (quick read)
        first50_rb = ttk.Radiobutton(range_frame, text="Read first 50 channels (quick)", 
                                     variable=range_var, value='first50')
        first50_rb.pack(anchor='w', padx=10, pady=(8, 3))
        
        first50_desc = ttk.Label(range_frame,
            text="    Fast option - reads channels 0-49 only.",
            font=('Arial', 9), foreground='#666666')
        first50_desc.pack(anchor='w', padx=10)
        
        # Option: All 1000 channels
        all_rb = ttk.Radiobutton(range_frame, text="Read ALL 1000 channels (full backup)", 
                                 variable=range_var, value='all')
        all_rb.pack(anchor='w', padx=10, pady=(8, 3))
        
        all_desc = ttk.Label(range_frame,
            text="    Complete backup - takes several minutes.",
            font=('Arial', 9), foreground='#666666')
        all_desc.pack(anchor='w', padx=10)
        
        # Button frame
        button_frame = tk.Frame(dialog, bg='#E8E8E8', pady=15)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def on_start_read():
            read_mode = range_var.get()  # 'selected', 'first50', or 'all'
            result['value'] = {'read_mode': read_mode}
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Start Read button
        start_btn = tk.Button(button_frame, text="📻  Start Read", command=on_start_read, 
                             width=18, height=2, font=('Arial', 11, 'bold'),
                             bg=BLUE_PALETTE['primary'], fg='white',
                             activebackground=BLUE_PALETTE['primary_dark'], activeforeground='white',
                             cursor='hand2')
        start_btn.pack(side=tk.LEFT, padx=15)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, 
                              width=10, height=2, font=('Arial', 10))
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog
        self.root.wait_window(dialog)
        
        return result['value']
    
    def _create_progress_dialog(self, title: str, total: int) -> dict:
        """Create a progress dialog for long operations with Cancel button
        
        Args:
            title: Dialog title
            total: Total number of steps
            
        Returns:
            Dictionary with 'dialog', 'var', 'bar', 'label', 'cancelled' keys
        """
        # Reset cancel flag
        self.cancel_operation = False
        
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Prevent closing via X button during operation
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Header
        header_frame = tk.Frame(dialog, bg=BLUE_PALETTE['header'], height=30)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text=title, font=('Arial', 10, 'bold'),
                bg=BLUE_PALETTE['header'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        
        # Progress content
        content = ttk.Frame(dialog, padding=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Progress variable and bar
        progress_var = tk.IntVar(value=0)
        progress_bar = ttk.Progressbar(content, variable=progress_var, maximum=total, length=350)
        progress_bar.pack(fill=tk.X, pady=5)
        
        # Status label
        status_label = ttk.Label(content, text="Starting...", font=('Arial', 9))
        status_label.pack(anchor='w')
        
        # Cancel button frame
        button_frame = ttk.Frame(content)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def on_cancel():
            self.cancel_operation = True
            status_label.config(text="Cancelling after current channel...")
            cancel_btn.config(state='disabled')
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        return {
            'dialog': dialog,
            'var': progress_var,
            'bar': progress_bar,
            'label': status_label,
            'cancel_btn': cancel_btn
        }

    def _create_tree_navigation(self, parent):
        """Create tree navigation panel (left side)"""
        # Header
        header = ttk.Label(parent, text="Channels", style='Header.TLabel')
        header.pack(fill=tk.X)
        
        # Toolbar (Motorola Astro CPS style)
        toolbar_frame = ttk.Frame(parent, padding=2)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Create toolbar buttons with icons/text
        # Add Channel button (green +)
        self.add_btn = tk.Button(
            toolbar_frame, 
            text="➕", 
            font=('Arial', 10),
            width=3,
            bg='#90EE90',  # Light green background
            activebackground='#32CD32',  # Lime green when clicked
            relief=tk.RAISED,
            bd=2,
            command=self._add_channel
        )
        self.add_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.add_btn, "Add new channel (creates a new channel with default values)")
        
        # Delete Channel button (red X)
        self.delete_btn = tk.Button(
            toolbar_frame,
            text="✕",
            font=('Arial', 10, 'bold'),
            width=3,
            bg='#FFB6C1',  # Light red/pink background
            activebackground='#FF6B6B',  # Red when clicked
            fg='#8B0000',  # Dark red text
            relief=tk.RAISED,
            bd=2,
            command=self._bulk_delete
        )
        self.delete_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.delete_btn, "Delete selected channel(s)")
        
        # Separator
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        
        # Move Up button (increase channel number priority / move earlier)
        self.move_up_btn = tk.Button(
            toolbar_frame,
            text="▲",
            font=('Arial', 9),
            width=3,
            relief=tk.RAISED,
            bd=2,
            command=self._move_channel_up
        )
        self.move_up_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.move_up_btn, "Decrease channel number by 1 (move to lower slot)")
        
        # Move Down button (increase channel number by 1)
        self.move_down_btn = tk.Button(
            toolbar_frame,
            text="▼",
            font=('Arial', 9),
            width=3,
            relief=tk.RAISED,
            bd=2,
            command=self._move_channel_down
        )
        self.move_down_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.move_down_btn, "Increase channel number by 1 (move to higher slot)")
        
        # Separator
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        
        # Duplicate button
        self.duplicate_btn = tk.Button(
            toolbar_frame,
            text="⧉",
            font=('Arial', 10),
            width=3,
            relief=tk.RAISED,
            bd=2,
            command=self._bulk_duplicate
        )
        self.duplicate_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.duplicate_btn, "Duplicate selected channel(s)")
        
        # Select Columns button row (above filters)
        columns_frame = ttk.Frame(parent, padding=2)
        columns_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.columns_btn = ttk.Button(
            columns_frame,
            text="Select Columns...",
            command=self._show_column_selector
        )
        self.columns_btn.pack(side=tk.LEFT)
        ToolTip(self.columns_btn, "Select columns to display in the channel list")
        
        # Filter bar (checkboxes)
        filter_frame = ttk.Frame(parent, padding=2)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(filter_frame, text="Filters:", font=('Arial', 8, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        
        # Initialize filter variables if not already (for when show() hasn't been called)
        if not hasattr(self, 'show_empty_channels') or self.show_empty_channels is None:
            self.show_empty_channels = tk.BooleanVar(value=False)
        
        if not hasattr(self, 'group_by_type') or self.group_by_type is None:
            self.group_by_type = tk.BooleanVar(value=False)  # Default: no grouping
        
        if not hasattr(self, 'group_by_mode') or self.group_by_mode is None:
            self.group_by_mode = tk.BooleanVar(value=False)  # Default: no grouping by mode
        
        self.show_empty_check = ttk.Checkbutton(
            filter_frame,
            text="Show empty channels",
            variable=self.show_empty_channels,
            command=self._on_show_empty_changed,
            style='Toggle.TCheckbutton'
        )
        self.show_empty_check.pack(side=tk.LEFT, padx=2)
        ToolTip(self.show_empty_check, "Show gaps in memory assignment (empty channel slots)")
        
        # Group by DMR (Analog/Digital type) checkbox
        self.group_by_type_check = ttk.Checkbutton(
            filter_frame,
            text="Group by DMR",
            variable=self.group_by_type,
            command=self._on_group_by_type_changed,
            style='Toggle.TCheckbutton'
        )
        self.group_by_type_check.pack(side=tk.LEFT, padx=8)
        ToolTip(self.group_by_type_check, "Separate channels into Analog and Digital (DMR) groups")
        
        # Group by Mode checkbox
        self.group_by_mode_check = ttk.Checkbutton(
            filter_frame,
            text="Group by mode",
            variable=self.group_by_mode,
            command=self._on_group_by_mode_changed,
            style='Toggle.TCheckbutton'
        )
        self.group_by_mode_check.pack(side=tk.LEFT, padx=8)
        ToolTip(self.group_by_mode_check, "Group channels by modulation mode (NFM, AM, DMR, USB, etc.)")
        
        # Search box
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        
        # Initialize search variable
        if not hasattr(self, 'search_var') or self.search_var is None:
            self.search_var = tk.StringVar()
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Bind search to filter as user types
        self.search_var.trace_add('write', lambda *args: self._on_search_changed())
        
        # === RADIO SELECTION TOOLBAR (for Read/Write operations) ===
        selection_frame = ttk.LabelFrame(parent, text="Radio Read/Write Selection", padding=5)
        selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Row 1: Quick select buttons
        quick_select_row = ttk.Frame(selection_frame)
        quick_select_row.pack(fill=tk.X, pady=(2, 5))
        
        select_all_btn = ttk.Button(quick_select_row, text="Select All", width=11,
                  command=self._select_all_for_radio)
        select_all_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(select_all_btn, "Select all channels for read/write")
        
        select_none_btn = ttk.Button(quick_select_row, text="Select None", width=11,
                  command=self._deselect_all_for_radio)
        select_none_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(select_none_btn, "Deselect all channels")
        
        ttk.Separator(quick_select_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        active_only_btn = ttk.Button(quick_select_row, text="Programmed", width=12,
                  command=self._select_active_channels)
        active_only_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(active_only_btn, "Select only programmed channels (skip empty slots)")
        
        active_range_btn = ttk.Button(quick_select_row, text="Full Range", width=12,
                  command=self._select_active_range)
        active_range_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(active_range_btn, "Select from first to last programmed channel (including empty slots)")
        
        # Separator between quick select and range selection
        ttk.Separator(selection_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # Row 2: Range selection
        range_row = ttk.Frame(selection_frame)
        range_row.pack(fill=tk.X, pady=(5, 2))
        
        ttk.Label(range_row, text="From:").pack(side=tk.LEFT, padx=(0, 2))
        self.range_from_var = tk.StringVar(value="0")
        range_from_entry = ttk.Entry(range_row, textvariable=self.range_from_var, width=6)
        range_from_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(range_row, text="To:").pack(side=tk.LEFT, padx=(5, 2))
        self.range_to_var = tk.StringVar(value="999")
        range_to_entry = ttk.Entry(range_row, textvariable=self.range_to_var, width=6)
        range_to_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(range_row, text="Select Range", width=12,
                  command=self._select_channel_range).pack(side=tk.LEFT, padx=5)
        
        # Selection count label
        self.selection_count_label = ttk.Label(range_row, text="Selected: 0", font=('Arial', 9, 'bold'))
        self.selection_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Tree with scrollbar
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.channel_tree = ttk.Treeview(
            tree_frame,
            columns=tuple(self.selected_columns),
            show='tree headings',
            selectmode='extended',  # Enable multi-select
            yscrollcommand=scrollbar.set,
            style='Tree.Treeview'
        )
        scrollbar.config(command=self.channel_tree.yview)
        
        self.channel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Populate the tree with channel data
        self._populate_channel_tree()
        
        # Bind selection event
        self.channel_tree.bind('<<TreeviewSelect>>', self._on_channel_select)
        
        # Bind click to handle checkbox column clicks
        self.channel_tree.bind('<Button-1>', self._on_tree_click)
        
        # Bind right-click context menu
        self.channel_tree.bind('<Button-3>', self._show_context_menu)
        
        # Prevent tree from collapsing on left arrow and navigate tabs instead
        self.channel_tree.bind('<Left>', lambda e: self._navigate_tab_left(e) or 'break')
        self.channel_tree.bind('<Right>', lambda e: self._navigate_tab_right(e) or 'break')
        
        # Bind keyboard navigation for channels only (up/down)
        # Bind to tree to override default behavior
        self.channel_tree.bind('<Up>', self._navigate_channel_up)
        self.channel_tree.bind('<Down>', self._navigate_channel_down)
    
    def _create_menu_bar(self):
        """Create menu bar with File menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open JSON...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save JSON...", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Import from CSV...", command=self._import_from_csv)
        file_menu.add_command(label="Export to CSV...", command=self._export_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        self.edit_menu = edit_menu  # Store reference for updating undo/redo state
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Selected Channels", command=self._bulk_delete, accelerator="Delete")
        edit_menu.add_command(label="Duplicate Selected Channels", command=self._bulk_duplicate, accelerator="Ctrl+D")
        
        # Program menu (Radio read/write operations)
        program_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Program", menu=program_menu)
        program_menu.add_command(label="Read from Radio...", command=self._read_from_radio, accelerator="Ctrl+R")
        program_menu.add_command(label="Write to Radio...", command=self._write_to_radio, accelerator="Ctrl+W")
        
        # View menu (rightmost position)
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Select Columns...", command=self._show_column_selector)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self._open_file())
        self.root.bind('<Control-s>', lambda e: self._save_file())
        self.root.bind('<Control-z>', lambda e: self._undo())
        self.root.bind('<Control-y>', lambda e: self._redo())
        self.root.bind('<Delete>', lambda e: self._bulk_delete())
        self.root.bind('<Control-d>', lambda e: self._bulk_duplicate())
        self.root.bind('<Control-r>', lambda e: self._read_from_radio())
        self.root.bind('<Control-w>', lambda e: self._write_to_radio())
        
        # Update undo/redo menu state
        self._update_undo_redo_menu()
    
    def _save_state(self, description: str = ""):
        """Save current state to undo stack before making changes
        
        Args:
            description: Optional description of the action (for debugging)
        """
        # Deep copy current channels state
        state_copy = copy.deepcopy(self.channels)
        self.undo_stack.append(state_copy)
        
        # Limit undo stack size
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)
        
        # Clear redo stack when new action is performed
        self.redo_stack.clear()
        
        # Update menu state
        self._update_undo_redo_menu()
    
    def _undo(self):
        """Undo the last action by restoring previous state"""
        if not self.undo_stack:
            return
        
        # Save current state to redo stack
        current_state = copy.deepcopy(self.channels)
        self.redo_stack.append(current_state)
        
        # Restore previous state
        self.channels = self.undo_stack.pop()
        
        # Rebuild tree with restored data
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        
        # Re-populate current channel's tabs if one is selected
        if self.current_channel and self.current_channel in self.channels:
            ch_data = self.channels[self.current_channel]
            ch_name = ch_data['channelName'].rstrip('\u0000').strip() or "(empty)"
            self.detail_header.config(text=f"Channel {self.current_channel} - {ch_name}")
            self._populate_general_tab(ch_data)
            self._populate_freq_tab(ch_data)
            self._populate_dmr_tab(ch_data)
            self._populate_advanced_tab(ch_data)
            self._populate_raw_tab(ch_data)
        elif self.current_channel and self.current_channel not in self.channels:
            # Channel was deleted, select first available
            self.current_channel = None
            first_channel = self._get_first_channel_item()
            if first_channel:
                self.channel_tree.selection_set(first_channel)
                self.channel_tree.focus(first_channel)
                self.channel_tree.event_generate('<<TreeviewSelect>>')
        
        # Update menu and status
        self._update_undo_redo_menu()
        self.status_label.config(text=f"Undo | Total Channels: {len(self.channels)}")
    
    def _redo(self):
        """Redo the last undone action"""
        if not self.redo_stack:
            return
        
        # Save current state to undo stack
        current_state = copy.deepcopy(self.channels)
        self.undo_stack.append(current_state)
        
        # Restore redo state
        self.channels = self.redo_stack.pop()
        
        # Rebuild tree with restored data
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        
        # Re-populate current channel's tabs if one is selected
        if self.current_channel and self.current_channel in self.channels:
            ch_data = self.channels[self.current_channel]
            ch_name = ch_data['channelName'].rstrip('\u0000').strip() or "(empty)"
            self.detail_header.config(text=f"Channel {self.current_channel} - {ch_name}")
            self._populate_general_tab(ch_data)
            self._populate_freq_tab(ch_data)
            self._populate_dmr_tab(ch_data)
            self._populate_advanced_tab(ch_data)
            self._populate_raw_tab(ch_data)
        elif self.current_channel and self.current_channel not in self.channels:
            # Channel was deleted, select first available
            self.current_channel = None
            first_channel = self._get_first_channel_item()
            if first_channel:
                self.channel_tree.selection_set(first_channel)
                self.channel_tree.focus(first_channel)
                self.channel_tree.event_generate('<<TreeviewSelect>>')
        
        # Update menu and status
        self._update_undo_redo_menu()
        self.status_label.config(text=f"Redo | Total Channels: {len(self.channels)}")
    
    def _update_undo_redo_menu(self):
        """Update the Edit menu undo/redo items based on stack state"""
        if not hasattr(self, 'edit_menu'):
            return
        
        # Update Undo menu item (index 0)
        if self.undo_stack:
            self.edit_menu.entryconfig(0, state='normal', 
                                       label=f"Undo ({len(self.undo_stack)})")
        else:
            self.edit_menu.entryconfig(0, state='disabled', label="Undo")
        
        # Update Redo menu item (index 1)
        if self.redo_stack:
            self.edit_menu.entryconfig(1, state='normal',
                                       label=f"Redo ({len(self.redo_stack)})")
        else:
            self.edit_menu.entryconfig(1, state='disabled', label="Redo")
    
    def _open_file(self):
        """Open a JSON channel file"""
        filename = filedialog.askopenfilename(
            title="Open Channel Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                filepath = Path(filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Handle new format with metadata
                if 'channels' in data:
                    channels = data['channels']
                else:
                    # Legacy format - entire file is channels dict
                    channels = data
                
                # Update current instance instead of creating new one
                self.channels = channels
                self.current_file = filepath
                
                # Update file identifier and window title
                self._update_file_identifier(filepath)
                
                # Clear undo/redo stacks for new file
                self.undo_stack.clear()
                self.redo_stack.clear()
                self._update_undo_redo_menu()
                
                # Rebuild tree with new data
                self.current_channel = None
                self._rebuild_channel_tree()
                
                # Update status
                self.status_label.config(text=f"Opened {filepath.name} | {len(self.channels)} channels")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def _save_file(self):
        """Save channel data to JSON file
        
        Implements Save/Save As behavior:
        - If file exists AND not from fresh read: Save directly (no dialog)
        - If no file OR fresh read: Show Save As dialog
        """
        # Check if we should save directly or show Save As dialog
        # Direct save: file exists AND it's not an unsaved fresh read
        if self.current_file and self.current_file.exists() and not self._is_unsaved_fresh_read:
            # Direct save - no dialog needed
            try:
                with open(self.current_file, 'w') as f:
                    json.dump(self.channels, f, indent=2)
                self.status_label.config(text=f"Saved to {self.current_file.name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
            return
        
        # Save As - show dialog
        now = datetime.now()
        
        # Use current filename if we have one (even for fresh reads), otherwise generate new
        if self.current_file:
            default_filename = self.current_file.name
            default_dir = str(self.current_file.parent) if self.current_file.parent.exists() else str(Path(__file__).parent.parent.parent)
        else:
            default_filename = f"config_{now.strftime('%y%m%d_%H%M')}.json"
            # Get repository root (CodeplugConverter directory)
            default_dir = str(Path(__file__).parent.parent.parent)
        
        filename = filedialog.asksaveasfilename(
            title="Save Channel Data As",
            initialdir=default_dir,
            initialfile=default_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                filepath = Path(filename)
                with open(filepath, 'w') as f:
                    json.dump(self.channels, f, indent=2)
                
                # Update file tracking - now it's a saved file
                self._update_file_identifier(filepath)
                self._is_unsaved_fresh_read = False  # Clear unsaved flag
                
                messagebox.showinfo("Success", "Channel data saved successfully!")
                self.status_label.config(text=f"Saved to {filepath.name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
    
    def _export_to_csv(self):
        """Export channel data to CSV file"""
        # Generate default filename with current date/time
        now = datetime.now()
        default_filename = f"channels_{now.strftime('%y%m%d_%H%M')}.csv"
        
        # Get repository root (CodeplugConverter directory)
        repo_root = Path(__file__).parent.parent.parent
        
        filename = filedialog.asksaveasfilename(
            title="Export to CSV",
            initialdir=str(repo_root),
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    # Define CSV columns
                    fieldnames = [
                        'Channel',
                        'Name',
                        'RX Frequency (MHz)',
                        'TX Frequency (MHz)',
                        'Offset (MHz)',
                        'Mode',
                        'Channel Type',
                        'RX CTCSS/DCS',
                        'TX CTCSS/DCS',
                        'Power',
                        'Squelch Mode',
                        'Bandwidth',
                        'DMR ID (Own)',
                        'DMR ID (Call)',
                        'DMR Slot',
                        'DMR Color Code (RX)',
                        'DMR Color Code (TX)'
                    ]
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Sort channels by channel number
                    sorted_channels = sorted(
                        self.channels.items(),
                        key=lambda x: int(x[0]) if x[0].isdigit() else 999999
                    )
                    
                    # Write each channel
                    for ch_id, ch in sorted_channels:
                        # Extract frequencies
                        rx_freq_str = self.freq_from_bytes(
                            ch['vfoaFrequency1'], ch['vfoaFrequency2'],
                            ch['vfoaFrequency3'], ch['vfoaFrequency4']
                        ).replace(' ⚠', '')
                        
                        tx_freq_str = self.freq_from_bytes(
                            ch['vfobFrequency1'], ch['vfobFrequency2'],
                            ch['vfobFrequency3'], ch['vfobFrequency4']
                        ).replace(' ⚠', '')
                        
                        try:
                            rx_freq = float(rx_freq_str)
                            tx_freq = float(tx_freq_str)
                            offset = tx_freq - rx_freq
                        except ValueError:
                            rx_freq = rx_freq_str
                            tx_freq = tx_freq_str
                            offset = 'N/A'
                        
                        # Get channel name
                        name = ch.get('channelName', '').rstrip('\u0000').strip() or '(empty)'
                        
                        # Get mode name
                        mode = self.MODE_NAMES.get(ch.get('vfoaMode', 6), 'NFM')
                        
                        # Get channel type
                        ch_type = self.CHANNEL_TYPES.get(ch.get('chType', 0), 'Analog')
                        
                        # Get CTCSS/DCS values
                        rx_ctcss = self.ctcss_dcs_from_value(ch.get('rxCtcss', 0))
                        tx_ctcss = self.ctcss_dcs_from_value(ch.get('txCtcss', ch.get('rxCtcss', 0)))
                        
                        # Get power level
                        power = self.POWER_LEVELS.get(ch.get('power', 0), 'Low')
                        
                        # Get squelch mode
                        squelch = self.SQUELCH_MODES.get(ch.get('sqlevel', 0), 'Carrier')
                        
                        # Get bandwidth
                        bandwidth = ch.get('bandwidth', 'N/A')
                        
                        # Get DMR IDs
                        own_id = self.id_from_bytes(
                            ch.get('ownId1', 0), ch.get('ownId2', 0),
                            ch.get('ownId3', 0), ch.get('ownId4', 0)
                        )
                        
                        call_id = self.id_from_bytes(
                            ch.get('callId1', 0), ch.get('callId2', 0),
                            ch.get('callId3', 0), ch.get('callId4', 0)
                        )
                        
                        # Get DMR slot and color codes
                        dmr_slot = ch.get('slot', 0) + 1 if ch_type == 'DMR' else 'N/A'
                        rx_cc = ch.get('rxCc', 0) if ch_type == 'DMR' else 'N/A'
                        tx_cc = ch.get('txCc', 0) if ch_type == 'DMR' else 'N/A'
                        
                        # Write row
                        writer.writerow({
                            'Channel': ch_id,
                            'Name': name,
                            'RX Frequency (MHz)': rx_freq,
                            'TX Frequency (MHz)': tx_freq,
                            'Offset (MHz)': f"{offset:.6f}" if isinstance(offset, float) else offset,
                            'Mode': mode,
                            'Channel Type': ch_type,
                            'RX CTCSS/DCS': rx_ctcss,
                            'TX CTCSS/DCS': tx_ctcss,
                            'Power': power,
                            'Squelch Mode': squelch,
                            'Bandwidth': bandwidth,
                            'DMR ID (Own)': own_id,
                            'DMR ID (Call)': call_id,
                            'DMR Slot': dmr_slot,
                            'DMR Color Code (RX)': rx_cc,
                            'DMR Color Code (TX)': tx_cc
                        })
                
                messagebox.showinfo("Success", 
                                  f"Exported {len(self.channels)} channels to CSV successfully!")
                self.status_label.config(text=f"Exported to {Path(filename).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {e}")
    
    def _import_from_csv(self):
        """Import channel data from CSV file
        
        Supports flexible CSV format with column headers. Required columns:
        - Channel (channel number)
        - RX Frequency (MHz)
        
        Optional columns:
        - Name, TX Frequency (MHz), Mode, Channel Type, RX CTCSS/DCS, TX CTCSS/DCS,
          Power, DMR ID (Own), DMR ID (Call), DMR Slot, DMR Color Code (RX), DMR Color Code (TX)
        """
        # Get repository root (CodeplugConverter directory)
        repo_root = Path(__file__).parent.parent.parent
        
        filename = filedialog.askopenfilename(
            title="Import from CSV",
            initialdir=str(repo_root),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            imported_channels = {}
            skipped_rows = []
            
            with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Check for required columns
                if not reader.fieldnames:
                    messagebox.showerror("Error", "CSV file appears to be empty or invalid")
                    return
                
                # Normalize field names (case-insensitive matching)
                field_map = {f.lower().strip(): f for f in reader.fieldnames}
                
                # Find channel column (required)
                ch_col = None
                for possible in ['channel', 'ch', 'channel number', 'ch #', 'number']:
                    if possible in field_map:
                        ch_col = field_map[possible]
                        break
                
                # Find RX frequency column (required)
                rx_freq_col = None
                for possible in ['rx frequency (mhz)', 'rx freq', 'rx frequency', 'receive frequency', 'frequency']:
                    if possible in field_map:
                        rx_freq_col = field_map[possible]
                        break
                
                if not ch_col or not rx_freq_col:
                    missing = []
                    if not ch_col:
                        missing.append("Channel")
                    if not rx_freq_col:
                        missing.append("RX Frequency")
                    messagebox.showerror("Error", 
                        f"CSV missing required columns: {', '.join(missing)}\n\n"
                        f"Found columns: {', '.join(reader.fieldnames)}")
                    return
                
                # Map optional columns
                def find_col(possible_names):
                    for name in possible_names:
                        if name.lower() in field_map:
                            return field_map[name.lower()]
                    return None
                
                name_col = find_col(['name', 'channel name'])
                tx_freq_col = find_col(['tx frequency (mhz)', 'tx freq', 'tx frequency', 'transmit frequency'])
                mode_col = find_col(['mode', 'modulation'])
                type_col = find_col(['channel type', 'type', 'ch type'])
                rx_ctcss_col = find_col(['rx ctcss/dcs', 'rx ctcss', 'rx tone', 'receive tone'])
                tx_ctcss_col = find_col(['tx ctcss/dcs', 'tx ctcss', 'tx tone', 'transmit tone'])
                power_col = find_col(['power', 'tx power', 'power level'])
                own_id_col = find_col(['dmr id (own)', 'own id', 'radio id', 'dmr id'])
                call_id_col = find_col(['dmr id (call)', 'call id', 'talkgroup', 'contact'])
                slot_col = find_col(['dmr slot', 'slot', 'timeslot', 'ts'])
                rx_cc_col = find_col(['dmr color code (rx)', 'rx cc', 'rx color code', 'color code'])
                tx_cc_col = find_col(['dmr color code (tx)', 'tx cc', 'tx color code'])
                
                row_num = 1  # For error reporting (header is row 0)
                for row in reader:
                    row_num += 1
                    
                    try:
                        # Get channel number
                        ch_num_str = row.get(ch_col, '').strip()
                        if not ch_num_str:
                            skipped_rows.append(f"Row {row_num}: Missing channel number")
                            continue
                        
                        try:
                            ch_num = int(ch_num_str)
                        except ValueError:
                            skipped_rows.append(f"Row {row_num}: Invalid channel number '{ch_num_str}'")
                            continue
                        
                        # Get RX frequency
                        rx_freq_str = row.get(rx_freq_col, '').strip()
                        if not rx_freq_str:
                            skipped_rows.append(f"Row {row_num}: Missing RX frequency")
                            continue
                        
                        try:
                            rx_freq_mhz = float(rx_freq_str)
                        except ValueError:
                            skipped_rows.append(f"Row {row_num}: Invalid RX frequency '{rx_freq_str}'")
                            continue
                        
                        # Create channel from default template
                        channel = self._create_default_channel()
                        channel['channelLow'] = ch_num
                        channel['channelHigh'] = 0
                        
                        # Set RX frequency
                        from ..utils.frequency import frequency_to_bytes
                        f1, f2, f3, f4 = frequency_to_bytes(rx_freq_mhz)
                        channel['vfoaFrequency1'] = f1
                        channel['vfoaFrequency2'] = f2
                        channel['vfoaFrequency3'] = f3
                        channel['vfoaFrequency4'] = f4
                        
                        # Set TX frequency (default to RX if not specified)
                        tx_freq_str = row.get(tx_freq_col, '').strip() if tx_freq_col else ''
                        if tx_freq_str:
                            try:
                                tx_freq_mhz = float(tx_freq_str)
                                f1, f2, f3, f4 = frequency_to_bytes(tx_freq_mhz)
                            except ValueError:
                                pass  # Keep RX frequency values
                        channel['vfobFrequency1'] = f1
                        channel['vfobFrequency2'] = f2
                        channel['vfobFrequency3'] = f3
                        channel['vfobFrequency4'] = f4
                        
                        # Set channel name
                        name = row.get(name_col, '').strip() if name_col else ''
                        if not name:
                            name = f'CH {ch_num}'
                        channel['channelName'] = name[:16].ljust(16, '\u0000')
                        
                        # Set mode
                        if mode_col:
                            mode_str = row.get(mode_col, '').strip().upper()
                            mode_map = {v.upper(): k for k, v in self.MODE_NAMES.items() if v != '?'}
                            channel['vfoaMode'] = mode_map.get(mode_str, 6)  # Default NFM
                            channel['vfobMode'] = channel['vfoaMode']
                        
                        # Set channel type
                        if type_col:
                            type_str = row.get(type_col, '').strip().lower()
                            if type_str in ['dmr', 'digital', '1']:
                                channel['chType'] = 1
                            else:
                                channel['chType'] = 0
                        else:
                            # Auto-detect from mode
                            channel['chType'] = 1 if channel['vfoaMode'] == 9 else 0
                        
                        # Set RX CTCSS/DCS
                        if rx_ctcss_col:
                            rx_ctcss_str = row.get(rx_ctcss_col, '').strip()
                            channel['rxCtcss'] = self._parse_ctcss_dcs(rx_ctcss_str)
                        
                        # Set TX CTCSS/DCS
                        if tx_ctcss_col:
                            tx_ctcss_str = row.get(tx_ctcss_col, '').strip()
                            channel['txCtcss'] = self._parse_ctcss_dcs(tx_ctcss_str)
                        else:
                            channel['txCtcss'] = channel['rxCtcss']  # Default to RX
                        
                        # Set power level
                        if power_col:
                            power_str = row.get(power_col, '').strip().lower()
                            power_map = {v.lower(): k for k, v in self.POWER_LEVELS.items()}
                            channel['power'] = power_map.get(power_str, 0)
                        
                        # Set DMR settings
                        if own_id_col:
                            own_id_str = row.get(own_id_col, '').strip()
                            if own_id_str and own_id_str != '-':
                                try:
                                    own_id = int(own_id_str)
                                    channel['ownId1'] = (own_id >> 24) & 0xFF
                                    channel['ownId2'] = (own_id >> 16) & 0xFF
                                    channel['ownId3'] = (own_id >> 8) & 0xFF
                                    channel['ownId4'] = own_id & 0xFF
                                except ValueError:
                                    pass
                        
                        if call_id_col:
                            call_id_str = row.get(call_id_col, '').strip()
                            if call_id_str and call_id_str != '-':
                                try:
                                    call_id = int(call_id_str)
                                    channel['callId1'] = (call_id >> 24) & 0xFF
                                    channel['callId2'] = (call_id >> 16) & 0xFF
                                    channel['callId3'] = (call_id >> 8) & 0xFF
                                    channel['callId4'] = call_id & 0xFF
                                except ValueError:
                                    pass
                        
                        if slot_col:
                            slot_str = row.get(slot_col, '').strip()
                            if slot_str and slot_str not in ['N/A', '-', '']:
                                try:
                                    slot = int(slot_str)
                                    channel['slot'] = max(1, min(2, slot))
                                except ValueError:
                                    pass
                        
                        if rx_cc_col:
                            rx_cc_str = row.get(rx_cc_col, '').strip()
                            if rx_cc_str and rx_cc_str not in ['N/A', '-', '']:
                                try:
                                    channel['rxCc'] = max(0, min(15, int(rx_cc_str)))
                                except ValueError:
                                    pass
                        
                        if tx_cc_col:
                            tx_cc_str = row.get(tx_cc_col, '').strip()
                            if tx_cc_str and tx_cc_str not in ['N/A', '-', '']:
                                try:
                                    channel['txCc'] = max(0, min(15, int(tx_cc_str)))
                                except ValueError:
                                    pass
                        else:
                            channel['txCc'] = channel.get('rxCc', 1)  # Default TX CC to RX CC
                        
                        # Add channel to import dict
                        imported_channels[str(ch_num)] = channel
                        
                    except Exception as e:
                        skipped_rows.append(f"Row {row_num}: Error - {str(e)}")
            
            if not imported_channels:
                messagebox.showerror("Error", 
                    f"No valid channels found in CSV.\n\n"
                    f"Skipped rows:\n" + "\n".join(skipped_rows[:10]))
                return
            
            # Ask user how to handle import
            existing_count = len(self.channels)
            import_count = len(imported_channels)
            
            if existing_count > 0:
                result = messagebox.askyesnocancel(
                    "Import Options",
                    f"Found {import_count} channels to import.\n\n"
                    f"You have {existing_count} existing channels.\n\n"
                    "Yes = Replace all (clear existing and import)\n"
                    "No = Merge (add/update channels from CSV)\n"
                    "Cancel = Abort import",
                    parent=self.root
                )
                
                if result is None:  # Cancel
                    return
                elif result:  # Yes - Replace
                    self._save_state("Import CSV (replace)")
                    self.channels = imported_channels
                else:  # No - Merge
                    self._save_state("Import CSV (merge)")
                    self.channels.update(imported_channels)
            else:
                # No existing channels, just import
                self._save_state("Import CSV")
                self.channels = imported_channels
            
            # Rebuild tree
            self.current_channel = None
            self._rebuild_channel_tree()
            
            # Show results
            msg = f"Imported {import_count} channels from CSV"
            if skipped_rows:
                msg += f"\n\nSkipped {len(skipped_rows)} rows"
                if len(skipped_rows) <= 5:
                    msg += ":\n" + "\n".join(skipped_rows)
            
            messagebox.showinfo("Import Complete", msg)
            self.status_label.config(text=f"Imported {import_count} channels | Total: {len(self.channels)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import CSV: {e}")
    
    def _parse_ctcss_dcs(self, value_str: str) -> int:
        """Parse CTCSS/DCS string to internal integer value
        
        Args:
            value_str: String like "Off", "100.0", "D023N", etc.
            
        Returns:
            Integer value for storage (0=Off, 670-2503=CTCSS, DCS codes)
        """
        if not value_str or value_str.lower() in ['off', '0', '-', 'none', 'n/a']:
            return 0
        
        # Try to parse as CTCSS tone (float Hz value)
        try:
            tone_hz = float(value_str)
            if 67.0 <= tone_hz <= 250.3:
                # Convert Hz to internal format (multiply by 10)
                return int(tone_hz * 10)
        except ValueError:
            pass
        
        # Try to parse as DCS code (D###N or D###R format)
        value_upper = value_str.upper().strip()
        if value_upper.startswith('D') and len(value_upper) == 5:
            try:
                code = int(value_upper[1:4])
                # DCS codes are stored differently - return raw for now
                # This is a simplified implementation
                return code
            except ValueError:
                pass
        
        return 0
    
    def _populate_channel_tree(self):
        """Populate the channel tree"""
        self._configure_tree_columns()
        self._rebuild_channel_tree()
    
    def _configure_tree_columns(self):
        """Configure tree columns based on selected columns"""
        # Configure R/W selection column (#0 - leftmost, uses 'text' in insert)
        # Use a programming/radio icon for the header
        self.channel_tree.heading('#0', text='⚡')  # Programming icon (lightning bolt)
        self.channel_tree.column('#0', width=35, anchor='center')
        
        # Reconfigure the tree with selected columns
        self.channel_tree['columns'] = tuple(self.selected_columns)
        
        # Set up headings and widths for selected columns
        for col_id in self.selected_columns:
            if col_id in self.available_columns:
                col_info = self.available_columns[col_id]
                self.channel_tree.heading(col_id, text=col_info['label'])
                self.channel_tree.column(col_id, width=col_info['width'])
        
        # Populate tree grouped by channel type
        analog_node = self.channel_tree.insert('', 'end', text='Analog Channels', open=True)
        dmr_node = self.channel_tree.insert('', 'end', text='DMR Channels', open=True)
        
        for ch_num, ch_data in sorted(self.channels.items(), key=lambda x: int(x[0])):
            name = ch_data['channelName'].rstrip('\u0000').strip() or "(empty)"
            rx_freq = self.freq_from_bytes(
                ch_data['vfoaFrequency1'], ch_data['vfoaFrequency2'],
                ch_data['vfoaFrequency3'], ch_data['vfoaFrequency4']
            )
            mode = self.MODE_NAMES.get(ch_data['vfoaMode'], '?')
            
            parent_node = dmr_node if ch_data['chType'] == 1 else analog_node
            
            self.channel_tree.insert(
                parent_node, 'end',
                text=ch_num,
                values=(name, rx_freq, mode),
                tags=(ch_num,)
            )
    
    def _rebuild_channel_tree(self, reselect_channel_id=None):
        """Rebuild the channel tree with current data"""
        # Clear existing channel items
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        
        # Check filter options
        show_empty = hasattr(self, 'show_empty_channels') and self.show_empty_channels and self.show_empty_channels.get()
        group_by_type = hasattr(self, 'group_by_type') and self.group_by_type and self.group_by_type.get()
        group_by_mode = hasattr(self, 'group_by_mode') and self.group_by_mode and self.group_by_mode.get()
        search_text = self.search_var.get().lower().strip() if hasattr(self, 'search_var') and self.search_var else ''
        
        # Configure tag for empty channels (grayed out)
        self.channel_tree.tag_configure('empty', foreground='#999999', background='#F5F5F5')
        
        # Create group nodes based on grouping options
        # Note: group_by_type (DMR) and group_by_mode are mutually exclusive (enforced in _on_group_changed)
        analog_node = None
        dmr_node = None
        mode_nodes = {}  # Dict of mode_name -> tree node
        
        if group_by_type:
            # Group by Analog vs Digital (DMR)
            analog_node = self.channel_tree.insert('', 'end', text='Analog Channels', open=True)
            dmr_node = self.channel_tree.insert('', 'end', text='DMR Channels', open=True)
        elif group_by_mode:
            # Group by modulation mode - create nodes dynamically based on data
            # First pass: collect all modes present in the data
            modes_present = set()
            for ch_id in self.channels:
                ch_data = self.channels[ch_id]
                mode = self.MODE_NAMES.get(ch_data.get('vfoaMode', 6), 'NFM')
                modes_present.add(mode)
            
            # Create nodes in a logical order (based on MODE_NAMES order)
            mode_order = [v for k, v in sorted(self.MODE_NAMES.items()) if v != '?' and v in modes_present]
            for mode in mode_order:
                mode_nodes[mode] = self.channel_tree.insert('', 'end', text=f'{mode} Channels', open=True)
        
        item_to_select = None
        
        # Get sorted channel IDs
        existing_ids = sorted([int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()])
        
        if show_empty and existing_ids:
            # Build complete range from 0 to max channel number
            max_ch = max(existing_ids)
            all_slots = list(range(0, max_ch + 1))
        else:
            # Just show existing channels
            all_slots = existing_ids
        
        # Add channels (and empty slots if filter enabled and no search active)
        for ch_num in all_slots:
            ch_id = str(ch_num)
            
            if ch_id in self.channels:
                # Channel exists in data - check if it's a "programmed" channel or an "empty" one
                ch_data = self.channels[ch_id]
                ch_name = ch_data.get('channelName', '').rstrip('\u0000').strip()
                
                # A channel is considered "empty" if it has no name
                # Empty channels behave like empty slots - hidden unless show_empty is checked
                is_empty_channel = not ch_name
                
                if is_empty_channel:
                    # Empty channel - treat like empty slot (hidden unless show_empty)
                    if not show_empty or search_text:
                        continue  # Skip empty channels when filter is off or searching
                    
                    # Show as grayed-out empty slot
                    empty_values = []
                    for col_id in self.selected_columns:
                        if col_id == 'ch':
                            empty_values.append(ch_id)
                        elif col_id == 'name':
                            empty_values.append('(empty slot)')
                        else:
                            empty_values.append('—')
                    
                    # Determine parent for empty channels
                    if group_by_type:
                        parent_node = analog_node  # Put empty slots under Analog by default
                    else:
                        parent_node = ''  # Root level
                    
                    item_id = self.channel_tree.insert(parent_node, 'end',
                        text='☐',  # Empty checkbox
                        values=tuple(empty_values),
                        tags=(ch_id, 'empty')  # Tag as empty for styling
                    )
                else:
                    # Programmed channel with a name - always show (subject to search filter)
                    
                    # Apply search filter
                    if search_text:
                        if search_text not in ch_name.lower() and search_text not in ch_id:
                            continue  # Skip this channel if it doesn't match search
                    
                    column_values = []
                    for col_id in self.selected_columns:
                        if col_id == 'sel':
                            # Special handling for selection checkbox column
                            column_values.append(self._get_checkbox_display(ch_id))
                        elif col_id in self.available_columns:
                            extract_func = self.available_columns[col_id]['extract']
                            column_values.append(extract_func(ch_data))
                    
                    # Determine parent based on grouping option
                    if group_by_type:
                        parent_node = dmr_node if ch_data.get('chType', 0) == 1 else analog_node
                    elif group_by_mode:
                        ch_mode = self.MODE_NAMES.get(ch_data.get('vfoaMode', 6), 'NFM')
                        parent_node = mode_nodes.get(ch_mode, '')
                    else:
                        parent_node = ''  # Root level when not grouping
                    
                    # Insert item - checkbox in #0 (text), data in columns
                    checkbox = self._get_checkbox_display(ch_id)
                    item_id = self.channel_tree.insert(parent_node, 'end',
                        text=checkbox,
                        values=tuple(column_values),
                        tags=(ch_id,)
                    )
            else:
                # Empty slot (not in self.channels) - show placeholder only when show_empty is on AND no search active
                if not show_empty or search_text:
                    continue
                    
                # Empty slots get empty checkbox and placeholder values
                empty_values = [ch_id, '(empty slot)'] + ['—'] * (len(self.selected_columns) - 2)
                
                # Determine parent for empty slots
                if group_by_type:
                    parent_node = analog_node  # Put empty slots under Analog by default
                else:
                    parent_node = ''  # Root level
                
                item_id = self.channel_tree.insert(parent_node, 'end',
                    text='☐',  # Empty checkbox
                    values=tuple(empty_values),
                    tags=(ch_id, 'empty')  # Tag as empty for styling
                )
            
            if reselect_channel_id and ch_id == reselect_channel_id:
                item_to_select = item_id
        
        # Reselect item if requested, or auto-select first channel if none selected
        if item_to_select:
            self.channel_tree.selection_set(item_to_select)
            self.channel_tree.focus(item_to_select)
            self.channel_tree.see(item_to_select)
            # Trigger selection event to ensure tabs are populated
            self.channel_tree.event_generate('<<TreeviewSelect>>')
        elif not self.current_channel:
            # Auto-select first channel on initial load
            first_channel = self._get_first_channel_item()
            if first_channel:
                self.channel_tree.selection_set(first_channel)
                self.channel_tree.focus(first_channel)
                self.channel_tree.see(first_channel)
                # Trigger selection event to populate tabs
                self.channel_tree.event_generate('<<TreeviewSelect>>')
        
        # Update status if it exists
        if hasattr(self, 'status_label'):
            visible_count = len([item for item in self.channel_tree.get_children('') 
                               if self.channel_tree.item(item, 'tags')])
            if group_by_type or group_by_mode:
                # Count children in groups
                visible_count = 0
                for group in self.channel_tree.get_children(''):
                    visible_count += len(self.channel_tree.get_children(group))
            
            # Count programmed vs empty channels in self.channels
            programmed_count = 0
            empty_channel_count = 0
            for ch_id, ch_data in self.channels.items():
                ch_name = ch_data.get('channelName', '').rstrip('\u0000').strip()
                if ch_name:
                    programmed_count += 1
                else:
                    empty_channel_count += 1
            
            # Count empty slots (not in self.channels at all)
            empty_slot_count = len(all_slots) - len(existing_ids) if show_empty else 0
            
            # Total empty = empty channels (no name) + empty slots (not in dict)
            total_empty = empty_channel_count + empty_slot_count
            
            # Build status message
            if search_text:
                self.status_label.config(text=f"Search: '{search_text}' | Showing {visible_count} channels")
            elif show_empty and total_empty > 0:
                self.status_label.config(text=f"Total: {programmed_count} channels + {total_empty} empty slots")
            else:
                self.status_label.config(text=f"Total: {programmed_count} channels + {total_empty} empty slots")
    
    def _get_first_channel_item(self):
        """Get the first channel item in the tree (skip group nodes)"""
        # Get all top-level items
        for item in self.channel_tree.get_children():
            # Check if this item has tags (is a channel, not a group)
            if self.channel_tree.item(item, 'tags'):
                return item
            # If no tags, it's a group node - check its children
            children = self.channel_tree.get_children(item)
            if children:
                # Return first child that has tags (is a channel)
                for child in children:
                    if self.channel_tree.item(child, 'tags'):
                        return child
        return None
    
    def _get_all_channel_items(self):
        """Get all channel items in the tree (skip group nodes)
        
        Yields:
            Tree item IDs for all channel items
        """
        for item in self.channel_tree.get_children():
            # Check if this item has tags (is a channel, not a group)
            if self.channel_tree.item(item, 'tags'):
                yield item
            else:
                # It's a group node - yield its children
                for child in self.channel_tree.get_children(item):
                    if self.channel_tree.item(child, 'tags'):
                        yield child
    
    def _create_detail_panel(self, parent):
        """Create tabbed detail panel (right side)"""
        # Header with channel info
        self.detail_header = ttk.Label(parent, text="Select a channel to view details", 
                                      style='Header.TLabel')
        self.detail_header.pack(fill=tk.X)
        
        # Notebook for tabs
        self.detail_notebook = ttk.Notebook(parent)
        self.detail_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: General Settings
        self.general_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.general_tab, text="General")
        
        # Tab 2: Frequency (RX/TX)
        self.freq_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.freq_tab, text="Frequency")
        
        # Tab 4: DMR Settings
        self.dmr_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.dmr_tab, text="DMR")
        
        # Tab 5: Advanced
        self.advanced_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.advanced_tab, text="Advanced")
        
        # Tab 6: Raw Data
        self.raw_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.raw_tab, text="Raw Data")
        
        # Variables for frequency copy
        self.copy_ctcss_var = tk.BooleanVar(value=True)
        self.current_rx_freq = tk.StringVar()
        self.current_tx_freq = tk.StringVar()
        self.current_rx_ctcss = tk.StringVar()
        self.current_tx_ctcss = tk.StringVar()
        self.offset_var = tk.StringVar(value="0.000000")
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        # Create a visible border line above status bar using a Frame with background color
        border_frame = tk.Frame(self.root, height=2, bg='#AAAAAA')
        border_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status bar frame with light background
        status_frame = tk.Frame(self.root, bg='#F0F0F0', relief=tk.FLAT)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status label with better padding to avoid border overlap
        self.status_label = tk.Label(
            status_frame,
            text=f"Total Channels: {len(self.channels)} | Ready",
            bg='#F0F0F0',
            fg='#000000',
            font=('Arial', 9),
            padx=10,
            pady=5,
            anchor='w'
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _on_channel_select(self, event):
        """Handle channel selection in tree"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.channel_tree.item(item, 'tags')
        
        if not tags:
            return  # Clicked on a group node
        
        ch_num = tags[0]
        self.selected_channel = ch_num
        self.current_channel = ch_num  # Track for updates
        ch_data = self.channels[ch_num]
        
        # Update header
        ch_name = ch_data['channelName'].rstrip('\u0000').strip() or "(empty)"
        self.detail_header.config(text=f"Channel {ch_num} - {ch_name}")
        
        # Populate all tabs
        self._populate_general_tab(ch_data)
        self._populate_freq_tab(ch_data)
        self._populate_dmr_tab(ch_data)
        self._populate_advanced_tab(ch_data)
        self._populate_raw_tab(ch_data)
    
    def _populate_general_tab(self, ch_data):
        """Populate General Settings tab"""
        # Clear existing widgets
        for widget in self.general_tab.winfo_children():
            widget.destroy()
        
        # Create scrollable frame - use lighter background to match ttk.Frame
        canvas = tk.Canvas(self.general_tab, bg='#E8E8E8', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.general_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Form fields
        row = 0
        
        # Channel Number (read-only - editing feature removed, see README TODO)
        ttk.Label(scrollable_frame, text="Channel Number:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        ch_num_label = ttk.Label(scrollable_frame, text=str(ch_data['channelLow']), 
                                 font=('Arial', 9), foreground=BLUE_PALETTE['primary'])
        ch_num_label.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        
        row += 1
        
        # Channel Name (editable with live updates)
        ttk.Label(scrollable_frame, text="Channel Name:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        # Get the actual channel name from data
        ch_name_raw = ch_data.get('channelName', '')
        if isinstance(ch_name_raw, str):
            ch_name = ch_name_raw.rstrip('\u0000').strip()
        else:
            ch_name = ''
        self.current_channel_name = tk.StringVar(value=ch_name)
        name_entry = ttk.Entry(scrollable_frame, textvariable=self.current_channel_name, width=30)
        # Bind to update data and header when user edits the name (but don't rebuild tree yet)
        self.current_channel_name.trace_add('write', lambda *args: self._on_channel_name_changed())
        # Rebuild tree only when user finishes editing (loses focus)
        name_entry.bind('<FocusOut>', lambda e: self._on_channel_name_focus_out())
        name_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Mode (chType is auto-set based on mode: DMR mode sets chType=1, others set chType=0)
        ttk.Label(scrollable_frame, text="Mode:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        mode = self.MODE_NAMES.get(ch_data['vfoaMode'], 'NFM')  # Default to NFM instead of ?
        # Filter out the unknown mode from dropdown options
        mode_values = [v for k, v in self.MODE_NAMES.items() if v != '?']
        mode_combo = ttk.Combobox(scrollable_frame, values=mode_values,
                                 state='readonly', width=27)
        mode_combo.set(mode if mode != '?' else 'NFM')
        mode_combo.bind('<<ComboboxSelected>>', lambda e: self._update_field('vfoaMode', 
            {v: k for k, v in self.MODE_NAMES.items()}[mode_combo.get()]))
        mode_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Add separator
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky='ew', padx=10, pady=15)
        row += 1
        
        # Validation warnings section
        ttk.Label(scrollable_frame, text="Validation:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Run validation
        warnings = validate_channel(ch_data)
        
        if warnings:
            # Show warnings in red
            for warning in warnings:
                warning_frame = ttk.Frame(scrollable_frame)
                warning_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=2)
                
                warning_icon = tk.Label(warning_frame, text="⚠", font=('Arial', 12), 
                                       foreground='#FF6600')
                warning_icon.pack(side=tk.LEFT, padx=(0, 5))
                
                warning_label = tk.Label(warning_frame, text=warning, font=('Arial', 9), 
                                        foreground='#CC0000', wraplength=400, justify=tk.LEFT)
                warning_label.pack(side=tk.LEFT)
                row += 1
        else:
            # Show validation passed
            validation_frame = ttk.Frame(scrollable_frame)
            validation_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=2)
            
            check_icon = tk.Label(validation_frame, text="✓", font=('Arial', 12), 
                                 foreground='#008800')
            check_icon.pack(side=tk.LEFT, padx=(0, 5))
            
            validation_label = tk.Label(validation_frame, text="All settings are valid", 
                                       font=('Arial', 9), foreground='#006600')
            validation_label.pack(side=tk.LEFT)
            row += 1
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _populate_freq_tab(self, ch_data):
        """Populate Frequency tab with RX (VFO A) and TX (VFO B) settings"""
        # Clear existing widgets
        for widget in self.freq_tab.winfo_children():
            widget.destroy()
        
        # Check if this is a DMR channel
        is_dmr = ch_data.get('chType', 0) == 1
        
        # Create scrollable frame - use lighter background to match ttk.Frame
        canvas = tk.Canvas(self.freq_tab, bg='#E8E8E8', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.freq_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Main container with three columns
        main_frame = ttk.Frame(scrollable_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # ===== LEFT COLUMN: RX Settings (VFO A) =====
        rx_frame = ttk.LabelFrame(main_frame, text="Receive (RX) - VFO A", padding=10)
        rx_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        rx_row = 0
        
        # RX Frequency
        ttk.Label(rx_frame, text="RX Frequency (MHz):", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        vfoa_rx_freq = self.freq_from_bytes(
            ch_data['vfoaFrequency1'], ch_data['vfoaFrequency2'],
            ch_data['vfoaFrequency3'], ch_data['vfoaFrequency4']
        )
        vfoa_rx_freq_var = tk.StringVar(value=vfoa_rx_freq)
        rx_entry = ttk.Entry(rx_frame, textvariable=vfoa_rx_freq_var, width=20)
        rx_entry.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Bind FocusOut to validate and save RX frequency
        rx_entry.bind('<FocusOut>', lambda e: self._on_frequency_focus_out(
            vfoa_rx_freq_var, 'vfoaFrequency', rx_entry))
        rx_row += 1
        
        # RX CTCSS/DCS (disabled for DMR channels)
        ttk.Label(rx_frame, text="RX CTCSS/DCS:", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        rx_ctcss = ch_data.get('rxCtcss', 0)
        rx_ctcss_display = self._ctcss_value_to_display(rx_ctcss)
        if is_dmr:
            # Use tk.Entry for disabled state with gray background
            rx_ctcss_entry = tk.Entry(rx_frame, width=20, bg='#E0E0E0', fg='#808080')
            rx_ctcss_entry.insert(0, rx_ctcss_display)
            rx_ctcss_entry.config(state='disabled', disabledbackground='#E0E0E0', disabledforeground='#808080')
            rx_ctcss_entry.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        else:
            rx_ctcss_combo = ttk.Combobox(rx_frame, values=self.CTCSS_DCS_COMBINED, width=17)
            rx_ctcss_combo.set(rx_ctcss_display)
            rx_ctcss_combo.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # RX Color Code (only for DMR channels)
        ttk.Label(rx_frame, text="RX Color Code:", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        rx_cc_value = ch_data.get('rxCc', 0)
        rx_cc_spin = tk.Spinbox(rx_frame, from_=0, to=15, width=17)
        rx_cc_spin.delete(0, tk.END)
        rx_cc_spin.insert(0, str(rx_cc_value))
        if not is_dmr:
            rx_cc_spin.config(state='disabled', disabledbackground='#E0E0E0', disabledforeground='#808080')
        rx_cc_spin.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # ===== RIGHT COLUMN: TX Settings =====
        tx_frame = ttk.LabelFrame(main_frame, text="VFO A - Transmit (TX)", padding=10)
        tx_frame.grid(row=0, column=2, sticky='nsew', padx=5, pady=5)
        
        tx_row = 0
        
        # TX Frequency (currently same as RX for PMR-171)
        ttk.Label(tx_frame, text="TX Frequency (MHz):", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        vfoa_tx_freq = self.freq_from_bytes(
            ch_data['vfobFrequency1'], ch_data['vfobFrequency2'],
            ch_data['vfobFrequency3'], ch_data['vfobFrequency4']
        )
        vfoa_tx_freq_var = tk.StringVar(value=vfoa_tx_freq)
        tx_entry = ttk.Entry(tx_frame, textvariable=vfoa_tx_freq_var, width=20)
        tx_entry.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Bind FocusOut to validate and save TX frequency
        tx_entry.bind('<FocusOut>', lambda e: self._on_frequency_focus_out(
            vfoa_tx_freq_var, 'vfobFrequency', tx_entry))
        tx_row += 1
        
        # TX CTCSS/DCS (disabled for DMR channels)
        ttk.Label(tx_frame, text="TX CTCSS/DCS:", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        tx_ctcss = ch_data.get('txCtcss', ch_data.get('rxCtcss', 0))
        tx_ctcss_display = self._ctcss_value_to_display(tx_ctcss)
        if is_dmr:
            # Use tk.Entry for disabled state with gray background
            tx_ctcss_entry = tk.Entry(tx_frame, width=20, bg='#E0E0E0', fg='#808080')
            tx_ctcss_entry.insert(0, tx_ctcss_display)
            tx_ctcss_entry.config(state='disabled', disabledbackground='#E0E0E0', disabledforeground='#808080')
            tx_ctcss_entry.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        else:
            tx_ctcss_combo = ttk.Combobox(tx_frame, values=self.CTCSS_DCS_COMBINED, width=17)
            tx_ctcss_combo.set(tx_ctcss_display)
            tx_ctcss_combo.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # TX Color Code (only for DMR channels)
        ttk.Label(tx_frame, text="TX Color Code:", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        tx_cc_value = ch_data.get('txCc', 0)
        tx_cc_spin = tk.Spinbox(tx_frame, from_=0, to=15, width=17)
        tx_cc_spin.delete(0, tk.END)
        tx_cc_spin.insert(0, str(tx_cc_value))
        if not is_dmr:
            tx_cc_spin.config(state='disabled', disabledbackground='#E0E0E0', disabledforeground='#808080')
        tx_cc_spin.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # ===== CENTER COLUMN: Copy Tools =====
        tools_frame = ttk.LabelFrame(main_frame, text="Copy & Offset Tools", padding=10)
        tools_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        
        tools_row = 0
        
        # Current offset display
        ttk.Label(tools_frame, text="Current Offset:", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        try:
            rx_freq_float = float(vfoa_rx_freq_var.get().split()[0])
            tx_freq_float = float(vfoa_tx_freq_var.get().split()[0])
            offset = tx_freq_float - rx_freq_float
        except (ValueError, IndexError):
            offset = 0.0
        
        offset_var = tk.StringVar(value=f"{offset:+.6f} MHz")
        offset_label = ttk.Label(tools_frame, textvariable=offset_var, 
                                font=('Arial', 11, 'bold'), foreground=BLUE_PALETTE['primary'])
        offset_label.grid(row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient='horizontal').grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        tools_row += 1
        
        # Simple copy section
        ttk.Label(tools_frame, text="Simple Copy:", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        tools_row += 1
        
        # Copy RX to TX button
        def copy_rx_to_tx():
            vfoa_tx_freq_var.set(vfoa_rx_freq_var.get())
            offset_var.set("+0.000000 MHz")
        
        # Copy TX to RX button
        def copy_tx_to_rx():
            vfoa_rx_freq_var.set(vfoa_tx_freq_var.get())
            offset_var.set("+0.000000 MHz")
        
        ttk.Button(tools_frame, text="RX ⟶ TX", command=copy_rx_to_tx).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        ttk.Button(tools_frame, text="RX ⟵ TX", command=copy_tx_to_rx).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient='horizontal').grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        tools_row += 1
        
        # Offset field section
        ttk.Label(tools_frame, text="Offset (MHz):", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        tools_row += 1
        
        # Calculate standard offset based on RX frequency, or use current offset if non-zero
        try:
            rx_freq_float = float(vfoa_rx_freq_var.get().split()[0])
            tx_freq_float = float(vfoa_tx_freq_var.get().split()[0])
            current_offset = tx_freq_float - rx_freq_float
            
            # Use current offset if it's non-zero, otherwise suggest standard offset
            if abs(current_offset) > 0.001:
                suggested_offset = current_offset
            else:
                suggested_offset = self.get_standard_offset(rx_freq_float)
        except (ValueError, IndexError):
            suggested_offset = 0.0
        
        custom_offset_var = tk.StringVar(value=f"{suggested_offset:+.1f}")
        custom_offset_entry = ttk.Entry(tools_frame, textvariable=custom_offset_var, 
                                       width=15, font=('Arial', 10))
        custom_offset_entry.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Preset offset buttons
        preset_frame = ttk.Frame(tools_frame)
        preset_frame.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        def set_offset(value):
            custom_offset_var.set(f"{value:+.1f}")
        
        ttk.Button(preset_frame, text="+5.0", command=lambda: set_offset(5.0), width=6).grid(
            row=0, column=0, padx=2, pady=2)
        ttk.Button(preset_frame, text="-0.6", command=lambda: set_offset(-0.6), width=6).grid(
            row=0, column=1, padx=2, pady=2)
        ttk.Button(preset_frame, text="-5.0", command=lambda: set_offset(-5.0), width=6).grid(
            row=0, column=2, padx=2, pady=2)
        
        preset_frame.grid_columnconfigure(0, weight=1)
        preset_frame.grid_columnconfigure(1, weight=1)
        preset_frame.grid_columnconfigure(2, weight=1)
        
        # Separator
        ttk.Separator(tools_frame, orient='horizontal').grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        tools_row += 1
        
        # Copy with offset section
        ttk.Label(tools_frame, text="Copy with Offset:", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        tools_row += 1
        
        # Apply offset RX to TX
        def apply_offset_rx_to_tx():
            try:
                rx_freq = float(vfoa_rx_freq_var.get().split()[0])
                offset_mhz = float(custom_offset_var.get())
                new_tx = rx_freq + offset_mhz
                vfoa_tx_freq_var.set(f"{new_tx:.6f}")
                offset_var.set(f"{offset_mhz:+.6f} MHz")
            except (ValueError, IndexError):
                pass
        
        # Apply offset TX to RX
        def apply_offset_tx_to_rx():
            try:
                tx_freq = float(vfoa_tx_freq_var.get().split()[0])
                offset_mhz = float(custom_offset_var.get())
                new_rx = tx_freq - offset_mhz
                vfoa_rx_freq_var.set(f"{new_rx:.6f}")
                offset_var.set(f"{offset_mhz:+.6f} MHz")
            except (ValueError, IndexError):
                pass
        
        ttk.Button(tools_frame, text="RX + ⟶ TX", command=apply_offset_rx_to_tx).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        ttk.Button(tools_frame, text="RX ⟵ + TX", command=apply_offset_tx_to_rx).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Layout canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _populate_dmr_tab(self, ch_data):
        """Populate DMR Settings tab"""
        # Clear existing widgets
        for widget in self.dmr_tab.winfo_children():
            widget.destroy()
        
        # Create scrollable frame - use lighter background to match ttk.Frame
        canvas = tk.Canvas(self.dmr_tab, bg='#E8E8E8', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dmr_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        frame = ttk.Frame(scrollable_frame, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        is_dmr = ch_data.get('chType', 0) == 1
        
        # Show compact message if not DMR
        if not is_dmr:
            # Create a subtle warning banner
            warning_frame = tk.Frame(frame, bg='#F0F0F0', relief=tk.RIDGE, bd=1)
            warning_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
            
            msg_frame = tk.Frame(warning_frame, bg='#F0F0F0')
            msg_frame.pack(pady=8)
            
            tk.Label(msg_frame, 
                    text="⚠",
                    font=('Arial', 10, 'bold'), 
                    bg='#F0F0F0',
                    fg='#AAAAAA').pack(side=tk.LEFT, padx=(5, 8))
            tk.Label(msg_frame,
                    text="DMR Settings Not Available (Analog Channel)",
                    font=('Arial', 9),
                    bg='#F0F0F0', 
                    fg='#888888').pack(side=tk.LEFT, padx=(0, 5))
        
        row = 0 if is_dmr else 1
        
        # Own ID
        ttk.Label(frame, text="Own ID:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        own_id = self.id_from_bytes(
            ch_data['ownId1'], ch_data['ownId2'],
            ch_data['ownId3'], ch_data['ownId4']
        )
        # Use tk.Entry for both cases for consistent behavior
        own_entry = tk.Entry(frame, width=20)
        own_entry.insert(0, own_id)
        if not is_dmr:
            own_entry.config(state='disabled', bg='#E0E0E0', fg='#808080',
                           disabledbackground='#E0E0E0', disabledforeground='#808080')
        own_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Talkgroup/Private Call (from callId bytes, 0-16777215)
        ttk.Label(frame, text="Talkgroup/Private Call:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        # Talkgroup is stored in callId1-4 bytes (same as DMR ID encoding)
        tg_value_str = self.id_from_bytes(
            ch_data.get('callId1', 0), ch_data.get('callId2', 0),
            ch_data.get('callId3', 0), ch_data.get('callId4', 0)
        )
        tg_value = int(tg_value_str) if tg_value_str != '-' else 0
        if not is_dmr:
            tg_entry = tk.Entry(frame, width=20, bg='#E0E0E0', fg='#808080')
            tg_entry.insert(0, str(tg_value))
            tg_entry.config(state='disabled', disabledbackground='#E0E0E0', disabledforeground='#808080')
        else:
            # Use tk.Spinbox for consistent behavior and insert value directly
            tg_entry = tk.Spinbox(frame, from_=0, to=16777215, width=18)
            tg_entry.delete(0, tk.END)
            tg_entry.insert(0, str(tg_value))
        tg_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Timeslot - use Spinbox with increment buttons like other numerical fields
        ttk.Label(frame, text="Timeslot:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        # Slot is stored as 1 or 2 in data, sanitize to only allow 1 or 2
        raw_slot = ch_data.get('slot', 1)
        slot_value = max(1, min(2, raw_slot)) if raw_slot != 0 else 1  # Default 0 to TS1
        if is_dmr:
            timeslot_spin = tk.Spinbox(frame, from_=1, to=2, width=18)
            timeslot_spin.delete(0, tk.END)
            timeslot_spin.insert(0, str(slot_value))
        else:
            # Disabled state - gray background
            timeslot_spin = tk.Spinbox(frame, from_=1, to=2, width=18)
            timeslot_spin.delete(0, tk.END)
            timeslot_spin.insert(0, str(slot_value))
            timeslot_spin.config(state='disabled', disabledbackground='#E0E0E0', 
                               disabledforeground='#808080')
        timeslot_spin.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Emergency Alarm - with ON/OFF indicator like Advanced tab
        ttk.Label(frame, text="Emergency Alarm:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=8)
        
        # Container frame for checkbox and status label
        emergency_frame = ttk.Frame(frame)
        emergency_frame.grid(row=row, column=1, sticky=tk.W, padx=10, pady=8)
        
        is_emergency_enabled = bool(ch_data.get('emergency', 0))
        emergency_var = tk.BooleanVar(value=is_emergency_enabled)
        
        # Status indicator label (changes color based on state)
        emergency_status = tk.Label(
            emergency_frame,
            text="ON" if is_emergency_enabled else "OFF",
            font=('Arial', 9, 'bold'),
            fg='#008800' if is_emergency_enabled else '#888888',
            width=4
        )
        emergency_status.pack(side=tk.LEFT, padx=(0, 8))
        
        # Checkbox with toggle style
        emergency_check = ttk.Checkbutton(emergency_frame, variable=emergency_var, style='Toggle.TCheckbutton')
        if is_emergency_enabled:
            emergency_check.state(['selected'])
        else:
            emergency_check.state(['!selected'])
        if not is_dmr:
            emergency_check.state(['disabled'])
            emergency_status.config(fg='#AAAAAA')  # Grayed out when disabled
        
        # Update status label when checkbox changes
        def on_emergency_toggle(*args):
            if emergency_var.get():
                emergency_status.config(text="ON", fg='#008800')
            else:
                emergency_status.config(text="OFF", fg='#888888')
        
        emergency_var.trace_add('write', on_emergency_toggle)
        emergency_check.pack(side=tk.LEFT)
        row += 1
        
        # Layout canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _populate_advanced_tab(self, ch_data):
        """Populate Advanced Settings tab"""
        # Clear existing widgets
        for widget in self.advanced_tab.winfo_children():
            widget.destroy()
        
        # Create scrollable frame - use lighter background to match ttk.Frame
        canvas = tk.Canvas(self.advanced_tab, bg='#E8E8E8', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.advanced_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        frame = ttk.Frame(scrollable_frame, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # Helper function to create a toggle row with clear visual state
        def create_toggle_row(parent, row_num, label_text, data_key):
            """Create a toggle checkbox row with clear On/Off indicator"""
            ttk.Label(parent, text=label_text, font=('Arial', 9, 'bold')).grid(
                row=row_num, column=0, sticky=tk.W, padx=10, pady=8)
            
            # Container frame for checkbox and status label
            toggle_frame = ttk.Frame(parent)
            toggle_frame.grid(row=row_num, column=1, sticky=tk.W, padx=10, pady=8)
            
            is_enabled = bool(ch_data.get(data_key, 0))
            var = tk.BooleanVar(value=is_enabled)
            
            # Status indicator label (changes color based on state)
            status_label = tk.Label(
                toggle_frame,
                text="ON" if is_enabled else "OFF",
                font=('Arial', 9, 'bold'),
                fg='#008800' if is_enabled else '#888888',
                width=4
            )
            status_label.pack(side=tk.LEFT, padx=(0, 8))
            
            # Checkbox with toggle style
            check = ttk.Checkbutton(toggle_frame, variable=var, style='Toggle.TCheckbutton')
            if is_enabled:
                check.state(['selected'])
            else:
                check.state(['!selected'])
            
            # Update status label when checkbox changes
            def on_toggle(*args):
                if var.get():
                    status_label.config(text="ON", fg='#008800')
                else:
                    status_label.config(text="OFF", fg='#888888')
            
            var.trace_add('write', on_toggle)
            check.pack(side=tk.LEFT)
            
            return var
        
        # Scrambler
        scrambler_var = create_toggle_row(frame, row, "Scrambler:", 'scrambler')
        row += 1
        
        # Compander
        compander_var = create_toggle_row(frame, row, "Compander:", 'compander')
        row += 1
        
        # VOX
        vox_var = create_toggle_row(frame, row, "VOX:", 'vox')
        row += 1
        
        # PTT ID
        ptt_id_var = create_toggle_row(frame, row, "PTT ID:", 'pttId')
        row += 1
        
        # Busy Lock
        busy_lock_var = create_toggle_row(frame, row, "Busy Lock:", 'busyLock')
        row += 1
        
        # Separator before non-toggle settings
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky='ew', padx=10, pady=15)
        row += 1
        
        # Scan List
        ttk.Label(frame, text="Scan List:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=8)
        scan_list_var = tk.IntVar(value=ch_data.get('scanList', 0))
        scan_list_spin = ttk.Spinbox(frame, from_=0, to=10, textvariable=scan_list_var, width=18)
        scan_list_spin.grid(row=row, column=1, sticky=tk.W, padx=10, pady=8)
        row += 1
        
        # Layout canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _populate_raw_tab(self, ch_data):
        """Populate Raw Data tab with JSON view"""
        # Clear existing widgets
        for widget in self.raw_tab.winfo_children():
            widget.destroy()
        
        # Create frame - use lighter background to match ttk.Frame
        frame = tk.Frame(self.raw_tab, bg='#E8E8E8')
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(frame, yscrollcommand=scrollbar.set, wrap=tk.WORD,
                             font=('Consolas', 9), bg='#F5F5F5')
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Format channel data as JSON
        json_data = json.dumps(ch_data, indent=2, ensure_ascii=False)
        text_widget.insert('1.0', json_data)
        text_widget.config(state=tk.DISABLED)
    
    def _show_context_menu(self, event):
        """Show right-click context menu for bulk operations"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        # Filter out group nodes (Analog Channels, DMR Channels)
        channel_items = [item for item in selection if self.channel_tree.item(item, 'tags')]
        
        if not channel_items:
            return
        
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        
        if len(channel_items) == 1:
            context_menu.add_command(label="Duplicate Channel", command=self._bulk_duplicate)
            context_menu.add_command(label="Delete Channel", command=self._bulk_delete)
        else:
            context_menu.add_command(
                label=f"Duplicate {len(channel_items)} Channels", 
                command=self._bulk_duplicate
            )
            context_menu.add_command(
                label=f"Delete {len(channel_items)} Channels", 
                command=self._bulk_delete
            )
        
        # Display menu at mouse position
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _bulk_delete(self):
        """Delete selected channels"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        # Filter out group nodes and get channel IDs
        channel_ids = []
        for item in selection:
            tags = self.channel_tree.item(item, 'tags')
            if tags:
                channel_ids.append(tags[0])
        
        if not channel_ids:
            return
        
        # Confirm deletion
        if len(channel_ids) == 1:
            ch_name = self.channels[channel_ids[0]].get('channelName', '').rstrip('\u0000').strip()
            message = f"Delete channel {channel_ids[0]} ({ch_name or '(empty)'})?"
        else:
            message = f"Delete {len(channel_ids)} selected channels?"
        
        if not messagebox.askyesno("Confirm Delete", message, parent=self.root):
            return
        
        # Save state before deletion for undo
        self._save_state("Delete channels")
        
        # Delete channels from data
        for ch_id in channel_ids:
            if ch_id in self.channels:
                del self.channels[ch_id]
        
        # Rebuild tree
        self._rebuild_channel_tree()
        
        # Update status
        self.status_label.config(text=f"Deleted {len(channel_ids)} channel(s) | Total: {len(self.channels)}")
    
    def _bulk_duplicate(self):
        """Duplicate selected channels - insert immediately after source channels"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        # Filter out group nodes and get channel IDs (sorted by channel number)
        channel_ids = []
        for item in selection:
            tags = self.channel_tree.item(item, 'tags')
            if tags and tags[0] in self.channels:
                channel_ids.append(tags[0])
        
        if not channel_ids:
            return
        
        # Sort by channel number (ascending) to process in order
        channel_ids.sort(key=lambda x: int(x))
        
        # Save state before duplication for undo
        self._save_state("Duplicate channels")
        
        existing_ids = [int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()]
        
        # Track the first duplicated channel to select it afterwards
        first_duplicate_id = None
        duplicated_count = 0
        
        # Process each channel to duplicate (in reverse order to handle shifting correctly)
        for ch_id in reversed(channel_ids):
            if ch_id not in self.channels:
                continue
            
            source_num = int(ch_id)
            insert_at = source_num + 1
            
            # Shift all channels >= insert_at up by 1 to make room
            channels_to_shift = sorted([i for i in existing_ids if i >= insert_at], reverse=True)
            
            for ch_num in channels_to_shift:
                old_id = str(ch_num)
                new_id = str(ch_num + 1)
                
                if old_id in self.channels:
                    ch_data = self.channels.pop(old_id)
                    ch_data['channelLow'] = ch_num + 1
                    self.channels[new_id] = ch_data
            
            # Update existing_ids after shifting
            existing_ids = [int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()]
            
            # Create the duplicate at insert_at
            new_channel = copy.deepcopy(self.channels[ch_id])
            
            # Update channel name to indicate it's a copy
            original_name = new_channel.get('channelName', '').rstrip('\u0000').strip()
            new_name = f"{original_name} (Copy)" if original_name else f"Channel {insert_at}"
            # Truncate to fit 16 chars including null padding
            new_name = new_name[:16].ljust(16, '\u0000')
            new_channel['channelName'] = new_name
            
            # Update channelLow field with new ID
            new_channel['channelLow'] = insert_at
            
            # Add to channels dict
            self.channels[str(insert_at)] = new_channel
            existing_ids.append(insert_at)
            
            # Track first duplicate (will be the last one processed since we're in reverse)
            first_duplicate_id = str(insert_at)
            duplicated_count += 1
        
        # Rebuild tree and select the first duplicated channel
        self._rebuild_channel_tree(reselect_channel_id=first_duplicate_id)
        
        # Update status
        self.status_label.config(text=f"Duplicated {duplicated_count} channel(s), inserted after source | Total: {len(self.channels)}")
    
    def _show_column_selector(self):
        """Show dialog to select which columns to display in the tree"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Columns")
        dialog.geometry("350x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg='SystemButtonFace')
        
        # Header
        header = tk.Label(dialog, text="Choose columns to display:", 
                          font=('Arial', 10, 'bold'))
        header.pack(pady=10, padx=10, anchor='w')
        
        # Frame for checkboxes
        checkbox_frame = tk.Frame(dialog)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        # Create checkbox variables using tk.Checkbutton
        checkbox_vars = {}
        for col_id, col_info in self.available_columns.items():
            var = tk.BooleanVar(value=(col_id in self.selected_columns))
            checkbox_vars[col_id] = var
            
            cb = tk.Checkbutton(checkbox_frame, text=col_info['label'], 
                               variable=var, font=('Arial', 9))
            cb.pack(anchor='w', pady=3)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        def on_ok():
            # Update selected columns
            new_selection = [col_id for col_id, var in checkbox_vars.items() if var.get()]
            
            if not new_selection:
                messagebox.showwarning("No Columns", 
                                      "Please select at least one column to display.",
                                      parent=dialog)
                return
            
            self.selected_columns = new_selection
            self._configure_tree_columns()
            self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="OK", command=on_ok, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, width=8).pack(side=tk.LEFT, padx=5)
        
        # Center dialog on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")


    def _navigate_channel_up(self, event):
        """Navigate to previous channel"""
        selection = self.channel_tree.selection()
        if not selection:
            return 'break'
        current_item = selection[0]
        prev_item = self.channel_tree.prev(current_item)
        if prev_item:
            # Check if prev item is a group node
            if not self.channel_tree.item(prev_item, 'tags'):
                # It's a group, get the last child
                children = self.channel_tree.get_children(prev_item)
                if children:
                    prev_item = children[-1]
                else:
                    return 'break'
            self.channel_tree.selection_set(prev_item)
            self.channel_tree.focus(prev_item)
            self.channel_tree.see(prev_item)
        return 'break'  # Prevent default treeview behavior
    
    def _navigate_channel_down(self, event):
        """Navigate to next channel"""
        selection = self.channel_tree.selection()
        if not selection:
            return 'break'
        current_item = selection[0]
        next_item = self.channel_tree.next(current_item)
        if next_item:
            # Check if next item is a group node
            if not self.channel_tree.item(next_item, 'tags'):
                # It's a group, get the first child
                children = self.channel_tree.get_children(next_item)
                if children:
                    next_item = children[0]
                else:
                    return 'break'
            self.channel_tree.selection_set(next_item)
            self.channel_tree.focus(next_item)
            self.channel_tree.see(next_item)
        return 'break'  # Prevent default treeview behavior
    
    def _navigate_tab_left(self, event):
        """Navigate to previous tab"""
        current_tab = self.detail_notebook.index(self.detail_notebook.select())
        if current_tab > 0:
            self.detail_notebook.select(current_tab - 1)
    
    def _navigate_tab_right(self, event):
        """Navigate to next tab"""
        current_tab = self.detail_notebook.index(self.detail_notebook.select())
        if current_tab < self.detail_notebook.index('end') - 1:
            self.detail_notebook.select(current_tab + 1)
    
    def _on_channel_name_changed(self):
        """Handle channel name changes (called on each keystroke)
        
        Forces truncation to 11 characters per PMR-171 protocol.
        """
        if self.current_channel and self.current_channel in self.channels:
            raw_name = self.current_channel_name.get()
            
            # Force truncation to protocol limit (11 chars)
            truncated_name = truncate_channel_name(raw_name)
            
            # Update channel data with properly formatted name
            self.channels[self.current_channel]['channelName'] = format_channel_name_for_storage(truncated_name)
            
            # Update header
            display_name = truncated_name.strip() or "(empty)"
            self.detail_header.config(text=f"Channel {self.current_channel} - {display_name}")
            
            # If name was truncated, update the entry field to show truncated version
            if raw_name != truncated_name and len(raw_name) > PMR171_MAX_CHANNEL_NAME_LENGTH:
                # Set the truncated name in the entry (will trigger this again but won't loop)
                self.current_channel_name.set(truncated_name)
    
    def _on_channel_name_focus_out(self):
        """Handle when channel name entry loses focus - rebuild tree and save state"""
        if self.current_channel:
            # Save state for undo (name change completed)
            self._save_state("Rename channel")
            self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _on_frequency_focus_out(self, freq_var: tk.StringVar, field_prefix: str, entry_widget):
        """Handle when frequency entry loses focus - validate and save frequency
        
        Args:
            freq_var: StringVar containing the frequency value
            field_prefix: Prefix for frequency fields (e.g., 'vfoaFrequency' or 'vfobFrequency')
            entry_widget: The entry widget for visual feedback
        """
        if not self.current_channel or self.current_channel not in self.channels:
            return
        
        freq_str = freq_var.get().strip()
        
        # Remove any warning symbols
        freq_str = freq_str.replace(' ⚠', '').strip()
        
        try:
            # Parse the frequency
            freq_mhz = float(freq_str)
            
            # Validate range (1 MHz to 1000 MHz reasonable for this radio)
            if freq_mhz < 1 or freq_mhz > 1000:
                # Show warning but still allow the value
                entry_widget.config(foreground='#CC0000')
                self.status_label.config(text=f"Warning: Frequency {freq_mhz} MHz may be out of range")
            else:
                # Reset to normal color
                entry_widget.config(foreground='black')
            
            # Convert to bytes using the frequency utility
            from ..utils.frequency import frequency_to_bytes
            f1, f2, f3, f4 = frequency_to_bytes(freq_mhz)
            
            # Get current values to check if changed
            ch_data = self.channels[self.current_channel]
            old_f1 = ch_data.get(f'{field_prefix}1', 0)
            old_f2 = ch_data.get(f'{field_prefix}2', 0)
            old_f3 = ch_data.get(f'{field_prefix}3', 0)
            old_f4 = ch_data.get(f'{field_prefix}4', 0)
            
            # Only save state and update if value actually changed
            if (f1, f2, f3, f4) != (old_f1, old_f2, old_f3, old_f4):
                # Save state for undo
                self._save_state(f"Change {field_prefix}")
                
                # Update channel data
                self.channels[self.current_channel][f'{field_prefix}1'] = f1
                self.channels[self.current_channel][f'{field_prefix}2'] = f2
                self.channels[self.current_channel][f'{field_prefix}3'] = f3
                self.channels[self.current_channel][f'{field_prefix}4'] = f4
                
                # Update the display to show formatted value
                freq_var.set(f"{freq_mhz:.6f}")
                
                # Rebuild tree to update frequency column
                self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
                
                self.status_label.config(text=f"Updated {field_prefix} to {freq_mhz:.6f} MHz")
            
        except ValueError:
            # Invalid frequency - show error and revert to original value
            entry_widget.config(foreground='#CC0000')
            self.status_label.config(text=f"Invalid frequency: '{freq_str}' - reverting")
            
            # Revert to original value from channel data
            ch_data = self.channels[self.current_channel]
            original_freq = self.freq_from_bytes(
                ch_data.get(f'{field_prefix}1', 0),
                ch_data.get(f'{field_prefix}2', 0),
                ch_data.get(f'{field_prefix}3', 0),
                ch_data.get(f'{field_prefix}4', 0)
            )
            freq_var.set(original_freq)
            entry_widget.config(foreground='black')
    
    def _update_field(self, field_name, value):
        """Update a field in the current channel's data"""
        if self.current_channel and self.current_channel in self.channels:
            # Save state before change for undo
            self._save_state(f"Change {field_name}")
            
            self.channels[self.current_channel][field_name] = value
            
            # Auto-set chType based on mode (DMR mode = 9 sets chType to 1, others to 0)
            if field_name == 'vfoaMode':
                if value == 9:  # DMR mode
                    self.channels[self.current_channel]['chType'] = 1
                else:
                    self.channels[self.current_channel]['chType'] = 0
                # Rebuild tree to update Mode column display
                self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
            # Rebuild tree if channel type changed directly (for backwards compatibility)
            elif field_name == 'chType':
                self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _add_channel(self):
        """Add a new channel - behavior depends on what's selected:
        - Empty slot selected: Fill that slot with a new channel (copy from nearest channel)
        - Enabled channel selected: Insert a copy immediately after, shifting subsequent channels up
        - No selection: Add at the end (copy from last channel)
        """
        # Get current selection
        selection = self.channel_tree.selection()
        selected_id = None
        is_empty_slot = False
        
        if selection:
            item = selection[0]
            tags = self.channel_tree.item(item, 'tags')
            if tags:
                selected_id = tags[0]
                # Check if it's an empty slot
                is_empty_slot = selected_id not in self.channels
        
        # Save state for undo
        self._save_state("Add channel")
        
        existing_ids = [int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()]
        
        if is_empty_slot and selected_id:
            # Case 1: Empty slot selected - fill that slot
            target_id = int(selected_id)
            
            # Find nearest existing channel to copy from
            source_channel = None
            source_id = None
            if existing_ids:
                # Find closest channel below this slot
                lower_ids = [i for i in existing_ids if i < target_id]
                upper_ids = [i for i in existing_ids if i > target_id]
                
                if lower_ids:
                    source_id = str(max(lower_ids))
                elif upper_ids:
                    source_id = str(min(upper_ids))
                
                if source_id:
                    source_channel = self.channels[source_id]
            
            if source_channel:
                new_channel = copy.deepcopy(source_channel)
            else:
                new_channel = self._create_default_channel()
            
            new_channel['channelLow'] = target_id
            new_channel['channelName'] = f'NEW CH {target_id}'.ljust(16, '\u0000')[:16]
            
            self.channels[selected_id] = new_channel
            self._rebuild_channel_tree(reselect_channel_id=selected_id)
            self.status_label.config(text=f"Enabled channel {target_id} | Total: {len(self.channels)}")
            
        elif selected_id and selected_id in self.channels:
            # Case 2: Enabled channel selected - insert after, shift subsequent channels up
            current_num = int(selected_id)
            insert_at = current_num + 1
            
            # Check if the next slot is free
            if str(insert_at) not in self.channels:
                # Next slot is free - just insert there
                source_channel = self.channels[selected_id]
                new_channel = copy.deepcopy(source_channel)
                new_channel['channelLow'] = insert_at
                new_channel['channelName'] = f'NEW CH {insert_at}'.ljust(16, '\u0000')[:16]
                self.channels[str(insert_at)] = new_channel
                self._rebuild_channel_tree(reselect_channel_id=str(insert_at))
                self.status_label.config(text=f"Inserted channel {insert_at} (copied from CH {selected_id}) | Total: {len(self.channels)}")
            else:
                # Need to shift channels up to make room
                # Find all channels >= insert_at and shift them up by 1
                channels_to_shift = sorted([i for i in existing_ids if i >= insert_at], reverse=True)
                
                for ch_num in channels_to_shift:
                    old_id = str(ch_num)
                    new_id = str(ch_num + 1)
                    
                    # Move channel to new slot
                    ch_data = self.channels.pop(old_id)
                    ch_data['channelLow'] = ch_num + 1
                    self.channels[new_id] = ch_data
                
                # Now insert the new channel at insert_at
                source_channel = self.channels[selected_id]  # Original selected channel is unchanged
                new_channel = copy.deepcopy(source_channel)
                new_channel['channelLow'] = insert_at
                new_channel['channelName'] = f'NEW CH {insert_at}'.ljust(16, '\u0000')[:16]
                self.channels[str(insert_at)] = new_channel
                
                self._rebuild_channel_tree(reselect_channel_id=str(insert_at))
                shifted_count = len(channels_to_shift)
                self.status_label.config(text=f"Inserted CH {insert_at}, shifted {shifted_count} channels | Total: {len(self.channels)}")
        else:
            # Case 3: No selection or invalid selection - add at the end
            next_id = max(existing_ids) + 1 if existing_ids else 0
            
            source_channel = None
            source_id = None
            if existing_ids:
                source_id = str(max(existing_ids))
                source_channel = self.channels[source_id]
            
            if source_channel:
                new_channel = copy.deepcopy(source_channel)
            else:
                new_channel = self._create_default_channel()
            
            new_channel['channelLow'] = next_id
            new_channel['channelName'] = f'NEW CH {next_id}'.ljust(16, '\u0000')[:16]
            
            self.channels[str(next_id)] = new_channel
            self._rebuild_channel_tree(reselect_channel_id=str(next_id))
            
            if source_id:
                self.status_label.config(text=f"Added channel {next_id} (copied from CH {source_id}) | Total: {len(self.channels)}")
            else:
                self.status_label.config(text=f"Added new channel {next_id} | Total: {len(self.channels)}")
    
    def _create_default_channel(self):
        """Create a new channel with default values (based on PMR-171 format)"""
        return {
            'channelLow': 0,
            'channelHigh': 0,
            'channelName': 'NEW CH'.ljust(16, '\u0000')[:16],
            'chType': 0,  # Analog
            'vfoaMode': 6,  # NFM
            'vfobMode': 6,
            'vfoaFrequency1': 0x1A,  # 446.000000 MHz (default FRS/PMR446)
            'vfoaFrequency2': 0x98,
            'vfoaFrequency3': 0x96,
            'vfoaFrequency4': 0x80,
            'vfobFrequency1': 0x1A,  # Same as RX
            'vfobFrequency2': 0x98,
            'vfobFrequency3': 0x96,
            'vfobFrequency4': 0x80,
            'vfoaPower': 0,  # Low
            'vfobPower': 0,
            'vfoaBandwidth': 0,  # Narrow
            'vfobBandwidth': 0,
            'vfoaSquelchMode': 0,  # Carrier
            'vfobSquelchMode': 0,
            'rxCtcss': 0,  # Off
            'txCtcss': 0,
            'rxCc': 1,  # Color Code 1
            'txCc': 1,
            'ownId1': 0,
            'ownId2': 0,
            'ownId3': 0,
            'ownId4': 0,
            'callId1': 0,
            'callId2': 0,
            'callId3': 0,
            'callId4': 0,
            'slot': 1,  # Timeslot 1
            'emergency': 0,
            'scrambler': 0,
            'compander': 0,
            'vox': 0,
            'pttId': 0,
            'busyLock': 0,
            'scanList': 0
        }
    
    def _move_channel_up(self):
        """Decrease channel number by 1 (swap with channel above if occupied)"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        # Get selected channel ID
        item = selection[0]
        tags = self.channel_tree.item(item, 'tags')
        if not tags:
            return  # Group node selected
        
        current_id = tags[0]
        
        # Check if this is an empty slot
        if current_id not in self.channels:
            self.status_label.config(text="Cannot move empty slot")
            return
        
        current_num = int(current_id)
        new_num = current_num - 1
        
        # Can't go below 0
        if new_num < 0:
            self.status_label.config(text="Channel number cannot be less than 0")
            return
        
        new_id = str(new_num)
        
        # Save state for undo
        self._save_state("Move channel up")
        
        # Check if the new slot is occupied - if so, swap
        if new_id in self.channels:
            # Swap the two channels
            other_channel = self.channels.pop(new_id)
            current_channel = self.channels.pop(current_id)
            
            # Update channelLow values
            current_channel['channelLow'] = new_num
            other_channel['channelLow'] = current_num
            
            # Put them back in swapped positions
            self.channels[new_id] = current_channel
            self.channels[current_id] = other_channel
            
            self.status_label.config(text=f"Swapped channels {current_num} ↔ {new_num}")
        else:
            # Move to empty slot
            channel_data = self.channels.pop(current_id)
            channel_data['channelLow'] = new_num
            self.channels[new_id] = channel_data
            
            self.status_label.config(text=f"Moved channel: {current_num} → {new_num}")
        
        # Rebuild tree and select the moved channel
        self._rebuild_channel_tree(reselect_channel_id=new_id)
        
        # Update current_channel to follow the moved channel
        self.current_channel = new_id
    
    def _on_show_empty_changed(self):
        """Handle 'Show empty channels' checkbox - disable other filters"""
        if self.show_empty_channels.get():
            # Uncheck other filters
            self.group_by_type.set(False)
            self.group_by_mode.set(False)
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _on_group_by_type_changed(self):
        """Handle 'Group by DMR' checkbox - disable other filters"""
        if self.group_by_type.get():
            # Uncheck other filters
            self.show_empty_channels.set(False)
            self.group_by_mode.set(False)
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _on_group_by_mode_changed(self):
        """Handle 'Group by mode' checkbox - disable other filters"""
        if self.group_by_mode.get():
            # Uncheck other filters
            self.show_empty_channels.set(False)
            self.group_by_type.set(False)
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _on_search_changed(self):
        """Handle search text changes - filter tree in real-time"""
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    # === Radio Selection Methods ===
    
    def _select_all_for_radio(self):
        """Select all visible channels for radio read/write"""
        count = 0
        for ch_id in self.channels.keys():
            if ch_id not in self.channel_checkboxes:
                self.channel_checkboxes[ch_id] = tk.BooleanVar(value=True)
            else:
                self.channel_checkboxes[ch_id].set(True)
            count += 1
        self._update_selection_count()
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        self.status_label.config(text=f"Selected all {count} channels for radio operation")
    
    def _deselect_all_for_radio(self):
        """Deselect all channels for radio read/write"""
        for var in self.channel_checkboxes.values():
            var.set(False)
        self._update_selection_count()
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        self.status_label.config(text="Deselected all channels")
    
    def _select_active_channels(self):
        """Select only active/programmed channels (skip empty slots)
        
        A channel is considered "programmed" if it has a non-empty name.
        Channels with blank names or "(empty)" names are skipped.
        """
        # First deselect all
        for var in self.channel_checkboxes.values():
            var.set(False)
        
        count = 0
        for ch_id, ch_data in self.channels.items():
            # Check if channel is programmed by checking if it has a meaningful name
            # Empty channels have blank names (just null chars or whitespace)
            ch_name = ch_data.get('channelName', '').rstrip('\u0000').strip()
            is_programmed = bool(ch_name)  # Non-empty name means programmed
            
            if ch_id not in self.channel_checkboxes:
                self.channel_checkboxes[ch_id] = tk.BooleanVar(value=is_programmed)
            else:
                self.channel_checkboxes[ch_id].set(is_programmed)
            
            if is_programmed:
                count += 1
        
        self._update_selection_count()
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        self.status_label.config(text=f"Selected {count} programmed channels (skipped empty)")
    
    def _select_active_range(self):
        """Select all channels from first to last programmed (including empty slots in between)"""
        # First deselect all
        for var in self.channel_checkboxes.values():
            var.set(False)
        
        # Find first and last active channel
        active_ids = []
        for ch_id, ch_data in self.channels.items():
            is_active = (ch_data.get('vfoaMode', 255) != 255 and 
                        (ch_data.get('vfoaFrequency1', 0) != 0 or 
                         ch_data.get('vfoaFrequency2', 0) != 0))
            if is_active and ch_id.isdigit():
                active_ids.append(int(ch_id))
        
        if not active_ids:
            self.status_label.config(text="No programmed channels found")
            return
        
        first_active = min(active_ids)
        last_active = max(active_ids)
        
        count = 0
        for ch_id in self.channels.keys():
            if ch_id.isdigit():
                ch_num = int(ch_id)
                in_range = first_active <= ch_num <= last_active
                
                if ch_id not in self.channel_checkboxes:
                    self.channel_checkboxes[ch_id] = tk.BooleanVar(value=in_range)
                else:
                    self.channel_checkboxes[ch_id].set(in_range)
                
                if in_range:
                    count += 1
        
        self._update_selection_count()
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        self.status_label.config(text=f"Selected range {first_active}-{last_active} ({count} channels, including empty slots)")
    
    def _select_channel_range(self):
        """Select channels within the specified From/To range
        
        If the To: value exceeds existing channels, new empty channels are created
        up to that number and selected. All channels in the range are selected,
        including empty slots.
        """
        try:
            from_ch = int(self.range_from_var.get())
            to_ch = int(self.range_to_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Range", 
                                  "Please enter valid channel numbers.",
                                  parent=self.root)
            return
        
        if from_ch > to_ch:
            from_ch, to_ch = to_ch, from_ch  # Swap if reversed
        
        # Get current max channel number
        existing_ids = [int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()]
        max_existing = max(existing_ids) if existing_ids else -1
        
        # Create new empty channels if range extends beyond existing
        new_channels_created = 0
        need_undo_save = to_ch > max_existing or any(str(ch) not in self.channels for ch in range(from_ch, min(to_ch + 1, max_existing + 1)))
        
        if need_undo_save:
            # Save state for undo since we're creating channels
            self._save_state("Create channels for range selection")
        
        # Create ALL channels in range (including gaps)
        for ch_num in range(from_ch, to_ch + 1):
            ch_id = str(ch_num)
            if ch_id not in self.channels:
                # Create empty channel
                new_channel = self._create_default_channel()
                new_channel['channelLow'] = ch_num
                new_channel['channelName'] = ''.ljust(16, '\u0000')[:16]  # Empty name
                self.channels[ch_id] = new_channel
                new_channels_created += 1
        
        # First deselect all
        for var in self.channel_checkboxes.values():
            var.set(False)
        
        # Select ALL channels in range (including empty ones)
        count = 0
        for ch_num in range(from_ch, to_ch + 1):
            ch_id = str(ch_num)
            # All channels in range should now exist (created above if needed)
            if ch_id not in self.channel_checkboxes:
                self.channel_checkboxes[ch_id] = tk.BooleanVar(value=True)
            else:
                self.channel_checkboxes[ch_id].set(True)
            count += 1
        
        self._update_selection_count()
        self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
        
        # Build status message
        if new_channels_created > 0:
            self.status_label.config(text=f"Selected range {from_ch}-{to_ch} ({count} channels, created {new_channels_created} new)")
        else:
            self.status_label.config(text=f"Selected range {from_ch}-{to_ch} ({count} channels)")
    
    def _update_selection_count(self):
        """Update the selection count label"""
        count = sum(1 for var in self.channel_checkboxes.values() if var.get())
        if hasattr(self, 'selection_count_label'):
            self.selection_count_label.config(text=f"Selected: {count}")
    
    def _get_selected_channel_ids(self) -> List[str]:
        """Get list of channel IDs selected for radio operation
        
        Returns:
            List of channel ID strings that are selected
        """
        selected = []
        for ch_id, var in self.channel_checkboxes.items():
            if var.get() and ch_id in self.channels:
                selected.append(ch_id)
        return sorted(selected, key=lambda x: int(x) if x.isdigit() else 0)
    
    def _on_tree_click(self, event):
        """Handle click on tree - toggle checkbox if clicking on R/W column (#0)"""
        # Identify the clicked region
        region = self.channel_tree.identify_region(event.x, event.y)
        
        # Get the column - #0 is the tree column (R/W checkbox)
        column = self.channel_tree.identify_column(event.x)
        
        # Check if it's the R/W checkbox column (#0)
        if column == '#0':
            # Get the item
            item = self.channel_tree.identify_row(event.y)
            if not item:
                return
            
            tags = self.channel_tree.item(item, 'tags')
            if not tags:
                return  # Group node
            
            ch_id = tags[0]
            
            # Toggle the checkbox
            if ch_id not in self.channel_checkboxes:
                self.channel_checkboxes[ch_id] = tk.BooleanVar(value=True)
            else:
                current = self.channel_checkboxes[ch_id].get()
                self.channel_checkboxes[ch_id].set(not current)
            
            # Update the display (text field is column #0)
            new_state = self.channel_checkboxes[ch_id].get()
            new_checkbox = '☑' if new_state else '☐'
            self.channel_tree.item(item, text=new_checkbox)
            
            # Update count
            self._update_selection_count()
    
    def _get_checkbox_display(self, ch_id: str) -> str:
        """Get the checkbox display character for a channel
        
        Args:
            ch_id: Channel ID
            
        Returns:
            '☑' if selected, '☐' otherwise
        """
        if ch_id in self.channel_checkboxes and self.channel_checkboxes[ch_id].get():
            return '☑'
        return '☐'
    
    def _move_channel_down(self):
        """Increase channel number by 1 (swap with channel below if occupied)"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        # Get selected channel ID
        item = selection[0]
        tags = self.channel_tree.item(item, 'tags')
        if not tags:
            return  # Group node selected
        
        current_id = tags[0]
        
        # Check if this is an empty slot
        if current_id not in self.channels:
            self.status_label.config(text="Cannot move empty slot")
            return
        
        current_num = int(current_id)
        new_num = current_num + 1
        new_id = str(new_num)
        
        # Save state for undo
        self._save_state("Move channel down")
        
        # Check if the new slot is occupied - if so, swap
        if new_id in self.channels:
            # Swap the two channels
            other_channel = self.channels.pop(new_id)
            current_channel = self.channels.pop(current_id)
            
            # Update channelLow values
            current_channel['channelLow'] = new_num
            other_channel['channelLow'] = current_num
            
            # Put them back in swapped positions
            self.channels[new_id] = current_channel
            self.channels[current_id] = other_channel
            
            self.status_label.config(text=f"Swapped channels {current_num} ↔ {new_num}")
        else:
            # Move to empty slot
            channel_data = self.channels.pop(current_id)
            channel_data['channelLow'] = new_num
            self.channels[new_id] = channel_data
            
            self.status_label.config(text=f"Moved channel: {current_num} → {new_num}")
        
        # Rebuild tree and select the moved channel
        self._rebuild_channel_tree(reselect_channel_id=new_id)
        
        # Update current_channel to follow the moved channel
        self.current_channel = new_id

def view_channel_file(json_path: Path, title: str = None):
    """Load and view a PMR-171 JSON file
    
    Args:
        json_path: Path to JSON file
        title: Window title (defaults to filename)
    """
    if not json_path.exists():
        print(f"Error: {json_path} not found!")
        return
    
    print(f"Loading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle new format with metadata
    if 'channels' in data:
        channels = data['channels']
        # TODO: Use radio_profile and radio_metadata for configuration
    else:
        # Legacy format - entire file is channels dict
        channels = data
    
    if title is None:
        title = "PMR-171 CPS"
    
    viewer = ChannelTableViewer(channels, title)
    viewer.current_file = json_path  # Set the file path for the banner display
    viewer.show()
