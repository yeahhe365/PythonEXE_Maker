import os
import sys
import subprocess
import logging
# import webbrowser
# from textwrap import dedent

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTextEdit, QLineEdit, QHBoxLayout, QDialog, QTextBrowser, QProgressBar,
    QGridLayout, QComboBox, QGroupBox, QMenuBar, QAction, QStatusBar, QListWidget,
    QListWidgetItem, QSplitter, QScrollArea, QFrame, QTabWidget
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QTranslator, QLocale  # , QCoreApplication

# Try to import Pillow
try:
    from PIL import Image
except ImportError:
    Image = None

# Set up logging: output logs to file and console
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler("app.log", mode='w', encoding='utf-8'),
    logging.StreamHandler(sys.stdout)])


class WorkerSignals(QObject):
    """Defining signals for Worker threads"""
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(str, int)
    conversion_failed = pyqtSignal(str)


class ConvertRunnable(QRunnable):
    """Runnable class for conversion tasks"""

    def __init__(self, script_path, convert_mode, output_dir, exe_name, icon_path, file_version,
                 copyright_info, extra_library, additional_options):
        super().__init__()
        self.script_path = script_path
        self.convert_mode = convert_mode
        self.output_dir = output_dir
        self.exe_name = exe_name
        self.icon_path = icon_path
        self.file_version = file_version
        self.copyright_info = copyright_info
        self.extra_library = extra_library
        self.additional_options = additional_options
        self.signals = WorkerSignals()
        self._is_running = True

    def run(self):
        version_file_path = None
        try:
            script_dir = os.path.dirname(self.script_path)
            exe_name = self.exe_name or os.path.splitext(os.path.basename(self.script_path))[0]
            output_dir = self.output_dir or script_dir

            if not self.ensure_pyinstaller():
                return

            options = self.prepare_pyinstaller_options(exe_name, output_dir)
            if self.icon_path:
                icon_file = self.handle_icon(script_dir)
                if icon_file:
                    options.append(f'--icon={icon_file}')

            if self.file_version or self.copyright_info:
                version_file_path = self.create_version_file(exe_name, script_dir)
                if version_file_path:
                    options.append(f'--version-file={version_file_path}')

            self.update_status("Start converting...")
            success = self.run_pyinstaller(options)

            if success:
                exe_path = os.path.join(output_dir, exe_name + '.exe')
                if os.path.exists(exe_path):
                    exe_size = os.path.getsize(exe_path) // 1024
                    self.signals.conversion_finished.emit(exe_path, exe_size)
                    self.update_status(
                        f"Conversion successful! EXE file is located at: {exe_path} (Size: {exe_size} KB)")
                else:
                    error_message = "Conversion completed, but the resulting EXE file was not found."
                    self.update_status(error_message)
                    self.signals.conversion_failed.emit(error_message)
            else:
                error_message = "Conversion failed, please see the error message above."
                self.update_status(error_message)
                self.signals.conversion_failed.emit(error_message)
        except Exception as e:
            error_message = f"Exception occurred during conversion : {e}"
            self.update_status(error_message)
            self.signals.conversion_failed.emit(error_message)
        finally:
            self.cleanup_files(version_file_path)

    def stop(self):
        """Stop the conversion task"""
        self._is_running = False

    def update_status(self, message: str):
        """Update conversion status"""
        logging.info(message)
        self.signals.status_updated.emit(message)

    def ensure_pyinstaller(self) -> bool:
        """Make sure PyInstaller is installed"""
        try:
            subprocess.run([sys.executable, '-m', 'PyInstaller', '--version'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_status("PyInstaller detected.")
            return True
        except subprocess.CalledProcessError:
            self.update_status("PyInstaller not detected, trying to install...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
                self.update_status("PyInstaller was installed successfully.")
                return True
            except subprocess.CalledProcessError as e:
                self.update_status(f"Failed to install PyInstaller : {e}")
                return False

    def prepare_pyinstaller_options(self, exe_name: str, output_dir: str) -> list:
        """Prepare command line options for PyInstaller"""
        mode = ["GUI Model", "Command Line Mode"]
        options = ['--onefile', '--clean', '--console' if self.convert_mode == mode[1] else '--windowed']

        if self.extra_library:
            hidden_imports = [lib.strip() for lib in self.extra_library.split(',') if lib.strip()]
            options += [f'--hidden-import={lib}' for lib in hidden_imports]

        if self.additional_options:
            options += self.additional_options.strip().split()

        options += ['--distpath', output_dir, '-n', exe_name]
        return options

    def handle_icon(self, script_dir: str) -> str:
        """Process icon files, support converting PNG to ICO"""
        if not Image:
            self.update_status(
                "Pillow library is not installed and cannot convert PNG icons. Please install Pillow or use the ICO icon.")
            return ""

        lower_icon = self.icon_path.lower()
        if lower_icon.endswith('.png'):
            self.update_status("PNG icon detected, converting to ICO format...")
            try:
                img = Image.open(self.icon_path)
                ico_path = os.path.join(script_dir, 'icon_converted.ico')
                img.save(ico_path, format='ICO',
                         sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                self.update_status("The icon conversion was successful.")
                return ico_path
            except Exception as e:
                self.update_status(f"PNG to ICO failed: {e}")
                return ""
        elif lower_icon.endswith('.ico'):
            return self.icon_path
        else:
            self.update_status("Unsupported icon format, only .png and .ico formats are supported.")
            return ""

    def create_version_file(self, exe_name: str, script_dir: str) -> str:
        """Create version information file"""
        try:
            from PyInstaller.utils.win32.versionfile import (
                VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
            )
        except ImportError as e:
            self.update_status(f"Failed to import version information class: {e}")
            return ""

        version_numbers = self.file_version.split('.') if self.file_version else ['1', '0', '0', '0']
        if len(version_numbers) != 4 or not all(num.isdigit() for num in version_numbers):
            version_numbers = ['1', '0', '0', '0']

        version_info = VSVersionInfo(
            ffi=FixedFileInfo(
                filevers=tuple(map(int, version_numbers)),
                prodvers=tuple(map(int, version_numbers)),
                mask=0x3f,
                flags=0x0,
                OS=0x40004,
                fileType=0x1,
                subtype=0x0,
                date=(0, 0)
            ),
            kids=[
                StringFileInfo(
                    [
                        StringTable(
                            '040904E4',
                            [
                                StringStruct('CompanyName', ''),
                                StringStruct('FileDescription', exe_name),
                                StringStruct('FileVersion', '.'.join(version_numbers)),
                                StringStruct('InternalName', f'{exe_name}.exe'),
                                StringStruct('LegalCopyright', self.copyright_info),
                                StringStruct('OriginalFilename', f'{exe_name}.exe'),
                                StringStruct('ProductName', exe_name),
                                StringStruct('ProductVersion', '.'.join(version_numbers))
                            ]
                        )
                    ]
                ),
                VarFileInfo([VarStruct('Translation', [0x0409, 0x04B0])])
            ]
        )

        version_file_path = os.path.join(script_dir, 'version_info.txt')
        try:
            with open(version_file_path, 'w', encoding='utf-8') as vf:
                vf.write(version_info.__str__())
            self.update_status("Generate version information file.")
            return version_file_path
        except Exception as e:
            self.update_status(f"Failed to generate version information file: {e}")
            return ""

    def run_pyinstaller(self, options: list) -> bool:
        """Run PyInstaller to convert"""
        cmd = [sys.executable, '-m', 'PyInstaller'] + options + [self.script_path]
        self.update_status(f"Execute Command: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )

            for line in process.stdout:
                if not self._is_running:
                    process.terminate()
                    self.update_status("Conversion canceled by user.")
                    return False
                line = line.strip()
                self.update_status(line)
                # Simple progress estimate
                if "Analyzing" in line:
                    self.signals.progress_updated.emit(30)
                elif "Collecting" in line:
                    self.signals.progress_updated.emit(50)
                elif "Building" in line:
                    self.signals.progress_updated.emit(70)
                elif "completed successfully" in line.lower():
                    self.signals.progress_updated.emit(100)

            process.stdout.close()
            process.wait()

            return process.returncode == 0
        except Exception as e:
            self.update_status(f"Exception occurred during conversion: {e}")
            return False

    def cleanup_files(self, version_file_path: str):
        """Clean temporary files"""
        script_dir = os.path.dirname(self.script_path)
        if version_file_path and os.path.exists(version_file_path):
            try:
                os.remove(version_file_path)
                self.update_status("Delete the version information file.")
            except Exception as e:
                self.update_status(f"Unable to delete version information file: {e}")

        if self.icon_path and self.icon_path.lower().endswith('.png'):
            ico_path = os.path.join(script_dir, 'icon_converted.ico')
            if os.path.exists(ico_path):
                try:
                    os.remove(ico_path)
                    self.update_status("Delete temporary ICO files.")
                except Exception as e:
                    self.update_status(f"Unable to delete temporary ICO file: {e}")


class DropArea(QLabel):
    """Drag and drop area, allowing users to drag in .py files"""
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText(self.tr("Drag in .py file"))
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                min-height: 80px;
                font-size: 13px;
                color: #555;
                padding: 10px;
            }
            QLabel:hover {
                border-color: #777;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.toLocalFile().endswith('.py') for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile().endswith(".py")]
        if paths:
            for path in paths:
                self.file_dropped.emit(path)
        else:
            QMessageBox.warning(self, self.tr("Warning"), self.tr(
                "Please drag and drop the Python file (.py) into the window."))


class ManualDialog(QDialog):
    """Instructions dialog box"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Manual"))
        self.setFixedSize(800, 600)
        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 13))
        self.text_browser.setHtml(self.manual_text())
        layout.addWidget(self.text_browser)
        self.setLayout(layout)

    @staticmethod
    def manual_text():
        return """
        <h1>PythonEXE Maker Manual</h1>
        <p>This program is used to convert Python scripts into executable files (EXE). Here are the steps to use:</p>
        <ol>
            <li>Configure the conversion mode, output directory, EXE information and other parameters in the left panel.</li>
            <li>In the "Task Management" tab on the right, add a Python script by dragging or browsing for files.</li>
            <li>Click the "Start Conversion" button to start the conversion. If you need to cancel midway, click "Cancel Conversion".</li>
            <li>The conversion progress and logs can be viewed in the "Log" tab.</li>
        </ol>
        <p><strong>Things to note:</strong></p>
        <ul>
            <li>Icon files support .png and .ico formats (.png will be automatically converted to .ico).</li>
            <li>If the Python script uses external libraries or resource files, please ensure that they are specified correctly in "Additional Modules" or "Additional Parameters".</li>
            <li>In the "Additional Parameters" field, you can enter the module names that need to be hidden and imported (separate multiple ones with commas).</li>
            <li>"Additional parameters" allows you to enter additional command line parameters for PyInstaller.</li>
        </ul>
        """


class AboutDialog(QDialog):
    """About dialog box"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("About PythonEXE Maker"))
        self.setFixedSize(600, 400)
        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 11))

        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, 'Icons', 'logo.png')

        if os.path.exists(logo_path):
            # Embed image using file URL
            logo_url = 'file://' + logo_path.replace('\\', '/')
            logo_html = f'<img src="{logo_url}" alt="Logo" width="200"><br>'
        else:
            logo_html = ''

        self.text_browser.setHtml(logo_html + self.about_text())
        layout.addWidget(self.text_browser)
        self.setLayout(layout)

    def about_text(self):
        return """
        <h1>About PythonEXE Maker</h1>
        <p>Version：1.1.0</p>
        <p>This is an open source free tool for converting Python scripts into executable files.</p>
        <p>If you have any questions or suggestions, please submit an issue on GitHub or view the source code:</p>
        <p><a href="https://github.com/chetanjain2099/PythonEXE_Maker">https://github.com/chetanjain2099/PythonEXE_Maker</a></p>
        <p><strong>Thank you for your use and support！</strong></p>
        """


class LogViewerDialog(QDialog):
    """Log viewing dialog box"""

    def __init__(self, parent=None, log_path="app.log"):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Log File"))
        self.setFixedSize(800, 600)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 9))
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.load_log(log_path)

    def load_log(self, log_path):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
            except Exception as e:
                self.text_edit.setPlainText(self.tr(f"Unable to read the log file: {e}"))
        else:
            self.text_edit.setPlainText(self.tr("The log file does not exist."))


class MainWindow(QMainWindow):
    """Main window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("PythonEXE Maker"))
        self.setGeometry(100, 100, 1300, 900)
        self.setFont(QFont("Arial", 10))

        self.script_paths = []
        self.thread_pool = QThreadPool()
        self.tasks = []
        self.task_widgets = {}

        self.init_ui()
        self.update_start_button_state()
        self.connect_signals()

    def init_ui(self):
        # Create central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Menu bar
        self.init_menu()

        splitter = QSplitter(Qt.Horizontal)

        # Settings and operation area on the left
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.init_settings_group())
        left_layout.addLayout(self.init_button_group())
        splitter.addWidget(left_widget)

        # Right tab (task management, log)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # "Task Management" tab
        task_tab = QWidget()
        task_tab_layout = QVBoxLayout(task_tab)

        # Script management area
        script_group = QGroupBox(self.tr("Script management"))
        script_layout = QVBoxLayout()

        # Drag area and browse button
        drop_browse_layout = QHBoxLayout()
        self.drop_area = DropArea(self)
        self.drop_area.file_dropped.connect(self.add_script_path)
        drop_browse_layout.addWidget(self.drop_area)

        browse_button = QPushButton(self.tr("Browse Files"))
        browse_button.setToolTip(
            self.tr("Click to select the Python file to be converted. Multiple selections are available."))
        browse_button.clicked.connect(self.browse_files)
        browse_button.setFixedHeight(80)
        browse_button.setStyleSheet("QPushButton { font-size: 13px; }")
        drop_browse_layout.addWidget(browse_button)

        script_layout.addLayout(drop_browse_layout)

        # Script list
        self.script_list = QListWidget()
        self.script_list.setToolTip(
            self.tr("List of selected Python scripts, which can be removed by double-clicking."))
        self.script_list.itemDoubleClicked.connect(self.remove_script)
        script_layout.addWidget(self.script_list)

        script_group.setLayout(script_layout)
        task_tab_layout.addWidget(script_group)

        # Task progress area
        task_progress_group = QGroupBox(self.tr("Conversion Task Progress"))
        task_progress_layout = QVBoxLayout(task_progress_group)

        self.task_area = QScrollArea()
        self.task_area.setWidgetResizable(True)
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignTop)
        self.task_area.setWidget(self.task_container)
        task_progress_layout.addWidget(self.task_area)

        task_progress_group.setLayout(task_progress_layout)
        task_tab_layout.addWidget(task_progress_group)

        self.tab_widget.addTab(task_tab, self.tr("Task Management"))

        # "Log" tab
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)

        # Log text
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFont(QFont("Courier New", 9))
        log_tab_layout.addWidget(self.status_text_edit)

        # Global progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        log_tab_layout.addWidget(self.progress_bar)

        # Status bar
        self.status_bar = QStatusBar()
        log_tab_layout.addWidget(self.status_bar)

        self.tab_widget.addTab(log_tab, self.tr("Log"))

        splitter.addWidget(self.tab_widget)
        splitter.setSizes([500, 800])

        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

        # Set program window icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'Icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(self.tr(f"Icon file not found: {icon_path}"))

    def init_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu(self.tr('File'))
        exit_action = QAction(self.tr('Quit'), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu(self.tr('Help'))
        manual_action = QAction(self.tr('Instructions for use'), self)
        manual_action.triggered.connect(self.show_manual)
        help_menu.addAction(manual_action)

        about_action = QAction(self.tr('About'), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        github_action = QAction(self.tr('Open Source Address'), self)
        # github_action.triggered.connect(lambda: webbrowser.open("https://github.com/yeahhe365/PythonEXE_Maker"))
        help_menu.addAction(github_action)

        website_action = QAction(self.tr('Official Website'), self)
        # website_action.triggered.connect(lambda: webbrowser.open("https://www.yeahhe.online/"))
        help_menu.addAction(website_action)

        forum_action = QAction(self.tr('LINUXDO Forum Homepage'), self)
        # forum_action.triggered.connect(lambda: webbrowser.open("https://www.linuxdo.com/users/yeahhe"))
        help_menu.addAction(forum_action)

        support_action = QAction(self.tr('Invite Developers to Coffee'), self)
        support_action.triggered.connect(self.open_bilibili_link)
        help_menu.addAction(support_action)

        # Log menu
        log_menu = menubar.addMenu(self.tr('Log'))
        view_log_action = QAction(self.tr('View log files'), self)
        view_log_action.triggered.connect(self.view_log_file)
        log_menu.addAction(view_log_action)

    def init_settings_group(self) -> QGroupBox:
        """Initialize the group of basic settings, EXE information and advanced settings"""
        settings_group = QGroupBox(self.tr("Basic Settings"))
        settings_layout = QGridLayout()

        # Conversion mode
        mode_label = QLabel(self.tr("Conversion Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([self.tr("GUI Model"), self.tr("Command Line Mode")])
        self.mode_combo.setToolTip(self.tr(
            "Select whether the generated EXE will be with a console (command line mode) or without a console (GUI mode)."))
        settings_layout.addWidget(mode_label, 0, 0)
        settings_layout.addWidget(self.mode_combo, 0, 1)

        # Output directory
        output_label = QLabel(self.tr("Output Directory:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText(self.tr("By default, it is in the same directory as the source file."))
        self.output_edit.setToolTip(self.tr(
            "Set the output directory for generated EXE files. If empty, it will be placed in the same directory as the source file by default."))
        output_button = QPushButton(self.tr("Browse"))
        output_button.setToolTip(self.tr("Select the output directory."))
        output_button.clicked.connect(self.browse_output_dir)
        output_h_layout = QHBoxLayout()
        output_h_layout.addWidget(self.output_edit)
        output_h_layout.addWidget(output_button)
        settings_layout.addWidget(output_label, 1, 0)
        settings_layout.addLayout(output_h_layout, 1, 1)

        # EXE information
        exe_info_group = QGroupBox(self.tr("EXE Information"))
        exe_info_layout = QGridLayout()

        name_label = QLabel(self.tr("EXE Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("Defaults to the same name as the source file"))
        self.name_edit.setToolTip(self.tr("Set the generated EXE file name."))
        exe_info_layout.addWidget(name_label, 0, 0)
        exe_info_layout.addWidget(self.name_edit, 0, 1)

        icon_label = QLabel(self.tr("Icon File:"))
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText(self.tr("Optional, supports .png and .ico"))
        self.icon_edit.setToolTip(self.tr(
            "Select an icon file to use with the EXE. If it is PNG, it will be automatically converted to ICO."))
        icon_button = QPushButton(self.tr("Browse"))
        icon_button.setToolTip(self.tr("Select the icon file."))
        icon_button.clicked.connect(self.browse_icon_file)
        icon_h_layout = QHBoxLayout()
        icon_h_layout.addWidget(self.icon_edit)
        icon_h_layout.addWidget(icon_button)
        exe_info_layout.addWidget(icon_label, 1, 0)
        exe_info_layout.addLayout(icon_h_layout, 1, 1)

        version_label = QLabel(self.tr("File Version:"))
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("1.0.0.0")
        self.version_edit.setToolTip(self.tr("Set the version number of the EXE file (X.X.X.X)."))
        exe_info_layout.addWidget(version_label, 2, 0)
        exe_info_layout.addWidget(self.version_edit, 2, 1)

        copyright_label = QLabel(self.tr("Copyright Information:"))
        self.copyright_edit = QLineEdit()
        self.copyright_edit.setToolTip(self.tr("Set the copyright information of the EXE file."))
        exe_info_layout.addWidget(copyright_label, 3, 0)
        exe_info_layout.addWidget(self.copyright_edit, 3, 1)

        exe_info_group.setLayout(exe_info_layout)
        settings_layout.addWidget(exe_info_group, 2, 0, 1, 2)

        # Advanced settings
        advanced_settings_group = QGroupBox(self.tr("Advanced Settings"))
        advanced_settings_layout = QGridLayout()

        # Extra modules
        library_label = QLabel(self.tr("Additional Modules:"))
        self.library_edit = QLineEdit()
        self.library_edit.setPlaceholderText(self.tr("Hidden imported modules, separated by commas"))
        self.library_edit.setToolTip(
            self.tr("Enter the name of the module that needs to be added (separate multiple with commas)."))
        advanced_settings_layout.addWidget(library_label, 0, 0)
        advanced_settings_layout.addWidget(self.library_edit, 0, 1)

        # Additional arguments
        options_label = QLabel(self.tr("Additional Parameters:"))
        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText(self.tr("For example：--add-data 'data.txt;.'"))
        self.options_edit.setToolTip(self.tr("Enter custom PyInstaller parameters."))
        advanced_settings_layout.addWidget(options_label, 1, 0)
        advanced_settings_layout.addWidget(self.options_edit, 1, 1)

        advanced_settings_group.setLayout(advanced_settings_layout)
        settings_layout.addWidget(advanced_settings_group, 3, 0, 1, 2)

        settings_group.setLayout(settings_layout)
        return settings_group

    def init_button_group(self) -> QHBoxLayout:
        """Initialize start and cancel conversion buttons"""
        button_layout = QHBoxLayout()

        self.start_button = QPushButton(self.tr("Start conversion"))
        self.start_button.setEnabled(False)
        self.start_button.setToolTip(self.tr("Start conversion of the selected Python script to EXE."))
        self.start_button.setStyleSheet("QPushButton { font-size: 13px; padding: 6px; }")
        self.start_button.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton(self.tr("Cancel conversion"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip(self.tr("Cancel a conversion task in progress."))
        self.cancel_button.setStyleSheet("QPushButton { font-size: 13px; padding: 6px; }")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        button_layout.addWidget(self.cancel_button)

        return button_layout

    def connect_signals(self):
        """Connect necessary signals"""
        pass

    def add_script_path(self, path: str):
        """Add script path to list"""
        if path not in self.script_paths:
            self.script_paths.append(path)
            self.script_list.addItem(QListWidgetItem(path))
            self.append_status(self.tr(f"Script added: {path}"))
            self.update_start_button_state()

    def browse_files(self):
        """Browse and add the Python script file"""
        script_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Select Python file"), "", "Python Files (*.py)")
        if script_paths:
            added = False
            for script_path in script_paths:
                if script_path not in self.script_paths:
                    self.script_paths.append(script_path)
                    self.script_list.addItem(QListWidgetItem(script_path))
                    self.append_status(self.tr(f"Script added: {script_path}"))
                    added = True
            if added:
                self.update_start_button_state()

    def browse_output_dir(self):
        """Browse and set the output directory"""
        output_dir = QFileDialog.getExistingDirectory(self, self.tr("Select output directory"))
        if output_dir:
            self.output_edit.setText(output_dir)

    def browse_icon_file(self):
        """Browse and set the icon file"""
        icon_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Icon file"), "", "Image Files (*.ico *.png)")
        if icon_path:
            self.icon_edit.setText(icon_path)

    def remove_script(self, item: QListWidgetItem):
        """Remove script"""
        path = item.text()
        if path in self.script_paths:
            self.script_paths.remove(path)
            self.script_list.takeItem(self.script_list.row(item))
            self.append_status(self.tr(f"Script removed: {path}"))
            self.update_start_button_state()

    def start_conversion(self):
        """Start converting all selected scripts"""
        if not self.script_paths:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select at least one Python script first."))
            return

        convert_mode = self.mode_combo.currentText()
        output_dir = self.output_edit.text().strip() or None
        exe_name = self.name_edit.text().strip() or None
        icon_path = self.icon_edit.text().strip() or None
        file_version = self.version_edit.text().strip() or None
        copyright_info = self.copyright_edit.text().strip()
        extra_library = self.library_edit.text().strip() or None
        additional_options = self.options_edit.text().strip() or None

        if file_version and not self.validate_version(file_version):
            QMessageBox.warning(self, self.tr("Warning"), self.tr(
                "The file version number format is incorrect. It should be X.X.X.X (such as 1.0.0.0)."))
            return

        self.toggle_ui_elements(False)
        self.status_text_edit.clear()
        self.append_status(self.tr("Start converting..."))
        self.progress_bar.show()
        self.status_bar.showMessage(self.tr("Converting..."))

        self.tasks = []
        self.task_widgets = {}
        # Clear the task progress display area
        for i in reversed(range(self.task_layout.count())):
            w = self.task_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        for script_path in self.script_paths:
            task_widget = self.create_task_widget(script_path)
            self.task_layout.addWidget(task_widget['widget'])
            self.task_widgets[script_path] = task_widget

            runnable = ConvertRunnable(script_path=script_path, convert_mode=convert_mode,
                                       output_dir=output_dir, exe_name=exe_name, icon_path=icon_path,
                                       file_version=file_version,
                                       copyright_info=copyright_info, extra_library=extra_library,
                                       additional_options=additional_options)

            runnable.signals.status_updated.connect(lambda msg, sp=script_path: self.update_status(msg, sp))
            runnable.signals.progress_updated.connect(lambda val, sp=script_path: self.update_progress(val, sp))
            runnable.signals.conversion_finished.connect(
                lambda exe, size, sp=script_path: self.conversion_finished(exe, size, sp))
            runnable.signals.conversion_failed.connect(lambda err, sp=script_path: self.conversion_failed(err, sp))

            self.thread_pool.start(runnable)
            self.tasks.append(runnable)

        self.cancel_button.setEnabled(True)

    def cancel_conversion(self):
        """Cancel all ongoing conversion tasks"""
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.append_status(self.tr("Cancellation of the conversion task has been requested."))
            self.status_bar.showMessage(self.tr("Cancel conversion..."))
            self.cancel_button.setEnabled(False)

    def conversion_finished(self, exe_path: str, exe_size: int, script_path: str):
        """Handle conversion completion"""
        self.append_status(self.tr(f"Conversion successful! EXE file is located at: {exe_path} (size: {exe_size} KB)"))
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(self.tr(f"Conversion successful! File: {exe_path} ({exe_size} KB)"))
            task_widget['progress'].setValue(100)
            self.progress_bar.setValue(100)
        if all([getattr(task, '_is_running', False) for task in self.tasks]):
            self.conversion_complete()

    def conversion_failed(self, error_message: str, script_path: str):
        """Handling conversion failure situations"""
        self.append_status(f"<span style='color:red;'>{error_message}</span>")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(f"<span style='color:red;'>{error_message}</span>")
            task_widget['progress'].setValue(0)
            self.progress_bar.setValue(0)
        if all([getattr(task, '_is_running', False) for task in self.tasks]):
            self.conversion_complete()

    def conversion_complete(self):
        """Processing after completion of all conversion tasks"""
        self.toggle_ui_elements(True)
        self.progress_bar.hide()
        self.status_bar.showMessage(self.tr("Conversion completed."))
        self.tasks = []

    def validate_version(self, version: str) -> bool:
        """Verify version number format"""
        parts = version.split('.')
        return len(parts) == 4 and all(part.isdigit() for part in parts)

    def toggle_ui_elements(self, enabled: bool):
        """Enable or disable UI elements"""
        self.start_button.setEnabled(enabled and bool(self.script_paths))
        self.mode_combo.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.icon_edit.setEnabled(enabled)
        self.version_edit.setEnabled(enabled)
        self.library_edit.setEnabled(enabled)
        self.options_edit.setEnabled(enabled)
        self.drop_area.setEnabled(enabled)
        self.script_list.setEnabled(enabled)
        if enabled:
            self.cancel_button.setEnabled(False)

    def append_status(self, text: str):
        """Append status information to the log"""
        logging.info(text)
        if "<span style='color:red;'>" in text:
            self.status_text_edit.setTextColor(QColor('red'))
        else:
            self.status_text_edit.setTextColor(QColor('black'))
        self.status_text_edit.append(text)

    def update_status(self, status: str, script_path: str):
        """Update the status of a specific script"""
        self.append_status(f"[{os.path.basename(script_path)}] {status}")

    def update_progress(self, value: int, script_path: str):
        """Update the progress bar of a specific script"""
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['progress'].setValue(value)
            self.progress_bar.setValue(value)

    def show_manual(self):
        """Show instructions dialog box"""
        manual_dialog = ManualDialog(self)
        manual_dialog.exec_()

    def show_about(self):
        """Show about dialog"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def open_bilibili_link(self):
        """Open the link to support developers"""
        # webbrowser.open("https://b23.tv/Sni5cax")
        pass

    def view_log_file(self):
        """View log files"""
        log_path = os.path.abspath("app.log")
        if os.path.exists(log_path):
            log_viewer = LogViewerDialog(self, log_path)
            log_viewer.exec_()
        else:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Log file does not exist."))

    def create_task_widget(self, script_path: str) -> dict:
        """Create a task display widget"""
        widget = QFrame()
        widget.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(widget)

        script_label = QLabel(os.path.basename(script_path))
        script_label.setFixedWidth(200)
        layout.addWidget(script_label)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setFixedWidth(200)
        layout.addWidget(progress)

        status = QLabel(self.tr("Waiting..."))
        status.setWordWrap(True)
        layout.addWidget(status)

        return {'widget': widget, 'script_label': script_label, 'progress': progress, 'status': status} # , 'log': log}

    def load_settings(self):
        """Load saved settings"""
        # QSettings (This method has been removed as QSettings is no longer used)
        pass

    def save_settings(self):
        """Save current settings"""
        # QSettings (This method has been removed as QSettings is no longer used)
        pass

    def update_start_button_state(self):
        """Update the enabled state of the start button"""
        self.start_button.setEnabled(bool(self.script_paths))

    def closeEvent(self, event):
        """Processing before closing the window"""
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.tasks = []
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    translatorFileExtension = '.qm'
    # Set translator for the software
    translator = QTranslator(app)
    systemLocale = QLocale.system()
    file = os.path.join(script_dir, 'language', 'translated',
                        systemLocale.name().split('_')[0] + translatorFileExtension)
    translator.load(file)
    app.installTranslator(translator)

    # Set icon for the software
    icon_path = os.path.join(script_dir, 'Icons', 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        logging.warning(f"Icon file not found: {icon_path}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
