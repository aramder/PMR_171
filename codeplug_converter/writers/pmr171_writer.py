"""PMR-171 JSON format writer"""

import json
from pathlib import Path
from typing import Dict, List, Any
from ..utils import frequency_to_bytes


class PMR171Writer:
    """Writer for Guohetec PMR-171 JSON format"""
    
    # User DMR ID
    DMR_ID = 3107683
    
    # Mode mappings (verified from MODE_TEST.json loaded into PMR-171)
    MODES = {
        'FM': 6,      # NFM (Narrow FM) - most common for amateur/commercial
        'NFM': 6,     # Narrow FM
        'WFM': 5,     # Wide FM (broadcast)
        'AM': 4,      # AM (Amplitude Modulation)
        'USB': 0,     # Upper Sideband (SSB)
        'LSB': 1,     # Lower Sideband (SSB)
        'CWR': 2,     # CW Reverse (USB side BFO for CW reception)
        'CWL': 3,     # CW Lower (LSB side BFO for CW reception)
        'DMR': 9,     # DMR (Digital Mobile Radio)
        'DIGI': 7,    # Digital (generic)
        'PKT': 8,     # Packet
        'DSTAR': 7,   # D-STAR digital → maps to DIGI
        'C4FM': 7,    # C4FM/Fusion digital → maps to DIGI
        'DIGITAL': 9, # Generic digital → maps to DMR
        'SSB': 0,     # Generic SSB → maps to USB
        'CW': 3,      # Generic CW → maps to CWL (standard LSB side)
    }
    
    def __init__(self, dmr_id: int = None):
        """Initialize PMR-171 writer
        
        Args:
            dmr_id: DMR ID to use (defaults to class DMR_ID)
        """
        self.dmr_id = dmr_id if dmr_id is not None else self.DMR_ID
    
    def dmr_id_to_bytes(self, dmr_id: int) -> tuple:
        """Convert DMR ID to 4 bytes"""
        return (
            (dmr_id >> 24) & 0xFF,
            (dmr_id >> 16) & 0xFF,
            (dmr_id >> 8) & 0xFF,
            dmr_id & 0xFF
        )
    
    def create_channel(self, 
                      index: int,
                      name: str,
                      rx_freq: float,
                      tx_freq: float = None,
                      mode: str = 'FM',
                      rx_ctcss: int = 0,
                      tx_ctcss: int = 0,
                      is_digital: bool = False,
                      **kwargs) -> Dict[str, Any]:
        """Create a channel entry in PMR-171 format
        
        Args:
            index: Channel number
            name: Channel name (max 15 chars)
            rx_freq: RX frequency in MHz
            tx_freq: TX frequency in MHz (None for simplex)
            mode: Mode string (FM, USB, LSB, etc.)
            rx_ctcss: RX CTCSS code
            tx_ctcss: TX CTCSS code
            is_digital: True for digital channels (DMR, etc.)
            **kwargs: Additional PMR-171 fields
            
        Returns:
            Channel dictionary in PMR-171 format
        """
        if tx_freq is None:
            tx_freq = rx_freq  # Simplex
            
        rx_bytes = frequency_to_bytes(rx_freq)
        tx_bytes = frequency_to_bytes(tx_freq)
        
        mode_value = self.MODES.get(mode.upper(), 6)
        
        # Determine channel type: 0=analog, 1=digital
        ch_type = 1 if is_digital else 0
        
        channel = {
            "callFormat": kwargs.get('callFormat', 0),
            "callId1": kwargs.get('callId1', 0),
            "callId2": kwargs.get('callId2', 0),
            "callId3": kwargs.get('callId3', 0),
            "callId4": kwargs.get('callId4', 0),
            "chBsMode": kwargs.get('chBsMode', 0),
            "chType": ch_type,  # 0=analog, 1=digital
            "channelHigh": (index >> 8) & 0xFF,
            "channelLow": index & 0xFF,
            "channelName": name[:15] + "\u0000",  # Null-terminated
            "dmodGain": kwargs.get('dmodGain', 0),
            "emitYayin": kwargs.get('emitYayin', 0),
            "ownId1": kwargs.get('ownId1', 0),
            "ownId2": kwargs.get('ownId2', 0),
            "ownId3": kwargs.get('ownId3', 0),
            "ownId4": kwargs.get('ownId4', 0),
            "receiveYayin": kwargs.get('receiveYayin', 0),
            "rxCc": kwargs.get('rxCc', 0),
            "rxCtcss": rx_ctcss,
            "scrEn": kwargs.get('scrEn', 0),
            "scrSeed1": kwargs.get('scrSeed1', 0),
            "scrSeed2": kwargs.get('scrSeed2', 0),
            "slot": kwargs.get('slot', 0),
            "spkgain": kwargs.get('spkgain', 0),
            "sqlevel": kwargs.get('sqlevel', 0),
            "txCc": kwargs.get('txCc', 2),
            "txCtcss": tx_ctcss,
            "vfoaFrequency1": rx_bytes[0],
            "vfoaFrequency2": rx_bytes[1],
            "vfoaFrequency3": rx_bytes[2],
            "vfoaFrequency4": rx_bytes[3],
            "vfoaMode": mode_value,
            "vfobFrequency1": tx_bytes[0],
            "vfobFrequency2": tx_bytes[1],
            "vfobFrequency3": tx_bytes[2],
            "vfobFrequency4": tx_bytes[3],
            "vfobMode": mode_value
        }
        
        return channel
    
    def write(self, channels: Dict[str, Dict], output_path: Path):
        """Write channels to JSON file
        
        Args:
            channels: Dictionary of channel dictionaries (indexed by string number)
            output_path: Path to output JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(channels, f, indent=4, ensure_ascii=False)
        
        print(f"Saved {len(channels)} channels to {output_path}")
    
    def channels_from_parsed(self, parsed_channels: List[Dict]) -> Dict[str, Dict]:
        """Convert parsed channel list to PMR-171 format
        
        Args:
            parsed_channels: List of channel dicts from parser
            
        Returns:
            Dictionary of PMR-171 channels indexed by string number
        """
        pmr_channels = {}
        
        for ch in parsed_channels:
            index = ch['index']
            pmr_ch = self.create_channel(
                index=index,
                name=ch['name'],
                rx_freq=ch['rx_freq'],
                tx_freq=ch.get('tx_freq'),
                mode=ch.get('mode', 'FM'),
                rx_ctcss=ch.get('rx_ctcss', 0),
                tx_ctcss=ch.get('tx_ctcss', 0),
                is_digital=ch.get('is_digital', False)
            )
            pmr_channels[str(index)] = pmr_ch
        
        return pmr_channels
