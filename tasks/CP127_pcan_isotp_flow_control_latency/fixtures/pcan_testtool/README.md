# PCAN Diagnostic Test Tool

## Overview
CAN bus diagnostic tool using Peak PCAN USB adapter.
Supports UDS (Unified Diagnostic Services) over ISO-TP (ISO 15765-2).

## Architecture
```
gui_app.py          - PyQt5 main application
src/
  pcan_driver.py    - PCAN-Basic API ctypes wrapper
  isotp.py          - ISO-TP transport layer
```

## Known Issue
When ECU sends a multi-frame response (First Frame), the tool takes
~100-150ms to reply with the Flow Control frame. This causes ECU
timeouts on some vehicles that expect FC within 50ms (N_BS timeout
per ISO 15765-2).

The latency seems to come from the reception loop in pcan_driver.py
which uses `time.sleep(0.1)` when no message is available, plus the
display_messages() in gui_app.py that rebuilds the entire QTableWidget
every 5ms.

## Requirements
- Python 3.8+
- PyQt5
- Peak PCAN USB adapter + PCANBasic.dll
- Windows OS (uses Windows-specific ctypes calls)
