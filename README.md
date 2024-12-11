# PythonEXE Maker

![iogo](https://github.com/user-attachments/assets/b78ea5b7-537b-4416-b886-394ffc291014)


**PythonEXE Maker** 是一个开源且免费的工具，旨在将 Python 脚本转换为独立的可执行文件（EXE）。通过友好的图形用户界面，用户可以轻松配置转换参数，管理多个转换任务，并自定义生成的 EXE 文件的各种属性，如图标、版本信息等。


## 特性

- **拖拽支持**：直接将 `.py` 文件拖入程序窗口，快速添加转换任务。
- **批量转换**：一次性转换多个 Python 脚本为 EXE 文件。
- **自定义设置**：
  - 选择转换模式（GUI 模式或命令行模式）。
  - 指定输出目录。
  - 设置 EXE 文件名称。
  - 添加自定义图标（支持 `.png` 和 `.ico` 格式，`.png` 会自动转换为 `.ico`）。
  - 配置文件版本信息和版权信息。
  - 指定额外的隐藏导入模块和附加 PyInstaller 参数。
- **任务管理**：实时查看每个转换任务的进度和状态。
- **日志查看**：详细的转换日志，方便排查问题。
- **可定制的“关于”对话框**：内嵌项目 Logo，展示项目信息。
- **依赖检查**：程序启动时自动检查并提示安装必要的依赖库。

## 截图

### 主界面

![Main Interface](screenshots/main_interface.png)

### 转换任务管理

![Task Management](screenshots/task_management.png)

### 日志查看

![Log Viewer](screenshots/log_viewer.png)

### 关于对话框

![About Dialog](screenshots/about_dialog.png)

*请将上述截图添加到项目的 `screenshots` 文件夹中，并根据需要调整图片路径。*

## 安装

### 前提条件

- **操作系统**：Windows
- **Python 版本**：Python 3.6 及以上
- **依赖库**：
  - [PyQt5](https://pypi.org/project/PyQt5/)
  - [Pillow](https://pypi.org/project/Pillow/)
  - [PyInstaller](https://pypi.org/project/PyInstaller/)

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/yeahhe365/PythonEXE_Maker.git
   cd PythonEXE_Maker
   ```

2. **创建虚拟环境（可选）**

   ```bash
   python -m venv venv
   source venv/bin/activate  # 对于 Windows 用户使用 venv\Scripts\activate
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

   *如果没有 `requirements.txt` 文件，请手动安装依赖：*

   ```bash
   pip install PyQt5 Pillow PyInstaller
   ```

## 使用说明

1. **运行程序**

   ```bash
   python PythonEXE_Maker_1.1.py
   ```

2. **配置转换参数**

   - **转换模式**：选择生成的 EXE 是带控制台（命令行模式）还是不带控制台（GUI 模式）。
   - **输出目录**：指定生成的 EXE 文件的存放位置，默认为源文件所在目录。
   - **EXE 信息**：
     - **EXE 名称**：设置生成的 EXE 文件名称，默认为源文件同名。
     - **图标文件**：选择一个图标文件用于 EXE，支持 `.png` 和 `.ico` 格式。
     - **文件版本**：设置 EXE 文件的版本号（格式：X.X.X.X）。
     - **版权信息**：设置 EXE 文件的版权信息。
   - **高级设置**：
     - **额外模块**：输入需要隐藏导入的模块名称，多个模块以逗号分隔。
     - **附加参数**：输入 PyInstaller 的其他命令行参数。

3. **添加转换任务**

   - **拖拽文件**：将 `.py` 文件直接拖入程序窗口的拖放区域。
   - **浏览文件**：点击“浏览文件”按钮，选择要转换的 Python 脚本。

4. **开始转换**

   - 点击“开始转换”按钮，程序将开始转换选中的 Python 脚本。
   - 转换过程中可以在“任务管理”选项卡中查看每个任务的进度和状态。
   - 转换日志可以在“日志”选项卡中查看详细信息。

5. **取消转换**

   - 在转换过程中，可以点击“取消转换”按钮，停止所有正在进行的转换任务。

## 贡献

欢迎任何形式的贡献！您可以通过以下方式参与：

- **提交 Issue**：在 [GitHub Issues](https://github.com/yeahhe365/PythonEXE_Maker/issues) 中提交您的问题或建议。
- **提交 Pull Request**：Fork 本仓库，进行修改后提交 Pull Request，我们会尽快审核。
- **捐赠支持**：如果您觉得这个项目对您有帮助，可以通过 [请开发者喝咖啡](https://b23.tv/Sni5cax) 来支持我。

## 许可证

本项目采用 [MIT 许可证](LICENSE) 进行许可。您可以自由地使用、修改和分发本项目的代码，但需要保留原作者的版权声明和许可说明。

## 联系我们

- **作者**：yeahhe365
- **GitHub**：[https://github.com/yeahhe365/PythonEXE_Maker](https://github.com/yeahhe365/PythonEXE_Maker)
- **官方网站**：[https://www.yeahhe.online/](https://www.yeahhe.online/)
- **论坛主页**：[LINUXDO 论坛](https://www.linuxdo.com/users/yeahhe)
- **支持链接**：[请开发者喝咖啡](https://b23.tv/Sni5cax)
