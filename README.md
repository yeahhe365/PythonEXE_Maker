# PythonEXE Maker

![iogo](https://github.com/user-attachments/assets/b78ea5b7-537b-4416-b886-394ffc291014)

**PythonEXE Maker** is an open source and free tool designed to convert Python scripts into standalone executable files (EXE). Through a friendly graphical user interface, users can easily configure conversion parameters, manage multiple conversion tasks, and customize various properties of the generated EXE file, such as icon, version information, etc.

## Features

- **Drag and drop support**: Directly drag `.py` files into the program window to quickly add conversion tasks.

- **Batch conversion**: Convert multiple Python scripts to EXE files at once.

- **Custom settings**:
  - Select the conversion mode (GUI mode or command line mode).
  - Specify the output directory.
  - Set the EXE file name.
  - Add a custom icon (supports `.png` and `.ico` formats, `.png` will be automatically converted to `.ico`).
  - Configure version information and copyright information of the file.
  - Specify additional hidden import modules and additional PyInstaller parameters.
- **Task management**: View the progress and status of each conversion task in real time.
- **Log viewing**: Detailed conversion log for easy troubleshooting.
- **Customizable "About" dialog**: Embedded project logo to display project information.
- **Dependency check**: Automatically check and prompt to install necessary dependency libraries when the program starts.

## Screenshots

### Main interface

![image](https://github.com/user-attachments/assets/5186bea7-476a-4063-ab2e-3a6cc5f5de99)

### Conversion task management

![image](https://github.com/user-attachments/assets/1a0041d9-a731-46e1-825c-45283e99c75b)

### Log view

![image](https://github.com/user-attachments/assets/1118b684-42c0-436a-a70a-e8b4da5b1e3d)

### About Dialog

![image](https://github.com/user-attachments/assets/b31b03a7-145f-4f18-936e-617a6c26ec39)

*Please add the above screenshot to the `screenshots` folder of your project and adjust the image path as needed. *

## Installation

### Prerequisites

- **Operating system**: Windows

- **Python version**: Python 3.6 and above

- **Dependencies**:

  - [PyQt5](https://pypi.org/project/PyQt5/)

  - [Pillow](https://pypi.org/project/Pillow/)

  - [PyInstaller](https://pypi.org/project/PyInstaller/)

### Installation steps

1. **Clone repository**

    ```bash
    git clone https://github.com/yeahhe365/PythonEXE_Maker.git
    cd PythonEXE_Maker
    ```

2. **Create a virtual environment (optional)**

    ```bash
    python -m venv venv
    source venv/bin/activate # For Windows users, use venv\Scripts\activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

    *If there is no `requirements.txt` file, please install the dependencies manually:*

    ```bash
    pip install PyQt5 Pillow PyInstaller
    ```

## Instructions

1. **Run the program**

    ```bash
    python PythonEXE_Maker_1.1.py
    ```

2. **Configure conversion parameters**

   - **Conversion mode**: Select whether the generated EXE is with a console (command line mode) or without a console (GUI mode).

   - **Output directory**: Specify the storage location of the generated EXE file, which defaults to the directory where the source file is located.

   - **EXE information**:

     - **EXE name**: Set the name of the generated EXE file, which defaults to the same name as the source file.

     - **Icon file**: Select an icon file for EXE, supporting `.png` and `.ico` formats.

     - **File version**: Set the version number of the EXE file (format: X.X.X.X).
     - **Copyright information**: Set the copyright information of the EXE file.
   - **Advanced settings**:
     - **Additional modules**: Enter the module names that need to be hidden import. Multiple modules are separated by commas.
     - **Additional arguments**: Enter additional command line arguments for PyInstaller.

3. **Add conversion task**

   - **Drag and drop files**: Drag the `.py` file directly into the drag and drop area of the program window.
   - **Browse files**: Click the "Browse files" button to select the Python script to be converted.

4. **Start conversion**

   - Click the "Start Convert" button and the program will start converting the selected Python script.
   - During the conversion process, you can view the progress and status of each task in the "Task Management" tab.
   - The Conversion logs can be viewed in detail in the "Log" tab.

5. **Cancel conversion**

   - During the conversion process, you can click the "Cancel Conversion" button to stop all ongoing conversion tasks.

## Contribution

Any form of contribution is welcome! You can participate in the following ways:

  - **Submit an Issue**: Submit your questions or suggestions in [GitHub Issues](https://github.com/yeahhe365/PythonEXE_Maker/issues).
  - **Submit a Pull Request**: Fork this repository, make modifications and submit a Pull Request, we will review it as soon as possible.
  - **Donation support**: If you find this project is helpful to you, you can support me by [Buying the developer a coffee](https://b23.tv/Sni5cax).

## License

This project is licensed under the [MIT License](LICENSE). You can freely use, modify and distribute the code of this project, but you need to retain the original author's copyright statement and license instructions.

## Contact us

- **Author**: yeahhe365
- **GitHub**: [https://github.com/yeahhe365/PythonEXE_Maker](https://github.com/yeahhe365/PythonEXE_Maker)
- **Official website**: [https://www.yeahhe.online/](https://www.yeahhe.online/)
- **Forum homepage**: [LINUXDO Forum](https://www.linuxdo.com/users/yeahhe)
- **Support link**: [Coffee for developers](https://b23.tv/Sni5cax)