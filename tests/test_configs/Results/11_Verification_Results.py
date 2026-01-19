#!/usr/bin/env python3
"""
Test 11 CTCSS Validation - Verification Script

Compares the original test file with the readback from the radio
to verify that all CTCSS tone mappings are correct.
"""

import json
import sys

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_channel(ch_num, original, readback):
    """Compare a single channel between original and readback"""
    issues = []
    
    # Check if channel exists in readback
    if ch_num not in readback:
        return [f"Channel {ch_num} missing from readback"]
    
    orig = original[ch_num]
    read = readback[ch_num]
    
    # Compare critical CTCSS fields
    if orig['emitYayin'] != read['emitYayin']:
        issues.append(f"  TX yayin mismatch: Expected {orig['emitYayin']}, Got {read['emitYayin']}")
    
    if orig['receiveYayin'] != read['receiveYayin']:
        issues.append(f"  RX yayin mismatch: Expected {orig['receiveYayin']}, Got {read['receiveYayin']}")
    
    # Check channel name
    if orig['channelName'].rstrip('\x00') != read['channelName'].rstrip('\x00'):
        issues.append(f"  Name mismatch: Expected '{orig['channelName'].rstrip(chr(0))}', Got '{read['channelName'].rstrip(chr(0))}'")
    
    return issues

def main():
    print("=" * 80)
    print("Test 11: Complete CTCSS Validation - Verification Results")
    print("=" * 80)
    print()
    
    # Load files
    original_file = "c:/Users/aramder/Documents/GitHub/CodeplugConverter/tests/test_configs/11_complete_ctcss_validation.json"
    readback_file = "D:/Radio/Guohetec/Testing/11_complete_ctcss_validation_readback.json"
    
    print(f"Loading original:  {original_file}")
    print(f"Loading readback:  {readback_file}")
    print()
    
    original = load_json(original_file)
    readback = load_json(readback_file)
    
    # Test channel groups
    test_channels = {
        "Common Tones": [0, 1, 2, 3, 4, 5],
        "Edge Cases": [10, 11, 12, 13],
        "Mid-Range": [14, 15, 16],
        "Split Tones": [20, 21, 22],
        "TX-Only": [25, 26],
        "RX-Only": [27, 28],
        "No Tone": [30],
        "Range Tests": [35, 36, 37, 38]
    }
    
    all_passed = True
    results = {}
    
    # Verify each channel group
    for group_name, channels in test_channels.items():
        print(f"\n{group_name}:")
        print("-" * 60)
        
        group_issues = []
        for ch_num in channels:
            ch_str = str(ch_num)
            issues = compare_channel(ch_str, original, readback)
            
            if issues:
                all_passed = False
                group_issues.append((ch_num, issues))
                orig = original[ch_str]
                read = readback[ch_str]
                print(f"[FAIL] Channel {ch_num}: {orig['channelName'].rstrip(chr(0))}")
                for issue in issues:
                    print(f"   {issue}")
            else:
                orig = original[ch_str]
                tx = orig['emitYayin']
                rx = orig['receiveYayin']
                print(f"[PASS] Channel {ch_num}: {orig['channelName'].rstrip(chr(0))} (TX={tx}, RX={rx})")
        
        results[group_name] = {
            'passed': len(group_issues) == 0,
            'issues': group_issues
        }
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    total_channels = sum(len(channels) for channels in test_channels.values())
    failed_channels = sum(len(results[group]['issues']) for group in results)
    passed_channels = total_channels - failed_channels
    
    print(f"\nTotal Test Channels: {total_channels}")
    print(f"Passed: {passed_channels}")
    print(f"Failed: {failed_channels}")
    print()
    
    if all_passed:
        print("*** SUCCESS: All CTCSS tone mappings verified correctly!")
        print()
        print("Next Steps:")
        print("1. Perform functional testing on the radio")
        print("2. Verify tones display correctly in radio menu")
        print("3. Test RX tone detection (squelch opening)")
        print("4. Test TX tone generation (with tone decoder)")
        print("5. Update documentation with VALIDATED status")
        return 0
    else:
        print("*** FAILURE: Some CTCSS mappings did not match!")
        print()
        print("Action Required:")
        print("1. Review failed channels above")
        print("2. Check if radio firmware modified values")
        print("3. Verify expected vs actual yayin values")
        print("4. Update CTCSS mapping if necessary")
        return 1

if __name__ == "__main__":
    sys.exit(main())
