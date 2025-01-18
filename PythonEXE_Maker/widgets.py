from PyQt5.QtWidgets import QLabel, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal


class DropArea(QLabel):
    """拖放区域，用于拖入 .py 文件"""
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
        """检测拖入文件是否为.py，符合则允许释放"""
        if event.mimeData().hasUrls() and any(url.toLocalFile().endswith('.py') for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """释放拖拽文件后，若是.py文件则发送信号"""
        paths = [
            url.toLocalFile() for url in event.mimeData().urls()
            if url.toLocalFile().endswith(".py")
        ]
        if paths:
            for path in paths:
                self.file_dropped.emit(path)
        else:
            QMessageBox.warning(self, "警告", "请拖放 Python 文件 (.py) 到窗口中。")