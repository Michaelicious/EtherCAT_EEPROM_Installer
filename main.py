import os
import sys
from time import sleep
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QFileDialog, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QPixmap

from ec_install_eeprom import (
    EEPROM_SIZE,
    read_eeprom_bin_file,
    read_eeprom_data,
    setup_ethercat,
    write_eeprom_data,
)

VERSION = "v1.6"

APP_ICON = "stxi_ethercat_logo.png"
STXI_LOGO = "STXI_logo_2021.png"


def resource_path(name: str) -> str:
    """Resolve a bundled resource path for both source and PyInstaller runs."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

_NO_SLAVE_HINT = (
    "  • Verify the slave device is powered and connected.\n"
    "  • Confirm NPCAP is installed in API-Compatible Mode.\n"
    "  • Use a real-time capable network card (Intel recommended)."
)


DIFF_COLOR = "#ffa726"   # orange used to mark BIN-vs-device byte differences


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_hex_html(data, diff: "set[int] | frozenset[int]" = frozenset()) -> str:
    """Render `data` as an HTML hex dump; byte indices in `diff` are shown in orange."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_cells, asc_cells = [], []
        for j in range(16):
            gi = i + j
            if j < len(chunk):
                b = chunk[j]
                hx = f"{b:02X}"
                ch = _esc(chr(b) if 32 <= b <= 126 else ".")
                if gi in diff:
                    hx = f'<span style="color:{DIFF_COLOR};font-weight:bold">{hx}</span>'
                    ch = f'<span style="color:{DIFF_COLOR};font-weight:bold">{ch}</span>'
            else:
                hx, ch = "  ", " "   # padding so the ASCII column stays aligned
            hex_cells.append(hx)
            asc_cells.append(ch)
        lines.append(f"{i:08X}  {'  '.join(hex_cells)}  {''.join(asc_cells)}")
    body = "\n".join(lines)
    return (
        '<pre style="margin:0;font-family:Consolas,monospace;'
        f'font-size:11px;color:#c8c8c8">{body}</pre>'
    )


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class ReadWorker(QThread):
    log = pyqtSignal(str)
    data_ready = pyqtSignal(object)   # bytearray
    finished = pyqtSignal(bool)

    def run(self):
        try:
            self.log.emit("Connecting to EtherCAT network…")
            master = setup_ethercat()
            if not master:
                self.log.emit(f"ERROR: No EtherCAT slave found.\n{_NO_SLAVE_HINT}")
                self.finished.emit(False)
                return
            slave = master.slaves[-1]
            self.log.emit(f"Connected — {len(master.slaves)} slave(s) detected. Reading EEPROM…")
            data = read_eeprom_data(slave, eeprom_size=EEPROM_SIZE)
            self.log.emit(f"SUCCESS: Device EEPROM read complete ({len(data)} bytes).")
            self.data_ready.emit(data)
            self.finished.emit(True)
        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            self.finished.emit(False)


class WriteWorker(QThread):
    log = pyqtSignal(str)
    device_data_ready = pyqtSignal(object)   # bytearray
    finished = pyqtSignal(bool)

    def __init__(self, bin_data: bytes):
        super().__init__()
        self.bin_data = bin_data

    def run(self):
        try:
            self.log.emit("Connecting to EtherCAT network…")
            master = setup_ethercat()
            if not master:
                self.log.emit(f"ERROR: No EtherCAT slave found.\n{_NO_SLAVE_HINT}")
                self.finished.emit(False)
                return

            slave = master.slaves[-1]
            self.log.emit(f"Connected — {len(master.slaves)} slave(s) detected.")

            read_size = max(EEPROM_SIZE, len(self.bin_data))
            self.log.emit("Reading current device EEPROM for comparison…")
            current = read_eeprom_data(slave, eeprom_size=read_size)
            self.device_data_ready.emit(current)

            if bytes(current[:len(self.bin_data)]) == self.bin_data:
                self.log.emit("SUCCESS: Device EEPROM already matches the BIN file — no write needed.")
                self.finished.emit(True)
                return

            self.log.emit(f"Mismatch detected. Writing {len(self.bin_data)} bytes to device EEPROM…")
            ok = write_eeprom_data(slave, self.bin_data)
            if not ok:
                self.log.emit(
                    "ERROR: Write failed after 3 attempts.\n"
                    "  • Check device connection and power.\n"
                    "  • Reconnect and try again."
                )
                self.finished.emit(False)
                return

            self.log.emit("Write complete. Waiting for device to settle…")
            sleep(0.5)
            self.log.emit("Verifying written data…")
            verified = read_eeprom_data(slave, eeprom_size=read_size)
            self.device_data_ready.emit(verified)

            if bytes(verified[:len(self.bin_data)]) == self.bin_data:
                self.log.emit("SUCCESS: EEPROM written and verified successfully.")
                self.finished.emit(True)
            else:
                self.log.emit(
                    "FAILURE: Post-write verification failed — data on device does not match BIN file.\n"
                    "  • Run the write operation again.\n"
                    "  • If it continues to fail, check for write-protection on the device."
                )
                self.finished.emit(False)
        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            self.finished.emit(False)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class EEPROMUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"STXi Motion EtherCAT EEPROM Tool  {VERSION}")
        self.setWindowIcon(QIcon(resource_path(APP_ICON)))
        self.resize(1300, 780)
        self.bin_data = b""
        self.dev_data = b""
        self._apply_styles()
        self._build_ui()

    # ------------------------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #dcdcdc;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
            QPushButton {
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 3px;
                min-width: 170px;
            }
            QPushButton:enabled {
                background-color: #bb5a5a;
                color: #fff;
                border: none;
            }
            QPushButton:enabled:hover {
                background-color: #943030;
            }
            QPushButton:pressed {
                background-color: #ffffff;
                color: #1a1a1a;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #555;
                border: 1px solid #3a3a3a;
            }
            QTextEdit {
                background-color: #0f0f0f;
                color: #c8c8c8;
                border: 1px solid #2e2e2e;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QLabel#section {
                font-size: 11px;
                font-weight: bold;
                color: #bb5a5a;
                letter-spacing: 2px;
                padding: 3px 0px 1px 0px;
            }
            QLabel#filelabel {
                font-size: 11px;
                color: #666;
                padding: 1px 0px;
            }
        """)

    def _build_ui(self):
        root = QVBoxLayout()
        root.setSpacing(6)
        root.setContentsMargins(12, 12, 12, 12)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self.choose_btn = QPushButton("Choose BIN File")
        self.choose_btn.clicked.connect(self._load_file)

        self.read_btn = QPushButton("Read Device EEPROM")
        self.read_btn.clicked.connect(self._start_read)

        self.write_btn = QPushButton("Write to Device")
        self.write_btn.setEnabled(False)
        self.write_btn.clicked.connect(self._start_write)

        btn_row.addWidget(self.choose_btn)
        btn_row.addWidget(self.read_btn)
        btn_row.addWidget(self.write_btn)
        btn_row.addStretch()

        # ---- STXi logo (top-right, same row as the buttons) ----
        logo_label = QLabel()
        pixmap = QPixmap(resource_path(STXI_LOGO))
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            )
        btn_row.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignRight)
        root.addLayout(btn_row)

        # ---- Loaded file indicator ----
        self.file_label = QLabel("No BIN file loaded.")
        self.file_label.setObjectName("filelabel")
        root.addWidget(self.file_label)

        # ---- Hex views ----
        hex_row = QHBoxLayout()
        hex_row.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        lbl_bin = QLabel("BIN FILE")
        lbl_bin.setObjectName("section")
        self.bin_hex = QTextEdit()
        self.bin_hex.setReadOnly(True)
        self.bin_hex.setPlaceholderText("Load a BIN file to view its contents…")
        left.addWidget(lbl_bin)
        left.addWidget(self.bin_hex)

        right = QVBoxLayout()
        right.setSpacing(2)
        lbl_dev = QLabel("DEVICE EEPROM")
        lbl_dev.setObjectName("section")
        self.dev_hex = QTextEdit()
        self.dev_hex.setReadOnly(True)
        self.dev_hex.setPlaceholderText(
            "Use 'Read Device EEPROM' or 'Write to Device' to populate this view…"
        )
        right.addWidget(lbl_dev)
        right.addWidget(self.dev_hex)

        hex_row.addLayout(left)
        hex_row.addLayout(right)
        root.addLayout(hex_row, stretch=1)

        # ---- Process log ----
        lbl_log = QLabel("PROCESS LOG")
        lbl_log.setObjectName("section")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(160)
        self.log_box.setPlaceholderText("Operation output will appear here…")
        root.addWidget(lbl_log)
        root.addWidget(self.log_box)

        self.setLayout(root)

    # ------------------------------------------------------------------
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select BIN File", "", "BIN Files (*.bin)")
        self.bin_data = b""
        self.write_btn.setEnabled(False)
        self.file_label.setText("No BIN file loaded.")
        if not path:
            self._refresh_hex_views()
            return
        try:
            self.bin_data = read_eeprom_bin_file(path)
            if self.bin_data:
                name = path.replace("\\", "/").split("/")[-1]
                self.file_label.setText(f"Loaded: {name}  ({len(self.bin_data)} bytes)   {path}")
                self.write_btn.setEnabled(True)
            else:
                self.bin_data = b""
                self._log("ERROR: The selected file is empty.")
        except Exception as e:
            self.bin_data = b""
            self._log(f"ERROR: Could not read file — {e}")
        self._refresh_hex_views()

    def _on_device_data(self, data):
        self.dev_data = bytes(data)
        self._refresh_hex_views()

    def _refresh_hex_views(self):
        """Render both hex panes; when both hold data, highlight differing bytes in orange."""
        bin_data, dev_data = self.bin_data, self.dev_data
        if bin_data and dev_data:
            n = min(len(bin_data), len(dev_data))
            common = {i for i in range(n) if bin_data[i] != dev_data[i]}
            bin_diff = common | set(range(n, len(bin_data)))
            dev_diff = common | set(range(n, len(dev_data)))
            self.bin_hex.setHtml(format_hex_html(bin_data, bin_diff))
            self.dev_hex.setHtml(format_hex_html(dev_data, dev_diff))
            total = len(bin_diff | dev_diff)
            if total:
                self._log(f"Comparison: {total} differing byte(s) highlighted in orange.")
            else:
                self._log("Comparison: BIN file and device EEPROM are identical.")
        else:
            self.bin_hex.setHtml(format_hex_html(bin_data)) if bin_data else self.bin_hex.clear()
            self.dev_hex.setHtml(format_hex_html(dev_data)) if dev_data else self.dev_hex.clear()

    def _start_read(self):
        self.dev_data = b""
        self.dev_hex.clear()
        self.log_box.clear()
        self._set_buttons(False)
        self.worker = ReadWorker()
        self.worker.log.connect(self._log)
        self.worker.data_ready.connect(self._on_device_data)
        self.worker.finished.connect(lambda _: self._set_buttons(True))
        self.worker.start()

    def _start_write(self):
        self.dev_data = b""
        self.dev_hex.clear()
        self.log_box.clear()
        self._set_buttons(False)
        self.worker = WriteWorker(self.bin_data)
        self.worker.log.connect(self._log)
        self.worker.device_data_ready.connect(self._on_device_data)
        self.worker.finished.connect(lambda _: self._set_buttons(True))
        self.worker.start()

    def _set_buttons(self, enabled: bool):
        self.choose_btn.setEnabled(enabled)
        self.read_btn.setEnabled(enabled)
        self.write_btn.setEnabled(enabled and bool(self.bin_data))

    def _log(self, msg: str):
        if msg.startswith("SUCCESS"):
            color = "#4caf50"
        elif msg.startswith(("ERROR", "FAILURE")):
            color = "#e05555"
        else:
            color = "#b0b0b0"
        safe = (
            msg.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace("\n", "<br>")
        )
        self.log_box.append(f'<span style="color:{color};">{safe}</span>')
        print(msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path(APP_ICON)))
    window = EEPROMUI()
    window.show()
    sys.exit(app.exec())
