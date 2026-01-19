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
                      rx_tone: str = None,
                      tx_tone: str = None,
                      is_digital: bool = False,
                      **kwargs) -> Dict[str, Any]:
        """Create a channel entry in PMR-171 format
        
        Args:
            index: Channel number
            name: Channel name (max 15 chars)
            rx_freq: RX frequency in MHz
            tx_freq: TX frequency in MHz (None for simplex)
            mode: Mode string (FM, USB, LSB, etc.)
            rx_tone: RX tone (CTCSS/DCS as string, e.g., '100.0', 'D023N')
            tx_tone: TX tone (CTCSS/DCS as string, e.g., '100.0', 'D023N')
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
        
        # Determine channel type: 255=analog, 1=digital (from actual radio dump)
        ch_type = 1 if is_digital else 255
        
        # callFormat: 255 for analog, 2 for digital (from actual radio dump)
        call_format = 2 if is_digital else 255
        
        # Convert tones to emitYayin/receiveYayin values
        # Testing proved rxCtcss/txCtcss are IGNORED by radio
        emit_yayin = self._tone_to_yayin(tx_tone)
        receive_yayin = self._tone_to_yayin(rx_tone)
        
        channel = {
            "callFormat": kwargs.get('callFormat', call_format),
            "callId1": kwargs.get('callId1', 0),
            "callId2": kwargs.get('callId2', 0),
            "callId3": kwargs.get('callId3', 0),
            "callId4": kwargs.get('callId4', 0),
            "chBsMode": kwargs.get('chBsMode', 0),
            "chType": ch_type,  # 255=analog, 1=digital
            "channelHigh": (index >> 8) & 0xFF,
            "channelLow": index & 0xFF,
            "channelName": name[:15] + "\u0000",  # Null-terminated
            "dmodGain": 0,  # Field ignored by radio (test 08)
            "emitYayin": kwargs.get('emitYayin', emit_yayin),  # TX tone (WORKING)
            "ownId1": kwargs.get('ownId1', 0),
            "ownId2": kwargs.get('ownId2', 0),
            "ownId3": kwargs.get('ownId3', 0),
            "ownId4": kwargs.get('ownId4', 0),
            "receiveYayin": kwargs.get('receiveYayin', receive_yayin),  # RX tone (WORKING)
            "rxCc": kwargs.get('rxCc', 0),
            "rxCtcss": 255,  # Field ignored by radio (test 07) - always 255
            "scrEn": 0,  # Field ignored by radio (test 08)
            "scrSeed1": 0,  # Field ignored by radio (test 08)
            "scrSeed2": 0,  # Field ignored by radio (test 08)
            "slot": kwargs.get('slot', 0),
            "spkgain": 0,  # Field ignored by radio (test 08)
            "sqlevel": 0,  # Field ignored by radio (test 08)
            "txCc": kwargs.get('txCc', 1),  # Radio uses 1, not 2
            "txCtcss": 255,  # Field ignored by radio (test 07) - always 255
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
    
    # Complete CTCSS frequency to yayin mapping table (all 50 standard tones)
    # Source: Test 10 results (10_complete_ctcss_mapping_test_readback.json) + previous testing
    # Validation: Test 11 - All tones confirmed operational (January 18, 2026)
    # Status: ✅ VALIDATED - 100% complete (50/50 tones mapped and verified)
    # Last Updated: January 18, 2026
    CTCSS_TO_YAYIN = {
        67.0: 1,   69.3: 2,   71.9: 3,   74.4: 4,   77.0: 5,   
        79.7: 6,   82.5: 7,   85.4: 8,   88.5: 9,   91.5: 10,
        94.8: 11,  97.4: 12,  100.0: 13, 103.5: 14, 107.2: 15,
        110.9: 16, 114.8: 17, 118.8: 18, 123.0: 19, 127.3: 20,
        131.8: 21, 136.5: 22, 141.3: 23, 146.2: 24, 151.4: 26,
        156.7: 27, 159.8: 28, 162.2: 29, 165.5: 30, 167.9: 31,
        171.3: 32, 173.8: 33, 177.3: 34, 179.9: 35, 183.5: 36,
        186.2: 37, 189.9: 38, 192.8: 39, 196.6: 40, 199.5: 41,
        203.5: 42, 206.5: 43, 210.7: 44, 218.1: 46, 225.7: 48,
        229.1: 49, 233.6: 50, 241.8: 52, 250.3: 54, 254.1: 55
    }
    
    # Reverse mapping for reading PMR171 files
    YAYIN_TO_CTCSS = {
        1: 67.0,  2: 69.3,  3: 71.9,  4: 74.4,  5: 77.0,
        6: 79.7,  7: 82.5,  8: 85.4,  9: 88.5,  10: 91.5,
        11: 94.8, 12: 97.4, 13: 100.0, 14: 103.5, 15: 107.2,
        16: 110.9, 17: 114.8, 18: 118.8, 19: 123.0, 20: 127.3,
        21: 131.8, 22: 136.5, 23: 141.3, 24: 146.2, 26: 151.4,
        27: 156.7, 28: 159.8, 29: 162.2, 30: 165.5, 31: 167.9,
        32: 171.3, 33: 173.8, 34: 177.3, 35: 179.9, 36: 183.5,
        37: 186.2, 38: 189.9, 39: 192.8, 40: 196.6, 41: 199.5,
        42: 203.5, 43: 206.5, 44: 210.7, 46: 218.1, 48: 225.7,
        49: 229.1, 50: 233.6, 52: 241.8, 54: 250.3, 55: 254.1
    }
    
    def _tone_to_yayin(self, tone: str = None) -> int:
        """Convert CTCSS/DCS tone to emitYayin/receiveYayin value
        
        Args:
            tone: Tone string (e.g., '100.0' for CTCSS, 'D023N' for DCS, or None)
            
        Returns:
            yayin value (0 for no tone, or encoded value)
            
        Note:
            Complete CTCSS mapping table from Test 10 (Jan 2026).
            Status: 100% complete (50/50 standard CTCSS tones mapped).
            Source: d:/Radio/Guohetec/Testing/10_complete_ctcss_mapping_test_readback.json
            
            Key discoveries:
            - Non-linear encoding with reserved gaps (yayin 25, 45, 47, 51, 53)
            - Radio uses emitYayin/receiveYayin (NOT txCtcss/rxCtcss)
            - Split tones supported (different TX/RX values)
            - DCS codes remain unmapped (likely use yayin 100+)
            
            See docs/COMPLETE_CTCSS_MAPPING.md for full details.
        """
        if not tone:
            return 0  # No tone
        
        # Try parsing as CTCSS frequency
        try:
            freq = float(tone)
            # Round to nearest 0.1 Hz for lookup
            freq = round(freq, 1)
            return self.CTCSS_TO_YAYIN.get(freq, 0)
        except (ValueError, TypeError):
            pass
        
        # TODO: Add DCS code support (D023N, D023I, etc.)
        # DCS codes likely use yayin values 100+ based on reserved gaps
        
        # Default: no tone configured
        return 0
    
    def _yayin_to_tone(self, yayin: int) -> str:
        """Convert emitYayin/receiveYayin value to CTCSS tone string
        
        Args:
            yayin: emitYayin or receiveYayin field value
            
        Returns:
            CTCSS frequency string (e.g., '100.0') or None if no tone
            
        Note:
            Used when reading PMR171 files to convert back to CHIRP format.
            Returns frequency with 1 decimal place as string.
        """
        if yayin == 0:
            return None
        
        freq = self.YAYIN_TO_CTCSS.get(yayin)
        if freq is not None:
            return f"{freq:.1f}"
        
        # TODO: Add DCS code decoding when mapping is complete
        
        return None  # Unknown yayin value
    
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
            
            # Convert CTCSS tone code to string format if needed
            rx_tone = self._ctcss_code_to_string(ch.get('rx_ctcss', 0))
            tx_tone = self._ctcss_code_to_string(ch.get('tx_ctcss', 0))
            
            pmr_ch = self.create_channel(
                index=index,
                name=ch['name'],
                rx_freq=ch['rx_freq'],
                tx_freq=ch.get('tx_freq'),
                mode=ch.get('mode', 'FM'),
                rx_tone=rx_tone,
                tx_tone=tx_tone,
                is_digital=ch.get('is_digital', False)
            )
            pmr_channels[str(index)] = pmr_ch
        
        return pmr_channels
    
    def _ctcss_code_to_string(self, code: int) -> str:
        """Convert CTCSS tone code to frequency string
        
        Args:
            code: CTCSS tone code (0 = no tone, 1-50 = CTCSS tones)
            
        Returns:
            Tone string (e.g., '100.0') or None for no tone
        """
        if code == 0:
            return None
        
        # Standard CTCSS tone frequencies (50 tones)
        # From CHIRP/radio standard mappings
        ctcss_tones = [
            67.0, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5, 94.8,
            97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3, 131.8,
            136.5, 141.3, 146.2, 151.4, 156.7, 162.2, 167.9, 173.8, 179.9, 186.2,
            192.8, 203.5, 210.7, 218.1, 225.7, 233.6, 241.8, 250.3, 69.3, 159.8,
            165.5, 171.3, 177.3, 183.5, 189.9, 196.6, 199.5, 206.5, 229.1, 254.1
        ]
        
        if 1 <= code <= len(ctcss_tones):
            return str(ctcss_tones[code - 1])
        
        return None
