"""Tests for PMR-171 writer"""

import pytest
from codeplug_converter.writers import PMR171Writer


def test_writer_initialization():
    """Test writer can be initialized"""
    writer = PMR171Writer()
    assert writer is not None
    assert writer.dmr_id == 3107683


def test_custom_dmr_id():
    """Test custom DMR ID"""
    writer = PMR171Writer(dmr_id=1234567)
    assert writer.dmr_id == 1234567


def test_create_channel():
    """Test channel creation"""
    writer = PMR171Writer()
    
    channel = writer.create_channel(
        index=0,
        name="Test",
        rx_freq=146.52,
        mode='FM'
    )
    
    assert channel['channelName'] == "Test\u0000"
    assert channel['channelLow'] == 0
    assert channel['vfoaMode'] == 6  # NFM


# TODO: Add more tests:
# - test_mode_mappings()
# - test_frequency_to_bytes()
# - test_simplex_vs_split()
# - test_digital_channels()
