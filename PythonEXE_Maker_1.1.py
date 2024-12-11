import os
import sys
import subprocess
import webbrowser
from textwrap import dedent

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTextEdit, QLineEdit, QHBoxLayout, QDialog, QTextBrowser, QProgressBar, QTabWidget, QGridLayout,
    QComboBox, QGroupBox, QMenuBar, QAction, QStatusBar
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import Pillow only if available
try:
    from PIL import Image
except ImportError:
    Image = None  # Will handle installation in main


class ConvertThread(QThread):
    status_updated = pyqtSignal(str)
    conversion_finished = pyqtSignal(str, int)

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

    def run(self):
        script_dir = os.path.dirname(self.script_path)
        exe_name = self.exe_name or os.path.splitext(os.path.basename(self.script_path))[0]
        output_dir = self.output_dir or script_dir

        try:
            self.ensure_pyinstaller()
        except Exception as e:
            self.status_updated.emit(str(e))
            return

        options = self.prepare_pyinstaller_options(exe_name, output_dir)

        if self.icon_path:
            try:
                icon_file, remove_icon = self.handle_icon_conversion(script_dir)
                if icon_file:
                    options.append(f'--icon={icon_file}')
            except Exception as e:
                self.status_updated.emit(str(e))

        version_file_path = None
        if self.file_version or self.copyright_info:
            try:
                version_file_path = self.generate_version_file(exe_name, script_dir)
                options.append(f'--version-file={version_file_path}')
            except Exception as e:
                self.status_updated.emit(str(e))
                return

        self.status_updated.emit("开始转换...")
        try:
            cmd = [sys.executable, '-m', 'PyInstaller'] + options + [self.script_path]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )

            for line in iter(process.stdout.readline, ''):
                self.status_updated.emit(line.strip())

            process.stdout.close()
            process.wait()

            if process.returncode == 0:
                exe_path = os.path.join(output_dir, exe_name + '.exe')
                if os.path.exists(exe_path):
                    exe_size = os.path.getsize(exe_path) // 1024
                    self.conversion_finished.emit(exe_path, exe_size)
                else:
                    self.status_updated.emit("转换完成，但未找到生成的 EXE 文件。")
            else:
                self.status_updated.emit("转换失败，请查看上面的错误信息。")
        except Exception as e:
            self.status_updated.emit(f"转换过程中出现异常: {e}")
        finally:
            self.cleanup_files(version_file_path)

    def ensure_pyinstaller(self):
        """Ensure PyInstaller is installed."""
        try:
            subprocess.run([sys.executable, '-m', 'PyInstaller', '--version'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.status_updated.emit("检测到 PyInstaller。")
        except subprocess.CalledProcessError:
            self.status_updated.emit("未检测到 PyInstaller，正在尝试安装...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
                self.status_updated.emit("PyInstaller 安装成功。")
            except subprocess.CalledProcessError as e:
                raise Exception(f"安装 PyInstaller 失败: {e}")

    def prepare_pyinstaller_options(self, exe_name, output_dir):
        """Prepare the PyInstaller command options."""
        options = ['--onefile', '--clean']
        if self.convert_mode == "命令行模式":
            options.append('--console')
        else:
            options.append('--windowed')

        if self.extra_library:
            hidden_imports = [lib.strip() for lib in self.extra_library.split(',') if lib.strip()]
            for lib in hidden_imports:
                options.append(f'--hidden-import={lib}')

        if self.additional_options:
            options.extend(self.additional_options.strip().split())

        options.extend(['--distpath', output_dir, '-n', exe_name])
        return options

    def handle_icon_conversion(self, script_dir):
        """Handle icon conversion from PNG to ICO if necessary."""
        if not Image:
            raise Exception("Pillow 库未安装，无法转换图标。")
        
        icon_file = self.icon_path
        remove_icon = False
        if self.icon_path.lower().endswith('.png'):
            self.status_updated.emit("检测到 PNG 图标，正在转换为 ICO 格式...")
            try:
                img = Image.open(self.icon_path)
                ico_path = os.path.join(script_dir, 'icon_converted.ico')
                img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                icon_file = ico_path
                remove_icon = True
                self.status_updated.emit("图标转换成功。")
            except Exception as e:
                self.status_updated.emit(f"PNG 转 ICO 失败: {e}")
                icon_file = None
        elif self.icon_path.lower().endswith('.ico'):
            # Icon is already in ICO format
            pass
        else:
            raise Exception("不支持的图标格式，仅支持 .png 和 .ico 格式。")
        return icon_file, remove_icon

    def generate_version_file(self, exe_name, script_dir):
        """Generate the version info file for PyInstaller."""
        version_numbers = self.file_version.split('.') if self.file_version else ['1', '0', '0', '0']
        if len(version_numbers) != 4 or not all(num.isdigit() for num in version_numbers):
            version_numbers = ['1', '0', '0', '0']

        version_file_content = dedent(f"""
        VSVersionInfo(
            ffi=FixedFileInfo(
                filevers=({', '.join(version_numbers)}),
                prodvers=({', '.join(version_numbers)}),
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
                            '040904B0',
                            [
                                StringStruct('CompanyName', ''),
                                StringStruct('FileDescription', '{exe_name}'),
                                StringStruct('FileVersion', '{'.'.join(version_numbers)}'),
                                StringStruct('InternalName', '{exe_name}.exe'),
                                StringStruct('LegalCopyright', '{self.copyright_info}'),
                                StringStruct('OriginalFilename', '{exe_name}.exe'),
                                StringStruct('ProductName', '{exe_name}'),
                                StringStruct('ProductVersion', '{'.'.join(version_numbers)}')
                            ]
                        )
                    ]
                ),
                VarFileInfo([VarStruct('Translation', [0x0409, 0x04B0])])
            ]
        )
        """)
        version_file_path = os.path.join(script_dir, 'version_info.txt')
        with open(version_file_path, 'w', encoding='utf-8') as vf:
            vf.write(version_file_content)
        self.status_updated.emit("生成版本信息文件。")
        return version_file_path

    def cleanup_files(self, version_file_path):
        """Clean up temporary files."""
        script_dir = os.path.dirname(self.script_path)
        if version_file_path and os.path.exists(version_file_path):
            try:
                os.remove(version_file_path)
                self.status_updated.emit("删除版本信息文件。")
            except Exception as e:
                self.status_updated.emit(f"无法删除版本信息文件: {e}")

        if self.icon_path.lower().endswith('.png'):
            ico_path = os.path.join(script_dir, 'icon_converted.ico')
            if os.path.exists(ico_path):
                try:
                    os.remove(ico_path)
                    self.status_updated.emit("删除临时 ICO 文件。")
                except Exception as e:
                    self.status_updated.emit(f"无法删除临时 ICO 文件: {e}")


class DropArea(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText("拖入 .py 文件")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                min-height: 100px;
                font-size: 16px;
                color: #555;
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
        for url in event.mimeData().urls():
            script_path = url.toLocalFile()
            if script_path.endswith(".py"):
                self.file_dropped.emit(script_path)
                return
        QMessageBox.warning(self, "警告", "请拖放 Python 文件 (.py) 到窗口中。")


class ManualDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用手册")
        self.setFixedSize(800, 600)
        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 14))
        self.text_browser.setHtml(self.manual_text())
        layout.addWidget(self.text_browser)
        self.setLayout(layout)

    @staticmethod
    def manual_text():
        return """
        <h1>Py转EXE助手 使用手册</h1>
        <p>这是一个用于将 Python 脚本转换为可执行文件 (EXE) 的工具。以下是使用说明:</p>
        <ol>
            <li>选择转换模式: 可选择 GUI 模式或命令行模式。</li>
            <li>选择输出目录: 默认与源文件同目录, 可点击 "浏览" 按钮选择自定义输出目录。</li>
            <li>设置 EXE 信息: 输入 EXE 名称 (默认与源文件同名)、选择图标文件 (支持 .png 和 .ico)、输入文件版本和版权信息。</li>
            <li>拖入 .py 文件或点击 "浏览文件" 按钮选择要转换的 Python 文件。</li>
            <li>点击 "开始转换" 按钮开始转换。</li>
            <li>转换完成后, 生成的 EXE 文件将位于指定的输出目录下。</li>
        </ol>
        <p><strong>注意事项:</strong></p>
        <ul>
            <li>图标文件支持 .png 和 .ico 格式。</li>
            <li>如果 Python 脚本中使用了外部库或资源文件, 请确保将它们正确打包到 EXE 中。</li>
            <li>“额外模块”处可输入需要隐藏导入的模块名称，多个模块请用逗号分隔。</li>
            <li>“附加 PyInstaller 参数”处可输入自定义的 PyInstaller 命令行参数。</li>
        </ul>
        <p><em>本程序为开源免费软件, 代码已托管在 GitHub 上。如有任何问题或建议, 欢迎提出 issue 或贡献代码。</em></p>
        """


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Py转EXE助手 by 从何开始123")
        self.setGeometry(100, 100, 900, 700)
        self.setFont(QFont("Arial", 12))

        # Initialize UI
        self.init_ui()
        # Connect signals
        self.connect_signals()

        self.script_path = ""

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Menu Bar
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu('帮助')
        manual_action = QAction('使用手册', self)
        manual_action.triggered.connect(self.show_manual)
        help_menu.addAction(manual_action)

        support_action = QAction('请开发者喝咖啡', self)
        support_action.triggered.connect(self.open_bilibili_link)
        help_menu.addAction(support_action)

        main_layout.setMenuBar(menubar)

        # Tab Widget for settings
        self.tab_widget = QTabWidget()

        # Basic Settings Tab
        basic_tab = QWidget()
        basic_layout = QGridLayout()

        # Conversion Mode
        mode_label = QLabel("转换模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["GUI 模式", "命令行模式"])
        basic_layout.addWidget(mode_label, 0, 0)
        basic_layout.addWidget(self.mode_combo, 0, 1)

        # Output Directory
        output_label = QLabel("输出目录:")
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("默认与源文件同目录")
        output_button = QPushButton("浏览")
        output_button.clicked.connect(self.browse_output_dir)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_button)
        basic_layout.addWidget(output_label, 1, 0)
        basic_layout.addLayout(output_layout, 1, 1)

        # EXE Information Group
        exe_info_group = QGroupBox("EXE 信息")
        exe_info_layout = QGridLayout()

        # EXE Name
        name_label = QLabel("EXE 名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("默认与源文件同名")
        exe_info_layout.addWidget(name_label, 0, 0)
        exe_info_layout.addWidget(self.name_edit, 0, 1)

        # Icon File
        icon_label = QLabel("图标文件:")
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("可选，支持 .png 和 .ico")
        icon_button = QPushButton("浏览")
        icon_button.clicked.connect(self.browse_icon_file)
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(icon_button)
        exe_info_layout.addWidget(icon_label, 1, 0)
        exe_info_layout.addLayout(icon_layout, 1, 1)

        # File Version
        version_label = QLabel("文件版本:")
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("1.0.0.0")
        exe_info_layout.addWidget(version_label, 2, 0)
        exe_info_layout.addWidget(self.version_edit, 2, 1)

        # Copyright
        copyright_label = QLabel("版权信息:")
        self.copyright_edit = QLineEdit()
        self.copyright_edit.setPlaceholderText("可选")
        exe_info_layout.addWidget(copyright_label, 3, 0)
        exe_info_layout.addWidget(self.copyright_edit, 3, 1)

        exe_info_group.setLayout(exe_info_layout)
        basic_layout.addWidget(exe_info_group, 2, 0, 1, 2)

        # Extra Modules
        library_label = QLabel("额外模块:")
        self.library_edit = QLineEdit()
        self.library_edit.setPlaceholderText("需要隐藏导入的模块，逗号分隔")
        basic_layout.addWidget(library_label, 3, 0)
        basic_layout.addWidget(self.library_edit, 3, 1)

        # Additional PyInstaller Options
        options_label = QLabel("附加 PyInstaller 参数:")
        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("如：--add-data 'data.txt;.'")
        basic_layout.addWidget(options_label, 4, 0)
        basic_layout.addWidget(self.options_edit, 4, 1)

        basic_tab.setLayout(basic_layout)
        self.tab_widget.addTab(basic_tab, "基本设置")

        main_layout.addWidget(self.tab_widget)

        # Drag-and-Drop Area and Browse Button
        drop_browse_layout = QHBoxLayout()
        self.drop_area = DropArea(self)
        self.drop_area.file_dropped.connect(self.set_script_path)
        drop_browse_layout.addWidget(self.drop_area)

        browse_button = QPushButton("浏览文件")
        browse_button.clicked.connect(self.browse_file)
        browse_button.setFixedHeight(100)
        browse_button.setStyleSheet("QPushButton { font-size: 16px; }")
        drop_browse_layout.addWidget(browse_button)
        main_layout.addLayout(drop_browse_layout)

        # Start Conversion Button
        self.start_button = QPushButton("开始转换")
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        main_layout.addWidget(self.start_button)

        # Status Display Area
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFont(QFont("Courier New", 10))
        main_layout.addWidget(self.status_text_edit)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Status Bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def connect_signals(self):
        self.start_button.clicked.connect(self.start_conversion)

    def set_script_path(self, path):
        self.script_path = path
        self.start_button.setEnabled(True)
        self.status_text_edit.append(f"已选择脚本: {self.script_path}")
        self.status_bar.showMessage(f"已选择脚本: {self.script_path}")

    def browse_file(self):
        script_path, _ = QFileDialog.getOpenFileName(self, "选择 Python 文件", "", "Python Files (*.py)")
        if script_path:
            self.set_script_path(script_path)

    def browse_output_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if output_dir:
            self.output_edit.setText(output_dir)

    def browse_icon_file(self):
        icon_path, _ = QFileDialog.getOpenFileName(self, "选择图标文件", "", "Image Files (*.ico *.png)")
        if icon_path:
            self.icon_edit.setText(icon_path)

    def start_conversion(self):
        if not self.script_path:
            QMessageBox.warning(self, "警告", "请先选择一个 Python 脚本。")
            return

        # Gather user inputs
        convert_mode = self.mode_combo.currentText()
        output_dir = self.output_edit.text() or None
        exe_name = self.name_edit.text().strip() or None
        icon_path = self.icon_edit.text().strip() or None
        file_version = self.version_edit.text().strip() or None
        copyright_info = self.copyright_edit.text().strip()
        extra_library = self.library_edit.text().strip() or None
        additional_options = self.options_edit.text().strip() or None

        # Validate version number if provided
        if file_version:
            if not self.validate_version(file_version):
                QMessageBox.warning(self, "警告", "文件版本号格式不正确，应为 X.X.X.X (如 1.0.0.0)。")
                return

        # Disable UI elements during conversion
        self.toggle_ui_elements(False)
        self.status_text_edit.clear()
        self.status_text_edit.append("开始转换...")
        self.progress_bar.show()
        self.status_bar.showMessage("转换中...")

        # Initialize and start the conversion thread
        self.convert_thread = ConvertThread(
            script_path=self.script_path,
            convert_mode=convert_mode,
            output_dir=output_dir,
            exe_name=exe_name,
            icon_path=icon_path,
            file_version=file_version,
            copyright_info=copyright_info,
            extra_library=extra_library,
            additional_options=additional_options
        )
        self.convert_thread.status_updated.connect(self.update_status)
        self.convert_thread.conversion_finished.connect(self.conversion_finished)
        self.convert_thread.finished.connect(self.conversion_thread_finished)
        self.convert_thread.start()

    def validate_version(self, version):
        """Validate the version string format X.X.X.X."""
        parts = version.split('.')
        return len(parts) == 4 and all(part.isdigit() for part in parts)

    def toggle_ui_elements(self, enabled):
        """Enable or disable UI elements."""
        self.start_button.setEnabled(enabled and bool(self.script_path))
        self.mode_combo.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.icon_edit.setEnabled(enabled)
        self.version_edit.setEnabled(enabled)
        self.copyright_edit.setEnabled(enabled)
        self.library_edit.setEnabled(enabled)
        self.options_edit.setEnabled(enabled)
        self.drop_area.setEnabled(enabled)

    def update_status(self, status):
        self.status_text_edit.append(status)
        self.status_bar.showMessage(status)

    def conversion_finished(self, exe_path, exe_size):
        self.status_text_edit.append(f"转换成功! EXE 文件位于: {exe_path}")
        self.status_text_edit.append(f"EXE 文件大小: {exe_size} KB")
        self.status_bar.showMessage("转换成功！")
        QMessageBox.information(
            self, "提示",
            f"转换成功!\nEXE 文件位于: {exe_path}\nEXE 文件大小: {exe_size} KB"
        )

    def conversion_thread_finished(self):
        self.progress_bar.hide()
        self.toggle_ui_elements(True)

    def open_bilibili_link(self):
        webbrowser.open("https://b23.tv/Sni5cax")

    def show_manual(self):
        manual_dialog = ManualDialog(self)
        manual_dialog.exec()


def check_pillow_dependency():
    """Check if Pillow is installed; offer to install if not."""
    if Image is None:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        reply = QMessageBox.question(
            None, '缺少依赖',
            '程序需要 Pillow 库来支持 PNG 转 ICO 功能，是否立即安装？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
                QMessageBox.information(None, '成功', 'Pillow 安装成功，请重启程序。')
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(None, '安装失败', f'安装 Pillow 失败: {e}')
            sys.exit()
        else:
            QMessageBox.warning(None, '缺少依赖', '未安装 Pillow 库，程序即将退出。')
            sys.exit()


if __name__ == "__main__":
    # Check for Pillow dependency before proceeding
    check_pillow_dependency()

    app = QApplication(sys.argv)
    # 确保 'icon.png' 文件存在，否则可能需要处理异常
    if os.path.exists('icon.png'):
        app.setWindowIcon(QIcon('icon.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())