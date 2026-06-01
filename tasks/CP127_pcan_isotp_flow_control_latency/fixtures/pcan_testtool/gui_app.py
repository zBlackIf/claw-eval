"""GUI application for PCAN diagnostic test tool.

Provides a Qt-based interface for CAN bus communication,
UDS diagnostics, and ISO-TP message display.
"""
from __future__ import annotations

import sys
import time
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QComboBox,
    QTextEdit, QGroupBox, QSpinBox, QCheckBox, QTabWidget, QHeaderView,
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

from src.pcan_driver import PcanDriver, PCAN_USBBUS1
from src.isotp import IsoTpLayer


class DiagTestTool(QMainWindow):
    """Main application window for PCAN diagnostic test tool."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIAT TestTool - PCAN Diagnostic")
        self.setMinimumSize(1200, 800)

        self.pcan = PcanDriver(channel=PCAN_USBBUS1, is_fd=False)
        self.isotp = IsoTpLayer(
            can_driver=self.pcan,
            tx_id=0x7E0,
            rx_id=0x7E8,
            block_size=0,
            stmin=0,
            on_message_complete=self._on_isotp_message,
        )

        # Wire up message callback: pcan -> isotp
        self.pcan.set_on_message(self.isotp.process_can_message)

        self._messages: deque = deque(maxlen=1000)
        self._display_index = 0

        self._setup_ui()
        self._setup_timers()

    def _setup_ui(self):
        """Build the GUI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Connection controls
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["PCAN_USBBUS1", "PCAN_USBBUS2"])
        conn_layout.addWidget(QLabel("Channel:"))
        conn_layout.addWidget(self.channel_combo)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["500 kbit/s", "250 kbit/s", "1 Mbit/s"])
        conn_layout.addWidget(QLabel("Baudrate:"))
        conn_layout.addWidget(self.baud_combo)

        self.fd_check = QCheckBox("CAN-FD")
        conn_layout.addWidget(self.fd_check)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect)
        conn_layout.addWidget(self.connect_btn)

        conn_layout.addStretch()
        self.status_label = QLabel("Disconnected")
        conn_layout.addWidget(self.status_label)

        layout.addWidget(conn_group)

        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Message monitor tab
        msg_widget = QWidget()
        msg_layout = QVBoxLayout(msg_widget)
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(6)
        self.message_table.setHorizontalHeaderLabels(
            ["Time", "Direction", "ID", "DLC", "Data", "Type"]
        )
        self.message_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        msg_layout.addWidget(self.message_table)

        # Stats bar
        stats_layout = QHBoxLayout()
        self.tx_label = QLabel("TX: 0")
        self.rx_label = QLabel("RX: 0")
        self.buf_label = QLabel("Buffer: 0")
        stats_layout.addWidget(self.tx_label)
        stats_layout.addWidget(self.rx_label)
        stats_layout.addWidget(self.buf_label)
        stats_layout.addStretch()
        msg_layout.addLayout(stats_layout)

        tabs.addTab(msg_widget, "Messages")

        # UDS diagnostic tab
        uds_widget = QWidget()
        uds_layout = QVBoxLayout(uds_widget)

        req_layout = QHBoxLayout()
        req_layout.addWidget(QLabel("Request ID:"))
        self.req_id_spin = QSpinBox()
        self.req_id_spin.setRange(0, 0x7FF)
        self.req_id_spin.setValue(0x7E0)
        self.req_id_spin.setDisplayIntegerBase(16)
        req_layout.addWidget(self.req_id_spin)

        req_layout.addWidget(QLabel("Response ID:"))
        self.resp_id_spin = QSpinBox()
        self.resp_id_spin.setRange(0, 0x7FF)
        self.resp_id_spin.setValue(0x7E8)
        self.resp_id_spin.setDisplayIntegerBase(16)
        req_layout.addWidget(self.resp_id_spin)
        uds_layout.addLayout(req_layout)

        self.uds_input = QTextEdit()
        self.uds_input.setMaximumHeight(60)
        self.uds_input.setPlaceholderText("Enter UDS request hex (e.g., 10 01)")
        uds_layout.addWidget(self.uds_input)

        self.send_btn = QPushButton("Send UDS Request")
        self.send_btn.clicked.connect(self._on_send_uds)
        uds_layout.addWidget(self.send_btn)

        self.uds_log = QTextEdit()
        self.uds_log.setReadOnly(True)
        self.uds_log.setFont(QFont("Courier", 9))
        uds_layout.addWidget(self.uds_log)

        tabs.addTab(uds_widget, "UDS Diagnostic")

    def _setup_timers(self):
        """Set up periodic GUI update timers."""
        # Display refresh timer - updates message table
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self._display_messages)
        self.display_timer.start(5)  # 5ms refresh

        # Stats update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(500)

    def _on_connect(self):
        """Handle connect/disconnect button."""
        if self.pcan._run:
            self.pcan.stop()
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
        else:
            if self.pcan.initialize():
                self.pcan.start()
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
            else:
                self.status_label.setText("Connection failed!")

    def _on_send_uds(self):
        """Send UDS diagnostic request."""
        hex_text = self.uds_input.toPlainText().strip()
        try:
            data = bytes.fromhex(hex_text.replace(" ", ""))
        except ValueError:
            self.uds_log.append("[ERROR] Invalid hex input")
            return

        self.isotp.tx_id = self.req_id_spin.value()
        self.isotp.rx_id = self.resp_id_spin.value()

        success = self.isotp.send_message(data)
        if success:
            self.uds_log.append(f"[TX] {data.hex(' ').upper()}")
        else:
            self.uds_log.append("[ERROR] Send failed")

    def _on_isotp_message(self, payload: bytes):
        """Callback when ISO-TP reassembly completes."""
        self.uds_log.append(f"[RX] {payload.hex(' ').upper()}")

    def _display_messages(self):
        """Update message table with received CAN frames.

        Called every 5ms by display_timer.
        NOTE: This implementation clears and rebuilds the entire table
        each time, which becomes a performance bottleneck as message
        count grows.
        """
        messages_to_show = list(self.pcan.buffer)[-1000:]

        # Clear and rebuild entire table each refresh
        self.message_table.setRowCount(0)
        self.message_table.setRowCount(len(messages_to_show))

        for row, msg in enumerate(messages_to_show):
            self.message_table.setItem(row, 0, QTableWidgetItem(f"{msg['timestamp']:.3f}"))
            self.message_table.setItem(row, 1, QTableWidgetItem("RX"))
            self.message_table.setItem(row, 2, QTableWidgetItem(f"0x{msg['id']:03X}"))
            self.message_table.setItem(row, 3, QTableWidgetItem(str(msg['dlc'])))
            self.message_table.setItem(row, 4, QTableWidgetItem(msg['data'].hex(' ').upper()))
            self.message_table.setItem(row, 5, QTableWidgetItem("FD" if msg['is_fd'] else "STD"))

        self.message_table.scrollToBottom()

    def _update_stats(self):
        """Update statistics labels."""
        self.tx_label.setText(f"TX: {self.pcan.tx_count}")
        self.rx_label.setText(f"RX: {self.pcan.rx_count}")
        self.buf_label.setText(f"Buffer: {self.pcan.buffer_size}")


def main():
    app = QApplication(sys.argv)
    window = DiagTestTool()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
