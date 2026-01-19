"""Base parser interface for radio configuration formats"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path


class BaseParser(ABC):
    """Abstract base class for radio configuration file parsers"""
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a radio configuration file
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            List of channel dictionaries in standardized format
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: Path) -> bool:
        """Check if this parser supports the given file format
        
        Args:
            file_path: Path to check
            
        Returns:
            True if this parser can handle the file
        """
        pass
    
    def get_format_name(self) -> str:
        """Get human-readable format name
        
        Returns:
            Format name (e.g., "CHIRP IMG", "Anytone RDT")
        """
        return self.__class__.__name__.replace('Parser', '')
