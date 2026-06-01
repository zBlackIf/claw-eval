"""ISO-TP (ISO 15765-2) transport layer implementation.

Handles segmentation and reassembly of messages longer than 8 bytes
over CAN bus. Implements Single Frame, First Frame, Consecutive Frame,
and Flow Control frame types.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional


# ISO-TP frame type nibbles (upper 4 bits of first byte)
FRAME_TYPE_SF = 0x0  # Single Frame
FRAME_TYPE_FF = 0x1  # First Frame
FRAME_TYPE_CF = 0x2  # Consecutive Frame
FRAME_TYPE_FC = 0x3  # Flow Control

# Flow Control Flow Status
FC_STATUS_CTS = 0    # Continue To Send
FC_STATUS_WAIT = 1   # Wait
FC_STATUS_OVERFLOW = 2  # Overflow

# Default parameters
DEFAULT_BS = 0       # Block Size (0 = no limit)
DEFAULT_STMIN = 0    # Separation Time minimum (ms)
DEFAULT_TIMEOUT = 1.0  # seconds


class IsoTpLayer:
    """ISO-TP transport protocol layer.

    Handles segmentation of long messages and reassembly of received
    multi-frame transmissions.

    Args:
        can_driver: PcanDriver instance for sending/receiving
        tx_id: CAN arbitration ID for transmitted frames
        rx_id: CAN arbitration ID for received frames (responses)
        block_size: Flow Control Block Size parameter
        stmin: Flow Control STmin parameter (ms)
        on_message_complete: Callback when a complete message is reassembled
    """

    def __init__(
        self,
        can_driver,
        tx_id: int = 0x7E0,
        rx_id: int = 0x7E8,
        block_size: int = DEFAULT_BS,
        stmin: int = DEFAULT_STMIN,
        on_message_complete: Optional[Callable] = None,
    ):
        self.can_driver = can_driver
        self.tx_id = tx_id
        self.rx_id = rx_id
        self.block_size = block_size
        self.stmin = stmin
        self.on_message_complete = on_message_complete

        # Reception state
        self._rx_buffer = bytearray()
        self._rx_expected_length = 0
        self._rx_sequence = 0
        self._rx_active = False

        # Transmission state
        self._tx_buffer = bytearray()
        self._tx_offset = 0
        self._tx_sequence = 0
        self._tx_active = False
        self._tx_bs_remaining = 0
        self._fc_received = threading.Event()

        self._lock = threading.Lock()
        self._pending_messages: deque = deque()

    def process_can_message(self, msg: dict):
        """Process an incoming CAN message through the ISO-TP state machine.

        This method is called by the CAN driver's on_message callback.
        It identifies the frame type and dispatches to the appropriate handler.
        """
        if msg["id"] != self.rx_id:
            return

        data = msg["data"]
        if not data:
            return

        frame_type = (data[0] >> 4) & 0x0F

        if frame_type == FRAME_TYPE_SF:
            self._handle_single_frame(data)
        elif frame_type == FRAME_TYPE_FF:
            self._handle_first_frame(data, msg)
        elif frame_type == FRAME_TYPE_CF:
            self._handle_consecutive_frame(data)
        elif frame_type == FRAME_TYPE_FC:
            self._handle_flow_control(data)

    def _handle_single_frame(self, data: bytes):
        """Handle a Single Frame (complete message in one CAN frame)."""
        length = data[0] & 0x0F
        if length == 0 and len(data) > 2:
            # Extended addressing: length in second byte
            length = data[1]
            payload = data[2:2 + length]
        else:
            payload = data[1:1 + length]
        self._deliver_message(bytes(payload))

    def _handle_first_frame(self, data: bytes, msg: dict):
        """Handle a First Frame (start of multi-frame message).

        Upon receiving a FF, we must send a Flow Control frame to tell
        the sender our reception parameters (BS, STmin).
        """
        # Parse message length from FF
        length = ((data[0] & 0x0F) << 8) | data[1]
        if length == 0 and len(data) >= 6:
            # Extended length (>4095 bytes)
            length = int.from_bytes(data[2:6], "big")
            payload = data[6:]
        else:
            payload = data[2:]

        with self._lock:
            self._rx_buffer = bytearray(payload)
            self._rx_expected_length = length
            self._rx_sequence = 1
            self._rx_active = True

        # Send Flow Control frame to allow sender to continue
        self._send_flow_control()

    def _handle_consecutive_frame(self, data: bytes):
        """Handle a Consecutive Frame (continuation of multi-frame message)."""
        seq = data[0] & 0x0F
        with self._lock:
            if not self._rx_active:
                return
            if seq != (self._rx_sequence & 0x0F):
                # Sequence error - abort
                self._rx_active = False
                return

            self._rx_buffer.extend(data[1:])
            self._rx_sequence += 1

            if len(self._rx_buffer) >= self._rx_expected_length:
                payload = bytes(self._rx_buffer[: self._rx_expected_length])
                self._rx_active = False
                self._deliver_message(payload)

    def _handle_flow_control(self, data: bytes):
        """Handle an incoming Flow Control frame (response to our FF)."""
        flow_status = data[0] & 0x0F
        if flow_status == FC_STATUS_CTS:
            bs = data[1] if len(data) > 1 else 0
            stmin = data[2] if len(data) > 2 else 0
            self._tx_bs_remaining = bs if bs > 0 else 0xFFFF
            self._fc_received.set()
        elif flow_status == FC_STATUS_WAIT:
            pass  # Wait for next FC
        elif flow_status == FC_STATUS_OVERFLOW:
            self._tx_active = False

    def _send_flow_control(self):
        """Send a Flow Control frame to the remote sender.

        This tells the sender: Continue To Send, with our block size and STmin.
        """
        fc_data = bytes([
            (FRAME_TYPE_FC << 4) | FC_STATUS_CTS,
            self.block_size,
            self.stmin,
            0x00, 0x00, 0x00, 0x00, 0x00,
        ])
        self.can_driver.send(self.tx_id, fc_data)

    def _deliver_message(self, payload: bytes):
        """Deliver a complete reassembled message to the application layer."""
        self._pending_messages.append(payload)
        if self.on_message_complete:
            self.on_message_complete(payload)

    def send_message(self, payload: bytes, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """Send a message using ISO-TP segmentation.

        If the message fits in a Single Frame (<=7 bytes), sends immediately.
        Otherwise, sends a First Frame and waits for Flow Control before
        sending Consecutive Frames.

        Args:
            payload: The message bytes to send
            timeout: Maximum time to wait for Flow Control response

        Returns:
            True if message was sent successfully
        """
        if len(payload) <= 7:
            return self._send_single_frame(payload)
        else:
            return self._send_multi_frame(payload, timeout)

    def _send_single_frame(self, payload: bytes) -> bool:
        """Send message as a Single Frame."""
        frame = bytearray(8)
        frame[0] = (FRAME_TYPE_SF << 4) | len(payload)
        frame[1:1 + len(payload)] = payload
        return self.can_driver.send(self.tx_id, bytes(frame))

    def _send_multi_frame(self, payload: bytes, timeout: float) -> bool:
        """Send message as First Frame + Consecutive Frames."""
        self._tx_buffer = bytearray(payload)
        self._tx_offset = 6
        self._tx_sequence = 1
        self._tx_active = True
        self._fc_received.clear()

        # Send First Frame
        ff = bytearray(8)
        ff[0] = (FRAME_TYPE_FF << 4) | ((len(payload) >> 8) & 0x0F)
        ff[1] = len(payload) & 0xFF
        ff[2:8] = payload[:6]
        if not self.can_driver.send(self.tx_id, bytes(ff)):
            return False

        # Wait for Flow Control
        if not self._fc_received.wait(timeout):
            self._tx_active = False
            return False

        # Send Consecutive Frames
        while self._tx_offset < len(self._tx_buffer) and self._tx_active:
            cf = bytearray(8)
            cf[0] = (FRAME_TYPE_CF << 4) | (self._tx_sequence & 0x0F)
            end = min(self._tx_offset + 7, len(self._tx_buffer))
            cf[1:1 + (end - self._tx_offset)] = self._tx_buffer[self._tx_offset:end]
            if not self.can_driver.send(self.tx_id, bytes(cf)):
                return False
            self._tx_offset = end
            self._tx_sequence += 1

            if self.stmin > 0:
                time.sleep(self.stmin / 1000.0)

            self._tx_bs_remaining -= 1
            if self._tx_bs_remaining == 0 and self._tx_offset < len(self._tx_buffer):
                self._fc_received.clear()
                if not self._fc_received.wait(timeout):
                    self._tx_active = False
                    return False

        self._tx_active = False
        return True

    def get_pending(self) -> Optional[bytes]:
        """Get next pending received message, or None."""
        try:
            return self._pending_messages.popleft()
        except IndexError:
            return None
