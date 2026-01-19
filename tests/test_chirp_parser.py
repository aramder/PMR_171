"""Tests for CHIRP parser"""

import pytest
from pathlib import Path
from pmr_171_cps.parsers import ChirpParser


def test_chirp_parser_initialization():
    """Test parser can be initialized"""
    parser = ChirpParser()
    assert parser is not None
    assert parser.CHANNEL_SIZE == 32


def test_supports_format():
    """Test format detection"""
    parser = ChirpParser()
    
    assert parser.supports_format(Path("test.img"))
    assert parser.supports_format(Path("test.IMG"))
    assert not parser.supports_format(Path("test.txt"))
    assert not parser.supports_format(Path("test.rdt"))


# TODO: Add more tests:
# - test_parse_valid_img()
# - test_parse_with_metadata()
# - test_parse_corrupted_channels()
# - test_frequency_validation()
# - test_duplicate_detection()
