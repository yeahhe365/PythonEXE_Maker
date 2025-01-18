import os
import sys
import subprocess
import logging

from PyQt5.QtCore import QRunnable, pyqtSignal, QObject

# 若要转换图标，需要尝试导入 Pillow
try:
    from PIL import Image
except ImportError:
    Image = None


class WorkerSignals(QObject):
    """定义 Worker 线程的信号"""
    status_updated = pyqtSignal(str)               # 用于传递状态信息字符串
    progress_updated = pyqtSignal(int)             # 用于更新进度条
    conversion_finished = pyqtSignal(str, int)     # (exe_path, exe_size)
    conversion_failed = pyqtSignal(str)            # 传递错误信息


class ConvertRunnable(QRunnable):
    """执行转换任务的 Runnable 类（配合 QThreadPool 使用）"""

    def __init__(self, script_path, convert_mode, output_dir, exe_name, icon_path,
                 file_version, copyright_info, extra_library, additional_options):
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
        """线程池执行入口"""
        version_file_path = None
        try:
            script_dir = os.path.dirname(self.script_path)
            exe_name = self.exe_name or os.path.splitext(os.path.basename(self.script_path))[0]
            output_dir = self.output_dir or script_dir

            if not self.ensure_pyinstaller():
                return

            # 准备 PyInstaller 命令参数
            options = self.prepare_pyinstaller_options(exe_name, output_dir)

            # 处理图标（如是PNG则自动转ICO）
            if self.icon_path:
                icon_file = self.handle_icon(script_dir)
                if icon_file:
                    options.append(f'--icon={icon_file}')

            # 生成版本信息文件
            if self.file_version or self.copyright_info:
                version_file_path = self.create_version_file(exe_name, script_dir)
                if version_file_path:
                    options.append(f'--version-file={version_file_path}')

            self.update_status("开始转换...")
            success = self.run_pyinstaller(options)

            if success:
                # 检查生成的exe文件
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
            # 任务结束
            self._is_running = False
            self.cleanup_files(version_file_path)

    def stop(self):
        """停止转换任务"""
        self._is_running = False

    def update_status(self, message: str):
        """更新转换状态（日志 + UI）"""
        logging.info(message)
        self.signals.status_updated.emit(message)

    def ensure_pyinstaller(self) -> bool:
        """确保本机已安装 PyInstaller，如未安装则尝试安装"""
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
        """准备 PyInstaller 命令行参数"""
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
        """处理图标：.png -> .ico 转换"""
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
        """生成版本信息文件"""
        try:
            from PyInstaller.utils.win32.versioninfo import (
                VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
                VarFileInfo, VarStruct
            )
        except ImportError as e:
            self.update_status(f"导入PyInstaller版本信息类失败: {e}")
            return ""

        version_numbers = self.file_version.split('.') if self.file_version else ['1', '0', '0', '0']
        if len(version_numbers) != 4 or not all(num.isdigit() for num in version_numbers):
            version_numbers = ['1', '0', '0', '0']

        # 构造版本信息
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
        """调用 PyInstaller 执行转换"""
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
                # 简易进度估计
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
        """清理临时文件（版本信息、转换后的ico等）"""
        script_dir = os.path.dirname(self.script_path)

        # 删除版本信息文件
        if version_file_path and os.path.exists(version_file_path):
            try:
                os.remove(version_file_path)
                self.update_status("删除版本信息文件。")
            except Exception as e:
                self.update_status(f"无法删除版本信息文件: {e}")

        # 若原图标是 png，则删除临时生成的 ico
        if self.icon_path and self.icon_path.lower().endswith('.png'):
            ico_path = os.path.join(script_dir, 'icon_converted.ico')
            if os.path.exists(ico_path):
                try:
                    os.remove(ico_path)
                    self.update_status("删除临时 ICO 文件。")
                except Exception as e:
                    self.update_status(f"无法删除临时 ICO 文件: {e}")