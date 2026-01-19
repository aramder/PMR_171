"""Command-line interface for PMR-171 CPS"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

from .parsers import ChirpParser
from .writers import PMR171Writer
from .gui import view_channel_file
from .utils import bytes_to_frequency


class ChannelManager:
    """Manages channel collection, merging, and deduplication"""
    
    def __init__(self):
        self.channels = {}
        self.writer = PMR171Writer()
    
    def merge_channels(self, new_channels: list, deduplicate: bool = True) -> int:
        """Merge new channels into existing collection
        
        Args:
            new_channels: List of parsed channel dicts
            deduplicate: Skip duplicate channels
            
        Returns:
            Number of channels added
        """
        added = 0
        existing_keys = set()
        
        if deduplicate:
            # Build set of existing channel identifiers
            for ch in self.channels.values():
                name = ch['channelName'].rstrip('\u0000').strip()
                rx_freq = (ch['vfoaFrequency1'], ch['vfoaFrequency2'],
                          ch['vfoaFrequency3'], ch['vfoaFrequency4'])
                existing_keys.add((name, rx_freq))
        
        # Convert parsed channels to PMR-171 format
        for parsed_ch in new_channels:
            # Create PMR-171 channel
            pmr_ch = self.writer.create_channel(
                index=parsed_ch['index'],
                name=parsed_ch['name'],
                rx_freq=parsed_ch['rx_freq'],
                tx_freq=parsed_ch.get('tx_freq'),
                mode=parsed_ch.get('mode', 'FM'),
                rx_ctcss=parsed_ch.get('rx_ctcss', 0),
                tx_ctcss=parsed_ch.get('tx_ctcss', 0),
                is_digital=parsed_ch.get('is_digital', False)
            )
            
            if deduplicate:
                name = pmr_ch['channelName'].rstrip('\u0000').strip()
                rx_freq = (pmr_ch['vfoaFrequency1'], pmr_ch['vfoaFrequency2'],
                          pmr_ch['vfoaFrequency3'], pmr_ch['vfoaFrequency4'])
                
                if (name, rx_freq) in existing_keys:
                    continue  # Skip duplicate
                
                existing_keys.add((name, rx_freq))
            
            # Add channel with next sequential index
            next_idx = len(self.channels)
            pmr_ch['channelHigh'] = (next_idx >> 8) & 0xFF
            pmr_ch['channelLow'] = next_idx & 0xFF
            self.channels[str(next_idx)] = pmr_ch
            added += 1
        
        return added
    
    def analyze_duplicates(self, show_details: bool = True) -> dict:
        """Analyze channels for duplicates
        
        Args:
            show_details: Print detailed report
            
        Returns:
            Analysis results dictionary
        """
        # Group channels by RX frequency
        freq_groups = defaultdict(list)
        
        for ch_id, ch in self.channels.items():
            rx_freq_tuple = (ch['vfoaFrequency1'], ch['vfoaFrequency2'],
                           ch['vfoaFrequency3'], ch['vfoaFrequency4'])
            
            rx_mhz = bytes_to_frequency(rx_freq_tuple)
            name = ch['channelName'].rstrip('\u0000').strip()
            
            freq_groups[rx_freq_tuple].append({
                'id': ch_id,
                'name': name,
                'rx_mhz': rx_mhz,
                'tx_freq': (ch['vfobFrequency1'], ch['vfobFrequency2'],
                           ch['vfobFrequency3'], ch['vfobFrequency4'])
            })
        
        # Find duplicates
        duplicates = {freq: channels for freq, channels in freq_groups.items()
                     if len(channels) > 1}
        
        results = {
            'total_channels': len(self.channels),
            'unique_frequencies': len(freq_groups),
            'duplicate_frequency_count': len(duplicates),
            'duplicates': duplicates
        }
        
        if show_details and duplicates:
            print("\n" + "=" * 70)
            print("DUPLICATE FREQUENCY ANALYSIS")
            print("=" * 70)
            print(f"\nFound {len(duplicates)} frequencies with multiple channels:")
            print(f"Total channels: {len(self.channels)}")
            print(f"Unique frequencies: {len(freq_groups)}")
            
            for freq_tuple, channels in sorted(duplicates.items(),
                                              key=lambda x: x[1][0]['rx_mhz']):
                rx_mhz = channels[0]['rx_mhz']
                print(f"\n[*] RX Frequency: {rx_mhz:.4f} MHz ({len(channels)} channels)")
                print("-" * 70)
                
                for ch in sorted(channels, key=lambda x: x['name']):
                    is_simplex = (ch['tx_freq'] == freq_tuple)
                    tx_mhz = bytes_to_frequency(ch['tx_freq'])
                    mode = "Simplex" if is_simplex else f"Split (TX: {tx_mhz:.4f} MHz)"
                    
                    safe_name = ch['name'].encode('ascii', 'replace').decode('ascii')
                    print(f"  Ch {ch['id']:3s}: {safe_name:25s} - {mode}")
        
        elif show_details:
            print("\n" + "=" * 70)
            print("No duplicate frequencies found!")
            print(f"All {len(self.channels)} channels have unique RX frequencies.")
            print("=" * 70)
        
        return results
    
    def save(self, output_path: Path):
        """Save channels to JSON file"""
        self.writer.write(self.channels, output_path)


def convert_chirp_files(file_paths: list, output: Path, deduplicate: bool = True):
    """Convert CHIRP .img files to PMR-171 JSON
    
    Args:
        file_paths: List of paths to .img files
        output: Output JSON path
        deduplicate: Remove duplicates
    """
    manager = ChannelManager()
    parser = ChirpParser()
    
    print("=" * 70)
    print("CHIRP Multi-File Converter")
    print("=" * 70)
    
    results = {}
    
    for file_path in file_paths:
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            results[file_path.name] = 0
            continue
        
        print(f"\nProcessing {file_path.name}...")
        channels = parser.parse(file_path)
        added = manager.merge_channels(channels, deduplicate=deduplicate)
        results[file_path.name] = added
        print(f"  Added {added} channels (total now: {len(manager.channels)})")
    
    print("\n" + "=" * 70)
    print("SUMMARY:")
    for filename, count in results.items():
        print(f"  {filename:30s}: {count:3d} channels")
    print(f"\nTotal unique channels: {len(manager.channels)}")
    print("=" * 70)
    
    if len(manager.channels) > 0:
        manager.save(output)
        print(f"\n[OK] Combined codeplug saved to {output}")
        
        # Analyze for duplicates
        print("\n" + "=" * 70)
        print("Running duplicate detection...")
        print("=" * 70)
        manager.analyze_duplicates(show_details=True)
        
        return manager.channels
    
    return None


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='PMR-171 CPS - Convert radio configuration files to PMR-171 JSON format'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert CHIRP files')
    convert_parser.add_argument('files', nargs='+', type=Path,
                               help='CHIRP .img files to convert')
    convert_parser.add_argument('-o', '--output', type=Path,
                               default=Path('output.json'),
                               help='Output JSON file (default: output.json)')
    convert_parser.add_argument('--no-dedupe', action='store_true',
                               help='Disable deduplication')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View channel table')
    view_parser.add_argument('file', type=Path, help='JSON file to view')
    
    # Default behavior (backwards compatibility)
    if len(sys.argv) == 1:
        # Run default conversion
        default_files = [
            Path("../Baofeng/UV-32.img"),
            Path("../Baofeng/My UV-5R.img"),
            Path("../Baofeng/My UV-82.img"),
        ]
        output = Path("All_Radios_Combined.json")
        convert_chirp_files(default_files, output)
        return
    
    # Old-style --view argument (backwards compatibility)
    if sys.argv[1] == '--view':
        json_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("All_Radios_Combined.json")
        view_channel_file(json_file)
        return
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        convert_chirp_files(args.files, args.output, deduplicate=not args.no_dedupe)
    
    elif args.command == 'view':
        view_channel_file(args.file)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
