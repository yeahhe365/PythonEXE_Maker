import os
import sys
import subprocess
import logging
import webbrowser

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTextEdit, QLineEdit,
    QDialog, QProgressBar, QGroupBox, QMenuBar, QAction, QStatusBar, QListWidget,
    QListWidgetItem, QSplitter, QScrollArea, QFrame, QTabWidget, QComboBox
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QThreadPool, QSize

# 引入我们在其它模块里定义的类和函数 (假设本地已有)
from converters import ConvertRunnable
from dialogs import ManualDialog, AboutDialog, LogViewerDialog
from widgets import DropArea

# ======= 日志配置 =======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log", mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


class MainWindow(QMainWindow):
    """主窗口：包含主要的UI和逻辑"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PythonEXE Maker")
        self.setGeometry(100, 100, 1300, 900)
        self.setFont(QFont("Arial", 11))

        # 存放脚本路径
        self.script_paths = []
        # 线程池
        self.thread_pool = QThreadPool()
        # 转换任务列表
        self.tasks = []
        # 每个脚本对应的任务UI元素
        self.task_widgets = {}

        # 在此属性中存储“附加文件”的路径
        self.extra_file_path = None

        # 初始化UI
        self.init_ui()
        # 应用全局样式表(若需要美化UI，可在这里调用 self.apply_global_stylesheet())
        # self.apply_global_stylesheet()

        # 检查并更新“开始转换”按钮的可用状态
        self.update_start_button_state()

    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # ============ 菜单栏 ============
        self.init_menu()

        # ============ 左右分割（QSplitter） ============
        splitter = QSplitter(Qt.Horizontal)

        # -------- 左侧设置区域 --------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.init_settings_group())
        left_layout.addLayout(self.init_button_group())
        splitter.addWidget(left_widget)

        # -------- 右侧Tab标签页（任务管理、日志） --------
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # 1) “任务管理”选项卡
        task_tab = QWidget()
        task_tab_layout = QVBoxLayout(task_tab)

        # ------ 脚本管理区 ------
        script_group = QGroupBox("脚本管理")
        script_layout = QVBoxLayout()

        # 拖拽区与“浏览文件”按钮
        drop_browse_layout = QHBoxLayout()
        self.drop_area = DropArea(self)  # 自定义拖拽控件（在 widgets.py 中）
        self.drop_area.file_dropped.connect(self.add_script_path)
        drop_browse_layout.addWidget(self.drop_area)

        browse_button = QPushButton("浏览文件")
        browse_button.setToolTip("点击选择要转换的 Python 文件，可多选。")
        # 如果有 Material Icon，可在此设置 browse_button.setIcon(...)
        browse_button.setFixedHeight(60)
        browse_button.clicked.connect(self.browse_files)
        drop_browse_layout.addWidget(browse_button)

        script_layout.addLayout(drop_browse_layout)

        # 脚本列表
        self.script_list = QListWidget()
        self.script_list.setToolTip("已选择的 Python 脚本列表，双击可移除。")
        self.script_list.itemDoubleClicked.connect(self.remove_script)
        script_layout.addWidget(self.script_list)

        script_group.setLayout(script_layout)
        task_tab_layout.addWidget(script_group)

        # ------ 任务进度区域 ------
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

        # 2) “日志”选项卡
        log_tab = QWidget()
        log_tab_layout = QVBoxLayout(log_tab)

        self.status_text_edit = QTextEdit()
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setFont(QFont("Courier New", 10))
        log_tab_layout.addWidget(self.status_text_edit)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        log_tab_layout.addWidget(self.progress_bar)

        self.status_bar = QStatusBar()
        log_tab_layout.addWidget(self.status_bar)

        self.tab_widget.addTab(log_tab, "日志")

        splitter.addWidget(self.tab_widget)
        splitter.setSizes([500, 800])

        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

        # 设置窗口图标(如有需要)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(f"图标文件未找到: {icon_path}")

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
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

        # 日志菜单
        log_menu = menubar.addMenu('日志')
        view_log_action = QAction('查看日志文件', self)
        view_log_action.triggered.connect(self.view_log_file)
        log_menu.addAction(view_log_action)

    def init_settings_group(self) -> QGroupBox:
        """初始化基本设置、EXE信息和高级设置的组"""
        settings_group = QGroupBox("基本设置")
        settings_layout = QGridLayout()

        # 转换模式
        mode_label = QLabel("转换模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["GUI 模式", "命令行模式"])
        self.mode_combo.setToolTip("选择生成的 EXE 是带控制台（命令行模式）还是不带控制台（GUI 模式）。")
        settings_layout.addWidget(mode_label, 0, 0)
        settings_layout.addWidget(self.mode_combo, 0, 1)

        # 输出目录
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

        # EXE 信息
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

        # 高级设置
        advanced_settings_group = QGroupBox("高级设置")
        advanced_settings_layout = QGridLayout()

        # 额外模块
        library_label = QLabel("额外模块:")
        self.library_edit = QLineEdit()
        self.library_edit.setPlaceholderText("隐藏导入的模块，逗号分隔")
        self.library_edit.setToolTip("输入需要隐藏导入的模块名称（多个用逗号分隔）。")
        advanced_settings_layout.addWidget(library_label, 0, 0)
        advanced_settings_layout.addWidget(self.library_edit, 0, 1)

        # 用按钮来选择需要打包的“附加文件”
        extra_file_label = QLabel("附加文件:")
        self.select_file_button = QPushButton("选择文件")
        self.select_file_button.setToolTip("点击选择一个要与脚本一起打包的文件。将自动生成 --add-data 参数。")
        self.select_file_button.clicked.connect(self.choose_extra_file)

        advanced_settings_layout.addWidget(extra_file_label, 1, 0)
        advanced_settings_layout.addWidget(self.select_file_button, 1, 1)

        advanced_settings_group.setLayout(advanced_settings_layout)
        settings_layout.addWidget(advanced_settings_group, 3, 0, 1, 2)

        settings_group.setLayout(settings_layout)
        return settings_group

    def init_button_group(self) -> QHBoxLayout:
        """初始化【开始转换】【取消转换】按钮"""
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("开始转换")
        self.start_button.setEnabled(False)
        self.start_button.setToolTip("开始将所选 Python 脚本转换为 EXE。")
        self.start_button.clicked.connect(self.start_conversion)

        self.cancel_button = QPushButton("取消转换")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip("取消正在进行的转换任务。")
        self.cancel_button.clicked.connect(self.cancel_conversion)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        return button_layout

    def add_script_path(self, path: str):
        """添加脚本路径到列表中"""
        if path not in self.script_paths:
            self.script_paths.append(path)
            self.script_list.addItem(QListWidgetItem(path))
            self.append_status(f"已添加脚本: {path}")
            self.update_start_button_state()

    def browse_files(self):
        """浏览并添加 Python 脚本文件"""
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

    def remove_script(self, item: QListWidgetItem):
        """移除选中的脚本路径"""
        path = item.text()
        if path in self.script_paths:
            self.script_paths.remove(path)
            self.script_list.takeItem(self.script_list.row(item))
            self.append_status(f"已移除脚本: {path}")
            self.update_start_button_state()

    def update_start_button_state(self):
        """根据是否有脚本，更新“开始转换”按钮状态"""
        self.start_button.setEnabled(bool(self.script_paths))

    def browse_output_dir(self):
        """浏览并设置输出目录"""
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if output_dir:
            self.output_edit.setText(output_dir)

    def browse_icon_file(self):
        """浏览并设置图标文件"""
        icon_path, _ = QFileDialog.getOpenFileName(self, "选择图标文件", "", "Image Files (*.ico *.png)")
        if icon_path:
            self.icon_edit.setText(icon_path)

    def choose_extra_file(self):
        """选择附加文件并保存路径"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择附加文件", "", "所有文件 (*.*)")
        if file_path:
            self.extra_file_path = file_path
            self.append_status(f"已选择附加文件: {file_path}")

    def start_conversion(self):
        """开始转换所有选中的脚本"""
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

        # 如果文件版本号不为空，但格式不正确，则提示
        if file_version and not self.validate_version(file_version):
            QMessageBox.warning(self, "警告", "文件版本号格式不正确，应为 X.X.X.X (如 1.0.0.0)。")
            return

        # -------------------
        # 关键修复：去掉额外引号，并使用 --add-data=SRC;DEST (Windows) / SRC:DEST (其他)
        # -------------------
        additional_options = None
        if self.extra_file_path:
            separator = ';' if os.name == 'nt' else ':'
            # 不要外层的引号，避免 PyInstaller 解析出错
            additional_options = f'--add-data={self.extra_file_path}{separator}.'

        # 禁用相关UI
        self.toggle_ui_elements(False)
        # 清空日志
        self.status_text_edit.clear()
        self.append_status("开始转换...")
        self.progress_bar.show()
        self.status_bar.showMessage("转换中...")

        self.tasks = []
        self.task_widgets = {}

        # 清空任务进度区域
        for i in reversed(range(self.task_layout.count())):
            w = self.task_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        # 为每个脚本创建转换任务
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
            # 信号连接：把脚本路径一起传过去以区分不同任务
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
        """取消所有正在进行的转换任务"""
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.append_status("已请求取消转换任务。")
            self.status_bar.showMessage("取消转换...")
            self.cancel_button.setEnabled(False)
            # 因为主动取消，这里直接调用 conversion_complete 来恢复UI
            self.conversion_complete()

    def conversion_finished(self, exe_path: str, exe_size: int, script_path: str):
        """处理单个脚本转换完成的情况"""
        self.append_status(f"转换成功! EXE 文件位于: {exe_path} (大小: {exe_size} KB)")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(f"转换成功! 文件: {exe_path} ({exe_size} KB)")
            task_widget['progress'].setValue(100)
        # 若所有任务都结束，则执行收尾
        if all(not getattr(task, '_is_running', False) for task in self.tasks):
            self.conversion_complete()

    def conversion_failed(self, error_message: str, script_path: str):
        """处理单个脚本转换失败的情况"""
        self.append_status(f"<span style='color:red;'>{error_message}</span>")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['status'].setText(f"<span style='color:red;'>{error_message}</span>")
            task_widget['progress'].setValue(0)
        # 若所有任务都结束，则执行收尾
        if all(not getattr(task, '_is_running', False) for task in self.tasks):
            self.conversion_complete()

    def conversion_complete(self):
        """所有转换任务完成或取消后的处理"""
        self.toggle_ui_elements(True)
        self.progress_bar.hide()
        self.status_bar.showMessage("转换完成。")
        self.tasks = []

    def validate_version(self, version: str) -> bool:
        """验证版本号格式 (X.X.X.X)"""
        parts = version.split('.')
        return len(parts) == 4 and all(part.isdigit() for part in parts)

    def toggle_ui_elements(self, enabled: bool):
        """启用或禁用与任务相关的 UI"""
        self.start_button.setEnabled(enabled and bool(self.script_paths))
        self.mode_combo.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.icon_edit.setEnabled(enabled)
        self.version_edit.setEnabled(enabled)
        self.library_edit.setEnabled(enabled)
        self.drop_area.setEnabled(enabled)
        self.script_list.setEnabled(enabled)
        self.select_file_button.setEnabled(enabled)
        if enabled:
            self.cancel_button.setEnabled(False)

    def append_status(self, text: str):
        """在日志文本框中追加状态信息，并更新状态栏"""
        logging.info(text)
        if "<span style='color:red;'>" in text:
            self.status_text_edit.setTextColor(QColor('red'))
        else:
            self.status_text_edit.setTextColor(QColor('black'))
        self.status_text_edit.append(text)
        self.status_bar.showMessage(text)

    def update_status(self, status: str, script_path: str):
        """更新特定脚本的状态"""
        self.append_status(f"[{os.path.basename(script_path)}] {status}")
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['log'].append(status)

    def update_progress(self, value: int, script_path: str):
        """更新特定脚本的进度条"""
        task_widget = self.task_widgets.get(script_path)
        if task_widget:
            task_widget['progress'].setValue(value)

    def show_manual(self):
        """显示“使用说明”对话框"""
        manual_dialog = ManualDialog(self)
        manual_dialog.exec_()

    def show_about(self):
        """显示“关于”对话框"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def open_bilibili_link(self):
        """打开支持开发者的链接"""
        webbrowser.open("https://b23.tv/Sni5cax")

    def view_log_file(self):
        """查看日志文件"""
        log_path = os.path.abspath("app.log")
        if os.path.exists(log_path):
            log_viewer = LogViewerDialog(self, log_path)
            log_viewer.exec_()
        else:
            QMessageBox.warning(self, "警告", "日志文件不存在。")

    def create_task_widget(self, script_path: str) -> dict:
        """
        创建一个转换任务在UI上的显示小部件：
        - 脚本名
        - 进度条
        - 状态文字
        - 简要日志
        """
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

        return {
            'widget': widget,
            'script_label': script_label,
            'progress': progress,
            'status': status,
            'log': log
        }

    def closeEvent(self, event):
        """关闭窗口前，尝试停止所有任务"""
        if hasattr(self, 'tasks') and self.tasks:
            for task in self.tasks:
                task.stop()
            self.tasks = []
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())