import os
import sys
import subprocess
import logging
import webbrowser
from textwrap import dedent

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTextEdit, QLineEdit, QHBoxLayout, QDialog, QTextBrowser, QProgressBar,
    QGridLayout, QComboBox, QGroupBox, QMenuBar, QAction, QStatusBar, QListWidget,
    QListWidgetItem, QSplitter, QScrollArea, QFrame, QTabWidget
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject

# 尝试导入 Pillow (Try to import Pillow)
try:
    from PIL import Image
except ImportError:
    Image = None

# 设置日志记录：将日志输出到文件和控制台 (Set up logging: output logs to file and console)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log", mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


class WorkerSignals(QObject):
    """定义Worker线程的信号 (Defining signals for Worker threads)"""
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(str, int)
    conversion_failed = pyqtSignal(str)


class ConvertRunnable(QRunnable):
    """转换任务的Runnable类 (Runnable class for conversion tasks) """
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

            self.update_status("开始转换...")
            success = self.run_pyinstaller(options)

            if success:
                exe_path = os.path.join(output_dir, exe_name + '.exe')
                if os.path.exists(exe_path):
                    exe_size = os.path.getsize(exe_path) // 1024
                    self.signals.conversion_finished.emit(exe_path, exe_size)
                    self.update_status(f"转换成功! EXE 文件位于: {exe_path} (大小: {exe_size} KB)")
                else:
                    error_message = "转换完成，但未找到生成的 EXE 文件。"
                    self.update_status(error_message)
                    self.signals.conversion_failed.emit(error_message)
            else:
                error_message = "转换失败，请查看上面的错误信息。"
                self.update_status(error_message)
                self.signals.conversion_failed.emit(error_message)
        except Exception as e:
            error_message = f"转换过程中出现异常: {e}"
            self.update_status(error_message)
            self.signals.conversion_failed.emit(error_message)
        finally:
            self.cleanup_files(version_file_path)

    def stop(self):
        """停止转换任务。 (Stop the conversion task) """
        self._is_running = False

    def update_status(self, message: str):
        """更新转换状态 (Update conversion status) """
        logging.info(message)
        self.signals.status_updated.emit(message)

    def ensure_pyinstaller(self) -> bool:
        """确保PyInstaller已安装 (Make sure PyInstaller is installed) """
        try:
            subprocess.run([sys.executable, '-m', 'PyInstaller', '--version'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_status("已检测到 PyInstaller。")
            return True
        except subprocess.CalledProcessError:
            self.update_status("未检测到 PyInstaller，正在尝试安装...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
                self.update_status("PyInstaller 安装成功。")
                return True
            except subprocess.CalledProcessError as e:
                self.update_status(f"安装 PyInstaller 失败: {e}")
                return False

    def prepare_pyinstaller_options(self, exe_name: str, output_dir: str) -> list:
        """准备PyInstaller的命令行选项 (Prepare command line options for PyInstaller) """
        options = ['--onefile', '--clean']
        options.append('--console' if self.convert_mode == "命令行模式" else '--windowed')

        if self.extra_library:
            hidden_imports = [lib.strip() for lib in self.extra_library.split(',') if lib.strip()]
            options += [f'--hidden-import={lib}' for lib in hidden_imports]

        if self.additional_options:
            options += self.additional_options.strip().split()

        options += ['--distpath', output_dir, '-n', exe_name]
        return options

    def handle_icon(self, script_dir: str) -> str:
        """处理图标文件，支持将PNG转换为ICO (Process icon files, support converting PNG to ICO) """
        if not Image:
            self.update_status("Pillow 库未安装，无法转换 PNG 图标。请安装 Pillow 或使用 ICO 图标。")
            return ""

        lower_icon = self.icon_path.lower()
        if lower_icon.endswith('.png'):
            self.update_status("检测到 PNG 图标，正在转换为 ICO 格式...")
            try:
                img = Image.open(self.icon_path)
                ico_path = os.path.join(script_dir, 'icon_converted.ico')
                img.save(ico_path, format='ICO',
                         sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                self.update_status("图标转换成功。")
                return ico_path
            except Exception as e:
                self.update_status(f"PNG 转 ICO 失败: {e}")
                return ""
        elif lower_icon.endswith('.ico'):
            return self.icon_path
        else:
            self.update_status("不支持的图标格式，仅支持 .png 和 .ico 格式。")
            return ""

    def create_version_file(self, exe_name: str, script_dir: str) -> str:
        """创建版本信息文件 (Create version information file)"""
        try:
            from PyInstaller.utils.win32.versionfile import (
                VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
            )
        except ImportError as e:
            self.update_status(f"导入版本信息类失败: {e}")
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
            self.update_status("生成版本信息文件。")
            return version_file_path
        except Exception as e:
            self.update_status(f"版本信息文件生成失败: {e}")
            return ""

    def run_pyinstaller(self, options: list) -> bool:
        """运行PyInstaller进行转换 (Run PyInstaller to convert) """
        cmd = [sys.executable, '-m', 'PyInstaller'] + options + [self.script_path]
        self.update_status(f"执行命令: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )

            for line in process.stdout:
                if not self._is_running:
                    process.terminate()
                    self.update_status("转换已被用户取消。")
                    return False
                line = line.strip()
                self.update_status(line)
                # 简单的进度估计 (Simple progress estimate)
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
            self.update_status(f"转换过程中出现异常: {e}")
            return False

    def cleanup_files(self, version_file_path: str):
        """清理临时文件 (Clean temporary files)"""
        script_dir = os.path.dirname(self.script_path)
        if version_file_path and os.path.exists(version_file_path):
            try:
                os.remove(version_file_path)
                self.update_status("删除版本信息文件。")
            except Exception as e:
                self.update_status(f"无法删除版本信息文件: {e}")

        if self.icon_path and self.icon_path.lower().endswith('.png'):
            ico_path = os.path.join(script_dir, 'icon_converted.ico')
            if os.path.exists(ico_path):
                try:
                    os.remove(ico_path)
                    self.update_status("删除临时 ICO 文件。")
                except Exception as e:
                    self.update_status(f"无法删除临时 ICO 文件: {e}")


class DropArea(QLabel):
    """拖放区域，允许用户拖入.py文件 (Drag and drop area, allowing users to drag in .py files) """
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText("拖入 .py 文件")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                min-height: 80px;
                font-size: 14px;
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
            QMessageBox.warning(self, "警告", "请拖放 Python 文件 (.py) 到窗口中。")


class ManualDialog(QDialog):
    """使用说明对话框 (Instructions dialog box) """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")
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
        <h1>PythonEXE Maker 使用说明</h1>
        <p>本程序用于将 Python 脚本转换为可执行文件 (EXE)。以下是使用步骤：</p>
        <ol>
            <li>在左侧面板中配置转换模式、输出目录、EXE 信息和其它参数。</li>
            <li>在右侧“任务管理”选项卡中，通过拖拽或浏览文件添加 Python 脚本。</li>
            <li>点击 “开始转换” 按钮开始转换，如需中途取消可点击“取消转换”。</li>
            <li>转换进度及日志可在“日志”选项卡中查看。</li>
        </ol>
        <p><strong>注意事项:</strong></p>
        <ul>
            <li>图标文件支持 .png 和 .ico 格式 (.png 将自动转换为 .ico)。</li>
            <li>如 Python 脚本使用了外部库或资源文件，请确保在“额外模块”或“附加参数”中正确指定。</li>
            <li>“额外模块”处可输入需要隐藏导入的模块名称（多个用逗号分隔）。</li>
            <li>“附加参数”可输入 PyInstaller 的其它命令行参数。</li>
        </ul>
        <p><strong>更多信息:</strong></p>
        <ul>
            <li><a href="https://github.com/yeahhe365/PythonEXE_Maker">GitHub 项目地址</a></li>
            <li><a href="https://www.yeahhe.online/">官方网站</a></li>
            <li><a href="https://www.linuxdo.com/users/yeahhe">LINUXDO 论坛主页</a></li>
        </ul>
        """


class AboutDialog(QDialog):
    """关于对话框 (About dialog box) """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 PythonEXE Maker")
        self.setFixedSize(600, 400)
        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 12))
        
        # 获取脚本所在目录 (Get the directory where the script is located)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, 'Icons', 'logo.png')
        
        if os.path.exists(logo_path):
            # 使用文件URL嵌入图片 (Embed image using file URL)
            logo_url = 'file://' + logo_path.replace('\\', '/')
            logo_html = f'<img src="{logo_url}" alt="Logo" width="200"><br>'
        else:
            logo_html = ''
        
        self.text_browser.setHtml(logo_html + self.about_text())
        layout.addWidget(self.text_browser)
        self.setLayout(layout)

    def about_text(self):
        return """
        <h1>关于 PythonEXE Maker</h1>
        <p>版本：1.1.0</p>
        <p>作者：yeahhe365</p>
        <p>这是一个开源免费工具，用于将 Python 脚本转换为可执行文件。</p>
        <p>如有问题或建议，欢迎在 GitHub 提交 issue 或查看源代码：</p>
        <p><a href="https://github.com/yeahhe365/PythonEXE_Maker">https://github.com/yeahhe365/PythonEXE_Maker</a></p>
        <p><strong>感谢您的使用与支持！</strong></p>
        """


class LogViewerDialog(QDialog):
    """日志查看对话框 (Log viewing dialog box) """
    def __init__(self, parent=None, log_path="app.log"):
        super().__init__(parent)
        self.setWindowTitle("查看日志文件")
        self.setFixedSize(800, 600)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.load_log(log_path)

    def load_log(self, log_path):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
            except Exception as e:
                self.text_edit.setPlainText(f"无法读取日志文件: {e}")
        else:
            self.text_edit.setPlainText("日志文件不存在。")


class MainWindow(QMainWindow):
    """主窗口 (Main window) """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PythonEXE Maker")
        self.setGeometry(100, 100, 1300, 900)
        self.setFont(QFont("Arial", 11))

        self.script_paths = []
        self.thread_pool = QThreadPool()
        self.tasks = []
        self.task_widgets = {}

        self.init_ui()
        self.update_start_button_state()
        self.connect_signals()

    def init_ui(self):
        # 创建中央部件 (Create central widget)
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 菜单栏 (Menu bar)
        self.init_menu()

        splitter = QSplitter(Qt.Horizontal)

        # 左侧设置与操作区 (Settings and operation area on the left)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.init_settings_group())
        left_layout.addLayout(self.init_button_group())
        splitter.addWidget(left_widget)

        # 右侧标签页 (任务管理、日志) (Right tab (task management, log))
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # "任务管理"选项卡 ("Task Management" tab)
        task_tab = QWidget()
        task_tab_layout = QVBoxLayout(task_tab)

        # 脚本管理区 (Script management area)
        script_group = QGroupBox("脚本管理")
        script_layout = QVBoxLayout()

        # 拖拽区与浏览按钮 (Drag area and browse button)
        drop_browse_layout = QHBoxLayout()
        self.drop_area = DropArea(self)
        self.drop_area.file_dropped.connect(self.add_script_path)
        drop_browse_layout.addWidget(self.drop_area)

        browse_button = QPushButton("浏览文件")
        browse_button.setToolTip("点击选择要转换的 Python 文件，可多选。")
        browse_button.clicked.connect(self.browse_files)
        browse_button.setFixedHeight(80)
        browse_button.setStyleSheet("QPushButton { font-size: 14px; }")
        drop_browse_layout.addWidget(browse_button)

        script_layout.addLayout(drop_browse_layout)

        # 脚本列表 (Script list)
        self.script_list = QListWidget()
        self.script_list.setToolTip("已选择的 Python 脚本列表，双击可移除。")
        self.script_list.itemDoubleClicked.connect(self.remove_script)
        script_layout.addWidget(self.script_list)

        script_group.setLayout(script_layout)
        task_tab_layout.addWidget(script_group)

        # 任务进度区域 (Task progress area)
        task_progress_group = QGroupBox("转换任务进度")
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

        self.tab_widget.addTab(task_tab, "任务管理")

        # "日志"选项卡 ("Log" tab)
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)

        # 日志文本 (Log text)
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFont(QFont("Courier New", 10))
        log_tab_layout.addWidget(self.status_text_edit)

        # 全局进度条 (Global progress bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        log_tab_layout.addWidget(self.progress_bar)

        # 状态栏 (Status bar)
        self.status_bar = QStatusBar()
        log_tab_layout.addWidget(self.status_bar)

        self.tab_widget.addTab(log_tab, "日志")

        splitter.addWidget(self.tab_widget)
        splitter.setSizes([500, 800])

        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

        # 设置程序窗口图标 (Set program window icon)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'Icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(f"图标文件未找到: {icon_path}")

    def init_menu(self):
        menubar = self.menuBar()

        # 文件菜单 (File menu)
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单 (Help menu)
        help_menu = menubar.addMenu('帮助')
        manual_action = QAction('使用说明', self)
        manual_action.triggered.connect(self.show_manual)
        help_menu.addAction(manual_action)

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        github_action = QAction('开源地址', self)
        github_action.triggered.connect(lambda: webbrowser.open("https://github.com/yeahhe365/PythonEXE_Maker"))
        help_menu.addAction(github_action)

        website_action = QAction('官方网站', self)
        website_action.triggered.connect(lambda: webbrowser.open("https://www.yeahhe.online/"))
        help_menu.addAction(website_action)

        forum_action = QAction('LINUXDO 论坛主页', self)
        forum_action.triggered.connect(lambda: webbrowser.open("https://www.linuxdo.com/users/yeahhe"))
        help_menu.addAction(forum_action)

        support_action = QAction('请开发者喝咖啡', self)
        support_action.triggered.connect(self.open_bilibili_link)
        help_menu.addAction(support_action)

        # 日志菜单 (Log menu)
        log_menu = menubar.addMenu('日志')
        view_log_action = QAction('查看日志文件', self)
        view_log_action.triggered.connect(self.view_log_file)
        log_menu.addAction(view_log_action)

    def init_settings_group(self) -> QGroupBox:
        """初始化基本设置、EXE信息和高级设置的组 (Initialize the group of basic settings, EXE information and advanced settings) """
        settings_group = QGroupBox("基本设置")
        settings_layout = QGridLayout()

        # 转换模式 (Conversion mode)
        mode_label = QLabel("转换模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["GUI 模式", "命令行模式"])
        self.mode_combo.setToolTip("选择生成的 EXE 是带控制台（命令行模式）还是不带控制台（GUI 模式）。")
        settings_layout.addWidget(mode_label, 0, 0)
        settings_layout.addWidget(self.mode_combo, 0, 1)

        # 输出目录 (Output directory)
        output_label = QLabel("输出目录:")
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("默认与源文件同目录")
        self.output_edit.setToolTip("设置生成 EXE 文件的输出目录。为空则默认放在源文件同目录下。")
        output_button = QPushButton("浏览")
        output_button.setToolTip("选择输出目录。")
        output_button.clicked.connect(self.browse_output_dir)
        output_h_layout = QHBoxLayout()
        output_h_layout.addWidget(self.output_edit)
        output_h_layout.addWidget(output_button)
        settings_layout.addWidget(output_label, 1, 0)
        settings_layout.addLayout(output_h_layout, 1, 1)

        # EXE 信息 (EXE information)
        exe_info_group = QGroupBox("EXE 信息")
        exe_info_layout = QGridLayout()

        name_label = QLabel("EXE 名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("默认与源文件同名")
        self.name_edit.setToolTip("设置生成的 EXE 文件名称。")
        exe_info_layout.addWidget(name_label, 0, 0)
        exe_info_layout.addWidget(self.name_edit, 0, 1)

        icon_label = QLabel("图标文件:")
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("可选，支持 .png 和 .ico")
        self.icon_edit.setToolTip("选择一个图标文件用于 EXE。若为 PNG，将自动转换为 ICO。")
        icon_button = QPushButton("浏览")
        icon_button.setToolTip("选择图标文件。")
        icon_button.clicked.connect(self.browse_icon_file)
        icon_h_layout = QHBoxLayout()
        icon_h_layout.addWidget(self.icon_edit)
        icon_h_layout.addWidget(icon_button)
        exe_info_layout.addWidget(icon_label, 1, 0)
        exe_info_layout.addLayout(icon_h_layout, 1, 1)

        version_label = QLabel("文件版本:")
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("1.0.0.0")
        self.version_edit.setToolTip("设置 EXE 文件的版本号（X.X.X.X）。")
        exe_info_layout.addWidget(version_label, 2, 0)
        exe_info_layout.addWidget(self.version_edit, 2, 1)

        copyright_label = QLabel("版权信息:")
        self.copyright_edit = QLineEdit()
        self.copyright_edit.setToolTip("设置 EXE 文件的版权信息。")
        exe_info_layout.addWidget(copyright_label, 3, 0)
        exe_info_layout.addWidget(self.copyright_edit, 3, 1)

        exe_info_group.setLayout(exe_info_layout)
        settings_layout.addWidget(exe_info_group, 2, 0, 1, 2)

        # 高级设置 (Advanced settings)
        advanced_settings_group = QGroupBox("高级设置")
        advanced_settings_layout = QGridLayout()

        # 额外模块 (Extra modules)
        library_label = QLabel("额外模块:")
        self.library_edit = QLineEdit()
        self.library_edit.setPlaceholderText("隐藏导入的模块，逗号分隔")
        self.library_edit.setToolTip("输入需要隐藏导入的模块名称（多个用逗号分隔）。")
        advanced_settings_layout.addWidget(library_label, 0, 0)
        advanced_settings_layout.addWidget(self.library_edit, 0, 1)

        # 附加参数 (Additional arguments)
        options_label = QLabel("附加参数:")
        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("例如：--add-data 'data.txt;.'")
        self.options_edit.setToolTip("输入自定义的 PyInstaller 参数。")
        advanced_settings_layout.addWidget(options_label, 1, 0)
        advanced_settings_layout.addWidget(self.options_edit, 1, 1)

        advanced_settings_group.setLayout(advanced_settings_layout)
        settings_layout.addWidget(advanced_settings_group, 3, 0, 1, 2)

        settings_group.setLayout(settings_layout)
        return settings_group

    def init_button_group(self) -> QHBoxLayout:
        """初始化开始和取消转换按钮 (Initialize start and cancel conversion buttons) """
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("开始转换")
        self.start_button.setEnabled(False)
        self.start_button.setToolTip("开始将所选 Python 脚本转换为 EXE。")
        self.start_button.setStyleSheet("QPushButton { font-size: 14px; padding: 6px; }")
        self.start_button.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("取消转换")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip("取消正在进行的转换任务。")
        self.cancel_button.setStyleSheet("QPushButton { font-size: 14px; padding: 6px; }")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        button_layout.addWidget(self.cancel_button)

        return button_layout

    def connect_signals(self):
        """连接必要的信号 (Connect necessary signals) """
        pass

    def add_script_path(self, path: str):
        """添加脚本路径到列表中 (Add script path to list) """
        if path not in self.script_paths:
            self.script_paths.append(path)
            self.script_list.addItem(QListWidgetItem(path))
            self.append_status(f"已添加脚本: {path}")
            self.update_start_button_state()

    def browse_files(self):
        """浏览并添加Python脚本文件 (Browse and add the Python script file) """
        script_paths, _ = QFileDialog.getOpenFileNames(self, "选择 Python 文件", "", "Python Files (*.py)")
        if script_paths:
            added = False
            for script_path in script_paths:
                if script_path not in self.script_paths:
                    self.script_paths.append(script_path)
                    self.script_list.addItem(QListWidgetItem(script_path))
                    self.append_status(f"已添加脚本: {script_path}")
                    added = True
            if added:
                self.update_start_button_state()

    def browse_output_dir(self):
        """浏览并设置输出目录 (Browse and set the output directory) """
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if output_dir:
            self.output_edit.setText(output_dir)

    def browse_icon_file(self):
        """浏览并设置图标文件 (Browse and set the icon file) """
        icon_path, _ = QFileDialog.getOpenFileName(self, "选择图标文件", "", "Image Files (*.ico *.png)")
        if icon_path:
            self.icon_edit.setText(icon_path)

    def remove_script(self, item: QListWidgetItem):
        """移除脚本 (Remove script) """
        path = item.text()
        if path in self.script_paths:
            self.script_paths.remove(path)
            self.script_list.takeItem(self.script_list.row(item))
            self.append_status(f"已移除脚本: {path}")
            self.update_start_button_state()

    def start_conversion(self):
        """开始转换所有选中的脚本 (Start converting all selected scripts) """
        if not self.script_paths:
            QMessageBox.warning(self, "警告", "请先选择至少一个 Python 脚本。")
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
            QMessageBox.warning(self, "警告", "文件版本号格式不正确，应为 X.X.X.X (如 1.0.0.0)。")
            return

        self.toggle_ui_elements(False)
        self.status_text_edit.clear()
        self.append_status("开始转换...")
        self.progress_bar.show()
        self.status_bar.showMessage("转换中...")

        self.tasks = []
        self.task_widgets = {}
        # 清空任务进度显示区域 (Clear the task progress display area)
        for i in reversed(range(self.task_layout.count())):
            w = self.task_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        for script_path in self.script_paths:
            task_widget = self.create_task_widget(script_path)
            self.task_layout.addWidget(task_widget['widget'])
            self.task_widgets[script_path] = task_widget

            runnable = ConvertRunnable(
                script_path=script_path,
                convert_mode=convert_mode,
                output_dir=output_dir,
                exe_name=exe_name,
                icon_path=icon_path,
                file_version=file_version,
                copyright_info=copyright_info,
                extra_library=extra_library,
                additional_options=additional_options
            )
            runnable.signals.status_updated.connect(
                lambda msg, sp=script_path: self.update_status(msg, sp)
            )
            runnable.signals.progress_updated.connect(
                lambda val, sp=script_path: self.update_progress(val, sp)
            )
            runnable.signals.conversion_finished.connect(
                lambda exe, size, sp=script_path: self.conversion_finished(exe, size, sp)
            )
            runnable.signals.conversion_failed.connect(
                lambda err, sp=script_path: self.conversion_failed(err, sp)
            )
            self.thread_pool.start(runnable)
            self.tasks.append(runnable)

        self.cancel_button.setEnabled(True)

    def cancel_conversion(self):
        """取消所有正在进行的转换任务 (Cancel all ongoing conversion tasks) """
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.append_status("已请求取消转换任务。")
            self.status_bar.showMessage("取消转换...")
            self.cancel_button.setEnabled(False)

    def conversion_finished(self, exe_path: str, exe_size: int, script_path: str):
        """处理转换完成的情况 (Handle conversion completion) """
        self.append_status(f"转换成功! EXE 文件位于: {exe_path} (大小: {exe_size} KB)")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(f"转换成功! 文件: {exe_path} ({exe_size} KB)")
            task_widget['progress'].setValue(100)
        if all(not getattr(task, '_is_running', False) for task in self.tasks):
            self.conversion_complete()

    def conversion_failed(self, error_message: str, script_path: str):
        """处理转换失败的情况 (Handling conversion failure situations) """
        self.append_status(f"<span style='color:red;'>{error_message}</span>")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(f"<span style='color:red;'>{error_message}</span>")
            task_widget['progress'].setValue(0)
        if all(not getattr(task, '_is_running', False) for task in self.tasks):
            self.conversion_complete()

    def conversion_complete(self):
        """所有转换任务完成后的处理 (Processing after completion of all conversion tasks) """
        self.toggle_ui_elements(True)
        self.progress_bar.hide()
        self.status_bar.showMessage("转换完成。")
        self.tasks = []

    def validate_version(self, version: str) -> bool:
        """验证版本号格式 (Verify version number format) """
        parts = version.split('.')
        return len(parts) == 4 and all(part.isdigit() for part in parts)

    def toggle_ui_elements(self, enabled: bool):
        """启用或禁用UI元素 (Enable or disable UI elements) """
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
        """在日志中追加状态信息 (Append status information to the log) """
        logging.info(text)
        if "<span style='color:red;'>" in text:
            self.status_text_edit.setTextColor(QColor('red'))
        else:
            self.status_text_edit.setTextColor(QColor('black'))
        self.status_text_edit.append(text)
        self.status_bar.showMessage(text)

    def update_status(self, status: str, script_path: str):
        """更新特定脚本的状态 (Update the status of a specific script) """
        self.append_status(f"[{os.path.basename(script_path)}] {status}")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['log'].append(status)

    def update_progress(self, value: int, script_path: str):
        """更新特定脚本的进度条 (Update the progress bar of a specific script) """
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['progress'].setValue(value)

    def show_manual(self):
        """显示使用说明对话框 (Show instructions dialog box) """
        manual_dialog = ManualDialog(self)
        manual_dialog.exec_()

    def show_about(self):
        """显示关于对话框 (Show about dialog) """
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def open_bilibili_link(self):
        """打开支持开发者的链接 (Open the link to support developers) """
        webbrowser.open("https://b23.tv/Sni5cax")

    def view_log_file(self):
        """查看日志文件 (View log files) """
        log_path = os.path.abspath("app.log")
        if os.path.exists(log_path):
            log_viewer = LogViewerDialog(self, log_path)
            log_viewer.exec_()
        else:
            QMessageBox.warning(self, "警告", "日志文件不存在。")

    def create_task_widget(self, script_path: str) -> dict:
        """创建一个任务的显示小部件 (Create a task display widget) """
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

        status = QLabel("等待中...")
        status.setWordWrap(True)
        layout.addWidget(status)

        log = QTextEdit()
        log.setReadOnly(True)
        log.setFont(QFont("Courier New", 10))
        log.setFixedHeight(50)
        log.setToolTip("本任务的转换日志片段")
        layout.addWidget(log)

        return {'widget': widget, 'script_label': script_label, 'progress': progress, 'status': status, 'log': log}

    def load_settings(self):
        """加载保存的设置 (Load saved settings) """
        # 此方法已被移除，因为不再使用 QSettings (This method has been removed as QSettings is no longer used)
        pass

    def save_settings(self):
        """保存当前设置 (Save current settings)"""
        # 此方法已被移除，因为不再使用 QSettings (This method has been removed as QSettings is no longer used)
        pass

    def update_start_button_state(self):
        """更新开始按钮的启用状态 (Update the enabled state of the start button) """
        self.start_button.setEnabled(bool(self.script_paths))

    def closeEvent(self, event):
        """关闭窗口前的处理 (Processing before closing the window) """
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.tasks = []
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'Icons', 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        logging.warning(f"图标文件未找到: {icon_path}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())