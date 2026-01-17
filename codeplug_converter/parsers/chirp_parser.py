"""CHIRP .img binary format parser"""

from pathlib import Path
from typing import List, Dict, Any
from .base_parser import BaseParser
from ..utils import bcd_to_frequency, is_valid_frequency, is_chirp_metadata, is_corrupted_channel


class ChirpParser(BaseParser):
    """Parser for CHIRP .img binary files
    
    CHIRP format (32 bytes per channel):
    Offset 0-7: RX/TX frequency (BCD encoded)
    Offset 8-9: RX/TX tone settings
    Offset 16-31: Channel name (ASCII, padded with FF)
    """
    
    CHANNEL_SIZE = 32
    
    def supports_format(self, file_path: Path) -> bool:
        """Check if file is a CHIRP .img file"""
        return file_path.suffix.lower() == '.img'
    
    def parse(self, file_path: Path, strict_validation: bool = True) -> List[Dict[str, Any]]:
        """Parse CHIRP .img file
        
        Args:
            file_path: Path to .img file
            strict_validation: Use strict frequency validation (Baofeng ranges only)
            
        Returns:
            List of parsed channel dictionaries
        """
        channels = []
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        num_channels = len(data) // self.CHANNEL_SIZE
        print(f"Found {num_channels} channel slots in {file_path.name}")
        
        for idx in range(min(num_channels, 1000)):  # Only parse first 1000 (rest is metadata)
            offset = idx * self.CHANNEL_SIZE
            chunk = data[offset:offset + self.CHANNEL_SIZE]
            
            if len(chunk) < self.CHANNEL_SIZE:
                break
            
            # Parse frequency (BCD encoded in first 8 bytes)
            rx_freq_bcd = chunk[0:4]
            tx_freq_bcd = chunk[4:8]
            
            rx_freq = bcd_to_frequency(rx_freq_bcd)
            tx_freq = bcd_to_frequency(tx_freq_bcd)
            
            # Parse channel name (offset 20, up to 12 bytes, FF padded)
            name_bytes = chunk[20:32]
            name_end = name_bytes.find(b'\xff')
            if name_end != -1:
                name_bytes = name_bytes[:name_end]
            name = name_bytes.decode('ascii', errors='replace').strip()
            
            # Skip CHIRP metadata channels
            if is_chirp_metadata(chunk, name):
                continue
            
            # Skip corrupted channels
            if is_corrupted_channel(chunk, name, rx_freq):
                continue
            
            # Validate frequencies
            valid_rx = is_valid_frequency(rx_freq, strict=strict_validation)
            valid_tx = tx_freq == 0 or is_valid_frequency(tx_freq, strict=strict_validation)
            
            if name and valid_rx and valid_tx:
                # Parse tones from offset 10-13
                rx_tone_code = chunk[10:12]
                tx_tone_code = chunk[12:14]
                
                channel = {
                    'index': idx,
                    'name': name,
                    'rx_freq': rx_freq,
                    'tx_freq': tx_freq if tx_freq != rx_freq else None,
                    'mode': 'FM',  # CHIRP images are typically FM
                    'rx_ctcss': int.from_bytes(rx_tone_code, 'little'),
                    'tx_ctcss': int.from_bytes(tx_tone_code, 'little'),
                    'is_digital': False
                }
                channels.append(channel)
                
                # Print with ASCII-safe name
                safe_name = name.encode('ascii', 'replace').decode('ascii')
                print(f"  {idx}: {safe_name} - RX:{rx_freq:.4f} TX:{tx_freq:.4f}")
        
        return channels
