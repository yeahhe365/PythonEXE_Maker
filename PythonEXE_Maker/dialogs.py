import os
import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QTextEdit
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QSize


class ManualDialog(QDialog):
    """使用说明对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")
        self.setFixedSize(800, 600)
        
        # 对话框样式示例（也可移到 main 的全局样式中统一管理）
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QTextBrowser {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """)

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
            <li>如需添加外部文件（资源、数据等），可在“高级设置”中的“附加文件”处点击按钮进行选择。</li>
            <li>点击 “开始转换” 按钮开始转换，如需中途取消可点击“取消转换”。</li>
            <li>转换进度及日志可在“日志”选项卡中查看。</li>
        </ol>
        <p><strong>注意事项:</strong></p>
        <ul>
            <li>图标文件支持 .png 和 .ico 格式 (.png 将自动转换为 .ico)。</li>
            <li>如 Python 脚本使用了外部库或资源文件，请确保在“额外模块”或“附加文件”中正确指定。</li>
            <li>“额外模块”处可输入需要隐藏导入的模块名称（多个用逗号分隔）。</li>
            <li>若需附加文件，可使用“附加文件”功能按钮进行选择。</li>
        </ul>
        <p><strong>更多信息:</strong></p>
        <ul>
            <li><a href="https://github.com/yeahhe365/PythonEXE_Maker">GitHub 项目地址</a></li>
            <li><a href="https://www.yeahhe.online/">官方网站</a></li>
            <li><a href="https://www.linuxdo.com/users/yeahhe">LINUXDO 论坛主页</a></li>
        </ul>
        """


class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 PythonEXE Maker")
        self.setFixedSize(600, 400)

        # 同样也可以为 AboutDialog 添加简易样式
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QTextBrowser {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 12))

        # 尝试加载同目录的logo.png
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, 'logo.png')
        if os.path.exists(logo_path):
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
    """查看日志文件的对话框"""
    def __init__(self, parent=None, log_path="app.log"):
        super().__init__(parent)
        self.setWindowTitle("查看日志文件")
        self.setFixedSize(800, 600)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QTextEdit {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        self.load_log(log_path)

    def load_log(self, log_path):
        """加载并显示日志文件内容"""
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
            except Exception as e:
                self.text_edit.setPlainText(f"无法读取日志文件: {e}")
        else:
            self.text_edit.setPlainText("日志文件不存在。")