"""PMR-171 Channel Programming Software

Converts various radio configuration formats to Guohetec PMR-171 JSON format
and manages radio programming via UART.
"""

__version__ = "0.1.0"
__author__ = "Aram Dergevorkian"

from .parsers import ChirpParser, BaseParser
from .writers import PMR171Writer
from .gui import ChannelTableViewer, view_channel_file
from .utils import frequency_to_bytes, bytes_to_frequency, bcd_to_frequency

__all__ = [
    'ChirpParser',
    'BaseParser',
    'PMR171Writer',
    'ChannelTableViewer',
    'view_channel_file',
    'frequency_to_bytes',
    'bytes_to_frequency',
    'bcd_to_frequency',
]
