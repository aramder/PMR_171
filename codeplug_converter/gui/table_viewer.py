"""Professional radio programming GUI for channel data"""

import copy
import csv
import json
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..utils.validation import validate_channel, get_frequency_band_name


class ChannelTableViewer:
    """Professional radio programming interface with tree navigation and tabbed detail view"""
    
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
    
    def __init__(self, channels: Dict[str, Dict], title: str = "Radio Programming Software"):
        """Initialize professional viewer
        
        Args:
            channels: Dictionary of channel data
            title: Window title
            radio_config: RadioConfig instance (defaults to PMR-171 if not specified)
        """
        self.channels = channels
        self.title = title
        self.selected_channel: Optional[str] = None
        self.current_channel: Optional[str] = None  # Track current channel for updates
        self.root = None
        self.channel_tree = None
        self.detail_notebook = None
        
        # Undo/Redo stacks - each entry is a deep copy of self.channels
        self.undo_stack: List[Dict[str, Dict]] = []
        self.redo_stack: List[Dict[str, Dict]] = []
        self.max_undo_levels = 50  # Limit memory usage
        
        # Available columns for tree view (ordered as desired)
        self.available_columns = {
            'name': {'label': 'Name', 'width': 120, 'extract': lambda ch: ch.get('channelName', '').rstrip('\u0000').strip() or "(empty)"},
            'rx_freq': {'label': 'RX Freq', 'width': 90, 'extract': lambda ch: self.freq_from_bytes(ch['vfoaFrequency1'], ch['vfoaFrequency2'], ch['vfoaFrequency3'], ch['vfoaFrequency4'])},
            'rx_ctcss': {'label': 'RX CTCSS/DCS', 'width': 90, 'extract': lambda ch: self.ctcss_dcs_from_value(ch.get('rxCtcss', 0))},
            'tx_freq': {'label': 'TX Freq', 'width': 90, 'extract': lambda ch: self.freq_from_bytes(ch['vfobFrequency1'], ch['vfobFrequency2'], ch['vfobFrequency3'], ch['vfobFrequency4'])},
            'tx_ctcss': {'label': 'TX CTCSS/DCS', 'width': 90, 'extract': lambda ch: self.ctcss_dcs_from_value(ch.get('txCtcss', ch.get('rxCtcss', 0)))},
            'mode': {'label': 'Mode', 'width': 60, 'extract': lambda ch: self.CHANNEL_TYPES.get(ch.get('chType', 0), 'Unknown')},
            'power': {'label': 'Power', 'width': 70, 'extract': lambda ch: self.POWER_LEVELS.get(ch.get('power', 0), 'Unknown')},
            'bandwidth': {'label': 'Bandwidth', 'width': 90, 'extract': lambda ch: ch.get('bandwidth', 'N/A')}
        }
        
        # Default selected columns (shown by default)
        self.selected_columns = ['name', 'rx_freq', 'mode']
        
        # Style colors matching professional radio software
        self.colors = {
            'header_bg': '#0099CC',  # Professional blue
            'header_fg': 'white',
            'selected_bg': '#0066CC',
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
        
        Based on RadioReference wiki: https://wiki.radioreference.com/index.php/Offset
        
        Args:
            freq_mhz: Frequency in MHz
            
        Returns:
            Standard offset in MHz (positive or negative)
        """
        # 10m Ham (29.5-29.7 MHz): -100 kHz
        if 29.5 <= freq_mhz <= 29.7:
            return -0.1
        
        # 6m Ham (50-54 MHz): -500 kHz (using -0.5 as more common)
        if 50 <= freq_mhz <= 54:
            return -0.5
        
        # 2m Ham (144-148 MHz): ±600 kHz (using +0.6 as default)
        if 144 <= freq_mhz <= 148:
            return 0.6
        
        # 220 MHz (220-222 MHz): +1 MHz
        if 220 <= freq_mhz <= 222:
            return 1.0
        
        # 1.25m Ham (222-225 MHz): -1.6 MHz
        if 222 <= freq_mhz <= 225:
            return -1.6
        
        # 380 MHz Federal LMR (380-400 MHz): +10 MHz
        if 380 <= freq_mhz <= 400:
            return 10.0
        
        # Federal UHF (406.1-420 MHz): +9 MHz
        if 406.1 <= freq_mhz <= 420:
            return 9.0
        
        # 70cm Ham (440-450 MHz): +5 MHz (default, -5 MHz also used)
        if 440 <= freq_mhz <= 450:
            return 5.0
        
        # UHF Canadian border (420-430 MHz): +5 MHz
        if 420 <= freq_mhz <= 430:
            return 5.0
        
        # UHF (450-470 MHz): +5 MHz
        if 450 <= freq_mhz <= 470:
            return 5.0
        
        # UHF-T (470-512 MHz): +3 MHz
        if 470 <= freq_mhz <= 512:
            return 3.0
        
        # Lower 700 MHz (698-746 MHz): +30 MHz
        if 698 <= freq_mhz <= 746:
            return 30.0
        
        # Upper 700 MHz (746-806 MHz): +30 MHz
        if 746 <= freq_mhz <= 806:
            return 30.0
        
        # 800 MHz (806-896 MHz): -45 MHz
        if 806 <= freq_mhz <= 896:
            return -45.0
        
        # 900 MHz (896-940 MHz): -39 MHz
        if 896 <= freq_mhz <= 940:
            return -39.0
        
        # 33cm Ham (902-928 MHz): -12 MHz (default, -25 MHz also used)
        if 902 <= freq_mhz <= 928:
            return -12.0
        
        # 23cm Ham (1240-1300 MHz): -12 MHz (default, -20 MHz also used)
        if 1240 <= freq_mhz <= 1300:
            return -12.0
        
        # No standard offset for this frequency
        return 0.0
    
    def show(self):
        """Display the professional radio programming interface"""
        if not self.channels:
            print("No channels to display!")
            return
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("1600x900")
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / 'assets' / 'LV_black.png'
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
                 indicatorcolor=[('selected', '#0066CC'), ('!selected', '#FFFFFF')],
                 indicatorrelief=[('selected', 'flat'), ('!selected', 'sunken')],
                 background=[('active', '#E8E8E8')])

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
    
    def _create_tree_navigation(self, parent):
        """Create tree navigation panel (left side)"""
        # Header
        header = ttk.Label(parent, text="Channels", style='Header.TLabel')
        header.pack(fill=tk.X)
        
        # Search box
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
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
        
        # View menu
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
                with open(filename, 'r') as f:
                    self.channels = json.load(f)
                self.root.destroy()
                # Restart viewer with new data
                viewer = ChannelTableViewer(self.channels, self.title)
                viewer.show()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def _save_file(self):
        """Save channel data to JSON file"""
        # Generate default filename with current date/time
        now = datetime.now()
        default_filename = f"config_{now.strftime('%y%m%d_%H%M')}.json"
        
        # Get repository root (CodeplugConverter directory)
        repo_root = Path(__file__).parent.parent.parent
        default_path = repo_root / default_filename
        
        filename = filedialog.asksaveasfilename(
            title="Save Channel Data",
            initialdir=str(repo_root),
            initialfile=default_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.channels, f, indent=2)
                messagebox.showinfo("Success", "Channel data saved successfully!")
                self.status_label.config(text=f"Saved to {Path(filename).name}")
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
    
    def _populate_channel_tree(self):
        """Populate the channel tree"""
        self._configure_tree_columns()
        self._rebuild_channel_tree()
    
    def _configure_tree_columns(self):
        """Configure tree columns based on selected columns"""
        # Configure channel number column
        self.channel_tree.heading('#0', text='Ch')
        self.channel_tree.column('#0', width=50)
        
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
        # Clear existing channel items (keep group nodes)
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        
        # Recreate group nodes
        analog_node = self.channel_tree.insert('', 'end', text='Analog Channels', open=True)
        dmr_node = self.channel_tree.insert('', 'end', text='DMR Channels', open=True)
        
        item_to_select = None
        
        # Add channels
        for ch_id, ch_data in sorted(self.channels.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999):
            # Extract column values
            column_values = []
            for col_id in self.selected_columns:
                if col_id in self.available_columns:
                    extract_func = self.available_columns[col_id]['extract']
                    column_values.append(extract_func(ch_data))
            
            # Determine parent based on channel type
            parent_node = dmr_node if ch_data.get('chType', 0) == 1 else analog_node
            
            # Insert item
            item_id = self.channel_tree.insert(parent_node, 'end',
                text=ch_id,
                values=tuple(column_values),
                tags=(ch_id,)
            )
            
            if reselect_channel_id and ch_id == reselect_channel_id:
                item_to_select = item_id
        
        # Reselect item if requested, or auto-select first channel if none selected
        if item_to_select:
            self.channel_tree.selection_set(item_to_select)
            self.channel_tree.focus(item_to_select)
            self.channel_tree.see(item_to_select)
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
            self.status_label.config(text=f"Total Channels: {len(self.channels)} | Ready")
    
    def _get_first_channel_item(self):
        """Get the first channel item in the tree (skip group nodes)"""
        # Check Analog Channels group first
        for group_node in self.channel_tree.get_children():
            children = self.channel_tree.get_children(group_node)
            if children:
                # Return first child that has tags (is a channel, not a group)
                for child in children:
                    if self.channel_tree.item(child, 'tags'):
                        return child
        return None
    
    def _create_detail_panel(self, parent):
        """Create tabbed detail panel (right side)"""
        # Header with channel info
        self.detail_header = ttk.Label(parent, text="Select a channel to view details", 
                                      style='Header.TLabel')
        self.detail_header.pack(fill=tk.X)
        
        # Notebook for tabs
        self.detail_notebook = ttk.Notebook(parent)
        self.detail_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            status_frame,
            text=f"Total Channels: {len(self.channels)} | Ready",
            padding=5
        )
        self.status_label.pack(side=tk.LEFT)
    
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
        
        self.status_label.config(text=f"Viewing Channel {ch_num}")
    
    def _populate_general_tab(self, ch_data):
        """Populate General Settings tab"""
        # Clear existing widgets
        for widget in self.general_tab.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
        canvas = tk.Canvas(self.general_tab)
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
                                 font=('Arial', 9), foreground='#0066CC')
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
        
        # Channel Type
        ttk.Label(scrollable_frame, text="Channel Type:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        ch_type = self.CHANNEL_TYPES.get(ch_data['chType'], 'Unknown')
        type_combo = ttk.Combobox(scrollable_frame, values=list(self.CHANNEL_TYPES.values()),
                                 state='readonly', width=27)
        type_combo.set(ch_type)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self._update_field('chType', 
            {v: k for k, v in self.CHANNEL_TYPES.items()}[type_combo.get()]))
        type_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Mode
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
        
        # Squelch Mode
        ttk.Label(scrollable_frame, text="Squelch Mode:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        squelch_mode = self.SQUELCH_MODES.get(ch_data.get('vfoaSquelchMode', 0), 'Unknown')
        squelch_combo = ttk.Combobox(scrollable_frame, values=list(self.SQUELCH_MODES.values()),
                                    state='readonly', width=27)
        squelch_combo.set(squelch_mode)
        squelch_combo.bind('<<ComboboxSelected>>', lambda e: self._update_field('vfoaSquelchMode', 
            {v: k for k, v in self.SQUELCH_MODES.items()}[squelch_combo.get()]))
        squelch_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Power Level
        ttk.Label(scrollable_frame, text="Power Level:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        power = self.POWER_LEVELS.get(ch_data.get('vfoaPower', 0), 'Unknown')
        power_combo = ttk.Combobox(scrollable_frame, values=list(self.POWER_LEVELS.values()),
                                  state='readonly', width=27)
        power_combo.set(power)
        power_combo.bind('<<ComboboxSelected>>', lambda e: self._update_field('vfoaPower', 
            {v: k for k, v in self.POWER_LEVELS.items()}[power_combo.get()]))
        power_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Bandwidth
        ttk.Label(scrollable_frame, text="Bandwidth:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        bw = "Narrow (12.5kHz)" if ch_data.get('vfoaBandwidth', 0) == 0 else "Wide (25kHz)"
        bw_combo = ttk.Combobox(scrollable_frame, values=["Narrow (12.5kHz)", "Wide (25kHz)"],
                               state='readonly', width=27)
        bw_combo.set(bw)
        bw_combo.bind('<<ComboboxSelected>>', lambda e: self._update_field('vfoaBandwidth', 
            0 if bw_combo.get() == "Narrow (12.5kHz)" else 1))
        bw_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
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
        
        # Create scrollable frame with matching background
        canvas = tk.Canvas(self.freq_tab, bg='#F5F5F5', highlightthickness=0)
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
            ch_data['vfoaFrequency1'], ch_data['vfoaFrequency2'],
            ch_data['vfoaFrequency3'], ch_data['vfoaFrequency4']
        )
        vfoa_tx_freq_var = tk.StringVar(value=vfoa_tx_freq)
        tx_entry = ttk.Entry(tx_frame, textvariable=vfoa_tx_freq_var, width=20)
        tx_entry.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
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
        
        # Offset display
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
                                font=('Arial', 11, 'bold'), foreground='#0066CC')
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
        
        # Copy RX to TX button (left to right arrow)
        def copy_rx_to_tx():
            vfoa_tx_freq_var.set(vfoa_rx_freq_var.get())
            offset_var.set("+0.000000 MHz")
        
        copy_rx_btn = ttk.Button(tools_frame, text="RX → TX (Simplex)", 
                                command=copy_rx_to_tx)
        copy_rx_btn.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Copy TX to RX button (right to left arrow)
        def copy_tx_to_rx():
            vfoa_rx_freq_var.set(vfob_vfoa_tx_freq_var.get())
            offset_var.set("+0.000000 MHz")
        
        copy_tx_btn = ttk.Button(tools_frame, text="RX ← TX",
                                command=copy_tx_to_rx)
        copy_tx_btn.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient='horizontal').grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        tools_row += 1
        
        # Offset field section
        ttk.Label(tools_frame, text="Offset (MHz):", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        tools_row += 1
        
        # Calculate standard offset based on RX frequency
        try:
            rx_freq_float = float(vfoa_rx_freq_var.get().split()[0])
            suggested_offset = self.get_standard_offset(rx_freq_float)
        except (ValueError, IndexError):
            suggested_offset = 0.0
        
        custom_offset_var = tk.StringVar(value=f"{suggested_offset:.1f}")
        custom_offset_entry = ttk.Entry(tools_frame, textvariable=custom_offset_var, 
                                       width=15, font=('Arial', 10))
        custom_offset_entry.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Preset offset buttons in a grid
        preset_frame = ttk.Frame(tools_frame)
        preset_frame.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        def set_offset(value):
            custom_offset_var.set(f"{value:.1f}")
        
        btn_plus5 = ttk.Button(preset_frame, text="+5.0", command=lambda: set_offset(5.0), width=7)
        btn_plus5.grid(row=0, column=0, padx=2, pady=2)
        
        btn_minus06 = ttk.Button(preset_frame, text="-0.6", command=lambda: set_offset(-0.6), width=7)
        btn_minus06.grid(row=0, column=1, padx=2, pady=2)
        
        btn_minus5 = ttk.Button(preset_frame, text="-5.0", command=lambda: set_offset(-5.0), width=7)
        btn_minus5.grid(row=0, column=2, padx=2, pady=2)
        
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
        
        # Apply offset RX to TX (left to right with offset)
        def apply_offset_rx_to_tx():
            try:
                rx_freq = float(vfoa_rx_freq_var.get().split()[0])
                offset_mhz = float(custom_offset_var.get())
                new_tx = rx_freq + offset_mhz
                tx_band = self.validation_module.get_frequency_band_name(new_tx)
                vfoa_tx_freq_var.set(f"{new_tx:.6f} ({tx_band})")
                offset_var.set(f"{offset_mhz:+.6f} MHz")
            except (ValueError, IndexError):
                pass
        
        btn_offset_right = ttk.Button(tools_frame, text="RX → TX + Offset",
                                     command=apply_offset_rx_to_tx)
        btn_offset_right.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Apply offset TX to RX (right to left with offset)
        def apply_offset_tx_to_rx():
            try:
                tx_freq = float(vfob_vfoa_tx_freq_var.get().split()[0])
                offset_mhz = float(custom_offset_var.get())
                new_rx = tx_freq + offset_mhz
                rx_band = self.validation_module.get_frequency_band_name(new_rx)
                vfoa_rx_freq_var.set(f"{new_rx:.6f} ({rx_band})")
                offset_var.set(f"{-offset_mhz:+.6f} MHz")
            except (ValueError, IndexError):
                pass
        
        btn_offset_left = ttk.Button(tools_frame, text="RX ← TX + Offset",
                                    command=apply_offset_tx_to_rx)
        btn_offset_left.grid(row=tools_row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        tools_row += 1
        
        # Layout canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _populate_dmr_tab(self, ch_data):
        """Populate DMR Settings tab"""
        # Clear existing widgets
        for widget in self.dmr_tab.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.dmr_tab, padding=10)
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
    
    def _populate_advanced_tab(self, ch_data):
        """Populate Advanced Settings tab"""
        # Clear existing widgets
        for widget in self.advanced_tab.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.advanced_tab, padding=10)
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
    
    def _populate_raw_tab(self, ch_data):
        """Populate Raw Data tab with JSON view"""
        # Clear existing widgets
        for widget in self.raw_tab.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.raw_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(frame, yscrollcommand=scrollbar.set, wrap=tk.WORD,
                             font=('Consolas', 9))
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
        """Duplicate selected channels"""
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
        
        # Save state before duplication for undo
        self._save_state("Duplicate channels")
        
        # Find next available channel ID
        existing_ids = [int(ch_id) for ch_id in self.channels.keys() if ch_id.isdigit()]
        next_id = max(existing_ids) + 1 if existing_ids else 0
        
        # Duplicate each selected channel
        duplicated_count = 0
        for ch_id in channel_ids:
            if ch_id in self.channels:
                # Create a deep copy of the channel
                import copy
                new_channel = copy.deepcopy(self.channels[ch_id])
                
                # Update channel name to indicate it's a copy
                original_name = new_channel.get('channelName', '').rstrip('\u0000').strip()
                new_name = f"{original_name} (Copy)" if original_name else f"Channel {next_id}"
                new_channel['channelName'] = new_name.ljust(16, '\u0000')  # Pad to 16 chars
                
                # Update channelLow field with new ID
                new_channel['channelLow'] = next_id
                
                # Add to channels dict
                self.channels[str(next_id)] = new_channel
                next_id += 1
                duplicated_count += 1
        
        # Rebuild tree
        self._rebuild_channel_tree()
        
        # Update status
        self.status_label.config(text=f"Duplicated {duplicated_count} channel(s) | Total: {len(self.channels)}")
    
    def _show_column_selector(self):
        """Show dialog to select which columns to display in the tree"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Columns")
        dialog.geometry("350x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = ttk.Label(dialog, text="Choose columns to display:", 
                          font=('Arial', 10, 'bold'))
        header.pack(pady=10, padx=10, anchor='w')
        
        # Frame for checkboxes
        checkbox_frame = ttk.Frame(dialog)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        # Create checkbox variables
        checkbox_vars = {}
        for col_id, col_info in self.available_columns.items():
            var = tk.BooleanVar(value=(col_id in self.selected_columns))
            checkbox_vars[col_id] = var
            
            cb = ttk.Checkbutton(checkbox_frame, text=col_info['label'], 
                                variable=var)
            cb.pack(anchor='w', pady=3)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
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
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
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
        """Handle channel name changes (called on each keystroke)"""
        if self.current_channel and self.current_channel in self.channels:
            new_name = self.current_channel_name.get()
            # Update channel data
            self.channels[self.current_channel]['channelName'] = new_name.ljust(16, '\u0000')[:16]
            # Update header
            display_name = new_name.strip() or "(empty)"
            self.detail_header.config(text=f"Channel {self.current_channel} - {display_name}")
    
    def _on_channel_name_focus_out(self):
        """Handle when channel name entry loses focus - rebuild tree and save state"""
        if self.current_channel:
            # Save state for undo (name change completed)
            self._save_state("Rename channel")
            self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
    def _update_field(self, field_name, value):
        """Update a field in the current channel's data"""
        if self.current_channel and self.current_channel in self.channels:
            # Save state before change for undo
            self._save_state(f"Change {field_name}")
            
            self.channels[self.current_channel][field_name] = value
            # Rebuild tree if channel type changed
            if field_name == 'chType':
                self._rebuild_channel_tree(reselect_channel_id=self.current_channel)
    
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
        title = f"Channel Viewer - {json_path.name}"
    
    viewer = ChannelTableViewer(channels, title)
    viewer.show()
