"""Professional radio programming GUI for channel data"""

import json
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


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
            channels: Dictionary of PMR-171 channel data
            title: Window title
        """
        self.channels = channels
        self.title = title
        self.selected_channel: Optional[str] = None
        self.current_channel: Optional[str] = None  # Track current channel for updates
        self.root = None
        self.channel_tree = None
        self.detail_notebook = None
        
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
    
    @staticmethod
    def id_from_bytes(b1: int, b2: int, b3: int, b4: int) -> str:
        """Decode DMR ID from 4 bytes"""
        if b1 == 0 and b2 == 0 and b3 == 0 and b4 == 0:
            return "-"
        dmr_id = struct.unpack('>I', bytes([b1, b2, b3, b4]))[0]
        return str(dmr_id)
    
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
            yscrollcommand=scrollbar.set,
            style='Tree.Treeview'
        )
        scrollbar.config(command=self.channel_tree.yview)
        
        self.channel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Populate the tree with channel data
        self._populate_channel_tree()
        
        # Bind selection event
        self.channel_tree.bind('<<TreeviewSelect>>', self._on_channel_select)
        
        # Prevent tree from collapsing on left arrow and navigate tabs instead
        self.channel_tree.bind('<Left>', lambda e: self._navigate_tab_left(e) or 'break')
        self.channel_tree.bind('<Right>', lambda e: self._navigate_tab_right(e) or 'break')
        
        # Bind keyboard navigation for channels only (up/down)
        self.root.bind('<Up>', self._navigate_channel_up)
        self.root.bind('<Down>', self._navigate_channel_down)
    
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
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Not Implemented", state='disabled')
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Select Columns...", command=self._show_column_selector)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self._open_file())
        self.root.bind('<Control-s>', lambda e: self._save_file())
    
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
        
        # Tab 2: Frequency (RX/TX combined)
        self.freq_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.freq_tab, text="Frequency")
        
        # Tab 3: DMR Settings
        self.dmr_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.dmr_tab, text="DMR")
        
        # Tab 4: Advanced
        self.advanced_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(self.advanced_tab, text="Advanced")
        
        # Tab 5: Raw Data
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
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _populate_freq_tab(self, ch_data):
        """Populate combined Frequency (RX/TX) tab with two-column layout"""
        # Clear existing widgets
        for widget in self.freq_tab.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
        canvas = tk.Canvas(self.freq_tab)
        scrollbar = ttk.Scrollbar(self.freq_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Main container with two columns
        main_frame = ttk.Frame(scrollable_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== LEFT COLUMN: RX Settings =====
        rx_frame = ttk.LabelFrame(main_frame, text="Receive (RX)", padding=10)
        rx_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        rx_row = 0
        
        # RX Frequency
        ttk.Label(rx_frame, text="Frequency (MHz):", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        rx_freq = self.freq_from_bytes(
            ch_data['vfoaFrequency1'], ch_data['vfoaFrequency2'],
            ch_data['vfoaFrequency3'], ch_data['vfoaFrequency4']
        )
        self.current_rx_freq.set(rx_freq)
        rx_entry = ttk.Entry(rx_frame, textvariable=self.current_rx_freq, width=20)
        rx_entry.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # RX CTCSS/DCS
        ttk.Label(rx_frame, text="CTCSS/DCS:", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        rx_ctcss = ch_data['rxCtcss']
        if rx_ctcss == 0:
            rx_ctcss_display = "Off"
        elif rx_ctcss >= 1000:
            rx_ctcss_display = f"{rx_ctcss / 10:.1f}"
        else:
            rx_ctcss_display = str(rx_ctcss)
        self.current_rx_ctcss.set(rx_ctcss_display)
        # Use combobox with combined CTCSS/DCS list
        rx_ctcss_combo = ttk.Combobox(rx_frame, textvariable=self.current_rx_ctcss, 
                                      values=self.CTCSS_DCS_COMBINED, width=17)
        rx_ctcss_combo.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # RX Squelch Level
        ttk.Label(rx_frame, text="Squelch Level:", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        squelch_value = ch_data.get('sqlevel', 5)
        squelch_spin = ttk.Spinbox(rx_frame, from_=0, to=9, width=18)
        squelch_spin.set(squelch_value)  # Explicitly set the value
        squelch_spin.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # RX Monitor Type
        ttk.Label(rx_frame, text="Monitor Type:", font=('Arial', 9, 'bold')).grid(
            row=rx_row, column=0, sticky=tk.W, padx=5, pady=5)
        monitor_types = ["Open Squelch", "Silent"]
        monitor_combo = ttk.Combobox(rx_frame, values=monitor_types, state='readonly', width=17)
        monitor_combo.current(ch_data.get('monitor', 0))
        monitor_combo.grid(row=rx_row, column=1, sticky=tk.W, padx=5, pady=5)
        rx_row += 1
        
        # ===== RIGHT COLUMN: TX Settings =====
        tx_frame = ttk.LabelFrame(main_frame, text="Transmit (TX)", padding=10)
        tx_frame.grid(row=0, column=2, sticky='nsew', padx=5, pady=5)
        
        tx_row = 0
        
        # TX Frequency
        ttk.Label(tx_frame, text="Frequency (MHz):", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        tx_freq = self.freq_from_bytes(
            ch_data['vfobFrequency1'], ch_data['vfobFrequency2'],
            ch_data['vfobFrequency3'], ch_data['vfobFrequency4']
        )
        self.current_tx_freq.set(tx_freq)
        tx_entry = ttk.Entry(tx_frame, textvariable=self.current_tx_freq, width=20)
        tx_entry.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # TX CTCSS/DCS
        ttk.Label(tx_frame, text="CTCSS/DCS:", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        tx_ctcss = ch_data.get('txCtcss', ch_data['rxCtcss'])  # Fall back to RX if not available
        if tx_ctcss == 0:
            tx_ctcss_display = "Off"
        elif tx_ctcss >= 1000:
            tx_ctcss_display = f"{tx_ctcss / 10:.1f}"
        else:
            tx_ctcss_display = str(tx_ctcss)
        self.current_tx_ctcss.set(tx_ctcss_display)
        # Use combobox with combined CTCSS/DCS list
        tx_ctcss_combo = ttk.Combobox(tx_frame, textvariable=self.current_tx_ctcss,
                                      values=self.CTCSS_DCS_COMBINED, width=17)
        tx_ctcss_combo.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # TX Color Code (DMR)
        ttk.Label(tx_frame, text="Color Code:", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        tx_cc_var = tk.IntVar(value=ch_data['txCc'])
        tx_cc_spin = ttk.Spinbox(tx_frame, from_=0, to=15, textvariable=tx_cc_var, width=18)
        # Gray out if not DMR - add visual styling
        if ch_data.get('chType', 0) != 1:
            tx_cc_spin.state(['disabled'])
            # Add visual graying - use tk.Spinbox instead for better styling control
            tx_cc_spin.destroy()
            tx_cc_spin = tk.Spinbox(tx_frame, from_=0, to=15, width=15, 
                                   bg='#E0E0E0', fg='#808080', state='disabled',
                                   disabledbackground='#E0E0E0', disabledforeground='#808080')
            tx_cc_spin.delete(0, tk.END)
            tx_cc_spin.insert(0, str(ch_data['txCc']))
        tx_cc_spin.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # TX Power Level
        ttk.Label(tx_frame, text="Power Level:", font=('Arial', 9, 'bold')).grid(
            row=tx_row, column=0, sticky=tk.W, padx=5, pady=5)
        power = self.POWER_LEVELS.get(ch_data.get('vfoaPower', 0), 'Low')
        power_combo = ttk.Combobox(tx_frame, values=list(self.POWER_LEVELS.values()),
                                  state='readonly', width=17)
        power_combo.set(power)
        power_combo.grid(row=tx_row, column=1, sticky=tk.W, padx=5, pady=5)
        tx_row += 1
        
        # ===== CENTER COLUMN: Copy Tools =====
        tools_frame = ttk.LabelFrame(main_frame, text="Copy Tools", padding=10)
        tools_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        
        tools_row = 0
        
        # Calculated offset display
        ttk.Label(tools_frame, text="Current Offset:", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        try:
            rx_freq_float = float(rx_freq.split()[0])
            tx_freq_float = float(tx_freq.split()[0])
            offset = tx_freq_float - rx_freq_float
            self.offset_var.set(f"{offset:+.6f}")
            current_offset = f"{offset:+.6f}"  # Store for offset input field
        except:
            self.offset_var.set("0.000000")
            current_offset = "+0.000000"
        
        offset_label = ttk.Label(tools_frame, textvariable=self.offset_var, 
                                font=('Arial', 10, 'bold'), foreground='blue')
        offset_label.grid(row=tools_row, column=0, columnspan=2, padx=5, pady=5)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient=tk.HORIZONTAL).grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', pady=10)
        tools_row += 1
        
        # Copy Frequency with graphical arrows
        ttk.Label(tools_frame, text="Copy Frequency:", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        # Create custom style for large arrow buttons
        arrow_font = ('Arial', 14, 'bold')  # Larger font for bigger arrows
        
        btn_rx_to_tx = tk.Button(tools_frame, text="RX  ▶  TX", font=arrow_font,
                                bg='#E0E0E0', activebackground='#D0D0D0',
                                relief=tk.RAISED, bd=2,
                                command=lambda: self._copy_freq_rx_to_tx(simplex=True))
        btn_rx_to_tx.grid(row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=4, ipady=10)
        tools_row += 1
        
        btn_tx_to_rx = tk.Button(tools_frame, text="RX  ◀  TX", font=arrow_font,
                                bg='#E0E0E0', activebackground='#D0D0D0',
                                relief=tk.RAISED, bd=2,
                                command=lambda: self._copy_freq_tx_to_rx(simplex=True))
        btn_tx_to_rx.grid(row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=4, ipady=10)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient=tk.HORIZONTAL).grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', pady=10)
        tools_row += 1
        
        # Offset input
        ttk.Label(tools_frame, text="Apply Offset (MHz):", font=('Arial', 9, 'bold')).grid(
            row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        offset_input_var = tk.StringVar(value=current_offset)
        offset_entry = ttk.Entry(tools_frame, textvariable=offset_input_var, width=15)
        offset_entry.grid(row=tools_row, column=0, columnspan=2, padx=5, pady=2)
        tools_row += 1
        
        # Preset offset buttons
        preset_frame = ttk.Frame(tools_frame)
        preset_frame.grid(row=tools_row, column=0, columnspan=2, pady=5)
        ttk.Button(preset_frame, text="+5.0", width=6,
                  command=lambda: offset_input_var.set("+5.000000")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="-5.0", width=6,
                  command=lambda: offset_input_var.set("-5.000000")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="+0.6", width=6,
                  command=lambda: offset_input_var.set("+0.600000")).pack(side=tk.LEFT, padx=2)
        tools_row += 1
        
        # Apply offset buttons with directional arrows
        btn_offset_rx_to_tx = tk.Button(tools_frame, text="RX+▶TX", font=arrow_font,
                                       bg='#D0E0FF', activebackground='#C0D0EF',
                                       relief=tk.RAISED, bd=2,
                                       command=lambda: self._copy_freq_with_offset('rx_to_tx', offset_input_var.get()))
        btn_offset_rx_to_tx.grid(row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=4, ipady=10)
        tools_row += 1
        
        btn_offset_tx_to_rx = tk.Button(tools_frame, text="RX◀+TX", font=arrow_font,
                                       bg='#D0E0FF', activebackground='#C0D0EF',
                                       relief=tk.RAISED, bd=2,
                                       command=lambda: self._copy_freq_with_offset('tx_to_rx', offset_input_var.get()))
        btn_offset_tx_to_rx.grid(row=tools_row, column=0, columnspan=2, sticky='ew', padx=5, pady=4, ipady=10)
        tools_row += 1
        
        # Separator
        ttk.Separator(tools_frame, orient=tk.HORIZONTAL).grid(
            row=tools_row, column=0, columnspan=2, sticky='ew', pady=10)
        tools_row += 1
        
        # CTCSS/DCS copy checkbox
        ctcss_check = ttk.Checkbutton(tools_frame, text="Copy CTCSS/DCS", 
                                     variable=self.copy_ctcss_var)
        ctcss_check.grid(row=tools_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tools_row += 1
        
        # Configure grid weights for responsive layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)  # Center column fixed width
        main_frame.columnconfigure(2, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _copy_freq_rx_to_tx(self, simplex=True):
        """Copy RX frequency to TX (simplex mode)"""
        self.current_tx_freq.set(self.current_rx_freq.get())
        if self.copy_ctcss_var.get():
            self.current_tx_ctcss.set(self.current_rx_ctcss.get())
        self._update_offset()
    
    def _copy_freq_tx_to_rx(self, simplex=True):
        """Copy TX frequency to RX (simplex mode)"""
        self.current_rx_freq.set(self.current_tx_freq.get())
        if self.copy_ctcss_var.get():
            self.current_rx_ctcss.set(self.current_tx_ctcss.get())
        self._update_offset()
    
    def _copy_freq_with_offset(self, direction, offset_str):
        """Copy frequency with offset applied"""
        try:
            offset = float(offset_str)
            
            if direction == 'rx_to_tx':
                rx_freq = float(self.current_rx_freq.get().split()[0])
                new_tx_freq = rx_freq + offset
                self.current_tx_freq.set(f"{new_tx_freq:.6f}")
            else:  # tx_to_rx
                tx_freq = float(self.current_tx_freq.get().split()[0])
                new_rx_freq = tx_freq + offset
                self.current_rx_freq.set(f"{new_rx_freq:.6f}")
            
            if self.copy_ctcss_var.get():
                if direction == 'rx_to_tx':
                    self.current_tx_ctcss.set(self.current_rx_ctcss.get())
                else:
                    self.current_rx_ctcss.set(self.current_tx_ctcss.get())
            
            self._update_offset()
        except ValueError:
            messagebox.showerror("Error", "Invalid offset value. Please enter a number.")
    
    def _update_offset(self):
        """Update the displayed offset calculation"""
        try:
            rx_freq = float(self.current_rx_freq.get().split()[0])
            tx_freq = float(self.current_tx_freq.get().split()[0])
            offset = tx_freq - rx_freq
            self.offset_var.set(f"{offset:+.6f}")
        except:
            self.offset_var.set("N/A")
    
    def _on_channel_name_changed(self):
        """Update channel name in data and header when user types (without rebuilding tree)"""
        if not self.current_channel or not hasattr(self, 'current_channel_name'):
            return
        
        new_name = self.current_channel_name.get()
        ch_id = str(self.current_channel)
        
        # Update the data
        if ch_id in self.channels:
            self.channels[ch_id]['channelName'] = new_name
        
        # Update the header banner
        ch_num = self.channels[ch_id].get('channelLow', ch_id)
        self.detail_header.config(text=f"Channel {ch_num} - {new_name}")
        
        # Update the tree item directly (without rebuilding entire tree)
        self._update_tree_item_name(ch_id, new_name)
    
    def _update_tree_item_name(self, ch_id, new_name):
        """Update a specific tree item's name column without rebuilding the tree"""
        # Find the tree item with this channel ID
        for group in self.channel_tree.get_children():
            for item in self.channel_tree.get_children(group):
                tags = self.channel_tree.item(item, 'tags')
                if tags and tags[0] == ch_id:
                    # Get current values
                    current_values = list(self.channel_tree.item(item, 'values'))
                    # Update the name (first column in values)
                    if len(current_values) > 0:
                        current_values[0] = new_name
                        self.channel_tree.item(item, values=tuple(current_values))
                    return
    
    def _on_channel_name_focus_out(self):
        """Optional: Could rebuild tree when user finishes editing, but not needed anymore"""
        pass
    
    def _update_field(self, field_name, value):
        """Update a field in the current channel data"""
        if not self.current_channel:
            return
        
        ch_id = str(self.current_channel)
        if ch_id in self.channels:
            self.channels[ch_id][field_name] = value
            self.status_label.config(text=f"Updated {field_name}")
    
    def _navigate_channel_up(self, event):
        """Navigate to previous channel with Up arrow"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        item = selection[0]
        prev_item = self.channel_tree.prev(item)
        if prev_item:
            self.channel_tree.selection_set(prev_item)
            self.channel_tree.focus(prev_item)
            self.channel_tree.see(prev_item)
    
    def _navigate_channel_down(self, event):
        """Navigate to next channel with Down arrow"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        item = selection[0]
        next_item = self.channel_tree.next(item)
        if next_item:
            self.channel_tree.selection_set(next_item)
            self.channel_tree.focus(next_item)
            self.channel_tree.see(next_item)
    
    def _navigate_tab_left(self, event):
        """Navigate to previous tab with Left arrow"""
        current = self.detail_notebook.index('current')
        if current > 0:
            self.detail_notebook.select(current - 1)
    
    def _navigate_tab_right(self, event):
        """Navigate to next tab with Right arrow"""
        current = self.detail_notebook.index('current')
        if current < self.detail_notebook.index('end') - 1:
            self.detail_notebook.select(current + 1)
    
    # Channel number editing removed - see README TODO section for future implementation
    
    def _rebuild_channel_tree(self, reselect_channel_id=None):
        """Rebuild the channel tree with updated numbering
        
        Args:
            reselect_channel_id: If provided, reselect and highlight this channel after rebuild
        """
        # Clear existing tree completely - delete all items including groups
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        
        # Separate analog and DMR channels, sorted by channel number
        analog_channels = []
        dmr_channels = []
        
        for ch_id, ch_data in self.channels.items():
            ch_num = ch_data.get('channelLow', 0)
            if isinstance(ch_num, str):
                try:
                    ch_num = int(ch_num)
                except (ValueError, TypeError):
                    ch_num = 0
            
            # Extract values for selected columns dynamically
            column_values = []
            for col_id in self.selected_columns:
                if col_id in self.available_columns:
                    try:
                        value = self.available_columns[col_id]['extract'](ch_data)
                        column_values.append(value)
                    except (KeyError, TypeError):
                        column_values.append('N/A')
            
            if ch_data.get('chType', 0) == 1:  # DMR
                dmr_channels.append((ch_num, tuple(column_values), ch_id))
            else:  # Analog
                analog_channels.append((ch_num, tuple(column_values), ch_id))
        
        # Sort by channel number - ensure we're comparing integers
        def sort_key(item):
            try:
                return int(item[0])
            except (ValueError, TypeError):
                return 999999
        
        analog_channels.sort(key=sort_key)
        dmr_channels.sort(key=sort_key)
        
        # Track which tree item corresponds to the channel we want to reselect
        item_to_select = None
        
        # Add analog group
        analog_group = self.channel_tree.insert('', 'end', text=f'Analog Channels ({len(analog_channels)})',
                                               open=True)
        for ch_num, column_values, ch_id in analog_channels:
            item_id = self.channel_tree.insert(analog_group, 'end',
                text=ch_num,
                values=column_values,
                tags=(ch_id,)
            )
            if reselect_channel_id and ch_id == reselect_channel_id:
                item_to_select = item_id
        
        # Add DMR group
        dmr_group = self.channel_tree.insert('', 'end', text=f'DMR Channels ({len(dmr_channels)})',
                                            open=True)
        for ch_num, column_values, ch_id in dmr_channels:
            item_id = self.channel_tree.insert(dmr_group, 'end',
                text=ch_num,
                values=column_values,
                tags=(ch_id,)
            )
            if reselect_channel_id and ch_id == reselect_channel_id:
                item_to_select = item_id
        
        # Reselect and highlight the channel if requested
        if item_to_select:
            self.channel_tree.selection_set(item_to_select)
            self.channel_tree.focus(item_to_select)
            self.channel_tree.see(item_to_select)
    
    def _populate_rx_tab(self, ch_data):
        """DEPRECATED: Now using combined freq tab"""
        pass
    
    def _populate_tx_tab(self, ch_data):
        """DEPRECATED: Now using combined freq tab"""
        pass
    
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
        
        # Call ID
        ttk.Label(frame, text="Call ID:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        call_id = self.id_from_bytes(
            ch_data['callId1'], ch_data['callId2'],
            ch_data['callId3'], ch_data['callId4']
        )
        if not is_dmr:
            # Use tk.Entry for better styling control when disabled
            call_entry = tk.Entry(frame, width=20, bg='#E0E0E0', fg='#808080', 
                                state='disabled', disabledbackground='#E0E0E0', 
                                disabledforeground='#808080')
        else:
            call_entry = ttk.Entry(frame, width=20)
        call_entry.insert(0, call_id)
        if not is_dmr:
            call_entry.config(state='disabled')
        call_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Own ID
        ttk.Label(frame, text="Own ID:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        own_id = self.id_from_bytes(
            ch_data['ownId1'], ch_data['ownId2'],
            ch_data['ownId3'], ch_data['ownId4']
        )
        if not is_dmr:
            own_entry = tk.Entry(frame, width=20, bg='#E0E0E0', fg='#808080',
                               state='disabled', disabledbackground='#E0E0E0',
                               disabledforeground='#808080')
        else:
            own_entry = ttk.Entry(frame, width=20)
        own_entry.insert(0, own_id)
        if not is_dmr:
            own_entry.config(state='disabled')
        own_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # RX Color Code
        ttk.Label(frame, text="RX Color Code:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        if not is_dmr:
            rx_cc_spin = tk.Spinbox(frame, from_=0, to=15, width=15,
                                   bg='#E0E0E0', fg='#808080', state='disabled',
                                   disabledbackground='#E0E0E0', disabledforeground='#808080')
            rx_cc_spin.delete(0, tk.END)
            rx_cc_spin.insert(0, str(ch_data.get('rxCc', 0)))
        else:
            rx_cc_var = tk.IntVar(value=ch_data.get('rxCc', 0))
            rx_cc_spin = ttk.Spinbox(frame, from_=0, to=15, textvariable=rx_cc_var, width=18)
        rx_cc_spin.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Timeslot
        ttk.Label(frame, text="Timeslot:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        timeslot_var = tk.IntVar(value=ch_data.get('timeslot', 1))
        timeslot_combo = ttk.Combobox(frame, values=[1, 2], state='readonly', width=17)
        timeslot_combo.set(timeslot_var.get())
        if not is_dmr:
            timeslot_combo.state(['disabled'])
        timeslot_combo.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Talk Group (0-65535)
        ttk.Label(frame, text="Talk Group:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        tg_value = max(0, min(65535, ch_data.get('talkgroup', 0)))  # Clamp to valid range
        if not is_dmr:
            tg_entry = tk.Entry(frame, width=20, bg='#E0E0E0', fg='#808080',
                              state='disabled', disabledbackground='#E0E0E0',
                              disabledforeground='#808080')
            tg_entry.insert(0, str(tg_value))
        else:
            tg_var = tk.IntVar(value=tg_value)
            tg_spinbox = ttk.Spinbox(frame, from_=0, to=65535, textvariable=tg_var, width=18)
            tg_entry = tg_spinbox
        tg_entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Emergency Alarm
        ttk.Label(frame, text="Emergency Alarm:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        emergency_var = tk.BooleanVar(value=bool(ch_data.get('emergency', 0)))
        emergency_check = ttk.Checkbutton(frame, variable=emergency_var)
        if ch_data.get('emergency', 0):
            emergency_check.state(['selected'])
        if not is_dmr:
            emergency_check.state(['disabled'])
        emergency_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
    
    def _populate_advanced_tab(self, ch_data):
        """Populate Advanced Settings tab"""
        # Clear existing widgets
        for widget in self.advanced_tab.winfo_children():
            widget.destroy()
        
        frame = ttk.Frame(self.advanced_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # Scrambler
        ttk.Label(frame, text="Scrambler:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        scrambler_var = tk.BooleanVar(value=bool(ch_data.get('scrambler', 0)))
        scrambler_check = ttk.Checkbutton(frame, variable=scrambler_var)
        # Force the checkbox to show proper state
        if ch_data.get('scrambler', 0):
            scrambler_check.state(['selected'])
        scrambler_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Compander
        ttk.Label(frame, text="Compander:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        compander_var = tk.BooleanVar(value=bool(ch_data.get('compander', 0)))
        compander_check = ttk.Checkbutton(frame, variable=compander_var)
        if ch_data.get('compander', 0):
            compander_check.state(['selected'])
        compander_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # VOX
        ttk.Label(frame, text="VOX:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        vox_var = tk.BooleanVar(value=bool(ch_data.get('vox', 0)))
        vox_check = ttk.Checkbutton(frame, variable=vox_var)
        if ch_data.get('vox', 0):
            vox_check.state(['selected'])
        vox_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # PTT ID
        ttk.Label(frame, text="PTT ID:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        ptt_id_var = tk.BooleanVar(value=bool(ch_data.get('pttId', 0)))
        ptt_id_check = ttk.Checkbutton(frame, variable=ptt_id_var)
        if ch_data.get('pttId', 0):
            ptt_id_check.state(['selected'])
        ptt_id_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Busy Lock
        ttk.Label(frame, text="Busy Lock:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        busy_lock_var = tk.BooleanVar(value=bool(ch_data.get('busyLock', 0)))
        busy_lock_check = ttk.Checkbutton(frame, variable=busy_lock_var)
        if ch_data.get('busyLock', 0):
            busy_lock_check.state(['selected'])
        busy_lock_check.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Scan List
        ttk.Label(frame, text="Scan List:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5)
        scan_list_var = tk.IntVar(value=ch_data.get('scanList', 0))
        scan_list_spin = ttk.Spinbox(frame, from_=0, to=10, textvariable=scan_list_var, width=18)
        scan_list_spin.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
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
        channels = json.load(f)
    
    if title is None:
        title = f"Channel Viewer - {json_path.name}"
    
    viewer = ChannelTableViewer(channels, title)
    viewer.show()
