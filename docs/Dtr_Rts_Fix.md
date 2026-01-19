# PMR-171 DTR/RTS Connection Fix

**Date:** January 18, 2026  
**Issue:** Radio not responding to serial commands  
**Resolution:** DTR and RTS signals must be set HIGH for radio to enter programming mode

## Problem Description

When attempting to read from or write to the PMR-171 radio via the GUI application, the software would:
1. Open the serial port successfully
2. Send commands to the radio
3. Receive no response (timeout errors)
4. Display "0 channels read" or freeze with "Not Responding"

## Debugging Journey

### Step 1: Initial Analysis

Created `tests/test_radio_read.py` to test serial communication independently from the GUI.

**Result:** "No response received (timeout)" - the radio was not responding to any commands.

### Step 2: Test Multiple Baud Rates

Created `tests/test_radio_init.py` to try different baud rates (9600, 19200, 38400, 57600, 115200, 230400, 460800) and various initialization commands (Equipment Type 0x27, Status Sync 0x0B, etc.).

**Result:** No response at any baud rate or with any command.

### Step 3: Analyze UART Captures

Analyzed existing UART captures from the manufacturer software (`tests/test_configs/Results/*.spm`):

1. **Finding 1:** The captures showed NO initialization commands at all - the manufacturer software jumped straight to Channel Write (0x40) or Channel Read (0x43) commands.

2. **Finding 2:** The pre-packet data in .spm files was just Eltima Serial Monitor metadata, not serial data.

**Conclusion:** The connection must be handled through hardware signals, not protocol commands.

### Step 4: Test DTR/RTS Signals

Created `tests/test_dtr_rts.py` to try various DTR/RTS combinations.

**Discovery:** The user heard **relay clicking** from the radio when DTR/RTS signals were toggled! This confirmed that hardware control signals do reach the radio.

### Step 5: Identify Working Configuration

Created `tests/test_quick.py` with shorter timeouts to quickly test combinations:

```python
# Test results:
# DTR=True, RTS=True  -> SUCCESS! Radio responds!
# DTR=True, RTS=False -> No response
# DTR=False, RTS=True -> No response
# DTR=False, RTS=False -> No response
```

**Root Cause:** The PMR-171 radio requires **both DTR and RTS signals to be HIGH** before it will respond to serial commands. This is likely a hardware interlock to prevent accidental programming.

## The Fix

Modified `pmr_171_cps/radio/pmr171_uart.py` in the `connect()` method:

```python
def connect(self) -> None:
    """
    Open serial connection to radio.
    
    The PMR-171 requires DTR and RTS to be set high to enter programming mode.
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
            write_timeout=None,
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
```

## Key Points

1. **DTR (Data Terminal Ready):** Must be set to `True`
2. **RTS (Request To Send):** Must be set to `True`
3. **Timing:** A brief delay (0.3s) after setting signals helps ensure stable connection
4. **rtscts=False:** Hardware flow control must be disabled to manually control RTS
5. **dsrdtr=False:** DSR/DTR flow control must be disabled to manually control DTR

## Why This Works

Many radios use DTR/RTS signals as a hardware interlock:
- **DTR HIGH:** Signals that a terminal (computer) is ready
- **RTS HIGH:** Requests permission to send data

The PMR-171 likely checks both signals before enabling its UART receiver, preventing accidental programming from noise or misconfigured software.

## Test Files Created

During debugging, these test files were created in `tests/`:

| File | Purpose |
|------|---------|
| `test_radio_read.py` | Comprehensive serial communication test |
| `test_radio_init.py` | Test various initialization sequences |
| `test_dtr_rts.py` | Test all DTR/RTS combinations |
| `test_dtr_click.py` | Focused DTR/RTS toggle testing |
| `test_quick.py` | Fast test with short timeouts |
| `analyze_connection_sequence.py` | Analyze UART captures for init commands |
| `analyze_raw_start.py` | Analyze pre-packet data in .spm files |

## Verification

After applying the fix:

```
============================================================
STEP 3: Testing PMR171Radio Class on COM3
============================================================
  Connecting...
    Connected: True

  Attempting to read channel 0...
    SUCCESS! Read in 0.001s
    Ch0: 0.0000 MHz (USB) RX=None, TX=None, Name=''
```

The radio now responds to commands with ~1ms latency per channel.

## Lessons Learned

1. **Check hardware signals first:** When serial communication fails completely, hardware control lines (DTR, RTS, CTS, DSR) are often the cause.

2. **Listen for physical feedback:** The relay clicking sound was the key clue that pointed to DTR/RTS being the issue.

3. **UART captures may not show everything:** Serial monitor captures typically don't include hardware signal state changes.

4. **Power cycling helps:** After multiple test attempts, power cycling the radio ensured a clean state for testing.

## Additional Fix: Buffer Synchronization

After the DTR/RTS fix enabled communication, an additional issue was discovered:
- First ~40 channels would read as empty
- Later channels read correctly

**Root cause:** Stale data in serial input buffer from previous operations was mixing with new responses.

**Fix:** Clear input buffer before each packet send:

```python
def _send_packet(self, packet: bytes) -> None:
    # CRITICAL: Clear input buffer before sending to avoid stale data
    self._serial.reset_input_buffer()
    
    self._serial.write(packet)
    self._serial.flush()
```

## Related Documentation

- [PMR171_PROTOCOL.md](PMR171_PROTOCOL.md) - Protocol specification
- [TESTING_FINDINGS.md](../tests/test_configs/Results/TESTING_FINDINGS.md) - CTCSS/DCS testing results
