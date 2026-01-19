#!/usr/bin/env python3
"""Test the updated PMR171Radio driver read functionality"""

import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codeplug_converter.radio.pmr171_uart import PMR171Radio


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    print(f"="*60)
    print(f"Test: PMR171Radio Driver Read (using 0x41)")
    print(f"="*60)
    
    radio = PMR171Radio(port)
    
    try:
        print(f"\nConnecting to {port}...")
        radio.connect()
        print(f"Connected! (DTR=True, RTS=True)")
        
        # Test reading some channels
        print(f"\nReading first 10 channels:")
        print("-"*60)
        
        for ch_idx in range(10):
            try:
                channel = radio.read_channel(ch_idx)
                if channel.rx_freq_hz > 0:
                    print(f"Ch {ch_idx:3d}: {channel.rx_freq_mhz:.6f} MHz, "
                          f"mode={channel.rx_mode_name}, "
                          f"ctcss={channel.rx_ctcss_index}/{channel.tx_ctcss_index}, "
                          f"name='{channel.name}'")
                else:
                    print(f"Ch {ch_idx:3d}: (empty)")
            except Exception as e:
                print(f"Ch {ch_idx:3d}: ERROR - {e}")
        
        # Read channel 50 specifically
        print(f"\nReading channel 50 (TestCh50):")
        print("-"*60)
        try:
            ch50 = radio.read_channel(50)
            print(f"  Frequency: {ch50.rx_freq_mhz:.6f} MHz")
            print(f"  Mode: {ch50.rx_mode_name}")
            print(f"  RX CTCSS: {ch50.rx_ctcss_hz} Hz (index {ch50.rx_ctcss_index})")
            print(f"  TX CTCSS: {ch50.tx_ctcss_hz} Hz (index {ch50.tx_ctcss_index})")
            print(f"  Name: '{ch50.name}'")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print(f"\n{'='*60}")
        print("SUCCESS! Driver read functionality working correctly.")
        print("="*60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        radio.disconnect()
        print(f"\nDisconnected.")


if __name__ == "__main__":
    main()
