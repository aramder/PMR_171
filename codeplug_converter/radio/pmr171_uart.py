"""
PMR-171 Radio UART Communication Module

This module provides direct serial communication with the PMR-171 radio
for reading and writing channel configurations.

Protocol Reference: See docs/PMR171_PROTOCOL.md

Packet Format:
  | 0xA5 | 0xA5 | 0xA5 | 0xA5 | Length | Command | DATA... | CRC_H | CRC_L |

Commands:
  - 0x40: Channel Write (26-byte payload)
  - 0x41: Channel Read (2-byte request, 26-byte response)
  - 0x07: PTT Control
  - 0x0A: Mode Setting
  - 0x0B: Status Synchronization
  - 0x27: Equipment Type Recognition

Note: 0x43 was previously thought to be read, but is actually
write acknowledgment/echo. The correct read command is 0x41.

CRC: CRC-16-CCITT (polynomial 0x1021, initial value 0xFFFF)
"""

import logging
import struct
import time
from typing import List, Dict, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from enum import IntEnum

# Set up debug logging
logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class PMR171Error(Exception):
    """Base exception for PMR-171 communication errors"""
    pass


class ConnectionError(PMR171Error):
    """Error connecting to radio"""
    pass


class CommunicationError(PMR171Error):
    """Error during communication"""
    pass


class CRCError(PMR171Error):
    """CRC verification failed"""
    pass


class TimeoutError(PMR171Error):
    """Communication timeout"""
    pass


class Command(IntEnum):
    """PMR-171 command codes"""
    PTT_CONTROL = 0x07
    MODE_SETTING = 0x0A
    STATUS_SYNC = 0x0B
    EQUIPMENT_TYPE = 0x27
    POWER_CLASS = 0x28
    RIT_SETTING = 0x29
    SPECTRUM_DATA = 0x39
    CHANNEL_WRITE = 0x40
    CHANNEL_READ = 0x41  # Note: 0x41 is READ, 0x43 was write acknowledgment


class Mode(IntEnum):
    """Radio operating modes"""
    USB = 0
    LSB = 1
    CWR = 2
    CWL = 3
    AM = 4
    WFM = 5
    NFM = 6
    DIGI = 7
    PKT = 8
    DMR = 9
    UNUSED = 255


# CTCSS Tone Index to Frequency mapping
CTCSS_TONES = {
    0: None, 1: 67.0, 2: 69.3, 3: 71.9, 4: 74.4, 5: 77.0, 6: 79.7,
    7: 82.5, 8: 85.4, 9: 88.5, 10: 91.5, 11: 94.8, 12: 97.4, 13: 100.0,
    14: 103.5, 15: 107.2, 16: 110.9, 17: 114.8, 18: 118.8, 19: 123.0,
    20: 127.3, 21: 131.8, 22: 136.5, 23: 141.3, 24: 146.2, 25: 150.0,
    26: 151.4, 27: 156.7, 28: 159.8, 29: 162.2, 30: 165.5, 31: 167.9,
    32: 171.3, 33: 173.8, 34: 177.3, 35: 179.9, 36: 183.5, 37: 186.2,
    38: 189.9, 39: 192.8, 40: 196.6, 41: 199.5, 42: 203.5, 43: 206.5,
    44: 210.7, 45: 213.8, 46: 218.1, 47: 221.3, 48: 225.7, 49: 229.1,
    50: 233.6, 51: 237.1, 52: 241.8, 53: 245.5, 54: 250.3, 55: 254.1
}

# Reverse mapping: frequency to index
CTCSS_FREQ_TO_INDEX = {v: k for k, v in CTCSS_TONES.items() if v is not None}

# Packet header
PACKET_HEADER = bytes([0xA5, 0xA5, 0xA5, 0xA5])

# Default serial settings
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1.0
CHANNEL_COUNT = 1000


@dataclass
class ChannelData:
    """Represents a single channel configuration"""
    index: int
    rx_mode: int
    tx_mode: int
    rx_freq_hz: int
    tx_freq_hz: int
    rx_ctcss_index: int
    tx_ctcss_index: int
    name: str
    
    @property
    def rx_freq_mhz(self) -> float:
        return self.rx_freq_hz / 1_000_000
    
    @property
    def tx_freq_mhz(self) -> float:
        return self.tx_freq_hz / 1_000_000
    
    @property
    def rx_ctcss_hz(self) -> Optional[float]:
        return CTCSS_TONES.get(self.rx_ctcss_index)
    
    @property
    def tx_ctcss_hz(self) -> Optional[float]:
        return CTCSS_TONES.get(self.tx_ctcss_index)
    
    @property
    def rx_mode_name(self) -> str:
        try:
            return Mode(self.rx_mode).name
        except ValueError:
            return f"Unknown({self.rx_mode})"
    
    @property
    def tx_mode_name(self) -> str:
        try:
            return Mode(self.tx_mode).name
        except ValueError:
            return f"Unknown({self.tx_mode})"
    
    @property
    def is_empty(self) -> bool:
        """Check if this is an empty/unused channel"""
        return self.rx_mode == Mode.UNUSED or self.rx_freq_hz == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with JSON codeplug"""
        # Calculate frequency bytes (big-endian)
        rx_bytes = self.rx_freq_hz.to_bytes(4, 'big')
        tx_bytes = self.tx_freq_hz.to_bytes(4, 'big')
        
        return {
            "channelLow": self.index,
            "channelHigh": 0,
            "channelName": self.name,
            "vfoaMode": self.rx_mode,
            "vfobMode": self.tx_mode,
            "vfoaFrequency1": rx_bytes[0],
            "vfoaFrequency2": rx_bytes[1],
            "vfoaFrequency3": rx_bytes[2],
            "vfoaFrequency4": rx_bytes[3],
            "vfobFrequency1": tx_bytes[0],
            "vfobFrequency2": tx_bytes[1],
            "vfobFrequency3": tx_bytes[2],
            "vfobFrequency4": tx_bytes[3],
            "emitYayin": self.tx_ctcss_index,
            "receiveYayin": self.rx_ctcss_index,
            "rxCtcss": 255,  # Ignored by radio
            "txCtcss": 255,  # Ignored by radio
            # Default values for other fields
            "power": 2,
            "step": 0,
            "txOffset": 0,
            "oneTone": 0,
            "scramble": 0,
            "compander": 0,
            "sql": 0,
            "chType": 1 if self.rx_mode == Mode.DMR else 0,
            "callFormat": 0,
            "callId1": 0,
            "callId2": 0,
            "callId3": 0,
            "callId4": 0,
            "ownId1": 0,
            "ownId2": 0,
            "ownId3": 0,
            "ownId4": 0,
            "rxCc": 0,
            "txCc": 2,
            "slot": 0,
            "vfoaFilter": 0,
            "vfobFilter": 0,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelData':
        """Create ChannelData from JSON codeplug dictionary"""
        # Extract frequency from bytes
        rx_freq = (
            (data.get("vfoaFrequency1", 0) << 24) |
            (data.get("vfoaFrequency2", 0) << 16) |
            (data.get("vfoaFrequency3", 0) << 8) |
            data.get("vfoaFrequency4", 0)
        )
        tx_freq = (
            (data.get("vfobFrequency1", 0) << 24) |
            (data.get("vfobFrequency2", 0) << 16) |
            (data.get("vfobFrequency3", 0) << 8) |
            data.get("vfobFrequency4", 0)
        )
        
        return cls(
            index=data.get("channelLow", 0),
            rx_mode=data.get("vfoaMode", Mode.NFM),
            tx_mode=data.get("vfobMode", Mode.NFM),
            rx_freq_hz=rx_freq,
            tx_freq_hz=tx_freq,
            rx_ctcss_index=data.get("receiveYayin", 0),
            tx_ctcss_index=data.get("emitYayin", 0),
            name=data.get("channelName", "")
        )
    
    def __repr__(self) -> str:
        rx_tone = f"{self.rx_ctcss_hz} Hz" if self.rx_ctcss_hz else "None"
        tx_tone = f"{self.tx_ctcss_hz} Hz" if self.tx_ctcss_hz else "None"
        return (f"Ch{self.index}: {self.rx_freq_mhz:.4f} MHz ({self.rx_mode_name}) "
                f"RX={rx_tone}, TX={tx_tone}, Name='{self.name}'")


def crc16_ccitt(data: bytes) -> int:
    """
    Calculate CRC-16-CCITT for PMR-171 protocol.
    
    Algorithm from PMR-171 manual (Sheet 39):
    - Polynomial: 0x1021
    - Initial value: 0xFFFF
    - Input: bytes from Length field through last DATA byte (before CRC)
    
    Args:
        data: Bytes to calculate CRC for
        
    Returns:
        16-bit CRC value
    """
    crc = 0xFFFF
    for byte in data:
        cur = byte << 8
        for _ in range(8):
            if (crc ^ cur) & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
            cur = (cur << 1) & 0xFFFF
    return crc


def build_packet(command: int, data: bytes = b'') -> bytes:
    """
    Build a complete PMR-171 packet.
    
    Packet format:
    | 0xA5 | 0xA5 | 0xA5 | 0xA5 | Length | Command | DATA... | CRC_H | CRC_L |
    
    Args:
        command: Command byte
        data: Data payload (can be empty)
        
    Returns:
        Complete packet bytes
    """
    # Length = 1 (command) + len(data) + 2 (CRC)
    length = 1 + len(data) + 2
    
    # Build packet without CRC
    packet = PACKET_HEADER + bytes([length, command]) + data
    
    # Calculate CRC over Length + Command + Data
    crc_data = bytes([length, command]) + data
    crc = crc16_ccitt(crc_data)
    
    # Append CRC (big-endian)
    packet += struct.pack('>H', crc)
    
    return packet


def parse_packet(data: bytes) -> Tuple[int, bytes, bool]:
    """
    Parse a PMR-171 packet.
    
    Args:
        data: Raw packet bytes (must start with header)
        
    Returns:
        Tuple of (command, payload, crc_valid)
        
    Raises:
        ValueError: If packet is malformed
    """
    if len(data) < 8:
        raise ValueError(f"Packet too short: {len(data)} bytes")
    
    if data[:4] != PACKET_HEADER:
        raise ValueError(f"Invalid header: {data[:4].hex()}")
    
    length = data[4]
    if length < 3:
        raise ValueError(f"Invalid length: {length}")
    
    expected_size = 4 + 1 + length  # header + length byte + (cmd + data + crc)
    if len(data) < expected_size:
        raise ValueError(f"Packet incomplete: expected {expected_size}, got {len(data)}")
    
    command = data[5]
    payload = data[6:5 + length - 2]  # Exclude CRC bytes
    
    # Verify CRC
    crc_data = data[4:5 + length - 2]  # Length + Command + Data
    calculated_crc = crc16_ccitt(crc_data)
    packet_crc = (data[5 + length - 2] << 8) | data[5 + length - 1]
    
    return command, payload, calculated_crc == packet_crc


def build_channel_packet(channel: ChannelData, command: int = Command.CHANNEL_WRITE) -> bytes:
    """
    Build a channel write/read packet.
    
    Channel data structure (26 bytes):
    - 0-1:   Channel index (big-endian)
    - 2:     RX Mode
    - 3:     TX Mode
    - 4-7:   RX Frequency (big-endian Hz)
    - 8-11:  TX Frequency (big-endian Hz)
    - 12:    RX CTCSS index
    - 13:    TX CTCSS index
    - 14-25: Channel name (12 bytes, null-terminated)
    
    Args:
        channel: ChannelData to encode
        command: Command code (CHANNEL_WRITE or CHANNEL_READ)
        
    Returns:
        Complete packet bytes
    """
    # Encode channel name (12 bytes, null-terminated)
    name_bytes = channel.name.encode('ascii', errors='replace')[:11]
    name_bytes = name_bytes + b'\x00' * (12 - len(name_bytes))
    
    # Build data payload
    data = struct.pack(
        '>HBBIIBBc11s',  # Note: 12 byte name field
        channel.index,
        channel.rx_mode,
        channel.tx_mode,
        channel.rx_freq_hz,
        channel.tx_freq_hz,
        channel.rx_ctcss_index,
        channel.tx_ctcss_index,
        name_bytes[:1],  # First byte of name
        name_bytes[1:12]  # Rest of name
    )
    
    # Alternative packing without struct issues
    data = (
        struct.pack('>H', channel.index) +  # Channel index (2 bytes)
        bytes([channel.rx_mode]) +           # RX mode (1 byte)
        bytes([channel.tx_mode]) +           # TX mode (1 byte)
        struct.pack('>I', channel.rx_freq_hz) +  # RX freq (4 bytes)
        struct.pack('>I', channel.tx_freq_hz) +  # TX freq (4 bytes)
        bytes([channel.rx_ctcss_index]) +    # RX CTCSS (1 byte)
        bytes([channel.tx_ctcss_index]) +    # TX CTCSS (1 byte)
        name_bytes                           # Name (12 bytes)
    )
    
    return build_packet(command, data)


def parse_channel_packet(data: bytes) -> ChannelData:
    """
    Parse a channel packet payload into ChannelData.
    
    Args:
        data: Payload bytes (26 bytes, after command byte)
        
    Returns:
        ChannelData object
    """
    if len(data) < 26:
        raise ValueError(f"Channel data too short: {len(data)} bytes")
    
    index = struct.unpack('>H', data[0:2])[0]
    rx_mode = data[2]
    tx_mode = data[3]
    rx_freq = struct.unpack('>I', data[4:8])[0]
    tx_freq = struct.unpack('>I', data[8:12])[0]
    rx_ctcss = data[12]
    tx_ctcss = data[13]
    
    # Decode name (null-terminated ASCII)
    name_bytes = data[14:26]
    try:
        name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')
    except:
        name = ""
    
    return ChannelData(
        index=index,
        rx_mode=rx_mode,
        tx_mode=tx_mode,
        rx_freq_hz=rx_freq,
        tx_freq_hz=tx_freq,
        rx_ctcss_index=rx_ctcss,
        tx_ctcss_index=tx_ctcss,
        name=name
    )


def list_serial_ports() -> List[Dict[str, str]]:
    """
    List available serial ports.
    
    Returns:
        List of dicts with 'port', 'description', 'hwid' keys
    """
    if not SERIAL_AVAILABLE:
        return []
    
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            'port': port.device,
            'description': port.description,
            'hwid': port.hwid or ''
        })
    return ports


class PMR171Radio:
    """
    PMR-171 Radio UART Interface
    
    Provides methods for reading and writing channel configurations
    directly to the radio via serial connection.
    
    Example:
        >>> radio = PMR171Radio('COM6')
        >>> radio.connect()
        >>> channels = radio.read_all_channels(progress_callback=print)
        >>> radio.disconnect()
    """
    
    def __init__(self, port: str, baudrate: int = DEFAULT_BAUDRATE, 
                 timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize PMR-171 radio interface.
        
        Args:
            port: Serial port name (e.g., 'COM6', '/dev/ttyUSB0')
            baudrate: Serial baud rate (default 115200)
            timeout: Read timeout in seconds
        """
        if not SERIAL_AVAILABLE:
            raise ImportError(
                "pyserial is required for UART communication. "
                "Install it with: pip install pyserial"
            )
        
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if serial port is open"""
        return self._serial is not None and self._serial.is_open
    
    def connect(self) -> None:
        """
        Open serial connection to radio.
        
        The PMR-171 requires DTR and RTS to be set high to enter programming mode.
        
        Raises:
            ConnectionError: If connection fails
        """
        if self.is_connected:
            return
        
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=None,  # No write timeout - writes should be instant
                rtscts=False,  # Disable hardware flow control
                dsrdtr=False   # Disable DSR/DTR flow control
            )
            
            # CRITICAL: Set DTR and RTS high to enable radio programming mode
            self._serial.dtr = True
            self._serial.rts = True
            
            # Clear any pending data
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            time.sleep(0.5)  # Allow radio to stabilize and enter programming mode
            
            logger.debug(f"Connected to {self.port} with DTR=True, RTS=True")
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {self.port}: {e}")
    
    def disconnect(self) -> None:
        """Close serial connection"""
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
    
    def _send_packet(self, packet: bytes) -> None:
        """
        Send a packet to the radio.
        
        Args:
            packet: Complete packet bytes
            
        Raises:
            CommunicationError: If send fails
        """
        if not self.is_connected:
            raise CommunicationError("Not connected to radio")
        
        try:
            self._serial.write(packet)
            self._serial.flush()
        except serial.SerialException as e:
            raise CommunicationError(f"Failed to send packet: {e}")
    
    def _receive_packet(self, expected_length: int = None) -> bytes:
        """
        Receive a packet from the radio.
        
        Args:
            expected_length: Expected packet length (optional)
            
        Returns:
            Complete packet bytes
            
        Raises:
            TimeoutError: If no response within timeout
            CRCError: If CRC verification fails
        """
        if not self.is_connected:
            raise CommunicationError("Not connected to radio")
        
        try:
            # Read header
            header = self._serial.read(4)
            if len(header) < 4:
                raise TimeoutError("Timeout waiting for packet header")
            
            if header != PACKET_HEADER:
                raise CommunicationError(f"Invalid header: {header.hex()}")
            
            # Read length byte
            length_byte = self._serial.read(1)
            if not length_byte:
                raise TimeoutError("Timeout waiting for length byte")
            
            length = length_byte[0]
            
            # Read rest of packet (command + data + CRC)
            remaining = self._serial.read(length)
            if len(remaining) < length:
                raise TimeoutError(f"Timeout reading packet data: got {len(remaining)}/{length}")
            
            packet = header + length_byte + remaining
            
            # Verify CRC
            command, payload, crc_valid = parse_packet(packet)
            if not crc_valid:
                raise CRCError("Packet CRC verification failed")
            
            return packet
            
        except serial.SerialException as e:
            raise CommunicationError(f"Serial error: {e}")
    
    def send_command(self, command: int, data: bytes = b'') -> bytes:
        """
        Send a command and receive response.
        
        Args:
            command: Command byte
            data: Command data payload
            
        Returns:
            Response payload bytes
        """
        packet = build_packet(command, data)
        self._send_packet(packet)
        response = self._receive_packet()
        cmd, payload, _ = parse_packet(response)
        return payload
    
    def read_channel(self, channel_index: int) -> ChannelData:
        """
        Read a single channel from the radio.
        
        Uses 0x41 command with just 2-byte channel index (big-endian).
        Radio responds with full 26-byte channel data.
        
        Args:
            channel_index: Channel number (0-999)
            
        Returns:
            ChannelData object
        """
        # Build channel read request - just the 2-byte channel index
        data = struct.pack('>H', channel_index)
        packet = build_packet(Command.CHANNEL_READ, data)
        
        self._send_packet(packet)
        response = self._receive_packet()
        cmd, payload, _ = parse_packet(response)
        
        return parse_channel_packet(payload)
    
    def write_channel(self, channel: ChannelData) -> bool:
        """
        Write a single channel to the radio.
        
        Args:
            channel: ChannelData to write
            
        Returns:
            True if successful
        """
        packet = build_channel_packet(channel, Command.CHANNEL_WRITE)
        self._send_packet(packet)
        
        # Wait for acknowledgment
        response = self._receive_packet()
        cmd, payload, _ = parse_packet(response)
        
        # Verify the write by checking response
        return cmd == Command.CHANNEL_WRITE
    
    def read_all_channels(self, 
                          progress_callback: Callable[[int, int, str], None] = None,
                          include_empty: bool = True,
                          cancel_check: Callable[[], bool] = None) -> List[ChannelData]:
        """
        Read all channels from the radio.
        
        Args:
            progress_callback: Optional callback(current, total, message)
            include_empty: If True, include empty channels in result
            cancel_check: Optional callback that returns True if operation should be cancelled
            
        Returns:
            List of ChannelData objects
        """
        channels = []
        
        for i in range(CHANNEL_COUNT):
            # Check for cancellation before starting each channel
            if cancel_check and cancel_check():
                if progress_callback:
                    progress_callback(i, CHANNEL_COUNT, f"Cancelled at channel {i}")
                break
            
            if progress_callback:
                progress_callback(i + 1, CHANNEL_COUNT, f"Reading channel {i}")
            
            try:
                channel = self.read_channel(i)
                if include_empty or not channel.is_empty:
                    channels.append(channel)
            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, CHANNEL_COUNT, f"Error reading channel {i}: {e}")
        
        return channels
    
    def read_selected_channels(self,
                               channel_indices: List[int],
                               progress_callback: Callable[[int, int, str], None] = None,
                               cancel_check: Callable[[], bool] = None) -> List[ChannelData]:
        """
        Read specific channels from the radio.
        
        Args:
            channel_indices: List of channel indices to read
            progress_callback: Optional callback(current, total, message)
            cancel_check: Optional callback that returns True if operation should be cancelled
            
        Returns:
            List of ChannelData objects
        """
        channels = []
        total = len(channel_indices)
        
        logger.info(f"read_selected_channels: {total} channels to read")
        
        for idx, ch_num in enumerate(channel_indices):
            # Check for cancellation before starting each channel
            if cancel_check and cancel_check():
                logger.info(f"Cancelled at channel {ch_num}")
                if progress_callback:
                    progress_callback(idx, total, f"Cancelled at channel {ch_num}")
                break
            
            if progress_callback:
                progress_callback(idx + 1, total, f"Reading channel {ch_num}")
            
            try:
                logger.debug(f"Reading channel {ch_num}...")
                channel = self.read_channel(ch_num)
                logger.info(f"Channel {ch_num}: {channel.rx_freq_mhz:.6f} MHz, name='{channel.name}'")
                channels.append(channel)
            except Exception as e:
                logger.error(f"Error reading channel {ch_num}: {e}")
                if progress_callback:
                    progress_callback(idx + 1, total, f"Error reading channel {ch_num}: {e}")
        
        logger.info(f"read_selected_channels: returning {len(channels)} channels")
        return channels
    
    def write_all_channels(self,
                           channels: List[ChannelData],
                           progress_callback: Callable[[int, int, str], None] = None,
                           cancel_check: Callable[[], bool] = None) -> int:
        """
        Write all channels to the radio.
        
        Args:
            channels: List of ChannelData objects to write
            progress_callback: Optional callback(current, total, message)
            cancel_check: Optional callback that returns True if operation should be cancelled
            
        Returns:
            Number of channels successfully written
        """
        success_count = 0
        total = len(channels)
        
        for i, channel in enumerate(channels):
            # Check for cancellation before starting each channel
            if cancel_check and cancel_check():
                if progress_callback:
                    progress_callback(i, total, f"Cancelled at channel {channel.index}")
                break
            
            if progress_callback:
                progress_callback(i + 1, total, f"Writing channel {channel.index}")
            
            try:
                if self.write_channel(channel):
                    success_count += 1
            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, total, f"Error writing channel {channel.index}: {e}")
        
        return success_count
    
    def write_selected_channels(self,
                                channels: List[ChannelData],
                                progress_callback: Callable[[int, int, str], None] = None,
                                cancel_check: Callable[[], bool] = None) -> int:
        """
        Write specific channels to the radio.
        
        Args:
            channels: List of ChannelData objects to write
            progress_callback: Optional callback(current, total, message)
            cancel_check: Optional callback that returns True if operation should be cancelled
            
        Returns:
            Number of channels successfully written
        """
        # Same implementation as write_all_channels but with explicit naming for clarity
        return self.write_all_channels(channels, progress_callback, cancel_check)
    
    def read_codeplug(self, 
                      progress_callback: Callable[[int, int, str], None] = None) -> Dict[str, Dict]:
        """
        Read all channels and return as JSON-compatible codeplug dictionary.
        
        Args:
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            Dictionary with channel IDs as keys, channel data dicts as values
        """
        channels = self.read_all_channels(progress_callback, include_empty=True)
        
        codeplug = {}
        for channel in channels:
            codeplug[str(channel.index)] = channel.to_dict()
        
        return codeplug
    
    def write_codeplug(self,
                       codeplug: Dict[str, Dict],
                       progress_callback: Callable[[int, int, str], None] = None) -> int:
        """
        Write a codeplug dictionary to the radio.
        
        Args:
            codeplug: Dictionary with channel IDs as keys, channel data dicts as values
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            Number of channels successfully written
        """
        channels = []
        for ch_id, ch_data in codeplug.items():
            channels.append(ChannelData.from_dict(ch_data))
        
        # Sort by channel index
        channels.sort(key=lambda c: c.index)
        
        return self.write_all_channels(channels, progress_callback)
    
    def get_radio_info(self) -> Dict[str, Any]:
        """
        Query radio for identification info.
        
        Returns:
            Dictionary with radio info (model, firmware, etc.)
        """
        try:
            payload = self.send_command(Command.EQUIPMENT_TYPE)
            # Parse equipment type response
            # Format varies by firmware version
            return {
                'raw_response': payload.hex(),
                'model': 'PMR-171',
                'connected': True
            }
        except Exception as e:
            return {
                'error': str(e),
                'connected': False
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current radio status.
        
        Returns:
            Dictionary with status information
        """
        try:
            payload = self.send_command(Command.STATUS_SYNC)
            # Parse status response - contains frequencies, modes, etc.
            return {
                'raw_response': payload.hex(),
                'status': 'connected'
            }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error'
            }


# Utility functions for GUI integration

def channels_to_codeplug(channels: List[ChannelData]) -> Dict[str, Dict]:
    """Convert list of ChannelData to codeplug dictionary format"""
    return {str(ch.index): ch.to_dict() for ch in channels}


def codeplug_to_channels(codeplug: Dict[str, Dict]) -> List[ChannelData]:
    """Convert codeplug dictionary to list of ChannelData"""
    channels = [ChannelData.from_dict(ch_data) for ch_data in codeplug.values()]
    channels.sort(key=lambda c: c.index)
    return channels
