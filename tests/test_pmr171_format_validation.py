"""Tests to validate PMR-171 JSON format compatibility with factory programming software"""

import pytest
import json
from pathlib import Path
from codeplug_converter.writers import PMR171Writer
from codeplug_converter.utils.frequency import frequency_to_bytes, bytes_to_frequency


class TestPMR171FormatValidation:
    """Test suite to ensure JSON output is compatible with PMR-171 factory software"""
    
    @pytest.fixture
    def writer(self):
        """Create a PMR171Writer instance"""
        return PMR171Writer()
    
    @pytest.fixture
    def example_json_path(self):
        """Path to the example MODE_TEST.json file"""
        return Path("examples/MODE_TEST.json")
    
    @pytest.fixture
    def example_data(self, example_json_path):
        """Load the example MODE_TEST.json for reference"""
        if example_json_path.exists():
            with open(example_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def test_json_structure_has_required_top_level_keys(self, example_data):
        """Verify JSON has radio_profile, radio_metadata, and channels keys"""
        assert example_data is not None, "MODE_TEST.json not found"
        assert "radio_profile" in example_data
        assert "radio_metadata" in example_data
        assert "channels" in example_data
        assert example_data["radio_profile"] == "pmr171"
        assert example_data["radio_metadata"]["manufacturer"] == "Guohetec"
        assert example_data["radio_metadata"]["model"] == "PMR-171"

    def test_channel_has_all_required_fields(self, writer):
        """Verify created channel has all 40+ required fields"""
        channel = writer.create_channel(
            index=0,
            name="Test",
            rx_freq=146.52,
            mode='FM'
        )
        
        required_fields = [
            'callFormat', 'callId1', 'callId2', 'callId3', 'callId4',
            'chBsMode', 'chType', 'channelHigh', 'channelLow', 'channelName',
            'dmodGain', 'emitYayin',
            'ownId1', 'ownId2', 'ownId3', 'ownId4',
            'receiveYayin', 'rxCc', 'rxCtcss', 'scrEn', 'scrSeed1', 'scrSeed2',
            'slot', 'spkgain', 'sqlevel', 'txCc', 'txCtcss',
            'vfoaFrequency1', 'vfoaFrequency2', 'vfoaFrequency3', 'vfoaFrequency4',
            'vfoaMode',
            'vfobFrequency1', 'vfobFrequency2', 'vfobFrequency3', 'vfobFrequency4',
            'vfobMode'
        ]
        
        for field in required_fields:
            assert field in channel, f"Missing required field: {field}"

    def test_channel_field_types(self, writer):
        """Verify all channel fields have correct data types"""
        channel = writer.create_channel(
            index=0,
            name="Test",
            rx_freq=146.52,
            mode='FM'
        )
        
        # Integer fields (should be int, not float or string)
        integer_fields = [
            'callFormat', 'callId1', 'callId2', 'callId3', 'callId4',
            'chBsMode', 'chType', 'channelHigh', 'channelLow',
            'dmodGain', 'emitYayin',
            'ownId1', 'ownId2', 'ownId3', 'ownId4',
            'receiveYayin', 'rxCc', 'rxCtcss', 'scrEn', 'scrSeed1', 'scrSeed2',
            'slot', 'spkgain', 'sqlevel', 'txCc', 'txCtcss',
            'vfoaFrequency1', 'vfoaFrequency2', 'vfoaFrequency3', 'vfoaFrequency4',
            'vfoaMode',
            'vfobFrequency1', 'vfobFrequency2', 'vfobFrequency3', 'vfobFrequency4',
            'vfobMode'
        ]
        
        for field in integer_fields:
            assert isinstance(channel[field], int), f"Field {field} should be int, got {type(channel[field])}"
            assert 0 <= channel[field] <= 255, f"Field {field} value {channel[field]} out of byte range"
        
        # String field
        assert isinstance(channel['channelName'], str)

    def test_channel_name_format(self, writer):
        """Verify channel name is max 15 chars + null terminator"""
        # Test normal length
        channel = writer.create_channel(index=0, name="Test", rx_freq=146.52)
        assert channel['channelName'] == "Test\u0000"
        
        # Test max length (15 chars)
        long_name = "A" * 15
        channel = writer.create_channel(index=0, name=long_name, rx_freq=146.52)
        assert len(channel['channelName']) == 16  # 15 chars + null
        assert channel['channelName'] == long_name + "\u0000"
        
        # Test truncation for names > 15 chars
        too_long = "A" * 20
        channel = writer.create_channel(index=0, name=too_long, rx_freq=146.52)
        assert len(channel['channelName']) == 16
        assert channel['channelName'] == ("A" * 15) + "\u0000"

    def test_channel_number_encoding(self, writer):
        """Verify channel number is split into high/low bytes correctly"""
        # Test channel 0
        channel = writer.create_channel(index=0, name="Test", rx_freq=146.52)
        assert channel['channelHigh'] == 0
        assert channel['channelLow'] == 0
        
        # Test channel 255
        channel = writer.create_channel(index=255, name="Test", rx_freq=146.52)
        assert channel['channelHigh'] == 0
        assert channel['channelLow'] == 255
        
        # Test channel 256 (0x0100)
        channel = writer.create_channel(index=256, name="Test", rx_freq=146.52)
        assert channel['channelHigh'] == 1
        assert channel['channelLow'] == 0
        
        # Test channel 1000 (0x03E8)
        channel = writer.create_channel(index=1000, name="Test", rx_freq=146.52)
        assert channel['channelHigh'] == 3
        assert channel['channelLow'] == 232

    def test_frequency_encoding_big_endian(self, writer):
        """Verify frequencies are encoded as big-endian 4-byte integers in Hz"""
        # Test 146.52 MHz = 146,520,000 Hz = 0x08BBB7C0
        channel = writer.create_channel(index=0, name="Test", rx_freq=146.52)
        assert channel['vfoaFrequency1'] == 0x08
        assert channel['vfoaFrequency2'] == 0xBB
        assert channel['vfoaFrequency3'] == 0xB7
        assert channel['vfoaFrequency4'] == 0xC0
        
        # Verify round-trip conversion
        freq_bytes = (
            channel['vfoaFrequency1'],
            channel['vfoaFrequency2'],
            channel['vfoaFrequency3'],
            channel['vfoaFrequency4']
        )
        reconstructed_freq = bytes_to_frequency(freq_bytes)
        assert abs(reconstructed_freq - 146.52) < 0.000001

    def test_frequency_precision(self):
        """Verify frequency conversion handles standard precision correctly"""
        # Test various common frequencies
        test_cases = [
            (146.52, 146_520_000),      # VHF calling frequency
            (446.00, 446_000_000),      # UHF PMR446
            (14.074, 14_074_000),       # HF FT8
            (7.200, 7_200_000),         # 40m band
            (144.39, 144_390_000),      # APRS
            (433.500, 433_500_000),     # UHF
        ]
        
        for freq_mhz, expected_hz in test_cases:
            freq_bytes = frequency_to_bytes(freq_mhz)
            reconstructed_hz = (
                (freq_bytes[0] << 24) |
                (freq_bytes[1] << 16) |
                (freq_bytes[2] << 8) |
                freq_bytes[3]
            )
            assert reconstructed_hz == expected_hz, \
                f"Frequency {freq_mhz} MHz encoded incorrectly: {reconstructed_hz} != {expected_hz}"

    def test_simplex_operation(self, writer):
        """Verify simplex channels have same RX and TX frequencies"""
        channel = writer.create_channel(
            index=0,
            name="Simplex",
            rx_freq=146.52,
            tx_freq=None  # Simplex (no explicit TX freq)
        )
        
        # VFO A (RX) and VFO B (TX) should be identical for simplex
        assert channel['vfoaFrequency1'] == channel['vfobFrequency1']
        assert channel['vfoaFrequency2'] == channel['vfobFrequency2']
        assert channel['vfoaFrequency3'] == channel['vfobFrequency3']
        assert channel['vfoaFrequency4'] == channel['vfobFrequency4']

    def test_split_operation(self, writer):
        """Verify split channels have different RX and TX frequencies"""
        channel = writer.create_channel(
            index=0,
            name="Split",
            rx_freq=146.52,
            tx_freq=146.52 + 0.6  # +600 kHz offset
        )
        
        # VFO A (RX) and VFO B (TX) should be different for split
        rx_bytes = (
            channel['vfoaFrequency1'],
            channel['vfoaFrequency2'],
            channel['vfoaFrequency3'],
            channel['vfoaFrequency4']
        )
        tx_bytes = (
            channel['vfobFrequency1'],
            channel['vfobFrequency2'],
            channel['vfobFrequency3'],
            channel['vfobFrequency4']
        )
        
        rx_freq = bytes_to_frequency(rx_bytes)
        tx_freq = bytes_to_frequency(tx_bytes)
        
        assert abs(rx_freq - 146.52) < 0.000001
        assert abs(tx_freq - 147.12) < 0.000001
        assert rx_bytes != tx_bytes

    def test_mode_mappings_complete(self, writer):
        """Verify all documented mode mappings are correct"""
        expected_modes = {
            'FM': 6, 'NFM': 6, 'WFM': 5, 'AM': 4,
            'USB': 0, 'LSB': 1, 'CWR': 2, 'CWL': 3,
            'DMR': 9, 'DIGI': 7, 'PKT': 8,
            'DSTAR': 7, 'C4FM': 7, 'DIGITAL': 9,
            'SSB': 0, 'CW': 3
        }
        
        for mode_str, expected_value in expected_modes.items():
            channel = writer.create_channel(
                index=0,
                name="Test",
                rx_freq=146.52,
                mode=mode_str
            )
            assert channel['vfoaMode'] == expected_value, \
                f"Mode {mode_str} should map to {expected_value}, got {channel['vfoaMode']}"
            assert channel['vfobMode'] == expected_value, \
                f"Mode {mode_str} TX should also be {expected_value}"

    def test_mode_case_insensitive(self, writer):
        """Verify mode strings are case-insensitive"""
        modes = ['fm', 'FM', 'Fm', 'fM']
        for mode in modes:
            channel = writer.create_channel(index=0, name="Test", rx_freq=146.52, mode=mode)
            assert channel['vfoaMode'] == 6

    def test_mode_default_fallback(self, writer):
        """Verify unknown modes default to FM (6)"""
        channel = writer.create_channel(
            index=0,
            name="Test",
            rx_freq=146.52,
            mode='UNKNOWN_MODE'
        )
        assert channel['vfoaMode'] == 6  # Should default to FM

    def test_analog_channel_type(self, writer):
        """Verify analog channels have chType=0"""
        channel = writer.create_channel(
            index=0,
            name="FM Channel",
            rx_freq=146.52,
            mode='FM',
            is_digital=False
        )
        assert channel['chType'] == 0

    def test_digital_channel_type(self, writer):
        """Verify digital channels have chType=1"""
        channel = writer.create_channel(
            index=0,
            name="DMR Channel",
            rx_freq=146.52,
            mode='DMR',
            is_digital=True
        )
        assert channel['chType'] == 1

    def test_ctcss_values(self, writer):
        """Verify CTCSS/DCS codes are stored correctly"""
        # Test no tone
        channel = writer.create_channel(
            index=0, name="Test", rx_freq=146.52,
            rx_ctcss=0, tx_ctcss=0
        )
        assert channel['rxCtcss'] == 0
        assert channel['txCtcss'] == 0
        
        # Test CTCSS tone (1-255)
        channel = writer.create_channel(
            index=0, name="Test", rx_freq=146.52,
            rx_ctcss=67, tx_ctcss=67  # 67.0 Hz CTCSS
        )
        assert channel['rxCtcss'] == 67
        assert channel['txCtcss'] == 67
        
        # Test DCS code (1000+)
        channel = writer.create_channel(
            index=0, name="Test", rx_freq=146.52,
            rx_ctcss=1023, tx_ctcss=1023  # DCS 023
        )
        assert channel['rxCtcss'] == 1023
        assert channel['txCtcss'] == 1023

    def test_default_field_values(self, writer):
        """Verify default values match factory software expectations"""
        channel = writer.create_channel(index=0, name="Test", rx_freq=146.52)
        
        # These should all be 0 by default (from MODE_TEST.json)
        zero_fields = [
            'callFormat', 'callId1', 'callId2', 'callId3', 'callId4',
            'chBsMode', 'dmodGain', 'emitYayin',
            'ownId1', 'ownId2', 'ownId3', 'ownId4',
            'receiveYayin', 'rxCc', 'rxCtcss', 'scrEn', 'scrSeed1', 'scrSeed2',
            'slot', 'spkgain', 'sqlevel', 'txCtcss'
        ]
        
        for field in zero_fields:
            assert channel[field] == 0, f"Field {field} should default to 0"
        
        # txCc should default to 2 (from MODE_TEST.json)
        assert channel['txCc'] == 2

    def test_json_serialization(self, writer, tmp_path):
        """Verify JSON can be serialized and matches expected format"""
        channels = {
            "0": writer.create_channel(index=0, name="Test1", rx_freq=146.52),
            "1": writer.create_channel(index=1, name="Test2", rx_freq=446.00)
        }
        
        output_file = tmp_path / "test_output.json"
        writer.write(channels, output_file)
        
        # Verify file was created
        assert output_file.exists()
        
        # Verify it can be loaded back
        with open(output_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        # Verify structure
        assert "0" in loaded
        assert "1" in loaded
        assert loaded["0"]["channelName"] == "Test1\u0000"
        assert loaded["1"]["channelName"] == "Test2\u0000"

    def test_channels_dict_keyed_by_strings(self, writer):
        """Verify channels dict uses string keys, not integers"""
        channels = writer.channels_from_parsed([
            {'index': 0, 'name': 'Ch0', 'rx_freq': 146.52},
            {'index': 1, 'name': 'Ch1', 'rx_freq': 446.00},
            {'index': 10, 'name': 'Ch10', 'rx_freq': 433.50}
        ])
        
        # Keys should be strings
        assert "0" in channels
        assert "1" in channels
        assert "10" in channels
        assert 0 not in channels
        assert 1 not in channels

    def test_compatibility_with_example_file(self, example_data, writer):
        """Verify our output matches structure of MODE_TEST.json"""
        if example_data is None:
            pytest.skip("MODE_TEST.json not found")
        
        # Get a reference channel from example file
        example_channel = example_data['channels']['0']
        
        # Create similar channel with our writer
        our_channel = writer.create_channel(
            index=0,
            name="MODE_0_SSB",
            rx_freq=146.52,
            mode='USB'
        )
        
        # Verify all fields exist in both
        for field in example_channel.keys():
            assert field in our_channel, f"Our channel missing field: {field}"
        
        for field in our_channel.keys():
            assert field in example_channel, f"Example channel missing field: {field}"

    def test_dmr_id_encoding(self, writer):
        """Verify DMR ID can be encoded to bytes correctly"""
        # Test default DMR ID
        dmr_bytes = writer.dmr_id_to_bytes(3107683)
        assert len(dmr_bytes) == 4
        assert all(0 <= b <= 255 for b in dmr_bytes)
        
        # Verify it can be reconstructed
        reconstructed = (dmr_bytes[0] << 24) | (dmr_bytes[1] << 16) | (dmr_bytes[2] << 8) | dmr_bytes[3]
        assert reconstructed == 3107683

    def test_channels_from_parsed_conversion(self, writer):
        """Verify conversion from parsed format to PMR-171 format"""
        parsed_channels = [
            {
                'index': 0,
                'name': 'Ch0',
                'rx_freq': 146.52,
                'tx_freq': 146.52,
                'mode': 'FM',
                'rx_ctcss': 67,
                'tx_ctcss': 67,
                'is_digital': False
            },
            {
                'index': 1,
                'name': 'Ch1',
                'rx_freq': 446.00,
                'mode': 'DMR',
                'is_digital': True
            }
        ]
        
        pmr_channels = writer.channels_from_parsed(parsed_channels)
        
        assert "0" in pmr_channels
        assert "1" in pmr_channels
        assert pmr_channels["0"]["channelName"] == "Ch0\u0000"
        assert pmr_channels["0"]["chType"] == 0  # Analog
        assert pmr_channels["0"]["rxCtcss"] == 67
        assert pmr_channels["1"]["channelName"] == "Ch1\u0000"
        assert pmr_channels["1"]["chType"] == 1  # Digital


class TestFrequencyValidation:
    """Test frequency conversion accuracy"""
    
    def test_frequency_boundary_cases(self):
        """Test frequency encoding at band edges"""
        # VHF low edge
        freq_bytes = frequency_to_bytes(136.0)
        assert bytes_to_frequency(freq_bytes) == 136.0
        
        # VHF high edge
        freq_bytes = frequency_to_bytes(174.0)
        assert bytes_to_frequency(freq_bytes) == 174.0
        
        # UHF low edge
        freq_bytes = frequency_to_bytes(400.0)
        assert bytes_to_frequency(freq_bytes) == 400.0
        
        # UHF high edge
        freq_bytes = frequency_to_bytes(520.0)
        assert bytes_to_frequency(freq_bytes) == 520.0

    def test_frequency_rounding(self):
        """Verify frequency rounding to nearest Hz"""
        # Test that floating point errors are handled
        freq_bytes = frequency_to_bytes(144.579999999)
        freq_mhz = bytes_to_frequency(freq_bytes)
        assert abs(freq_mhz - 144.580) < 0.000001

    def test_example_file_frequencies(self):
        """Verify we can decode frequencies from MODE_TEST.json"""
        # Channel 0-10, 20: 146.52 MHz (from MODE_TEST.json: 8, 187, 183, 192)
        freq_bytes = (8, 187, 183, 192)
        freq = bytes_to_frequency(freq_bytes)
        assert abs(freq - 146.52) < 0.000001
        
        # Channel 21: 446.00 MHz (from MODE_TEST.json: 26, 149, 107, 128)
        freq_bytes = (26, 149, 107, 128)
        freq = bytes_to_frequency(freq_bytes)
        assert abs(freq - 446.00) < 0.000001
        
        # Channel 22 RX: 146.94 MHz (from MODE_TEST.json: 8, 194, 32, 96)
        freq_bytes = (8, 194, 32, 96)
        freq = bytes_to_frequency(freq_bytes)
        assert abs(freq - 146.94) < 0.000001
        
        # Channel 22 TX: 146.34 MHz (from MODE_TEST.json: 8, 184, 248, 160)
        freq_bytes = (8, 184, 248, 160)
        freq = bytes_to_frequency(freq_bytes)
        assert abs(freq - 146.34) < 0.000001
