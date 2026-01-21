#!/usr/bin/env python3
"""Quick test of CSV export/import functionality"""

import csv
import json
import struct
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pmr_171_cps.gui.table_viewer import ChannelTableViewer

def main():
    """Test CSV export and import"""
    
    # Load sample data
    sample_file = Path(__file__).parent.parent / "examples" / "Mode_Test.json"
    print(f"Loading sample data from: {sample_file}")
    
    with open(sample_file, 'r') as f:
        data = json.load(f)
    
    channels = data.get('channels', data)
    print(f"Loaded {len(channels)} channels")
    
    # Create viewer instance (without showing GUI)
    viewer = ChannelTableViewer(channels, "Test")
    
    # Export to CSV manually (replicating _export_to_csv logic)
    csv_file = Path(__file__).parent / "test_export.csv"
    
    print(f"\n=== Exporting to CSV: {csv_file} ===")
    
    fieldnames = [
        'Channel', 'Name', 'RX Frequency (MHz)', 'TX Frequency (MHz)', 'Offset (MHz)',
        'Mode', 'Channel Type', 'RX CTCSS/DCS', 'TX CTCSS/DCS', 'Power', 'Squelch Mode',
        'Bandwidth', 'DMR ID (Own)', 'DMR ID (Call)', 'DMR Slot',
        'DMR Color Code (RX)', 'DMR Color Code (TX)'
    ]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        sorted_channels = sorted(channels.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999)
        
        for ch_id, ch in sorted_channels:
            # Extract frequencies
            rx_freq_str = viewer.freq_from_bytes(
                ch['vfoaFrequency1'], ch['vfoaFrequency2'],
                ch['vfoaFrequency3'], ch['vfoaFrequency4']
            ).replace(' ⚠', '')
            
            tx_freq_str = viewer.freq_from_bytes(
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
            
            name = ch.get('channelName', '').rstrip('\u0000').strip() or '(empty)'
            mode = viewer.MODE_NAMES.get(ch.get('vfoaMode', 6), 'NFM')
            ch_type = viewer.CHANNEL_TYPES.get(ch.get('chType', 0), 'Analog')
            
            writer.writerow({
                'Channel': ch_id,
                'Name': name,
                'RX Frequency (MHz)': rx_freq,
                'TX Frequency (MHz)': tx_freq,
                'Offset (MHz)': f"{offset:.6f}" if isinstance(offset, float) else offset,
                'Mode': mode,
                'Channel Type': ch_type,
                'RX CTCSS/DCS': viewer.ctcss_dcs_from_value(ch.get('rxCtcss', 0)),
                'TX CTCSS/DCS': viewer.ctcss_dcs_from_value(ch.get('txCtcss', 0)),
                'Power': viewer.POWER_LEVELS.get(ch.get('power', 0), 'Low'),
                'Squelch Mode': viewer.SQUELCH_MODES.get(ch.get('sqlevel', 0), 'Carrier'),
                'Bandwidth': ch.get('bandwidth', 'N/A'),
                'DMR ID (Own)': viewer.id_from_bytes(ch.get('ownId1', 0), ch.get('ownId2', 0), ch.get('ownId3', 0), ch.get('ownId4', 0)),
                'DMR ID (Call)': viewer.id_from_bytes(ch.get('callId1', 0), ch.get('callId2', 0), ch.get('callId3', 0), ch.get('callId4', 0)),
                'DMR Slot': ch.get('slot', 0) + 1 if ch_type == 'DMR' else 'N/A',
                'DMR Color Code (RX)': ch.get('rxCc', 0) if ch_type == 'DMR' else 'N/A',
                'DMR Color Code (TX)': ch.get('txCc', 0) if ch_type == 'DMR' else 'N/A'
            })
    
    print(f"Exported {len(channels)} channels to CSV")
    
    # Display CSV contents
    print("\n=== CSV Contents ===")
    with open(csv_file, 'r', encoding='utf-8') as f:
        print(f.read())
    
    # Test import back
    print("\n=== Testing CSV Import ===")
    imported_channels = {}
    
    with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            ch_num = row['Channel']
            name = row['Name']
            rx_freq = row['RX Frequency (MHz)']
            tx_freq = row['TX Frequency (MHz)']
            mode = row['Mode']
            
            print(f"  CH {ch_num}: {name} | RX: {rx_freq} MHz | TX: {tx_freq} MHz | Mode: {mode}")
            imported_channels[ch_num] = {
                'name': name,
                'rx_freq': rx_freq,
                'tx_freq': tx_freq,
                'mode': mode
            }
    
    print(f"\nImported {len(imported_channels)} channels from CSV")
    
    # Verify round-trip
    print("\n=== Round-trip Verification ===")
    all_match = True
    for ch_id in channels.keys():
        if ch_id not in imported_channels:
            print(f"  ❌ Channel {ch_id} missing in import")
            all_match = False
            continue
        
        orig_name = channels[ch_id].get('channelName', '').rstrip('\u0000').strip() or '(empty)'
        imp_name = imported_channels[ch_id]['name']
        
        if orig_name != imp_name:
            print(f"  ❌ Channel {ch_id} name mismatch: '{orig_name}' vs '{imp_name}'")
            all_match = False
    
    if all_match:
        print("  ✅ All channels match!")
    
    # Cleanup
    csv_file.unlink()
    print(f"\nCleaned up test file: {csv_file}")
    
    return 0 if all_match else 1

if __name__ == "__main__":
    sys.exit(main())
