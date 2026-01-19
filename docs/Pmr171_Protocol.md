# PMR-171 Control Protocol V1.5

Documentation extracted from FCC filing manual: https://fcc.report/FCC-ID/2BEJV-PMR-171/7105057.pdf

## Overview

Data communication is transmitted through PMR-171 built-in sound card, which can transmit, read and write data through sound card. The control protocol data can be controlled by Bluetooth SPP, BLE, RS232, USB interface, and the protocol follows the serial port standard.

## Packet Format

```
| 0xA5 | 0xA5 | 0xA5 | 0xA5 | Length | Command | DATA... | CRC_H | CRC_L |
|------|------|------|------|--------|---------|---------|-------|-------|
| Header (4 bytes)           | 1 byte | 1 byte  | N bytes | CRC (2 bytes) |
```

### Header
Four `0xA5` bytes mark the start of every packet.

### Package Length
One byte indicating the number of bytes from the next byte (Command) to the end of the packet (including CRC bytes).

### Command Type
Single byte command identifier.

### DATA
Variable length data payload specific to each command.

### CRC
16-bit CRC verification calculated from the Package Length byte through the last DATA byte (exclusive of CRC bytes themselves).
- CRC High byte followed by CRC Low byte
- Uses CRC-16-CCITT algorithm (polynomial 0x1021, initial value 0xFFFF)

#### CRC Algorithm (from Manual, Sheet 39)
```c
unsigned int CRC16Check(unsigned char *buf, unsigned char len)
{
    unsigned char i, j;
    unsigned int uncrcReg = 0xFFFF;
    unsigned int uncur;
    for (i = 0; i < len; i++)
    {
        uncur = buf[i] << 8;
        for (j = 0; j < 8; j++)
        {
            if ((int)(uncrcReg ^ uncur) < 0)
            {
                uncrcReg = (uncrcReg << 1) ^ 0x1021;
            }
            else
            {
                uncrcReg <<= 1;
            }
            uncur <<= 1;
        }
    }
    return uncrcReg;
}
```

#### Python Implementation
```python
def crc16_ccitt(data: bytes) -> int:
    """Calculate CRC-16-CCITT for PMR-171 protocol"""
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
```

## Radio Reply Format

Standard reply format mirrors the request format with same header.

For spectrum data, the radio uses a different header:
```
| 0x7E | 0x7E | 0x7E | 0x7E | Spectrum data... |
```

V1.0 hardware: Spectral packets are 256 bytes, no headers and no checksums
V2.0 hardware: Spectrum packets 80 bytes, no headers and no verification

## Known Commands

### Command 0x07 - PTT Control
Control station PTT (Push-To-Talk) state.

APP Send:
```
| 0xA5 | 0xA5 | 0xA5 | 0xA5 | Length | 0x07 | PTT | CRC_H | CRC_L |
```
PTT values: 0=Release, 1=Press

### Command 0x0A - Mode Setting
Set operating mode.

APP Send:
```
| 0xA5 | 0xA5 | 0xA5 | 0xA5 | Length | 0x0A | Mode | CRC_H | CRC_L |
```
Mode values:
- 0: USB
- 1: LSB
- 2: CWR
- 3: CWL
- 4: AM
- 5: WFM
- 6: NFM
- 7: DIGI
- 8: PKT
- 9: DMR (added in firmware update, not in original FCC documentation)

### Command 0x0B - Status Synchronization
Request/receive full radio status.

Radio Reply includes:
- VFOA mode
- VFOB mode
- VFOA frequency
- VFOB frequency
- A/B selection
- NR/NB settings
- RXT, XIT
- Filter bandwidth
- Spectrum bandwidth
- Voltage
- UTC time
- Status bar status
- S/PO table values
- SWR/AUD/ALC
- CRC

### Command 0x27 - Equipment Type Recognition
Query device type.

### Command 0x28 - Power Class
Set power output level (0-100).

### Command 0x29 - Receive Frequency Offset (RIT)
Set RIT value (0-120).

### Command 0x39 - Spectrum Data Request
Request spectrum data from radio.

## CTCSS Tone Table

The protocol supports 56 CTCSS tones (index 0 = no tone):

| Index | Freq   | Index | Freq   | Index | Freq   | Index | Freq   |
|-------|--------|-------|--------|-------|--------|-------|--------|
| 0     | None   | 14    | 103.5  | 28    | 159.8  | 42    | 203.5  |
| 1     | 67.0   | 15    | 107.2  | 29    | 162.2  | 43    | 206.5  |
| 2     | 69.3   | 16    | 110.9  | 30    | 165.5  | 44    | 210.7  |
| 3     | 71.9   | 17    | 114.8  | 31    | 167.9  | 45    | 213.8  |
| 4     | 74.4   | 18    | 118.8  | 32    | 171.3  | 46    | 218.1  |
| 5     | 77.0   | 19    | 123.0  | 33    | 173.8  | 47    | 221.3  |
| 6     | 79.7   | 20    | 127.3  | 34    | 177.3  | 48    | 225.7  |
| 7     | 82.5   | 21    | 131.8  | 35    | 179.9  | 49    | 229.1  |
| 8     | 85.4   | 22    | 136.5  | 36    | 183.5  | 50    | 233.6  |
| 9     | 88.5   | 23    | 141.3  | 37    | 186.2  | 51    | 237.1  |
| 10    | 91.5   | 24    | 146.2  | 38    | 189.9  | 52    | 241.8  |
| 11    | 94.8   | 25    | 150.0  | 39    | 192.8  | 53    | 245.5  |
| 12    | 97.4   | 26    | 151.4  | 40    | 196.6  | 54    | 250.3  |
| 13    | 100.0  | 27    | 156.7  | 41    | 199.5  | 55    | 254.1  |

## Leading Tones (1750Hz burst)
- 0: None
- 1750: 1750 Hz burst
- 2135: 2135 Hz burst

## Bluetooth UUIDs

### V1.0 Hardware (BLE)
- Service UUID: `0000FFF0-0000-1000-8000-00805F9B34FB`
- Write features: `0000FFF2-0000-1000-8000-00805F9B34FB`
- Notification: `0000FFF1-0000-1000-8000-00805F9B34FB`

### V2.0 Hardware (BLE)
- Service UUID: `FFE0`
- Feature UUID FFE1: Serial port transmission (notify, write)
- Feature UUID FFE2: Audio Bluetooth/SD card music playback control (write)

## Channel Programming Commands (Discovered from UART Analysis)

### Command 0x40 - Channel Write
Write channel configuration to radio memory.

Packet structure (34 bytes total):
```
| A5 A5 A5 A5 | 1D | 40 | CH_H CH_L | RX_MODE TX_MODE | RX_FREQ (4B) | TX_FREQ (4B) | RX_CTCSS TX_CTCSS | ... | CRC_H CRC_L |
```

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-3    | 4    | Header | 0xA5 0xA5 0xA5 0xA5 |
| 4      | 1    | Length | 0x1D (29) - bytes from Command to end |
| 5      | 1    | Command | 0x40 (Channel Write) |
| 6-7    | 2    | Channel Index | Big-endian, 0-999 |
| 8      | 1    | RX Mode | See mode table |
| 9      | 1    | TX Mode | See mode table |
| 10-13  | 4    | RX Frequency | Big-endian Hz (e.g., 0x08BBB7C0 = 146,520,000 Hz) |
| 14-17  | 4    | TX Frequency | Big-endian Hz |
| 18     | 1    | RX CTCSS Index | See CTCSS table (0=None, 1-55=tone) |
| 19     | 1    | TX CTCSS Index | See CTCSS table (0=None, 1-55=tone) |
| 20-31  | 12   | Channel Name | Null-terminated ASCII string (max 11 chars + null) |
| 32-33  | 2    | CRC | CRC-16-CCITT (polynomial 0x1021, init 0xFFFF) |

### Command 0x41 - Channel Read
Read channel configuration from radio memory.

**Request Format:**
```
| A5 A5 A5 A5 | 05 | 41 | CH_H CH_L | CRC_H CRC_L |
```
- Just send 2-byte channel index (big-endian)
- Radio responds with full 26-byte channel data

**Response Format:**
Same as write command (0x40) - 26-byte channel data with all fields populated.

**Note:** 0x43 was previously incorrectly documented as the read command. It is actually
a write acknowledgment/echo. The correct read command is 0x41.

### Example Channel Write Packet
```
Channel 0: 146.52 MHz NFM, CTCSS 100.0 Hz, Name "100.0Hz Bot"

Full packet (34 bytes):
A5 A5 A5 A5 1D 40 00 00 06 06 08 BB B7 C0 08 BB B7 C0 0D 0D 
31 30 30 2E 30 48 7A 20 42 6F 74 00 [CRC_H] [CRC_L]

Breakdown:
- A5 A5 A5 A5: Header (4 bytes)
- 1D: Length (29 = 0x1D bytes following)
- 40: Command (Channel Write)
- 00 00: Channel 0 (big-endian)
- 06: RX Mode 6 (NFM)
- 06: TX Mode 6 (NFM)  
- 08 BB B7 C0: RX Freq 146,520,000 Hz (146.52 MHz, big-endian)
- 08 BB B7 C0: TX Freq 146,520,000 Hz (146.52 MHz, big-endian)
- 0D: RX CTCSS index 13 (100.0 Hz)
- 0D: TX CTCSS index 13 (100.0 Hz)
- 31 30 30 2E 30 48 7A 20 42 6F 74 00: Channel Name "100.0Hz Bot\0"
- [CRC_H] [CRC_L]: CRC-16-CCITT
```

### Example Channel Names from UART Capture
| Channel | Name (ASCII) | Description |
|---------|--------------|-------------|
| 0 | `100.0Hz Bot` | 100.0 Hz both RX and TX |
| 10 | `67.0Hz Both` | 67.0 Hz both RX and TX |
| 20 | `Split 100/1` | Split tones (100/131.8) |
| 25 | `TX Only 100` | TX-only CTCSS |
| 27 | `RX Only 100` | RX-only CTCSS |
| 30 | `No Tone` | No CTCSS |

## CTCSS Index to Frequency Mapping (Verified from UART Captures)

| Index | Frequency | Index | Frequency | Index | Frequency |
|-------|-----------|-------|-----------|-------|-----------|
| 0     | None      | 19    | 123.0 Hz  | 37    | 186.2 Hz  |
| 1     | 67.0 Hz   | 20    | 127.3 Hz  | 38    | 189.9 Hz  |
| 2     | 69.3 Hz   | 21    | 131.8 Hz  | 39    | 192.8 Hz  |
| 13    | 100.0 Hz  | 24    | 146.2 Hz  | 46    | 218.1 Hz  |
| 15    | 107.2 Hz  | 27    | 156.7 Hz  | 49    | 229.1 Hz  |
| ...   | ...       | 29    | 162.2 Hz  | 54    | 250.3 Hz  |
|       |           |       |           | 55    | 254.1 Hz  |

## DMR Channel Configuration

DMR (Digital Mobile Radio) channels use Mode 9 and have additional fields beyond analog channels:

### DMR-Specific Fields

| Field | Description |
|-------|-------------|
| `chType` | Channel type: 0 = Analog, 1 = Digital (DMR) |
| `callId1-4` | Talkgroup ID (big-endian 32-bit) |
| `ownId1-4` | DMR Radio ID (big-endian 32-bit) |
| `rxCc` | RX Color Code (0-15) |
| `txCc` | TX Color Code (0-15) |
| `slot` | Timeslot: 1 or 2 |
| `callFormat` | Call format (group/private) |

### DMR Channel Example (from SAMPLE_CHANNELS.json)

```json
{
    "channelLow": 50,
    "channelName": "DMR TG91 WW",
    "vfoaMode": 9,
    "chType": 1,
    "callId4": 91,          // Talkgroup 91 (Worldwide)
    "ownId2": 57, "ownId3": 67, "ownId4": 117,  // DMR Radio ID
    "rxCc": 1, "txCc": 1,   // Color Code 1
    "slot": 1               // Timeslot 1
}
```

### Notes on DMR Support
- Mode 9 (DMR) was added in a firmware update after the original FCC filing
- The original FCC documentation (v1.5) only lists modes 0-8
- DMR channels require `chType: 1` to enable digital-specific features
- CTCSS tones are typically not used with DMR (`rxCtcss: 0, txCtcss: 0`)

## Notes

1. Channel Write (0x40) and Channel Read (0x43) commands send 1000 channels
2. Each channel packet is 34 bytes (4 header + 1 length + 29 data)
3. Frequencies are stored as big-endian 32-bit integers in Hz
4. CTCSS tones use an index into the standard 56-tone table (0=None, 1-55=tone)
5. Mode 6 = NFM (Narrowband FM), Mode 9 = DMR (Digital), Mode 255 = unused/empty channel
6. Channel name is 12 bytes, null-terminated ASCII (max 11 visible chars)
7. CRC-16-CCITT verified: 100% of 6032 packets pass CRC validation
8. DMR mode (9) added in firmware update, not in original FCC documentation

## References

- FCC Filing: https://fcc.report/FCC-ID/2BEJV-PMR-171/7105057.pdf
- User Manual V1.0
