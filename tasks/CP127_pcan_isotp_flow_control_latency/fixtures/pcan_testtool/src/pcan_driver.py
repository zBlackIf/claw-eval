"""PCAN USB driver wrapper for CAN/CAN-FD communication.

Uses the PCAN-Basic API via ctypes to interface with Peak CAN hardware.
Provides thread-safe message buffering and callback-based reception.
"""
from __future__ import annotations

import ctypes
import threading
import time
from collections import deque
from ctypes import c_int, c_ubyte, c_uint, c_ulong, c_ushort, Structure, POINTER, byref
from typing import Callable, Optional


# PCAN-Basic API constants
PCAN_USBBUS1 = 0x51
PCAN_BAUD_500K = 0x001C
PCAN_TYPE_ISA = 0x01
PCAN_ERROR_OK = 0x00000
PCAN_ERROR_QRCVEMPTY = 0x00020
PCAN_RECEIVE_EVENT = 0x03

# FD Bitrate strings
PCAN_FD_BITRATE_500K_2M = (
    b"f_clock_mhz=80, nom_brp=10, nom_tseg1=12, nom_tseg2=3, nom_sjw=1, "
    b"data_brp=4, data_tseg1=7, data_tseg2=2, data_sjw=1"
)


class TPCANMsg(Structure):
    _fields_ = [
        ("ID", c_uint),
        ("MSGTYPE", c_ubyte),
        ("LEN", c_ubyte),
        ("DATA", c_ubyte * 8),
    ]


class TPCANTimestamp(Structure):
    _fields_ = [
        ("millis", c_uint),
        ("millis_overflow", c_ushort),
        ("micros", c_ushort),
    ]


class TPCANMsgFD(Structure):
    _fields_ = [
        ("ID", c_uint),
        ("MSGTYPE", c_ubyte),
        ("DLC", c_ubyte),
        ("DATA", c_ubyte * 64),
    ]


class TPCANTimestampFD(Structure):
    _fields_ = [("value", c_ulong)]


class PcanDriver:
    """PCAN USB driver with threaded reception loop.

    Attributes:
        channel: PCAN channel handle (default PCAN_USBBUS1)
        is_fd: Whether CAN-FD mode is enabled
        buffer: Thread-safe deque of received messages
    """

    def __init__(self, channel: int = PCAN_USBBUS1, is_fd: bool = False):
        self.channel = channel
        self.is_fd = is_fd
        self._run = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.buffer: deque = deque(maxlen=2000)
        self._tx: int = 0
        self._rx: int = 0
        self._pcan = ctypes.windll.LoadLibrary("PCANBasic")
        self._on_message: Optional[Callable] = None

    @property
    def tx_count(self) -> int:
        return self._tx

    @property
    def rx_count(self) -> int:
        return self._rx

    @property
    def buffer_size(self) -> int:
        return len(self.buffer)

    def set_on_message(self, callback: Callable):
        """Register callback invoked for each received message."""
        self._on_message = callback

    def initialize(self) -> bool:
        """Initialize PCAN channel. Returns True on success."""
        if self.is_fd:
            result = self._pcan.CAN_InitializeFD(c_ushort(self.channel), PCAN_FD_BITRATE_500K_2M)
        else:
            result = self._pcan.CAN_Initialize(
                c_ushort(self.channel), c_ushort(PCAN_BAUD_500K), c_ubyte(0), c_uint(0), c_ushort(0)
            )
        return result == PCAN_ERROR_OK

    def start(self):
        """Start the background reception thread."""
        if self._run:
            return
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop reception and uninitialize."""
        self._run = False
        if self._thread:
            self._thread.join(timeout=2)
        self._pcan.CAN_Uninitialize(c_ushort(self.channel))

    def _loop(self):
        """Main reception loop - polls PCAN hardware for messages."""
        while self._run:
            with self._lock:
                if self.is_fd:
                    msg = TPCANMsgFD()
                    ts = TPCANTimestampFD()
                    result = self._pcan.CAN_ReadFD(
                        c_ushort(self.channel), byref(msg), byref(ts)
                    )
                else:
                    msg = TPCANMsg()
                    ts = TPCANTimestamp()
                    result = self._pcan.CAN_Read(
                        c_ushort(self.channel), byref(msg), byref(ts)
                    )

            if result == PCAN_ERROR_OK:
                data = bytes(msg.DATA[: msg.LEN if not self.is_fd else self._dlc_to_len(msg.DLC)])
                parsed = {
                    "id": msg.ID,
                    "dlc": msg.DLC if self.is_fd else msg.LEN,
                    "data": data,
                    "timestamp": ts.value if self.is_fd else (ts.millis + ts.millis_overflow * 0x100000000) * 1000 + ts.micros,
                    "is_fd": self.is_fd,
                    "is_brs": bool(msg.MSGTYPE & 0x04) if self.is_fd else False,
                    "data_len": len(data),
                    "recv_time": time.time(),
                }
                self.buffer.append(parsed)
                self._rx += 1
                if self._on_message:
                    self._on_message(parsed)
            elif result == PCAN_ERROR_QRCVEMPTY:
                # No message available - sleep and retry
                time.sleep(0.1)
            else:
                time.sleep(0.1)

    def send(self, can_id: int, data: bytes, is_fd: bool = False, bitrate_switch: bool = False) -> bool:
        """Send a CAN message.

        Args:
            can_id: CAN arbitration ID
            data: Payload bytes
            is_fd: Use CAN-FD frame format
            bitrate_switch: Enable bitrate switching for data phase

        Returns:
            True if message was sent successfully
        """
        if is_fd or self.is_fd:
            msg = TPCANMsgFD()
            msg.ID = c_uint(can_id)
            msg.MSGTYPE = c_ubyte(0x04 if bitrate_switch else 0x00)
            msg.DLC = c_ubyte(self._len_to_dlc(len(data)))
            for i, b in enumerate(data):
                msg.DATA[i] = b
            result = self._pcan.CAN_WriteFD(c_ushort(self.channel), byref(msg))
        else:
            msg = TPCANMsg()
            msg.ID = c_uint(can_id)
            msg.MSGTYPE = c_ubyte(0x00)
            msg.LEN = c_ubyte(len(data))
            for i, b in enumerate(data):
                msg.DATA[i] = b
            result = self._pcan.CAN_Write(c_ushort(self.channel), byref(msg))

        if result == PCAN_ERROR_OK:
            self._tx += 1
            return True
        return False

    @staticmethod
    def _dlc_to_len(dlc: int) -> int:
        """Convert CAN-FD DLC code to actual data length."""
        table = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7,
                 8: 8, 9: 12, 10: 16, 11: 20, 12: 24, 13: 32, 14: 48, 15: 64}
        return table.get(dlc, 8)

    @staticmethod
    def _len_to_dlc(length: int) -> int:
        """Convert data length to CAN-FD DLC code."""
        if length <= 8:
            return length
        for dlc, l in [(9, 12), (10, 16), (11, 20), (12, 24), (13, 32), (14, 48), (15, 64)]:
            if length <= l:
                return dlc
        return 15
