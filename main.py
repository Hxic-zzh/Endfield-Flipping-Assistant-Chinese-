# file name: main.py
import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication
from ui_main import MainWindow

def cleanup_on_startup():
    """程序启动时清理目录内容（不删除目录本身）"""
    directories_to_clean = ['debug_cells', 'debug_cells_x']
    for dir_name in directories_to_clean:
        if os.path.exists(dir_name):
            for item in os.listdir(dir_name):
                item_path = os.path.join(dir_name, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"清理 {item_path} 时出错: {e}")
            print(f"[启动清理] 已清空目录: {dir_name}")
        else:
            os.makedirs(dir_name, exist_ok=True)
            print(f"[启动清理] 创建目录: {dir_name}")

if __name__ == '__main__':
    print("程序启动，执行目录清理...")
    cleanup_on_startup()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())