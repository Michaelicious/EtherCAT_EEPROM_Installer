import sys
from time import sleep
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal

# --- Import your existing functions here ---
from ec_install_eeprom import (
    read_eeprom_bin_file,
    setup_ethercat,
    # read_eeprom_data,
    verify_eeprom_data,
    write_eeprom_data
)

class EEPROMWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, bin_data):
        super().__init__()
        self.bin_data = bin_data
        self.slave  = None  # set in setup_ethercat()

    def run(self):
        try:
            self.log.emit("Setting up EtherCAT...")
            self.master = setup_ethercat()
            if not self.master:
                self.log.emit("Failed to find EtherCAT slave. Is there a slave connected?")
                self.finished.emit(False)
                return
            self.log.emit("Reading EEPROM data from slave...")
            self.slave = self.master.slaves[-1]
            # eeprom_read_from_slave = read_eeprom_data(self.slave, eeprom_size=1024)
            # self.log.emit("EEPROM data read successfully from slave.")
            self.log.emit("Verifying EEPROM data...")
            if verify_eeprom_data(self.slave, self.bin_data):
                self.log.emit("Verification successful. No need to write.")
                self.finished.emit(True)
                return

            self.log.emit("EEPROM Data not up to date with BIN file. Writing EEPROM data...")
            res = write_eeprom_data(self.slave, self.bin_data)
            self.log.emit("Writing EEPROM data finished with result: {}".format(res))
            sleep(0.5)  # Allow some time for the write operation to complete  
            self.log.emit("Verifying EEPROM data After writing...")
            if verify_eeprom_data(self.slave, self.bin_data):
                self.log.emit("Verification successful.")
                self.finished.emit(True)
            else:
                self.log.emit("Verification failed after writing EEPROM. \nTry running again.")
                self.finished.emit(False)
        except Exception as e:
            self.log.emit(f"Error: {e}")
            self.finished.emit(False)

class EEPROMUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STXi Motion EtherCAT EEPROM Tool V1.1")
        self.resize(1000, 600)
        
        self.bin_data = b''
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # color = "#5f1717ff"
        self.setStyleSheet("""
                           QPushButton {
                            font-size: 16px;
                            padding: 10px;
                        }
                        QPushButton:pressed {
                            background-color: #ffffff;
                        }
                        QPushButton:disabled {
                            background-color: gray;
                            color: lightgray;
                        }
                        QPushButton:enabled {
                            background-color: #bb5a5a;
                            color: white;
                        }
                        QPushButton:enabled:hover {
                            background-color: #5f1717ff;
                            color: white;
                        }
                    """)
        # File selection
        file_layout = QHBoxLayout()
        self.choose_button = QPushButton("Choose BIN File")
        self.choose_button.clicked.connect(self.load_file)
        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_process)
        file_layout.addWidget(self.start_button)
        file_layout.addWidget(self.choose_button)
        layout.addLayout(file_layout)

        # Main display: messages + hex view
        main_layout = QHBoxLayout()

        # Left: info messages
        self.info_log = QTextEdit()
        self.info_log.setReadOnly(True)
        self.info_log.setPlaceholderText("Information messages...")
        self.info_log.setMinimumSize(550, 600)
        main_layout.addWidget(self.info_log, 1)

        # Right: hex view
        self.hex_view = QTextEdit()
        self.hex_view.setReadOnly(True)
        self.hex_view.setPlaceholderText("Hex view of BIN file...")
        self.hex_view.setMinimumSize(550, 600)
        self.hex_view.setFixedWidth(550)
        main_layout.addWidget(self.hex_view, 2)

        layout.addLayout(main_layout)
        self.setLayout(layout)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select BIN file", "", "BIN Files (*.bin)")
        self.display_hex(b'')
        self.bin_data = b''
        self.start_button.setEnabled(False)
        QApplication.processEvents()  # Ensure UI updates before file loading
        if file_path:
            try:
                self.bin_data = read_eeprom_bin_file(file_path)
                if self.bin_data:
                    self.display_hex(self.bin_data)
                    self.log_message(f"File {file_path} loaded successfully. Size: {len(self.bin_data)} bytes.")
                    self.start_button.setEnabled(True)
                else:
                    self.log_message("Selected file is empty.")
            except Exception as e:
                self.log_message(f"Failed to read file: {e}")
        else:
            self.log_message("No file selected.")

    def display_hex(self, data: bytes):
        hex_lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            # Create hex representation
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            # Pad hex string with spaces to align ASCII representation
            hex_str = f"{hex_str:<48}"
            # Create ASCII representation
            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            hex_lines.append(f"{i:08X}\t{hex_str}\t{ascii_str}")
        self.hex_view.setPlainText('\n'.join(hex_lines))

    def log_message(self, msg):
        self.info_log.append(msg)
        print(msg)

    def start_process(self):
        self.info_log.clear()
        self.start_button.setEnabled(False)
        self.worker = EEPROMWorker(self.bin_data)
        self.worker.log.connect(self.log_message)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()

    def on_process_finished(self, success: bool):
        if success:
            QMessageBox.information(self, "EEPROM", "Process finished successfully.")
        else:
            QMessageBox.critical(self, "EEPROM", "Process failed. See logs.")
        self.start_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EEPROMUI()
    window.show()
    sys.exit(app.exec())
