"""Tests for utility functions"""

import pytest
from codeplug_converter.utils import (
    frequency_to_bytes,
    bytes_to_frequency,
    bcd_to_frequency,
    is_valid_frequency,
    is_chirp_metadata,
    is_corrupted_channel
)


def test_frequency_to_bytes():
    """Test frequency conversion to bytes"""
    # 146.52 MHz = 146,520,000 Hz
    result = frequency_to_bytes(146.52)
    assert result == (8, 184, 81, 64)


def test_bytes_to_frequency():
    """Test bytes to frequency conversion"""
    result = bytes_to_frequency((8, 184, 81, 64))
    assert abs(result - 146.52) < 0.000001


def test_round_trip_conversion():
    """Test frequency conversion round trip"""
    original = 146.52
    bytes_form = frequency_to_bytes(original)
    recovered = bytes_to_frequency(bytes_form)
    assert abs(original - recovered) < 0.000001


def test_bcd_to_frequency():
    """Test BCD decoding"""
    # [00 60 64 44] = 446.460 MHz
    bcd_bytes = bytes([0x00, 0x60, 0x64, 0x44])
    result = bcd_to_frequency(bcd_bytes)
    assert abs(result - 446.460) < 0.001


def test_is_valid_frequency_strict():
    """Test strict frequency validation"""
    assert is_valid_frequency(146.52, strict=True)  # VHF
    assert is_valid_frequency(446.00, strict=True)  # UHF
    assert is_valid_frequency(223.50, strict=True)  # 1.25m
    assert not is_valid_frequency(88.5, strict=True)  # FM broadcast
    assert not is_valid_frequency(800.0, strict=True)  # Out of range


def test_is_valid_frequency_relaxed():
    """Test relaxed frequency validation"""
    assert is_valid_frequency(118.0, strict=False)  # Airband
    assert is_valid_frequency(800.0, strict=False)  # Commercial
    assert not is_valid_frequency(10.0, strict=False)  # HF


def test_is_chirp_metadata():
    """Test CHIRP metadata detection"""
    # Test chunk with chirp marker
    chunk_with_chirp = b'chirp' + b'\x00' * 27
    assert is_chirp_metadata(chunk_with_chirp, "test")
    
    # Test normal channel
    normal_chunk = b'\x00' * 32
    assert not is_chirp_metadata(normal_chunk, "Normal")


def test_is_corrupted_channel():
    """Test corrupted channel detection"""
    # All FF bytes (empty slot)
    empty_chunk = b'\xff' * 32
    assert is_corrupted_channel(empty_chunk, "", 0.0)
    
    # Replacement character
    normal_chunk = b'\x00' * 32
    assert is_corrupted_channel(normal_chunk, "Test�Name", 146.52)
    
    # Too short name
    assert is_corrupted_channel(normal_chunk, "T", 146.52)
    
    # Valid channel
    assert not is_corrupted_channel(normal_chunk, "Valid Name", 146.52)


# TODO: Add more tests for edge cases
