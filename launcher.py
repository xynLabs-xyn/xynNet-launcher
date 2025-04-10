import os
import json
import requests
import psutil
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import warnings
import zipfile
import io
import subprocess
import sys
from PyQt5 import QtWidgets, QtGui, QtCore, QtQml, QtQuick

# Version checking and updates
version_url = "https://xynnet.com/client-updates/latest_version.json"
update_url = "https://xynnet.com/client-updates/update.zip"

config_file = "launcher_config.json"

class CustomPromptDialog(QtWidgets.QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 120)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.message_label = QtWidgets.QLabel(message, self)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setStyleSheet("color: #ddd;")
        layout.addWidget(self.message_label)

        buttons_layout = QtWidgets.QHBoxLayout()

        self.yes_button = QtWidgets.QPushButton('Yes', self)
        self.yes_button.setStyleSheet("""
            background: #333;
            color: #ddd;
            border: none;
            border-radius: 5px;
            padding: 5px;
        """)
        self.yes_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.yes_button)

        self.no_button = QtWidgets.QPushButton('No', self)
        self.no_button.setStyleSheet("""
            background: #333;
            color: #ddd;
            border: none;
            border-radius: 5px;
            padding: 5px;
        """)
        self.no_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.no_button)

        layout.addLayout(buttons_layout)

        self.setStyleSheet("""
            QDialog {
                background: #111;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background: #555;
            }
        """)


class CustomDialog(QtWidgets.QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.message_label = QtWidgets.QLabel(message, self)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setStyleSheet("color: #ddd;")
        layout.addWidget(self.message_label)

        self.close_button = QtWidgets.QPushButton('OK', self)
        self.close_button.setStyleSheet("""
            background: #333;
            color: #ddd;
            border: none;
            border-radius: 5px;
            padding: 5px;
        """)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

        self.setStyleSheet("""
            QDialog {
                background: #111;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background: #555;
            }
        """)

    def set_message(self, message):
        self.message_label.setText(message)

warnings.simplefilter('ignore', InsecureRequestWarning)

def load_local_version():
    """Load the local version from the configuration file."""
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                return config.get("version", "0.0.0")
        except (json.JSONDecodeError, Exception):
            return "1.0.0"
    return "0.0.0"

def save_local_version(version):
    """Save the updated version to the local configuration file."""
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
    config["version"] = version
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
    except IOError:
        pass

def get_latest_version():
    """Retrieve the latest version from the server."""
    try:
        response = requests.get(version_url, verify=False)
        response.raise_for_status()
        json_data = response.json()
        return json_data.get("latest_version", "0.0.0")
    except requests.RequestException:
        return None

def find_executable(root_dir, filename):
    """Search for a file in a directory."""
    for root, dirs, files in os.walk(root_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

def is_process_running(executable_name):
    """Check if the executable process is running."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == executable_name:
            return True
    return False   

def download_update(url, extract_to, progress_callback=None):
    """Download the update from the specified server URL and extract it."""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            num_files = len(zip_file.namelist())
            for i, file in enumerate(zip_file.namelist()):
                zip_file.extract(file, extract_to)
                if progress_callback:
                    progress = (i + 1) / num_files * 100
                    progress_callback(int(progress), f"Extracting: {file}")
    except (requests.exceptions.RequestException, zipfile.BadZipFile):
        pass

def launch_game(executable_path):
    """Launch the client."""
    try:
        subprocess.Popen([executable_path])
    except Exception:
        pass

class Launcher(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.game_path = None
        self.executable_name = "client.exe"
        self.local_version = load_local_version()
        self.latest_version = None
        self.initUI()
        self.check_game_path()
        self.old_pos = None

    def check_game_path(self):
        """Check if the client path is set in the config file or prompt the user."""
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
                self.game_path = config.get("game_path")
                self.executable_name = config.get("executable_name", "client.exe")
        
        if not self.game_path or not os.path.isdir(self.game_path):
            self.select_game_directory()
        else:
            self.update_status_label()

    def select_game_directory(self):
        """Prompt the user to select the client directory."""
        game_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if game_path:
            self.game_path = game_path

            # Executable is in the bin/ subdirectory
            executable_path = os.path.join(game_path, "bin", "client.exe")
            if os.path.isfile(executable_path):
                # Save the client path and executable name to the configuration file
                with open(config_file, "w") as f:
                    json.dump({
                        "game_path": game_path,
                        "executable_name": "client.exe",
                        "version": "1.0.0"
                    }, f)
                self.update_status_label()
            else:
                dlg = CustomDialog("Error", "No client.exe found in the 'bin' directory of the selected path.", self)
                dlg.exec_()
                self.select_game_directory()
        else:
            dlg = CustomDialog("Error", "No directory selected, exiting.", self)
            dlg.exec_()
            sys.exit()


    def update_status_label(self):
        """Update the status based on whether the client executable is found."""
        executable_path = find_executable(self.game_path, self.executable_name)
        if executable_path:
            self.status_label.setText(f"Path: {self.game_path}, Version: {self.local_version}")
            self.status_label.setStyleSheet("color: #ddd;")
        else:
            self.status_label.setText("Client not found")
            self.status_label.setStyleSheet("color: red;")

    def initUI(self):
        self.setWindowTitle('Game Launcher')
        self.setFixedSize(480, 127)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        background_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png")
        self.background_label = QtWidgets.QLabel(self)
        self.background_label.setGeometry(0, 0, 480, 127)
        self.background_label.setPixmap(QtGui.QPixmap(background_path))
        self.background_label.setScaledContents(True)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(20, 100, 440, 10)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        self.status_label = QtWidgets.QLabel('Initializing...', self)
        self.status_label.setGeometry(20, 20, 440, 20)
        self.status_label.setStyleSheet("color: #ddd;")
        self.status_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        updateimage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update.png")
        self.update_button = QtWidgets.QPushButton(self)
        self.update_button.setGeometry(20, 70, 94, 21)
        self.update_button.setIcon(QtGui.QIcon(updateimage_path))
        self.update_button.setIconSize(QtCore.QSize(94, 21))
        self.update_button.clicked.connect(self.update_game)

        playimage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "play.png")
        self.play_button = QtWidgets.QPushButton(self)
        self.play_button.setGeometry(366, 70, 94, 21)
        self.play_button.setIcon(QtGui.QIcon(playimage_path))
        self.play_button.setIconSize(QtCore.QSize(94, 21))
        self.play_button.clicked.connect(self.play_game)

        ximage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "x.png")
        self.exit_button = QtWidgets.QPushButton(self)
        self.exit_button.setGeometry(450, 10, 21, 21)
        pixmap = QtGui.QPixmap(ximage_path)

        self.exit_button.setIcon(QtGui.QIcon(pixmap))
        self.exit_button.setIconSize(QtCore.QSize(21, 21))

        self.exit_button.setStyleSheet("background: transparent; border: none;")

        self.exit_button.clicked.connect(self.close)


    def mousePressEvent(self, event):
        self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = event.globalPos() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

    def update_game(self):
        self.latest_version = get_latest_version()
        if self.latest_version and self.latest_version > self.local_version:
            self.progress_bar.show()
            self.download_thread = QtCore.QThread()
            self.worker = DownloadWorker(self)
            self.worker.moveToThread(self.download_thread)
            self.worker.progress.connect(self.update_progress)
            self.download_thread.started.connect(self.worker.run)
            self.download_thread.start()
        else:
            dlg = CustomDialog("No Update Needed", "You are up to date!", self)
            dlg.exec_()

    def update_progress(self, value, file):
        self.progress_bar.setValue(value)
        if value == 100:
            self.progress_bar.hide()
            save_local_version(self.latest_version)
            self.local_version = self.latest_version
            dlg = CustomDialog("Update Complete", "The client has been updated.", self)
            dlg.exec_()
            self.status_label.setText(f"Updated to version: {self.latest_version}")

    # Boosted Creature updated on the server
    boostedcreature_url = "https://xynnet.com/boostedcreature.json"

    def update_boostedcreature_json(self, game_cache_folder):
        """Update the boostedcreature.json file in the client cache folder for the player."""
        json_file_path = os.path.join(game_cache_folder, "boostedcreature.json")
        
        try:
            response = requests.get(self.boostedcreature_url, verify=False)
            response.raise_for_status()  # Ensure the request was successful

            # Write the JSON content to the file
            with open(json_file_path, "w") as json_file:
                json.dump(response.json(), json_file, indent=4)

        except requests.RequestException as e:
            print(f"Failed to update boostedcreature.json: {e}")


    def play_game(self):
        """Check version and fetch updated boostedcreature.json before launching the client."""
        # Retrieve the latest version from the server
        self.latest_version = get_latest_version()

        # Check if the version needs to be updated
        if self.latest_version and self.latest_version > self.local_version:
            dlg = CustomDialog("Update Required", "You need to update!", self)
            dlg.exec_()
            return

        executable_path = find_executable(self.game_path, self.executable_name)

        if executable_path:
            if is_process_running(self.executable_name):
                # Show the custom prompt dialog
                prompt = CustomPromptDialog(
                    "Client Running",
                    "The client is already running.\nDo you want to open another one?",
                    self
                )
                if prompt.exec_() != QtWidgets.QDialog.Accepted:
                    return

            # Before launching the client, update the JSON file
            game_cache_folder = os.path.join(self.game_path, "cache")
            self.update_boostedcreature_json(game_cache_folder)

            # Set environment variables and launch the client
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(self.game_path, 'bin', 'platforms')
            os.environ['PATH'] += os.pathsep + os.path.join(self.game_path, 'bin')
            os.environ['QML2_IMPORT_PATH'] = os.path.join(self.game_path, 'bin', 'Qt', 'QtQuick.2')
            os.environ['QT_PLUGIN_PATH'] = os.path.join(self.game_path, 'bin', 'Qt')

            launch_game(executable_path)
        else:
            dlg = CustomDialog("Error", "Client executable not found.", self)
            dlg.exec_()


class DownloadWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        download_update(update_url, self.parent.game_path, self.progress.emit)

def main():
    app = QtWidgets.QApplication(sys.argv)
    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
