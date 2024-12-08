try:
    import CmdLog as cl  # 导入模块
except ImportError:
    print("错误程序无法使用，正在退出程序...")
    exit(1)

try:
    import sys
    cl.log("模块", "模块sys导入成功")

    import threading
    cl.log("模块", "模块threading导入成功")

    import requests
    cl.log("模块", "模块requests导入成功")

    import os
    cl.log("模块", "模块os导入成功")

    import json
    cl.log("模块", "模块json导入成功")

    import platform
    cl.log("模块", "模块platform导入成功")

    from urllib.parse import urlparse
    cl.log("模块", "模块urlparse导入成功")

    from datetime import datetime
    cl.log("模块", "模块datetime导入成功")

    from PyQt5 import QtWidgets, QtCore
    cl.log("模块", "模块PyQt5.QtWidgets导入成功")

    import time  # 用于睡眠函数

except ImportError as e:
    print("模块导入失败", e)
    cl.log("退出", "模块导入失败: " + str(e))
    input("按回车键退出")
    exit()

# ====================================================
# 配置文件路径
config_file_path = 'config.json'

# 默认配置
default_config = {
    "default_threads": 4,
    "username": "Guest",
    "version": "1.0.0",
    "first_run_time": str(datetime.now()),
    "program_directory": os.getcwd(),  # 添加程序目录
    "computer_info": {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    }
}

def load_config():
    """加载配置"""
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("配置文件格式错误，使用默认配置。")
            cl.log("配置", "配置文件格式错误，使用默认配置。")
            return default_config
    else:
        with open(config_file_path, 'w') as f:
            json.dump(default_config, f, indent=4)
            cl.log("配置", "配置文件不存在，已创建默认配置文件。")
        return default_config


class DownloadThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, str, int)  # file_name, thread_id
    finished = QtCore.pyqtSignal()  # 记录下载完成的信号
    error = QtCore.pyqtSignal(str)  # 错误信息信号

    def __init__(self, url, num_threads, file_name):
        super().__init__()
        self.url = url
        self.num_threads = num_threads
        self.file_name = file_name

    def run(self):
        try:
            cl.log("下载", f"开始进行 HTTP 下载: {self.url}")
            self.http_download()
        except Exception as err:
            self.error.emit(str(err))
            cl.log("下载错误", f"下载过程中出现错误: {str(err)}")

    def http_download(self):
        try:
            response = requests.head(self.url)
            file_size = int(response.headers['Content-Length'])
            cl.log("下载", f"文件大小: {file_size} bytes")

            with open(f'{self.file_name}.file', 'wb') as f:
                f.truncate(file_size)

            chunk_size = file_size // self.num_threads
            threads = []
            for i in range(self.num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i != self.num_threads - 1 else file_size - 1
                thread = threading.Thread(target=self.download_chunk_http, args=(start, end, i))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            self.finished.emit()
            cl.log("下载", "HTTP 下载完成")
        except Exception as err:
            self.error.emit(f"HTTP 下载错误: {str(err)}")
            cl.log("下载错误", f"HTTP 下载出现错误: {str(err)}")

    def download_chunk_http(self, start, end, thread_id):
        try:
            headers = {'Range': f'bytes={start}-{end}'}
            response = requests.get(self.url, headers=headers, stream=True)
            response.raise_for_status()  # 检查请求是否成功
            with open(f'{self.file_name}.file', 'r+b') as f:
                f.seek(start)
                f.write(response.content)

            self.progress.emit((end - start + 1) // (1024 * 1024), self.file_name, thread_id)
            cl.log("下载进度", f"线程 {thread_id + 1}: 下载进度 {(end - start + 1) // (1024 * 1024)} MB")
        except Exception as err:
            self.error.emit(f"下载进度错误: {str(err)}")
            cl.log("下载错误", f"下载进度出现错误: {str(err)}")


class DownloadManager(QtWidgets.QWidget):
    def __init__(self, config):
        super().__init__()
        cl.log("窗口", "初始化下载管理器窗口.")
        self.initUI(config)

    def initUI(self, config):
        self.setWindowTitle('多线程下载器')
        self.setGeometry(300, 200, 600, 400)  # 调整窗口大小以适应侧边内容

        # 创建主布局
        layout = QtWidgets.QHBoxLayout(self)

        # 创建左侧布局
        left_layout = QtWidgets.QVBoxLayout()

        self.url_input = QtWidgets.QTextEdit(self)
        self.url_input.setPlaceholderText("请输入下载链接，每行一个")

        self.num_threads_input = QtWidgets.QLineEdit(self)
        self.num_threads_input.setPlaceholderText(f"请输入线程数（默认为 {config['default_threads']}）")

        self.file_name_input = QtWidgets.QLineEdit(self)
        self.file_name_input.setPlaceholderText("自定义文件名（为空则使用URL的）")

        self.download_button = QtWidgets.QPushButton('开始下载', self)
        self.download_button.clicked.connect(self.start_download)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setValue(0)

        self.progress_label = QtWidgets.QLabel(self)

        left_layout.addWidget(self.url_input)
        left_layout.addWidget(self.num_threads_input)
        left_layout.addWidget(self.file_name_input)
        left_layout.addWidget(self.download_button)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.progress_label)

        # 将左侧布局添加到主布局
        layout.addLayout(left_layout)

        self.setLayout(layout)

        self.show_info(config)

    def show_info(self, config):
        info_text = f"用户名: {config['username']}\n"
        info_text += f"第一次启动时间: {config['first_run_time']}\n"
        info_text += f"计算机信息: {json.dumps(config['computer_info'], indent=4)}"
        self.progress_label.setText(info_text)
        cl.log("信息", "显示用户信息")

    def start_download(self):
        try:
            urls = self.url_input.toPlainText().strip().splitlines()
            num_threads_str = self.num_threads_input.text()
            num_threads = int(num_threads_str) if num_threads_str else config['default_threads']
            cl.log("操作", f"用户选择线程数 {num_threads}")

            if not urls:
                raise ValueError("请输入至少一个下载链接。")

            cl.log("操作", f"用户输入的下载链接: {urls}")

            for url in urls:
                if url:
                    custom_file_name = self.file_name_input.text()
                    if not custom_file_name:
                        parsed_url = urlparse(url)
                        custom_file_name = os.path.basename(parsed_url.path) or "downloaded_file"

                    cl.log("下载", f"准备下载: {url}，文件名: {custom_file_name}")
                    self.setWindowTitle(f"多线程下载器 - 下载文件: {custom_file_name}")

                    self.download_thread = DownloadThread(url, num_threads, custom_file_name)
                    self.download_thread.progress.connect(self.update_progress)
                    self.download_thread.finished.connect(self.download_completed)
                    self.download_thread.error.connect(self.show_error)  # 连接错误信号
                    self.download_thread.start()
                    cl.log("操作", f"启动下载线程: {url}")
                else:
                    raise ValueError("URL不能为空。")

        except ValueError as err:
            cl.log("错误", str(err))
            QtWidgets.QMessageBox.critical(self, "错误", str(err))
        except Exception as err:
            cl.log("错误", f"下载过程中出现了错误: {str(err)}")
            QtWidgets.QMessageBox.critical(self, "错误", f"下载过程中出现了错误: {str(err)}")

    def update_progress(self, value, file_name, thread_id):
        current_value = self.progress_bar.value() + value
        self.progress_bar.setValue(current_value)
        self.progress_label.setText(f"{file_name} - 线程 {thread_id + 1}: 已下载 {current_value} MB")
        cl.log("进度更新", f"{file_name} - 线程 {thread_id + 1}: 已下载 {current_value} MB")

    def download_completed(self):
        QtWidgets.QMessageBox.information(self, "下载完成", "所有文件下载完成！")
        cl.log("下载完成", "所有文件下载完成！")
        self.progress_bar.setValue(0)
        self.progress_label.setText("")

    def show_error(self, message):
        """显示下载过程中出现的错误"""
        QtWidgets.QMessageBox.critical(self, "错误", message)
        cl.log("错误", message)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")


def main():
    app = QtWidgets.QApplication(sys.argv)

    cl.log("窗口", "程序启动，加载配置...")
    config = load_config()  # 加载配置
    manager = DownloadManager(config)
    manager.show()

    cl.log("窗口", "下载管理器窗口显示")
    sys.exit(app.exec_())



main()
